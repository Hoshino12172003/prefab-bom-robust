"""Replay evidence and check the exact parametric audit against brute force."""
import csv
import importlib.util
import itertools
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts' / 'v25_phase21_20261110_212532'


def rows(name):
    with (ART / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def modules():
    imported = []
    for name in ('frontier', 'portfolio_expirations'):
        spec = importlib.util.spec_from_file_location(name, ART / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        imported.append(module)
    yield imported
    for module in imported:
        del sys.modules[module.__name__]


def test_cost_and_budget_evidence(modules):
    f, _ = modules
    evidence = {r['id']: r for r in rows('battery_cost_ratio_evidence.csv')}
    anchor = evidence['BATPAC50_EV']
    assert Fraction(anchor['pack_cost']) / Fraction(anchor['cell_cost']) == f.RATIO == Fraction(27, 19)
    reported = [Fraction(r['ratio_exact']) for k, r in evidence.items() if 'BATPAC40' in k]
    assert (min(reported), max(reported)) == f.RATIO_BOUNDS
    assert f.SCALES == {1: 215, 3: 644, 5: 1073}
    oem = next(r for r in rows('position_cost_evidence.csv') if r['id'] == 'OEM_DELTA')
    assert oem['quantity'] == '' and oem['evidence_role'] == 'ENDOGENOUS_BREAK_EVEN'


def test_release_and_independent_nominal_flow(modules):
    f, _ = modules
    assert f.no_oem_service('L1', 215, 0) == 107
    assert f.no_oem_service('L2', 1073, 0) == 854
    assert f.no_oem_service('L3', 0, 1073) == 927
    assert all(f.capacity(risk, stage, t) == 73 for risk, stage in (('L2', 1), ('L3', 2))
               for t in f.PERIODS)
    evidence = {r['id']: r for r in rows('risk_parameter_evidence.csv')}
    for risk, stage in (('L1', 0), ('L2', 1), ('L3', 2)):
        assert Fraction(evidence[risk]['remaining_factor']) == f.RISKS[risk][stage]
        assert evidence[risk]['evidence_level'] == 'EXPERIMENTAL_STRESS_TEST'


def test_exact_events_and_portfolio_exits_against_brute_force(modules, monkeypatch):
    f, p = modules
    monkeypatch.setattr(f, 'DEMAND', (3, 1, 3, 1, 2))
    monkeypatch.setattr(f, 'TOTAL', 10)
    monkeypatch.setattr(f, 'capacity', lambda risk, stage, t: 1)
    ratio, k = Fraction(3, 2), 7
    budget = k * ratio
    frontier = f.Frontier('NOM', k, ratio)
    portfolios = []
    for c, t1, o in itertools.product(range(int(budget) + 1), range(k + 1), range(k + 1)):
        spend = c + ratio * (t1 + o)
        if spend > budget:
            continue
        # Simulate daily arrivals and consume at each due day without the prefix-deficit formula.
        kits, t1_stock, available = c, t1, o
        delivered = production_in_transit = shipment_in_transit = 0
        for demand in f.DEMAND:
            t1_stock += production_in_transit
            available += shipment_in_transit
            service = min(available, demand)
            delivered += service
            available -= service
            shipment_in_transit = min(1, t1_stock)
            t1_stock -= shipment_in_transit
            production_in_transit = min(1, kits)
            kits -= production_in_transit
        kind = f.SUPPORT[int(c > 0) + 2*int(t1 > 0) + 4*int(o > 0)]
        premium = (budget-spend)/(ratio*o) if o else float('inf')
        portfolios.append((premium, delivered, kind, (c, t1, o)))
    points = sorted({Fraction(0), *(a for a, _, _, _ in portfolios if a != float('inf'))})
    expected, exits = [], Counter()
    for point in points:
        z = max(b for a, b, _, _ in portfolios if a >= point)
        right = max(b for a, b, _, _ in portfolios if a > point)
        at_kind = {kind for a, b, kind, _ in portfolios if a >= point and b == z}
        right_kind = {kind for a, b, kind, _ in portfolios if a > point and b == right}
        if point == 0 or z != right or at_kind != right_kind:
            expected.append((point, z, right, at_kind, right_kind))
        for limit, count, _, _ in portfolios:
            if limit == point and count == z:
                exits[z, point] += 1
    actual = frontier.events()
    assert [(Fraction(r['premium_exact']), r['z_at'], r['z_right'],
             set(r['supports_at'].split('|')), set(r['supports_right'].split('|'))) for r in actual] == expected
    exit_actual = Counter()
    left, inclusive = Fraction(0), True
    for right, z in [(a, z) for a, z, after, *_ in expected if z != after] + [(None, expected[-1][2])]:
        for point, count in p.expirations(frontier, z, left, inclusive):
            exit_actual[z, point] += count
        left, inclusive = right, False
    assert exit_actual == exits


@pytest.mark.parametrize(('table', 'count'), [
    ('single_buffer_capability.csv', 12), ('equal_cost_dominance.csv', 12),
    ('risk_location_policy_response.csv', 24), ('optimal_policy_set_ranges.csv', 72),
    ('near_optimal_policy_ranges.csv', 216), ('threshold_direct_checks.csv', 3),
])
def test_direct_certificates_and_logs(table, count):
    results = rows(table)
    assert len(results) == count
    for r in results:
        assert r['label'] == 'STRUCTURAL_DIAGNOSTIC_ONLY'
        assert r['status'] == 'OPTIMAL' and r['exact_crosscheck'] == 'MATCH'
        assert float(r['objective']) == float(r['best_bound'])
        assert float(r['mip_gap']) == float(r['integer_ledger_residual']) == 0
        assert float(r['residual']) <= 1e-7
        assert Fraction(r['spend']) <= Fraction(r['budget'])
        log = (ART / r['log']).read_text(encoding='utf-8')
        assert r['run'] in log and re.search(r'^Optimal solution found', log, re.MULTILINE)


def test_phase21_critical_result_rows():
    rows_by_name = {r['run']: r for r in rows('risk_location_policy_response.csv')}
    expected = dict(NOM=1524, L1=1073, L2=1326, L3=1325)
    assert {risk: int(rows_by_name[f'P5_{risk}_K5_PROBE']['z']) for risk in expected} == expected
    assert {r['all_optima_OEM_only'] for r in rows('equal_cost_dominance.csv')} == {'False'}
    endpoints = {r['run']: r for r in rows('near_optimal_policy_ranges.csv')}
    oem = endpoints['P7_L1_COST_PROBE_1000_x_O_max']
    assert (oem['z_star'], oem['target'], oem['objective']) == ('1073', '1072', '871')
    summary = json.loads((ART/'run_summary.json').read_text(encoding='utf-8'))
    assert summary['formal_managerial_runs'] == summary['algorithm_runs'] == 0
    assert len(list((ART/'logs').glob('*.log'))) == summary['diagnostic_runs'] == 352
