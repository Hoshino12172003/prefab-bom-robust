"""Run only the six Gate 4A cases and the two mandatory midpoint counterparts."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from baseline import Incomplete, ccg, master, memory, oracle
from common import BASELINE, SETTINGS, TOL, bmax, frozen_inputs, gp, write_json


CASES=("G1_MID","G2_MID","G1_ZERO","G2_ZERO","G1_MAX","G2_MAX")


def checkpoint(out,evidence,results):
    for key, rows in evidence.items():
        if rows:
            fields=list(dict.fromkeys(k for r in rows for k in r))
            with (out/f"gate4a_{key}.csv").open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fields,lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
    write_json(out,"gate4a_cases.json",results)


def result(row, scenario, iteration, out, method, evidence):
    for (n,p),q in row["b"].items():
        evidence["first_stage_solutions"].append(dict(run=out,method=method,node=n,item=p,quantity=q))
    return dict(method=method,status="PASS",iterations=iteration,ot=row["ot"],rho=row["ot"]/28000,tau=row["tau"],
        cost_ticks=row["cost_ticks"],cost_usd=row["cost_ticks"]/365000,capital_cents=row["capital_cents"],
        master_scenarios=row["selected_ids"],primary_winner=scenario["winner"],recovery_worst=scenario["recovery_worst"],
        max_residual=max(row["max_residual"],*(r.get("residual",0) for r in scenario["solves"])),
        first_stage_variables=row["first_stage_variables"],variables=row["variables"],constraints=row["constraints"],nonzeros=row["nonzeros"])


def run_case(env,op,nominal,scenarios,case,budget,gamma,out,evidence,results,direct_de):
    started=perf_counter()
    common=dict(case=case,gamma=gamma,budget_cents=budget)
    try:
        row,replay,iterations=ccg(env,op,nominal,scenarios,budget,gamma,case,out,evidence,
                                   lambda:checkpoint(out,evidence,results))
        summary=result(row,replay,iterations,case,"CCG",evidence)
    except Incomplete as error:
        summary=dict(method="CCG",status="INCOMPLETE",stop=error.row)
    except (gp.GurobiError,MemoryError) as error:
        summary=dict(method="CCG",status="RESOURCE_OR_SOLVER_ERROR",stop=str(error))
    results.append(dict(**common,**summary,wall_seconds=perf_counter()-started,peak_rss_bytes=memory()))
    checkpoint(out,evidence,results)
    print(case,"CCG",summary["status"],flush=True)
    if not direct_de or not case.endswith("_MID"):
        return
    started=perf_counter()
    try:
        row=master(env,op,nominal,scenarios,budget,f"{case}_DE",out,evidence,export=gamma==1)
        replay=oracle(env,op,row,scenarios,f"{case}_DE_replay",evidence["final_replay"],audit=True)
        assert replay["reason"]=="CERTIFIED"
        comparator=result(row,replay,1,case,"DIRECT_DE",evidence)
    except Incomplete as error:
        comparator=dict(method="DIRECT_DE",status="INCOMPLETE",stop=error.row)
    except (gp.GurobiError,MemoryError) as error:
        comparator=dict(method="DIRECT_DE",status="RESOURCE_OR_SOLVER_ERROR",stop=str(error))
    results.append(dict(**common,**comparator,wall_seconds=perf_counter()-started,peak_rss_bytes=memory()))
    comparison=dict(case=case,ccg_status=summary["status"],de_status=comparator["status"],match=False)
    if summary["status"]==comparator["status"]=="PASS":
        for k in ("ot","rho","tau","cost_ticks","cost_usd"):
            comparison[f"ccg_{k}"]=summary[k]
            comparison[f"de_{k}"]=comparator[k]
        comparison["match"]=all(summary[k]==comparator[k] for k in ("ot","tau","cost_ticks"))
        comparison["both_first_stages_feasible"]=max(summary["max_residual"],comparator["max_residual"])<=TOL
    evidence["direct_de_comparison"].append(comparison)
    checkpoint(out,evidence,results)
    print(case,"Direct DE",comparator["status"],"match",comparison["match"],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("bundle","xlsb","out"):
        parser.add_argument(f"--{name}",type=Path,required=True)
    parser.add_argument("--cases",nargs="+",choices=CASES,default=CASES)
    parser.add_argument("--ccg-only",action="store_true",help="Retry C&CG cases while preserving existing independent DE runs")
    args=parser.parse_args()
    assert len(args.cases)==len(set(args.cases))
    out=args.out.resolve()
    out.mkdir(parents=True)
    op,nominal,protocol,scenarios,meta=frozen_inputs(args.xlsb,args.bundle)
    evidence,results=defaultdict(list),[]
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile",str(out/"gate4a_gurobi.log"))
        env.start()
        write_json(out,"gate4a_config.json",dict(**meta,cases=args.cases,baseline=BASELINE,
            scenario_counts={g:len(s) for g,s in scenarios.items()},gurobi_default_heuristics=env.getParam("Heuristics"),
            economics_ticks_per_usd=365000,comparison_tolerance=TOL,direct_de_enabled=not args.ccg_only))
        ceiling=bmax(env,op,nominal,protocol,out)
        budget={"ZERO":0,"MID":ceiling//2,"MAX":ceiling}
        for case in args.cases:
            gamma=int(case[1])
            print("starting",case,flush=True)
            run_case(env,op,nominal,scenarios[gamma],case,budget[case[3:]],gamma,out,evidence,results,not args.ccg_only)
    passed=[r for r in results if r["status"]=="PASS"]
    comparisons=evidence["direct_de_comparison"]
    exact=bool(passed) and all(r["status"]=="PASS" for r in results)
    certified=(exact and {r["case"] for r in passed if r["method"]=="CCG"}==set(CASES) and
               {r["case"] for r in comparisons if r["match"] and r["both_first_stages_feasible"]}=={"G1_MID","G2_MID"})
    write_json(out,"gate4a_summary.json",dict(PLAIN_CCG_CERTIFIED=certified,exact_all_attempted=exact,peak_rss_bytes=memory(),
        bmax_cents=ceiling,results=results,comparisons=comparisons))


if __name__=="__main__":
    main()
