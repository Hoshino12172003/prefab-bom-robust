"""Certify the V3.3 finite-scenario recovery extension without changing Gate 3."""

import argparse
import csv
import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
GATE3 = HERE.parent / "v321_gate3_direct_de"
GATE35 = HERE.parent / "v321_gate35_risk_effectiveness/evidence"
sys.path.insert(0,str(GATE3))
from run_gate3 import H, ALPHA, DELTA, STORAGE, SETTINGS, Operation, direct, prepare, audit_prep
from event_catalog import Event, enumerate_scenarios
from network import COST, CELL, TOL, solve_info, capital
from recovery import Recovery, backlog_series
from run_gate2c import sha256, write_csv, write_json
from numerical_certification import identities, stationary_capacities
from prefab_v25.source import load_tables


BASELINE = "0d651ec05d8bb53846d1e42f3725a16bc3368e2c"
REFERENCE_BUDGET = 25_000_000


def frozen_events():
    gate35 = json.loads((GATE35/"gate35_summary.json").read_bytes())
    assert gate35["GATE3_DIRECT_DE"] == "PASS"
    events = [Event(r["event"],tuple(r["asset"]),"production",r["start"],r["duration"],Fraction(r["availability"]),r["recovery"])
              for r in gate35["selected_events"]]
    with (GATE35/"gate35_event_thresholds.csv").open(encoding="utf-8") as f:
        candidates = [r for r in csv.DictReader(f) if r["resource"] in ("ENGINE_PROD","GEAR_OEM") and
                      r["first_effective_threshold"] == "True"]
    chosen = min(candidates,key=lambda r:(int(r["duration"]),-Fraction(r["availability"]),r["resource"]))
    events.append(Event(chosen["event"],tuple(chosen["asset"].split("->")),
                        "transport" if chosen["resource"]=="GEAR_OEM" else "production", int(chosen["start"]),
                        int(chosen["duration"]),Fraction(chosen["availability"]),int(chosen["recovery"])))
    assert [e.id for e in events]==["BAT_PROD_D5_A20","SEAT_PROD_D1_A40","GEAR_OEM_D2_A20"]
    return events


def exact_level(model, expr, sense, run, level, evidence):
    model.setObjective(expr,sense)
    model.optimize()
    info = solve_info(model)
    exact = (model.Status==GRB.OPTIMAL and info["mip_gap"]==0 and
             abs(info["objective"]-info["best_bound"])<=TOL and
             max(info[k] for k in ("model_row_violation","model_bound_violation","integrality_error"))<=TOL)
    row = dict(run=run,level=level,sense="MAX" if sense==GRB.MAXIMIZE else "MIN",exact=exact,**info)
    evidence["lexicographic_objective_audit"].append(row)
    print(run,level,row["solver_status"],row["objective"],row["best_bound"],row["runtime_seconds"],flush=True)
    return row


def lex_de(env, op, nominal, scenarios, label, budget, out, evidence, primary_only=False):
    with gp.Model(label,env=env) as model:
        prep = prepare(model,op.base,op.states,H,nominal,ALPHA,DELTA,STORAGE)
        end,seat,pool,materials = prep[6:]
        model.addConstr(materials<=budget,name="PreparationCapital")
        common = model.addVars(op.states,vtype=GRB.INTEGER,name="CommonOpening60")
        for k in op.states:
            model.addConstr(common[k]==op.initial[k]+end[k])
        model.update()
        pre = {v.index for v in model.getVars()}
        assert len(pre)==len(prep[1])+len(prep[2])+len(common)+1
        rho = model.addVar(vtype=GRB.INTEGER,ub=op.demand,name="WorstOnTimeCount")
        tau = model.addVar(vtype=GRB.INTEGER,ub=op.maximum_backlog,name="WorstOrderPeriodBacklog")
        # A cost envelope can be continuous. At its minimizer it is the
        # maximum of integer-valued holding sums from the physical plans.
        worst_hold = model.addVar(name="WorstHoldingCentsPeriods")
        bounds = op.bounds(prep[3])
        blocks = {}
        for index,(scenario,profile) in enumerate(scenarios.items()):
            block = op.add_recovery(model,f"W{index}",profile,common,bounds,seat,pool)
            blocks[scenario] = block
            ot,area,holding = block[-3:]
            model.addConstr(ot>=rho,name=f"OTGuarantee_{index}")
            model.addConstr(area<=tau,name=f"BacklogGuarantee_{index}")
            model.addConstr(holding<=worst_hold,name=f"HoldingEnvelope_{index}")
        # 1/3650 converts summed inventory cents-days into cents at 10%/year.
        prep_hold=gp.quicksum(COST[op.states[n,p][0]]*v for (n,p,t),v in prep[2].items() if p not in CELL)
        costs=3650*materials + prep_hold + worst_hold
        result=dict(run=label,scenario_count=len(scenarios),first_stage_variables=len(pre),budget_cents=budget)
        one = exact_level(model,rho,GRB.MAXIMIZE,label,"service",evidence)
        result.update(on_time=one["objective"],rho=None if one["objective"] is None else one["objective"]/op.demand,
                      variables=model.NumVars,constraints=model.NumConstrs,nonzeros=model.NumNZs)
        if not one["exact"] or primary_only:
            return dict(result,status="PASS_PRIMARY" if one["exact"] else "INCOMPLETE")
        guaranteed = round(one["objective"])
        rho.LB=rho.UB=guaranteed
        two = exact_level(model,tau,GRB.MINIMIZE,label,"backlog",evidence)
        if not two["exact"]:
            return dict(result,status="INCOMPLETE",tau=two["objective"])
        burden = round(two["objective"])
        tau.LB=tau.UB=burden
        three = exact_level(model,costs,GRB.MINIMIZE,label,"economics",evidence)
        if not three["exact"]:
            return dict(result,status="INCOMPLETE",tau=burden)
        if label=="gamma2":
            model.write(str(out/"gate36_representative.lp.gz"))
            model.write(str(out/"gate36_representative.mps.gz"))
        opening = {k:round(v.X) for k,v in common.items()}
        buffer = {k:round(v.X) for k,v in end.items()}
        prep_error,_,_=audit_prep(model,prep,H)
        spent=capital(op,buffer)
        assert spent<=budget and abs(spent-materials.getValue())<=TOL
        assert all(abs(common[k].X-op.initial[k]-end[k].X)<=TOL for k in common)
        recourse = set()
        metrics=[]
        for index,(scenario,block) in enumerate(blocks.items()):
            variables=tuple(v for group in block[:4] for v in group.values())
            ids={v.index for v in variables}
            assert len(ids)==len(variables) and not ids & pre and not ids & recourse
            recourse.update(ids)
            for n,p in common:
                row=model.getRow(block[4][n,p,op.periods[0]])
                assert [(row.getVar(i).index,row.getCoeff(i)) for i in range(row.size()) if row.getVar(i).index in pre] == [(common[n,p].index,-1)]
            evidence["nonanticipativity_audit"].append(dict(run=label,scenario=scenario,common_first_stage=len(pre),
                stage_one_scenario_copies=0,common_opening_rows=len(common),scenario_variables=len(ids),tail_starts=75,status="PASS"))
            r=op.replay(model,block,opening,bounds,seat,pool,scenarios[scenario],label,scenario,evidence)
            assert r["on_time"]>=guaranteed and r["backlog_area"]<=burden
            evidence["scenario_metrics"].append(dict(run=label,scenario=scenario,**r))
            metrics.append(r)
        assert len(recourse)+len(pre)+3==model.NumVars
        assert min(r["on_time"] for r in metrics)==guaranteed and max(r["backlog_area"] for r in metrics)==burden
        assert abs(three["objective"]/365000-(spent/100+prep_hold.getValue()/365000+max(r["holding_usd"] for r in metrics)))<=TOL
        return dict(result,status="PASS",tau=burden,material_capital_usd=spent/100,prep_holding_usd=prep_hold.getValue()/365000,
                    worst_recourse_holding_usd=max(r["holding_usd"] for r in metrics),economic_cost_usd=three["objective"]/365000,
                    prep_residual=prep_error,buffers=[[*k,q] for k,q in buffer.items() if q])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for item in ("xlsb","bundle","out"):
        p.add_argument("--"+item,type=Path,required=True)
    args=p.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True)
    start=perf_counter()
    tables=load_tables(args.xlsb)
    base,states,metadata=identities(tables,args.bundle,args.xlsb)
    op=Recovery(base,states)
    old=Operation(base,states)
    assert op.demand==old.demand==28000 and op.due==old.due and set(op.ott)=={k for k in old.keys if k[:2]==("zp7","zp8")}
    assert all(op.nominal[k]==v for k,v in old.nominal.items()) and all(op.history[k]==v for k,v in old.history.items())
    assert op.periods[-1]>=max(t+op.arcs[i,j].lead for i,j,_,t,_ in base.network.historical)
    write_csv(out,"gate36_clearance_paths.csv",op.path_rows)
    write_csv(out,"gate36_historical_pipeline.csv",[dict(node=n,item=p,arrival=t,quantity=q,tail=t>74) for (n,p,t),q in sorted(op.history.items())])
    _,capacity=stationary_capacities(tables,Fraction(1))
    nominal={(r["origin"],r["destination"]):Fraction(r["stationary_nominal_exact"]) for r in capacity}
    events=frozen_events()
    profiles={e.id:e.profile(op.periods) for e in events}
    scenarios, mapping={},[]
    for gamma in (0,1,2):
        scenarios[gamma],m=enumerate_scenarios(events,gamma,op.nominal,op.periods)
        mapping.extend(m)
    write_csv(out,"gate36_scenario_catalog.csv",[dict(gamma=g,scenario=s,asset_period_profile=json.dumps([(*k,str(v)) for k,v in sorted(profile.items())]))
                                                 for g,collection in scenarios.items() for s,profile in collection.items()])
    write_csv(out,"gate36_scenario_map.csv",mapping)
    write_json(out,"gate36_config.json",dict(**metadata,baseline=BASELINE,code_sha256={p.name:sha256(p) for p in HERE.glob("*.py")},
        gate35_threshold_sha256=sha256(GATE35/"gate35_event_thresholds.csv"),settings=SETTINGS,H=H,alpha=str(ALPHA),delta=str(DELTA),
        demand_periods=op.demand_periods,recourse_periods=op.periods,tail_nominal_rule="CYCLIC_SOURCE_ARC_CAPACITY_14",
        longest_lead=max(r["lead"] for r in op.path_rows),epsilon_service=0,epsilon_backlog=0,holding_rate="1/10",
        holding_periods_per_year=365,position_cost="V31_BASE_ZERO",capacity_expansion="DISABLED",cell_inventory_holding="NOT_IDENTIFIED",
        operating_cost="NOT_IDENTIFIED",certification_budget_cents=0,positive_regression_budget_cents=REFERENCE_BUDGET))
    evidence=defaultdict(list)
    runs, regression=[],[]
    pair_id="+".join(e.id for e in events[:2])
    pair_profiles,_=enumerate_scenarios(events[:2],1,op.nominal,op.periods)
    expected_pair=next(r["on_time"] for r in json.loads((GATE35/"gate35_summary.json").read_bytes())["gamma"]
                       if r["gamma"]==1 and r["budget_usd"]==250000)
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile",str(out/"gate36_gurobi.log"))
        env.start()
        for g in (0,1,2):
            label=f"gamma{g}"
            old_result=direct(env,old,nominal,"short_"+label,scenarios[g],0,DELTA,None,out,defaultdict(list))
            assert old_result["exact"] and old_result["status"]=="PASS"
            r=lex_de(env,op,nominal,scenarios[g],label,0,out,evidence)
            runs.append(r)
            regression.append(dict(run=label,old=old_result["objective"],extended=r["on_time"],match=r["on_time"]==old_result["objective"]))
            write_json(out,"gate36_progress.json",runs)
        for label,sc in (("fixed_BAT",events[0].id),("fixed_BAT_SEAT",pair_id)):
            runs.append(lex_de(env,op,nominal,{sc:scenarios[2][sc]},label,0,out,evidence))
        r=lex_de(env,op,nominal,pair_profiles,"positive_primary",REFERENCE_BUDGET,out,evidence,primary_only=True)
        runs.append(r)
        regression.append(dict(run=r["run"],old=expected_pair,extended=r["on_time"],match=r["on_time"]==expected_pair))
    for k,rs in evidence.items():
        write_csv(out,f"gate36_{k}.csv",rs)
    write_csv(out,"gate36_primary_regression.csv",regression)
    if evidence["scenario_metrics"]:
        write_csv(out,"gate36_terminal_backlog.csv",[{k:r[k] for k in ("run","scenario","terminal_backlog")} for r in evidence["scenario_metrics"]])
    pre=[r for r in runs if r["run"]!="positive_primary"]
    metrics=evidence["scenario_metrics"]
    full=all(r["status"]=="PASS" for r in pre)
    all_exact=all(r["exact"] for r in evidence["lexicographic_objective_audit"])
    tail_test=(sum(backlog_series(1,74,{},97))==24 and backlog_series(1,74,{},97)[-1]==1)
    delay_test=(sum(backlog_series(1,74,{76:1},97))-sum(backlog_series(1,74,{75:1},97))==1)
    choice_test=(sum(backlog_series(2,74,{74:1,75:1},97))<sum(backlog_series(2,74,{74:1,77:1},97)))
    gamma_order=full and all((-a["rho"],a["tau"])<=(-b["rho"],b["tau"]) for a,b in zip(runs[:2],runs[1:3]))
    checks={"G36-01": all(r["match"] for r in regression),"G36-02":full,
            "G36-03":full and max(r["backlog_identity_error"] for r in metrics)<=TOL,
            "G36-04":tail_test,"G36-05":delay_test,"G36-06":choice_test,
            "G36-07":full and len({r["first_stage_variables"] for r in pre})==1,"G36-08":full,
            "G36-09":full and max(r[k] for r in metrics for k in ("max_balance_residual","max_capacity_violation","max_inventory_violation"))<=TOL,
            "G36-10":all_exact}
    write_json(out,"gate36_summary.json",dict(V33_RECOVERY_OBJECTIVE_CERTIFIED=all(checks.values()) and gamma_order,
        checks={k:"PASS" if v else "NOT_CERTIFIED" for k,v in checks.items()},gamma_lex_monotonic=gamma_order,
        tail_length=len(op.periods)-len(op.demand_periods),end=op.periods[-1],scenario_counts={g:len(s) for g,s in scenarios.items()},
        results=runs,primary_regression=regression,runtime_seconds=perf_counter()-start))


if __name__=="__main__":
    main()
