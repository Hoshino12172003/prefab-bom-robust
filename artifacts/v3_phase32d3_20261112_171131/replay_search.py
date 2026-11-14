"""Replay branch coverage, every recorded node bound, and the saved frontier."""

import json
from dataclasses import replace
from itertools import chain

import numpy as np

from prefab_v3.event_search import Space
from prepare import HERE, Coordinates, read


def json_lines(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def replay(directory, coords, cases, gamma1_values=None):
    result = read(directory / "result.json")
    threshold = cases[result["case"]]["threshold"] if not result["full_space"] else None
    space = Space(coords.ordered, coords.nominal, result["gamma"], threshold)
    stack = [space.root()]
    calls = {r["tag"]: r for r in json_lines(directory / "solver_calls.jsonl") if "q" in r}
    by_profile = {tuple(r["profile"]): r["q"] for r in calls.values()}
    assert len(calls) == len(by_profile)
    n = coords.n_receipts
    keys = sorted({k[:2] for k in coords.keys[:n]})
    proof = {(r["node"], r["sku"]): r for r in result["monotonicity"]}
    assert set(proof) == set(keys) and all(p["inventory_upper_slack"] >= 0 for p in proof.values())
    axis = [(key, t) for key in keys for t in range(61, 75)]
    lo, hi = (np.array([proof[key][f"inventory_{bound}"] for key, _ in axis]) for bound in ("lb", "ub"))
    cumulative = np.array([[k[:2] == key and k[2] <= t for k in coords.keys[:n]] for key, t in axis],
                          dtype=np.int64)
    incumbent, replayed, pruned = None, 0, 0

    def profile(events):
        return tuple(map(int, np.minimum.reduce([coords.nominal, *(e.profile for e in events)])))

    def verify_witness(call, env):
        assert call["gap"] == call["matrix_residual"] == 0
        assert np.all(np.array(call["affected_capacity_loads"]) <= env[n:])
        ledger = np.array(call["affected_cell_inventory"]) + cumulative @ (
            np.array(env[:n]) - call["profile"][:n])
        assert np.all((lo <= ledger) & (ledger <= hi))

    for r in json_lines(directory / "nodes.jsonl"):
        if r["action"] == "incumbent":
            events = [coords.by_id[i] for i in r["selected"]]
            assert len(events) <= result["gamma"] and len({e.resource for e in events}) == len(events)
            assert all(sum(bool(e.mask & (1 << t)) for e in events) <= 2 for t in range(14))
            assert threshold is None or sum(e.rank for e in events) <= threshold
            q = by_profile[profile(events)]
            assert q == r["incumbent"] == r["lower"] and (incumbent is None or q < incumbent)
            incumbent = q
            continue
        node = stack.pop()
        assert r["selected"] == [e.id for e in node.selected] and r["remaining"] == len(node.remaining)
        assert (r["budget"], r["active_once"], r["active_twice"]) == (node.room, node.once, node.twice)
        assert r["incumbent"] == incumbent
        reason, _, tag = r["bound_provenance"].partition(":")
        if tag:
            call = calls[tag]
            env = profile(chain(node.selected, node.remaining))
            if reason == "envelope_feasible_integer_plan":
                verify_witness(call, env)
            else:
                assert reason in ("exact_rhs", "envelope_milp") and tuple(call["profile"]) == env
            assert max(node.lower, call["q"]) == r["lower"]
        else:
            assert reason in ("zero_service_witness", "inherited") and node.lower == r["lower"]
        if r["action"] == "prune":
            assert r["lower"] >= incumbent + int(result["gamma"] == 1)
            pruned += 1
            if gamma1_values is not None:
                assert not node.remaining
                assert r["lower"] <= gamma1_values[sum(e.code for e in node.selected)]
        else:
            assert r["action"] == "visit" and by_profile[node.profile] >= incumbent
            node = replace(node, lower=r["lower"])
            stack.extend(space.extend(node, i) for i in reversed(range(len(node.remaining))))
        replayed += 1
    frontier = json_lines(directory / "frontier.jsonl")
    assert len(stack) == len(frontier) == result["frontier_size"]
    for i, (node, row) in enumerate(zip(stack, frontier, strict=True)):
        assert row["selected"] == [e.id for e in node.selected] and row["remaining"] == [e.id for e in node.remaining]
        assert (row["room"], row["active_once"], row["active_twice"], row["rank"]) == (
            node.room, node.once, node.twice, node.rank)
        if row["inherited_lower"] > node.lower:
            # Only the next interrupted node can acquire a bound without a visit record.
            assert i == len(stack)-1
            env = profile(chain(node.selected, node.remaining))
            assert by_profile[env] == row["inherited_lower"]
        else:
            assert row["inherited_lower"] == node.lower
    lower = min([r["inherited_lower"] for r in frontier] + [incumbent])
    assert lower == result["lower_bound"] and incumbent == result["worst"]
    assert pruned == result["pruned_nodes"] and result["exact"] == (not frontier)
    return dict(run=directory.name, replayed_nodes=replayed, certified_prunes=pruned,
                frontier_size=len(frontier), lower=lower, incumbent=incumbent)


def main():
    coords = Coordinates()
    cases = read(HERE / "benchmark_design.json")
    values = {}
    for p in ("P1", "P2", "P3", "P4"):
        rows = json_lines(HERE / f"reference/gamma1_{p}/class_certificates.jsonl")
        values[p] = {r["rhs_id"]: r["certified_q"] for r in rows}
        assert len(values[p]) == 355 and all(r["exact_q"] for r in rows)
    summaries = []
    for p in sorted((HERE / "search").glob("*/result.json")):
        result = read(p)
        summaries.append(replay(p.parent, coords, cases, values[result["policy"]] if result["gamma"] == 1 else None))
    (HERE / "search_replay.json").write_text(json.dumps(summaries, indent=2)+"\n", encoding="utf-8")
    print("Search runs replayed:", len(summaries), "certified prunes:", sum(s["certified_prunes"] for s in summaries))


if __name__ == "__main__":
    main()
