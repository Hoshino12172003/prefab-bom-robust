"""Join exact results, solver evidence, and the D-4 release decision."""

import csv
import re
import subprocess
import sys
from pathlib import Path

from run import HERE, ROOT, BUDGET, TOTALS, frozen_catalog as io, read, spend


def main(instruction):
    results = {g:read(HERE / f"outer/G{g}/result.json") for g in (1,2,3)}
    exact = {r["gamma"]:r for r in read(HERE / "final_policy_independent_certificate.json") if r["label"] != "zero_policy"}
    enum = read(HERE / "gamma1_enum/summary.json")
    attempts = [read(HERE / f) for f in ("gamma1_de/solver_result.json",
                                        "gamma1_de/memory_retry/solver_result.json",
                                        "gamma1_de/conservative_retry/solver_result.json")]
    for attempt in attempts:
        log=(HERE / attempt["solve_log"]).read_text(encoding="utf-8",errors="replace")
        failure=re.search(r"Error \d+: [^\r\n]+",log)
        attempt["solver_error"]=failure[0] if failure else attempt.get("solver_error")
        attempt["terminal_status"]=("OPTIMAL" if attempt["monolithic_gurobi_optimal"]
                                    else "MEM_LIMIT" if "Memory limit reached" in log
                                    else "OUT_OF_MEMORY" if failure and "Out of memory" in failure[0]
                                    else "UNCERTIFIED")
        actual=re.search(r"Best objective\s+([\d.e+-]+), best bound",log,re.I)
        if actual:
            attempt.setdefault("objval",float(actual[1]))
    de = next((r for r in attempts if r["monolithic_gurobi_optimal"]),attempts[-1])
    identity = read(HERE / "gamma1_de/model_identity.json")
    start = read(HERE / "gamma1_de/feasible_start.json")
    flat = read(HERE / "policy_flatness_certificate.json")
    assert flat["all_budget_feasible_policies_are_optimal"] and flat["feasible_integer_policies"] == 57884083
    finite = [read(HERE / f"finite/{m}/result.json") for m in ("Direct","Plain","BTB","Implicit")]
    assert all(r["rhs_ids"] == finite[0]["rhs_ids"] and r["budget"] == str(BUDGET) for r in finite)
    assert len({r["objective"] for r in finite}) == 1
    io.write(HERE / "finite_matched_comparison.csv",
             ({k:v for k,v in r.items() if k not in ("rhs_ids","direct")} for r in finite))
    it, policy, workloads, all_certificates = [], [], [], []
    for g,r in results.items():
        final = r["final_oracle"]
        z, x = r["objective"], tuple(r["policy"])
        assert z == flat["robust_value"] and final["worst"] == final["lower_bound"] == z
        assert final["exact"] and not final["frontier_size"]
        assert (final["raw_count"],final["rhs_count"]) == TOTALS[g]
        if g == 1:
            assert enum["exact"] and enum["rhs_count"] == 355 and enum["policy"] == list(x)
            assert enum["worst"] == z and final["worst_rhs"] == enum["worst_rhs"]
            proof = "EXHAUSTIVE_355_FIXED_POLICY"
        else:
            p = exact[g]
            assert p["lower"] == p["upper"] == z and p["policy"] == list(x) and p["exact"]
            assert p["raw_count"] == TOTALS[g][0] and p["full_matrix_branch_replays"] == 414
            proof = "INDEPENDENT_ROOT_BRANCH_FULL_MATRIX_REPLAY"
        last = r["iterations"][-1]
        assert last["upper"] == last["lower"] == z and last["absolute_gap"] == 0
        for row in r["iterations"]:
            o, m = row["oracle"], row["mp"]
            assert row["lower"] <= z <= row["upper"] and o["exact"] and not o["frontier_size"]
            assert m["objective_bound"] == row["upper"] and m["solver_gap"] == m["matrix_residual"] == 0
            it.append(dict(gamma=g, iteration=row["iteration"], blocks=len(row["master_scenarios"]),
                active="|".join(row["master_scenarios"]), x_C=row["policy"][0],x_T=row["policy"][1],x_O=row["policy"][2],
                UB=row["upper"],LB=row["lower"],gap=row["absolute_gap"],oracle_W=row["oracle_worst"],
                worst_rhs=row["worst_scenario"],added_rhs=row["added_scenario"],
                oracle_nodes=o["visited_nodes"],oracle_prunes=o["pruned_nodes"],envelope_milps=o["envelope_calls"],
                scenario_milps=o["exact_recourse_calls"],cache_hits=o["cache_hits"],envelope_cache_hits=o["envelope_cache_hits"],
                frontier=o["frontier_size"],oracle_seconds=row["oracle_seconds"],mp_seconds=row["master_seconds"],
                peak_bytes=max(m["peak_bytes"],o["peak_bytes"]),master_log=m["log"]))
        rows = [row for row in it if row["gamma"]==g]
        assert all(a["UB"]>=b["UB"] and a["LB"]<=b["LB"] for a,b in zip(rows,rows[1:]))
        calls = [row["oracle"] for row in r["iterations"]]
        workloads.append(dict(gamma=g,raw_trajectories=TOTALS[g][0],rhs_classes=TOTALS[g][1],
            iterations=len(rows),final_blocks=len(r["selected"]),mp_calls=len(rows),
            separation_scenario_milps=sum(o["exact_recourse_calls"] for o in calls),
            separation_envelope_milps=sum(o["envelope_calls"] for o in calls),
            final_scenario_milps=final["exact_recourse_calls"],final_envelope_milps=final["envelope_calls"],
            final_certification=proof,wall_seconds=r["total_seconds"],peak_bytes=max(row["peak_bytes"] for row in rows)))
        cost=spend(x)
        policy.append(dict(gamma=g,objective=z,service_rate=z/28000,x_C=x[0],x_T=x[1],x_O=x[2],
                           investment=str(cost),unused_budget=str(BUDGET-cost),worst_rhs=r["final_worst_rhs"],
                           actual_active_branches="S",final_oracle_frontier=0,independent_certificate=proof))
        all_certificates.append(dict(gamma=g, exact=True, objective=z, policy=x, LB=z, UB=z,
                                     frontier=0, final_worst_rhs=r["final_worst_rhs"], certification=proof))
    assert de["model_dimensions_confirmed"] or not de["monolithic_gurobi_optimal"]
    assert identity["blocks"] == start["full_blocks_matrix_verified"] == 355
    assert identity["matrix_pilot"]["coefficient_differences"] == 0
    bounds = read(HERE / "gamma1_de/bound_certificate.json")
    assert bounds["exact"] and bounds["mps_sha256"] == identity["sha256"] and bounds["start_sha256"] == start["sha256"]
    lb, ub = bounds["lower"], bounds["upper"]
    assert lb == ub == results[1]["objective"] and start["matrix_residual"] == 0
    # The feasible start supplies the lower bound on the actual full DE.
    # A globally solved submodel containing its worst block supplies the upper bound.
    if de["monolithic_gurobi_optimal"]:
        assert de["objective"] == de["objval"] == de["objbound"] == lb and de["verified_blocks"] == 355
    io.write(HERE / "gamma1_direct_crosscheck.csv",[dict(
        direct_blocks=355,direct_columns=identity["cols"],direct_rows=identity["rows"],direct_nnz=identity["nnz"],
        direct_cli_exit=de["cli_exit"],direct_monolithic_optimal=de["monolithic_gurobi_optimal"],
        direct_terminal_status=de["terminal_status"],
        direct_cli_obj=de.get("objval"),direct_cli_bound=de.get("objbound"),
        direct_independent_feasible_lb=lb,direct_exact_upper_from_subset=ub,direct_exact_objective=lb,
        implicit_ccg_objective=results[1]["objective"],final_policy_enumerated_rhs=enum["rhs_count"],
        start_accepted=de["start_accepted"],direct_peak_bytes=de["peak_bytes"],
        direct_cli_seconds=de["solver_seconds_wall"],direct_log=de["solve_log"],
        direct_cli_error=de.get("solver_error"),independent_bound_source=bounds["source_upper"],
        independent_gap=ub-lb)])
    io.write(HERE / "full_implicit_ccg_iteration_log.csv",it)
    io.write(HERE / "gamma_robust_policy_comparison.csv",policy)
    io.write(HERE / "implicit_ccg_workload.csv",workloads)
    for name in ("gamma_policy_set_audit.csv","gamma_worst_event_comparison.csv","binding_capacity_rows.csv",
                 "binding_bom_components.csv","affected_vin_groups.csv"):
        assert (HERE / name).stat().st_size > 0
    assert all((HERE / f"outer_G{g}.exit").read_text().strip()=="0" for g in (1,2,3))
    assert all(int((HERE / f).read_text(encoding="utf-8-sig")) == 0 for f in (
        "gamma1_enum.exit","certify.exit","direct_bound.exit","interpret.exit","finite_Direct.exit",
        "finite_Plain.exit","finite_BTB.exit","finite_Implicit.exit"))
    status = ("PASS_IMPLICIT_CCG_EXACT_BUT_HIGH_GAMMA_POLICY_FLAT" if de["monolithic_gurobi_optimal"]
              else "INCONCLUSIVE_PHASE32D4")
    cert=dict(status=status, three_full_robust_solves=all_certificates,
        gamma1_direct_objective_exact_via_bounds=lb,gamma1_direct_monolithic_optimal=de["monolithic_gurobi_optimal"],
        remaining_acceptance_gate=None if de["monolithic_gurobi_optimal"] else "MONOLITHIC_GAMMA1_DIRECT_GUROBI_OPTIMAL",
        gamma1_final_policy_full_enumeration=enum,gamma2_3_independent_certificates=exact,
        finite_matched_objective=finite[0]["objective"],policy_flatness=flat)
    io.dump(HERE / "implicit_ccg_exactness_certificate.json",cert)
    assert int((HERE / "pytest_exit_code.txt").read_text(encoding="utf-8-sig")) == 0
    test_log=(HERE / "pytest.txt").read_text(encoding="utf-8-sig")
    tests=int(re.search(r"=+ (\d+) passed in ",test_log)[1])
    audit=dict(status=status, git_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        instruction_sha256=io.digest(instruction), preflight=read(HERE / "preflight.json"), K=2,
        scope="HISTORICAL_STRESS_TEST_ONLY", pytest_passed=tests, pytest_failed=0,
        direct_result=de, direct_attempts=attempts,direct_bound_certificate=bounds,
        direct_model_identity=identity, certificate="implicit_ccg_exactness_certificate.json",
        algorithms=dict(primary="Implicit Event-Space C&CG",BTB="finite-scenario auxiliary enhancement",
                        new_mechanism=False, full_rhs_enumeration_gamma2_3=False))
    io.dump(HERE / "audit.json",audit)
    manifest=HERE / "sha256_manifest.csv"
    files=[p for p in HERE.rglob("*") if p.is_file() and p!=manifest]
    files.extend(ROOT / p for p in ("src/prefab_v3/implicit_ccg.py","tests/test_v3_phase32d4_implicit_ccg.py",
                                  "tests/test_v3_phase32d4_artifacts.py",
                                  "docs/v3_phase32d4_full_implicit_ccg.md"))
    with manifest.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.writer(stream)
        writer.writerow(("path","sha256"))
        writer.writerows((p.relative_to(ROOT).as_posix(),io.digest(p)) for p in sorted(files))
    print(status,"tests",tests,"manifest entries",len(files),flush=True)


if __name__=="__main__":
    main(Path(sys.argv[1]))
