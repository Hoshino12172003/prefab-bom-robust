import csv
import json
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "artifacts/v3_phase32b_20261111_214914"


def read(name):
    with (OUT / f"{name}.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_rhs_signatures_keep_effective_differences_and_remove_only_aliases():
    rows = read("rhs_equivalence_audit")
    assert len(rows) == 40
    assert len({r["effective_rhs_sha256"] for r in rows}) == 38
    by_id = {r["scenario"]: r for r in rows}
    for alias, canonical in (("ES", "DE_ENGINE_61"), ("GS", "DE_GEAR_61")):
        assert by_id[alias]["representative"] == canonical
        assert by_id[alias]["effective_rhs_sha256"] == by_id[canonical]["effective_rhs_sha256"]
    assert by_id["DE_ENGINE_61"]["effective_rhs_sha256"] != by_id["DE_GEAR_61"]["effective_rhs_sha256"]
    data = json.loads((OUT/"structure_summary.json").read_text(encoding="utf-8"))
    old = data["old_battery_combinatorial"]
    assert (old["legal_trajectories"], old["unique_rhs"], old["mip_solves"]) == (287443, 38527, 0)


def test_capacity_dominance_and_inventory_guard_are_reported_separately():
    rows = {(r["weaker"], r["stronger"]): r for r in read("scenario_dominance_audit")}
    assert rows["E_1", "E_11"]["verdict"] == "PROVEN_GLOBAL_DOMINANCE"
    assert rows["E_11", "E_1"]["verdict"] == "NOT_PROVEN"
    assert rows["NR", "B_RECEIPT_1"]["verdict"] == "PROVEN_GLOBAL_DOMINANCE"
    assert int(rows["NR", "B_RECEIPT_1"]["increased_receipt_rows"]) > 0
    assert rows["DE_ENGINE_61", "DE_GEAR_61"]["verdict"] == "NOT_PROVEN"
    assert rows["DE_GEAR_61", "DE_ENGINE_61"]["verdict"] == "NOT_PROVEN"


def test_receipt_comparison_requires_proven_storage_slack(monkeypatch):
    monkeypatch.syspath_prepend(str(OUT))
    from structure import monotone_order

    receipt = ("receipt", "receiving", "cell", 66)
    nominal = {receipt: 20}
    loss = {receipt: 10}
    assert monotone_order({}, loss, nominal, {}) == (False, 0, 0)
    assert monotone_order({}, loss, nominal, {("receiving", "cell"): 20}) == (True, 0, 1)
    assert monotone_order(loss, {}, nominal, {("receiving", "cell"): 20}) == (False, 0, 0)


def test_bom_timing_respects_gear_lead_and_seat_jit():
    rows = {(r["scenario"], r["resource"]): r for r in read("bom_risk_reachability")}
    seat = rows["DE_GEAR_61", "SEAT"]
    gear = rows["DE_GEAR_61", "GEAR"]
    assert seat["first_delivery_reachable"] == "61"
    assert gear["first_delivery_reachable"] == "63"
    assert int(seat["reachable_vins"]) > int(gear["reachable_vins"]) > 0
    assert all(r["actual_screened_from_plain"] == "False" for r in read("bom_time_screening_audit"))


def test_reachability_bounds_and_strict_worst_pruning_direction():
    rows = read("reachability_safe_bounds")
    assert len(rows) == 32
    assert {r["policy_id"] for r in rows} == {"C", "T"}
    for r in rows:
        lb, q, ub, incumbent = (int(r[k]) for k in (
            "common_feasible_lower", "exact_service", "safe_upper", "pilot_service"))
        assert lb <= q <= ub
        assert (r["certified_nonworst_at_pilot"] == "True") == (lb > incumbent)
        assert (r["certified_exact_without_individual_solve"] == "True") == (lb == ub)
        assert r["used_to_skip_any_plain_solve"] == "False"
    assert all(any(r["policy_id"] == policy and r["certified_exact_without_individual_solve"] == "True"
                   for r in rows) for policy in ("C", "T"))


def test_time_decomposition_has_no_double_counting_and_retains_plain_verification():
    for r in read("ccg_runtime_decomposition"):
        components = sum(float(r[f"{k}_seconds"]) for k in (
            "MP_solve", "oracle_solve", "verification_solve", "build", "other"))
        assert abs(components-float(r["wall_seconds"])) < 1e-8
        assert float(r["serialization_seconds"]) == 0
    for n in (4, 8, 16):
        p = json.loads((OUT/f"n{n:02d}_PLAIN.json").read_text(encoding="utf-8"))
        assert p["status"] == "EXACT_FINITE" and p["Q"] == 26465
        assert len(p["verify"]) == n and len(p["final"]) == 2
        assert all(sum(r["kind"] == "ORACLE" and r["tag"] == f"oracle_{it['iteration']:02d}"
                       for r in p["records"]) == n for it in p["iterations"])


def test_batch_only_adds_ranked_exact_violations():
    for width in (2, 4):
        p = json.loads((OUT/f"n16_BATCH{width}.json").read_text(encoding="utf-8"))
        assert p["status"] == "EXACT_FINITE" and p["Q"] == 26465
        for it in p["iterations"]:
            ranked = sorted((r["value"], r["name"]) for r in p["records"]
                            if r["tag"] == f"oracle_{it['iteration']:02d}" and r["value"] < it["upper"])
            expected = [n for _, n in ranked[:width]] if it["upper"] > it["lower"] else []
            assert it["added_scenario"] == expected


def test_five_initializations_and_expanded_direct_are_audited():
    init = read("ccg_initialization_audit")
    assert {r["variant"] for r in init} == {f"INIT_{name}" for name in "ABCDE"}
    assert all(r["n"] == "24" and r["status"] == "EXACT_FINITE" for r in init)
    assert len({r["Q"] for r in init}) == 1
    assert next(r["initial_blocks"] for r in init if r["variant"] == "INIT_B").startswith("NR|")
    assert float(next(r["pilot_elapsed_seconds"] for r in init if r["variant"] == "INIT_E")) > 0
    for n, method in ((24, "INIT_A"), (32, "PLAIN"), (38, "PLAIN")):
        direct = json.loads((OUT/f"n{n:02d}_DIRECT.json").read_text(encoding="utf-8"))
        plain = json.loads((OUT/f"n{n:02d}_{method}.json").read_text(encoding="utf-8"))
        assert direct["names"] == plain["names"] and len(set(direct["names"])) == n
        assert direct["soft_mem_gb"] is None and plain["soft_mem_gb"] is None
        if direct["status"] == "EXACT_FINITE":
            assert direct["Q"] == plain["Q"]
        else:
            assert direct["records"][-1]["status"] != 2
