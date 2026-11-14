import json
from pathlib import Path

import gurobipy as gp
import pytest
from gurobipy import GRB

from prefab_v25.data import Arc, CELL, Group, Network, OEM, Order, PACK, T1
from prefab_v3.base import ASSEMBLY, Base, Weights, add_block
from prefab_v3.plain_ccg import BoundError, MasterSolution, add_recourse_block, build_master, generate
from prefab_v3.robust import on_time, protection_inventory


def oracle_table():
    return {
        (1, 0, 0): {"base": 10, "a": 3, "b": 3},
        (0, 1, 0): {"base": 9, "a": 7, "b": 5},
        (0, 0, 1): {"base": 8, "a": 6, "b": 6},
    }


def solve_table(table, initial=("base",)):
    calls = []

    def master(selected, _):
        value, policy = max((min(row[n] for n in selected), x) for x, row in table.items())
        return MasterSolution(value, policy, {})

    def recourse(name, x, tag):
        calls.append((tag, name, x))
        return table[x][name]

    return generate(("b", "base", "a"), initial, master, recourse), calls


def test_bounds_and_all_scenario_oracle_with_deterministic_ties():
    table = oracle_table()
    direct = max(min(row.values()) for row in table.values())
    result, calls = solve_table(table)
    rows = result.iterations
    assert [r["upper"] for r in rows] == [10, 7, 6]
    assert [r["lower"] for r in rows] == [3, 5, 6]
    assert all(r["lower"] <= direct <= r["upper"] for r in rows)
    assert rows[0]["worst_ties"] == ("a", "b")
    assert [r["added_scenario"] for r in rows] == ["a", "b", ""]
    assert result.objective == direct == min(result.verified_services.values())
    assert [c[:2] for c in calls] == [
        (tag, name) for tag in ("oracle_01", "oracle_02", "oracle_03", "verify")
        for name in ("b", "base", "a")
    ]
    assert all(c[2] == result.policy for c in calls[-3:])


def test_alternative_optimum_and_retaining_best_lower_bound():
    table = {
        (1, 0, 0): {"base": 10, "a": 6, "b": 7},
        (0, 1, 0): {"base": 9, "a": 8, "b": 5},
        (0, 0, 1): {"base": 8, "a": 6, "b": 6},
    }
    result, calls = solve_table(table)
    assert [r["oracle_worst"] for r in result.iterations] == [6, 5, 6]
    assert [r["lower"] for r in result.iterations] == [6, 6, 6]
    assert result.policy == (1, 0, 0)
    direct_representative = (0, 0, 1)
    assert min(table[direct_representative].values()) == result.objective == 6
    assert result.policy != direct_representative
    assert all(c[2] == result.policy for c in calls if c[0] == "verify")


@pytest.mark.parametrize("initial", [(), ("base", "base"), ("unknown",)])
def test_invalid_or_duplicate_initial_scenarios_are_rejected(initial):
    with pytest.raises(ValueError, match="nonempty subset"):
        solve_table(oracle_table(), initial)


def test_bound_inconsistency_and_final_verification_fail_closed():
    with pytest.raises(BoundError, match="selected-scenario recourse"):
        generate(("a",), ("a",), lambda *_: MasterSolution(2, (0, 0, 0), {}), lambda *_: 1)
    with pytest.raises(BoundError, match="fresh full-set verification"):
        generate(("a",), ("a",), lambda *_: MasterSolution(2, (0, 0, 0), {}),
                 lambda _, __, tag: 1 if tag == "verify" else 2)


def two_vins():
    periods = (61, 62)
    bom = ((PACK, 1), ("engine", 1))
    group = Group("two", tuple(Order(str(i), ASSEMBLY[1], 62, bom) for i in range(2)))
    arcs = (
        Arc(T1, OEM, 1, {61: 2, 62: 0}, {PACK: ((PACK, 1),)}),
        Arc(*ASSEMBLY, 0, {61: 0, 62: 2}, {group.id: bom}),
    )
    net = Network(periods, arcs, (group,), {(T1, PACK): 2, (OEM, "engine"): 2}, (), (), {}, {}, {})
    products = {PACK: "battery", "engine": "engine", **dict.fromkeys(CELL, "component"), group.id: "car"}
    return Base(net, products, dict.fromkeys(products, 0), ()), {
        "normal": ({}, {}),
        "shipping_loss": ({}, {(T1, OEM, 61): 0}),
    }


def test_real_integer_blocks_shared_policy_separate_operations_and_direct_equality():
    base, profiles = two_vins()
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model(env=env) as model:
            x, eta, blocks = build_master(model, base, profiles, profiles, (1, 1, 1), 1)
            model.update()
            assert all(v.VType == GRB.INTEGER for v in model.getVars())
            assert len([c for c in model.getConstrs() if c.ConstrName == "investment_budget"]) == 1
            normal, loss = blocks.values()
            assert normal.outflow["two", 62].index != loss.outflow["two", 62].index
            assert normal.protection_opening[OEM, PACK].getVar(0).index == x[2].index
            assert loss.protection_opening[OEM, PACK].getVar(0).index == x[2].index
            model.optimize()
            assert model.Status == GRB.OPTIMAL and eta.X == 1
            assert tuple(v.X for v in x) == (0, 0, 1)
            assert loss.flow[T1, OEM, PACK, 61].X == 0
            with pytest.raises(ValueError, match="distinct"):
                build_master(model, base, profiles, ("normal", "normal"), (1, 1, 1), 1)

        def master(names, _):
            with gp.Model(env=env) as model:
                x, eta, _ = build_master(model, base, profiles, names, (1, 1, 1), 1)
                model.optimize()
                assert model.Status == GRB.OPTIMAL
                return MasterSolution(int(eta.X), tuple(int(v.X) for v in x), {})

        def fixed(name, x, _):
            with gp.Model(env=env) as model:
                block = add_recourse_block(model, base, name, profiles[name], x)
                model.setObjective(on_time(block, base), GRB.MAXIMIZE)
                model.optimize()
                assert model.Status == GRB.OPTIMAL
                return int(model.ObjVal)

        assert fixed("normal", (0, 0, 0), "test") == 2
        assert fixed("shipping_loss", (0, 0, 0), "test") == 0
        result = generate(profiles, ("normal",), master, fixed)
        with gp.Model(env=env) as independent:
            y = independent.addVars(3, vtype=GRB.INTEGER)
            z = independent.addVar(vtype=GRB.INTEGER)
            independent.addConstr(y.sum() <= 1)
            for name, (_, factors) in profiles.items():
                block = add_block(independent, base, name, Weights(0, 0, 0, 0, 0), reschedule=True,
                                  fixed_receipts={}, arc_factors=factors,
                                  protection=protection_inventory(tuple(y.values())))
                independent.addConstr(z <= block.outflow["two", 61] + block.outflow["two", 62])
            independent.setObjective(z, GRB.MAXIMIZE)
            independent.optimize()
            assert independent.Status == GRB.OPTIMAL and independent.ObjVal == result.objective
            assert result.verified_services == {"normal": 2, "shipping_loss": 1}


def test_full_size_certificates_close_bounds_and_verify_every_final_scenario():
    out = Path(__file__).resolve().parents[1] / "artifacts/v3_phase32a_20261111_212045"
    for n in (4, 8, 16):
        direct = json.loads((out/f"n{n:02d}_DIRECT_DE.json").read_text(encoding="utf-8"))
        for method in ("CCG_MINIMAL", "CCG_INFORMED"):
            r = json.loads((out/f"n{n:02d}_{method}.json").read_text(encoding="utf-8"))
            assert direct["benchmark"] == r["benchmark"]
            assert r["objective"] == direct["objective"]
            bounds = [(it["lower"], it["upper"]) for it in r["iterations"]]
            assert all(lb <= direct["objective"] <= ub for lb, ub in bounds)
            assert [lb for lb, _ in bounds] == sorted(lb for lb, _ in bounds)
            assert [ub for _, ub in bounds] == sorted((ub for _, ub in bounds), reverse=True)
            assert bounds[-1] == (direct["objective"], direct["objective"])
            assert len(set(r["final"])) == len(r["final"]) < n
            verify = [ev for ev in r["oracle"] if ev["evaluation"] == "verify"]
            assert len(verify) == n and {ev["scenario"] for ev in verify} == set(r["benchmark"])
            assert all(ev["policy"] == r["policy"] for ev in verify)
            assert all(ev["exact_matrix_residual"] == ev["solver_gap"] == 0 for ev in verify)
            assert min(ev["service"] for ev in verify) == direct["objective"]
