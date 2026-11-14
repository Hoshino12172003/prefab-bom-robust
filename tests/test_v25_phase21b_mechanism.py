"""Regression checks for fixed-policy transfer and audited mechanism attribution."""
import csv
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'artifacts/v25_phase21b_20261110_221400'
RISKS = ('NR','L1','L2','L3')
POSITIONS = ('x_C','x_T','x_O')


def rows(name):
    with (HERE/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def test_efficiency_covers_entire_primary_optimal_sets_and_p4_tail():
    audit = rows('buffer_delivery_efficiency_audit')
    primary = [r for r in audit if r['test_kind']=='MAIN_ALL_OPEN']
    assert len(audit)==48 and len(primary)==36
    assert {r['all_optima_Q_equals_X'] for r in primary}=={'True'}
    assert sum(int(r['exact_optimal_policy_count']) for r in primary)==2258910
    assert all(r['eta_below_one_policy_count']=='0' and Fraction(r['eta'])==1 for r in primary)
    tail, = [r for r in audit if r['optimum_evidence']=='P4_TAIL']
    assert (tail['unused_buffer_max'],tail['min_eta'],tail['eta_below_one_policy_count'])==('567','103/166','345824')
    assert json.loads(tail['unused_cause_ranges'])=={
        'transport_not_reaching_horizon':[0,545],'additional_due_date_loss':[0,22],
    }


def test_zero_baseline_and_matched_relaxation_distinguish_risk_effects():
    zero = rows('zero_buffer_baseline')
    assert {r['risk'] for r in zero}==set(RISKS)
    assert all(int(r['Q'])==int(r['regular_battery_credits'])==0 for r in zero)
    relax = rows('risk_relaxation_audit')
    matched = [r for r in relax if r['policy_role']=='MATCHED_MIN_COST']
    assert len(matched)==27 and {r['classification'] for r in matched}=={'RISK_NONBINDING_AT_TESTED_POLICY'}
    fixed_nr = [r for r in relax if r['policy_role']=='NR_MIN_COST_TRANSFER'
                and r['days']=='5' and r['regime']=='COST_PROBE']
    assert {r['risk']:int(r['delta_Q_relax']) for r in fixed_nr}=={'L1':762,'L2':670,'L3':670}


def test_cross_policy_matrix_regret_and_full_set_overlap():
    cross = rows('fixed_policy_cross_risk_matrix')
    reg = rows('policy_regret_matrix')
    assert len(cross)==len(reg)==144
    xs, values = defaultdict(set), {}
    for r in cross:
        x = tuple(int(r[v]) for v in POSITIONS)
        group = r['days'],r['regime'],r['policy_origin']
        xs[group].add(x)
        values[(*group,r['evaluated_risk'])] = int(r['Q'])
        shortfall = sum(int(r[name]) for name in ('unreleased_kits','conversion_not_reaching_horizon',
                        'transport_not_reaching_horizon','terminal_availability_above_total_demand',
                        'additional_due_date_loss'))
        assert shortfall==sum(x)-int(r['Q'])
    assert len(xs)==36 and all(len(policies)==1 for policies in xs.values())
    for r in reg:
        key = r['days'],r['regime'],r['policy_origin'],r['risk']
        assert int(r['fixed_Q'])==values[key]
        assert int(r['regret_vehicles'])==int(r['Q_star'])-values[key]>=0
        assert int(r['matching_R_vehicles'])==int(r['regret_vehicles'])
    k5 = [[values['5','COST_PROBE',i,j] for j in RISKS] for i in RISKS]
    assert k5==[[1524,762,854,854],[1073,1073,1073,927],[1326,899,1326,927],[1325,898,1325,1325]]
    full = rows('optimal_set_cross_policy_overlap')
    for risk,expected in {'L1':899,'L2':1325,'L3':959}.items():
        others = [r for r in full if r['days']=='5' and r['regime']=='COST_PROBE' and r['risk']==risk
                  and r['policy_origin']!=risk]
        assert len(others)==3 and max(int(r['maximum_fixed_Q']) for r in others)==expected
        assert all(r['also_optimal_in_evaluated_risk']=='0' for r in others)


def test_budget_matching_and_position_ablation():
    audit = rows('budget_mechanism_audit')
    for days,expected in {'1':(305,215,305,305),'3':(915,644,897,897),'5':(1524,1073,1326,1325)}.items():
        observed = {r['risk']:int(r['Q_star']) for r in audit if r['regime']=='COST_PROBE' and r['days']==days}
        assert observed==dict(zip(RISKS,expected))
    assert all(r['classification']=='FULLY_HEDGED_AT_TESTED_BUDGET' for r in audit
               if r['risk']!='NR' and r['delta_Q_vs_NR']=='0')
    ablation = rows('buffer_form_ablation')
    assert len(ablation)==108
    assert all(r[r['excluded_position']]=='0' for r in ablation)
    witness = {(r['risk'],r['excluded_position']):int(r['service_loss'])
               for r in ablation if r['days']=='5' and r['regime']=='COST_PROBE'}
    assert (witness['NR','x_C'],witness['L1','x_T'],witness['L3','x_O'])==(451,2,398)


def test_binding_slacks_and_due_prefix_attribution():
    timeline = rows('binding_constraint_timeline')
    assert len(timeline)==504
    for r in timeline:
        for i,b in enumerate((10,6,4),1):
            assert int(r[f'component_{i}_available_before_use'])-int(r[f'component_{i}_consumed'])==int(r[f'component_{i}_closing'])
            assert int(r[f'component_{i}_consumed'])==b*int(r['pack_production'])
        assert Fraction(r['production_capacity_slack'])==Fraction(r['production_capacity_rhs'])-int(r['pack_production'])
        assert Fraction(r['transport_capacity_slack'])==Fraction(r['transport_capacity_rhs'])-int(r['pack_transport'])
        assert int(r['oem_assembly_capacity_slack'])>0
    time = rows('time_to_service_attribution')
    assert len(time)==2016
    for risk in ('L2','L3'):
        prefix = [r for r in time if r['days']=='5' and r['regime']=='COST_PROBE' and r['policy_origin']=='NR'
                  and r['risk']==risk and r['relative_period'] in ('13','14')]
        assert [(int(r['cumulative_due']),int(r['earliest_cumulative_pack_availability'])) for r in prefix]==[(2952,803),(3003,876)]
        assert prefix[-1]['actual_Q_cumulative']==prefix[-1]['earliest_cumulative_on_time']=='854'


def test_solver_certificates_and_logs():
    certificates = rows('direct_solver_certificates')
    assert len(certificates)==len({r['run'] for r in certificates})==292
    assert len(list((HERE/'logs').glob('*.log')))==292
    for r in certificates:
        assert r['status']=='OPTIMAL' and r['objective']==r['objective_bound']
        assert float(r['max_residual'])==float(r['integer_ledger_residual'])==0
        assert (HERE/r['log']).read_text(encoding='utf-8').count('Optimal solution found')==1
