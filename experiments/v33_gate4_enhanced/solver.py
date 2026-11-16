"""Exact dominant-cover and feasibility-bound variants of the Gate 4A solver."""

import math
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter

EXPERIMENTS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(EXPERIMENTS / folder) for folder in ("v33_gate4a_plain_ccg","v33_gate4_dominance")]
import baseline
from audit import capacity_vectors, certify_cover
from common import GRB, TOL, dimensions, gp, solve_info


METHODS = ("plain", "dominance", "bounds", "combined")


def physical_state(solution):
    # These are all the first-stage inputs to Recovery.add_recovery, rather than
    # just the inventory policy vector. A cache is scoped to one frozen run.
    return (tuple(sorted(solution["opening"].items())), tuple(sorted(solution["bounds"].items())),
            tuple(sorted(solution["seat"])), solution["pool"])


def meets(witness, thresholds):
    ot, area, holding = witness
    min_ot, max_area, max_holding = thresholds
    return ot >= min_ot and area <= max_area and holding <= max_holding


def replay_holding(op, model, block):
    stocks = model.getAttr("X",block[3])
    return sum(baseline.COST[op.states[n,p][0]]*round(val) for (n,p,_),val in stocks.items() if p not in baseline.CELL)


def feasibility(env, op, solution, scenario, profile, thresholds, label, rows):
    started = perf_counter()
    with gp.Model(f"{label}_{scenario}_threshold",env=env) as model:
        args = [solution[k] for k in ("opening","bounds","seat","pool")]
        block = op.add_recovery(model,"R",profile,*args)
        ot, area, holding = block[-3:]
        floor, ceiling, cost = thresholds
        model.addConstr(ot >= floor)
        model.addConstr(area <= ceiling)
        model.addConstr(holding <= cost)
        model.setObjective(0)
        model.optimize()
        info = solve_info(model)
        if info["mip_gap"] is not None and not math.isfinite(info["mip_gap"]):
            info["mip_gap"] = "Infinity"
        row = dict(run=label, scenario=scenario, thresholds=thresholds, **dimensions(model), **info)
        row["wall_seconds"] = perf_counter()-started
        rows.append(row)
        if model.Status == GRB.INFEASIBLE:
            row["certificate"] = "THRESHOLDS_INFEASIBLE"
            return None
        if not model.SolCount or max(info[k] for k in
                ("model_row_violation","model_bound_violation","integrality_error")) > TOL:
            raise baseline.Incomplete(dict(level="threshold", **row))
        metrics = op.replay(model,block,*args,profile,label,scenario,defaultdict(list))
        witness = metrics["on_time"], metrics["backlog_area"], replay_holding(op,model,block)
        assert meets(witness,thresholds)
        row["certificate"] = "AUDITED_FEASIBLE_WITNESS"
        row["witness"] = witness
        row["max_replayed_residual"] = max(metrics[k] for k in
            ("max_balance_residual","max_capacity_violation","max_inventory_violation","backlog_identity_error"))
        return witness


def bound_separation(env, op, current, allowed, active, cache, priority, label, evidence):
    key = physical_state(current)
    thresholds = current["ot"], current["tau"], current["cost_ticks"]-current["prep_cost_ticks"]
    ordered = sorted(allowed, key=lambda s: (-priority.get(s,0), s))
    for s in ordered:
        if s in active:
            reason = "MASTER_WITNESS"
        elif any(meets(w,thresholds) for w in cache[key,s]):
            reason = "AUDITED_CACHED_WITNESS"
        else:
            witness = feasibility(env,op,current,s,allowed[s],thresholds,label,evidence["oracle"])
            if witness is None:
                priority[s] += 1
                return s
            cache[key,s].append(witness)
            continue
        evidence["bound_skips"].append(dict(run=label,scenario=s,reason=reason))
    return None


def solve(env, op, nominal, catalog, budget, method, out, evidence):
    active = {"NOM":catalog["NOM"]}
    compressed = method in ("dominance","combined")
    bounded = method in ("bounds","combined")
    keep, coverage = certify_cover(capacity_vectors(op,catalog))[:2] if compressed else (list(catalog),{})
    allowed = {s:catalog[s] for s in keep}
    cache, priority = defaultdict(list), defaultdict(int)
    for iteration in range(1,len(allowed)+2):
        label = f"{method}_i{iteration}"
        started = perf_counter()
        current = baseline.master(env,op,nominal,active,budget,label,out,evidence)
        master_end = perf_counter()
        prev = len(evidence["oracle"])
        prior_skips = len(evidence["bound_skips"])
        if bounded:
            added = bound_separation(env,op,current,allowed,active,cache,priority,label,evidence)
        else:
            added = baseline.oracle(env,op,current,allowed,label,evidence["oracle"])["added"]
        evidence["iterations"].append(dict(iteration=iteration, active=list(active), added=added,
            master_seconds=master_end-started, oracle_seconds=perf_counter()-master_end,
            oracle_milps=len(evidence["oracle"])-prev, skipped_by_witness=len(evidence["bound_skips"])-prior_skips,
            variables=current["variables"], constraints=current["constraints"], nonzeros=current["nonzeros"],
            ot=current["ot"], tau=current["tau"], cost_ticks=current["cost_ticks"], rss_bytes=baseline.memory()))
        print(method, iteration, added, flush=True)
        if added is None:
            started = perf_counter()
            replay = baseline.oracle(env,op,current,catalog,f"{method}_independent",evidence["replay"],audit=True)
            assert replay["reason"] == "CERTIFIED"
            return dict(status="PASS", replay_seconds=perf_counter()-started, representative_count=len(allowed),
                iterations=iteration, ot=current["ot"], tau=current["tau"], cost_ticks=current["cost_ticks"],
                max_residual=max(current["max_residual"],*(r.get("residual",0) for r in replay["solves"])),
                coverage=coverage)
        assert added not in active
        active[added] = catalog[added]
    raise AssertionError("scenario blocks must increase until certification")
