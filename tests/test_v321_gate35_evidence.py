import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1] / "experiments/v321_gate35_risk_effectiveness/evidence"


def rows(filename):
    with (EVIDENCE / filename).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def report():
    return json.loads((EVIDENCE / "gate35_summary.json").read_bytes())


def test_material_bound_deliveries_and_archived_policies():
    data = report()
    cut = data["battery_material_cut"]
    assert cut["cell_last_usable"] == 72
    assert cut["historical_pack_at_oem"] + cut["historical_pack_at_t1"] + cut["opening_kits"] + cut["usable_receipt_kits"] == 1451
    base = data["nominal_solves"]["strict_nominal_zero"]
    assert base["on_time"] == cut["nominal_on_time_bound"] == 26448
    cohorts = [r for r in rows("gate35_due_cohorts.csv") if r["policy"] == "strict_nominal_zero"]
    assert sum(int(r["shortfall"]) for r in cohorts if r["family"] == "BEV") == 1552
    assert all(r["shortfall"] == "0" for r in cohorts if r["family"] == "nonBEV")
    assert cut["prep_kit_bound"] == cut["prep_total_cells"] // 20 == 29
    assert data["nominal_solves"]["gate3_positive"]["on_time"] == cut["positive_on_time_bound"] == 26477


def test_original_events_and_threshold_grid():
    impacts = rows("gate35_event_impacts.csv")
    assert Counter(r["policy"] for r in impacts) == {"zero": 8, "gate3_positive": 8}
    assert all(r["delta_on_time"] == "0" and r["exact"] == "True" and r["mip_gap"] == "0.0" for r in impacts)
    assert {r["event"] for r in impacts if r["has_window_arrival"] == "False"} == {"BAT_UP", "SEAT_UP"}
    grid = rows("gate35_event_thresholds.csv")
    assert len(grid) == len({(r["resource"],r["duration"],r["availability"]) for r in grid}) == 150
    for resource, duration in sorted({(r["resource"],r["duration"]) for r in grid}):
        series = [r for r in grid if (r["resource"],r["duration"]) == (resource,duration)]
        series.sort(key=lambda r: -float(r["availability"]))
        assert all(r["exact"] == "True" and r["evidence_type"] == "DIAGNOSTIC_SCENARIO" for r in series)
        ot = [int(r["on_time"]) for r in series]
        assert all(a >= b for a,b in zip(ot,ot[1:]))
        first = next((r for r in series if int(r["delta_on_time"]) < 0), None)
        assert [r for r in series if r["first_effective_threshold"] == "True"] == ([first] if first else [])


def test_budget_gamma_and_readiness():
    data = report()
    assert len(data["selected_events"]) == 2
    assert data["GATE3_DIRECT_DE"] == "PASS" and not data["original_catalog_discriminative"]
    budgets = rows("gate35_budget_response.csv")
    assert [int(r["budget_usd"]) for r in budgets] == [0, 50000, 100000, 150000, 200000, 250000, 500000, 1000000]
    assert all(float(r["capital_used_usd"]) <= int(r["budget_usd"]) for r in budgets)
    assert all(int(left["on_time"]) <= int(right["on_time"]) for left,right in zip(budgets,budgets[1:]))
    gamma = rows("gate35_gamma_diagnostic.csv")
    strict = []
    for b in (0,250000):
        series = {int(r["gamma"]): int(r["on_time"]) for r in gamma if int(r["budget_usd"]) == b}
        assert series.keys() == {0,1,2}
        assert series[0] >= series[1] >= series[2]
        strict.append(series[2] < series[1])
    assert data["RISK_SET_DISCRIMINATIVE"] == (any(strict) and data["nonnominal_worst"])
    assert all(q["exact"] and q["replay_error"] <= 1e-6 for q in data["de_results"])


def test_evidence_sha256():
    manifest = {r["path"]: r for r in rows("sha256_manifest.csv")}
    assert manifest.keys() == {p.name for p in EVIDENCE.iterdir() if p.name not in (".gitattributes","sha256_manifest.csv")}
    for name,r in manifest.items():
        payload = (EVIDENCE / name).read_bytes()
        assert len(payload) == int(r["bytes"]) and hashlib.sha256(payload).hexdigest() == r["sha256"]
