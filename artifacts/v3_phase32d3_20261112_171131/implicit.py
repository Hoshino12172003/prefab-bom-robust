"""Fixed-policy search using atomic events, safe envelopes, and exact Gurobi solves."""

import argparse
import json
from collections import Counter
from time import perf_counter

import numpy as np

from prefab_v3.e4_ccg import Prefix
from prefab_v3.event_search import SearchLimit, Space, search
from prepare import HERE, SOURCE, TOTALS, Coordinates, policies, read
from recourse import Recourse
from reference import peak_bytes


def run_case(solver, policy, name, case, level, out, full=False):
    coords = solver.coords
    space = Space(coords.ordered, coords.nominal, case["gamma"], case["threshold"])
    prefix = Prefix(solver.base)
    exact, bank, stats = {}, [], Counter()
    keep_ties = case["gamma"] == 1
    out.mkdir(parents=True, exist_ok=True)
    first_call = len(solver.calls)
    t0 = perf_counter()
    limit = dict(nodes=2500, leaf=64, envelope=8, seconds=160) if full else None
    last_bound = "zero_service_witness"
    max_envelopes = 8
    iteration = 0

    def remaining_time():
        return min(180, limit["seconds"]-(perf_counter()-t0)) if limit else 180

    with (out / "nodes.jsonl").open("w", encoding="utf-8") as nodes:
        def record(action, node, lower, incumbent):
            nonlocal iteration
            iteration += 1
            nodes.write(json.dumps(dict(iteration=iteration, action=action,
                selected=[e.id for e in node.selected], remaining=len(node.remaining), budget=node.room,
                active_once=node.once, active_twice=node.twice, lower=lower, incumbent=incumbent,
                bound_provenance=last_bound if action != "incumbent" else "legal_integer_optimum"))+"\n")

        def evaluate(profile, kind):
            if profile in exact:
                stats["exact_cache_hits"] += 1
                return exact[profile].q
            if limit and stats[f"{kind}_calls"] >= limit[kind]:
                raise SearchLimit(f"{kind} MILP limit")
            stats[f"{kind}_calls"] += 1
            w = solver.solve(profile, kind, seconds=remaining_time(), capture_vector=True)
            exact[profile] = w
            if level >= 1:
                bank.append(w)
            return w.q

        def bound(node, incumbent):
            nonlocal last_bound
            last_bound = "inherited" if node.lower else "zero_service_witness"
            if incumbent is None or level == 0:
                return node.lower
            target = incumbent + int(keep_ties)
            if node.lower >= target:
                return node.lower
            env = node.envelope() if node.remaining else node.profile
            if env in exact:
                stats["envelope_cache_hits"] += 1
                last_bound = "exact_rhs:" + exact[env].tag
                return exact[env].q
            w = solver.bank_bound(bank, env, target)
            if w is not None:
                stats["witness_bounds"] += 1
                last_bound = "envelope_feasible_integer_plan:" + w.tag
                return w.q
            if level == 2 and len(node.selected) <= 1 and len(node.remaining) >= 8 and (
                    stats["envelope_calls"] < max_envelopes):
                upper = prefix.upper(coords.profiles(env, solver.opening), solver.policy)[2]
                if upper >= target:
                    q = evaluate(env, "envelope")
                    last_bound = "envelope_milp:" + exact[env].tag
                    return q
                stats["envelope_skipped_by_upper"] += 1
            return node.lower

        def seed():
            node = space.root()
            while node.remaining:
                trials = [space.extend(node, i) for i in range(len(node.remaining))]
                node = min(trials, key=lambda n: (prefix.upper(coords.profiles(n.profile, solver.opening),
                                                             solver.policy)[2], n.selected[-1].id))
            return node

        result = search(space, evaluate, bound, record, seeds=(seed(),), keep_ties=keep_ties,
                        node_limit=limit["nodes"] if limit else None,
                        seconds=limit["seconds"] if limit else None)
    frontier = result.pop("frontier")
    with (out / "frontier.jsonl").open("w", encoding="utf-8") as stream:
        for n in frontier:
            stream.write(json.dumps(dict(selected=[e.id for e in n.selected], remaining=[e.id for e in n.remaining],
                                         room=n.room, active_once=n.once, active_twice=n.twice,
                                         rank=n.rank, inherited_lower=n.lower))+"\n")
    calls = solver.calls[first_call:]
    assert len(calls) == stats["leaf_calls"] + stats["envelope_calls"]
    assert len({tuple(c["profile"]) for c in calls}) == len(calls)
    with (out / "solver_calls.jsonl").open("w", encoding="utf-8") as stream:
        for r in calls:
            stream.write(json.dumps(r)+"\n")
    if result["worst"] is not None:
        code = sum(coords.by_id[i].code for i in result["worst_events"])
        witness = exact[coords.code_profile(code)]
        assert witness.q == result["worst"]
        np.savez_compressed(out / "worst_witness.npz", vector=witness.vector, profile=witness.profile, rhs_id=code)
    result.update(case=name, policy=policy, x=solver.policy, gamma=case["gamma"],
                  rhs_count=case["rhs_count"], raw_count=case["raw_count"], level=level, full_space=full,
                  resource_limits=limit, frontier_size=len(frontier), dominance_pruned_nodes=0,
                  envelope_calls=stats["envelope_calls"], exact_recourse_calls=stats["leaf_calls"],
                  cache_hits=stats["exact_cache_hits"], envelope_cache_hits=stats["envelope_cache_hits"],
                  witness_bounds=stats["witness_bounds"], total_full_milp=len(calls),
                  envelope_skipped_by_upper=stats["envelope_skipped_by_upper"],
                  evaluation_fraction=len(calls)/case["rhs_count"],
                  leaf_evaluation_fraction=stats["leaf_calls"]/case["rhs_count"],
                  total_wall_seconds=perf_counter()-t0, peak_bytes=peak_bytes(), monotonicity=solver.proof,
                  worst_event_details=[coords.records[i-1] for i in result["worst_events"]])
    (out / "result.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(policy, name, "level", level, "exact", result["exact"], "W", result["worst"],
          "leaf", result["exact_recourse_calls"], "env", result["envelope_calls"],
          "nodes", result["visited_nodes"], "frontier", result["frontier_size"], flush=True)


def main(mode, policy):
    if mode != "gamma1":
        assert len(read(HERE / "gamma1_gate.json")) == 4
    coords = Coordinates()
    x = policies()[policy]
    SOURCE.init()
    cases = read(HERE / "benchmark_design.json")
    if mode == "gamma1":
        work = [(k, v, 2) for k, v in cases.items() if v["gamma"] == 1]
    elif mode == "ladder":
        work = [(k, v, 2) for k, v in cases.items() if v["gamma"] > 1]
    elif mode == "levels":
        work = [(k, cases[k], level) for k in ("G2_N32", "G3_N64") for level in (0, 1)]
    else:
        raw, rhs = TOTALS[3]
        work = [("G3_FULL", dict(gamma=3, rhs_count=rhs, raw_count=raw, threshold=None), 2)]
    for name, case, level in work:
        out = HERE / "search" / f"{policy}_{name}_L{level}"
        with SOURCE.env() as env:
            solver = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, out / "logs")
            try:
                run_case(solver, policy, name, case, level, out, mode == "full")
            finally:
                solver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("gamma1", "ladder", "levels", "full"))
    parser.add_argument("policy", choices=tuple(policies()))
    args = parser.parse_args()
    main(args.mode, args.policy)
