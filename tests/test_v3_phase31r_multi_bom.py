import csv
import gzip
import json
from fractions import Fraction
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "artifacts/v3_phase31r_20261111_202237"


def read(name):
    with (OUT / f"{name}.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_source_resource_incidence_and_no_invented_component_flexibility():
    resources = {r["resource_id"]: r for r in read("multi_bom_risk_candidate_catalog")}
    assert len(resources) == 12
    for name, sku_count, lead in (("ENGINE", 29, 1), ("GEAR", 8, 2), ("SEAT", 4, 0)):
        r = resources[name]
        assert int(r["distinct_exposed_SKUs"]) == sku_count
        assert int(r["lead_time"]) == lead
        assert r["capacity"] == "2100..2100"
        assert r["number_of_VINs_affected"] == "28000"
        assert r["number_of_distinct_vehicle_configurations_affected"] == "104"
        assert "SHARED_CAPACITY_COUPLING" in r["qualification"]
    for name in ("B_RECEIPT", "seat-supplier_trans->seat-supplier_prod"):
        assert resources[name]["max_direct_mothers_per_SKU"] == "1"
        assert "NO_CROSS_PRODUCT_FLEXIBILITY" in resources[name]["qualification"]


def test_resource_period_membership_and_scaling_rhs_support():
    rows = read("multi_bom_scenario_catalog")
    supports = set()
    for row in rows:
        events = json.loads(row["episode_details"])
        keys = {(r, t) for r, start, duration, _ in events for t in range(start, start + duration)}
        assert all(61 <= t <= 74 for _, t in keys)
        assert len(keys) == int(row["exposure_resource_days"])
        assert all(Fraction(severity) in (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
                   for _, _, _, severity in events)
        assert row["admissible_Gamma"] == "|".join(str(g) for g in (2, 4, 6) if len(keys) <= g)
        assert row["label"] == "STRESS_TEST_ONLY"
        if row["role"] == "DE_SCALING":
            assert len(keys) == 2
            supports.add(frozenset(keys))
    assert len(rows) == 40 and len(supports) == 16


def test_full_fixed_matrix_optimality_and_exact_integer_replay():
    rows = read("fixed_policy_multi_bom_service_audit")
    assert len(rows) == len({(r["scenario_id"], r["policy_id"]) for r in rows}) == 480
    assert len({r["policy_id"] for r in rows}) == 20
    assert len({r["scenario_id"] for r in rows}) == 24
    assert {int(r["pack_equivalent_budget"]) for r in rows} == {215, 429, 644, 858, 1073}
    for r in rows:
        c, t, o = (int(r[x]) for x in ("x_C", "x_T", "x_O"))
        spend = c + Fraction(27, 19)*t + Fraction(297, 190)*o
        assert spend == Fraction(r["spend"]) <= Fraction(r["budget"])
        assert r["status"] == "OPTIMAL" and r["Q_direct"] == r["bound"]
        assert float(r["gap"]) == float(r["solver_residual"]) == int(r["exact_matrix_residual"]) == 0
        assert "Optimal solution found" in (OUT / r["log"]).read_text(encoding="utf-8")


def test_existing_reduction_still_exact_on_its_domain():
    control = {"NR", "B_RECEIPT_1", "B_PROD_4", "B_SHIP_4"}
    rows = [r for r in read("fixed_policy_multi_bom_service_audit") if r["scenario_id"] in control]
    assert len(rows) == 80
    assert all(r["Q_direct"] == r["Q_battery_prefix"] for r in rows)


def test_same_integer_witness_refutes_min_additive_and_lp():
    target = ("BGS_OVERLAP", "K644_C")
    rows = read("fixed_policy_multi_bom_service_audit")
    r = next(r for r in rows if (r["scenario_id"], r["policy_id"]) == target)
    assert (int(r["x_C"]), int(r["x_T"]), int(r["x_O"])) == (915, 0, 0)
    isolated = json.loads(r["isolated_service"])
    assert isolated == {"B_RECEIPT_1": 26889, "G_4": 26500, "S_1": 26465}
    for sid, q in isolated.items():
        assert next(int(r["Q_direct"]) for r in rows if (r["scenario_id"], r["policy_id"]) == (sid, target[1])) == q
    assert int(r["Q_direct"]) == 25991
    assert min(isolated.values()) >= 26400 > int(r["Q_direct"])
    assert min(isolated.values()) - int(r["Q_direct"]) == 474
    nominal = next(int(r["Q_direct"]) for r in rows if (r["scenario_id"], r["policy_id"]) == ("NR", target[1]))
    assert nominal - sum(nominal - q for q in isolated.values()) - int(r["Q_direct"]) == -863
    lp = next(r for r in read("LP_relaxation_audit") if (r["scenario_id"], r["policy_id"]) == target)
    assert float(lp["LP_upper_bound"]) == 25991.5
    with gzip.open(OUT / "witness/BGS_OVERLAP.json.gz", "rt", encoding="utf-8") as file:
        plan = json.load(file)[target[1]]
    assert sum(plan["group_on_time"]) == 25991
    assert "seat-supplier_inv->zp7@61:1050" in plan["saturated_capacity"]


def test_due_prefix_dp_still_loses_bom_matching():
    rows = read("scalar_covering_prefix_dp")
    assert [int(r["due_period"]) for r in rows] == list(range(61, 75))
    assert all(int(r["restored_receipts_storage_headroom"]) >= 0 for r in rows)
    q = 0
    for r in rows:
        q = min(q + int(r["due_demand"]), int(r["isolated_battery_prefix_optimum"]),
                int(r["isolated_seat_prefix_optimum"]))
        assert q == int(r["scalar_covering_dp"])
    assert q - int(rows[-1]["exact_joint_total"]) == 474


def test_full_de_recourse_block_replication_and_bounds():
    rows = read("direct_de_multi_bom_scaling")
    assert [int(r["scenario_count"]) for r in rows] == [4, 8, 16]
    for r in rows:
        n = int(r["scenario_count"])
        assert int(r["integers"]) == 75810*n + 4
        assert int(r["constraints"]) == 23020*n + 1
        assert int(r["matrix_distinct_incomparable_rhs"]) == n
        assert r["presolve"] == "AUTO" and r["status"] == "OPTIMAL"
        assert int(r["Q"]) == float(r["bound"]) == 26465
        assert float(r["gap"]) == float(r["solver_residual"]) == 0
        assert r["integer_matrix_replay"] == "True"
