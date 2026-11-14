"""Assemble Phase 3.1R evidence and hash the delivered run files."""
import json
import platform
import re
import subprocess
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import run_matrix as run
from design import HERE, LABEL, ROOT, SOURCE
from prefab_v25.source import verified_bytes


REPORT = ROOT / "docs/v3_phase31r_multi_bom_risk_audit.md"
TESTS = ROOT / "tests/test_v3_phase31r_multi_bom.py"
ATTACHMENT = Path("private_inputs/attachment/已粘贴的文本.txt")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def main():
    prior = run.verify_frozen()
    fixed = run.read(HERE / "fixed_policy_multi_bom_service_audit.csv")
    de = run.read(HERE / "direct_de_multi_bom_scaling.csv")
    lp = run.read(HERE / "LP_relaxation_audit.csv")
    dp = run.read(HERE / "scalar_covering_prefix_dp.csv")
    pytest_exit = int((HERE / "pytest_exit_code.txt").read_text(encoding="utf-8"))
    pytest_log = (HERE / "pytest.txt").read_text(encoding="utf-8")
    test_count = int(re.search(r"(\d+) passed in", pytest_log)[1])
    assert pytest_exit == 0 and test_count == 60
    assert len(fixed) == 480 and len(de) == 3 and len(lp) == 7 and len(dp) == 14
    assert all(r["status"] == "OPTIMAL" and r["Q_direct"] == r["bound"]
               and float(r["gap"]) == 0 for r in fixed)
    assert all(r["status"] == "OPTIMAL" and float(r["Q"]) == float(r["bound"])
               and float(r["gap"]) == 0 and r["integer_matrix_replay"] == "True" for r in de)
    for script in [*HERE.glob("*.py"), TESTS]:
        compile(script.read_bytes(), str(script), "exec")
    git("diff", "--check")
    inputs = {p: run.digest(ROOT / p) for p in (
        "src/prefab_v3/__init__.py", "src/prefab_v3/base.py", "src/prefab_v3/interface.py",
        "src/prefab_v3/robust.py", "src/prefab_v25/__init__.py", "src/prefab_v25/data.py", "src/prefab_v25/source.py")}
    result = {
        "status": "PASS_MULTI_BOM_CCG_STRUCTURALLY_JUSTIFIED",
        "run_id": HERE.name,
        "scope": LABEL,
        "opening": "historical source state at t=60; model periods 61..74",
        "git_sha": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "source_dimensions": {"VIN": 28000, "items": 28049, "nodes": 12, "arcs": 11},
        "source_inputs": {"source_zip": str(SOURCE), "source_zip_sha256": run.digest(SOURCE),
                          "source_xlsb_sha256": sha256(verified_bytes(SOURCE)).hexdigest(),
                          "instruction": str(ATTACHMENT), "instruction_sha256": run.digest(ATTACHMENT),
                          "code_sha256": inputs, "frozen_phase_manifests_verified": prior},
        "environment": {"python": platform.python_version(), "gurobi": run.gp.gurobi.version(),
                        "gurobi_license": "usable for observed full-size solves",
                        "libraries": {p: version(p) for p in ("numpy", "pyxlsb", "psutil", "pytest")}},
        "design": {"first_stage": ["x_C", "x_T", "x_O"], "x_C_kit": [10, 6, 4],
                   "stage_one_costs": [str(c) for c in run.COSTS], "budget_K": list(run.KS),
                   "policy_count": 20, "initial_scenarios_including_control": 21,
                   "overlap_sensitivity_scenarios": 3, "exposure_budgets": [2, 4, 6],
                   "standalone_stress_outside_exposure_budgets": ["S_7", "E_11"]},
        "fixed_policy_results": {"optimal": len(fixed),
                                 "maximum_solver_residual": max(float(r["solver_residual"]) for r in fixed),
                                 "maximum_exact_matrix_residual": max(int(r["exact_matrix_residual"]) for r in fixed),
                                 "battery_only_and_control_replays": 80,
                                 "battery_prefix_mismatches": sum(int(r["prefix_overestimate"]) != 0 for r in fixed),
                                 "independent_min_mismatches": sum(int(r["min_overestimate"]) != 0 for r in fixed),
                                 "additive_loss_mismatches": sum(int(r["additive_error"]) != 0 for r in fixed),
                                 "joint_cases_with_late_deliveries_in_witness": sum(
                                     int(r["late_outflow"]) > 0 and len(json.loads(r["isolated_service"])) > 1
                                     for r in fixed)},
        "nonseparability": {"marker": "NONTRIVIAL_MULTI_BOM_INTEGER_RECOURSE_CONFIRMED",
                           "policy": [915, 0, 0], "scenario": "BGS_OVERLAP",
                           "Q": 25991, "isolated_min": 26465, "isolated_additive_loss": 25128,
                           "lp_upper_bound": 25991.5, "lp_models_solved": len(lp),
                           "positive_lp_integer_gaps": sum(float(r["LP_gap"]) > 0 for r in lp),
                           "scalar_covering_prefix_mip_solves": 2*len(dp),
                           "scalar_covering_scenario": "BS", "scalar_covering_upper_bound": int(dp[-1]["scalar_covering_dp"]),
                           "restored_receipts_storage_headroom": int(dp[-1]["restored_receipts_storage_headroom"]),
                           "scope": "tested scalar recursions and unrounded complete LP"},
        "finite_de": [json.loads((HERE / f"de_{n:02d}_result.json").read_text(encoding="utf-8")) for n in (4, 8, 16)],
        "structural_gate": {"source_supported_branches": True, "joint_witness": True,
                            "tested_simple_reductions_refuted": True, "measured_de_growth": True,
                            "DE_scenario_levels_not_run": [32, 64],
                            "prospective_risk_calibration": False,
                            "full_uncertainty_set_worst_case_certified": False,
                            "algorithmic_necessity_or_speedup_established": False},
        "gurobi_mip_parameters": {"Threads": 1, "Seed": 20261110, "MIPGap": 0, "MIPGapAbs": 0,
                                  "FeasibilityTol": 1e-9, "IntFeasTol": 1e-9, "OptimalityTol": 1e-9,
                                  "Presolve": "AUTO", "LogToConsole": 0, "fixed_and_prefix_TimeLimit": 45,
                                  "de_TimeLimit": 90, "de_SoftMemLimit_GB": 3},
        "pytest": {"passed": test_count, "failed": 0, "exit_code": pytest_exit,
                   "scope": "9 relevant test modules, including 7 new tests", "output": "pytest.txt",
                   "command": pytest_log.splitlines()[0]},
        "syntax_compile_exit_code": 0,
        "git_diff_check_exit_code": 0,
        "solver_logs": sum(1 for _ in (HERE / "logs").glob("*.log")),
        "phase31r_ccg_calls": 0,
        "phase31r_formal_prospective_solver_calls": 0,
        "stopped_after_phase31r": True,
    }
    (HERE / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = HERE / "sha256_manifest.csv"
    files = [p for p in HERE.rglob("*") if p.is_file() and p != manifest]
    files += [REPORT, TESTS]
    records = [dict(path=p.relative_to(ROOT).as_posix(), sha256=run.digest(p)) for p in sorted(files)]
    run.write(manifest.name, records)
    assert all(run.digest(ROOT / r["path"]) == r["sha256"] for r in run.read(manifest))
    print(result["status"], f"{len(records)} files verified")


if __name__ == "__main__":
    main()
