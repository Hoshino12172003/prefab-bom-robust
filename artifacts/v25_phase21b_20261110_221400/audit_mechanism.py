"""Frozen-model policy transfer, ablation and operational mechanism diagnostics."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import gurobipy as gp
import numpy as np
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A21 = ROOT/'artifacts/v25_phase21a_20261110_214856'
REQUEST = Path('private_inputs/attachment/已粘贴的文本.txt')
sys.path.insert(0,str(A21))
import audit_joint_policy as cert
from frontier import DEMAND, LABEL, RATIO, RISKS, SCALES, TOTAL, capacity, no_oem_service
from prefab_v25.data import CELL, OEM, PACK, PROD, T1, PRODUCTION_ARC, TRANSPORT_ARC

RISKS4 = ('NOM','L1','L2','L3')
POSITIONS = cert.POSITIONS
ZERO = Fraction(0)
ONE = Fraction(1)
PASS = 'PASS_RISK_POLICY_MATCHING_NONTRIVIAL'
direct_results = []


def risk_name(risk):
    return 'NR' if risk == 'NOM' else risk


def policy(row):
    return tuple(int(row[v]) for v in POSITIONS)


def export(name, rows):
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        w = csv.DictWriter(f,list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def fixed_service(risk, x):
    return min(TOTAL,int(no_oem_service(risk,x[0],x[1]))+x[2])


def physical_trace(risk,c,t1,o):
    """Cumulative earliest output and receipts. Supports scalar or array portfolios."""
    factor = RISKS[risk][0]
    usable = factor.numerator*c//factor.denominator
    produced = sent = received = due = missed = 0
    for t,demand in enumerate(DEMAND,1):
        due += demand
        old_produced = produced
        available = o+received
        short = np.maximum(0,due-available)
        missed = np.maximum(missed,short)
        yield t,due,available,missed,produced,sent
        sent = np.minimum(sent+capacity(risk,2,t),t1+old_produced)
        produced = np.minimum(old_produced+capacity(risk,1,t),usable)
        received = sent


def loss_components(risk, c, t1, o, q):
    timeline = list(physical_trace(risk,c,t1,o))
    usable = RISKS[risk][0].numerator*c//RISKS[risk][0].denominator
    # At the opening of day 13, day-12 production is the latest that can reach OEM by day 14.
    produced_through_12 = timeline[12][4]
    sent_through_13 = timeline[13][5]
    available = timeline[-1][2]
    fields = dict(unreleased_kits=c-usable,conversion_not_reaching_horizon=usable-produced_through_12,
                  transport_not_reaching_horizon=t1+produced_through_12-sent_through_13,
                  terminal_availability_above_total_demand=np.maximum(0,available-TOTAL),
                  additional_due_date_loss=np.minimum(available,TOTAL)-q)
    assert all(np.all(v>=0) for v in fields.values())
    assert np.all(sum(fields.values()) == c+t1+o-q)
    return fields


def set_for(joint,premium,allowed=7):
    high = joint.oem_cap(premium) if allowed&4 else np.zeros_like(joint.c)
    eligible = np.ones(len(joint.c),dtype=bool)
    if not allowed&1:
        eligible &= joint.c==0
    if not allowed&2:
        eligible &= joint.t==0
    value = np.minimum(TOTAL,joint.base+high)
    q = int(value[eligible].max())
    select = eligible & (value==q)
    return q,np.column_stack((joint.c[select],joint.t[select],np.maximum(0,q-joint.base[select]),high[select]))


def solve(direct,name,k,ratio,premium,expected,warm,*,fixed=None,allowed=7,cost_target=None):
    """Direct MILP using the frozen Phase 2.1 recourse builder and integer ledger replay."""
    model = direct.model
    _,scale,coefficients,rhs = cert.budget_terms(k,ratio,premium)
    for i,(v,a) in enumerate(zip(direct.x,coefficients)):
        v.LB = 0 if fixed is None else fixed[i]
        v.UB = (GRB.INFINITY if allowed&(1<<i) else 0) if fixed is None else fixed[i]
        v.Start = int(warm[i])
        model.chgCoeff(direct.budget,v,a)
    direct.budget.RHS = rhs
    target = 0 if cost_target is None else cost_target
    direct.z.LB,direct.z.UB = (0,TOTAL) if cost_target is None else (target,target)
    direct.z.Start = int(expected if cost_target is None else cost_target)
    if cost_target is None:
        model.setObjective(direct.z,GRB.MAXIMIZE)
    else:
        model.setObjective(gp.LinExpr(coefficients,direct.x),GRB.MINIMIZE)
    model.reset()
    path = HERE/'logs'/f'{name}.log'
    model.Params.LogFile = os.path.relpath(path)
    model.message(f'{LABEL} {name} budget={Fraction(rhs,scale)} fixed_x={fixed} allowed_mask={allowed}')
    model.optimize()
    assert model.Status==GRB.OPTIMAL and model.MIPGap==0,name
    assert abs(model.ObjVal-expected)<=1e-7 and abs(model.ObjBound-expected)<=1e-7,(
        name,model.ObjVal,model.ObjBound,expected)
    raw = model.getAttr('X')
    solution = [round(v) for v in raw]
    residual = max(model.ConstrVio,model.BoundVio,model.IntVio)
    assert residual<=1e-7 and max(abs(a-b) for a,b in zip(raw,solution))<=1e-7 and min(solution)>=0
    x,z,q,spend = direct.replay(solution,(scale,coefficients,rhs),allowed,target)
    assert fixed is None or x==fixed
    assert q==z== (expected if cost_target is None else target)
    assert q==fixed_service(direct.risk,x)
    if cost_target is not None:
        assert Fraction(spend)*scale==expected
    result = dict(run=name,x_C=x[0],x_T=x[1],x_O=x[2],Q=q,spend=spend,status='OPTIMAL',
                  objective=int(expected),objective_bound=int(expected),objective_scale=scale if cost_target is not None else 1,
                  max_residual=residual,integer_ledger_residual=0,runtime_s=model.Runtime,
                  log=path.relative_to(HERE).as_posix())
    direct_results.append(result)
    return result,solution


def choose_policy(intervals,k,ratio,premium,archived=None):
    _,_,coef,_ = cert.budget_terms(k,ratio,premium)
    triples = intervals[:,:3]
    spends = triples@np.asarray(coef)
    j = int(np.argmin(spends))
    minima = triples[spends==spends[j]]
    if archived is not None:
        assert np.any(np.all(minima==archived,axis=1))
    selected = tuple(int(v) for v in triples[j]) if archived is None else archived
    return int(spends[j]),selected,len(minima)


def efficiency(context,risk,kind,q,intervals,x,run):
    c,t,lo,hi = intervals.T
    x_min,x_max = c+t+lo,c+t+hi
    assert np.all(x_min>=q)
    size = int((hi-lo+1).sum())
    equal_count = int(np.count_nonzero(x_min==q))
    causes = {}
    if np.any(x_max>q):
        lower,upper = loss_components(risk,c,t,lo,q),loss_components(risk,c,t,hi,q)
        causes = {name: [int(np.min(lower[name])),int(np.max(upper[name]))] for name in lower if np.any(upper[name]>0)}
    quantity = sum(x)
    return dict(**context,risk=risk_name(risk),test_kind=kind,Q_star=q,x_C=x[0],x_T=x[1],x_O=x[2],X=quantity,
                eta=str(Fraction(q,quantity)),Q_equals_X=quantity==q,unused_buffer=quantity-q,
                representative_unused_attribution=json.dumps({k:int(v) for k,v in loss_components(risk,*x,q).items()}),
                exact_optimal_policy_count=size,equal_policy_count=equal_count,eta_one_policy_count=equal_count,
                eta_below_one_policy_count=size-equal_count,all_optima_Q_equals_X=size==equal_count,
                min_X=int(x_min.min()),max_X=int(x_max.max()),
                min_eta=str(Fraction(q,int(x_max.max()))),max_eta=str(Fraction(q,int(x_min.min()))),
                unused_buffer_min=int(x_min.min()-q),unused_buffer_max=int(x_max.max()-q),
                unused_cause_ranges=json.dumps(causes),optimum_evidence=run)


def timeline_rows(context,origin,direct,result,solution,matched):
    risk = direct.risk
    x = policy(result)
    inventory,_,dispatch,service,_ = direct.block
    actual,fulfilled_due = Counter(),Counter()
    for group in direct.network.groups:
        due = group.representative.due
        for t in direct.network.periods:
            q = solution[service[group.id,t].index]
            if t<=due:
                actual[t] += q
                fulfilled_due[due] += q
    trace = list(physical_trace(risk,*x))
    nr_trace = list(physical_trace('NOM',*x))
    binding,time = [],[]
    prev_release = cumulative = prev_earliest = 0
    prev_comp = (0,0,0)
    demand_by_t = dict(zip(direct.network.periods,DEMAND))
    assembly = next(arc for arc in direct.network.arcs if arc.origin==OEM)
    for j,t in enumerate(direct.network.periods):
        day,due,available,missed,prod_before,trans_before = trace[j]
        qprod = solution[dispatch[*PRODUCTION_ARC,PACK,t].index]
        qtrans = solution[dispatch[*TRANSPORT_ARC,PACK,t].index]
        assembly_used = sum(solution[dispatch[*assembly.key,g.id,t].index] for g in direct.network.groups)
        released = solution[direct.release[t].index]
        comp = tuple(solution[inventory[PROD,item,t].index] for item in CELL)
        consumption = tuple(b*qprod for b in (10,6,4))
        accessible = tuple(prior+b*(released-prev_release) for prior,b in zip(prev_comp,(10,6,4)))
        assert tuple(a-b for a,b in zip(accessible,consumption))==comp
        prev_release,prev_comp = released,comp
        cumulative += actual[t]
        earliest_cumulative = due-int(missed)
        ctx = dict(**context,policy_origin=risk_name(origin),risk=risk_name(risk),run=result['run'],
                   relative_period=day,source_period=t)
        time.append(dict(**ctx,actual_Q_t=actual[t],actual_Q_cumulative=cumulative,due_today=demand_by_t[t],
                         due_cohort_completed_on_time=fulfilled_due[t],due_cohort_shortfall=demand_by_t[t]-fulfilled_due[t],
                         cumulative_due=due,earliest_cumulative_pack_availability=int(available),
                         earliest_cumulative_on_time=earliest_cumulative,
                         earliest_Q_t=earliest_cumulative-prev_earliest,
                         earliest_nominal_availability_same_policy=int(nr_trace[j][2]),
                         earliest_nominal_cumulative_on_time_same_policy=due-int(nr_trace[j][3]),
                         running_due_prefix_deficit=int(missed),
                         cumulative_conversion_dispatch_before_t=int(prod_before),
                         cumulative_transport_dispatch_before_t=int(trans_before),
                         nominal_first_possible_OEM_day_C=3,nominal_first_possible_OEM_day_T=2,
                         nominal_first_possible_OEM_day_O=1))
        prev_earliest = earliest_cumulative
        if matched:
            prod_rhs = Fraction(294)*RISKS[risk][1]
            trans_rhs = Fraction(294)*RISKS[risk][2]
            assert int(prod_rhs)==capacity(risk,1,day) and int(trans_rhs)==capacity(risk,2,day)
            binding.append(dict(**ctx,opened_kit_pool=x[0],cumulative_released_kits=released,quarantined_kits=x[0]-released,
                                component_1_available_before_use=accessible[0],component_2_available_before_use=accessible[1],
                                component_3_available_before_use=accessible[2],component_1_consumed=consumption[0],
                                component_2_consumed=consumption[1],component_3_consumed=consumption[2],
                                component_1_availability_slack=comp[0],component_2_availability_slack=comp[1],
                                component_3_availability_slack=comp[2],component_1_closing=comp[0],
                                component_2_closing=comp[1],component_3_closing=comp[2],
                                positive_component_pool_exhausted=accessible[0]>0 and comp[0]==0,
                                pack_production=qprod,production_capacity_rhs=str(prod_rhs),
                                production_capacity_slack=str(prod_rhs-qprod),production_integer_capacity_slack=int(prod_rhs)-qprod,
                                pack_transport=qtrans,transport_capacity_rhs=str(trans_rhs),
                                transport_capacity_slack=str(trans_rhs-qtrans),transport_integer_capacity_slack=int(trans_rhs)-qtrans,
                                oem_assembly=assembly_used,oem_assembly_capacity_slack=assembly.capacity[t]-assembly_used,
                                due_demand_slack=demand_by_t[t]-fulfilled_due[t],actual_Q_t=actual[t],
                                t1_pack_inventory=solution[inventory[T1,PACK,t].index],
                                oem_pack_inventory=solution[inventory[OEM,PACK,t].index]))
    assert cumulative==time[-1]['earliest_cumulative_on_time']==result['Q']
    return binding,time


def capture_context(days,k,regime,ratio,premium,models,outputs,archived_a,archived_runs):
    ctx = dict(label=LABEL,regime=regime,days=days,K=k,
               budget_semantics=f'K{days} quantity cap' if regime=='EQUAL' else f'K{days}-derived budget',
               budget_B=str(ratio*k),c_C='1',c_T=str(ratio),c_O=str(ratio*(1+premium)),premium=str(premium))
    name = f'K{days}_{regime}'
    opt, chosen, opt_sets, cross = {},{},{},{}
    for risk in RISKS4:
        joint = cert.JointSet(risk,ratio*k,ratio)
        q,intervals = set_for(joint,premium)
        opt[risk],opt_sets[risk] = q,intervals
        if regime=='EQUAL':
            archive = archived_runs[f'P2_{risk}_K{days}_all_open']
        else:
            suffix = 'ZERO' if regime=='COST_ZERO' else 'PROBE'
            archive = archived_runs[f'P5_{risk}_K{days}_{suffix}']
        assert int(archive['z'])==q
        source = archived_a.get((risk,regime)) if days==5 else None
        cost,x,mc_count = choose_policy(intervals,k,ratio,premium,policy(source) if source else None)
        cost_result,_ = solve(models[risk],f'{name}_{risk}_min_cost',k,ratio,premium,cost,x,cost_target=q)
        chosen[risk] = x
        outputs['minimum_cost_policy_certificates'].append(dict(**ctx,risk=risk_name(risk),Q_star=q,
            selected_x_C=x[0],selected_x_T=x[1],selected_x_O=x[2],minimum_cost_tie_count=mc_count,
            selected_from='PHASE21A' if source else 'LEXICOGRAPHIC_AMONG_MINIMUM_COST_OPTIMA',**cost_result))
        outputs['buffer_delivery_efficiency_audit'].append(efficiency(ctx,risk,'MAIN_ALL_OPEN',q,intervals,x,archive['run']))
        if days==5 and risk!='NOM':
            # Compare the frozen full set cardinality, not just the archived chosen point.
            a = next(r for r in archived_a['counts'] if (r['risk'],r['regime'])==(risk,regime))
            assert int(a['optimal_policy_count'])==int(np.sum(intervals[:,3]-intervals[:,2]+1))
        for i,pos in enumerate(POSITIONS):
            allowed = 7^(1<<i)
            q_restricted,values = set_for(joint,premium,allowed)
            start = tuple(int(v) for v in values[0,:3])
            result,_ = solve(models[risk],f'{name}_{risk}_without_{pos}',k,ratio,premium,q_restricted,start,allowed=allowed)
            outputs['buffer_form_ablation'].append(dict(**ctx,risk=risk_name(risk),excluded_position=pos,
                Q_star=q,service_loss=q-q_restricted,service_loss_pp=100*(q-q_restricted)/TOTAL,**result))
    for origin in RISKS4:
        x = chosen[origin]
        for risk in RISKS4:
            expected = fixed_service(risk,x)
            result,solution = solve(models[risk],f'{name}_{origin}_to_{risk}',k,ratio,premium,expected,x,fixed=x)
            cross[origin,risk] = result
            physical = {key:int(value) for key,value in loss_components(risk,*x,expected).items()}
            outputs['fixed_policy_cross_risk_matrix'].append(dict(**ctx,policy_origin=risk_name(origin),
                evaluated_risk=risk_name(risk),X=sum(x),efficiency=str(Fraction(expected,sum(x))),
                service_percent=100*expected/TOTAL,**physical,**result))
            binding,time = timeline_rows(ctx,origin,models[risk],result,solution,origin==risk)
            outputs['binding_constraint_timeline'].extend(binding)
            outputs['time_to_service_attribution'].extend(time)
    x_nr = chosen['NOM']
    q_nr = opt['NOM']
    nr_cert = cross['NOM','NOM']
    outputs['no_risk_benchmark'].append(dict(**ctx,Q_NR_star=q_nr,service_percent=100*q_nr/TOTAL,
        x_C=x_nr[0],x_T=x_nr[1],x_O=x_nr[2],minimum_protection_cost=nr_cert['spend'],
        service_log=nr_cert['log'],minimum_cost_log=f'logs/{name}_NOM_min_cost.log'))
    c,t,lo,hi = opt_sets['NOM'].T
    common_low = lo.copy()
    for risk in RISKS4[1:]:
        common_low = np.maximum(common_low,opt[risk]-no_oem_service(risk,c,t))
    common = int(np.maximum(0,hi-common_low+1).sum())
    for risk in RISKS4:
        match = cross[risk,risk]['Q']
        assert match==opt[risk]
        best_other = max(cross[i,risk]['Q'] for i in RISKS4 if i!=risk)
        ties = [risk_name(i) for i in RISKS4 if i!=risk and cross[i,risk]['Q']==match]
        outputs['risk_policy_matching_effect'].append(dict(**ctx,risk=risk_name(risk),
            matched_Q=match,best_other_representative_Q=best_other,M_vehicles=match-best_other,
            M_percentage_points=100*(match-best_other)/TOTAL,tied_other_representatives='|'.join(ties),
            common_optimal_portfolios_across_all_four=common))
        delta = q_nr-opt[risk]
        classification = 'NO_DISRUPTION_REFERENCE' if risk=='NOM' else (
            'FULLY_HEDGED_AT_TESTED_BUDGET' if delta==0 else 'REOPTIMIZED_SERVICE_LOSS')
        outputs['budget_mechanism_audit'].append(dict(**ctx,risk=risk_name(risk),Q_NR_star=q_nr,Q_star=opt[risk],
            delta_Q_vs_NR=delta,delta_pp_vs_NR=100*delta/TOTAL,classification=classification,
            M_vehicles=match-best_other,M_percentage_points=100*(match-best_other)/TOTAL,
            NR_policy_regret=opt[risk]-cross['NOM',risk]['Q'],common_optimal_portfolios_across_all_four=common,
            x_C=chosen[risk][0],x_T=chosen[risk][1],x_O=chosen[risk][2]))
        for origin in RISKS4:
            row = cross[origin,risk]
            regret = opt[risk]-row['Q']
            assert regret>=0
            outputs['policy_regret_matrix'].append(dict(**ctx,policy_origin=risk_name(origin),risk=risk_name(risk),
                Q_star=opt[risk],matched_representative_Q=match,fixed_Q=row['Q'],regret_vehicles=regret,
                regret_percentage_points=100*regret/TOTAL,matching_R_vehicles=match-row['Q'],
                matching_R_percentage_points=100*(match-row['Q'])/TOTAL,
                x_C=row['x_C'],x_T=row['x_T'],x_O=row['x_O'],fixed_policy_log=row['log']))
            # Exact audit across the full optimal policy set of each origin.
            c,t,lo,hi = opt_sets[origin].T
            base = no_oem_service(risk,c,t)
            hit = int(np.maximum(0,hi-np.maximum(lo,opt[risk]-base)+1).sum())
            outputs['optimal_set_cross_policy_overlap'].append(dict(**ctx,policy_origin=risk_name(origin),risk=risk_name(risk),
                origin_optimal_portfolios=int((hi-lo+1).sum()),also_optimal_in_evaluated_risk=hit,
                minimum_fixed_Q=int(np.minimum(TOTAL,base+lo).min()),maximum_fixed_Q=int(np.minimum(TOTAL,base+hi).max()),
                evaluated_risk_optimal_Q=opt[risk]))
        if risk!='NOM':
            factor_index = RISKS4.index(risk)-1
            assert all(v==1 for j,v in enumerate(RISKS[risk]) if j!=factor_index)
            # A singleton layer restoration is exactly the NR recourse instance.
            for origin,role in ((risk,'MATCHED_MIN_COST'),('NOM','NR_MIN_COST_TRANSFER')):
                stressed,relaxed = cross[origin,risk],cross[origin,'NOM']
                assert policy(stressed)==policy(relaxed)
                gain = relaxed['Q']-stressed['Q']
                outputs['risk_relaxation_audit'].append(dict(**ctx,risk=risk,policy_role=role,
                    x_C=stressed['x_C'],x_T=stressed['x_T'],x_O=stressed['x_O'],
                    restored_mechanism=('component_quality_release','production_capacity','transport_capacity')[factor_index],
                    stressed_factor=str(RISKS[risk][factor_index]),restored_factor='1',
                    stressed_Q=stressed['Q'],relaxed_Q=relaxed['Q'],delta_Q_relax=gain,
                    delta_percentage_points=100*gain/TOTAL,classification=(
                        'RISK_NONBINDING_AT_TESTED_POLICY' if gain==0 else 'SERVICE_GAIN_ON_SINGLE_LAYER_RESTORATION'),
                    stressed_log=stressed['log'],restored_log=relaxed['log']))


def extra_efficiency(outputs):
    single = cert.records(cert.PRIOR/'single_buffer_capability.csv')
    threshold = cert.records(cert.PRIOR/'threshold_direct_checks.csv')
    for row in [r for r in single if r['mode']!='all_open']+threshold:
        risk,k,ratio,premium = row['risk'],int(row['k']),Fraction(row['ratio']),Fraction(row['premium'])
        days = next(d for d,value in SCALES.items() if value==k)
        kind = 'P2_SINGLE_POSITION' if 'mode' in row else 'P4_ARCHIVED_BREAKPOINT_SPOT_CHECK'
        ctx = dict(label=LABEL,regime=row.get('mode','P4'),days=days,K=k,
                   budget_semantics=f'K{days} quantity cap' if kind.startswith('P2') else f'K{days}-derived budget',
                   budget_B=str(ratio*k),c_C='1',c_T=str(ratio),c_O=str(ratio*(1+premium)),premium=str(premium))
        allowed = {'C_only':1,'T1_only':2,'OEM_only':4}.get(row.get('mode'),7)
        q,intervals = set_for(cert.JointSet(risk,ratio*k,ratio),premium,allowed)
        assert q==int(row['z'])==fixed_service(risk,policy(row))
        outputs['buffer_delivery_efficiency_audit'].append(efficiency(ctx,risk,kind,q,intervals,policy(row),row['run']))


def main():
    phase21a_checks = cert.verify_manifest(A21/'sha256_manifest.csv')
    phase21_checks = cert.verify_manifest(cert.PRIOR/'sha256_manifest.csv')
    legacy = json.loads((cert.PRIOR/'audit.json').read_text(encoding='utf-8'))
    assert cert.digest(cert.prior.SOURCE)==legacy['source_sha256']
    assert all(cert.digest(Path(p))==h for p,h in legacy['input_code_sha256'].items())
    probe = Fraction(legacy['common_premium_probe'])
    network,phase20_checks = cert.prior.load_prospective()
    archived_a = {(r['risk'],r['regime']):r for r in cert.records(A21/'minimum_cost_service_optimal.csv')}
    archived_a['counts'] = cert.records(A21/'joint_policy_set_summary.csv')
    archived_runs = {}
    for name in ('equal_cost_dominance','risk_location_policy_response'):
        archived_runs.update((r['run'],r) for r in cert.records(cert.PRIOR/f'{name}.csv'))
    outputs = {n:[] for n in (
        'buffer_delivery_efficiency_audit','zero_buffer_baseline','no_risk_benchmark',
        'fixed_policy_cross_risk_matrix','policy_regret_matrix','binding_constraint_timeline',
        'risk_relaxation_audit','buffer_form_ablation','time_to_service_attribution','budget_mechanism_audit',
        'risk_policy_matching_effect','optimal_set_cross_policy_overlap','minimum_cost_policy_certificates')}
    (HERE/'logs').mkdir(exist_ok=True)
    with gp.Env() as env:
        models = {risk:cert.prior.Direct(network,risk,env) for risk in RISKS4}
        for risk,direct in models.items():
            result,_ = solve(direct,f'ZERO_{risk}',0,RATIO,probe,0,(0,0,0),fixed=(0,0,0))
            outputs['zero_buffer_baseline'].append(dict(label=LABEL,risk=risk_name(risk),budget_B='0',
                regular_battery_credits=0,**result))
        for days,k in SCALES.items():
            for regime,r,p in (('EQUAL',ONE,ZERO),('COST_ZERO',RATIO,ZERO),('COST_PROBE',RATIO,probe)):
                capture_context(days,k,regime,r,p,models,outputs,archived_a,archived_runs)
                print(f'K{days} {regime} certified',flush=True)
            for key,table in outputs.items():
                export(f'{key}.csv',table)
        for direct in models.values():
            direct.model.dispose()
    extra_efficiency(outputs)
    export('buffer_delivery_efficiency_audit.csv',outputs['buffer_delivery_efficiency_audit'])
    export('direct_solver_certificates.csv',direct_results)
    main_rows = [r for r in outputs['buffer_delivery_efficiency_audit'] if r['test_kind']=='MAIN_ALL_OPEN']
    logs = list((HERE/'logs').glob('*.log'))
    assert len(logs)==len(direct_results)==292
    assert all(p.read_text(encoding='utf-8').count('Optimal solution found')==1 for p in logs)
    assert cert.verify_manifest(A21/'sha256_manifest.csv')==phase21a_checks
    assert cert.verify_manifest(cert.PRIOR/'sha256_manifest.csv')==phase21_checks
    audit = dict(status=PASS,label=LABEL,git_sha=subprocess.check_output(['git','rev-parse','HEAD'],
        cwd=ROOT,text=True).strip(),gurobi_version=gp.gurobi.version(),attachment_sha256=cert.digest(REQUEST),
        source_zip_sha256=legacy['source_sha256'],source_xlsb_sha256=legacy['source_xlsb_sha256'],
        frozen_input_manifest_sha256={p.relative_to(ROOT).as_posix():cert.digest(p) for p in
            (A21/'sha256_manifest.csv',cert.PRIOR/'sha256_manifest.csv',cert.prior.PHASE20/'sha256_manifest.csv')},
        frozen_inputs_verified={'phase20':phase20_checks,'phase21':phase21_checks,'phase21a':phase21a_checks},
        frozen_code_sha256=legacy['input_code_sha256'],direct_diagnostic_calls=len(logs),
        solver_gap=0,max_solver_residual=max(r['max_residual'] for r in direct_results),
        integer_ledger_residual=0,direct_total_runtime_s=sum(r['runtime_s'] for r in direct_results),
        scope_counts={name:len(rows) for name,rows in outputs.items()},
        all_open_efficiency={'environments':len(main_rows),'all_optima_equal':sum(r['all_optima_Q_equals_X'] for r in main_rows),
            'total_optimal_policies_counted_by_environment':sum(r['exact_optimal_policy_count'] for r in main_rows),
            'eta_below_one_policy_count':sum(r['eta_below_one_policy_count'] for r in main_rows)},
        no_additional_supply_claim='dedicated protective coverage',
        algorithm_calls=0,managerial_optimization_calls=0,tests='PENDING',
        command='python -B artifacts/v25_phase21b_20261110_221400/audit_mechanism.py')
    (HERE/'audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
