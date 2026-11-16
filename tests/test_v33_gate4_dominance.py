import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "experiments/v33_gate4_dominance"


def test_partial_order_has_no_aggregate_capacity_shortcut():
    spec = importlib.util.spec_from_file_location("dominance_audit", ROOT / "audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    keep, cover, pairs = module.certify_cover({
        "a": {1:0, 2:2}, "b": {1:1, 2:0}, "c": {1:2, 2:3}, "duplicate_a": {1:0, 2:2},
    })
    assert keep == ["a", "b"] and cover == {"a":"a", "b":"b", "c":"a", "duplicate_a":"a"}
    assert not next(row for row in pairs if (row["harder"],row["other"])==("b","a"))["covers"]


def test_all_frozen_cover_witnesses_are_direct():
    for gamma, expected, representatives in ((1,11,5),(2,51,10)):
        with (ROOT / f"evidence/gamma{gamma}_cover.csv").open(newline="",encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with (ROOT / f"evidence/gamma{gamma}_pairs.csv").open(newline="",encoding="utf-8") as f:
            strict = {(r["harder"],r["other"]) for r in csv.DictReader(f) if r["strict"]=="True"}
        keep = {r["scenario"] for r in rows if r["retained"]=="True"}
        assert len(rows)==expected and len(keep)==representatives
        assert all(r["representative"] in keep for r in rows)
        assert all((r["representative"],r["scenario"]) in strict for r in rows if r["scenario"] not in keep)
