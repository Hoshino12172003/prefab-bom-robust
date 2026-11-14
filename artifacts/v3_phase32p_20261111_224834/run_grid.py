"""Run the frozen Plain exact C&CG grid and exact optimal-set certificates."""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
from itertools import product
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from grid import BASELINE, FROZEN, HERE, ROOT, freeze, load, prior, profile
from prefab_v25.data import BUFFER_EFFECTS
from prefab_v3 import plain_ccg as ccg

GRID = BASE = PROFILES = None
POSITIONS = "CTO"
RESULTS = HERE/"runs"


def initialize():
    global GRID, BASE, PROFILES
    GRID = load()
    FROZEN.init()
    BASE = FROZEN.BASE
    PROFILES = {n: profile(n, data, BASE, FROZEN.OPENING) for n, data in GRID["scenarios"].items()}


def policy_class(x):
    active = "_".join(p for p, q in zip(POSITIONS, x) if q > 0)
    return active if "_" in active else f"{active}_ONLY" if active else "ZERO_BUFFER"


def operation_metrics(b, vector, scenario, policy):
    net = BASE.network
    periods = net.periods
    assignment = {g.id: g.representative.due for g in net.groups}
    deviation = sum(abs(t-assignment[g])*int(vector[v.index]) for (g, t), v in b.outflow.items())
    early = sum(int(vector[v.index]) for (g, t), v in b.outflow.items() if t < assignment[g])
    late = sum(int(vector[v.index]) for (g, t), v in b.outflow.items() if t > assignment[g])
    flows, utilization, binding = {}, {}, []
    _, factors = PROFILES[scenario]
    for arc in net.arcs:
        daily = [sum(int(vector[b.flow[(*arc.key, p, t)].index]) for p in arc.recipes) for t in periods]
        flows["->".join(arc.key)] = daily
        if arc.key == FROZEN.ASSEMBLY:
            utilization = {str(t): str(F(q, arc.capacity[t])) for t, q in zip(periods, daily)}
        for t, q in zip(periods, daily):
            cap = int(arc.capacity[t]*factors.get((*arc.key, t), 1))
            if q == cap and (arc.key == FROZEN.ASSEMBLY or (*arc.key, t) in factors):
                binding.append(f"{'->'.join(arc.key)}@{t}:{cap}")
    protection = ccg.protection_inventory(policy)
    usage = {}
    for effects in BUFFER_EFFECTS:
        for (node, sku), _ in effects:
            opening = net.initial.get((node, sku), 0)
            received = [b.receipts.get((node, sku, t), 0) for t in periods]
            inventory = [int(vector[b.inventory[node, sku, t].index]) for t in periods]
            consumed = [sum(int(q)*int(vector[b.flow[(*a.key, output, t)].index])
                            for a in net.arcs if a.origin == node for output, recipe in a.recipes.items()
                            for child, q in recipe if child == sku) for t in periods]
            usage[f"{node}|{sku}"] = dict(regular_opening=opening, protective_opening=protection[node, sku],
                inventory=inventory, production_or_dispatch_consumption=consumed, historical_receipts=received)
            for t, stock, receipt in zip(periods, inventory, received):
                if receipt < FROZEN.OPENING.get((node, sku, t), 0):
                    binding.append(f"receipt:{node}|{sku}@{t}:{receipt};stock={stock}")
    return dict(shortfall=sum(int(vector[v.index]) for v in b.shortfall.values()),
        delivery_deviation_vehicle_days=deviation, early_delivered=early, late_delivered=late,
        assembly_utilization=utilization, production_transport_assembly_daily=flows,
        pooled_inventory_and_consumption=usage, active_capacity_or_reduced_receipt=binding)


def run_case(case, ablate=None):
    name = case["case"] + (f"__NO_{ablate}" if ablate else "")
    path = RESULTS/f"{name}.json"
    if path.is_file():
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["case"] == case and result["ablate"] == ablate and result["status"] == "EXACT_FINITE":
            return name, result["status"], result["objective"]
    start = perf_counter()
    costs = tuple(map(F, case["costs"]))
    budget = F(case["budget"])
    names = tuple(case["scenarios"])
    logs = HERE/"logs"/name
    logs.mkdir(parents=True, exist_ok=True)
    metrics = []
    operations = {}
    axes = {}
    supports = {}
    result = dict(case=case, ablate=ablate, status="UNCERTIFIED", stage="PRIMARY", objective=None)

    with FROZEN.env() as env:
        def model_log(model, tag):
            path = logs/f"{tag}.log"
            path.write_text("", encoding="utf-8")
            FROZEN.configure(model, seconds=180)
            model.Params.LogFile = os.path.relpath(path, ROOT)
            return path

        def certificate(model, log, allow_infeasible=False):
            model.update()
            assert model.NumVars == model.NumIntVars and model.NumBinVars == 0
            model.optimize()
            item = dict(log=log.relative_to(HERE).as_posix(), status=model.Status,
                integers=model.NumIntVars, constraints=model.NumConstrs, runtime=model.Runtime,
                nodes=int(model.NodeCount))
            metrics.append(item)
            if allow_infeasible and model.Status == GRB.INFEASIBLE:
                return None, None
            if model.Status != GRB.OPTIMAL or model.MIPGap != 0 or model.ObjVal != model.ObjBound:
                raise RuntimeError(f"{log.name}: uncertified Gurobi status {model.Status}")
            vector, residual = FROZEN.exact_vector(model, FROZEN.matrix_rows(model))
            q = int(model.ObjVal)
            assert q == model.ObjVal
            item.update(objective=q, bound=q, gap=0, residual=residual)
            return q, vector

        def policy_of(x, vector):
            p = tuple(int(vector[v.index]) for v in x)
            assert sum(c*u for c, u in zip(costs, p)) <= budget
            return p

        def master(active, i):
            with gp.Model("master", env=env) as model:
                log = model_log(model, f"master_{i:02d}")
                x, eta, blocks = ccg.build_master(model, BASE, PROFILES, active, costs, budget)
                if ablate:
                    x[POSITIONS.index(ablate)].UB = 0
                q, vector = certificate(model, log)
                assert q == vector[eta.index] == min(prior.selected_quantity(b, BASE, vector) for b in blocks.values())
                return ccg.MasterSolution(q, policy_of(x, vector), dict(log=log.relative_to(HERE).as_posix()))

        def recourse(s, x, tag):
            with gp.Model(s, env=env) as model:
                log = model_log(model, f"{tag}_{s}")
                block = ccg.add_recourse_block(model, BASE, s, PROFILES[s], x)
                model.setObjective(ccg.on_time(block, BASE), GRB.MAXIMIZE)
                q, vector = certificate(model, log)
                assert q == prior.selected_quantity(block, BASE, vector)
                if tag == "verify":
                    operations[s] = operation_metrics(block, vector, s, x)
                return q

        try:
            sol = ccg.generate(names, case["initial"], master, recourse)
            cost = sum(c*u for c, u in zip(costs, sol.policy))
            result.update(stage="OPTIMAL_SET" if not ablate else "DONE", objective=sol.objective, policy=sol.policy,
                cost=str(cost), unused=str(budget-cost), budget_binding=cost==budget,
                cannot_add_cheapest_unit=budget-cost<min(costs), policy_class=policy_class(sol.policy),
                verified=sol.verified_services, worst=sorted(s for s, q in sol.verified_services.items() if q==sol.objective),
                iterations=sol.iterations, selected=sol.selected, operations=operations)
            if not ablate:
                witnesses = [sol.policy]
                with gp.Model("optimal_set", env=env) as model:
                    x, eta, blocks = ccg.build_master(model, BASE, PROFILES, names, costs, budget)
                    eta.LB = eta.UB = sol.objective
                    for i, p in enumerate(POSITIONS):
                        for tag, sense, bound in (("min", GRB.MINIMIZE, 0), ("max", GRB.MAXIMIZE, int(budget/costs[i]))):
                            side = f"{p}_{tag}"
                            witness = next((w for w in witnesses if w[i] == bound), None)
                            if witness is not None:
                                axes[side] = dict(value=bound, policy=witness, proof="DOMAIN_OR_BUDGET_AND_WITNESS", log="")
                                continue
                            log = model_log(model, f"projection_{side}")
                            model.reset()
                            model.setObjective(x[i], sense)
                            value, vector = certificate(model, log)
                            witness = policy_of(x, vector)
                            assert witness[i] == value
                            assert min(prior.selected_quantity(b, BASE, vector) for b in blocks.values()) == sol.objective
                            witnesses.append(witness)
                            axes[side] = dict(value=value, policy=witness, proof="FULL_BLOCK_FIXED_SERVICE", log=metrics[-1]["log"])
                    if case["case"] in GRID["ablation_anchors"]:
                        for mask in product((False, True), repeat=3):
                            label = policy_class(mask)
                            if any((enabled and axes[f"{p}_max"]["value"] == 0) or
                                   (not enabled and axes[f"{p}_min"]["value"] > 0)
                                   for p, enabled in zip(POSITIONS, mask)):
                                supports[label] = dict(proof="IMPOSSIBLE_BY_PROJECTION", policy=None, log="")
                                continue
                            witness = next((w for w in witnesses if policy_class(w) == label), None)
                            if witness is not None:
                                supports[label] = dict(proof="CERTIFIED_WITNESS", policy=witness, log="")
                                continue
                            for v, enabled, c in zip(x, mask, costs):
                                v.UB = int(budget/c) if enabled else 0
                                v.LB = int(enabled)
                            log = model_log(model, f"support_{label}")
                            model.reset()
                            model.setObjective(0, GRB.MINIMIZE)
                            _, vector = certificate(model, log, allow_infeasible=True)
                            if vector is None:
                                supports[label] = dict(proof="FULL_BLOCK_INFEASIBLE", policy=None, log=metrics[-1]["log"])
                            else:
                                witness = policy_of(x, vector)
                                assert policy_class(witness) == label
                                assert min(prior.selected_quantity(b, BASE, vector) for b in blocks.values()) == sol.objective
                                supports[label] = dict(proof="FULL_BLOCK_FEASIBLE", policy=witness, log=metrics[-1]["log"])
            result.update(status="EXACT_FINITE", stage="DONE")
        except (RuntimeError, gp.GurobiError) as exc:
            result["error"] = str(exc)
    result.update(projections=axes, joint_supports=supports, solver_calls=metrics, wall_seconds=perf_counter()-start)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)
    return name, result["status"], result["objective"]


def run_jobs(jobs, workers):
    with ProcessPoolExecutor(max_workers=workers, initializer=initialize) as pool:
        calls = {pool.submit(run_case, case, ablation): (case["case"], ablation) for case, ablation in jobs}
        for future in as_completed(calls):
            print(*future.result(), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    freeze()
    initialize()
    RESULTS.mkdir(exist_ok=True)
    cases = GRID["cases"]
    base = run_case(cases[BASELINE])
    print(*base, flush=True)
    assert base[1:] == ("EXACT_FINITE", 26465)
    x = json.loads((RESULTS/f"{BASELINE}.json").read_text(encoding="utf-8"))["policy"]
    assert x == [915, 0, 0]
    if not args.baseline_only:
        jobs = [(c, None) for n, c in cases.items() if n != BASELINE]
        jobs += [(cases[n], p) for n in GRID["ablation_anchors"] for p in POSITIONS]
        run_jobs(jobs, args.workers)
        freeze()


if __name__ == "__main__":
    main()
