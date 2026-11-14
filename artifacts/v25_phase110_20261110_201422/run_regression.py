"""Re-solve the six frozen cells with raw capacities and replay strict witnesses."""
import gzip
import json
import os
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = ROOT/'artifacts/v25_phase16_20261110_160104'
sys.path.insert(0,str(PREVIOUS))

from run_audit import (FORMAL, GRB, SOURCE, build, compile_network, csv_file, digest, frozen_runs,
                       gp, load_tables, manifest_bytes, save_json)
from finalize_audit import exact, exact_expr, physical_upper
from prefab_v25.data import COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC

HOLD = 'HOLD_CAPACITY_NORMALIZATION_NOT_EQUIVALENT_IN_IMPLEMENTATION'
EXPECTED = dict(nominal_B0=26448,nominal_B20=26472,nominal_B50=26508,nominal_B100=26569,DE_B0=25974,DE_B50=26034)


def compare_matrix(raw, old, run, network):
    raw.update()
    assert raw.NumVars==old.NumVars and raw.NumConstrs==old.NumConstrs and raw.DNumNZs==old.DNumNZs
    assert raw.ModelSense==old.ModelSense==GRB.MAXIMIZE and raw.ObjCon==old.ObjCon
    attributes=('VarName','LB','UB','VType','Obj')
    assert all(raw.getAttr(attr)==old.getAttr(attr) for attr in attributes)
    changed=[]
    battery={COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC}
    arcs={a.key:a for a in network.arcs}
    for r0,r1 in zip(old.getConstrs(),raw.getConstrs()):
        assert (r0.ConstrName,r0.Sense)==(r1.ConstrName,r1.Sense)
        a=old.getRow(r0)
        b=raw.getRow(r1)
        old_terms={a.getVar(i).VarName:a.getCoeff(i) for i in range(a.size())}
        new_terms={b.getVar(i).VarName:b.getCoeff(i) for i in range(b.size())}
        if r0.RHS==r1.RHS and old_terms==new_terms:
            continue
        assert old_terms.keys()==new_terms.keys() and r1.Sense=='<'
        assert set(old_terms.values())=={float(Fraction(5,21))} and set(new_terms.values())=={1.0}
        variable=next(iter(new_terms))
        block,idx=variable.split('_q[',1)
        i,j,_,t=idx.removesuffix(']').split(',')
        t=int(t)
        scenario=run.scenarios[int(block[1:])]
        assert (i,j) in battery
        expected=arcs[i,j].capacity[t]*scenario.factor((i,j),t)
        assert r1.RHS==float(expected) and r0.RHS==float(expected*Fraction(5,21))
        assert set(new_terms)=={f'{block}_q[{i},{j},{p},{t}]' for p in arcs[i,j].recipes}
        changed.append(dict(run=run.id,row=r1.ConstrName,scenario=scenario.name,origin=i,destination=j,period=t,
                            old_rhs=r0.RHS,raw_rhs=r1.RHS,terms=len(new_terms),
                            old_lhs_factor=float(Fraction(5,21)),new_lhs_factor=1))
    assert len(changed)==3*len(network.periods)*len(run.scenarios)
    assert len({(r['scenario'],r['origin'],r['destination'],r['period']) for r in changed})==len(changed)
    return changed


def verify_witness(model, network, run, blocks, prior_row):
    path=PREVIOUS/prior_row['exact_certificate_file']
    assert digest(path)==prior_row['exact_certificate_sha256']
    with gzip.open(path,'rt',encoding='utf8') as f:
        witness=json.load(f)
    variables=model.getVars()
    assert witness.keys()<={v.VarName for v in variables}
    values=[Fraction(v) if isinstance(v,str) else v for x in variables for v in (witness.get(x.VarName,0),)]
    assert all(v.LB<=q<=v.UB and (v.VType!=GRB.INTEGER or type(q) is int) for v,q in zip(variables,values))
    for c in model.getConstrs():
        residual=exact_expr(model.getRow(c),values)-exact(c.RHS)
        assert (residual==0 if c.Sense=='=' else residual<=0 if c.Sense=='<' else residual>=0),(run.id,c.ConstrName,residual)
    per_scenario={s.name:exact_expr(b[-1],values) for s,b in zip(run.scenarios,blocks)}
    count=min(per_scenario.values())
    assert count==EXPECTED[run.id]
    if run.de:
        assert exact_expr(model.getObjective(),values)==Fraction(count,network.demand_weight)
    quantities=[witness.get(name,0) for name in prior_row.get('buffer_names',('x_cell_kit','x_t1_pack','x_oem_pack'))]
    spend=sum(Fraction(c)*q for c,q in zip(run.costs,quantities))
    assert spend<=Fraction(run.budget)
    return count,str(spend),per_scenario,digest(path)


def main():
    network,_=compile_network(load_tables(SOURCE))
    runs=frozen_runs(manifest_bytes(FORMAL/'manifest.json'))
    prior=json.loads((PREVIOUS/'audit.json').read_text(encoding='utf8'))
    rows, matrix=[] ,[]
    with gp.Env(empty=True) as env:
        env.setParam('LogToConsole',0)
        env.start()
        for run in runs:
            print('START',run.id,flush=True)
            model,_,blocks=build(env,network,run)
            try:
                with model:
                    old=PREVIOUS/'opt_model_identity'/f'{run.id}.mps'
                    old_sha=next(x['sha256'] for x in prior['model_files'] if x['run']==run.id and x['format']=='mps')
                    assert digest(old)==old_sha
                    with gp.read(os.path.relpath(old),env=env) as archived:
                        changed=compare_matrix(model,archived,run,network)
                    matrix.extend(changed)
                    csv_file(HERE/'capacity_row_equivalence.csv',matrix)
                    model.Params.LogFile=os.path.relpath(HERE/f'{run.id}.log')
                    model.Params.LogToConsole=0
                    model.Params.Threads=4
                    model.Params.Seed=20261110
                    model.Params.MIPGap=model.Params.MIPGapAbs=0
                    model.Params.OptimalityTol=model.Params.FeasibilityTol=model.Params.IntFeasTol=1e-9
                    for suffix in ('lp','mps'):
                        model.write(os.path.relpath(HERE/f'{run.id}.{suffix}'))
                    model.optimize()
                    assert model.Status==GRB.OPTIMAL and model.MIPGap<=1e-9
                    strict_upper,tolerant_upper,_=physical_upper(network,run)
                    previous=next(x for x in prior['all_formal_recertification'] if x['run']==run.id)
                    count,spend,per_scenario,witness_hash=verify_witness(model,network,run,blocks,previous)
                    assert strict_upper==count==EXPECTED[run.id]
                    raw_values=model.getAttr('X')
                    scenario_values=[round(sum(b[-1].getCoeff(i)*raw_values[b[-1].getVar(i).index]
                                              for i in range(b[-1].size()))) for b in blocks]
                    numeric=min(scenario_values)
                    assert strict_upper<=numeric<=tolerant_upper
                    assert abs(model.ObjVal-numeric/network.demand_weight)<=1e-9
                    assert abs(model.ObjBound-model.ObjVal)<=1e-9
                    quality=max(model.ConstrVio,model.BoundVio,model.IntVio)
                    assert quality<=1e-9
                    model.write(os.path.relpath(HERE/f'{run.id}.sol.gz'))
                    rows.append(dict(run=run.id,status='OPTIMAL',seconds=model.Runtime,objective=model.ObjVal,
                                     bound=model.ObjBound,mip_gap=model.MIPGap,numeric_deliveries=numeric,
                                     strict_independent_upper=strict_upper,strict_witness_deliveries=count,
                                     phase16_exact=EXPECTED[run.id],strict_budget_used_rational=spend,
                                     strict_witness_scenarios=per_scenario,exact_max_residual=0,numeric_max_residual=quality,
                                     strict_witness_sha256=witness_hash,raw_capacity_rows_changed=len(changed),
                                     other_model_differences=0,passed=True))
            except AssertionError as exc:
                save_json(HERE/'regression_status.json',dict(status=HOLD,failed_run=run.id,error=repr(exc),completed=rows))
                raise
            csv_file(HERE/'phase16_regression_after_semantic_cleanup.csv',rows)
            print('END',run.id,numeric,'strict',count,flush=True)
    save_json(HERE/'regression_status.json',dict(status='SIX_STRICT_CERTIFICATES_RECONFIRMED',runs=rows,optimizer_calls=6))


if __name__=='__main__':
    main()
