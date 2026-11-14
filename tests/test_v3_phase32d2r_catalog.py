import csv
import json
from itertools import combinations, product
from math import comb
from pathlib import Path

import numpy as np


OUT = Path(__file__).resolve().parents[1] / "artifacts/v3_phase32d2r_20261112_134524"
CATALOG = OUT / "multibom_effective_rhs_catalog"


def read(name):
    with (OUT / f"{name}.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_independent_raw_and_effective_counts():
    meta = json.loads((CATALOG / "rhs_coordinates.json").read_text(encoding="utf-8"))
    groups = meta["groups"]
    intervals = [frozenset(range(t, t+d)) for d in (4, 7, 11) for t in range(61, 76-d)]
    valid_triples = sum(not a & b & c for a, b, c in product(intervals, repeat=3))
    receipt_alternatives = {}
    for event in groups["B_RECEIPT"]["options"]:
        i, t, d = (event[k] for k in ("local_id", "start", "duration"))
        if i:
            receipt_alternatives.setdefault(i, set()).add(frozenset(range(t, t+d)))
    ordinary = [g for r, g in groups.items() if r != "B_RECEIPT"]
    assert all({o["local_id"] for o in g["options"]} == set(range(1, 70)) for g in ordinary)
    ordinary_options = 69
    receipt_options = len(receipt_alternatives)
    receipt_triples = sum(any(not a & b & c for a in alternatives)
                          for b, c in product(intervals, repeat=2)
                          for alternatives in receipt_alternatives.values()) * 3**2
    effective = (
        1,
        5*ordinary_options + receipt_options,
        comb(5, 2)*ordinary_options**2 + 5*ordinary_options*receipt_options,
        comb(5, 3)*valid_triples*3**3 + comb(5, 2)*receipt_triples,
    )
    legal = (1, 6*69, comb(6, 2)*69**2, comb(6, 3)*valid_triples*3**3)
    rows = [r for r in read("multibom_scenario_count_by_gamma") if r["family"] == "Total"]
    assert len(rows) == 3
    for gamma, row in enumerate(rows, 1):
        assert int(row["legal_trajectories"]) == sum(legal[:gamma+1])
        assert int(row["distinct_rhs"]) == sum(effective[:gamma+1])
    with np.load(CATALOG / "classes.npz") as archive:
        ids = archive["ids"]
        multiplicity = archive["exact_event_count_multiplicity"]
        assert ids[0] == 0 and np.all(ids[1:] > ids[:-1])
        assert tuple(multiplicity.sum(axis=1)) == legal
        assert tuple(np.bincount((multiplicity > 0).argmax(axis=0))) == effective


def test_family_counts_use_union_and_event_counts_are_disjoint():
    raw = read("multibom_scenario_count_by_gamma")
    effective = read("multibom_family_summary")
    for gamma in ("1", "2", "3"):
        total = next(r for r in raw if r["gamma_evt"] == gamma and r["family"] == "Total")
        rows = [r for r in effective if r["gamma_evt"] == gamma]
        assert sum(int(r["legal_event_family_trajectories"]) for r in rows) == int(total["legal_trajectories"])
        assert sum(int(r["globally_effective_family_rhs"]) for r in rows) == int(total["distinct_rhs"])
        assert sum(int(r["raw_family_distinct_rhs"]) for r in rows) > int(total["distinct_rhs"])
        table = {r["family"]: r for r in rows}
        assert all((int(table[f]["legal_event_family_trajectories"]) > 0) == (int(gamma) >= len(f))
                   for f in ("B", "G", "S", "BG", "BS", "GS", "BGS", "E", "BSE", "GSE"))


def test_joint_witness_rejects_all_four_tested_reductions():
    validation = json.loads((OUT / "validation_run.json").read_text(encoding="utf-8"))
    witness = validation["witness"]
    assert (witness["policy"], witness["scenario"], witness["integer_Q"]) == ("C", "BGS7", 18600)
    for key in ("branch_min", "additive", "battery_only_recursion", "scalar_due_prefix_dp"):
        assert witness[key] != witness["integer_Q"]
    value = 0
    for row in read("scalar_due_prefix_dp"):
        value = min(value+int(row["due_demand"]), min(json.loads(row["isolated_prefix_json"]).values()))
        assert value == int(row["scalar_DP"])
    assert value == witness["scalar_due_prefix_dp"] == 21350


def test_frozen_btb_sample_uses_exact_integer_recourse_and_no_pairs():
    rows = read("fixed_policy_full_milp")
    prefix = read("prefix_solver_calls")
    btb = read("multibom_btb_reaudit")
    assert len(rows) == 51 and len(prefix) == 42
    assert len({r["rhs_id"] for r in rows}) == 17
    for r in rows + prefix:
        assert r["status"] == "OPTIMAL" and int(r["integer_variables"]) == 75810
        assert int(r["Q"]) == float(r["bound"])
        assert float(r["gap"]) == float(r["matrix_residual"]) == float(r["solver_residual"]) == 0
        assert "Optimal solution found" in (OUT / r["log"]).read_text(encoding="utf-8")
    for r in btb:
        assert int(r["candidates"]) == int(r["individual_MILP"]) == 17
        assert all(int(r[k]) == 0 for k in ("eligible_seat_pairs", "pruned", "bound_exact", "common_MILP"))
        assert int(r["worst_subset_Q"]) == min(int(p["Q"]) for p in rows if p["policy"] == r["policy"])
