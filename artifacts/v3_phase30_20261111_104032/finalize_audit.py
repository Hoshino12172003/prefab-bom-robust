"""Seal the full-model audit after deterministic and regression verification."""
import ast
import csv
import json
import subprocess

from assemble_evidence import PAPER,REQUEST,TEST,csv_rows
from run_replication import HERE,ROOT,SOURCE
from hashlib import sha256


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    frozen={}
    for pattern in ("v25_phase20_*","v25_phase21_*","v25_phase21a_*","v25_phase21b_*","v25_phase22_*"):
        folder,= (ROOT/"artifacts").glob(pattern)
        manifest=folder/"sha256_manifest.csv"
        rows=csv_rows(manifest)
        assert all(digest(ROOT/r["path"])==r["sha256"] for r in rows)
        frozen[manifest.relative_to(ROOT).as_posix()]=dict(sha256=digest(manifest),verified=len(rows))
    phase22,=(ROOT/"artifacts").glob("v25_phase22_*")
    old=json.loads((phase22/"audit.json").read_text(encoding="utf-8"))
    assert digest(SOURCE)==old["source_zip_sha256"]
    from pathlib import Path
    assert all(digest(Path(p))==h for p,h in old["unchanged_code_sha256"].items())
    run=json.loads((HERE/"replication_run.json").read_text(encoding="utf-8"))
    cases=run["results"]
    assert len(cases)==4 and all(r["status"]=="OPTIMAL" and r["objective"]==r["bound"] and r["gap"]==0 for r in cases)
    assert len(list((HERE/"logs").glob("*.log")))==4
    for r in cases:
        assert (HERE/r["log"]).read_text(encoding="utf-8").count("Optimal solution found")==1
    assert (HERE/"pytest_exit_code.txt").read_text().strip()=="0"
    pytest_summary=(HERE/"pytest.txt").read_text(encoding="utf-8").splitlines()[-1]
    assert pytest_summary.startswith("47 passed")
    source_code=list((ROOT/"src/prefab_v3").glob("*.py"))
    for path in [*source_code,*HERE.glob("*.py"),ROOT/TEST]:
        ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    a=dict(status="PASS_FULL_BASE_WITH_DOCUMENTED_APPLICATION_DIFFERENCES",
        git_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        evidence_scope="QU2021_REPLICATION_MODEL and V3_ROBUST_EXTENSION_MODEL interface",
        source_hashes={str(path):digest(path) for path in (SOURCE,PAPER,REQUEST)},
        xlsb_sha256=run["source"]["source_sha256"],frozen_phase2_manifests=frozen,
        source_versions=dict(section_49_and_figure_10_eta_conflict=True,eq10_rescheduling_interpretation="VIN horizon total",
            xlsb_planned_rows_are_ceilings=True,raw_capacity=True,explicit_VIN_solve=False),
        physical_structure_removed=False,source_vins=28000,focal_bev_vins=3003,
        solver_version=run["gurobi"],sealed_deterministic_full_solves=4,earlier_pilot_full_solves=3,
        solver_parameters=dict(Threads=4,Seed=20261110,MIPGap=0,MIPGapAbs=0,OptimalityTol=1e-9,
            FeasibilityTol=1e-9,IntFeasTol=1e-9,TimeLimit=120),
        deterministic_results=cases,robust_extension="INTERFACE_CERTIFIED_ON_SYNTHETIC_CASE",
        prospective_regular_state="NOT_CALIBRATED",uncertainty_calibration=None,
        benders="CLASSICAL_BENDERS_NOT_DIRECTLY_APPLICABLE_WITH_INTEGER_RECOURSE",
        focal_reducibility_status_scope="FOCAL_BATTERY_MECHANISM_VALIDATION_MODEL_ONLY",
        full_reducibility="FOCAL_FORMULA_INSUFFICIENT; OTHER_REDUCTIONS_OPEN",
        algorithm_calls=0,tests=dict(summary=pytest_summary,exit_code=0,log="pytest.txt",
            phase110_source_semantics_included=True),
        commands=["python -B artifacts/v3_phase30_20261111_104032/run_replication.py",
            "python -B artifacts/v3_phase30_20261111_104032/assemble_evidence.py",
            "python -m pytest -p no:cacheprovider -q tests/test_v3_phase30_base.py tests/test_v25_phase110_source_semantics.py tests/test_v25_phase20_prospective_spec.py tests/test_v25_phase21_calibration.py tests/test_v25_phase21a_joint_policy.py tests/test_v25_phase21b_mechanism.py tests/test_v25_phase22_design_and_reducibility.py"],
        sha256_manifest="sha256_manifest.csv")
    (HERE/"audit.json").write_text(json.dumps(a,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    manifest=HERE/"sha256_manifest.csv"
    files=sorted([p for p in HERE.rglob("*") if p.is_file() and p!=manifest]+source_code+
        [ROOT/TEST,ROOT/"docs/v3_phase30_full_base_restoration.md",ROOT/"docs/v3_full_model_spec.md"])
    with manifest.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(("path","sha256"))
        writer.writerows((p.relative_to(ROOT).as_posix(),digest(p)) for p in files)
    assert all(digest(ROOT/r["path"])==r["sha256"] for r in csv_rows(manifest))
    print(f"{a['status']} | {pytest_summary} | {len(files)} output SHA-256 verified")


if __name__=="__main__":
    main()
