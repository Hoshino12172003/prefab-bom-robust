"""Independently check the recorded bounds against DE and assemble deliverables."""
import csv
import json
import platform
import re
import subprocess
from collections import Counter
from hashlib import sha256
from pathlib import Path

from run_benchmark import (BASELINE, BUDGET, COSTS, COUNTS, FROZEN, HERE, LABEL, METHODS,
                           ROOT, SEVERE, ccg, frozen, verify_inputs)
from prefab_v25.source import verified_bytes


ATTACHMENT = Path.home() / "private_inputs/attachment/已粘贴的文本.txt"
REPORT = ROOT / "docs/v3_phase32a_plain_ccg.md"
TEST = ROOT / "tests/test_v3_phase32a_plain_ccg.py"
SOURCE = ROOT / "src/prefab_v3/plain_ccg.py"


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def write_csv(name, rows):
    # The Phase 3.1R writer targets its own run directory. Keep it read-only.
    with (HERE / name).open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def fingerprint(path):
    return re.search(r"Model fingerprint: (0x[0-9a-f]+)", path.read_text(encoding="utf-8"))[1]


def evidence():
    iterations, comparisons, policies, usage, evaluations, cases = [], [], [], [], [], []
    for n in COUNTS:
        runs = {m: json.loads((HERE/f"n{n:02d}_{m}.json").read_text(encoding="utf-8")) for m in METHODS}
        direct = runs["DIRECT_DE"]
        optimum = direct["objective"]
        families = tuple(direct["benchmark"])
        current_fp = fingerprint(HERE / direct["largest"]["log"])
        archived_fp = fingerprint(FROZEN / f"logs/DE_{n:02d}.log")
        assert current_fp == archived_fp
        case = dict(n=n, benchmark=families, direct_objective=optimum, direct_model_fingerprint=current_fp,
                    matches_frozen_direct_fingerprint=True, method_certificates=[])
        for method, r in runs.items():
            assert tuple(r["benchmark"]) == families
            if r["objective"] != optimum:
                raise RuntimeError(f"HOLD_CCG_DE_MISMATCH: {n} {method}")
            assert r["certification"] == "EXACT_FINITE" and len(set(r["final"])) == len(r["final"])
            assert set(r["final"]) <= set(families)
            assert str(sum(c*v for c, v in zip(COSTS, r["policy"], strict=True))) == r["cost"]
            expected_initial = {"DIRECT_DE": [], "CCG_MINIMAL": [BASELINE],
                                "CCG_INFORMED": [BASELINE, SEVERE]}
            assert r["initial"] == expected_initial[method]
            if method == "DIRECT_DE":
                assert tuple(r["final"]) == families
            per_round = {}
            for ev in r["oracle"]:
                round_records = per_round.setdefault(ev["evaluation"], {})
                assert ev["scenario"] not in round_records
                assert ev["solver_objective"] == ev["service"] == ev["solver_bound"] and ev["solver_gap"] == 0
                assert ev["status"] == "OPTIMAL" and ev["exact_matrix_residual"] == 0
                assert (HERE / ev["log"]).is_file()
                round_records[ev["scenario"]] = ev
                evaluations.append(dict(label=LABEL, n=n, method=method, **ev))
            for records in per_round.values():
                assert set(records) == set(families)
            fresh = per_round["verify"]
            assert all(ev["policy"] == r["policy"] for ev in fresh.values())
            assert r["verified"] == {s: ev["service"] for s, ev in fresh.items()}
            assert min(r["verified"].values()) == optimum
            worst_optimum = sorted(s for s, q in r["verified"].items() if q == optimum)
            assert worst_optimum == r["worst"]
            relation = "DE_REPRESENTATIVE" if method == "DIRECT_DE" else (
                "SAME_REPRESENTATIVE" if r["policy"] == direct["policy"] else "ALTERNATIVE_ROBUST_OPTIMUM")
            before_upper, before_lower = float("inf"), -1
            expected_blocks = list(r["initial"])
            expected_rounds = {"verify"}
            worst_counts = Counter()
            for it in r["iterations"]:
                key = f"oracle_{it['iteration']:02d}"
                expected_rounds.add(key)
                recs = per_round[key]
                worst = min(ev["service"] for ev in recs.values())
                ties = sorted(s for s, ev in recs.items() if ev["service"] == worst)
                worst_counts.update(ties)
                assert all(ev["policy"] == it["policy"] for ev in recs.values())
                assert worst == it["oracle_worst"] and ties == it["worst_ties"] and it["selected_tie"] == ties[0]
                assert it["master_scenarios"] == expected_blocks
                assert it["lower"] == max(before_lower, worst)
                assert it["lower"] <= optimum <= it["upper"] <= before_upper
                assert it["upper"] == it["mp_objective"] == it["solver_objective"] == it["solver_bound"]
                assert it["absolute_gap"] == it["upper"] - it["lower"]
                assert it["solver_gap"] == it["exact_matrix_residual"] == 0 and (HERE / it["log"]).is_file()
                before_lower, before_upper = it["lower"], it["upper"]
                if it["added_scenario"]:
                    assert it["absolute_gap"] > ccg.TOLERANCE and worst < it["upper"]
                    assert it["added_scenario"] == ties[0] and ties[0] not in expected_blocks
                    expected_blocks.append(ties[0])
                else:
                    assert it is r["iterations"][-1] and it["absolute_gap"] <= ccg.TOLERANCE
                    assert it["best_policy"] == r["policy"] and it["lower"] == optimum
                iterations.append(dict(label=LABEL, n=n, method=method, iteration=it["iteration"],
                    master_scenario_count=len(it["master_scenarios"]), master_scenarios="|".join(it["master_scenarios"]),
                    added_scenario=it["added_scenario"], x_C=it["policy"][0], x_T=it["policy"][1], x_O=it["policy"][2],
                    mp_objective=it["mp_objective"], UB=it["upper"], oracle_worst_service=worst, LB=it["lower"],
                    absolute_gap=it["absolute_gap"], relative_gap=it["relative_gap"],
                    master_solver_seconds=it["solver_seconds"], master_inclusive_seconds=it["master_seconds"],
                    oracle_seconds=it["oracle_seconds"], total_seconds=it["total_seconds"],
                    master_integers=it["integers"], master_constraints=it["constraints"],
                    peak_process_bytes=max(it["peak_process_bytes"], *(ev["peak_process_bytes"] for ev in recs.values())),
                    worst_ties="|".join(ties), deterministic_worst=ties[0], direct_objective=optimum,
                    best_policy=it["best_policy"], master_log=it["log"]))
            assert set(per_round) == expected_rounds
            if method != "DIRECT_DE":
                assert expected_blocks == r["final"] and r["iterations"] and before_lower == before_upper == optimum
            largest = r["largest"]
            assert largest["status"] == "OPTIMAL" and largest["solver_objective"] == optimum
            assert largest["solver_gap"] == largest["exact_matrix_residual"] == 0
            comparisons.append(dict(label=LABEL, n=n, method=method, robust_objective=optimum,
                certified_LB=optimum, certified_UB=optimum, abs_gap=0, relative_gap=0,
                wall_seconds=r["total_seconds"], before_final_verification_seconds=r["model_seconds"],
                final_verification_seconds=r["verification_seconds"], peak_process_bytes=r["peak_process_bytes"],
                largest_integers=largest["integers"], largest_constraints=largest["constraints"],
                largest_model_solver_seconds=largest["solver_seconds"], largest_model_nodes=largest["nodes"],
                solver_max_residual=max(largest["solver_residual"], *(it["solver_residual"] for it in r["iterations"]),
                                        *(ev["solver_residual"] for ev in r["oracle"])),
                exact_matrix_max_residual=0, iterations=len(r["iterations"]), complete_recourse_solves=len(r["oracle"]),
                final_blocks=len(r["final"]), block_ratio=len(r["final"])/n, certification="EXACT_FINITE"))
            policies.append(dict(label=LABEL, n=n, method=method, x_C=r["policy"][0], x_T=r["policy"][1],
                x_O=r["policy"][2], robust_service=optimum, first_stage_cost=r["cost"], budget=str(BUDGET),
                worst_scenarios="|".join(worst_optimum), policy_identity=relation, full_set_reverified=True))
            for name in families:
                usage.append(dict(label=LABEL, n=n, method=method, scenario=name, initial=name in r["initial"],
                    in_final_master=name in r["final"], added_in_iteration=next(
                        (it["iteration"] for it in r["iterations"] if it["added_scenario"] == name), ""),
                    never_included_in_master=name not in r["final"], oracle_worst_count=worst_counts[name],
                    repeatedly_worst=worst_counts[name] > 1, active_worst_at_optimum=name in worst_optimum,
                    verified_service=r["verified"][name], block_ratio=len(r["final"])/n))
            case["method_certificates"].append(dict(method=method, policy=r["policy"], relation=relation,
                objective=optimum, verified_service=r["verified"], final_worst=worst_optimum,
                initial_blocks=r["initial"], final_blocks=r["final"], per_iteration_bounds=[
                    [it["lower"], it["upper"]] for it in r["iterations"]],
                never_added=[s for s in families if s not in r["final"]],
                repeatedly_worst=[s for s in families if worst_counts[s] > 1]))
        cases.append(case)
    return iterations, comparisons, policies, usage, evaluations, cases


def main():
    frozen_inputs = verify_inputs()
    data = evidence()
    for name, rows in zip(("plain_ccg_iteration_log.csv", "plain_ccg_vs_direct_de.csv", "plain_ccg_policy_audit.csv",
                           "plain_ccg_scenario_usage.csv", "plain_ccg_oracle_evaluations.csv"), data[:5], strict=True):
        write_csv(name, rows)
    comparisons = data[1]
    direct_wall = {r["n"]: r["wall_seconds"] for r in comparisons if r["method"] == "DIRECT_DE"}
    faster = [[r["n"], r["method"]] for r in comparisons
              if r["method"] != "DIRECT_DE" and r["wall_seconds"] < direct_wall[r["n"]]]
    status = ("PASS_PLAIN_CCG_EXACT_BASELINE" if faster
              else "PASS_PLAIN_CCG_EXACT_BUT_NO_COMPUTATIONAL_GAIN")
    certificate = dict(status=status, scope="FINITE_SCENARIO_EXACT_CCG_BASELINE", label=LABEL,
                       directions=dict(master="UB", evaluated_incumbent="LB"), tolerance=ccg.TOLERANCE,
                       tie_break=ccg.TIE_BREAK, benchmark_cases=data[-1], observed_faster_end_to_end=faster)
    write_json("plain_ccg_exactness_certificate.json", certificate)
    print(status)
    for row in comparisons:
        print(row["n"], row["method"], row["final_blocks"], round(row["wall_seconds"], 2),
              round(row["peak_process_bytes"]/2**30, 3))
    if not REPORT.is_file() or not (HERE/"pytest.txt").is_file():
        return  # Preliminary comparison before publishing the report and running regressions.
    pytest_log = (HERE/"pytest.txt").read_text(encoding="utf-8")
    test_passed = int(re.search(r"(\d+) passed in", pytest_log)[1])
    assert int((HERE/"pytest_exit_code.txt").read_text(encoding="utf-8")) == 0
    for p in (SOURCE, TEST, *HERE.glob("*.py")):
        compile(p.read_bytes(), str(p), "exec")
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, encoding="utf-8").strip()

    git("diff", "--check")
    write_json("audit.json", dict(status=status, label=LABEL, certificate="plain_ccg_exactness_certificate.json",
        git_sha=git("rev-parse", "HEAD"), git_branch=git("branch", "--show-current"),
        frozen_inputs=frozen_inputs, source_zip_sha256=frozen.digest(frozen.SOURCE),
        source_xlsb_sha256=sha256(verified_bytes(frozen.SOURCE)).hexdigest(),
        instruction_sha256=frozen.digest(ATTACHMENT), first_stage_costs=[str(c) for c in COSTS],
        budget=str(BUDGET), baseline=BASELINE, informed_extra=SEVERE,
        gurobi_version=[13, 0, 1], gurobi_license="Usable in the observed full-size solves",
        python_version=platform.python_version(),
        parameters=dict(Threads=1, Seed=20261110, MIPGap=0, MIPGapAbs=0, FeasibilityTol=1e-9,
                        IntFeasTol=1e-9, OptimalityTol=1e-9, Presolve="AUTO", TimeLimit=90, SoftMemLimit=3),
        benchmark_results=comparisons, full_recourse_MILP_solves=len(data[4]),
        solver_log_count=sum(1 for _ in (HERE/"logs").glob("*.log")),
        optional_levels_not_run=[24, 32, 64], full_combinatorial_oracle=False,
        no_enhancements=True, stopped_after_phase32a=True,
        pytest=dict(passed=test_passed, failed=0, exit_code=0, output="pytest.txt", command=pytest_log.splitlines()[0]),
        git_diff_check_exit_code=0, syntax_compile_exit_code=0))
    manifest = HERE/"sha256_manifest.csv"
    files = [p for p in HERE.rglob("*") if p.is_file() and p != manifest]
    files.extend([REPORT, TEST, SOURCE])
    records = [dict(path=p.relative_to(ROOT).as_posix(), sha256=frozen.digest(p)) for p in sorted(files)]
    write_csv(manifest.name, records)
    assert all(frozen.digest(ROOT / r["path"]) == r["sha256"] for r in frozen.read(manifest))
    print(f"Manifest verified for {len(records)} files")


if __name__ == "__main__":
    main()
