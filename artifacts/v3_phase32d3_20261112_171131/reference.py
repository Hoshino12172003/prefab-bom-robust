"""Flat RHS references independent of event-tree generation and envelopes."""

import argparse
import json
from time import perf_counter

import gurobipy as gp
import numpy as np
import psutil

from prefab_v3.e4_ccg import Prefix
from prepare import HERE, SOURCE, Coordinates, explicit_classes, policies, read
from recourse import Recourse


def peak_bytes():
    memory = psutil.Process().memory_info()
    return getattr(memory, "peak_wset", memory.rss)


def main(mode, policy):
    if mode != "gamma1":
        assert len(read(HERE / "gamma1_gate.json")) == 4
    coords = Coordinates()
    cases = read(HERE / "benchmark_design.json")
    if mode == "pointwise_small":
        cases = {k: cases[k] for k in ("G2_N32", "G3_N64")}
    else:
        cases = {k: v for k, v in cases.items() if (v["gamma"] == 1) == (mode == "gamma1")}
    ids, mult, ranks = explicit_classes(coords)
    x = policies()[policy]
    SOURCE.init()
    out = HERE / "reference" / f"{mode}_{policy}"
    out.mkdir(parents=True, exist_ok=True)
    prefix = Prefix(SOURCE.BASE)
    with SOURCE.env() as env:
        solver = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, out / "logs")
        try:
            solver.verify_against_builder([coords.ordered[0].profile, coords.atoms[0].profile,
                                           coords.ordered[-1].profile])
            with (out / "class_certificates.jsonl").open("w", encoding="utf-8") as stream, (
                    out / "solver_calls.jsonl").open("w", encoding="utf-8") as solve_stream:
                for name, case in cases.items():
                    started = perf_counter()
                    solved, bank = {}, []
                    solver.model.reset()
                    gamma, threshold = case["gamma"], case["threshold"]
                    relevant = mult[:gamma+1].sum(axis=0) > 0
                    if threshold is not None:
                        relevant &= ranks <= threshold
                    codes = [int(c) for c in ids[relevant]]
                    assert len(codes) == case["rhs_count"]
                    profiles = {c: coords.code_profile(c) for c in codes}
                    # The pointwise Gamma=1 reference solves every distinct RHS.
                    # Ladder references enumerate all RHS but need only certify the minimum.
                    if mode == "ladder":
                        codes.sort(key=lambda c: (prefix.upper(coords.profiles(profiles[c], SOURCE.OPENING), x)[2], c))
                    best, ties, exact, reused, replayed = None, set(), 0, 0, 0
                    for i, c in enumerate(codes, 1):
                        profile = profiles[c]
                        if c in solved:
                            w = solved[c]
                            proof = "EXACT_MEMO"
                            reused += 1
                        else:
                            w = None if mode != "ladder" or best is None else solver.bank_bound(bank, profile, best)
                            if w is not None:
                                solver.replay_matrix(w, profile)
                                replayed += 1
                                proof = "FEASIBLE_INTEGER_MATRIX_REPLAY"
                            else:
                                w = solver.solve(profile, f"rhs{c}", capture_vector=(mode == "ladder"))
                                solved[c] = w
                                if mode == "ladder":
                                    bank.append(w)
                                exact += 1
                                proof = "FULL_MILP"
                                solve_stream.write(json.dumps(solver.calls[-1])+"\n")
                                solve_stream.flush()
                        if proof != "FEASIBLE_INTEGER_MATRIX_REPLAY":
                            if best is None or w.q < best:
                                best, ties = w.q, {c}
                            elif w.q == best:
                                ties.add(c)
                        stream.write(json.dumps(dict(case=name, rhs_id=c, proof=proof, certified_q=w.q,
                                                     exact_q=proof != "FEASIBLE_INTEGER_MATRIX_REPLAY",
                                                     witness=w.tag))+"\n")
                        if i % 50 == 0:
                            print(mode, policy, name, i, "/", len(codes), "solves", exact, flush=True)
                    stream.flush()
                    record = dict(case=name, policy=policy, x=x, rhs_count=len(codes), gamma=gamma,
                                  mode="EXHAUSTIVE_POINTWISE_MILP" if mode != "ladder" else
                                       "EXHAUSTIVE_FLAT_EXACT_MINIMUM",
                                  worst=best, worst_rhs=sorted(ties), worst_rhs_complete=mode != "ladder",
                                  exact=True, full_milp=exact, memoized_exact=reused, matrix_replays=replayed,
                                  wall_seconds=perf_counter()-started, peak_bytes=peak_bytes(),
                                  gurobi=gp.gurobi.version(), row_checks=3, monotonicity=solver.proof)
                    (out / f"{name}.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
                    print(mode, policy, name, "W", best, "MILP", exact, "matrix replays", replayed, flush=True)
        finally:
            solver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("gamma1", "ladder", "pointwise_small"))
    parser.add_argument("policy", choices=tuple(policies()))
    args = parser.parse_args()
    main(args.mode, args.policy)
