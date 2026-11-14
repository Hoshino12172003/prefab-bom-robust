"""Validate comparison completeness and publish the machine-readable audit."""

import csv
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from prepare import D2R, D2R_AUDIT, HERE, ROOT, Coordinates, explicit_classes, frozen_catalog, policies, read
from replay_search import json_lines


def output(name, rows):
    frozen_catalog.write(HERE / name, rows)


def main(instruction):
    cases = read(HERE / "benchmark_design.json")
    policy = policies()
    preflight = read(HERE / "preflight.json")
    assert frozen_catalog.verify_manifest(D2R) == preflight["d2r_manifest"]
    prior = read(D2R_AUDIT)
    frozen = {n: frozen_catalog.verify_manifest(ROOT / "artifacts" / n, info)
              for n, info in prior["frozen_inputs"].items()}
    assert frozen_catalog.digest(frozen_catalog.frozen.SOURCE) == prior["source_zip_sha256"]
    mapping = read(HERE / "mapping_audit.json")
    assert mapping["atomic_collision"]["first_legal"] != mapping["atomic_collision"]["second_legal"]
    replay = read(HERE / "search_replay.json")
    independent = {r["policy"]: r for r in read(HERE / "full_independent_certificate.json")}
    assert len(replay) == 52 and all(r["full_certificate"] for r in independent.values())
    assert int((HERE / "pytest_exit_code.txt").read_text(encoding="utf-8-sig")) == 0
    test_log = (HERE / "pytest.txt").read_text(encoding="utf-8-sig")
    tests = len(re.findall(r"^(tests/[^\r\n]+?) PASSED ", test_log, re.MULTILINE))
    assert tests and re.search(rf"=+ {tests} passed in ", test_log)
    ids, mult, ranks = explicit_classes(Coordinates())
    ref_ids = {}
    for name, case in cases.items():
        mask = mult[:case["gamma"]+1].sum(axis=0) > 0
        if case["threshold"] is not None:
            mask &= ranks <= case["threshold"]
        ref_ids[name] = set(map(int, ids[mask]))

    refs, summaries, compare, policy_rows = {}, [], defaultdict(list), []
    ref_modes = ("gamma1", "ladder", "pointwise_small")
    for mode in ref_modes:
        for p in policy if mode != "pointwise_small" else ("P1",):
            out = HERE / "reference" / f"{mode}_{p}"
            by_case = defaultdict(list)
            for row in json_lines(out / "class_certificates.jsonl"):
                by_case[row["case"]].append(row)
            for name, rows in by_case.items():
                ref = read(out / f"{name}.json")
                assert len(rows) == ref["rhs_count"] == cases[name]["rhs_count"]
                assert {r["rhs_id"] for r in rows} == ref_ids[name]
                assert min(r["certified_q"] for r in rows if r["exact_q"]) == ref["worst"]
                assert all(r["certified_q"] >= ref["worst"] for r in rows)
                counter = Counter(r["proof"] for r in rows)
                assert counter["FULL_MILP"] == ref["full_milp"]
                assert counter["FEASIBLE_INTEGER_MATRIX_REPLAY"] == ref["matrix_replays"]
                if mode != "ladder":
                    assert ref["full_milp"] == ref["rhs_count"]
                    assert ref["worst_rhs"] == sorted(r["rhs_id"] for r in rows if r["certified_q"] == ref["worst"])
                refs[mode, p, name] = ref

    columns = ("gamma", "raw_count", "rhs_count", "level", "exact", "worst", "worst_rhs_complete", "lower_bound",
               "visited_nodes", "pruned_nodes", "dominance_pruned_nodes", "envelope_calls", "exact_recourse_calls",
               "cache_hits", "envelope_cache_hits", "witness_bounds", "total_full_milp", "evaluation_fraction",
               "leaf_evaluation_fraction", "incumbent_updates", "total_wall_seconds", "peak_bytes",
               "frontier_size", "stop")
    nodes, results = [], {}
    for path in sorted((HERE / "search").glob("*/result.json")):
        ans = read(path)
        name, p, level, gamma = (ans[k] for k in ("case", "policy", "level", "gamma"))
        results[p, name, level] = ans
        row = dict(policy=p, case=name, **{key: ans[key] for key in columns},
                   worst_events="|".join(map(str, ans["worst_events"])))
        summaries.append(row)
        for r in json_lines(path.parent / "nodes.jsonl"):
            nodes.append(dict(policy=p, case=name, level=level, **r))
        if name == "G3_FULL":
            assert ans["exact"] and ans["frontier_size"] == 0
            assert independent[p]["value"] == ans["worst"] == ans["lower_bound"]
            assert independent[p]["trajectories_covered"] == ans["raw_count"]
            continue
        mode = "gamma1" if gamma == 1 else "ladder"
        ref = refs[mode, p, name]
        strict = gamma == 1
        assert ans["exact"] and ref["exact"] and ans["worst"] == ref["worst"] and ans["rhs_count"] == ref["rhs_count"]
        assert ans["lower_bound"] == ans["worst"]
        assert not strict or (ref["worst_rhs_complete"] and ans["worst_rhs_complete"] and ans["worst_rhs"] == ref["worst_rhs"])
        assert sum(r["single_rhs"] for r in ans["worst_event_details"]) in ref_ids[name]
        if level == 2:
            pointwise = refs.get(("pointwise_small", p, name))
            assert pointwise is None or pointwise["worst"] == ans["worst"]
            compare[gamma].append(dict(**row, reference_mode=ref["mode"], reference_worst=ref["worst"],
                reference_full_milp=ref["full_milp"], reference_matrix_replays=ref["matrix_replays"],
                reference_wall_seconds=ref["wall_seconds"], reference_peak_bytes=ref["peak_bytes"],
                exact_match=True, complete_tie_set_match=True if strict else None,
                complete_tie_count=len(ref["worst_rhs"]) if strict else None,
                pointwise_small_full_milp=None if pointwise is None else pointwise["full_milp"],
                pointwise_small_worst=None if pointwise is None else pointwise["worst"],
                pointwise_small_wall_seconds=None if pointwise is None else pointwise["wall_seconds"]))
    for p, x in policy.items():
        a, b = results[p, "G1_N355", 2], results[p, "G3_FULL", 2]
        assert a["worst"] == b["worst"]
        policy_rows.append(dict(policy=p, x_C=x[0], x_T=x[1], x_O=x[2], gamma1_worst=a["worst"],
                                gamma1_milp=a["total_full_milp"], gamma1_ties=len(a["worst_rhs"]),
                                gamma2_full_value_by_nesting=a["worst"],
                                gamma3_worst=b["worst"], gamma3_lower=b["lower_bound"],
                                gamma3_leaf_milp=b["exact_recourse_calls"], gamma3_envelope_milp=b["envelope_calls"],
                                gamma3_wall_seconds=b["total_wall_seconds"], gamma3_peak_bytes=b["peak_bytes"],
                                gamma3_frontier=b["frontier_size"], gamma3_complete_ties=b["worst_rhs_complete"],
                                full_matrix_branch_replays=independent[p]["root_branches"]))
    assert {gamma: len(rows) for gamma, rows in compare.items()} == {1: 4, 2: 20, 3: 20}
    files = {1: "implicit_vs_enumeration_gamma1.csv", 2: "implicit_vs_enumeration_gamma2.csv",
             3: "implicit_vs_enumeration_gamma3_subsets.csv"}
    for gamma, rows in compare.items():
        output(files[gamma], sorted(rows, key=lambda r: (r["rhs_count"], r["policy"])))
    output("implicit_policy_comparison.csv", policy_rows)
    output("implicit_scalability_summary.csv", summaries)
    output("implicit_search_iteration_log.csv", nodes)

    calls = [r for path in (HERE / "reference").glob("*/solver_calls.jsonl") for r in json_lines(path)]
    searches = [r for path in (HERE / "search").glob("*/solver_calls.jsonl") for r in json_lines(path)]
    mapping_calls = [r for path in (HERE / "mapping_audit").glob("*/solver_calls.json") for r in read(path)]
    fresh = [r for path in (HERE / "independent_full").glob("*/independent_solver_calls.json") for r in read(path)]
    assert all(r["status"] == 2 and r["q"] == r["objective_bound"] and r["gap"] == r["matrix_residual"] == 0
               for r in calls+searches+mapping_calls)
    assert all(r["Q"] == r["bound"] and r["gap"] == r["matrix_residual"] == 0 for r in fresh)
    maximum_residual = max([r["residual"] for r in calls+searches+mapping_calls] + [r["solver_residual"] for r in fresh])
    status = "PASS_IMPLICIT_EVENT_SEPARATION_EXACT_PROTOTYPE"
    assert all(r["gamma3_leaf_milp"]+r["gamma3_envelope_milp"] < 0.01*1564150 for r in policy_rows)
    cert = dict(status=status, gamma1_complete_worst_rhs=read(HERE / "gamma1_gate.json"),
                matched_benchmarks={gamma: len(rows) for gamma, rows in compare.items()},
                full_independent_certificate=independent, full_worst_value_only=True,
                gamma2_full_value_by_nesting={r["policy"]: r["gamma2_full_value_by_nesting"] for r in policy_rows},
                all_logged_prunes_replayed=sum(r["certified_prunes"] for r in replay),
                maximum_solver_residual=maximum_residual,
                maximum_integer_matrix_residual=0, approximate_or_incomplete_runs=0)
    frozen_catalog.dump(HERE / "implicit_exactness_certificate.json", cert)
    audit = dict(status=status, git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                 instruction_sha256=frozen_catalog.digest(instruction), source_zip_sha256=prior["source_zip_sha256"],
                 frozen_d2r_manifest=preflight["d2r_manifest"], frozen_manifests=frozen, scope="HISTORICAL_STRESS_TEST_ONLY",
                 gamma=[1, 2, 3], K=2, preflight=preflight, benchmark_design=cases,
                 g2_full_exhaustive_reference="NOT_RUN_OPTIONAL_51070_CLASSES; VALUE_CERTIFIED_BY_NESTING",
                 mapping=mapping, certificate=cert, pytest_passed=tests, pytest_failed=0,
                 gurobi=refs["gamma1", "P1", "G1_N355"]["gurobi"],
                 solver_calls=dict(reference=len(calls), implicit=len(searches), mapping_audit=len(mapping_calls),
                                   independent_full_verification=len(fresh)),
                 btb_role="BTB_NOT_PRIMARY_FULL_SET_MECHANISM", btb_used_for_order_and_skip_envelope_only=True,
                 outer_ccg_run=False, new_outer_algorithm=False)
    frozen_catalog.dump(HERE / "audit.json", audit)
    manifest = HERE / "sha256_manifest.csv"
    paths = [p for p in HERE.rglob("*") if p.is_file() and p != manifest]
    paths += [ROOT / p for p in ("src/prefab_v3/event_search.py", "tests/test_v3_phase32d3_event_search.py",
                                 "tests/test_v3_phase32d3_artifacts.py", "docs/v3_phase32d3_implicit_event_separation.md")]
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("path", "sha256"))
        writer.writerows((p.relative_to(ROOT).as_posix(), frozen_catalog.digest(p)) for p in sorted(paths))
    print(status, "comparisons", cert["matched_benchmarks"], "tests", tests, "calls", audit["solver_calls"])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
