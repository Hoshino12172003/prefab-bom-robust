"""Export the frozen Phase 2.0 specification and trace its source rows."""
import hashlib
import csv
import json
import platform
import subprocess
from pathlib import Path
from zipfile import ZipFile

from non_battery_diagnostic import (
    ASSEMBLY, BATTERY_ARCS, BATTERY_ITEMS, CELL, COMPONENT_ARC, HERE, OEM, PACK,
    PRODUCTION_ARC, ROOT, SOURCE, TRANSPORT_ARC, compile_network, due_requirements,
    load_tables, write,
)

STATUS = 'PASS_PROSPECTIVE_INSTANCE_SPEC_FROZEN'
PAPER = Path('external_inputs/Optimisation model for multi-item multi-echelon supply chain.pdf')
REQUEST = Path('private_inputs/attachment/已粘贴的文本.txt')
SOURCE_URL = 'https://data.mendeley.com/datasets/pr3sdy5vp3/1'
PAPER_DOI = '10.1016/j.ejor.2020.08.005'
PHASES = {
    '1.6': 'v25_phase16_20261110_160104',
    '1.7': 'v25_phase17_20261110_163116',
    '1.10': 'v25_phase110_20261110_201422',
}
DOCS = (
    'v25_phase20_prospective_instance_spec.md',
    'v25_phase20_regular_supply_protocol_audit.md',
    'v25_phase20_endogenous_buffer_definition.md',
    'endogenous_buffer_policy_reliability_protocol.md',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def source_exports(tables, network):
    orders = [o for group in network.groups for o in group.orders if (PACK, 1) in o.bom]
    configurations = {}
    due = {t: 0 for t in range(1, 15)}
    rows = []
    for order in sorted(orders, key=lambda order: order.vin):
        config = '/'.join(item for item, _ in order.bom)
        configurations[config] = configurations.get(config, 0) + 1
        due[order.due - 60] += 1
        rows.append(dict(vin=order.vin, due_node=order.node, source_due=order.due,
                         period=order.due - 60, quantity=1, configuration=config,
                         bom=json.dumps(dict(order.bom), separators=(',', ':'))))
    write(HERE / 'bev_orders.csv', rows)

    provenance = []

    def record(parameter, key, value, unit, source, role, source_period='', period=''):
        provenance.append(dict(parameter=parameter, key=key, value=value, unit=unit,
                               source=source, role=role, source_period=source_period, period=period))

    for row in rows:
        record('BEV_order', row['vin'], row['bom'], 'one vehicle', 'XLSB demands + BOM',
               'PRIMARY_UNCHANGED_VIN', row['source_due'], row['period'])
    for arc in network.arcs:
        key = '/'.join(arc.key)
        role = 'BATTERY_PHYSICAL' if arc.key in BATTERY_ARCS else (
            'SHARED_OEM_PHYSICAL' if arc.key == ASSEMBLY else 'NON_BATTERY_BACKGROUND_ONLY')
        record('lead', key, arc.lead, 'periods', 'XLSB arcs', role)
        for t, value in sorted(arc.capacity.items()):
            unit = ('component output units' if arc.key == COMPONENT_ARC else
                    'pack output units' if arc.key in BATTERY_ARCS else 'arc output units')
            record('arc_capacity', key, value, unit, 'XLSB capacity_at_arc', role, t, t - 60)
        if arc.key != ASSEMBLY:
            for item, recipe in arc.recipes.items():
                for child, quantity in recipe:
                    record('recipe', f'{key}/{item}/{child}', quantity, 'input per output',
                           'XLSB operations + BOM', role)
    for (origin, dest, item, t), quantity in network.product_caps.items():
        record('product_flow_ceiling', '/'.join((origin, dest, item)), quantity, 'arc output units',
               'XLSB max_flow_product_per_arc', 'NON_BATTERY_BACKGROUND_ONLY', t, t - 60)
    for (origin, dest, t), quantity in network.group_caps.items():
        record('group_flow_ceiling', '/'.join((origin, dest)), quantity, 'arc output units',
               'XLSB max_flow_group_per_arc', 'NON_BATTERY_BACKGROUND_ONLY', t, t - 60)
    for node, item, quantity, lo, hi, t in tables['initial_inventories']:
        role = 'EXCLUDED_HISTORICAL_BATTERY_STATE' if item in BATTERY_ITEMS else 'NON_BATTERY_BACKGROUND_ONLY'
        record('opening_stock', f'{node}/{item}', int(quantity), 'item units', 'XLSB initial_inventories', role, t)
        record('end_period_stock_bounds', f'{node}/{item}', f'{int(lo)}..{int(hi)}', 'item units',
               'XLSB initial_inventories', 'RETAINED_BOUND_NOT_ENDOWMENT', t)
    for origin, dest, item, t, quantity in network.historical:
        role = 'EXCLUDED_HISTORICAL_BATTERY_STATE' if item in BATTERY_ITEMS else 'NON_BATTERY_BACKGROUND_ONLY'
        record('pre_window_dispatch', '/'.join((origin, dest, item)), quantity, 'item units',
               'XLSB initial_flows', role, t)
    for node, item in network.external:
        role = 'BATTERY_ELIGIBILITY_ONLY_NO_REGULAR_CREDIT' if item in BATTERY_ITEMS else 'NON_BATTERY_BACKGROUND_ONLY'
        record('external_eligibility', f'{node}/{item}', 1, 'eligibility flag', 'XLSB nodes_inflow', role)
    for parameter, value, unit, role in (
        ('time_reveal', 0, 'experiment periods', 'MODEL_ADAPTATION'),
        ('primary_denominator', len(orders), 'VINs', 'PRIMARY_UNCHANGED_VIN'),
        ('full_network_service', '', 'rate', 'NOT_COMPUTED'),
        ('adopted_protocol', 'RSP-C', 'label', 'MODEL_ADAPTATION'),
        ('regular_battery_in_scope', 0, 'ledger credit', 'MODEL_ADAPTATION_NOT_HISTORICAL_ZERO'),
        ('source_shortage_quantity', '', 'not used', 'EXCLUDED_HISTORICAL_BATTERY_STATE'),
        ('L1_L2_L3_final_profiles', '', 'fractions', 'UNSET'),
        ('c_C_c_T_c_O_B', '', 'currency units', 'UNSET'),
    ):
        record(parameter, 'main', value, unit, 'Phase 2.0 protocol decision', role)
    write(HERE / 'prospective_instance_parameter_provenance.csv', provenance)
    return configurations, due


def decisions():
    write(HERE / 'regular_supply_protocol_audit.csv', [
        dict(protocol='RSP-A', selected=False, evidence='0 battery product/group planned-flow rows; capacity is an upper bound',
             timing='No eligible nonhistorical committed battery receipts', historic_dependency='Would require excluded battery state or a new assumption',
             ledger_separation='Possible in principle; no supported quantities', research_scope='Unavailable', decision='REJECT_SOURCE_EVIDENCE'),
        dict(protocol='RSP-B', selected=False, evidence='Regular u can be modeled independently; no supported pre-window pipeline',
             timing='First positive dispatch day 7, producer day 27, OEM day 29', historic_dependency='Would require unsupported opening pipeline for positive timely regular supply',
             ledger_separation='Separate operating account for u and budget for x', research_scope='No positive timely regular battery plan under evidence', decision='REJECT_TIMING'),
        dict(protocol='RSP-C', selected=True, evidence='Use source physical network and original 3003 BEV VINs',
             timing='Dedicated positions acquired before reveal; processing follows original leads', historic_dependency='None in battery ledger; nonbattery background explicitly conditioned on source',
             ledger_separation='No regular battery stock or receipts credited; nonbattery background separate', research_scope='RQ1 protection value; RQ2 layer response; RQ3 policy stability',
             decision='MODEL_ADAPTATION_PROTECTIVE_COVERAGE'),
    ])
    write(HERE / 'risk_layer_semantics.csv', [
        dict(layer='L1', target='dedicated component kit lot at T1 production', mechanism='quality/usability clearance',
             schema='gamma_avail[t]=rational in [0,1], nondecreasing; K[t]=floor(gamma_avail[t]*x_C)',
             applies_to='x_C usable component release only', unaffected='x_T;x_O;production and transport capacities',
             numeric_profile='UNSET', evidence_class='EXPLICIT_SCENARIO_ASSUMPTION'),
        dict(layer='L2', target='T1 Pack production arc', mechanism='shared production capacity RHS',
             schema='gamma_prod[t]=rational in [0,1]; RHS=gamma_prod[t]*source_prod_cap[t]',
             applies_to='new pack production from released components', unaffected='precompleted x_T and x_O;lead times',
             numeric_profile='UNSET', evidence_class='SOURCE_ARC_EXPERIMENTAL_RISK'),
        dict(layer='L3', target='T1 to OEM Pack transport arc', mechanism='shared transport capacity RHS',
             schema='gamma_trans[t]=rational in [0,1]; RHS=gamma_trans[t]*source_trans_cap[t]',
             applies_to='T1 completed Pack shipments including x_T and new packs', unaffected='x_O;lead times',
             numeric_profile='UNSET', evidence_class='SOURCE_ARC_EXPERIMENTAL_RISK'),
    ])
    write(HERE / 'buffer_variable_semantics.csv', [
        dict(variable='x_C', domain='Z_nonnegative', physical_name='balanced battery-component kit-equivalent buffer at T1 production node',
             opening_endowment='10/6/4 dedicated component units', pathway='release then produce then transport then assemble', risk_exposure='L1,L2,L3', cost='c_C'),
        dict(variable='x_T', domain='Z_nonnegative', physical_name='completed BEV Pack buffer at T1 inventory node',
             opening_endowment='1 dedicated BEV Pack', pathway='transport then assemble', risk_exposure='L3', cost='c_T'),
        dict(variable='x_O', domain='Z_nonnegative', physical_name='completed BEV Pack buffer at OEM assembly-side inventory',
             opening_endowment='1 dedicated BEV Pack', pathway='assemble', risk_exposure='none of L1,L2,L3', cost='c_O'),
    ])


def diagnostic_export():
    cases = json.loads((HERE / 'non_battery_diagnostic.json').read_text(encoding='utf-8'))
    if [case['scope'] for case in cases] != ['BEV3003', 'FULL28000'] or not all(
        case['label'] == 'STRUCTURAL_DIAGNOSTIC_ONLY' and case['status'] == 2
        and case['fixed_due_withdrawals_feasible'] and case['exact_material_residual'] == 0
        and case['max_solver_residual'] == 0 for case in cases
    ):
        raise ValueError('nonbattery feasibility gate failed')
    rows = []
    for case in cases:
        with (HERE / f"{case['scope']}_selected_parts_ledger.csv").open(encoding='utf-8-sig') as file:
            ledger = list(csv.DictReader(file))
        for item in ('D83', 'G1Z', 'Q2J', 'Q4H'):
            entries = [row for row in ledger if row['item'] == item]
            rows.append(dict(**case, item=item, due_withdrawals=sum(int(r['withdrawal']) for r in entries),
                             min_oem_closing=min(int(r['closing']) for r in entries),
                             zero_closing_periods=sum(int(r['closing']) == 0 for r in entries),
                             inference='JIT withdrawals feasible under source nonbattery background; not a service solve'))
    write(HERE / 'non_battery_binding_audit.csv', rows)
    return cases


def diagnostic_requirements(network):
    bev = tuple(g for g in network.groups if (PACK, 1) in g.representative.bom)
    rows = []
    for scope, groups in (('BEV3003', bev), ('FULL28000', network.groups)):
        withdrawals, vehicles = due_requirements(groups)
        for (node, item, period), units in sorted(withdrawals.items()):
            rows.append(dict(scope=scope, node=node, item=item, source_period=period, quantity=units))
        for period, units in sorted(vehicles.items()):
            rows.append(dict(scope=scope, node=OEM, item='VEHICLE_TOTAL', source_period=period, quantity=units))
    write(HERE / 'diagnostic_due_requirements.csv', rows)


def protected_inputs():
    paths = {phase: ROOT / 'artifacts' / folder / 'audit.json' for phase, folder in PHASES.items()}
    history = {phase: json.loads(path.read_text(encoding='utf-8-sig')) for phase, path in paths.items()}
    inputs = history['1.10']['input_sha256']
    compiler = {p: h for p, h in inputs.items() if Path(p).suffix == '.py'}
    protected = {}
    for group, entries in (
        ('phase110_archives', history['1.10']['protected_archive_sha256']),
        ('phase110_outputs', history['1.10']['output_sha256']),
        ('model_and_runner', compiler),
    ):
        failures = [p for p, h in entries.items() if not Path(p).is_file() or digest(Path(p)) != h]
        if failures:
            raise ValueError(f'protected files changed in {group}: {failures}')
        protected[group] = {'checked': len(entries), 'mismatches': 0}
    input_hashes = {str(p): digest(p) for p in (SOURCE, PAPER, REQUEST, *paths.values())}
    with ZipFile(SOURCE) as archive:
        member = next(n for n in archive.namelist() if n.endswith('.xlsb'))
        input_hashes[f'{SOURCE}::{member}'] = hashlib.sha256(archive.read(member)).hexdigest()
    return {k: v['status'] for k, v in history.items()}, protected, input_hashes | compiler


def main():
    tables = load_tables(SOURCE)
    network, source_audit = compile_network(tables)
    configurations, due = source_exports(tables, network)
    decisions()
    cases = diagnostic_export()
    diagnostic_requirements(network)
    states, protected, inputs = protected_inputs()
    arcs = {arc.key: arc for arc in network.arcs}
    upstream, prod, trans = (arcs[k] for k in (COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC))
    first_dispatch = min(t - 60 for t, cap in upstream.capacity.items() if cap > 0)
    git = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    spec = dict(status=STATUS, git_sha=git, instance='source-calibrated prospective planning instance',
                source_dataset=SOURCE_URL, source_paper_doi=PAPER_DOI,
                reveal=0, period_map={t: t - 60 for t in network.periods}, vin_count=3003,
                metric='BEV on-time fulfillment rate', configurations=configurations, due_counts=due,
                metric_denominator=3003, secondary_full_network_service=None, source_battery_sku=PACK,
                source_battery_bom=dict(prod.recipes[PACK]),
                battery_chain=[dict(origin=a.origin, destination=a.destination, lead=a.lead,
                                    capacity={t-60: c for t, c in a.capacity.items()})
                               for a in (upstream, prod, trans)],
                first_eligible_battery_timing=dict(dispatch=first_dispatch, t1_component=first_dispatch+upstream.lead,
                                                   oem_pack=first_dispatch+upstream.lead+prod.lead+trans.lead),
                source_battery_planned_flow_rows=sum((i, j) in BATTERY_ARCS for i, j, *_ in
                                                    (*network.product_caps, *network.group_caps)),
                retained_non_battery=True, protocol='RSP-C', protocol_class='MODEL_ADAPTATION',
                regular_battery_ledger_credit=0, historical_battery_stock_or_flows_adopted=False,
                buffers={x: {'domain': 'Z_nonnegative', 'required_positive': False}
                         for x in ('x_C', 'x_T', 'x_O')}, forced_mix=False,
                risk_schema=dict(L1='cumulative_rational_kit_release', L2='rational_prod_capacity_factor',
                                 L3='rational_transport_capacity_factor', numeric_parameters=None),
                cost_parameters=dict(c_C=None, c_T=None, c_O=None, delta_O=None, budget=None),
                managerial_gate='HOLD_FINAL_POSITION_COST_CALIBRATION',
                clean_baseline='SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED',
                formal_optimizer_calls=0, algorithm_optimizer_calls=0)
    dump('prospective_manifest.json', spec)
    audit = dict(status=STATUS, git_sha=git, specification='prospective_manifest.json',
                 source_checks=source_audit, diagnostics=cases, structural_optimizer_calls=len(cases),
                 diagnostic_command=f'python {HERE.relative_to(ROOT).as_posix()}/non_battery_diagnostic.py',
                 runtime=dict(python=platform.python_version(), gurobi='13.0.1',
                              diagnostic_exit_code=0, solver_version_evidence='BEV3003.log; FULL28000.log'),
                 formal_optimizer_calls=0, algorithm_optimizer_calls=0, reliability_tests_executed=0,
                 retained_states=states, clean_baseline=spec['clean_baseline'], managerial_gate=spec['managerial_gate'],
                 input_sha256=inputs, protected_files=protected, artifact_checksums='sha256_manifest.csv')
    test_log = HERE / 'pytest_phase20.txt'
    if test_log.exists():
        test_exit = int((HERE / 'pytest_exit_code.txt').read_text())
        if test_exit != 0:
            raise ValueError(f'Phase 2.0 regression tests failed with exit code {test_exit}')
        audit['tests'] = dict(command='python -m pytest -p no:cacheprovider -vv tests/test_v25_phase20_prospective_spec.py',
                              exit_code=test_exit, summary=test_log.read_text(encoding='utf-8-sig').splitlines()[-1].strip('= '),
                              log=test_log.name)
    dump('audit.json', audit)
    files = [p for p in HERE.iterdir() if p.is_file() and p.name != 'sha256_manifest.csv']
    files.extend(ROOT / 'docs' / name for name in DOCS)
    files.append(ROOT / 'tests' / 'test_v25_phase20_prospective_spec.py')
    write(HERE / 'sha256_manifest.csv', [
        dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p)) for p in sorted(files) if p.is_file()
    ])


if __name__ == '__main__':
    main()
