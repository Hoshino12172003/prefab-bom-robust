import csv
import json
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "artifacts/v3_phase32d3_20261112_171131"
POLICIES = ("P1", "P2", "P3", "P4")


def read(path):
    return json.loads((OUT / path).read_text(encoding="utf-8"))


def test_frozen_atoms_keep_equal_rhs_with_different_concurrency():
    audit = read("mapping_audit.json")
    assert read("preflight.json")["atomic_identities"] == 414
    assert audit["atomic_collision"]["first_legal"] != audit["atomic_collision"]["second_legal"]
    assert all(r["row_checks"] == 7 and r["all_atomic_profiles_pass_envelope_witness"] for r in audit["policies"])
    assert all(x["inventory_upper_slack"] > 0 for r in audit["policies"] for x in r["inventory_headroom"])


def test_gamma1_all_values_and_complete_worst_ties():
    for p in POLICIES:
        ref = read(f"reference/gamma1_{p}/G1_N355.json")
        search = read(f"search/{p}_G1_N355_L2/result.json")
        assert ref["full_milp"] == 355 and search["worst_rhs_complete"]
        assert ref["worst"] == search["worst"] == 11775
        assert ref["worst_rhs"] == search["worst_rhs"] and len(ref["worst_rhs"]) == 4


def test_ladders_include_real_three_event_cases_and_agree_with_reference():
    cases = read("benchmark_design.json")
    for name, case in cases.items():
        if case["gamma"] == 1:
            continue
        if case["gamma"] == 3:
            assert case["effective_family_counts"]["BGS"] > 0
        for p in POLICIES:
            ref = read(f"reference/ladder_{p}/{name}.json")
            search = read(f"search/{p}_{name}_L2/result.json")
            assert ref["worst"] == search["lower_bound"] == search["worst"] and search["exact"]
            assert ref["rhs_count"] == ref["full_milp"] + ref["matrix_replays"]
            assert ref["rhs_count"] == search["rhs_count"]
    for name in ("G2_N32", "G3_N64"):
        ref = read(f"reference/pointwise_small_P1/{name}.json")
        assert ref["full_milp"] == cases[name]["rhs_count"]
        for level in (0, 1, 2):
            assert ref["worst"] == read(f"search/P1_{name}_L{level}/result.json")["worst"]


def test_full_value_requires_independent_complete_root_coverage():
    for row in read("full_independent_certificate.json"):
        assert row["full_certificate"] and row["trajectories_covered"] == 2657350
        assert row["value"] == 11775 and row["root_branches"] == 414
        p = row["policy"]
        result = read(f"search/{p}_G3_FULL_L2/result.json")
        assert result["exact"] and result["frontier_size"] == 0
        assert result["lower_bound"] == row["value"] and result["total_full_milp"] == 6
        assert not result["worst_rhs_complete"]
        with (OUT / f"independent_full/{p}/root_branch_matrix_replay.csv").open(encoding="utf-8-sig") as stream:
            evidence = list(csv.DictReader(stream))
        assert len({r["event_id"] for r in evidence}) == 414
        assert 1+sum(int(r["represented_legal_trajectories"]) for r in evidence) == row["trajectories_covered"]
        assert all(int(r["matrix_residual"]) == 0 and int(r["witness_Q"]) >= row["value"] for r in evidence)
