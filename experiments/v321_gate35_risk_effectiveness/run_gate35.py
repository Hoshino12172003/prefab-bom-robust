"""Execute the independent Gate 3.5 risk diagnostics on the frozen Gate 3 model."""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import gurobipy as gp

HERE = Path(__file__).resolve().parent
GATE3 = HERE.parent / "v321_gate3_direct_de"
sys.path.insert(0, str(GATE3))
from run_gate3 import H, ALPHA, DELTA, STORAGE, SETTINGS, direct, prepare, Operation, identities, stationary_capacities
from event_catalog import EVENTS, enumerate_scenarios
from audits import battery_cut, nominal_bottlenecks, period_effect, recourse
from network import ASSEMBLY, TOL
from run_gate2c import sha256, write_csv, write_json
from prefab_v25.source import load_tables


BASELINE = "c4dc91ddec1f306f50aa8473b6e739ba471c6372"
SCAN_IDS = ("BAT_PROD", "BAT_OEM", "SEAT_PROD", "ENGINE_PROD", "GEAR_OEM")
AVAILABILITY = tuple(map(Fraction, ("1.0", "0.8", "0.6", "0.4", "0.2", "0.0")))
DURATION = (1, 2, 3, 5, 7)
BUDGET_USD = (0, 50_000, 100_000, 150_000, 200_000, 250_000, 500_000, 1_000_000)
GAMMA_BUDGETS = (0, 250_000)
SELECTION_RULE = "In fixed asset order, retain first two effective events on different BOM branches. Per asset use shortest effective duration, then highest effective availability."


def gate3_policy(run):
    with (GATE3 / "evidence/gate3_first_stage_solution.csv").open(encoding="utf-8") as source:
        b = {(r["node"], r["item"]): int(r["buffer"]) for r in csv.DictReader(source) if r["run"] == run}
    assert len(b) == 91
    return b


def evaluate_original(env, op, bounds, seat, pool, policies, nominal_plans):
    items, details = [], []
    for name, b in policies.items():
        nom, _, _, usage_nom, delivered_nom = nominal_plans[name]
        for e in EVENTS:
            result, _, _, usage, delivered = recourse(env, op, bounds, seat, pool, b, e.profile(op.periods), f"{name}_{e.id}")
            period_rows = list(period_effect(op, e, usage_nom, usage))
            delta = result["on_time"]-nom["on_time"]
            assert delta <= 0
            horizon = any(r["horizon_eligible"] for r in period_rows)
            excluded = any(r["nominal_witness_excluded"] for r in period_rows)
            reason = ("SERVICE_LOSS" if delta else "NO_ARRIVAL_IN_OPERATING_WINDOW" if not horizon else
                      "NOMINAL_PLAN_EXCLUDED_BUT_REOPTIMIZATION_PRESERVES_SERVICE" if excluded else
                      "NOMINAL_PLAN_REMAINS_FEASIBLE")
            items.append(dict(policy=name, event=e.id, asset="->".join(e.asset), duration=e.duration,
                affected_periods=";".join(str(r["period"]) for r in period_rows), has_window_arrival=horizon,
                delta_on_time=delta, delta_service=delta/op.demand, service_changes=bool(delta),
                nominal_witness_excluded=excluded, disruption_binds=any(r["disruption_binds"] for r in period_rows),
                delivery_plan_changes=delivered != delivered_nom, reason=reason, **result))
            details.extend(dict(policy=name, event=e.id, asset="->".join(e.asset), **r) for r in period_rows)
    return items, details


def threshold_scan(env, op, bounds, seat, pool, nominal_plan):
    events = {e.id:e for e in EVENTS}
    nom, _, _, usage_nom, _ = nominal_plan
    rows, selected, branches = [], [], set()
    for event_id in SCAN_IDS:
        e = events[event_id]
        candidate = None
        for duration in DURATION:
            first = False
            previous = nom["on_time"]
            for available in AVAILABILITY:
                label = f"{event_id}_D{duration}_A{int(available*100)}"
                event = replace(e,id=label,duration=duration,availability=available)
                result, _, _, usage, _ = recourse(env, op, bounds, seat, pool, {}, event.profile(op.periods), label)
                assert result["on_time"] <= previous
                previous = result["on_time"]
                delta = result["on_time"]-nom["on_time"]
                threshold = delta < 0 and not first
                if threshold:
                    first = True
                    if candidate is None:
                        candidate = event
                periods = list(period_effect(op, event, usage_nom, usage))
                tight = [r["period"] for r in periods if r["disruption_binds"]]
                rows.append(dict(event=label, resource=event_id, asset="->".join(event.asset), start=event.start,
                    duration=duration, availability=float(available), recovery=event.recovery,
                    delta_on_time=delta, delta_service=delta/op.demand,
                    binding_resource="->".join(event.asset) if tight else "",
                    binding_periods=";".join(map(str,tight)), first_effective_threshold=threshold,
                    evidence_type="DIAGNOSTIC_SCENARIO", **result))
        branch = event_id.split("_")[0]
        if candidate is not None and branch not in branches and len(selected) < 2:
            selected.append(candidate)
            branches.add(branch)
        print("threshold grid complete",event_id,flush=True)
    return rows, selected


def optimize_diagnostics(env, op, nominal, selected, output):
    if len(selected) < 2:
        return [], [], {}, [], defaultdict(list)
    evidence = defaultdict(list)
    gamma = {g: enumerate_scenarios(selected,g,op.nominal,op.periods) for g in (0,1,2)}
    solutions = {}
    for g, b in [(1,b) for b in BUDGET_USD] + [(g,b) for b in GAMMA_BUDGETS for g in (0,2)]:
        tag = f"diagnostic_G{g}_B{b}"
        result = direct(env, op, nominal, tag, gamma[g][0], b*100, DELTA, None, output, evidence)
        assert result["status"] == "PASS" and result["exact"], result
        solutions[g,b] = result
    chosen = defaultdict(list)
    for r in evidence["first_stage_solution"]:
        if r["buffer"]:
            chosen[r["run"]].append(dict(node=r["node"],item=r["item"],form=op.states[r["node"],r["item"]][0],quantity=r["buffer"]))
    budget_rows = []
    prior = None
    for b in BUDGET_USD:
        result = solutions[1,b]
        value = round(result["objective"])
        assert prior is None or value >= prior
        cost = result["capital_used_cents"]
        budget_rows.append(dict(budget_usd=b, rho=result["rho"], on_time=value, capital_used_usd=cost/100,
            capital_slack_usd=(b*100-cost)/100, budget_binding=b*100==cost,
            marginal_on_time_gain="" if prior is None else value-prior,
            marginal_service_gain="" if prior is None else (value-prior)/op.demand,
            chosen_buffer_form_and_position=json.dumps(chosen[result["run"]]),
            worst_scenarios=";".join(result["worst_scenarios"]), gap=result["mip_gap"], evidence_type="DIAGNOSTIC_SCENARIO"))
        prior = value
    gamma_rows = []
    for b in GAMMA_BUDGETS:
        ordered = [solutions[g,b]["rho"] for g in (0,1,2)]
        assert ordered[2] <= ordered[1] <= ordered[0]
        for g in (0,1,2):
            r = solutions[g,b]
            gamma_rows.append(dict(budget_usd=b,gamma=g,scenarios=r["scenario_count"],on_time=round(r["objective"]),
                rho=r["rho"],worst_scenarios=";".join(r["worst_scenarios"]),capital_used_usd=r["capital_used_cents"]/100,
                strict_drop_G2_vs_G1=ordered[2]<ordered[1],gap=r["mip_gap"],evidence_type="DIAGNOSTIC_SCENARIO"))
    return budget_rows, gamma_rows, solutions, [r for _,m in gamma.values() for r in m], evidence


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--xlsb",type=Path,required=True)
    cli.add_argument("--bundle",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args = cli.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True)
    started = perf_counter()
    archive = json.loads((GATE3/"evidence/gate3_summary.json").read_bytes())
    assert archive["GATE3_DIRECT_DE"] == "PASS"
    tables = load_tables(args.xlsb)
    base, states, metadata = identities(tables,args.bundle,args.xlsb)
    op = Operation(base,states)
    _, capacities = stationary_capacities(tables,Fraction(1))
    nominal = {(r["origin"],r["destination"]):Fraction(r["stationary_nominal_exact"]) for r in capacities}
    zero = gate3_policy("g1_B0")
    positive = gate3_policy("g1_B250000")
    assert not any(zero.values()) and positive==gate3_policy("g1_B1000000")
    write_json(out,"gate35_config.json",dict(**metadata, baseline=BASELINE, code_sha256={p.name:sha256(p) for p in HERE.glob("*.py")},
        frozen_gate3_sha256={p:sha256(GATE3/"evidence"/p) for p in ("gate3_summary.json","gate3_first_stage_solution.csv","event_catalog.csv")},
        H=H,alpha=str(ALPHA),delta=str(DELTA),storage=STORAGE, availability=[str(a) for a in AVAILABILITY],
        duration=DURATION, budget_usd=BUDGET_USD, gamma_budget_usd=GAMMA_BUDGETS, settings=SETTINGS,
        selection_rule=SELECTION_RULE, evidence_type="DIAGNOSTIC_SCENARIO"))
    cut = battery_cut(op,nominal,ALPHA,H)
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile",str(out/"gate35_gurobi.log"))
        env.start()
        with gp.Model("gate35_preparation_bounds",env=env) as model:
            prep = prepare(model,base,states,H,nominal,ALPHA,DELTA,STORAGE)
            seat, pool = prep[7:9]
            bounds = op.bounds(prep[3])
            strict_bounds = op.bounds({k:(0,0,"") for k in prep[3]})
        baseline = recourse(env,op,strict_bounds,seat,0,zero,{},"strict_nominal_zero")
        plans = {"zero":recourse(env,op,bounds,seat,pool,zero,{},"nominal_zero_same_pool"),
                 "gate3_positive":recourse(env,op,bounds,seat,pool,positive,{},"nominal_gate3_positive")}
        assert baseline[0]["on_time"]==plans["zero"][0]["on_time"]==cut["nominal_on_time_bound"]
        assert plans["gate3_positive"][0]["on_time"]==cut["positive_on_time_bound"]
        bottlenecks = list(nominal_bottlenecks(op,strict_bounds,seat,0,baseline,"strict_nominal_zero"))
        bottlenecks.extend(nominal_bottlenecks(op,bounds,seat,pool,plans["gate3_positive"],"gate3_positive"))
        write_csv(out,"gate35_nominal_bottlenecks.csv",bottlenecks)
        rows = []
        for name, plan in [("strict_nominal_zero",baseline),("gate3_positive",plans["gate3_positive"])]:
            grouped = Counter()
            for (g,t),q in plan[-1].items():
                family = "BEV" if ("BEV",1) in op.groups[g].representative.bom else "nonBEV"
                grouped[op.due[g],family] += round(q)
            for due in op.periods:
                for family in ("BEV","nonBEV"):
                    demand = sum(len(g.orders) for g in op.groups.values() if g.representative.due==due and
                                 (("BEV",1) in g.representative.bom)==(family=="BEV"))
                    delivered = grouped[due,family]
                    rows.append(dict(policy=name,due=due,family=family,demand=demand,on_time=delivered,shortfall=demand-delivered))
        write_csv(out,"gate35_due_cohorts.csv",rows)
        for name, required in (("strict_nominal_zero",cut["nominal_bev_bound"]),("gate3_positive",cut["nominal_bev_bound"]+cut["prep_kit_bound"])):
            assert sum(r["on_time"] for r in rows if r["policy"]==name and r["family"]=="BEV")==required
        impacts, details = evaluate_original(env,op,bounds,seat,pool,{"zero":zero,"gate3_positive":positive},plans)
        write_csv(out,"gate35_event_impacts.csv",impacts)
        write_csv(out,"gate35_event_period_impacts.csv",details)
        thresholds, selected = threshold_scan(env,op,bounds,seat,pool,plans["zero"])
        write_csv(out,"gate35_event_thresholds.csv",thresholds)
        budgets, gamma_rows, solutions, mapping, evidence = optimize_diagnostics(env,op,nominal,selected,out)
    if budgets:
        write_csv(out,"gate35_budget_response.csv",budgets)
        write_csv(out,"gate35_gamma_diagnostic.csv",gamma_rows)
        write_csv(out,"gate35_diagnostic_scenario_map.csv",mapping)
        for key, records in evidence.items():
            write_csv(out,f"gate35_diagnostic_{key}.csv",records)
    original_effect = any(r["service_changes"] for r in impacts)
    nonnom_worst = any("NOM" not in r["worst_scenarios"] for r in gamma_rows)
    strict_gamma = any(r["strict_drop_G2_vs_G1"] for r in gamma_rows)
    ready = len(selected)>=2 and nonnom_worst and strict_gamma
    write_json(out,"gate35_summary.json",dict(GATE3_DIRECT_DE=archive["GATE3_DIRECT_DE"],
        original_catalog_discriminative=original_effect, RISK_SET_DISCRIMINATIVE=ready,
        risk_set_scope="Gate 3.5 selected diagnostic event pair", recommend_gate4=ready, battery_material_cut=cut,
        original_events={p:{r["event"]:r["delta_on_time"] for r in impacts if r["policy"]==p} for p in plans},
        nominal_solves={"strict_nominal_zero":baseline[0], **{k:r[0] for k,r in plans.items()}},
        threshold_cases=len(thresholds), effective_threshold_cases=sum(r["delta_on_time"]<0 for r in thresholds),
        selected_events=[dict(event=e.id,asset=list(e.asset),start=e.start,duration=e.duration,
                              availability=str(e.availability),recovery=e.recovery) for e in selected],
        gamma_strict=strict_gamma, nonnominal_worst=nonnom_worst, budgets=budgets,gamma=gamma_rows,
        de_results=list(solutions.values()), runtime_seconds=perf_counter()-started))


if __name__ == "__main__":
    main()
