"""Aggregate full-catalog screening, exact reference, and measured solver evidence."""
import json
import re
import statistics
import subprocess
from collections import defaultdict

import catalog_d1 as c

HERE, ROOT, FROZEN = c.HERE,c.ROOT,c.FROZEN
REPORT = ROOT/"docs/v3_phase32d1_full_rhs_oracle_feasibility.md"
TEST = ROOT/"tests/test_v3_phase32d1_full_rhs.py"


def main():
    frozen = c.verify_frozen()
    meta = c.read(HERE/"catalog_metadata.json")
    assert meta["catalog_sha256"]==FROZEN.digest(HERE/"full_effective_rhs_catalog.csv")
    assert meta["mapping_sha256"]==FROZEN.digest(HERE/"trajectory_to_rhs_mapping.csv")
    catalog = {r["rhs_class_id"]:r for r in FROZEN.read(HERE/"full_effective_rhs_catalog.csv")}
    assert len(catalog)==38527
    matrix = {(r["policy"],r["rhs_class_id"]):r for r in FROZEN.read(HERE/"reference_tie_matrix_replay.csv")}
    timing = c.read(HERE/"reference_tie_matrix_replay.json")
    summary, classes, unresolved, worst, runtime, traces, model_calls = [],[],[],[],[],[],[]
    grouped = defaultdict(lambda:[0,0,0,0])
    discrepancies = 0
    for policy in c.POLICIES:
        btb = c.read(HERE/f"{policy}_btb.json")
        ref = c.read(HERE/f"{policy}_reference.json")
        check = c.read(HERE/f"{policy}_worst_verification.json")
        detail = FROZEN.read(HERE/f"{policy}_first_pass.csv")
        values = ref["service_by_class"]
        assert set(values)==set(catalog)=={r["rhs_class_id"] for r in detail}
        assert len(detail)==len(catalog)
        w = min(values.values())
        assert ref["worst"]==w and set(ref["ties"])=={n for n,q in values.items() if q==w}
        assert ref["nonbattery_proof"]["full_vin_nonbattery_JIT"]
        completed = {r["rhs_class_id"]:r for r in check["calls"]}
        assert all(r["Q"]==w and r["status"]==2 for r in completed.values())
        call_list = btb["calls"]
        assert len(call_list)==c.FIRST_BATCH and all(r["Q"]==values[r["rhs_class_id"]] and r["status"]==2 for r in call_list)
        assert [r["rank"] for r in btb["trace"]]==list(range(1,c.FIRST_BATCH+1))
        traces.extend(btb["trace"])
        model_calls.extend(call_list+check["calls"])
        counts = btb["categories"]
        total = len(catalog)
        for r in detail:
            id_ = r["rhs_class_id"]
            q = values[id_]
            low,up = int(r["lower_before_individual"]),int(r["safe_upper"])
            invalid = not low<=q<=up
            discrepancies += invalid
            classes.append(dict(**r,independent_reference_Q=q,reference_bound_violation=invalid))
            source = catalog[id_]
            family = "BATTERY" if source["disrupted_BOM_branches"]=="1" else "NR_EFFECTIVE"
            if r["classification"]=="MILP_REQUIRED":
                unresolved.append(dict(label=c.LABEL,policy=policy,rhs_class_id=id_,priority_rank=r["priority_rank"],
                    execution_status=r["prefix_execution"],reference_Q=q,
                    disrupted_BOM_branches=source["disrupted_BOM_branches"],battery_layers=source["disrupted_battery_layers"],
                    effective_resources=source["disrupted_resources"],representative_severity=source["severity"],
                    representative_duration=source["duration"],representative_start=source["start"],
                    recovery=source["recovery"],reachable_due_date_windows=source["reachable_due_date_windows"],
                    affected_VIN_configurations=source["affected_VIN_configurations"],reachable_VINs=source["reachable_VINs"],
                    max_structural_BOM_depth=source["max_structural_BOM_depth"],
                    shared_capacity_changed_rows=source["shared_capacity_changed_rows"],
                    coactive_effective_layer_periods=source["coactive_effective_layer_periods"],
                    cause="NO_SEAT_JIT_PAIR_NO_POSITIVE_BTB_LOWER"))
            groups = (("FAMILY",family),("BATTERY_LAYERS",source["disrupted_battery_layers"]),
                      ("SEVERITY_OF_REPRESENTATIVE",source["severity"]),("DURATION_OF_REPRESENTATIVE",source["duration"]),
                      ("ONSET_OF_REPRESENTATIVE",source["start"]),("RECOVERY",source["recovery"]),
                      ("DUE_DATE_OVERLAP",source["reachable_due_date_windows"]))
            for scope, key in groups:
                item = grouped[policy,scope,key]
                item[0] += 1
                item[1] += r["classification"]=="BOUND_EXACT"
                item[2] += r["classification"]=="SAFE_PRUNED"
                item[3] += r["classification"]=="MILP_REQUIRED"
        for family in ("GEAR","SEAT","MULTI_BOM_JOINT"):
            grouped[policy,"FAMILY",family] = [0,0,0,0]
        for id_ in ref["ties"]:
            r = completed.get(id_,{})
            verified = matrix[policy,id_]
            assert int(verified["Q"])==w and int(verified["integer_matrix_residual"])==0
            worst.append(dict(label=c.LABEL,policy=policy,policy_vector=ref["policy"],rhs_class_id=id_,
                W=w,tie_count=len(ref["ties"]),multiplicity=catalog[id_]["multiplicity"],
                representative_trajectory=catalog[id_]["representative_trajectory"],
                reference_status="EXACT_CONSTRUCTIVE_HISTORICAL_REFERENCE",integer_feasibility="PROVEN",
                direct_status="OPTIMAL_MATRIX_REPLAY" if r else "NOT_RUN",direct_Q=r.get("Q"),
                integer_matrix_residual=verified["integer_matrix_residual"],constructive_matrix_replay=True,
                reference_witness_group=verified["reference_witness_group"],solver_residual=r.get("residual"),
                log=r.get("log",""),witness=r.get("witness",""),witness_sha256=r.get("witness_sha256",""),
                BTB_full_set_certificate=False))
        t_milp = sum(r["wall_seconds"] for r in call_list)
        t_screen = sum(r["rescreen_seconds"] for r in btb["trace"])
        measured = t_milp+btb["bound_seconds"]+t_screen
        t_verify = ref["reference_seconds"]+check["verification_seconds"]+timing[policy]["seconds"]
        estimate = t_milp/len(call_list)*total/3600
        summary.append(dict(label=c.LABEL,policy=policy,vector=btb["policy"],origin=meta["policies"][policy]["source"],
            effective_rhs=total,exact=counts["BOUND_EXACT"],pruned=counts["SAFE_PRUNED"],MILP_required=counts["MILP_REQUIRED"],
            exact_rate=counts["BOUND_EXACT"]/total,prune_rate=counts["SAFE_PRUNED"]/total,
            MILP_fraction=counts["MILP_REQUIRED"]/total,first_batch_solved=len(call_list),
            remaining_BTB_MILPs=counts["MILP_REQUIRED"]-len(call_list),BTB_prefix_incumbent=btb["incumbent"],
            independent_reference_worst=w,worst_RHS_ties=len(ref["ties"]),
            worst_legal_trajectory_ties=sum(int(catalog[n]["multiplicity"]) for n in ref["ties"]),
            direct_worst_classes_replayed=len(completed),constructive_worst_matrix_checks=len(ref["ties"]),
            independent_reference_complete=True,
            BTB_full_set_certificate=False,maximum_observed_solver_residual=max(r["residual"] for r in call_list+check["calls"]),
            extrapolated_serial_full_MILP_hours=estimate))
        runtime.append(dict(label=c.LABEL,policy=policy,shared_RHS_generation_seconds=meta["catalog_seconds"],
            measured_full_bound_scan_seconds=btb["bound_seconds"],measured_mean_bound_seconds=btb["bound_seconds"]/total,
            measured_rescreen_seconds=t_screen,measured_BTB_prefix_milps=len(call_list),measured_BTB_prefix_milp_wall_s=t_milp,
            measured_BTB_prefix_subtotal_s=measured,measured_per_milp_wall_median_s=statistics.median(r["wall_seconds"] for r in call_list),
            measured_per_milp_wall_min_s=min(r["wall_seconds"] for r in call_list),
            measured_per_milp_wall_max_s=max(r["wall_seconds"] for r in call_list),
            measured_reference_wall_seconds=ref["reference_seconds"],measured_worst_verification_wall_seconds=check["verification_seconds"],
            measured_constructive_tie_replay_seconds=timing[policy]["seconds"],measured_verification_total_seconds=t_verify,
            measured_stage_sum_including_shared_generation_seconds=meta["catalog_seconds"]+measured+t_verify,
            extrapolated_plain_serial_full_MILP_hours=estimate,full_BTB_wall_time="NOT_RUN",
            extrapolation_basis="Measured first contiguous safe-upper-ranked batch; no randomized selection"))
    for row in summary:
        assert row["exact"]+row["pruned"]+row["MILP_required"]==38527
    assert len(worst)==len(matrix)
    c.write("full_rhs_policy_summary.csv",summary)
    c.write("full_rhs_bound_classification.csv",classes)
    c.write("full_rhs_milp_required.csv",unresolved)
    c.write("full_rhs_worst_case_certificate.csv",worst)
    c.write("full_rhs_runtime_breakdown.csv",runtime)
    c.write("full_rhs_incumbent_updates.csv",traces)
    c.write("full_rhs_solver_calls.csv",(dict(
        label=c.LABEL,policy=r["policy"],rhs_class_id=r["rhs_class_id"],purpose=r["purpose"],status=r["status"],
        Q=r["Q"],certified_bound=r["certified_bound"],solver_residual=r["residual"],build_seconds=r["build_seconds"],
        solver_seconds=r["solver_seconds"],wall_seconds=r["wall_seconds"],log=r["log"]) for r in model_calls))
    c.write("full_rhs_risk_family_analysis.csv",(dict(label=c.LABEL,policy=k[0],scope=k[1],group=k[2],
        candidates=v[0],bound_exact=v[1],safe_pruned=v[2],MILP_required=v[3],
        exact_rate=v[1]/v[0] if v[0] else None,prune_rate=v[2]/v[0] if v[0] else None,
        MILP_fraction=v[3]/v[0] if v[0] else None) for k,v in sorted(grouped.items())))
    status = "HOLD_FULL_RHS_EXACTNESS" if discrepancies else "IMPLICIT_SEPARATION_JUSTIFIED"
    print(status,len(classes),"classifications",len(model_calls),"full MILPs",len(worst),"reference ties",
          discrepancies,"bound violations",flush=True)
    for r in summary:
        print(r["policy"],r["BTB_prefix_incumbent"],r["independent_reference_worst"],r["worst_RHS_ties"],
              r["direct_worst_classes_replayed"],round(r["extrapolated_serial_full_MILP_hours"],2))
    if not REPORT.is_file() or not (HERE/"pytest_exit_code.txt").is_file():
        return
    assert int((HERE/"pytest_exit_code.txt").read_text())==0
    tests = int(re.search(r"(\d+) passed in",(HERE/"pytest.txt").read_text(encoding="utf-8"))[1])
    subprocess.run(["git","diff","--check"],cwd=ROOT,check=True)
    sha = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,encoding="utf-8").strip()
    for p in (*HERE.glob("*.py"),TEST):
        compile(p.read_bytes(),str(p),"exec")
    c.dump("audit.json",dict(status=status,label=c.LABEL,git_sha=sha,frozen_inputs=frozen,
        frozen_uncertainty=dict(resources=list(c.RESOURCE_IDS),gamma=c.U.gamma,concurrency=c.U.concurrency,
            severity=[str(s) for s in c.U.severities],duration=c.U.durations,recovery_steps=c.U.recovery_steps),
        raw_trajectories=meta["raw_trajectories"],effective_RHS=len(catalog),full_bound_checks=len(classes),
        bound_violation_count=discrepancies,first_batch_calls=len(traces),all_full_recourse_calls=len(model_calls),
        full_worst_integer_matrix_replays=len(matrix),maximum_constructive_integer_matrix_residual=0,
        independent_reference="Exact historical reduction, full effective-RHS enumeration for all four policies",
        complete_BTB_explicit_oracle=False,reference_used_for_BTB_pruning=False,full_CCG_calls=0,
        x_reoptimizations=0,new_separation_rule=False,source_zip_sha256=FROZEN.digest(FROZEN.SOURCE),
        instruction_sha256=meta["attachment_sha256"],catalog_sha256=meta["catalog_sha256"],mapping_sha256=meta["mapping_sha256"],
        policies=summary,tests_passed=tests,uncertainty_calibration="HOLD_UNCERTAINTY_CALIBRATION",
        terminal_stage="PHASE32D1"))
    manifest = HERE/"sha256_manifest.csv"
    files = [p for p in HERE.rglob("*") if p.is_file() and p!=manifest]+[REPORT,TEST]
    rows = [dict(path=p.relative_to(ROOT).as_posix(),sha256=FROZEN.digest(p)) for p in sorted(files)]
    c.write(manifest.name,rows)
    assert all(FROZEN.digest(ROOT/r["path"])==r["sha256"] for r in FROZEN.read(manifest))
    print("Manifest verified",len(rows),flush=True)


if __name__=="__main__":
    main()
