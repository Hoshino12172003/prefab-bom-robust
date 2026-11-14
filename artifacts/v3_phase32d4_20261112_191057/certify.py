"""Independent full-domain certificates and the optimal-policy-set audit."""

from math import lcm
from time import perf_counter

import gurobipy as gp
import numpy as np
from gurobipy import GRB

from prefab_v3 import plain_ccg
from prefab_v3.e4_ccg import Prefix
from prefab_v3.robust import protection_inventory

from run import (HERE, SOURCE, COSTS, BUDGET, TOTALS, Coordinates, Recourse, case, certified_event,
                 fixed_oracle, frozen_catalog, optimize_model, read, spend)
import verify_full as d3_verify
from replay_search import json_lines


d3_verify.HERE = HERE


def independent(env, coords, x, gamma, oracle_dir, label, groups):
    started = perf_counter()
    result = read(oracle_dir / "result.json")
    assert result["exact"] and result["frontier_size"] == 0
    code, _, _ = certified_event(coords, result)
    q = result["worst"]
    nodes = json_lines(oracle_dir / "nodes.jsonl")
    prunes = {n["selected"][0]: n for n in nodes if n["action"] == "prune"}
    assert len(prunes) == 414 and set(prunes) == set(groups)
    assert all(len(n["selected"]) == 1 for n in prunes.values())
    assert [n["selected"] for n in nodes if n["action"] == "visit"] == [[]]
    solved = {r["tag"]: r for r in json_lines(oracle_dir / "solver_calls.jsonl")}
    profile = coords.code_profile(int(code))
    witness = next(tag for tag, r in solved.items() if tuple(r["profile"]) == profile and r["q"] == q)
    tags = sorted({n["bound_provenance"].split(":")[1] for n in prunes.values()} | {witness})
    out = HERE / "independent_full" / label
    checker = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, out / "matrix")
    replay, logs, fresh = [], [], {}
    try:
        for tag in tags:
            rec = solved[tag]
            fresh[tag], audit = d3_verify.direct(env, checker, coords, label, tag, tuple(rec["profile"]), rec["q"])
            logs.append(audit)
        for event, (n3, remainder, env_profile) in groups.items():
            node = prunes[event]
            kind, tag = node["bound_provenance"].split(":")
            assert remainder == node["remaining"]
            if kind in ("envelope_milp", "exact_rhs"):
                assert fresh[tag].profile == env_profile
            else:
                assert kind == "envelope_feasible_integer_plan"
            checker.replay_matrix(fresh[tag], env_profile)
            assert fresh[tag].q >= q
            replay.append(dict(first_event=event, remaining_events=remainder,
                               represented_trajectories=1+remainder if gamma == 2 else n3,
                               witness=tag, witness_service=fresh[tag].q, residual=0))
        checker.replay_matrix(fresh[witness], coords.nominal)
        with np.load(oracle_dir / "worst_witness.npz") as archived:
            checker.matrix_check(archived["vector"], checker.rhs(profile))
            assert archived["vector"][checker.objective_idx].sum() == q
    finally:
        checker.close()
    raw = 1+sum(r["represented_trajectories"] for r in replay)
    assert raw == TOTALS[gamma][0]
    frozen_catalog.write(out / "branches.csv", replay)
    frozen_catalog.dump(out / "solver_calls.json", logs)
    cert = dict(gamma=gamma, label=label, policy=x, lower=q, upper=q, exact=True, raw_count=raw,
        rhs_count=TOTALS[gamma][1], full_matrix_branch_replays=len(replay), independent_milps=len(logs),
        worst_rhs=int(code), matrix_residual=0, seconds=perf_counter()-started)
    frozen_catalog.dump(out / "certificate.json", cert)
    print(label, "independent full certificate", q, "raw coverage", raw, flush=True)
    return cert


def robust_flatness(x_zero, z, costs, budget):
    """Check the inventory lift from a certified zero-protection recourse plan."""
    assert x_zero == (0, 0, 0)
    net = SOURCE.BASE.network
    x_max = tuple(int(budget/c) for c in costs)
    extra = protection_inventory(x_max)
    rows = []
    for (node, sku), additive_bound in sorted(extra.items()):
        assert (node, sku) not in net.external
        fixed = sum(q for (n, s, _), q in SOURCE.OPENING.items() if (n, s) == (node, sku))
        inflow = sum(a.capacity[t] for a in net.arcs for t in net.periods
            if a.destination == node and sku in a.recipes and t+a.lead in net.periods)
        base = net.initial.get((node, sku), 0)
        _, hi = net.inventory_bounds.get((node, sku), (0, float("inf")))
        gross = base+fixed+inflow+additive_bound
        assert gross <= hi
        rows.append(dict(node=node, sku=sku, max_extra=additive_bound, initial=base,
                         nominal_receipts=fixed, inbound_capacity_bound=inflow, gross_bound=gross,
                         inventory_upper=None if hi == float("inf") else hi,
                         headroom=None if hi == float("inf") else hi-gross))
    scale = lcm(budget.denominator, *(v.denominator for v in costs))
    c, t, o = (int(v*scale) for v in costs)
    b = int(budget*scale)
    count = sum((b-c*i-t*j)//o+1 for i in range(x_max[0]+1)
                for j in range((b-c*i)//t+1))
    return dict(all_budget_feasible_policies_are_optimal=True, robust_value=z,
                budget_integer_form=dict(c=[c,t,o], rhs=b), feasible_integer_policies=count,
                axis_min=[0,0,0], axis_max=x_max, bound_rows=rows,
                zero_policy_certified=True)


def policy_projections(env, coords, result, flatness):
    active = tuple(result["selected"])
    profiles = {n: coords.profiles(coords.code_profile(int(n)), SOURCE.OPENING) for n in active}
    z = result["objective"]
    rows = []
    for i, name in enumerate(("x_C", "x_T", "x_O")):
        for sense, direction in ((GRB.MINIMIZE, "min"), (GRB.MAXIMIZE, "max")):
            with gp.Model(env=env) as model:
                x, eta, _ = plain_ccg.build_master(model, SOURCE.BASE, profiles, active, COSTS, BUDGET)
                model.addConstr(eta == z)
                model.setObjective(x[i], sense)
                v, vector, metrics = optimize_model(model, HERE / "policy_set" / f"{name}_{direction}.log")
                policy = tuple(int(vector[a.index]) for a in x)
                assert policy[i] == v == flatness[f"axis_{direction}"][i]
                cost = spend(policy)
                rows.append(dict(gamma=3, coordinate=name, direction=direction, value=v, x_C=policy[0],
                                 x_T=policy[1], x_O=policy[2], robust_service=z, cost=str(cost),
                                 budget_slack=str(BUDGET-cost), full_set_certificate="ZERO_POLICY_INVENTORY_LIFT",
                                 **metrics))
    frozen_catalog.write(HERE / "gamma_policy_set_audit.csv", rows)
    return rows


def main():
    SOURCE.init()
    coords = Coordinates()
    groups = d3_verify.root_groups(coords)
    results = {g: read(HERE / f"outer/G{g}/result.json") for g in (1,2,3)}
    z = results[3]["objective"]
    assert z == 11775 and all(r["objective"] == z for r in results.values())
    with SOURCE.env() as env:
        checks = [independent(env, coords, tuple(results[g]["policy"]), g,
                             HERE / f"outer/G{g}/final_oracle", f"G{g}", groups) for g in (2,3)]
        zero = fixed_oracle(env, coords, (0,0,0), case(3), HERE / "zero_policy", True)
        assert zero["exact"] and zero["worst"] == z
        checks.append(independent(env, coords, (0,0,0), 3, HERE / "zero_policy", "zero_policy", groups))
        # The verified seat prefix supplies a policy-independent upper bound.
        seat = coords.profiles(coords.code_profile(results[3]["final_worst_rhs"]), SOURCE.OPENING)
        assert Prefix(SOURCE.BASE).upper(seat, (0,0,0))[1] == z
        flatness = robust_flatness((0,0,0), z, COSTS, BUDGET)
        policy_projections(env, coords, results[3], flatness)
    frozen_catalog.dump(HERE / "policy_flatness_certificate.json", flatness)
    frozen_catalog.dump(HERE / "final_policy_independent_certificate.json", checks)


if __name__ == "__main__":
    main()
