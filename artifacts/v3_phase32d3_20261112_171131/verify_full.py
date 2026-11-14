"""Independently replay every full-space branch with fresh full integer witnesses."""

import json
import os
from collections import Counter
from fractions import Fraction
from time import perf_counter

import gurobipy as gp
import numpy as np
from gurobipy import GRB

from prefab_v3 import plain_ccg as plain
from prefab_v3.event_budget import Event
from prefab_v3.robust import Episode
from prepare import HERE, ROOT, SOURCE, TOTALS, Coordinates, frozen_catalog, policies, read
from recourse import Recourse, Witness
from replay_search import json_lines


def direct(env, check, coords, p, tag, profile, expected):
    path = HERE / "independent_full" / p / f"{tag}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gp.Model(env=env) as model:
        SOURCE.configure(model, seconds=180)
        path.write_text("", encoding="utf-8")
        model.Params.LogFile = os.path.relpath(path, ROOT)
        b = plain.add_recourse_block(model, SOURCE.BASE, "recourse",
                                     coords.profiles(profile, SOURCE.OPENING), check.policy)
        model.setObjective(plain.on_time(b, SOURCE.BASE), GRB.MAXIMIZE)
        model.update()
        a, h, s = SOURCE.matrix_rows(model)
        assert (a != check.matrix).nnz == 0 and np.array_equal(h, check.rhs(profile))
        assert np.array_equal(s, check.sense)
        model.optimize()
        assert model.Status == GRB.OPTIMAL and model.MIPGap == 0 and model.ObjVal == model.ObjBound == expected
        raw, residual = SOURCE.exact_vector(model, (a, h, s))
        vector = raw.astype(np.int64)
        assert vector[check.objective_idx].sum() == expected
        record = dict(tag=tag, Q=expected, bound=model.ObjBound, gap=model.MIPGap, solver_residual=residual,
                      matrix_residual=0, solver_seconds=model.Runtime, log=path.relative_to(HERE).as_posix())
    plan = path.with_suffix(".npz")
    np.savez_compressed(plan, vector=vector, profile=profile)
    record["witness"] = plan.relative_to(HERE).as_posix()
    record["witness_sha256"] = frozen_catalog.digest(plan)
    return Witness(expected, profile, None, None, tag, vector), record


def root_groups(coords):
    """A separate count of trajectories indexed by earliest event, without DFS."""
    result = {}
    count = 1
    for i, first in enumerate(coords.ordered):
        remaining = tuple(e for e in coords.ordered[i+1:] if e.resource != first.resource)
        res = np.array([e.resource for e in remaining])
        days = np.array([e.mask for e in remaining], dtype=np.int64)
        allowed = ((days[:, None] & days & first.mask) == 0) & (res[:, None] != res)
        triples = np.count_nonzero(np.triu(allowed, 1))
        covered = 1 + len(remaining) + int(triples)
        envelope = tuple(map(int, np.minimum.reduce([first.profile, *(e.profile for e in remaining)])))
        result[first.id] = (covered, len(remaining), envelope)
        count += covered
    assert count == TOTALS[3][0]
    return result


def verify(p, x, coords, groups):
    started = perf_counter()
    root = HERE / "search" / f"{p}_G3_FULL_L2"
    result = read(root / "result.json")
    if not result["exact"]:
        return dict(policy=p, full_certificate=False, reason=result["stop"])
    nodes = json_lines(root / "nodes.jsonl")
    prunes = {r["selected"][0]: r for r in nodes if r["action"] == "prune"}
    assert set(prunes) == set(groups) and all(len(r["selected"]) == 1 for r in prunes.values())
    assert [r["selected"] for r in nodes if r["action"] == "visit"] == [[]]
    solved = {r["tag"]: r for r in json_lines(root / "solver_calls.jsonl")}
    worst = result["worst"]
    ids = result["worst_events"]
    event_records = [coords.records[i-1] for i in ids]
    events = tuple(Event(r["resource"], Episode(r["start"], r["duration"], Fraction(r["severity"])))
                   for r in event_records)
    assert frozen_catalog.BUDGET.validate(events, 3) > 0
    witness_code = sum(coords.by_id[i].code for i in ids)
    actual = frozen_catalog.profile("worst_witness", events)
    assert coords.profiles(coords.code_profile(witness_code), SOURCE.OPENING) == actual
    witness_profile = coords.code_profile(witness_code)
    exact_tag = next(tag for tag, r in solved.items() if tuple(r["profile"]) == witness_profile and r["q"] == worst)
    tags = {r["bound_provenance"].split(":")[1] for r in prunes.values()} | {exact_tag}
    fresh, records, evidence = {}, [], []
    with SOURCE.env() as env:
        check = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, HERE / "independent_full" / p / "matrix")
        try:
            for tag in sorted(tags):
                r = solved[tag]
                fresh[tag], log = direct(env, check, coords, p, tag, tuple(r["profile"]), r["q"])
                records.append(log)
            for i, (n, remaining, envelope) in groups.items():
                node = prunes[i]
                reason, tag = node["bound_provenance"].split(":")
                assert remaining == node["remaining"]
                if reason in ("exact_rhs", "envelope_milp"):
                    assert fresh[tag].profile == envelope
                else:
                    assert reason == "envelope_feasible_integer_plan"
                check.replay_matrix(fresh[tag], envelope)
                assert fresh[tag].q >= worst
                evidence.append(dict(event_id=i, represented_legal_trajectories=n,
                                     remaining_events=remaining, witness=tag, witness_Q=fresh[tag].q,
                                     envelope_min=int(min(envelope)), matrix_residual=0))
            with np.load(root / "worst_witness.npz") as archived:
                check.matrix_check(archived["vector"], check.rhs(witness_profile))
                assert archived["vector"][check.objective_idx].sum() == worst
            # The empty trajectory is covered directly, independently of the subtrees.
            nominal = next(r for r in solved.values() if tuple(r["profile"]) == coords.nominal)
            assert nominal["q"] >= worst
            check.replay_matrix(fresh[exact_tag], coords.nominal)
        finally:
            check.close()
    out = HERE / "independent_full" / p
    frozen_catalog.write(out / "root_branch_matrix_replay.csv", evidence)
    frozen_catalog.dump(out / "independent_solver_calls.json", records)
    result = dict(policy=p, full_certificate=True, value=worst, rhs_id=witness_code, root_branches=len(evidence),
                  trajectories_covered=1+sum(r["represented_legal_trajectories"] for r in evidence),
                  replay_matrix_rows=23019, maximum_matrix_residual=0, independent_milps=len(records),
                  witness_uses=dict(Counter(r["witness"] for r in evidence)), seconds=perf_counter()-started)
    print(p, "independently certified full value", worst, "coverage", result["trajectories_covered"],
          "fresh solves", len(records), flush=True)
    return result


def main():
    SOURCE.init()
    coords = Coordinates()
    groups = root_groups(coords)
    results = [verify(p, x, coords, groups) for p, x in policies().items()]
    (HERE / "full_independent_certificate.json").write_text(json.dumps(results, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
