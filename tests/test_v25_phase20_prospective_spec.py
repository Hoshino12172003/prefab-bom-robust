"""Phase 2.0 frozen-data and witness checks without importing a solver."""
import csv
import gzip
import json
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'artifacts' / 'v25_phase20_20261110_203851'


def rows(name):
    with (EVIDENCE / name).open(newline='', encoding='utf-8-sig') as file:
        return list(csv.DictReader(file))


@pytest.fixture(scope='module')
def spec():
    return json.loads((EVIDENCE / 'prospective_manifest.json').read_text(encoding='utf-8'))


def test_source_vins_and_both_configurations(spec):
    orders = rows('bev_orders.csv')
    digest = sha256((EVIDENCE / 'bev_orders.csv').read_bytes()).hexdigest()
    assert digest == 'dcdd1be6e7c5d4441b5a8c48d7e9708c04998961bf6032aeba6fcb9b29501242'
    assert len(orders) == len({o['vin'] for o in orders}) == spec['metric_denominator'] == 3003
    assert Counter(o['configuration'] for o in orders) == {
        'BEV/D83/G1Z/Q4H': 2436, 'BEV/D83/G1Z/Q2J': 567,
    }
    assert all(o['quantity'] == '1' and o['due_node'] == 'zp8' and
               json.loads(o['bom']) == dict.fromkeys(o['configuration'].split('/'), 1) for o in orders)


def test_reveal_and_original_due_days(spec):
    due = Counter(int(o['period']) for o in rows('bev_orders.csv'))
    assert [due[t] for t in range(1, 15)] == [52, 293, 159, 709, 76, 64, 384, 59, 275, 182, 68, 274, 357, 51]
    assert all(int(o['period']) == int(o['source_due']) - 60 for o in rows('bev_orders.csv'))
    assert spec['reveal'] == 0
    assert spec['period_map'] == {str(t): t - 60 for t in range(61, 75)}
    assert spec['secondary_full_network_service'] is None


def test_battery_shared_calendar_leads_and_bom(spec):
    upstream, production, transport = spec['battery_chain']
    assert [(a['origin'], a['destination'], a['lead']) for a in spec['battery_chain']] == [
        ('battery-supplier_trans', 'battery-supplier_prod', 20),
        ('battery-supplier_prod', 'battery-supplier_inv', 1),
        ('battery-supplier_inv', 'zp7', 1),
    ]
    assert upstream['capacity'] == {str(t): 2058 if t in (7, 14) else 0 for t in range(1, 15)}
    assert production['capacity'] == transport['capacity'] == {str(t): 294 for t in range(1, 15)}
    assert spec['source_battery_sku'] == 'BEV'
    assert spec['source_battery_bom'] == {f'componment_battery{i}': q for i, q in enumerate((10, 6, 4), 1)}


def test_rsp_c_is_unique_and_excludes_historical_battery(spec):
    protocols = rows('regular_supply_protocol_audit.csv')
    assert [p['protocol'] for p in protocols] == ['RSP-A', 'RSP-B', 'RSP-C']
    assert [p['protocol'] for p in protocols if p['selected'] == 'True'] == [spec['protocol']] == ['RSP-C']
    assert spec['protocol_class'] == 'MODEL_ADAPTATION'
    assert spec['source_battery_planned_flow_rows'] == 0
    assert spec['first_eligible_battery_timing'] == {'dispatch': 7, 't1_component': 27, 'oem_pack': 29}
    assert spec['regular_battery_ledger_credit'] == 0
    assert not spec['historical_battery_stock_or_flows_adopted']
    state = [r for r in rows('prospective_instance_parameter_provenance.csv')
             if r['parameter'] in ('opening_stock', 'pre_window_dispatch') and 'battery' in r['key']]
    assert state and {r['role'] for r in state} == {'EXCLUDED_HISTORICAL_BATTERY_STATE'}


def test_all_buffer_locations_remain_endogenous(spec):
    assert spec['buffers'] == {x: {'domain': 'Z_nonnegative', 'required_positive': False}
                               for x in ('x_C', 'x_T', 'x_O')}
    assert not spec['forced_mix']
    semantics = {r['variable']: r for r in rows('buffer_variable_semantics.csv')}
    assert semantics['x_C']['opening_endowment'] == '10/6/4 dedicated component units'
    assert [semantics[x]['risk_exposure'] for x in ('x_C', 'x_T', 'x_O')] == [
        'L1,L2,L3', 'L3', 'none of L1,L2,L3',
    ]
    assert all(value is None for value in spec['cost_parameters'].values())
    assert spec['managerial_gate'] == 'HOLD_FINAL_POSITION_COST_CALIBRATION'


def test_risk_targets_and_l1_integer_release_conservation(spec):
    risks = rows('risk_layer_semantics.csv')
    assert [r['layer'] for r in risks] == ['L1', 'L2', 'L3']
    assert {r['numeric_profile'] for r in risks} == {'UNSET'}
    assert risks[0]['evidence_class'] == 'EXPLICIT_SCENARIO_ASSUMPTION'
    assert spec['risk_schema']['numeric_parameters'] is None
    # Synthetic values check accounting only and are not prospective scenarios.
    for kits in range(8):
        previous = 0
        released = Counter()
        for factor in (Fraction(0), Fraction(1, 3), Fraction(2, 3), Fraction(1)):
            k = int(factor * kits)
            n, d = factor.numerator, factor.denominator
            assert [v for v in range(kits + 1) if d*v <= n*kits <= d*v+d-1] == [k]
            for i, units in enumerate((10, 6, 4)):
                released[i] += units * (k - previous)
                assert released[i] + units * (kits - k) == units * kits
            previous = k


@pytest.mark.parametrize(('scope', 'order_count'), [('BEV3003', 3003), ('FULL28000', 28000)])
def test_nonbattery_witness_balances_and_shared_capacities(scope, order_count, spec):
    provenance = rows('prospective_instance_parameter_provenance.csv')
    background = [r for r in provenance if r['role'] == 'NON_BATTERY_BACKGROUND_ONLY']
    leads = {tuple(r['key'].split('/')): int(r['value']) for r in background if r['parameter'] == 'lead'}
    assert len(leads) == 7 and spec['retained_non_battery']
    caps = {(*r['key'].split('/'), int(r['source_period'])): int(r['value'])
            for r in background if r['parameter'] == 'arc_capacity'}
    limits = {(*r['key'].split('/'), int(r['source_period'])): int(r['value'])
              for r in background if r['parameter'] in ('group_flow_ceiling', 'product_flow_ceiling')}
    recipes = {}
    for r in background:
        if r['parameter'] == 'recipe':
            origin, dest, output, child = r['key'].split('/')
            recipes.setdefault((origin, dest, output), []).append((child, int(r['value'])))
    state = Counter({tuple(r['key'].split('/')): int(r['value'])
                     for r in background if r['parameter'] == 'opening_stock'})
    eligible = {tuple(r['key'].split('/')) for r in background if r['parameter'] == 'external_eligibility'}
    bounds = {tuple(r['key'].split('/')): tuple(map(int, r['value'].split('..')))
              for r in provenance if r['parameter'] == 'end_period_stock_bounds'}
    requirements = [r for r in rows('diagnostic_due_requirements.csv') if r['scope'] == scope]
    due_vehicles = {int(r['source_period']): int(r['quantity'])
                    for r in requirements if r['item'] == 'VEHICLE_TOTAL'}
    assert sum(due_vehicles.values()) == order_count
    assert all(q <= 2000 for q in due_vehicles.values())
    net = Counter()
    for r in background:
        if r['parameter'] == 'pre_window_dispatch':
            origin, dest, item = r['key'].split('/')
            net[dest, item, int(r['source_period']) + leads[origin, dest]] += int(r['value'])
    with gzip.open(EVIDENCE / f'{scope}_witness.json.gz', 'rt', encoding='utf-8') as file:
        witness = {kind: {tuple(k): q for k, q in entries} for kind, entries in json.load(file).items()}
    assert all(type(q) is int and q > 0 for vals in witness.values() for q in vals.values())
    totals = Counter()
    keys = {(origin, child) for (origin, _, _), children in recipes.items() for child, _ in children}
    keys.update((dest, product) for _, dest, product in recipes)
    for (origin, dest, item, t), q in witness['dispatch'].items():
        assert 61 <= t <= 74
        totals[origin, dest, t] += q
        assert q <= limits.get((origin, dest, item, t), q)
        for child, units in recipes[origin, dest, item]:
            net[origin, child, t] -= units * q
        net[dest, item, t + leads[origin, dest]] += q
    assert all(q <= min(caps[k], limits.get(k, caps[k])) for k, q in totals.items())
    for (node, item, t), q in witness['supply'].items():
        assert (node, item) in eligible & keys and 61 <= t <= 74
        net[node, item, t] += q
    for r in requirements:
        if r['item'] != 'VEHICLE_TOTAL':
            assert (r['node'], r['item']) in keys
            net[r['node'], r['item'], int(r['source_period'])] -= int(r['quantity'])
    for t in range(61, 75):
        for node, item in keys:
            state[node, item] += net[node, item, t]
            lo, hi = bounds.get((node, item), (0, float('inf')))
            assert lo <= state[node, item] == witness['inventory'].get((node, item, t), 0) <= hi


def test_phase_scope_and_prior_statuses(spec):
    audit = json.loads((EVIDENCE / 'audit.json').read_text(encoding='utf-8'))
    assert audit['status'] == spec['status'] == 'PASS_PROSPECTIVE_INSTANCE_SPEC_FROZEN'
    assert audit['structural_optimizer_calls'] == 2
    assert all(row['label'] == 'STRUCTURAL_DIAGNOSTIC_ONLY' for row in audit['diagnostics'])
    assert all(row['max_solver_residual'] == row['exact_material_residual'] == 0 for row in audit['diagnostics'])
    assert audit['formal_optimizer_calls'] == audit['algorithm_optimizer_calls'] == audit['reliability_tests_executed'] == 0
    assert audit['clean_baseline'] == 'SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED'
    assert audit['retained_states'] == {
        '1.6': 'PASS_ROOT_CAUSE_FIXED_AND_ALL_FORMAL_RUNS_RECERTIFIED',
        '1.7': 'HOLD_SHORTAGE_UNIT_UNIDENTIFIED',
        '1.10': 'PASS_WITH_EXPLICIT_MODEL_ADAPTATIONS',
    }
    assert all(row['checked'] and row['mismatches'] == 0 for row in audit['protected_files'].values())
