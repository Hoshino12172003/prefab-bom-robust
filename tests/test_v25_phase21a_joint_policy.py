"""Regression evidence for the K5 budget row and exact joint policies."""
import csv
import gzip
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'artifacts/v25_phase21a_20261110_214856'


def read(name):
    with (HERE/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def positive_sets():
    policies = defaultdict(set)
    with gzip.open(HERE/'joint_optimal_policy_set.csv.gz','rt',encoding='utf-8',newline='') as f:
        header = next(f)
        reader = csv.DictReader((line for line in f if ',COST_PROBE,' in line),
                                fieldnames=next(csv.reader([header])))
        for r in reader:
            for oem in range(int(r['x_O_min']),int(r['x_O_max'])+1):
                policies[r['risk']].add((int(r['x_C']),int(r['x_T']),oem))
    return policies


def test_budget_rows_match_legacy_model():
    rows = read('k_budget_semantics_audit.csv')
    assert Counter(r['K_label'] for r in rows) == {'K1':19,'K3':15,'K5':306}
    assert all(r['reconstruction_matches'] == 'True' for r in rows)
    k5 = [r for r in rows if r['K_label']=='K5']
    assert Counter(r['semantics'] for r in k5) == {'K5 quantity cap':103,'K5-derived budget':203}
    for row in k5:
        assert row['cost_budget_row_present']=='True'
        economic = row['semantics']=='K5-derived budget'
        assert (row['quantity_cap_1073']=='False')==economic
        assert Fraction(row['budget_B']) == (Fraction(28971,19) if economic else 1073)
    l2 = next(r for r in k5 if r['run']=='P5_L2_K5_PROBE')
    [[_,sense,coefficients,rhs]] = json.loads(l2['captured_pure_buffer_rows'])
    assert (sense,coefficients,rhs)==('<',[2380434,3382722,3386603],3629660706)
    assert int(l2['archived_buffer_sum']) == 1326
    assert 2380434*854+3382722*440+3386603*32 <= rhs


def test_joint_families_and_full_witnesses(positive_sets):
    assert positive_sets['L1'] == {(0,1073,0)}
    assert positive_sets['L2'] == {(854,472-o,o) for o in range(33)}
    assert positive_sets['L3'] == (
        {(853,472-o,o) for o in range(398,473)} | {(854,471-o,o) for o in range(398,472)}
    )
    assert (854,472,32) not in positive_sets['L2']
    rows = read('joint_optimal_representative_policies.csv')
    assert len(rows)==63 and len({r['run'] for r in rows})==63
    for row in rows:
        assert row['actual_ontime']==row['z_star'] and row['objective']==row['bound']
        assert row['status']=='OPTIMAL' and float(row['residual']) <= 1e-7
        if row['regime']=='COST_PROBE':
            assert tuple(int(row[v]) for v in ('x_C','x_T','x_O')) in positive_sets[row['risk']]


def test_pairwise_coupling_covers_both_directions(positive_sets):
    names = ('x_C','x_T','x_O')
    rows = [r for r in read('joint_policy_coupling.csv') if r['regime']=='COST_PROBE']
    expected = defaultdict(set)
    for risk,policies in positive_sets.items():
        for x in policies:
            for i,name in enumerate(names):
                for j,response in enumerate(names):
                    if i!=j:
                        expected[risk,name,x[i],response].add(x[j])
    assert len(rows)==len(expected)
    for row in rows:
        key = row['risk'],row['fixed_position'],int(row['fixed_value']),row['response_position']
        values = expected.pop(key)
        assert (int(row['minimum']),int(row['maximum']),int(row['feasible_values']))==(
            min(values),max(values),len(values))
        intervals = [tuple(map(int,s.split('-'))) for s in row['exact_integer_intervals'].split('|')]
        assert {v for bounds in intervals for v in range(bounds[0],bounds[-1]+1)}==values
    assert not expected


def test_minimum_cost_frontier_is_exact():
    rows = read('service_cost_policy_frontier.csv')
    assert len(rows)==36
    costs = defaultdict(dict)
    for row in rows:
        x = tuple(int(row[v]) for v in ('x_C','x_T','x_O'))
        r,d = Fraction(row['ratio']),Fraction(row['premium'])
        cost = x[0]+r*(x[1]+(1+d)*x[2])
        assert cost==Fraction(row['protection_cost'])==Fraction(int(row['bound']),int(row['obj_scale']))
        assert int(row['actual_ontime'])>=int(row['service_target'])
        if row['regime']=='COST_PROBE':
            costs[row['risk']][int(row['service_loss_allowance'])]=cost
    for risk in ('L1','L2','L3'):
        marginal = Fraction(27,19) if risk!='L3' else Fraction(3386603,2380434)
        assert all(costs[risk][0]-costs[risk][loss]==loss*marginal for loss in (1,2,5))


def test_breakpoint_not_invariant_to_budget_units():
    events = {(r['risk'],r['budget_multiplier'],r['threshold_type']):r
              for r in read('breakpoint_granularity_audit.csv')}
    for event, expected in (
        ('first_policy_composition_breakpoint', ('','1/12744','1/41715')),
        ('first_service_breakpoint', ('','1/10773','1/39744')),
    ):
        rows = [events['L3',factor,event] for factor in ('1/2','1','2')]
        assert tuple(r['threshold_exact'] for r in rows)==expected
        assert all(r['classification']=='INTEGER_BUDGET_GRANULARITY_THRESHOLD' for r in rows)
    at = events['L3','1','first_service_breakpoint']
    assert (at['z_at'],at['z_immediately_right'])==('1326','1325')
