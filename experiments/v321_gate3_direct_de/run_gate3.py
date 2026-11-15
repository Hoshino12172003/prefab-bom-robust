"""Solve and replay the frozen finite Gate 3 deterministic equivalents."""

import argparse
import hashlib
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from event_catalog import EVENTS, enumerate_scenarios
from network import Operation, prepare, audit_prep, solve, capital, TOL, CELL
from run_gate2c import PARAMS, sha256, write_csv, write_json
from numerical_certification import identities, stationary_capacities
from prefab_v25.source import load_tables


HERE = Path(__file__).resolve().parent
PR4 = "cc06c06f56f1f7da1562b089fa0c472a3a62b624"
GATE2C = HERE.parent / "v32_gate2c_joint_preparedness/evidence_v321/gate2c_summary.json"
GATE1 = HERE.parent / "v31_gate1_gate2b_certification/numerical/gate1_summary.json"
H = 23
ALPHA = Fraction(1,2)
DELTA = Fraction(1,2)
STORAGE = "technical-bound-only"
BUDGETS = (0, 25_000_000, 100_000_000)
FIXED = {("zp7","BEV"):10, ("zp7","Q1A"):10, ("zp7","Q2J"):10,
         **{("battery-supplier_prod",p):q for p,q in zip(CELL,(20,12,8))}}
SETTINGS = PARAMS | {"TimeLimit":180, "SoftMemLimit":12}


def stats(model):
    return dict(variables=model.NumVars, constraints=model.NumConstrs, integers=model.NumIntVars, nonzeros=model.NumNZs)


def run_replay(env, operation, scenarios, opening, bounds, seat, pool, run, evidence):
    outcomes = {}
    for index,(scenario, multipliers) in enumerate(scenarios.items()):
        with gp.Model(f"{run}_replay_{index}",env=env) as model:
            block = operation.add(model,"replay",multipliers,opening,bounds,seat,pool)
            info = solve(model,block[-1])
            assert info["exact"], (run, scenario, info)
            deliveries, balance, capacity = operation.replay(model,block,opening,bounds,seat,pool,multipliers,
                                                               f"{run}_replay",scenario,evidence)
            assert abs(info["objective"]-deliveries) <= TOL
            outcomes[scenario] = dict(deliveries=deliveries, service=deliveries/operation.demand,
                                      max_balance_residual=balance,max_capacity_violation=capacity,**info)
    return outcomes


def direct(env, operation, nominal, run, scenarios, budget, delta, fixed, out, evidence):
    with gp.Model(run,env=env) as model:
        prep = prepare(model,operation.base,operation.states,H,nominal,ALPHA,delta,STORAGE)
        end, seat, pool, cost = prep[6:]
        for k,var in end.items():
            if fixed is not None:
                var.LB = var.UB = fixed.get(k,0)
        model.addConstr(cost <= budget,name="PreparationCapital")
        opening = model.addVars(operation.states, vtype=GRB.INTEGER,name="CommonOpening60")
        for k in operation.states:
            model.addConstr(opening[k] == operation.initial[k] + end[k],name=f"Opening60[{k[0]},{k[1]}]")
        model.update()
        stage_one = tuple(model.getVars())
        stage_one_ids = {v.index for v in stage_one}
        assert len(stage_one)==len(prep[1])+len(prep[2])+1+len(opening)
        assert all(v.VarName.startswith(("flow[","Ipre[","TerminalCellKit","CommonOpening60[")) for v in stage_one)
        # Scaling rho by the weighted integer demand gives the same maximizer and an integer worst guarantee.
        rho_count = model.addVar(vtype=GRB.INTEGER, ub=operation.demand, name="WorstOnTimeCount")
        operational_limits = prep[3] if run != "nominal_reduction" else {k:(0,0,"") for k in prep[3]}
        bounds = operation.bounds(operational_limits)
        blocks = {}
        for index,(scenario,multipliers) in enumerate(scenarios.items()):
            block = operation.add(model,f"W{index}",multipliers,opening,bounds,seat,pool)
            blocks[scenario] = block
            model.addConstr(block[-1] >= rho_count,name=f"WorstService[{index}]")
        model.setObjective(rho_count,GRB.MAXIMIZE)
        model.update()
        dimensions = stats(model)
        if run == "g1_B250000":
            model.write(str(out/"gate3_representative.lp.gz"))
            model.write(str(out/"gate3_representative.mps.gz"))
        info = solve(model,rho_count)
        if not info["exact"]:
            return dict(run=run,scenario_count=len(scenarios),budget_cents=budget,first_stage_variables=len(stage_one),
                        status="INCOMPLETE",**dimensions,**info)
        worst_ot = round(info["objective"])
        prep_residual, inventory, _ = audit_prep(model,prep,H)
        buffer = {k: round(var.X) for k,var in end.items()}
        opening_solution = {k: round(var.X) for k,var in opening.items()}
        spent = capital(operation,buffer)
        assert abs(cost.getValue()-spent)<=TOL and spent<=budget
        assert budget or all(v==0 for v in buffer.values())
        assert fixed is None or all(buffer[k]==fixed.get(k,0) for k in buffer)
        for (n,p),v in buffer.items():
            assert abs(opening[n,p].X - operation.initial[n,p] - v)<=TOL
            evidence["first_stage_solution"].append(dict(run=run,node=n,item=p,buffer=v,
                regular_opening=operation.initial[n,p],common_state_t60=opening_solution[n,p],capital_used_cents=spent))
        stage_two_ids = set()
        deliveries = {}
        for index,(scenario,block) in enumerate(blocks.items()):
            flow, inv, balances, _ = block
            variables = tuple(flow.values()) + tuple(inv.values())
            ids = {v.index for v in variables}
            assert len(ids)==len(variables) and not ids & stage_one_ids and not ids & stage_two_ids
            stage_two_ids.update(ids)
            assert all(v.VarName.startswith(f"W{index}_") for v in variables)
            common_rows = 0
            start = operation.periods[0]
            for (n,p),shared in opening.items():
                row = model.getRow(balances[n,p,start])
                common = [(row.getVar(i).index,row.getCoeff(i)) for i in range(row.size()) if row.getVar(i).index in stage_one_ids]
                assert common==[(shared.index,-1.0)]
                common_rows += 1
            evidence["nonanticipativity_audit"].append(dict(run=run,scenario=scenario,scenario_count=len(blocks),
                common_first_stage_variables=len(stage_one),scenario_indexed_preparation=0,common_t60_rows=common_rows,
                independent_recourse_variables=len(ids),earliest_recourse_period=min(operation.periods),status="PASS"))
            ot, _, _ = operation.replay(model,block,opening_solution,bounds,seat,pool,scenarios[scenario],run,scenario,evidence)
            assert ot>=worst_ot
            deliveries[scenario] = ot
        assert len(stage_two_ids)+len(stage_one_ids)+1==model.NumVars
        assert min(deliveries.values()) == worst_ot
    replay = run_replay(env,operation,scenarios,opening_solution,bounds,seat,pool,run,evidence)
    worst_replay = min(r["deliveries"] for r in replay.values())
    error = abs(worst_replay-worst_ot)/operation.demand
    for scenario,ot in deliveries.items():
        r = replay[scenario]
        evidence["scenario_service"].append(dict(run=run,scenario=scenario,DE_ot=ot,DE_service=ot/operation.demand,
            replay_ot=r["deliveries"],replay_service=r["service"],binding_in_DE=ot==worst_ot,
            worst_in_independent_replay=r["deliveries"]==worst_replay))
        target = "fixed_b_equivalence" if fixed is not None else "optimized_replay"
        evidence[target].append(dict(run=run,scenario=scenario,rho_DE=worst_ot/operation.demand,
            independent_worst=worst_replay/operation.demand,absolute_error=error,**r))
    print(run,len(scenarios),worst_ot,worst_replay,info["runtime_seconds"],flush=True)
    return dict(run=run,scenario_count=len(scenarios),budget_cents=budget,first_stage_variables=len(stage_one),
        prep_residual=prep_residual,capital_used_cents=spent,rho=worst_ot/operation.demand,
        worst_scenarios=[s for s,r in replay.items() if r["deliveries"]==worst_replay],
        binding_scenarios=[s for s,q in deliveries.items() if q==worst_ot],
        replay_error=error,status="PASS" if error<=TOL else "FAIL",**dimensions,**info)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsb",type=Path,required=True)
    parser.add_argument("--bundle",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    started = perf_counter()
    out = args.out.resolve()
    out.mkdir(parents=True)
    frozen = json.loads(GATE2C.read_bytes())
    assert frozen["READY_FOR_GATE3"] and set(frozen["prior_gate_status"].values())=={"PASS"}
    assert set(frozen["checks"].values())=={"PASS"} and frozen["EMPIRICAL_RESIDUAL_CAPACITY"]=="NOT_IDENTIFIED"
    tables = load_tables(args.xlsb)
    base,states,metadata = identities(tables,args.bundle,args.xlsb)
    operation = Operation(base,states)
    assert operation.demand==28000 and len(operation.groups)==1286 and len(base.network.historical)==117
    _, capacity = stationary_capacities(tables,Fraction(1))
    nominal = {(r["origin"],r["destination"]): Fraction(r["stationary_nominal_exact"]) for r in capacity}
    write_json(out,"gate3_config.json",dict(**metadata,settings=SETTINGS,baseline=PR4,
        prerequisite_sha256=sha256(GATE2C), code_sha256={p.name:sha256(p) for p in HERE.glob("*.py")},
        H=H,alpha=str(ALPHA),delta=str(DELTA),storage=STORAGE,budget_cents=BUDGETS,
        budget_evidence="CERTIFICATION_SCENARIO",fixed_buffer=[[*k,q] for k,q in FIXED.items()],
        empirical_residual_capacity="NOT_IDENTIFIED",service_denominator=operation.demand,
        objective="maximize integer weighted on-time count; rho=count/denominator"))
    catalog = []
    for event in EVENTS:
        assert event.asset in operation.arcs and event.start in operation.periods
        profile = event.profile(operation.periods)
        catalog.append(dict(event_id=event.id,asset="->".join(event.asset),asset_type=event.asset_type,start=event.start,
            duration=event.duration,severity=str(1-event.availability),disruption_availability=str(event.availability),
            recovery=event.recovery,affected_periods=";".join(str(k[-1]) for k in profile),
            capacity_multiplier_by_period=json.dumps({t:str(profile.get((*event.asset,t),1)) for t in operation.periods}),
            has_window_arrival=any(i==event.asset[0] and j==event.asset[1] and (i,j,t) in profile for i,j,_,t in operation.keys),
            evidence_type="CERTIFICATION_SCENARIO"))
    write_csv(out,"event_catalog.csv",catalog)
    risk, catalog_rows, mappings, counts = {}, [], [], {}
    for gamma in (1,2):
        risk[gamma], mapping = enumerate_scenarios(EVENTS,gamma,operation.nominal,operation.periods)
        mappings.extend(mapping)
        counts[gamma] = dict(raw=len(mapping),legal=sum(r["compatibility"]=="LEGAL" for r in mapping),
                             deduplicated=len(risk[gamma]))
        for s, profile in risk[gamma].items():
            trajectory = [(*k,str(profile.get(k,1))) for k in sorted(operation.nominal)]
            catalog_rows.append(dict(gamma=gamma,scenario=s,event_count=0 if s=="NOM" else len(s.split("+")),
                trajectory_sha256=hashlib.sha256(json.dumps(trajectory).encode()).hexdigest(),
                affected_asset_periods=json.dumps([(*k,str(m)) for k,m in sorted(profile.items())])))
    write_csv(out,"gate3_scenario_catalog.csv",catalog_rows)
    write_csv(out,"gate3_scenario_dedup_map.csv",mappings)
    assert counts=={1:dict(raw=9,legal=9,deduplicated=9),2:dict(raw=37,legal=36,deduplicated=36)}
    jobs = [("nominal_reduction",0,0,Fraction(0),None),("fixed_b_G1",1,BUDGETS[1],DELTA,FIXED),
            ("g1_B0",1,0,DELTA,None),("g1_B250000",1,BUDGETS[1],DELTA,None),
            ("g1_B1000000",1,BUDGETS[2],DELTA,None),("g2_B1000000",2,BUDGETS[2],DELTA,None)]
    evidence, results = defaultdict(list),[]
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile", str(out/"gate3_gurobi.log"))
        env.start()
        for run,gamma,budget,delta,fixed in jobs:
            print("starting",run,flush=True)
            result = direct(env,operation,nominal,run,risk[gamma] if gamma else {"NOM":{}},budget,delta,fixed,out,evidence)
            results.append(dict(gamma=gamma,**result))
            write_json(out,"gate3_job_progress.json",results)
    for key, records in evidence.items():
        write_csv(out,f"gate3_{key}.csv",records)
    jobs_by_id = {r["run"]:r for r in results}
    nominal_target = next(r["objective"] for r in json.loads(GATE1.read_bytes())["cases"] if r["case"]=="technical_bound")
    exact = all(r["exact"] for r in results)
    checks = {
        "G3-01":jobs_by_id["nominal_reduction"]["exact"] and jobs_by_id["nominal_reduction"]["objective"]==nominal_target,
        "G3-02":jobs_by_id["fixed_b_G1"]["status"]=="PASS",
        "G3-03":all(r["status"]=="PASS" for r in results if r["run"].startswith("g")),
        "G3-04":exact and len({r["first_stage_variables"] for r in results})==1,
        "G3-05":exact,"G3-06":exact,"G3-07":exact,"G3-08":exact,"G3-09":True,"G3-10":exact,
    }
    passed = all(checks.values())
    write_json(out,"gate3_summary.json",dict(GATE3_DIRECT_DE="PASS" if passed else "INCOMPLETE",READY_FOR_GATE4=passed,
        checks={k:"PASS" if v else "NOT_CERTIFIED" for k,v in checks.items()},nominal_gate1_on_time=nominal_target,
        event_count=len(EVENTS),scenario_counts=counts,results=results,runtime_seconds=perf_counter()-started))


if __name__ == "__main__":
    main()
