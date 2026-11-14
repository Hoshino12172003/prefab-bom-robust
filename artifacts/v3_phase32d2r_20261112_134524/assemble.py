"""Publish Phase D-2R audit after tests and frozen-input verification."""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from catalog import ARTIFACTS, CATALOG, D2, HERE, ROOT, digest, dump, verify_manifest, write


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(instruction):
    prior = read_json(D2 / "audit.json")
    frozen = {name: verify_manifest(ARTIFACTS / name, expected)
              for name, expected in prior["frozen_inputs_verified"].items()}
    frozen[D2.name] = verify_manifest(D2)
    source = read_json(ARTIFACTS / "v3_phase31r_20261111_202237/audit.json")["source_inputs"]
    assert digest(Path(source["source_zip"])) == source["source_zip_sha256"] == prior["source_zip_sha256"]
    assert all(digest(ROOT / path) == value for path, value in source["code_sha256"].items())
    old = read_json(ARTIFACTS / "v3_phase31_20261111_193210/audit.json")
    assert digest(ARTIFACTS / "v25_phase20_20261110_203851/FULL28000_witness.json.gz") == old[
        "phase20_JIT_witness_sha256"]

    for file in ("pytest_exit_code.txt", "pytest_semantics_exit_code.txt", "revalidation_exit_code.txt"):
        assert int((HERE / file).read_text(encoding="utf-8-sig")) == 0
    semantic_log = (HERE / "pytest_semantics.txt").read_text(encoding="utf-8-sig")
    tests = [
        ("A", "test_a_battery_seven_days_at_gamma_one", 1, 2, 7, "legal"),
        ("B", "test_b_seat_eleven_days_at_gamma_one", 1, 2, 11, "legal"),
        ("C", "test_c_overlapping_battery_gear_at_gamma_two", 2, 2, 8, "legal; rejected at K=1"),
        ("D", "test_d_three_seven_day_events_with_and_without_triple_overlap", 3, 2, 21,
         "staggered legal; triple overlap rejected"),
        ("E", "test_e_joint_families_rejected_at_gamma_one", 1, 2, 8, "all BG, BS, GS rejected"),
    ]
    for case, name, *_ in tests:
        found = re.findall(rf"::{name}[^\r\n]* PASSED ", semantic_log)
        assert len(found) == (3 if case == "E" else 1)
    write(HERE / "event_budget_regression.csv",
          (dict(case=case, gamma_evt=gamma, K=k, resource_days=days, observed=result,
                test=name, status="PASS") for case, name, gamma, k, days, result in tests))

    solver = read_json(HERE / "validation_run.json")
    counts = read_json(HERE / "count_run.json")
    pytest_log = (HERE / "pytest.txt").read_text(encoding="utf-8-sig")
    passed = len(re.findall(r"^(tests/[^\r\n]+?) PASSED ", pytest_log, re.MULTILINE))
    assert passed > len(tests) and re.search(rf"=+ {passed} passed in ", pytest_log)
    assert solver["witness"]["integer_Q"] == 18600
    assert solver["full_integer_calls"] == 51 and solver["prefix_integer_calls"] == 42
    assert counts["catalog_classes"] > 38527
    classes = counts["catalog_classes"]
    days = {r["policy"]: r["wall_seconds"]/r["individual_MILP"]*classes/86400 for r in solver["btb"]}
    audit = dict(
        status="PASS_EVENT_BUDGET_MULTIBOM_UNCERTAINTY",
        scope="HISTORICAL_STRESS_TEST_ONLY",
        git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        instruction_sha256=digest(instruction), source_zip_sha256=source["source_zip_sha256"],
        frozen_inputs=frozen, frozen_entries_verified=sum(r["entries"] for r in frozen.values()),
        gamma_evt=[1, 2, 3], gamma_evidence_role="ROBUSTNESS_SENSITIVITY", daily_concurrency=2,
        active_resource_days_role="TOTAL_DISRUPTION_EXPOSURE_DIAGNOSTIC",
        duration_grid=[4, 7, 11], severity_grid=["1/4", "1/2", "3/4"], recovery="ABRUPT_RECOVERY",
        event_budget_tests="A–E passed before catalog generation",
        python=sys.version.split()[0], gurobi=solver["gurobi"], pyxlsb="1.0.10",
        environment_repair="Initial catalog import lacked pyxlsb. Pinned optional dependency installed to temp target.",
        counts=counts, integer_validation=solver,
        rhs_catalog_sha256=digest(CATALOG / "classes.npz"),
        rhs_dictionary_sha256=digest(CATALOG / "rhs_coordinates.json"),
        test_command=(HERE / "pytest_command.txt").read_text(encoding="utf-8-sig").strip(),
        pytest_passed=passed, pytest_failed=0,
        gate=dict(eligible_for_followup_research=True, full_oracle_exhaustively_solved=False,
                  frozen_btb_pairs_structurally_possible_in_core=False,
                  serial_extrapolation_days_by_policy=days,
                  extrapolation_not_a_measured_full_runtime=True,
                  implicit_separation_implemented=False, full_scale_ccg_run=False),
    )
    dump(HERE / "audit.json", audit)
    manifest = HERE / "sha256_manifest.csv"
    paths = [path for path in HERE.rglob("*") if path.is_file() and path != manifest]
    paths.extend(ROOT / path for path in (
        "src/prefab_v3/event_budget.py", "tests/test_v3_phase32d2r_event_budget.py",
        "tests/test_v3_phase32d2r_catalog.py", "docs/v3_phase32d2r_gamma_semantics_repair.md",
    ))
    with manifest.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("path", "sha256"))
        writer.writerows((p.relative_to(ROOT).as_posix(), digest(p)) for p in sorted(paths))
    print(audit["status"], "pytest", passed, "frozen entries", audit["frozen_entries_verified"],
          "serial extrapolation days", days, flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
