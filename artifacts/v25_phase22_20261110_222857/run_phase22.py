"""Run only the authorized Phase 2.2 freeze and diagnostic checks."""
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

import gurobipy as gp

from design import (DEMAND,F,HERE,LAYERS,NR,ONE,P21A,P21B,PASS_HOLD,RATIO,RATIOS,ROOT,
                    SCALES,TOTAL,Profile,benchmark_candidates,benchmark_family,exact_cover,export,
                    factors_json,fixed_service,formal_profiles,prior,read,t1_screen,write_grids)
from direct_diagnostics import run_direct

REQUEST=Path('private_inputs/attachment/已粘贴的文本.txt')


def benchmark_grid():
    family,dominance=benchmark_family()
    export('benchmark_scenario_dominance_audit.csv',dominance)
    export('benchmark_instance_manifest.csv',(dict(case_id=case,classification=classification,replicas=n,
        demand=TOTAL*n,aggregated_order_groups=28,horizon=14,scenario_count=len(profiles),
        scenario_ids='|'.join(p.name for p in profiles),scenario_factor_paths=json.dumps(
            {p.name:json.loads(factors_json(p)) for p in profiles}),
        budget_rule=f'{n}*K5*c_T',budget_exact=str(n*SCALES[5]*RATIO),ratio=str(RATIO),premium='1/10',
        replication='original VINs' if n==1 else 'parallel pooled copies; scale each due cohort, initial nonbattery state and capacities',
        scaling_axes='scenario' if n==1 else 'proportional demand and matching resources',
        lead_times='20/1/1',demand_due_counts='|'.join(str(n*d) for d in DEMAND),seed=0,
        time_limit_s=60,soft_memory_gb=2,presolve='AUTO') for case,n,profiles,classification in family))
    results=[]
    for case,*_ in family:
        subprocess.run([sys.executable,'-B',str(HERE/'direct_diagnostics.py'),case],cwd=ROOT,check=True)
        results.append(json.loads((HERE/f'{case}_metrics.json').read_text(encoding='utf-8')))
        print(f'{case}: {results[-1]["status"]}, {results[-1]["scenario_count"]} scenarios',flush=True)
    export('direct_de_scaling_benchmark.csv',results)
    return results


def archived_recourse():
    profiles={'NR':NR,
              'L1':Profile('FROZEN21_L1',(F(1,2),F(0),F(0)),14,'ABRUPT','PRIOR_CERTIFIED'),
              'L2':Profile('FROZEN21_L2',(F(0),F(3,4),F(0)),14,'ABRUPT','PRIOR_CERTIFIED'),
              'L3':Profile('FROZEN21_L3',(F(0),F(0),F(3,4)),14,'ABRUPT','PRIOR_CERTIFIED')}
    for r in read(P21B/'fixed_policy_cross_risk_matrix.csv'):
        x=tuple(int(r[v]) for v in ('x_C','x_T','x_O'))
        profile=profiles[r['evaluated_risk']]
        q=fixed_service(profile,x)
        assert int(r['Q'])==q
        yield dict(scope='ARCHIVED_PHASE21B_FIXED_POLICY',case_id=r['run'],policy=r['policy_origin'],
            evaluated_profile=profile.name,x_C=x[0],x_T=x[1],x_O=x[2],buffer_count=sum(x),exact_Q=q,
            direct_Q=int(r['Q']),Q_count_difference=sum(x)-q,matched=True,status=r['status'],
            integer_recourse_optimizer_needed_for_evaluation=False,solver_log=(P21B/r['log']).relative_to(ROOT).as_posix())


def direct_recourse(network,profiles,env):
    k=SCALES[5]
    r,premium=RATIO,F(1,10)
    budget=r*k
    policies=[('ZERO',(0,0,0)),('MAX_C',(int(budget),0,0)),('MAX_T1',(0,k,0)),
              ('MAX_OEM',(0,0,int(budget/(r*(ONE+premium)))))]
    rng=random.Random(2252)
    for i in range(4):
        c=rng.randint(0,int(budget))
        t1=rng.randint(0,int((budget-c)/r))
        o=rng.randint(0,int((budget-c-r*t1)/(r*(ONE+premium))))
        policies.append((f'RANDOM_{i+1}',(c,t1,o)))
    rows=[]
    for tag,x in policies:
        for profile in profiles:
            name=f'FIXED_{tag}_{profile.name}'
            result=run_direct(name,network,[profile],k,r,premium,1,fixed=x,env=env)
            q=fixed_service(profile,x)
            assert result['status']=='OPTIMAL' and result['objective']==q
            rows.append(dict(scope='NEW_RANDOM_OR_EXTREME_DIRECT',case_id=name,policy=tag,evaluated_profile=profile.name,
                x_C=x[0],x_T=x[1],x_O=x[2],buffer_count=sum(x),exact_Q=q,direct_Q=result['objective'],
                Q_count_difference=sum(x)-q,matched=True,status=result['status'],
                integer_recourse_optimizer_needed_for_evaluation=False,
                solver_log=(HERE/result['log']).relative_to(ROOT).as_posix()))
    return rows


def t1_direct_checks(network,candidates,profiles,env):
    lookup={p.name:p for p in profiles}
    core=[r for r in candidates if r['kind']=='CORE']
    selected=[max((r for r in core if r['layer']==layer),key=lambda r:r['V_T']) for layer in LAYERS]
    selected.append(next(r for r in core if not r['V_T']))
    rows=[]
    for i,row in enumerate(selected):
        k=SCALES[int(row['budget_id'][1:])]
        r,p=F(row['r_PC']),F(row['delta_O'])
        for allowed,key in ((True,'Q_star'),(False,'Q_without_T1')):
            result=run_direct(f'T1_CHECK_{i}_'+('FULL' if allowed else 'ABLATION'),network,[lookup[row['scenario_id']]],
                k,r,p,1,allow_t1=allowed,env=env,expected=row[key])
            assert result['status']=='OPTIMAL'
            rows.append(dict(**row,allow_T1=allowed,direct_objective=result['objective'],direct_bound=result['objective_bound'],
                direct_status=result['status'],max_solver_residual=result['max_solver_residual'],log=result['log']))
    export('t1_direct_spot_checks.csv',rows)
    return rows


def main():
    manifests=(prior.prior.PHASE20/'sha256_manifest.csv',prior.PRIOR/'sha256_manifest.csv',
               P21A/'sha256_manifest.csv',P21B/'sha256_manifest.csv')
    frozen={p.relative_to(ROOT).as_posix():dict(sha256=prior.digest(p),entries=prior.verify_manifest(p)) for p in manifests}
    old=json.loads((P21B/'audit.json').read_text(encoding='utf-8'))
    assert prior.digest(prior.prior.SOURCE)==old['source_zip_sha256']
    assert all(prior.digest(Path(p))==h for p,h in old['frozen_code_sha256'].items())
    (HERE/'logs').mkdir(exist_ok=True)
    profiles=list(formal_profiles())
    grid=write_grids()
    candidate_rows=t1_screen(profiles)
    (HERE/'resource_protocol.json').write_text(json.dumps(dict(threads=1,seed=0,presolve='AUTO',
        optimality_tol=1e-9,feasibility_tol=1e-9,integer_feasibility_tol=1e-9,
        mip_gap=0,mip_gap_abs=0,time_limit_s=60,soft_mem_limit_gb=2,
        benchmark_starts='no MIP starts',measurement='one fresh process per DE; Windows peak working set and Gurobi MaxMemUsed',
        limitations='fixed bounded diagnostic family; no algorithm performance comparison'),indent=2)+'\n',encoding='utf-8')
    de=benchmark_grid()
    network,_=prior.prior.load_prospective()
    formal=[next(p for p in profiles if p.name==name) for name in
            ('L1_S3_LONG_GRADUAL','L2_S3_LONG_ABRUPT','L3_S3_LONG_GRADUAL')]
    compound=next(p for p in benchmark_candidates() if p.name.endswith('111'))
    with gp.Env() as env:
        recourse=[*archived_recourse(),*direct_recourse(network,[NR,*formal,compound],env)]
        t1_direct=t1_direct_checks(network,candidate_rows,profiles,env)
    export('recourse_necessity_audit.csv',recourse)
    assert all(row['matched'] for row in recourse)
    assert any(row['Q_count_difference']>0 for row in recourse)
    assert all(prior.verify_manifest(ROOT/name)==p['entries'] for name,p in frozen.items())
    logs=list((HERE/'logs').glob('*.log'))
    assert len(logs)==len(de)+len(t1_direct)+40
    core=[r for r in candidate_rows if r['kind']=='CORE']
    summary=dict(status=PASS_HOLD,formal_design='FROZEN_EXPERIMENTAL_DESIGN',
        git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        frozen_input_manifests=frozen,source_zip_sha256=old['source_zip_sha256'],source_xlsb_sha256=old['source_xlsb_sha256'],
        request_sha256=prior.digest(REQUEST),unchanged_code_sha256=old['frozen_code_sha256'],
        severity=['1/4','1/2','3/4'],duration_periods=[4,7,11],nominal_horizon=14,
        candidate_profile_count=len(grid),unique_service_profiles=sum(r['unique_service_evaluation'] for r in grid),
        nominal_reference_per_cost_and_budget=len(SCALES)*len(RATIOS)*4,
        primary_managerial_risk_budget_cells=len(core)//(len(RATIOS)*4),t1_core_positive=sum(r['V_T']>0 for r in core),
        t1_core_cases=len(core),t1_sensitivity_positive=sum(r['V_T']>0 for r in candidate_rows if r['kind']!='CORE'),
        t1_sensitivity_cases=len(candidate_rows)-len(core),t1_max_core_service_effect=max(r['V_T'] for r in core),
        t1_conclusion='T1_POSITION_WEAK_MECHANISM',t1_role='INTERMEDIATE_BENCHMARK_POSITION',
        recourse_matches=len(recourse),new_fixed_policy_direct=40,archived_fixed_policy_replays=144,
        benchmark_runs=len(de),benchmark_statuses=dict(Counter(r['status'] for r in de)),
        benchmark_largest_variables=max(r['variables'] for r in de),
        optimizer_calls=len(logs),algorithm_calls=0,formal_managerial_direct_sweep_calls=0,
        algorithm_gate='FAIL_REDUCIBLE_EXACT_SERVICE_AND_FIRST_STAGE_COVER',
        command='python -B artifacts/v25_phase22_20261110_222857/run_phase22.py',tests='PENDING')
    (HERE/'audit.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
