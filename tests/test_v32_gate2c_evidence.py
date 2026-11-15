"""Independently check the published V3.2 certificates and expected conflicts."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

EVIDENCE = Path(__file__).resolve().parents[1] / "experiments/v32_gate2c_joint_preparedness/evidence"


def rows(name):
    with (EVIDENCE / f"gate2c_{name}.csv").open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_joint_capacity_and_exact_certificates():
    summary = json.loads((EVIDENCE / "gate2c_summary.json").read_bytes())
    results = summary["results"]
    assert len(results) == 107
    assert all(r["solver_status"] == "OPTIMAL" and r["mip_gap"] == 0 for r in results)
    assert max(r["max_replay_violation"] for r in results) <= 1e-6
    assert summary["shared_negative_control"]["solver_status"] == 3
    assert Counter(r["run_id"] for r in rows("joint_buffers")) == {r["run_id"]: 91 for r in results}
    caps = rows("resource_usage")
    assert all(float(r["used"]) <= float(r["integer_rhs"]) for r in caps)
    assert any(int(r["positive_skus"]) > 1 for r in caps if r["resource_type"] != "shared_storage")
    monotone = rows("monotonicity_audit")
    assert Counter(r["dimension"] for r in monotone) == {"alpha": 80, "H": 20}
    assert all(float(r["low"]) <= float(r["high"]) for r in monotone)


def test_frozen_projection_conflicts_are_preserved():
    r = rows("bmax_crosscheck")
    bad = [x for x in r if x["status"] == "FAIL"]
    assert Counter(x["check"] for x in bad) == {"C2C-07": 22, "C2C-10": 12}
    assert all(int(x["old_Bmax"]) == 0 and int(x["observed"]) > 0 and x["node_id"] == "zp7"
               for x in bad if x["check"] == "C2C-07")
    assert all(int(x["observed"]) == 0 and int(x["old_Bmax"]) > 0 and x["item_id"].startswith("componment_battery")
               for x in bad if x["check"] == "C2C-10")
    compared = [x for x in r if x["check"] == "C2C-10" and
                (x["basis"] == "single_kit_compatible" or not x["item_id"].startswith("componment_battery"))]
    assert len(compared) == 455
    assert all(x["observed"] == x["old_Bmax"] for x in compared)
    summary = json.loads((EVIDENCE / "gate2c_summary.json").read_bytes())
    assert summary["READY_FOR_GATE3"] is False
    assert summary["EMPIRICAL_RESIDUAL_CAPACITY"] == "NOT_IDENTIFIED"


def test_shared_oem_seat_row_contains_all_four_skus():
    gp = pytest.importorskip("gurobipy")
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.read(str(EVIDENCE / "gate2c_model.mps.gz"), env=env) as model:
            row = model.getConstrByName("SharedOemSeat[23]")
            assert row.RHS == 4000 and row.Sense == "<"
            lhs = model.getRow(row)
            assert {lhs.getVar(i).VarName: lhs.getCoeff(i) for i in range(lhs.size())} == {
                f"Ipre[zp7,{sku},23]": 1 for sku in ("Q1A", "Q2J", "Q4H", "Q4P")
            }
            assert model.ModelSense == gp.GRB.MAXIMIZE and model.NumIntVars == model.NumVars


def test_manifest_matches_released_bytes():
    with (EVIDENCE / "sha256_manifest.csv").open(encoding="utf-8") as stream:
        manifest = {r["path"]: r for r in csv.DictReader(stream)}
    assert manifest.keys() == {p.name for p in EVIDENCE.iterdir() if p.name not in (".gitattributes", "sha256_manifest.csv")}
    for name, row in manifest.items():
        payload = (EVIDENCE / name).read_bytes()
        assert len(payload) == int(row["bytes"])
        assert hashlib.sha256(payload).hexdigest() == row["sha256"]
