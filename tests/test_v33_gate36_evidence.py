import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest


EVIDENCE = Path(__file__).resolve().parents[1] / "experiments/v33_gate36_recovery_objective/evidence"


def rows(name):
    with (EVIDENCE / f"gate36_{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_primary_and_terminal_horizons():
    report = json.loads((EVIDENCE / "gate36_summary.json").read_bytes())
    assert report["tail_length"] == 23 and report["end"] == 97
    assert report["scenario_counts"] == {"0": 1, "1": 4, "2": 7}
    assert max(int(r["lead"]) for r in rows("clearance_paths")) == 23
    assert Counter(int(r["arrival"]) for r in rows("historical_pipeline") if r["tail"] == "True") == {76: 4, 80: 3, 83: 4}
    assert all(r["match"] == "True" and float(r["old"]) == float(r["extended"]) for r in rows("primary_regression"))


def test_objective_and_stage_certificates():
    report = json.loads((EVIDENCE / "gate36_summary.json").read_bytes())
    assert report["V33_RECOVERY_OBJECTIVE_CERTIFIED"] and report["gamma_lex_monotonic"]
    assert set(report["checks"].values()) == {"PASS"}
    lex = rows("lexicographic_objective_audit")
    assert len(lex) == 16 and all(r["exact"] == "True" and float(r["mip_gap"]) == 0 for r in lex)
    assert all(int(r["common_opening_rows"]) == 91 and int(r["stage_one_scenario_copies"]) == 0
               for r in rows("nonanticipativity_audit"))
    assert max(abs(float(r["residual"])) for r in rows("balance_audit")) <= 1e-6
    assert max(abs(float(r["violation"])) for r in rows("capacity_audit")) <= 1e-6


def test_exposure_reconciles_to_recovery_trajectories():
    by_area, by_terminal = Counter(), Counter()
    for r in rows("recovery_trajectories"):
        key = r["run"],r["scenario"],r["segment"]
        level = int(r["backlog"])
        by_area[key] += level
        if r["period"] == "97":
            by_terminal[key] += level
    total = defaultdict(Counter)
    for r in rows("segment_exposure"):
        key = r["run"],r["scenario"],r["segment"]
        assert by_area[key] == int(r["area"]) and by_terminal[key] == int(r["terminal"])
        total[key[:2]].update(area=int(r["area"]),terminal=int(r["terminal"]),on_time=int(r["on_time"]))
    for r in rows("scenario_metrics"):
        assert total[r["run"],r["scenario"]] == dict(area=int(r["backlog_area"]),terminal=int(r["terminal_backlog"]),on_time=int(r["on_time"]))


def test_exported_model_keeps_common_opening_and_excludes_tail_ot():
    gp = pytest.importorskip("gurobipy")
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.read(str(EVIDENCE / "gate36_representative.mps.gz"), env=env) as model:
            variables = model.getVars()
            common = {v.VarName.removeprefix("CommonOpening60"): v.index for v in variables
                      if v.VarName.startswith("CommonOpening60[")}
            assert len(common) == 91
            assert all(int(v.VarName.rsplit(",",1)[-1][:-1]) <= 74 for v in variables if "_OT[" in v.VarName)
            indices = set(common.values())
            for i in range(7):
                tag = f"W{i}_"
                for position, index in common.items():
                    row = model.getRow(model.getConstrByName(f"{tag}Bal{position[:-1]},61]"))
                    terms = [(row.getVar(j), row.getCoeff(j)) for j in range(row.size())]
                    assert [(v.index,c) for v,c in terms if v.index in indices] == [(index,-1)]
                    assert all(v.VarName.startswith(tag) for v,_ in terms if v.index not in indices)


def test_manifest():
    with (EVIDENCE / "sha256_manifest.csv").open(encoding="utf-8", newline="") as stream:
        manifest = {r["path"]: r for r in csv.DictReader(stream)}
    assert manifest.keys() == {p.name for p in EVIDENCE.iterdir() if p.name not in (".gitattributes", "sha256_manifest.csv")}
    for name, row in manifest.items():
        content = (EVIDENCE / name).read_bytes()
        assert len(content) == int(row["bytes"]) and hashlib.sha256(content).hexdigest() == row["sha256"]
