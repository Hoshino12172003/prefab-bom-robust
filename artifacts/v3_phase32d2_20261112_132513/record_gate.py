"""Verify frozen input hashes and record the stop at the exposure-budget gate."""

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D1 = ROOT / "artifacts/v3_phase32d1_20261112_111159"
TEST = "tests/test_v3_phase32d2_gamma_gate.py"
DOC = "docs/v3_phase32d2_multibom_uncertainty_calibration.md"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(directory, expected=None):
    manifest = directory / "sha256_manifest.csv"
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    identity = {"entries": len(rows), "manifest_sha256": digest(manifest)}
    if expected is not None and identity != expected:
        raise ValueError(f"Frozen manifest identity mismatch: {manifest}")
    for row in rows:
        if digest(ROOT / row["path"]) != row["sha256"]:
            raise ValueError(f"Frozen file identity mismatch: {row['path']}")
    return identity


def main(instruction):
    previous = read_json(D1 / "audit.json")
    frozen = {
        name: verify_manifest(ROOT / "artifacts" / name, expected)
        for name, expected in previous["frozen_inputs"].items()
    }
    frozen[D1.name] = verify_manifest(D1)
    phase30 = ROOT / "artifacts/v3_phase30_20261111_104032/audit.json"
    source_zip = next(Path(p) for p, h in read_json(phase30)["source_hashes"].items()
                      if h == previous["source_zip_sha256"])
    actual_source_hash = digest(source_zip)
    if actual_source_hash != previous["source_zip_sha256"]:
        raise ValueError("Source ZIP identity mismatch")

    pytest_log = (HERE / "pytest.txt").read_text(encoding="utf-8-sig")
    pytest_exit = int((HERE / "pytest_exit_code.txt").read_text(encoding="utf-8-sig"))
    passed = re.findall(r"^(tests/[^\r\n]+?) PASSED ", pytest_log, re.MULTILINE)
    if pytest_exit != 0 or len(passed) != 14:
        raise ValueError("Expected 14 passing validation tests")

    cases = [
        {"gamma": gamma, "duration": duration, "required_exposures": duration,
         "passes_exposure_budget": duration <= gamma}
        for gamma in (2, 4, 6)
        for duration in (4, 7, 11)
    ]
    with (HERE / "gamma_compatibility.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cases[0]))
        writer.writeheader()
        writer.writerows(cases)

    audit = {
        "status": "HOLD_GAMMA_SEMANTICS_CONFLICT",
        "stop_section": "F",
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "instruction_sha256": digest(instruction),
        "source_zip_sha256": actual_source_hash,
        "frozen_inputs_verified": frozen,
        "frozen_manifest_entries_verified": sum(entry["entries"] for entry in frozen.values()),
        "gamma_semantics": {
            "unit": "active disrupted resource-period",
            "equal_weights": 1,
            "concurrency_is_independent": True,
            "counts_recovery_tail": False,
            "counts_starts": False,
            "scales_by_severity": False,
        },
        "proposed_core_durations": [4, 7, 11],
        "gamma_sensitivity_values": [2, 4, 6],
        "single_episode_budget_checks": cases,
        "minimum_joint_exposures": {"two_resources": 8, "three_resources": 12},
        "frozen_battery_only_reference": {
            "source": D1.relative_to(ROOT).as_posix() + "/audit.json",
            "parameters": previous["frozen_uncertainty"],
            "legal_trajectories": previous["raw_trajectories"],
            "effective_rhs": previous["effective_RHS"],
            "reenumerated_this_phase": False,
        },
        "pytest": {
            "command": f"python -m pytest -p no:cacheprovider -vv {TEST}",
            "exit_code": pytest_exit,
            "passed": len(passed),
            "failed": 0,
            "test_ids": passed,
        },
        "new_multibom_scenarios_generated": 0,
        "gurobi_optimize_calls": 0,
        "blocked_outputs": [
            "multibom_risk_resource_catalog.csv",
            "multibom_scenario_count.csv",
            "multibom_effective_rhs_catalog",
            "multibom_nonseparability_certificate.csv",
            "multibom_btb_retest.csv",
            "D-3 formulation, prototype and exactness results",
        ],
        "solver_logs": None,
    }
    (HERE / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    manifest = HERE / "sha256_manifest.csv"
    paths = [p for p in HERE.iterdir() if p.is_file() and p != manifest]
    paths.extend(ROOT / p for p in (TEST, DOC))
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("path", "sha256"))
        writer.writerows((p.relative_to(ROOT).as_posix(), digest(p)) for p in sorted(paths))
    print(f"{audit['status']} | verified frozen entries: {audit['frozen_manifest_entries_verified']}"
          f" | passed tests: {len(passed)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
