"""Verify the revised certificate against its evidence and the original runs."""

import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "experiments/v32_gate2c_joint_preparedness"
OLD = ROOT / "evidence"
NEW = ROOT / "evidence_v321"


def records(name, directory=NEW):
    with (directory / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def document(name, directory=NEW):
    return json.loads((directory / name).read_bytes())


def test_joint_solutions_and_network_unchanged():
    certificate = document("gate2c_summary.json")
    results = certificate["results"]
    original = {r["run_id"]: r for r in document("gate2c_summary.json", OLD)["results"]}
    assert len(results) == len(original) == 107
    for r in results:
        assert r["solver_status"] == "OPTIMAL" and r["mip_gap"] == 0
        assert r["objective"] == original[r["run_id"]]["objective"]
        assert r["max_replay_violation"] <= 1e-6
        for metric in ("shared_capacity_violation", "inventory_violation", "bom_violation",
                       "integrality_violation", "oem_seat_pool_violation"):
            assert r[metric] == 0
    for name in ("gate2c_model.lp.gz", "gate2c_model.mps.gz"):
        assert gzip.decompress((NEW / name).read_bytes()) == gzip.decompress((OLD / name).read_bytes())
    assert certificate["shared_negative_control"]["solver_status"] == 3
    comparisons = records("gate2c_monotonicity_audit.csv")
    assert Counter(r["dimension"] for r in comparisons) == {"alpha": 80, "H": 20}
    assert all(r["status"] == "PASS" and float(r["low"]) <= float(r["high"]) for r in comparisons)


def test_every_joint_position_uses_its_own_scenario():
    scenarios = document("gate2c_scenarios.json")
    assert len(scenarios) == 100
    for sid, scenario in scenarios.items():
        assert hashlib.sha256(json.dumps(scenario, sort_keys=True).encode()).hexdigest() == sid
        assert len(scenario["K_eff"]) == 91
    results = {r["run_id"]: r for r in document("gate2c_summary.json")["results"]}
    projections = {(r["scenario_id"], r["node_id"], r["item_id"]): r
                   for r in records("gate2c_scenario_projections.csv")}
    assert len(projections) == 9100
    witnesses = {(r["run_id"], r["node_id"], r["item_id"]): int(r["quantity"])
                 for r in records("gate2c_joint_buffers.csv")}
    audited = [r for r in records("gate2c_bmax_crosscheck.csv") if r["check"] == "C2C-07"]
    assert len(audited) == len(witnesses) == 9737
    assert len({(r["run_id"], r["node_id"], r["item_id"]) for r in audited}) == len(audited)
    for row in audited:
        run, position = row["run_id"], (row["node_id"], row["item_id"])
        case = results[run]
        sid = case["scenario_id"]
        assert row["scenario_id"] == sid
        assert row["status"] == "PASS"
        assert int(row["observed"]) == witnesses[(run, *position)] <= int(projections[(sid, *position)]["Bproj"])


def test_frozen_reproduction_uses_one_kit_per_horizon():
    rows = [r for r in records("gate2c_bmax_crosscheck.csv") if r["check"] == "C2C-10"]
    assert len(rows) == 455
    assert all(r["status"] == "PASS" and int(r["observed"]) == int(r["reference"]) for r in rows)
    actual = {(int(r["H"]), int(r["factor"])): int(r["unit_optimum"]) for r in rows
              if r["projection_unit"] == "complete battery kit"}
    expected = {2: 0, 20: 14, 21: 29, 22: 44, 23: 58}
    assert actual == {(h, factor): q for h, q in expected.items() for factor in (10, 6, 4)}
    old_failures = Counter(r["check"] for r in records("gate2c_bmax_crosscheck.csv", OLD) if r["status"] == "FAIL")
    assert old_failures == {"C2C-07": 22, "C2C-10": 12}
    config = document("gate2c_config.json")
    assert config["original_failure_csv_sha256"] == hashlib.sha256((OLD / "gate2c_bmax_crosscheck.csv").read_bytes()).hexdigest()
    summary = document("gate2c_summary.json")
    assert summary["frozen_projection_units"] == 445
    assert summary["READY_FOR_GATE3"] is True
    assert set(summary["checks"].values()) == {"PASS"}
    assert set(summary["prior_gate_status"].values()) == {"PASS"}
    assert summary["EMPIRICAL_RESIDUAL_CAPACITY"] == "NOT_IDENTIFIED"


def test_revised_archive_sha256():
    manifest = {r["path"]: r for r in records("sha256_manifest.csv")}
    assert manifest.keys() == {p.name for p in NEW.iterdir() if p.name not in (".gitattributes", "sha256_manifest.csv")}
    for name, row in manifest.items():
        data = (NEW / name).read_bytes()
        assert len(data) == int(row["bytes"])
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
