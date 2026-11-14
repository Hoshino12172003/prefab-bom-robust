"""Check exact feasible vectors and independent material/budget upper bounds."""
import io
import os
from collections import defaultdict
from fractions import Fraction
from zipfile import ZIP_DEFLATED, ZipFile

from run_audit import (
    BUFFER_NAMES, FORMAL, GRB, HERE, ROOT, SOURCE, WITNESSES, build, compare, compile_network,
    csv_file, digest, frozen_runs, gp, gzip, json, load_tables, manifest_bytes, platform,
    re, receipts, save_json, subprocess,
)
from prefab_v25.data import CELL, COMPONENT_ARC, OEM, PACK, PROD, PRODUCTION_ARC, TRANSPORT_ARC
from prefab_v25.model import initial_state


def exact(value):
    return int(value) if isinstance(value, (float, int)) and value == int(value) else Fraction(value)


def exact_expr(expr, values):
    return exact(expr.getConstant()) + sum(exact(expr.getCoeff(i))*values[expr.getVar(i).index]
                                           for i in range(expr.size()))


def sol_values(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return dict(line.rstrip().rsplit(maxsplit=1) for line in stream if not line.startswith('#') and line.strip())


def physical_upper(network, run):
    arcs = {a.key: a for a in network.arcs}
    assert {a.key for a in network.arcs if set(a.recipes) & set((*CELL, PACK))} == {
        COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC}
    assert {key for key in network.external if key[1] in (*CELL, PACK)} == {(COMPONENT_ARC[0], i) for i in CELL}
    assert network.periods[0]+arcs[COMPONENT_ARC].lead > network.periods[-1]
    assert all(g.representative.weight == 1 and all(c == 1 for i, c in g.representative.bom if i == PACK)
               for g in network.groups)
    non_bev = sum(len(g.orders) for g in network.groups if (PACK, 1) not in g.representative.bom)
    lead = arcs[PRODUCTION_ARC].lead+arcs[TRANSPORT_ARC].lead
    assert lead == 2
    stock_packs = sum(q for (_, i), q in network.initial.items() if i == PACK)
    committed_packs = sum(q for o, d, i, t, q in network.historical if i == PACK and
                          t+arcs[o, d].lead+(0 if d == OEM else arcs[TRANSPORT_ARC].lead) <= network.periods[-1])
    assert (stock_packs, committed_packs, non_bev) == (52, 359, 24997)
    caps = {}
    for scenario in run.scenarios:
        arrived = receipts(network, scenario)
        complete = min((network.initial[PROD, item] + sum(
            arrived.get((PROD, item, t), 0) for t in network.periods if t+lead <= network.periods[-1]))//coef
                       for item, coef in arcs[PRODUCTION_ARC].recipes[PACK])
        caps[scenario.name] = stock_packs+committed_packs+complete+non_bev
    rational = Fraction(run.budget)//min(Fraction(cost) for cost in run.costs)
    decimal = Fraction(str(run.budget))//min(Fraction(str(cost)) for cost in run.costs)
    assert rational == decimal
    tolerant = (Fraction(run.budget)+Fraction('1e-9'))//min(Fraction(cost) for cost in run.costs)
    return min(caps.values())+rational, min(caps.values())+tolerant, caps


def remove_one_kit(network, scenario, block, values, buffers):
    """Trace one kit through feasible shipments, then replay all stock balances."""
    inventory, supply, dispatch, service = block[:4]
    periods = network.periods
    arcs = {a.key: a for a in network.arcs}
    t0 = periods[0]
    for key in (PRODUCTION_ARC, TRANSPORT_ARC):
        t = next(t for t in periods if t >= t0 and values[dispatch[(*key, PACK, t)].index] > 0)
        values[dispatch[(*key, PACK, t)].index] -= 1
        t0 = t+arcs[key].lead
    cars = next(a for a in network.arcs if a.origin == OEM and any(g.id in a.recipes for g in network.groups))
    bev = [g.id for g in network.groups if (PACK, 1) in g.representative.bom]
    t, group = next((t, g) for t in periods if t >= t0 for g in bev
                    if values[dispatch[(*cars.key, g, t)].index] > 0)
    values[dispatch[(*cars.key, group, t)].index] -= 1
    delivery = next(t1 for t1 in periods if t1 >= t+cars.lead and values[service[group, t1].index] > 0)
    values[service[group, delivery].index] -= 1
    events = defaultdict(int)
    for arc in network.arcs:
        for t in periods:
            for item, recipe in arc.recipes.items():
                quantity = values[dispatch[(*arc.key, item, t)].index]
                events[arc.destination, item, t+arc.lead] += quantity
                for child, coefficient in recipe:
                    events[arc.origin, child, t] -= coefficient*quantity
    for g in network.groups:
        for t in periods:
            events[g.representative.node, g.id, t] -= values[service[g.id, t].index]
    stock = initial_state(network, buffers)
    arrivals = receipts(network, scenario)
    for t in periods:
        for node, item in stock:
            key = (node, item, t)
            stock[node, item] += arrivals.get(key, 0) + events[key]
            if key in supply:
                stock[node, item] += values[supply[key].index]
            values[inventory[key].index] = stock[node, item]
    return t0, group, delivery


def exact_witness(model, network, run, buffers, blocks, values, solver_floor, upper):
    count_gap = solver_floor-upper
    assert count_gap in (0, 1)
    x = [values[v.index] for v in buffers]
    if count_gap:
        x[0] -= 1
        assert x[0] >= 0
    strict_cost = sum(Fraction(cost)*q for cost, q in zip(run.costs, x))
    decimal_cost = sum(Fraction(str(cost))*q for cost, q in zip(run.costs, x))
    assert max(strict_cost, decimal_cost) <= Fraction(run.budget)
    for var, q in zip(buffers, x):
        values[var.index] = q
    modifications = {}
    deliveries = {}
    for s, block in zip(run.scenarios, blocks):
        if count_gap:
            modifications[s.name] = remove_one_kit(network, s, block, values, x)
        deliveries[s.name] = exact_expr(block[-1], values)
    count = min(deliveries.values())
    assert count == upper
    if run.de:
        rho = model.getVarByName('rho')
        values[rho.index] = Fraction(count, network.demand_weight)
    vars_ = model.getVars()
    assert all(v.LB <= q <= v.UB and (v.VType != GRB.INTEGER or isinstance(q, int))
               for v, q in zip(vars_, values))
    for constraint in model.getConstrs():
        residual = exact_expr(model.getRow(constraint), values)-exact(constraint.RHS)
        valid = residual == 0 if constraint.Sense == '=' else residual <= 0 if constraint.Sense == '<' else residual >= 0
        assert valid, (run.id, constraint.ConstrName, residual)
    # Sparse named exact vector, with rho represented by a rational string if present.
    path = HERE / f'{run.id}__exact_certificate.json.gz'
    with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as raw:
        with io.TextIOWrapper(raw, encoding='utf-8') as stream:
            json.dump({v.VarName: str(q) if isinstance(q, Fraction) else q for v, q in zip(vars_, values) if q},
                      stream, separators=(',', ':'))
    return dict(exact_deliveries=count, exact_service=f'{count}/{network.demand_weight}',
                exact_matrix_objective=str(exact_expr(model.getObjective(), values)), exact_row_residual=0,
                exact_bound_residual=0, exact_integer_residual=0, exact_buffer=x,
                exact_budget_used_binary=str(strict_cost), exact_budget_used_decimal=str(decimal_cost),
                exact_scenario_on_time=deliveries, edits_from_numeric_optimum=modifications,
                exact_certificate_file=path.name, exact_certificate_sha256=digest(path))


def main():
    evidence = json.loads((HERE/'execution.json').read_text(encoding='utf-8'))
    assert not evidence.get('immediate_stop')
    archive = json.loads((FORMAL/'audit.json').read_text(encoding='utf-8'))
    network, _ = compile_network(load_tables(SOURCE))
    runs = {r.id: r for r in frozen_runs(manifest_bytes(FORMAL/'manifest.json'))}
    rows, identity, hashes = [], [], []
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag', 0)
        env.start()
        for name, run in runs.items():
            model, buffers, blocks = build(env, network, run)
            with model:
                for ext in ('lp', 'mps'):
                    path = HERE/'opt_model_identity'/f'{name}.{ext}'
                    actual_hash = digest(path)
                    assert actual_hash == evidence['metadata'][name]['exports'][ext]['sha256']
                    hashes.append(dict(run=name, format=ext, path=path.relative_to(HERE).as_posix(),
                                       sha256=actual_hash, bytes=path.stat().st_size))
                path = HERE/'opt_model_identity'/f'{name}.mps'
                with gp.read(os.path.relpath(path), env=env) as exported:
                    identity.extend(compare(name, model, exported, 'in_memory_vs_exported_mps_reloaded'))
                numeric = next(r for r in evidence['solves'] if r['run'] == name and r['profile'] == 'frozen_opttol')
                assert numeric['status_name'] == 'OPTIMAL' and numeric['mipgap'] <= 1e-9
                assert max(v for k, v in numeric.items() if k.endswith('_residual')) <= 1e-9
                strict_upper, tolerant_upper, scenario_caps = physical_upper(network, run)
                count = round(numeric['delivery_equivalent'])
                assert abs(numeric['delivery_equivalent']-count) <= 1e-8
                assert count == tolerant_upper
                sol = sol_values(HERE/f'{name}__frozen_opttol.sol.gz')
                assert set(sol) == {v.VarName for v in model.getVars()}
                values = [round(float(sol[v.VarName])) if v.VType == GRB.INTEGER else Fraction(sol[v.VarName])
                          for v in model.getVars()]
                x = [values[v.index] for v in buffers]
                spent = sum(Fraction(c)*q for c, q in zip(run.costs, x))
                assert min(exact_expr(b[-1], values) for b in blocks) == count
                assert max(0, spent-Fraction(run.budget)) <= Fraction('1e-9')
                cert = exact_witness(model, network, run, buffers, blocks, values, count, strict_upper)
                rows.append(dict(run=name, archived_count=round(archive['results'][name]['objective']*28000),
                                 numerical_count=count, numerical_solver_status=numeric['status_name'],
                                 numerical_bound=numeric['objbound'], numerical_seconds=numeric['seconds'],
                                 numerical_gap=numeric['mipgap'], numerical_buffer=x,
                                 numerical_exact_budget_excess_usd=float(max(0, spent-Fraction(run.budget))),
                                 strict_material_budget_upper=strict_upper, tolerance_material_budget_upper=tolerant_upper,
                                 zero_buffer_scenario_material_caps=scenario_caps, **cert))
                print('CERT', name, count, cert['exact_deliveries'], flush=True)
    csv_file(HERE/'model_coefficient_diff.csv', evidence['comparison']+identity)
    csv_file(HERE/'model_file_sha256.csv', hashes)
    csv_file(HERE/'all_formal_recertification.csv', rows)
    new_logs = sorted(HERE.glob('*.log'))
    with ZipFile(HERE/'gurobi_logs.zip', 'w', compression=ZIP_DEFLATED) as z:
        for p in new_logs:
            z.write(p, p.name)
    identity_chain = {}
    for name, run in runs.items():
        old = archive['results'][name]
        config = next(r for r in archive['matrix'] if r['id'] == name)
        assert (config['budget_usd'], tuple(config['costs']), config['scenarios']) == (
            run.budget, run.costs, [s.name for s in run.scenarios])
        text = (FORMAL/f'{name}.log').read_text(encoding='utf-8')
        val, bound = re.findall(r'Best objective (\S+), best bound (\S+), gap', text)[-1]
        assert abs(float(val)-old['objective']) < 1e-11 and abs(float(bound)-old['bound']) < 1e-11
        identity_chain[name] = dict(budget=config['budget_usd'], scenarios=config['scenarios'],
                                    solution_file=old['solution_artifact'], solution_sha256=old['solution_sha256'],
                                    historical_log_sha256=digest(FORMAL/f'{name}.log'),
                                    historical_log_objval=val, historical_log_objbound=bound,
                                    result_objval=old['objective'], result_objbound=old['bound'])
    tests = (HERE/'pytest_verified.txt').read_text(encoding='utf-8')
    passed = int(re.findall(r'(\d+) passed in', tests)[-1])
    test_exit_code = int((HERE/'pytest_verified_exit_code.txt').read_text(encoding='utf-8-sig').strip())
    assert test_exit_code == 0 and passed == 119
    audit = dict(status='PASS_ROOT_CAUSE_FIXED_AND_ALL_FORMAL_RUNS_RECERTIFIED',
                 historical_artifacts_modified=False, original_model_modified=False,
                 git_sha=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                 python=platform.python_version(), gurobi=list(gp.gurobi.version()),
                 root_cause='Operationally isolated to LP dual optimality tolerance: with identical matrix and no start, '
                 'tightening only OptimalityTol from 1e-6 to 1e-9 removes the incorrect low bounds. '
                 'The solver-internal step was not instrumented.',
                 operational_control_profile='frozen_opttol; no time/solution/objective limits; no callback; no starts',
                 original_archive_has_lp_or_mps=False,
                 original_archive_comparison_scope='old entrypoint captured at optimize call vs new build; original export unavailable',
                 all_formal_recertification=rows, model_files=hashes, metadata=evidence['metadata'],
                 coefficient_diffs=evidence['comparison']+identity, objectives=evidence['objectives'],
                 solver_runs=evidence['solves'], archive_identity=identity_chain,
                 identity_chain_findings=dict(new_run_directory_required=True, per_run_filename_and_hash_match=True,
                     cache_read_on_formal_execution=False, same_model_object_for_optimizer_and_attributes=True,
                     objval_and_objbound_match_solver_log=True, maximize_incumbent_is_lower_bound=True,
                     maximize_solver_bound_is_upper_bound=True, delivery_rounding_used_for_certification=False),
                 exact_budget_policy='preserve literal frozen cost; exact proof checks the matrix binary64 coefficients '
                     'as rationals and the manifest shortest decimal costs; solver-tolerance outcomes are separate',
                 regression_tests=dict(passed=passed, failed=0, exit_code=test_exit_code, added_cases=13,
                     first_run='118 passed, 1 setup error in default pytest temporary directory',
                     rerun='python -m pytest -vv --basetemp <fresh scratch path>',
                     witness_fixture=str(WITNESSES.relative_to(ROOT)), witness_fixture_sha256=digest(WITNESSES)),
                 full_solver_logs_archive='gurobi_logs.zip', full_solver_logs_archive_sha256=digest(HERE/'gurobi_logs.zip'),
                 input_sha256={str(p): digest(p) for p in [SOURCE, WITNESSES, FORMAL/'audit.json', FORMAL/'manifest.json',
                     *sorted(FORMAL.glob('*_solution.json.gz')), ROOT/'src/prefab_v25/model.py', ROOT/'src/prefab_v25/formal.py',
                     ROOT/'src/prefab_v25/source.py', ROOT/'src/prefab_v25/data.py',
                     ROOT/'examples/run_v25_formal.py', ROOT/'tests/test_v25_formal_witness_regression.py']},
                 output_sha256={p.name: digest(p) for p in sorted(HERE.iterdir())
                                if p.is_file() and p.name != 'audit.json'})
    save_json(HERE/'audit.json', audit)


if __name__ == '__main__':
    main()
