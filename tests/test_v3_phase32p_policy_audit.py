import csv
import hashlib
import json
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "artifacts/v3_phase32p_20261111_224834"


def read(name):
    with (OUT/f"{name}.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def result(case):
    return json.loads((OUT/"runs"/f"{case}.json").read_text(encoding="utf-8"))


def test_frozen_design_and_grid_coverage():
    source = (OUT/"frozen_policy_grid.json").read_bytes()
    assert hashlib.sha256(source).hexdigest() == (OUT/"frozen_policy_grid.sha256").read_text().strip()
    protocol = json.loads(source)
    rows = read("buffer_policy_full_grid")
    assert len(rows) == len(protocol["cases"]) == 127
    assert {r["case"] for r in rows} == set(protocol["cases"])
    assert all(r["status"] == "EXACT_FINITE" and r["label"] == "STRESS_TEST_ONLY" for r in rows)
    assert len(read("buffer_policy_budget_sensitivity")) == 49
    assert len(read("buffer_policy_severity_duration")) == 54
    assert len(read("buffer_policy_cost_sensitivity")) == 25
    assert len(read("buffer_policy_risk_location")) == 6
    assert len(read("buffer_policy_recovery_sensitivity")) == 3


def test_plain_full_service_verification_and_projection_witnesses():
    rows = read("buffer_policy_optimal_set_audit")
    assert len(rows) == 127*6
    for case in {r["case"] for r in rows}:
        r = result(case)
        assert r["status"] == "EXACT_FINITE"
        q = r["objective"]
        assert set(r["verified"]) == set(r["case"]["scenarios"])
        assert q == min(r["verified"].values())
        assert r["iterations"][-1]["lower"] == r["iterations"][-1]["upper"] == q
        assert len(r["projections"]) == 6
        for i, p in enumerate("CTO"):
            low, high = (r["projections"][f"{p}_{direction}"] for direction in ("min", "max"))
            assert low["policy"][i] == low["value"] <= r["policy"][i] <= high["value"] == high["policy"][i]
            assert all(sum(F(c)*x for c, x in zip(r["case"]["costs"], a["policy"])) <= F(r["case"]["budget"])
                       for a in (low, high))


def test_baseline_and_strict_budget_switches_hold_across_optimal_set():
    old, medium, high = (result(f"BASE_B{b}") for b in (100, 150, 200))
    assert old["policy"] == [915, 0, 0] and old["objective"] == 26465
    assert old["cost"] == "915" and old["unused"] == "3/19"
    assert old["projections"]["T_max"]["value"] == old["projections"]["O_max"]["value"] == 0
    assert medium["objective"] == 26912
    assert [medium["projections"][f"T_{d}"]["value"] for d in ("min", "max")] == [20, 25]
    assert high["objective"] == 27050 and high["projections"]["O_min"]["value"] == 27
    rows = read("policy_switching_witness")
    assert any(r["old_case"] == "BASE_B100" and r["new_case"] == "BASE_B150" and
               "T" in r["positions_with_strict_switch"] for r in rows)


def test_pack_transport_stress_requires_oem_inventory_at_center_costs():
    base = result("R3_S50_D7_ABRUPT_B100")
    stressed = result("R3_S75_D7_ABRUPT_B100")
    assert base["policy"] == [915, 0, 0] and base["objective"] == 27363
    assert stressed["objective"] == 27286
    assert stressed["projections"]["T_min"]["value"] == 125
    assert stressed["projections"]["O_min"]["value"] == 5
    ops = stressed["operations"]["R3_S75_D7_ABRUPT"]
    assert any("battery-supplier_inv->zp7@" in k and k.endswith(":73") for k in ops["active_capacity_or_reduced_receipt"])


def test_joint_supports_and_ablations_distinguish_zero_value_from_zero_representative():
    joint = read("buffer_policy_joint_support_audit")
    assert len(joint) == 7*8
    seat = "R5_S50_D7_ABRUPT_B100"
    assert any(r["case"] == seat and r["policy_class"] == "ZERO_BUFFER" and r["possible"] == "True" for r in joint)
    assert any(r["case"] == seat and r["policy_class"] == "C_T_O" and r["possible"] == "True" for r in joint)
    rows = read("buffer_ablation_by_environment")
    assert len(rows) == 21 and all(r["status"] == "EXACT_FINITE" and int(r["delta"]) >= 0 for r in rows)
    assert all(int(r["delta"]) == 0 for r in rows if r["case"] == seat)
    assert any(r["forbidden"] == "C" and int(r["delta"]) > 0 for r in rows)


def test_nested_budget_gamma_and_price_monotonicity():
    budgets = defaultdict(list)
    for row in read("buffer_policy_budget_sensitivity"):
        budgets[row["risk"]].append((F(row["budget"]), int(row["robust_on_time"])))
    for b in budgets.values():
        q = [q for _, q in sorted(b)]
        assert q == sorted(q)
    gamma = [result(f"GAMMA_{g}") for g in (2, 4, 6)]
    assert all(set(a["verified"]) < set(b["verified"]) and a["objective"] >= b["objective"] for a, b in zip(gamma, gamma[1:]))
    costs = {(int(r["alpha_T_multiplier"]), int(r["alpha_O_multiplier"])): int(r["robust_on_time"])
             for r in read("buffer_policy_cost_sensitivity")}
    for t, o in costs:
        for a, b in costs:
            if a>=t and b>=o:
                assert costs[a, b] <= costs[t, o]


def test_effective_receipt_plateau_and_frozen_threshold_protocol():
    rows = {r["scenario"]: r for r in read("scenario_effective_profiles")}
    short, medium, long = (rows[f"R1_S50_D{d}_ABRUPT"] for d in (4, 7, 11))
    assert short["effective_rhs_sha256"] == medium["effective_rhs_sha256"] != long["effective_rhs_sha256"]
    rhs_short = {tuple(key): q for key, q in json.loads(short["effective_rhs"])}
    rhs_long = {tuple(key): q for key, q in json.loads(long["effective_rhs"])}
    assert all(rhs_long[key] == value for key, value in rhs_short.items())
    added = rhs_long.keys() - rhs_short.keys()
    assert len(added) == 3 and all(key[0] == "receipt" and key[-1] == 73 for key in added)
    plateau = [result(f"R1_S50_D{d}_ABRUPT_B100") for d in (4, 7, 11)]
    assert all(r["objective"] == 26889 and r["policy"] == [915, 0, 0] for r in plateau)
    assert rows["R1_S50_D7_GRADUAL"]["effective_rhs_sha256"] == rows["R1_S50_D7_ABRUPT"]["effective_rhs_sha256"]
    threshold = json.loads((OUT/"contingent_threshold_jobs.json").read_text(encoding="utf-8"))
    assert threshold["parent_grid_sha256"] == (OUT/"frozen_policy_grid.sha256").read_text().strip()
    assert len(threshold["jobs"]) == 7*len(threshold["edges"])
    assert all(result(c["case"])["status"] == "EXACT_FINITE" for c in threshold["jobs"])


def test_policy_region_figures_are_exported_for_certified_cells():
    for stem in ("map_A_budget_location", "map_B_severity_duration", "map_C_relative_costs"):
        assert (OUT/"figures"/f"{stem}.pdf").read_bytes().startswith(b"%PDF")
        assert (OUT/"figures"/f"{stem}.png").read_bytes().startswith(b"\x89PNG")
