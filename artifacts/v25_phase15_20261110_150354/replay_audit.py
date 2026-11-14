"""Replay Phase 1 and 1.5 evidence without any optimizer calls."""
import csv
import gzip
import json
import platform
import re
import subprocess
from ast import literal_eval
from collections import Counter, defaultdict
from hashlib import sha256
from math import fsum
from pathlib import Path
from zipfile import ZipFile

from run_diagnostic import ROOT, GRB, gp, compile_network, frozen_runs, initial_state, load_tables, manifest_bytes, receipts, serial
from prefab_v25.data import CELL, COMPONENT_ARC, OEM, PACK, PROD, T1, PRODUCTION_ARC, TRANSPORT_ARC, expand
from prefab_v25.model import _audit, _block

HERE = ROOT / 'artifacts' / 'v25_phase15_20261110_150354'
FORMAL = ROOT / 'artifacts' / 'v25_formal_20261110'
SOURCE = Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
SPEC = Path('E:/浏览器文件/V2.5_Phase1_spec_bundle_v2_with_manifest.zip')
OLD = SOURCE.with_name('paper_scale_instance_v1.zip')
SHA = '02143f46cab6e6a173a0f495e21b20d21311096f'
ARRAYS = ('inventory', 'supply', 'dispatch', 'deliveries')


def git(*args):
    return subprocess.check_output(('git', *args), cwd=ROOT, text=True).strip()


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def csv_file(name, rows):
    with (HERE / f'{name}.csv').open('w', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_blocks(path, diagnostic=False):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        data = json.load(stream)
    if diagnostic:
        data = data['scenarios']
    return {name: [{literal_eval(k): v for k, v in block[array].items()} for array in ARRAYS]
            for name, block in data.items()}


def check(network, scenario, x, arrays):
    for array in arrays:
        assert all(v >= -1e-7 and abs(v-round(v)) <= 1e-7 for v in array.values())
    assert all((key[0], key[1]) in network.external for key in arrays[1])
    result = _audit(network, scenario, initial_state(network, x), *arrays)
    assert all(v <= 1e-7 for k, v in result.items() if k.endswith('_residual')), result
    return result


def vin_counts(network, deliveries):
    due = Counter()
    on_time = Counter()
    served = Counter()
    for group in network.groups:
        order = group.representative
        cls = 'BEV' if (PACK, 1) in order.bom else 'nonBEV'
        due[cls, order.due] += len(group.orders)
        assignments = expand(group, {t: round(deliveries[group.id, t]) for t in network.periods})
        served[cls] += len(assignments)
        on_time[cls, order.due] += sum(t <= order.due for t in assignments.values())
    return due, on_time, served


def replay_reduced_oem(network, scenario, arrays, reduce, retained):
    """Remove BEV assembly/shipments from an archived feasible plan and replay."""
    _, supply, original_dispatch, original_deliveries = arrays
    dispatch, deliveries = original_dispatch.copy(), original_deliveries.copy()
    car = next(arc for arc in network.arcs if arc.origin == OEM and any(
        g.id in arc.recipes for g in network.groups))
    bev = [g for g in network.groups if (PACK, 1) in g.representative.bom]
    remaining = reduce
    dropped = Counter()
    for t in network.periods:
        for group in bev:
            key = (*car.key, group.id, t)
            qty = min(remaining, round(dispatch[key]))
            dispatch[key] -= qty
            remaining -= qty
            dropped[group.id] += qty
    assert remaining == 0
    for group in bev:
        for t in network.periods:
            key = (group.id, t)
            qty = min(dropped[group.id], round(deliveries[key]))
            deliveries[key] -= qty
            dropped[group.id] -= qty
    assert not any(dropped.values())

    state = initial_state(network, (0, 0, retained))
    arrival = receipts(network, scenario)
    events = defaultdict(int)
    for arc in network.arcs:
        for t in network.periods:
            for item, recipe in arc.recipes.items():
                quantity = dispatch[(*arc.key, item, t)]
                events[arc.destination, item, t+arc.lead] += quantity
                for child, coefficient in recipe:
                    events[arc.origin, child, t] -= coefficient*quantity
    for group in network.groups:
        for t in network.periods:
            events[group.representative.node, group.id, t] -= deliveries[group.id, t]
    stock = {}
    for t in network.periods:
        for node, item in state:
            key = (node, item, t)
            state[node, item] += events[key] + arrival.get(key, 0) + supply.get(key, 0)
            stock[key] = state[node, item]
    return stock, supply, dispatch, deliveries


def check_gurobi_rows(network, run, retained, blocks, worst, log_path):
    """Evaluate all original Gurobi rows and variable domains without optimizing."""
    with gp.Model('V25_DE' if run.de else 'V25_nominal') as model:
        model.Params.OutputFlag = 0
        buffers = [model.addVar(vtype=GRB.INTEGER, name=name) for name in ('x_cell_kit', 'x_t1_pack', 'x_oem_pack')]
        model.addConstr(gp.quicksum(c*x for c, x in zip(run.costs, buffers)) <= run.budget)
        state = initial_state(network, buffers)
        original = [_block(model, network, s, state, receipts(network, s), f's{i}')
                    for i, s in enumerate(run.scenarios)]
        if run.de:
            rho = model.addVar(lb=0, ub=1, name='rho')
            for block in original:
                model.addConstr(block[-1] >= network.demand_weight*rho)
            model.setObjective(rho, GRB.MAXIMIZE)
        else:
            model.setObjective(original[0][-1]/network.demand_weight, GRB.MAXIMIZE)
        model.update()
        fingerprint = f'0x{model.Fingerprint & 0xffffffff:08x}'
        archived, = re.findall(r'Model fingerprint: (0x[0-9a-f]+)', log_path.read_text(encoding='utf-8'))
        assert fingerprint == archived, (fingerprint, archived)
        values = {var.index: x for var, x in zip(buffers, (0, 0, retained))}
        if run.de:
            values[rho.index] = worst/network.demand_weight
        for scenario, block in zip(run.scenarios, original):
            for variables, quantities in zip(block[:4], blocks[scenario.name].values()):
                values.update({v.index: quantities[k] for k, v in variables.items()})
        assert len(values) == model.NumVars
        bound_residual = max(0, *(max(v.LB-values[v.index], values[v.index]-v.UB) for v in model.getVars()))
        int_residual = max(abs(values[v.index]-round(values[v.index])) for v in model.getVars()
                           if v.VType == GRB.INTEGER)
        row_residual = 0
        for constraint in model.getConstrs():
            row = model.getRow(constraint)
            diff = fsum(row.getCoeff(j)*values[row.getVar(j).index] for j in range(row.size()))-constraint.RHS
            violation = abs(diff) if constraint.Sense == '=' else diff if constraint.Sense == '<' else -diff
            row_residual = max(row_residual, violation)
        objective = fsum(v.Obj*values[v.index] for v in model.getVars())
        assert abs(objective-worst/network.demand_weight) <= 1e-12
        assert max(bound_residual, int_residual, row_residual) <= 1e-7
        return dict(fingerprint=fingerprint, rows=model.NumConstrs, variables=model.NumVars,
                    row_residual=row_residual, bound_residual=bound_residual, integer_residual=int_residual,
                    objective=objective, optimizer_calls=0)


def main():
    assert git('rev-parse', 'HEAD') == SHA and not git('status', '--porcelain', '--untracked-files=no')
    spec = manifest_bytes(SPEC)
    assert spec == (FORMAL / 'manifest.json').read_bytes()
    manifest = json.loads(spec)
    runs = {run.id: run for run in frozen_runs(spec)}
    tables = load_tables(SOURCE)
    network, _ = compile_network(tables)
    workbook_battery_rows = {
        'battery_initial_inventory_direct.csv': tuple(row for row in tables['initial_inventories']
                                                      if row[1] in (*CELL, PACK)),
        'battery_initial_flows_direct.csv': tuple(row for row in tables['initial_flows']
                                                  if row[2] in (*CELL, PACK)),
    }
    with ZipFile(SPEC) as z:
        spec_members = z.namelist()
        for name, rows in workbook_battery_rows.items():
            lines = z.read(f'paper_scale_v2/{name}').decode('utf-8-sig').splitlines()
            csv_rows = list(csv.reader(lines))[1:]
            assert csv_rows == [[str(int(v)) if isinstance(v, (int, float)) else v for v in row]
                                for row in rows]
    published = json.loads((HERE / 'mendeley_file_index.json').read_text(encoding='utf-8'))
    assert len(published) == 1 and published[0]['content_details']['sha256_hash'] == network.source_sha256
    formal = json.loads((FORMAL / 'audit.json').read_text(encoding='utf-8'))
    result_rows, scenario_rows, risk_rows, historical_rows, period_rows, witness_rows = [], [], [], [], [], []
    formal_blocks = {}
    for run_id, run in runs.items():
        result = formal['results'][run_id]
        path = FORMAL / result['solution_artifact']
        assert digest(path) == result['solution_sha256']
        formal_blocks[run_id] = read_blocks(path)

    def record(run_id, label, run, budget, result, blocks):
        x = tuple(result['buffers'][name] for name in manifest['first_stage_buffers']['variables'])
        used = sum(c*q for c, q in zip(run.costs, x))
        assert used <= budget + 1e-7
        start = len(scenario_rows)
        for scenario in run.scenarios:
            arrays = blocks[scenario.name]
            residual = check(network, scenario, x, arrays)
            due, on_time, served = vin_counts(network, arrays[-1])
            assert sum(due.values()) == network.demand_weight == 28000
            total = sum(on_time.values())
            assert total == residual['weighted_on_time']
            assert total == round(result['scenarios'][scenario.name]['weighted_on_time'])
            scenario_rows.append(dict(run=run_id, label=label, scenario=scenario.name, demand=28000,
                                      total_on_time=total, service_rate=total/28000, scenario_objective=total/28000,
                                      total_delivered=sum(served.values()), bev_on_time=sum(v for (kind, _), v in on_time.items() if kind == 'BEV'),
                                      non_bev_on_time=sum(v for (kind, _), v in on_time.items() if kind == 'nonBEV'),
                                      shared_de_objective=result['objective'] if run.de else '',
                                      active_reduction={'NOM': 'none', 'L1_CERT': 'L1 t66 component arrivals -50%',
                                                        'L2_CERT': 'L2 t64-t66 pack production -50%',
                                                        'L3_CERT': 'L3 t64-t66 pack transport -50%'}[scenario.name],
                                      **residual))
        rows = scenario_rows[start:]
        worst = min(r['total_on_time'] for r in rows)
        assert abs(result['objective']-worst/28000) <= 1e-7
        result_rows.append(dict(run=run_id, label=label, status=result['status'],
                                solver_reported_certified=result['certified'], objective=result['objective'],
                                upper_bound=result['bound'], mip_gap=result['gap'], seconds=result['seconds'],
                                max_residual=result['quality_residual'], worst_on_time=worst,
                                x_cell_kit=x[0], x_t1_pack=x[1], x_oem_pack=x[2], budget=budget,
                                budget_used=used, budget_slack=budget-used))
        for row in rows:
            row['at_returned_worst'] = row['total_on_time'] == worst

    for run_id, run in runs.items():
        record(run_id, 'ARCHIVED_PHASE1', run, run.budget, formal['results'][run_id], formal_blocks[run_id])
    de = runs['DE_B0']
    scenarios = {s.name: s for s in de.scenarios}
    diagnostic_files = sorted(HERE.glob('DIAGNOSTIC_ONLY_DE_B*.json.gz'))
    assert [p.name for p in diagnostic_files] == ['DIAGNOSTIC_ONLY_DE_B100.json.gz']
    with gzip.open(diagnostic_files[0], 'rt', encoding='utf-8') as stream:
        diagnostic = json.load(stream)
    diag_blocks = read_blocks(diagnostic_files[0], diagnostic=True)
    record('DE_B100', 'DIAGNOSTIC_ONLY', de, diagnostic['budget'], diagnostic, diag_blocks)
    assert diagnostic['certified'] and diagnostic['worst_on_time'] == 26074

    mechanism_rows = []
    bev = [g for g in network.groups if (PACK, 1) in g.representative.bom]
    for label, blocks, x in (('DE_B0', formal_blocks['DE_B0'], 0), ('DIAGNOSTIC_ONLY_DE_B100', diag_blocks, 100)):
        for s in de.scenarios:
            inventory, _, dispatch, deliveries = blocks[s.name]
            arrival = receipts(network, s)
            for t in network.periods:
                mechanism_rows.append(dict(run=label, scenario=s.name, period=t, x_oem_pack=x,
                                           cell_1_receipt=arrival.get((PROD, CELL[0], t), 0),
                                           cell_2_receipt=arrival.get((PROD, CELL[1], t), 0),
                                           cell_3_receipt=arrival.get((PROD, CELL[2], t), 0),
                                           pack_production_dispatch=dispatch[(*PRODUCTION_ARC, PACK, t)],
                                           pack_transport_dispatch=dispatch[(*TRANSPORT_ARC, PACK, t)],
                                           oem_pack_end_inventory=inventory[OEM, PACK, t],
                                           bev_on_time_delivery=sum(deliveries[g.id, t] for g in bev if t <= g.representative.due)))

    nom = formal_blocks['nominal_B0']['NOM']
    due, on_time, _ = vin_counts(network, nom[-1])
    for (kind, t), demand in sorted(due.items()):
        count = on_time[kind, t]
        period_rows.append(dict(family=kind, due_period=t, demand=demand, on_time=count, not_on_time=demand-count))
    assert (sum(due.values()), sum(on_time.values())) == (28000, 26448)

    arc_by_key = {a.key: a for a in network.arcs}
    for node in (PROD, T1, OEM, 'battery-supplier_trans'):
        for item in (*CELL, PACK):
            if (node, item) in network.initial:
                historical_rows.append(dict(kind='initial_stock', origin=node, destination=node, item=item,
                                            dispatch_or_stock_t=60, receipt_t=60, quantity=network.initial[node, item]))
    for i, j, item, t, q in network.historical:
        if item in (*CELL, PACK):
            historical_rows.append(dict(kind='historical_dispatch', origin=i, destination=j, item=item,
                                        dispatch_or_stock_t=t, receipt_t=t+arc_by_key[i, j].lead, quantity=q))
    for s in de.scenarios:
        reduced = receipts(network, s)
        normal = receipts(network, scenarios['NOM'])
        for t, factor in s.arrival.items():
            if factor < 1:
                for item in CELL:
                    risk_rows.append(dict(scenario=s.name, kind='L1_arrival', t=t, item=item, multiplier=factor,
                                          nominal=normal[PROD, item, t], reduced=reduced[PROD, item, t]))
        for kind, profile, arc in (('L2_pack_production', s.production, PRODUCTION_ARC),
                                   ('L3_pack_transport', s.transport, TRANSPORT_ARC)):
            for t, factor in profile.items():
                if factor < 1:
                    base = arc_by_key[arc].capacity[t]
                    risk_rows.append(dict(scenario=s.name, kind=kind, t=t, item=PACK, multiplier=factor,
                                          nominal=base, reduced=base*factor))
    for row in risk_rows:
        row['loss'] = row['nominal']-row['reduced']

    prod_recipe = arc_by_key[PRODUCTION_ARC].recipes[PACK]
    available_packs = network.initial[OEM, PACK] + network.initial[T1, PACK] + sum(
        row['quantity'] for row in historical_rows if row['kind'] == 'historical_dispatch' and row['item'] == PACK)
    early_kits = min(network.initial[PROD, item]//coefficient for item, coefficient in prod_recipe)
    caps = {s.name: available_packs+early_kits+min(receipts(network, s)[PROD, item, 66]//coefficient
                                                   for item, coefficient in prod_recipe) for s in de.scenarios}
    assert (available_packs, early_kits, caps['NOM'], caps['L1_CERT']) == (411, 93, 1451, 977)
    assert {key for key in network.external if key[1] in (*CELL, PACK)} == {
        (COMPONENT_ARC[0], item) for item in CELL}
    assert {a.key for a in network.arcs if set(a.recipes) & set((*CELL, PACK))} == {
        COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC}
    assert network.periods[0]+arc_by_key[COMPONENT_ARC].lead > network.periods[-1]
    assert 73+arc_by_key[PRODUCTION_ARC].lead+arc_by_key[TRANSPORT_ARC].lead > network.periods[-1]
    assert all(v == 0 for v in formal['results']['DE_B50']['buffers'].values())
    fixed_zero = {key: {'service_lower_bound': check(network, scenarios[key], (0, 0, 0), nom)['weighted_on_time'],
                        'battery_mass_upper_bound': caps[key]+24997}
                  for key in ('NOM', 'L2_CERT', 'L3_CERT')}
    fixed_zero['L1_CERT'] = {'service_lower_bound': check(network, scenarios['L1_CERT'], (0, 0, 0),
                                                         formal_blocks['DE_B0']['L1_CERT'])['weighted_on_time'],
                            'battery_mass_upper_bound': caps['L1_CERT']+24997}
    assert all(row['service_lower_bound'] == row['battery_mass_upper_bound'] for row in fixed_zero.values())

    witnesses, matrices = {}, {}
    for target, retained, parent in (('nominal_B20', 20, formal_blocks['nominal_B100']),
                                     ('nominal_B50', 50, formal_blocks['nominal_B100']),
                                     ('DE_B50', 50, diag_blocks)):
        run = runs[target]
        witnesses[target] = {}
        for s in run.scenarios:
            arrays = replay_reduced_oem(network, s, parent[s.name], 100-retained, retained)
            measured = check(network, s, (0, 0, retained), arrays)
            witnesses[target][s.name] = dict(zip(ARRAYS, arrays))
            assert 8756*retained == run.budget
            witness_rows.append(dict(run=target, scenario=s.name, x_cell_kit=0, x_t1_pack=0, x_oem_pack=retained,
                                     budget_used=8756*retained, budget_slack=0,
                                     archived_bound=formal['results'][target]['bound'],
                                     feasible_service=measured['weighted_on_time']/28000, **measured))
        assert min(r['feasible_service'] for r in witness_rows if r['run'] == target) > formal['results'][target]['bound']
        worst = min(r['weighted_on_time'] for r in witness_rows if r['run'] == target)
        matrices[target] = check_gurobi_rows(network, run, retained, witnesses[target], worst, FORMAL/f'{target}.log')
    with gzip.open(HERE / 'read_only_feasible_witnesses.json.gz', 'wt', encoding='utf-8') as out:
        json.dump(serial(witnesses), out, allow_nan=False)

    prior_spec, = ROOT.glob('V2.1*.zip')
    input_files = [SOURCE, SPEC, OLD, prior_spec, HERE/'mendeley_file_index.json',
                   ROOT/'docs'/'v25_phase1_formal_certification.md',
                   *sorted(FORMAL.iterdir()), *sorted((ROOT/'src'/'prefab_v25').glob('*.py')),
                   ROOT/'examples'/'run_v25_phase1.py', ROOT/'examples'/'run_v25_formal.py',
                   Path(__file__), HERE/'run_diagnostic.py']
    hashes = {str(p.resolve()): digest(p) for p in input_files}
    with ZipFile(SOURCE) as z:
        members = z.namelist()
        for member in members:
            if member.endswith('.xlsb'):
                hashes[f'{SOURCE}::{member}'] = sha256(z.read(member)).hexdigest()
    with ZipFile(SPEC) as z:
        for member in ('paper_scale_v2/manifest.json', 'paper_scale_v2/README.md', 'paper_scale_v2/FREEZE_NOTE.md',
                       'paper_scale_v2/data_provenance_matrix.csv',
                       *(f'paper_scale_v2/{name}' for name in workbook_battery_rows)):
            hashes[f'{SPEC}::{member}'] = sha256(z.read(member)).hexdigest()
    with ZipFile(OLD) as z:
        old_members = z.namelist()
        hashes[f'{OLD}::README.md'] = sha256(z.read('README.md')).hexdigest()
    with ZipFile(prior_spec) as z:
        prior_members = z.namelist()
    audit = dict(status='HOLD_HISTORICAL_SHORTAGE_EMBEDDED', git_sha=SHA, branch=git('branch', '--show-current'),
                 tracked_changes=git('status', '--porcelain', '--untracked-files=no'),
                 input_sha256=hashes, environment=dict(python=platform.python_version(),
                 gurobi=diagnostic['gurobi_version'], license='Academic, non-commercial; expires 2027-04-10',
                 threads=4, seed=20261110, feasibility_tol=1e-9, integrality_tol=1e-9, time_limit=180),
                 baseline=dict(demand=28000, on_time=26448, not_on_time=1552, bev_demand=3003,
                               bev_on_time=1451, non_bev_on_time=24997, t59_article_shortage=860,
                               t59_unit_mapping_verified=False, counterpart_not_constructed=True,
                               nominal_type='post_shortage_nominal', frozen_csv_battery_rows_equal_source=True,
                               explanation='t60 stock and historical flow carry the depleted battery trajectory',
                               battery_initial_and_transit=available_packs, preexisting_kits=early_kits,
                               battery_horizon_ceiling=caps),
                 runs=result_rows, scenarios=scenario_rows, risk_reductions=risk_rows,
                 independently_certified_fixed_zero_buffers=fixed_zero, true_fixed_zero_worst='L1_CERT',
                 diagnostic=dict(optimizer_calls=1, result='first_strict_improvement_at_B100',
                                 skipped=['B150', 'B200'], extra_deliveries=100, extra_oem_packs=100,
                                 proved_limiting_scenario='L1_CERT', at_returned_worst=['L1_CERT', 'L3_CERT'],
                                 label='DIAGNOSTIC_ONLY'),
                 replay_optimizer_calls=0, historical_supply_modified=False,
                 archived_upper_bound_contradicted=['nominal_B20', 'nominal_B50', 'DE_B50'],
                 feasible_witnesses=witness_rows, gurobi_original_matrix_replay=matrices,
                 cause_of_bound_discrepancy='UNDETERMINED',
                 counterpart=dict(found=False, public_index=published, original_zip_members=members,
                                  frozen_spec_zip_members=spec_members, earlier_v21_zip_members=prior_members,
                                  exploratory_v1_zip_members=old_members,
                                  search_scope=['Mendeley V1 and DOI', 'published Sections 4.2, 4.7 and 4.9',
                                                'local prefab research data', 'project files and relevant historical paths'],
                                  paper='https://doi.org/10.1016/j.ejor.2020.08.005',
                                  dataset='https://data.mendeley.com/datasets/pr3sdy5vp3/1'),
                 output_sha256={p.name: digest(p) for p in [*diagnostic_files, *HERE.glob('DIAGNOSTIC_ONLY*.log'),
                                                           HERE/'read_only_feasible_witnesses.json.gz']})
    for name, rows in [('all_runs', result_rows), ('all_scenarios', scenario_rows),
                       ('diagnostic_runs', [r for r in result_rows if r['label'] == 'DIAGNOSTIC_ONLY']),
                       ('diagnostic_scenarios', [r for r in scenario_rows if r['label'] == 'DIAGNOSTIC_ONLY']),
                       ('scenario_reductions', risk_rows), ('battery_initial_and_transit', historical_rows),
                       ('diagnostic_battery_period_ledger', mechanism_rows),
                       ('nominal_B0_due_cohorts', period_rows), ('read_only_feasible_witnesses', witness_rows)]:
        csv_file(name, rows)
        audit['output_sha256'][f'{name}.csv'] = digest(HERE / f'{name}.csv')
    (HERE / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(fixed_zero=fixed_zero, witnesses=witness_rows, scenario_rows=scenario_rows[-4:]), indent=2))


if __name__ == '__main__':
    main()
