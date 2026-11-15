import csv
import hashlib
import importlib
import json
from collections import defaultdict
from pathlib import Path

import pytest


@pytest.fixture
def baseline(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "experiments/v33_gate4a_plain_ccg"))
    return importlib.import_module("baseline")


def test_primary_violation_selects_one_by_backlog_then_id(baseline):
    master = dict(ot=10, tau=2, prep_cost_ticks=5, cost_ticks=10)
    service = {"NOM":10, "B":9, "A":9, "C":9}
    backlog = {"C":10, "B":11, "A":11}
    added, reason, winner = baseline.separation_choice(master, service, backlog, {})
    assert (added, reason, winner) == ("A", "PRIMARY_VIOLATION", "A")


def test_scenario_with_higher_own_service_can_bind_common_backlog(baseline):
    master = dict(ot=10, tau=12, prep_cost_ticks=5, cost_ticks=10)
    service = {"NOM":12, "primary_worst":10, "unseen":11}
    backlog = {"NOM":11, "primary_worst":12, "unseen":13}
    assert baseline.separation_choice(master, service, backlog, {}) == (
        "unseen", "CONDITIONAL_BACKLOG_VIOLATION", "primary_worst"
    )


def test_cost_only_checks_feasibility_and_never_ranks_risk(baseline):
    master = dict(ot=10, tau=12, prep_cost_ticks=5, cost_ticks=10)
    service = {"NOM":10, "new_a":11, "new_b":11}
    backlog = {"NOM":12, "new_a":11, "new_b":12}
    assert baseline.separation_choice(master, service, backlog, {"NOM":5,"new_a":6,"new_b":7}) == (
        "new_a", "ECONOMIC_FEASIBILITY_VIOLATION", "NOM"
    )
    assert baseline.separation_choice(master, service, backlog, {"NOM":5,"new_a":4,"new_b":5}) == (
        None, "CERTIFIED", "NOM"
    )


def test_resource_stop_cannot_return_optimal_certificate(baseline, monkeypatch):
    row = {"solver_status":"TIME_LIMIT", "exact":False}
    monkeypatch.setattr(baseline,"exact",lambda *args: row)
    evidence=[]
    with pytest.raises(baseline.Incomplete) as failure:
        baseline.solve_stage(None,None,None,"case","service",evidence)
    assert failure.value.row==evidence[0] and not evidence[0]["exact"]


def test_published_evidence_is_scoped_and_exact_when_certified():
    root=Path(__file__).resolve().parents[1]/"experiments/v33_gate4a_plain_ccg/evidence"
    report=json.loads((root/"gate4a_summary.json").read_bytes())
    bmax=json.loads((root/"gate4a_bmax.json").read_bytes())
    assert bmax["exact"] and bmax["mip_gap"]==bmax["prep_max_residual"]==0
    assert bmax["bmax_cents"]==bmax["objective"]==bmax["best_bound"]==23978005774
    assert bmax["budget_grid_cents"]==[0,22931054,5994501443,11989002887,17983504330,23978005774]
    with (root/"gate4a_iteration_profile.csv").open(encoding="utf8",newline="") as stream:
        iterations=list(csv.DictReader(stream))
    active=defaultdict(lambda:{"NOM"})
    for row in iterations:
        assert set(row["master_scenarios"].split(";"))==active[row["run"]]
        assert int(row["primary_lb"])<=int(row["primary_ub"]) and float(row["max_mip_gap"])==0
        if row["added"]:
            assert row["added"] not in active[row["run"]]
            active[row["run"]].add(row["added"])
    attempts=report["results"]
    assert report["PLAIN_CCG_CERTIFIED"]==(
        sum(r["method"]=="CCG" and r["status"]=="PASS" for r in attempts)==6 and
        sum(r["match"] for r in report["comparisons"])==2
    )
    with (root/"gate4a_final_replay.csv").open(encoding="utf8",newline="") as stream:
        replays=list(csv.DictReader(stream))
    for r in attempts:
        if r["status"]!="PASS" or r["method"]!="CCG":
            continue
        full=[row for row in replays if row["run"]==f'{r["case"]}_independent_replay']
        stage={tier:{row["scenario"]:float(row["objective"]) for row in full if row["level"]==tier}
               for tier in ("service","backlog","economics")}
        assert len(full)==3*{1:11,2:51}[r["gamma"]]
        assert stage["service"].keys()==stage["backlog"].keys()==stage["economics"].keys()
        assert min(stage["service"].values())==r["ot"] and max(stage["backlog"].values())==r["tau"]
        assert all(row["exact"]=="True" and float(row["mip_gap"])==0 for row in full)
        assert r["max_residual"]<=1e-6
    with (root/"sha256_manifest.csv").open(encoding="utf8",newline="") as stream:
        manifest=list(csv.DictReader(stream))
    for row in manifest:
        data=(root/row["path"]).read_bytes()
        assert len(data)==int(row["bytes"]) and hashlib.sha256(data).hexdigest()==row["sha256"]
