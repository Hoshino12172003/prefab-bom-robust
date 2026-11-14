"""Assemble timing and structural evidence after the diagnostic solves."""
import json
import platform
import re
import statistics
import subprocess
from collections import Counter
from pathlib import Path

from profile_runs import FROZEN, HERE, LABEL, PHASE_A, ROOT, verify_frozen, write_csv

JOBS = [
    (4, "PLAIN"), (8, "PLAIN"), (16, "PLAIN"), (16, "TWO"), (16, "BATCH2"), (16, "BATCH4"),
    (24, "DIRECT"), (24, "INIT_A"), (24, "INIT_B"), (24, "INIT_C"), (24, "INIT_D"), (24, "INIT_E"),
    (32, "DIRECT"), (32, "PLAIN"),
]
INIT = {
    "INIT_A": "Fixed arbitrary DE_ENGINE_68",
    "INIT_B": "NR plus maximum multi-branch severity-days, ties by greatest ID",
    "INIT_C": "Maximum effective resource-period Jaccard distance, then resource union, start-date difference, IDs",
    "INIT_D": "Uniform without replacement, Python Random seed 20261111",
    "INIT_E": "NR plus worst of three prespecified exact pilot MILPs at zero investment",
}
REPORT = ROOT/"docs/v3_phase32b_ccg_bottleneck_analysis.md"
TEST = ROOT/"tests/test_v3_phase32b_audit.py"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def solver_sections(path):
    log = path.read_text(encoding="utf-8")
    pre = re.search(r"Presolve time: ([\d.]+)s", log)
    root = re.search(r"Root relaxation:.*?, ([\d.]+) seconds", log)
    size = re.search(r"Presolved: ([\d,]+) rows, ([\d,]+) columns, ([\d,]+) nonzeros", log)
    removed_all = "All rows and columns removed" in log
    return dict(presolve_seconds=float(pre[1]) if pre else "",
                root_lp_seconds=float(root[1]) if root else "",
                presolved_rows=int(size[1].replace(",", "")) if size else 0 if removed_all else "",
                presolved_columns=int(size[2].replace(",", "")) if size else 0 if removed_all else "",
                presolved_nonzeros=int(size[3].replace(",", "")) if size else 0 if removed_all else "")


def phases(rows):
    parts = dict(
        MP_solve=sum(r["solve_wall_seconds"] for r in rows if r["kind"] in ("MASTER", "DIRECT")),
        oracle_solve=sum(r["solve_wall_seconds"] for r in rows if r["kind"] in ("ORACLE", "PILOT")),
        verification_solve=sum(r["solve_wall_seconds"] for r in rows if r["kind"] == "VERIFY"),
        build=sum(r["build_seconds"] for r in rows),
    )
    return parts, sum(parts.values())


def aggregate():
    maximal = [(38, "DIRECT"), (38, "PLAIN")]
    jobs = JOBS + (maximal if all((HERE/f"n{n:02d}_{m}.json").is_file() for n, m in maximal) else [])
    runs = [read_json(HERE/f"n{n:02d}_{m}.json") for n, m in jobs]
    by_case = {(r["n"], r["method"]): r for r in runs}
    assert len(by_case) == len(jobs)
    de = {n: read_json(PHASE_A/f"n{n:02d}_DIRECT_DE.json")["objective"] for n in (4, 8, 16)}
    de.update({r["n"]: r["Q"] for r in runs if r["method"] == "DIRECT" and r["status"] == "EXACT_FINITE"})
    assert len({r["Q"] for r in runs if r["n"] == 24 and r["method"] in INIT and r["status"] == "EXACT_FINITE"}) == 1
    timing, detailed, init, scaling, batch, violations, oracle, active = [], [], [], [], [], [], [], []
    for n in (4, 8, 16):
        prior = read_json(PHASE_A/f"n{n:02d}_DIRECT_DE.json")
        q = prior["largest"]
        scaling.append(dict(label=LABEL, n=n, method="DIRECT_PHASE32A", kind="DIRECT", tag="archived", blocks=n,
            integers=q["integers"], rows=q["constraints"], nonzeros=q["nonzeros"], gurobi_seconds=q["solver_seconds"],
            nodes=q["nodes"], status=2, peak_process_bytes=prior["peak_process_bytes"],
            gurobi_peak_gb=q["gurobi_peak_gb"], log=f"{PHASE_A.name}/{q['log']}",
            **solver_sections(PHASE_A/q["log"])))
    for r in runs:
        n, method, records = r["n"], r["method"], r["records"]
        assert records and r["label"] == LABEL
        if r["status"] == "EXACT_FINITE":
            assert set(r["verify"]) == set(r["names"]) and min(r["verify"].values()) == r["Q"]
            if n in de:
                assert r["Q"] == de[n]
        for q in records:
            parts = solver_sections(HERE/q["log"])
            remaining = (max(0, q["gurobi_seconds"]-parts["root_lp_seconds"]-parts["presolve_seconds"])
                         if isinstance(parts["root_lp_seconds"], float) and isinstance(parts["presolve_seconds"], float)
                         else "")
            detailed.append(dict(label=LABEL, n=n, method=method, **q, **parts,
                                 solver_other_than_reported_presolve_root_seconds=remaining,
                                 python_outside_build_solve_seconds=q["job_wall_seconds"]-q["build_seconds"]-q["solve_wall_seconds"]))
            if q["kind"] in ("MASTER", "DIRECT"):
                scaling.append(dict(label=LABEL, n=n, method=method, kind=q["kind"], tag=q["tag"],
                    blocks=(q["integers"]-4)//75810, integers=q["integers"], rows=q["rows"],
                    nonzeros=q["nonzeros"], gurobi_seconds=q["gurobi_seconds"], nodes=q["nodes"],
                    status=q["status"], peak_process_bytes=q["peak_process_bytes"],
                    gurobi_peak_gb=q["gurobi_peak_gb"], log=q["log"], **parts))
        def time_row(scope, subset, wall):
            parts, classified = phases(subset)
            other = wall-classified
            assert other >= -1e-6
            return dict(label=LABEL, n=n, method=method, scope=scope, status=r["status"], wall_seconds=wall,
                        **{f"{k}_seconds": v for k, v in parts.items()}, other_seconds=other,
                        master_build_seconds=sum(q["build_seconds"] for q in subset if q["kind"] in ("MASTER", "DIRECT")),
                        oracle_job_wall_seconds=sum(q["job_wall_seconds"] for q in subset if q["kind"] in ("ORACLE", "PILOT")),
                        verification_job_wall_seconds=sum(q["job_wall_seconds"] for q in subset if q["kind"] == "VERIFY"),
                        serialization_seconds=sum(q["serialization_seconds"] for q in subset), solves=len(subset))
        timing.append(time_row("RUN", records, r["wall_seconds"]))
        by_phase = {
            "VERIFY": [q for q in records if q["kind"] == "VERIFY"],
            "PILOT": [q for q in records if q["kind"] == "PILOT"],
        }
        for it in r["iterations"]:
            i = it["iteration"]
            key = f"ROUND_{i:02d}"
            by_phase[key] = [q for q in records if q["tag"] in (f"round_{i:02d}", f"oracle_{i:02d}")]
            assert sum(q["kind"] == "ORACLE" for q in by_phase[key]) == n
        for scope, subset in by_phase.items():
            if subset:
                timing.append(time_row(scope, subset, sum(q["job_wall_seconds"] for q in subset)))
        oracle_q = [q for q in records if q["kind"] == "ORACLE"]
        if oracle_q:
            costs = [q["job_wall_seconds"] for q in oracle_q]
            mean = statistics.mean(costs)
            oracle.append(dict(label=LABEL, n=n, method=method, oracle_calls=len(costs),
                mean_recourse_wall_s=mean, median_recourse_wall_s=statistics.median(costs),
                sum_recourse_wall_s=sum(costs), sum_recourse_build_s=sum(q["build_seconds"] for q in oracle_q),
                sum_recourse_solve_s=sum(q["solve_wall_seconds"] for q in oracle_q),
                extrapolated_one_pass_38527_serial_hours=mean*38527/3600, measured_38527=False))
        if method in INIT:
            parts, _ = phases(records)
            direct = by_case[n, "DIRECT"]
            relation = ("SAME_REPRESENTATIVE" if r["policy"] == direct["policy"] else "ALTERNATIVE_ROBUST_OPTIMUM"
                        ) if r["status"] == direct["status"] == "EXACT_FINITE" else "UNCERTIFIED_COMPARISON"
            init.append(dict(label=LABEL, n=n, variant=method, rule=INIT[method], status=r["status"],
                initial_blocks="|".join(r["initial"]), iterations=len(r["iterations"]), final_blocks=len(r["final"]),
                Q=r["Q"], policy=r["policy"], policy_comparison=relation, total_seconds=r["wall_seconds"],
                MP_solve_seconds=parts["MP_solve"], oracle_solve_seconds=parts["oracle_solve"],
                oracle_elapsed_seconds=sum(q["job_wall_seconds"] for q in records if q["kind"] == "ORACLE"),
                pilot_elapsed_seconds=sum(q["job_wall_seconds"] for q in records if q["kind"] == "PILOT"),
                peak_process_bytes=r["peak_process_bytes"]))
        if n == 16 and method in ("PLAIN", "BATCH2", "BATCH4"):
            row = next(q for q in timing if q["n"] == n and q["method"] == method and q["scope"] == "RUN")
            largest = max(q["integers"] for q in records if q["kind"] == "MASTER")
            batch.append(dict(label=LABEL, n=n, method=method, status=r["status"], Q=r["Q"],
                iterations=len(r["iterations"]), final_blocks=len(r["final"]), largest_master_integers=largest,
                largest_master_constraints=max(q["rows"] for q in records if q["kind"] == "MASTER"),
                total_seconds=r["wall_seconds"], MP_solve_seconds=row["MP_solve_seconds"],
                oracle_solve_seconds=row["oracle_solve_seconds"], peak_process_bytes=r["peak_process_bytes"]))
            for it in r["iterations"]:
                round_values = {q["name"]: q["value"] for q in oracle_q if q["tag"] == f"oracle_{it['iteration']:02d}"}
                ranked = sorted((value, name) for name, value in round_values.items() if value < it["upper"])
                for rank, (value, name) in enumerate(ranked, 1):
                    violations.append(dict(label=LABEL, method=method, iteration=it["iteration"],
                        rank=rank, scenario=name, Q=value, UB=it["upper"], deficit=it["upper"]-value,
                        gap_to_exact_worst=value-min(round_values.values())))
        if r["status"] == "EXACT_FINITE":
            attach_usage(active, r, "PHASE32B")
    for n in (4, 8, 16):
        for m in ("CCG_MINIMAL", "CCG_INFORMED"):
            old = read_json(PHASE_A/f"n{n:02d}_{m}.json")
            r = dict(n=n, method=m, names=old["benchmark"], verify=old["verified"], Q=old["objective"],
                     initial=old["initial"], final=old["final"], iterations=old["iterations"])
            attach_usage(active, r, "PHASE32A_FROZEN")
    primary = [r for r in active if (r["source"] == "PHASE32A_FROZEN" and r["method"] == "CCG_MINIMAL")
               or (r["source"] == "PHASE32B" and (r["method"], r["n"]) in (
                   ("INIT_A", 24), ("PLAIN", 32), ("PLAIN", 38)))]
    frequencies = []
    for name in dict.fromkeys(r["scenario"] for r in primary):
        subset = [r for r in primary if r["scenario"] == name]
        frequencies.append(dict(label=LABEL, scenario=name, benchmark_families=len(subset),
            added_frequency=sum(r["added"] for r in subset), final_worst_frequency=sum(r["final_worst"] for r in subset),
            oracle_worst_frequency=sum(r["oracle_worst_rounds"] for r in subset),
            transient_only_frequency=sum(r["only_transiently_worst"] for r in subset),
            never_worst=all(not r["final_worst"] and r["oracle_worst_rounds"] == 0 for r in subset)))
    files = {
        "ccg_runtime_decomposition.csv": timing, "ccg_solve_profile.csv": detailed,
        "ccg_initialization_audit.csv": init, "ccg_active_scenario_audit.csv": active,
        "active_scenario_frequency.csv": frequencies, "batch_scenario_addition_audit.csv": batch,
        "batch_violation_detail.csv": violations, "master_scaling_audit.csv": scaling, "oracle_scaling_audit.csv": oracle,
    }
    for path, rows in files.items():
        write_csv(path, rows)
    return runs, de


def attach_usage(out, r, source):
    added, worst = set(), Counter()
    for it in r["iterations"]:
        a = it["added_scenario"]
        added.update(([a] if a else []) if isinstance(a, str) else a)
        worst.update(it["worst_ties"])
    ties = [n for n in r["names"] if r["verify"][n] == r["Q"]]
    for n in r["names"]:
        out.append(dict(label=LABEL, n=r["n"], method=r["method"], source=source, scenario=n,
            added=n in added, initial=n in r["initial"], final_master=n in r["final"], final_worst=n in ties,
            oracle_worst_rounds=worst[n], only_transiently_worst=bool(worst[n]) and n not in ties,
            never_worst=not worst[n] and n not in ties, final_worst_tie_count=len(ties),
            verified_service=r["verify"][n]))


def main():
    inputs = verify_frozen()
    runs, de = aggregate()
    structure = read_json(HERE/"structure_summary.json")
    reach = FROZEN.read(HERE/"reachability_safe_bounds.csv")
    exact_policies = {r["policy_id"] for r in reach if r["certified_exact_without_individual_solve"] == "True"}
    strict = sum(r["certified_nonworst_at_pilot"] == "True" for r in reach)
    status = ("PASS_BOTTLENECK_IDENTIFIED_ENHANCEMENT_JUSTIFIED"
              if len(exact_policies) == 2 and strict else "HOLD_ONLY_GENERIC_CCG_ENHANCEMENTS_FOUND")
    assert all(r["used_to_skip_any_plain_solve"] == "False" for r in reach)
    for r in runs:
        print(r["n"], r["method"], r["status"], r["Q"], len(r["iterations"]), len(r["final"]),
              round(r["wall_seconds"], 2), round(r["peak_process_bytes"]/2**30, 3))
    if not (HERE/"pytest_exit_code.txt").is_file() or not REPORT.is_file():
        return
    assert len(runs) == len(JOBS) + 2
    assert int((HERE/"pytest_exit_code.txt").read_text(encoding="utf-8")) == 0
    output = (HERE/"pytest.txt").read_text(encoding="utf-8")
    passed = int(re.search(r"(\d+) passed in", output)[1])
    for p in (*HERE.glob("*.py"), TEST):
        compile(p.read_bytes(), str(p), "exec")
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    git = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, encoding="utf-8").strip()
    attachment = Path.home()/"private_inputs/attachment/已粘贴的文本.txt"
    audit = dict(status=status, label=LABEL, git_sha=git, frozen_inputs=inputs, python=platform.python_version(),
        gurobi="13.0.1", input_zip_sha256=FROZEN.digest(FROZEN.SOURCE), instruction_sha256=FROZEN.digest(attachment),
        platform=platform.platform(),
        common_solver_parameters=dict(Threads=1, Seed=20261110, MIPGap=0, MIPGapAbs=0,
            FeasibilityTol=1e-9, IntFeasTol=1e-9, OptimalityTol=1e-9, Presolve="AUTO"),
        structure=structure, direct_certified_objectives=de,
        runs=[{k: r[k] for k in ("n", "method", "status", "Q", "policy", "wall_seconds", "peak_process_bytes",
                                 "available_bytes_at_start", "time_limit_s", "soft_mem_gb")} for r in runs],
        candidate="E4 BOM-time service bounds plus common integer witness for compatible scenario groups",
        candidate_used_in_plain=False, formal_enhancement_implemented=False, stopped_after_phase32b=True,
        full_combinatorial_separation=False, uncertainty_status="HOLD_UNCERTAINTY_CALIBRATION",
        probe_cases=len(reach), strict_nonworst_proofs=strict,
        exact_sandwiches=sum(r["certified_exact_without_individual_solve"] == "True" for r in reach),
        solver_logs=sum(1 for p in (HERE/"logs").glob("*.log") if p.stat().st_size),
        pytest_passed=passed, pytest_exit_code=0, git_diff_check_exit_code=0, syntax_compile_exit_code=0)
    (HERE/"audit.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    manifest = HERE/"sha256_manifest.csv"
    files = [p for p in HERE.rglob("*") if p.is_file() and p != manifest]
    files += [REPORT, TEST]
    rows = [dict(path=p.relative_to(ROOT).as_posix(), sha256=FROZEN.digest(p)) for p in sorted(files)]
    write_csv(manifest.name, rows)
    assert all(FROZEN.digest(ROOT/r["path"]) == r["sha256"] for r in FROZEN.read(manifest))
    print(status, len(rows), "files verified")


if __name__ == "__main__":
    main()
