import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest


EVIDENCE = Path(__file__).resolve().parents[1] / "experiments/v321_gate3_direct_de/evidence"


def rows(filename):
    with (EVIDENCE / filename).open(encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def test_certified_exact_runs_and_common_opening():
    report = json.loads((EVIDENCE / "gate3_summary.json").read_bytes())
    assert report["GATE3_DIRECT_DE"] == "PASS" and report["READY_FOR_GATE4"]
    assert set(report["checks"].values()) == {"PASS"}
    assert report["scenario_counts"] == {"1": {"raw": 9, "legal": 9, "deduplicated": 9},
                                         "2": {"raw": 37, "legal": 36, "deduplicated": 36}}
    solutions = {r["run"]: r for r in report["results"]}
    assert solutions["nominal_reduction"]["objective"] == report["nominal_gate1_on_time"] == 26448
    assert all(r["exact"] and r["mip_gap"] == 0 and r["replay_error"] <= 1e-6 for r in solutions.values())
    nonanticipativity = list(rows("gate3_nonanticipativity_audit.csv"))
    assert len({r["common_first_stage_variables"] for r in nonanticipativity}) == 1
    assert all(r["common_t60_rows"] == "91" and r["scenario_indexed_preparation"] == "0" and
               r["earliest_recourse_period"] == "61" for r in nonanticipativity)
    counted = Counter(r["run"] for r in nonanticipativity)
    assert counted == {key: r["scenario_count"] for key,r in solutions.items()}


def test_independent_replay_and_capacity_audits():
    assert all(abs(float(r["residual"])) <= 1e-6 for r in rows("gate3_balance_audit.csv"))
    assert all(float(r["violation"]) <= 1e-6 for r in rows("gate3_scenario_capacity_audit.csv"))
    is_zero = {"g1_B0", "nominal_reduction"}
    assert all(int(r["buffer"]) == 0 for r in rows("gate3_first_stage_solution.csv") if r["run"] in is_zero)
    for filename in ("gate3_fixed_b_equivalence.csv", "gate3_optimized_replay.csv"):
        assert all(r["exact"] == "True" and float(r["absolute_error"]) <= 1e-6 for r in rows(filename))


def test_exported_matrix_shares_opening_and_separates_recourse():
    gp = pytest.importorskip("gurobipy")
    report = json.loads((EVIDENCE / "gate3_summary.json").read_bytes())
    reference = next(r for r in report["results"] if r["run"] == "g1_B250000")
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.read(str(EVIDENCE / "gate3_representative.mps.gz"), env=env) as model:
            assert (model.NumVars, model.NumConstrs, model.NumNZs) == tuple(reference[k] for k in ("variables", "constraints", "nonzeros"))
            opening = {v.VarName.removeprefix("CommonOpening60"): v.index for v in model.getVars()
                       if v.VarName.startswith("CommonOpening60[")}
            assert len(opening) == 91
            common = set(opening.values())
            for index in range(9):
                tag = f"W{index}_"
                for pos, shared in opening.items():
                    row = model.getRow(model.getConstrByName(f"{tag}balance{pos[:-1]},61]"))
                    terms = [(row.getVar(i), row.getCoeff(i)) for i in range(row.size())]
                    assert [(v.index, c) for v,c in terms if v.index in common] == [(shared, -1)]
                    assert all(v.VarName.startswith(tag) for v,_ in terms if v.index not in common)


def test_manifest_matches_evidence():
    manifest = {r["path"]: r for r in rows("sha256_manifest.csv")}
    assert manifest.keys() == {p.name for p in EVIDENCE.iterdir() if p.name not in (".gitattributes", "sha256_manifest.csv")}
    for name, r in manifest.items():
        content = (EVIDENCE / name).read_bytes()
        assert int(r["bytes"]) == len(content) and hashlib.sha256(content).hexdigest() == r["sha256"]
