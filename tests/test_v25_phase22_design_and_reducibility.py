"""Frozen design, exact miniature certificate, and Direct evidence regressions."""
import csv
import importlib.util
import itertools
import json
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest


ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'artifacts/v25_phase22_20261110_222857'


def rows(name):
    with (HERE/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def design():
    name='phase22_frozen_design'
    spec=importlib.util.spec_from_file_location(name,HERE/'design.py')
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    yield module
    del sys.modules[name]


def test_budget_cost_and_risk_design():
    b=rows('formal_budget_grid')
    assert [(int(r['K']),F(r['B_baseline'])) for r in b]==[(215,F(5805,19)),(644,F(17388,19)),(1073,F(28971,19))]
    costs=rows('formal_cost_grid')
    assert len(costs)==12
    assert {F(r['r_PC']) for r in costs}=={F(27,19),F(13,10),F(157,100)}
    assert {F(r['delta_O']) for r in costs}=={F(0),F(1,20),F(1,10),F(1,5)}
    grid=rows('formal_managerial_scenario_grid')
    assert len({r['scenario_id'] for r in grid})==len({r['factor_paths'] for r in grid})==55
    canonical={r['scenario_id'] for r in grid if r['unique_service_evaluation']=='True'}
    assert canonical=={r['canonical_service_profile'] for r in grid} and len(canonical)==16
    core=[r for r in grid if r['kind']=='CORE']
    assert len(core)==27 and {int(r['duration_periods']) for r in core}=={4,7,11}
    for r in grid:
        paths=[[F(q) for q in path] for path in json.loads(r['factor_paths'])]
        assert len(paths)==3 and all(len(path)==14 and all(0<=v<=1 for v in path) for path in paths)
        assert all(a<=b for a,b in zip(paths[0],paths[0][1:]))


def test_projected_robust_cover_against_explicit_toy_recourse(design,monkeypatch):
    monkeypatch.setattr(design,'DEMAND',(2,1,3,2,1))
    monkeypatch.setattr(design,'TOTAL',9)
    monkeypatch.setattr(design,'WINDOW',5)
    monkeypatch.setattr(design,'RAW',((2,1,2,1,2),(1,2,1,2,2)))
    profiles=[design.NR,
        design.Profile('COMPOUND',(F(1,2),F(1,4),F(3,4)),2,'GRADUAL','test'),
        design.Profile('TRANSPORT',(F(0),F(0),F(1,2)),3,'ABRUPT','test')]

    def explicit(profile,x):
        # Enumerate all small integer dispatches and all due-day service options.
        c,t1,o=x
        f=profile.factors
        states={(0,t1,o,0,0,0)}
        for i,d in enumerate(design.DEMAND):
            next_states=set()
            for produced,t_stock,o_stock,in_prod,in_ship,count in states:
                t_stock+=in_prod
                o_stock+=in_ship
                for pp,ss,qq in itertools.product(
                        range(min(int(f[0][i]*c)-produced,int(f[1][i]*design.RAW[0][i]))+1),
                        range(min(t_stock,int(f[2][i]*design.RAW[1][i]))+1),range(min(d,o_stock)+1)):
                    next_states.add((produced+pp,t_stock-ss,o_stock-qq,pp,ss,count+qq))
            states=next_states
        return max(state[-1] for state in states)

    k,r,p=4,F(3,2),F(1,10)
    candidates=[]
    for x in itertools.product(range(7),range(5),range(5)):
        spend=x[0]+r*x[1]+r*(1+p)*x[2]
        if spend>k*r:
            continue
        values=[explicit(s,x) for s in profiles]
        assert values==[design.fixed_service(s,x) for s in profiles]
        candidates.append((min(values),spend,x))
    for allowed in (True,False):
        subset=[v for v in candidates if allowed or v[2][1]==0]
        q,cost=min((-q,cost) for q,cost,_ in subset)
        actual,x,spend=design.exact_cover(profiles,k,r,p,allow_t1=allowed)
        assert actual==-q and spend==cost and (actual,spend,x) in subset


def test_t1_ablation_and_nr_reference():
    screen=rows('t1_position_value_audit')
    assert len(screen)==1944
    assert all(int(r['V_T'])==int(r['Q_star'])-int(r['Q_without_T1'])>=0 for r in screen)
    assert all(int(r['loss_vs_NR'])==int(r['Q_NR_star'])-int(r['Q_star'])>=0 for r in screen)
    core=[r for r in screen if r['kind']=='CORE']
    assert len(core)==972 and sum(int(r['V_T'])>0 for r in core)==109
    assert max(int(r['V_T']) for r in core)==171
    assert len(rows('formal_nr_reference_audit'))==36
    direct=rows('t1_direct_spot_checks')
    assert len(direct)==8
    assert all(r['direct_status']=='OPTIMAL' and float(r['direct_bound'])==int(r['direct_objective'])==
               int(r['Q_star'] if r['allow_T1']=='True' else r['Q_without_T1']) for r in direct)


def test_de_robust_equivalence_and_clean_scenario_family():
    base=rows('direct_de_scaling_benchmark')
    assert len(base)==6
    assert {int(r['scenario_count']) for r in base}=={1,2}
    assert {int(r['replicas']) for r in base}=={1,2,3}
    for r in base:
        assert r['status']=='OPTIMAL' and float(r['gap'])==0
        assert int(r['objective'])==int(r['independent_exact_bound'])==float(r['objective_bound'])
        assert r['presolve']=='AUTO' and int(r['process_peak_working_set_bytes'])>0
        assert r['rounded_matrix_residual']=='0'
        assert (HERE/r['log']).is_file()
    for n in ('1','2','3'):
        checked=[r for r in rows('benchmark_scenario_dominance_audit') if r['replicas']==n]
        assert len(checked)==10 and {r['scenario_id'][-3:] for r in checked if r['retained']=='True'}=={'003','300'}


def test_fixed_policy_recourse_closes_all_certificates():
    cases=rows('recourse_necessity_audit')
    assert len(cases)==184
    assert all(r['exact_Q']==r['direct_Q'] and r['integer_recourse_optimizer_needed_for_evaluation']=='False' for r in cases)
    assert max(int(r['Q_count_difference']) for r in cases)>=762
    assert len([r for r in cases if r['scope']=='NEW_RANDOM_OR_EXTREME_DIRECT'])==40
    assert len(list((HERE/'logs').glob('*.log')))==54
