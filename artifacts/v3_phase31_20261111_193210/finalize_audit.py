"""Seal Phase 3.1 evidence, preserving the Phase 3.0 baseline."""
import ast
import csv
import json
import subprocess
from pathlib import Path

from run_diagnostics import CELL,HERE,ROOT,SOURCE,digest,frozen,load_tables,read

STATUS="HOLD_UNCERTAINTY_CALIBRATION"
REQUEST=Path("private_inputs/attachment/已粘贴的文本.txt")
TEST=ROOT/"tests/test_v3_phase31_robust.py"
CODE=ROOT/"src/prefab_v3/robust.py"
DOCS=[ROOT/"docs"/n for n in ("v3_phase31_robust_uncertainty_freeze.md","v3_two_stage_robust_model.md")]


def main():
    prior_count=frozen()
    phase20=ROOT/"artifacts/v25_phase20_20261110_203851/sha256_manifest.csv"
    witness=next(r for r in read(phase20) if r["path"].endswith("FULL28000_witness.json.gz"))
    assert digest(ROOT/witness["path"])==witness["sha256"]
    run=json.loads((HERE/"diagnostic_run.json").read_text(encoding="utf-8"))
    replay=read(HERE/"historical_fixed_policy_reduction_check.csv")
    assert len(replay)==81 and all(r["direct_Q"]==r["conditional_exact_Q"] for r in replay)
    ablation=read(HERE/"full_model_buffer_ablation.csv")
    fixed=read(HERE/"historical_fixed_policy_scenario_audit.csv")
    direct=read(HERE/"selected_scenario_de_validation.csv")
    all_results=[*ablation,*fixed,*direct]
    assert len(all_results)==len(replay)
    assert all(r["status"]=="OPTIMAL" and r["Q"]==r["bound"] and r["gap"]=="0.0"
               and r["exact_matrix_residual"]=="0" for r in all_results)
    logs=list((HERE/"logs").glob("*.log"))
    assert len(logs)==len(all_results) and all(
        p.read_text(encoding="utf-8").count("Optimal solution found")==1 for p in logs)
    table=load_tables(SOURCE)
    parents={m for m,c,_ in table["BOM"] if c in CELL and m!=c}
    assert parents=={"BEV"}
    for file in ("risk_resource_catalog","uncertainty_parameter_provenance"):
        assert all(None not in r and all(v is not None for v in r.values())
                   for r in read(HERE/f"{file}.csv"))
    tests=(HERE/"pytest.txt").read_text(encoding="utf-8").splitlines()[-1]
    assert tests.startswith("53 passed") and (HERE/"pytest_exit_code.txt").read_text().strip()=="0"
    for p in (*HERE.glob("*.py"),TEST,CODE):
        ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
    candidate=next(r for r in read(HERE/"uncertainty_set_size_audit.csv") if
        (r["gamma_resource_days"],r["recovery_steps"],r["concurrency"],r["allowed_durations"])==("6","0","2","1|3|5"))
    losses={p:[int(r["ablation_loss"]) for r in ablation if r["excluded_position"]==p] for p in ("x_C","x_T","x_O")}
    result=dict(status=STATUS,
        git_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        phase30_frozen_manifest_entries=prior_count,phase20_JIT_witness_sha256=witness["sha256"],
        formal_prospective_state=None,formal_uncertainty_calibration=None,
        missing_inputs=["independent prospective opening inventory","dated normal receipts by SKU and resource",
                        "documented schedule commitments and resource-specific exposure calibration"],
        candidate_status="EXPERIMENTAL_STRESS_TEST",candidate_size=candidate,
        upstream_choice="BALANCED_10_6_4_KIT",source_cell_mothers=sorted(parents),
        conditional_historical_full_service_reduction=True,formal_prospective_reducibility="NOT_IDENTIFIED",
        CCG_structural_justification=False,CCG_calls=0,formal_prospective_optimizer_calls=0,
        source_vins=run["source_vins"],source_products=run["source_products"],
        source_xlsb_sha256=run["source_xlsb_sha256"],source_zip_sha256=run["source_zip_sha256"],
        attachment_sha256=digest(REQUEST),direct_historical_solver_runs=len(all_results),
        gurobi_version=run["gurobi_version"],maximum_solver_residual=max(float(r["max_solver_residual"]) for r in all_results),
        exact_integer_matrix_residual=0,independent_service_replays=len(replay),
        ablation={p:dict(conditions=len(v),positive=sum(n>0 for n in v),maximum=max(v)) for p,v in losses.items()},
        selected_DE=direct[0],test_summary=tests,test_exit_code=0,
        reproducibility_commands=[f"python -B {HERE.relative_to(ROOT).as_posix()}/{name}.py"
            for name in ("run_diagnostics","fixed_policy_diagnostics","audit_historical_reduction","finalize_audit")],
        sha256_manifest="sha256_manifest.csv")
    (HERE/"audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    manifest=HERE/"sha256_manifest.csv"
    files=sorted([p for p in HERE.rglob("*") if p.is_file() and p!=manifest]+[CODE,TEST,*DOCS])
    with manifest.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(("path","sha256"))
        writer.writerows((p.relative_to(ROOT).as_posix(),digest(p)) for p in files)
    assert all(digest(ROOT/r["path"])==r["sha256"] for r in read(manifest))
    print(STATUS, tests, f"{len(files)} output hashes verified")


if __name__=="__main__":
    main()
