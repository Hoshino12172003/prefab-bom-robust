"""Assemble the frozen grid, exact optimal-set audit, and switching certificates."""
import csv
import hashlib
import json
import platform
import re
import subprocess
from collections import defaultdict
from fractions import Fraction as F
from itertools import combinations

from grid import BASELINE, FROZEN, HERE, LOCATIONS, REFERENCE, ROOT, freeze, load, profile
from profile_runs import rhs_changes
from run_grid import POSITIONS, RESULTS, policy_class
from threshold import activity

LABEL = "STRESS_TEST_ONLY"
REPORT = ROOT/"docs/v3_phase32p_endogenous_buffer_policy_validation.md"
TEST = ROOT/"tests/test_v3_phase32p_policy_audit.py"


def read_result(name):
    path = RESULTS/f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write(name, rows):
    assert rows, name
    with (HERE/name).open("w", newline="", encoding="utf-8-sig") as file:
        w = csv.DictWriter(file, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def full_row(case, result):
    c, t, o = map(F, case["costs"])
    r = result or {}
    x = r.get("policy", (None,)*3)
    proj = r.get("projections", {})
    multiple = len(proj) == 6 and any(proj[f"{p}_min"]["value"] != proj[f"{p}_max"]["value"] for p in POSITIONS)
    return dict(label=LABEL, case=case["case"], risk=case["risk"], tags="|".join(case["tags"]),
        budget_multiplier=case["budget_multiplier"], budget=case["budget"], severity_pct=case["severity"],
        duration=case["duration"], recovery_steps=case["recovery"], Gamma=case["gamma"],
        alpha_T_multiplier=case["alpha_T_multiplier"], alpha_O_multiplier=case["alpha_O_multiplier"],
        c_C=str(c), c_T=str(t), c_O=str(o), alpha_T=str(t/c), alpha_O=str(o/t),
        cost_label="COST_SENSITIVITY_ONLY" if "COST" in case["tags"] or "THRESHOLD" in case["tags"] else "",
        scenarios="|".join(case["scenarios"]), initial="|".join(case["initial"]),
        status=r.get("status", "NOT_RUN"), stage=r.get("stage", ""), error=r.get("error", ""),
        x_C=x[0], x_T=x[1], x_O=x[2], representative_class=r.get("policy_class", ""),
        optimal_set_taxonomy="MULTIPLE_OPTIMA" if multiple else r.get("policy_class", "") if len(proj)==6 else "",
        C_activity=activity(r, "C") if len(proj)==6 else "",
        T_activity=activity(r, "T") if len(proj)==6 else "",
        O_activity=activity(r, "O") if len(proj)==6 else "",
        robust_on_time=r.get("objective"), investment=r.get("cost", ""), unused_budget=r.get("unused", ""),
        budget_binding=r.get("budget_binding"), cannot_add_cheapest_unit=r.get("cannot_add_cheapest_unit"),
        active_worst="|".join(r.get("worst", [])), iterations=len(r.get("iterations", [])),
        solve_calls=len(r.get("solver_calls", [])), seconds=r.get("wall_seconds"),
        run_json=f"runs/{case['case']}.json" if result else "")


def validate(result):
    if result["status"] != "EXACT_FINITE":
        return
    q, x = result["objective"], result["policy"]
    case = result["case"]
    names = set(case["scenarios"])
    assert set(result["verified"]) == set(result["operations"]) == names
    assert q == min(result["verified"].values())
    assert result["iterations"][-1]["lower"] == q == result["iterations"][-1]["upper"]
    assert all(r["lower"] <= q <= r["upper"] for r in result["iterations"])
    assert result["policy_class"] == policy_class(x)
    costs, budget = list(map(F, case["costs"])), F(case["budget"])
    total = sum(c*v for c, v in zip(costs, x))
    assert total == F(result["cost"]) and budget-total == F(result["unused"]) >= 0
    assert all(result["verified"][s]+op["late_delivered"]+op["shortfall"] == 28000
               for s, op in result["operations"].items())
    if result["ablate"]:
        assert x[POSITIONS.index(result["ablate"])] == 0 and not result["projections"]
    else:
        assert len(result["projections"]) == 6
        for i, p in enumerate(POSITIONS):
            assert result["projections"][f"{p}_min"]["value"] <= x[i] <= result["projections"][f"{p}_max"]["value"]
            for suffix in ("min", "max"):
                row = result["projections"][f"{p}_{suffix}"]
                assert row["policy"][i] == row["value"]
                assert sum(c*v for c, v in zip(costs, row["policy"])) <= budget
    assert all(a["status"] in (2, 3) and (HERE/a["log"]).is_file() for a in result["solver_calls"])


def nominal_mechanisms(result):
    return {s: result["operations"][s]["active_capacity_or_reduced_receipt"] for s in result["worst"]}


def switching_pairs(results):
    exact = [r for r in results.values() if r and r["status"] == "EXACT_FINITE"]
    pools = defaultdict(list)
    for r in exact:
        c = r["case"]
        tags = set(c["tags"])
        if tags & {"BASE_BUDGET", "LOCATION_BUDGET"}:
            pools["BUDGET", c["risk"]].append((c["budget_multiplier"], r))
        if c["risk"] in LOCATIONS and "LOCATION_BUDGET" in tags and c["budget_multiplier"] == 100:
            pools["LOCATION", "REFERENCE"].append((c["risk"], r))
        if "SEVERITY_DURATION" in tags:
            pools["SEVERITY", c["risk"], c["duration"]].append((c["severity"], r))
            pools["DURATION", c["risk"], c["severity"]].append((c["duration"], r))
        if "COST" in tags:
            pools["ALPHA_T", c["alpha_O_multiplier"]].append((c["alpha_T_multiplier"], r))
            pools["ALPHA_O", c["alpha_T_multiplier"]].append((c["alpha_O_multiplier"], r))
        if "GAMMA" in tags:
            pools["GAMMA", "NESTED_MENU"].append((c["gamma"], r))
        if c["risk"] in ("R1", "R2", "R3") and (c["severity"], c["duration"]) == REFERENCE and c["budget_multiplier"]==100:
            pools["RECOVERY", c["risk"]].append((c["recovery"], r))
    witnesses = []
    for (kind, *_), items in pools.items():
        ordered = sorted(items, key=lambda item: item[0])
        pair_iter = combinations(ordered, 2) if kind in ("BUDGET", "LOCATION") else zip(ordered, ordered[1:])
        for (l, old), (u, new) in pair_iter:
            states = [(p, activity(old, p), activity(new, p)) for p in POSITIONS]
            strict = [p for p, a, b in states if {a, b} == {"IMPOSSIBLE", "REQUIRED"}]
            if not strict:
                continue
            witnesses.append(dict(label=LABEL, evidence="DISJOINT_OPTIMAL_SUPPORT_ON_COORDINATE",
                changed_parameter=kind, old_value=l, new_value=u, old_case=old["case"]["case"], new_case=new["case"]["case"],
                old_policy=compact(old["policy"]), new_policy=compact(new["policy"]),
                old_class=old["policy_class"], new_class=new["policy_class"], activity_changes=compact(states),
                positions_with_strict_switch="|".join(strict), old_service=old["objective"], new_service=new["objective"],
                service_change=new["objective"]-old["objective"], old_investment=old["cost"], new_investment=new["cost"],
                investment_change=str(F(new["cost"])-F(old["cost"])),
                old_worst="|".join(old["worst"]), new_worst="|".join(new["worst"]),
                old_binding_resources=compact(nominal_mechanisms(old)), new_binding_resources=compact(nominal_mechanisms(new)),
                interpretation={
                    "BUDGET": "Same risk and prices. The budget changes which positions can reach the globally optimal integer service.",
                    "LOCATION": "Same duration, severity, budget and prices. Check resource-days and each affected logistics step.",
                    "SEVERITY": "Same window and branch; the source capacity or receipt quantity changes.",
                    "DURATION": "Same onset and severity; the affected part of the delivery calendar changes.",
                    "ALPHA_T": "T and O unit costs both change at fixed O/T ratio; discrete budget.",
                    "ALPHA_O": "O unit cost changes at fixed T/C ratio; discrete budget.",
                    "GAMMA": "Nested finite menu; changed active support can change the bottleneck.",
                    "RECOVERY": "Additional two-step capacity attenuation can extend the affected window.",
                }[kind]))
    return witnesses


def economic_reference(r):
    c = r["case"]
    costs = tuple(map(F, c["costs"]))
    return (c["risk"] in ("BASE4", "R1", "R2", "R3", "R4", "R5") and
            50 <= c["budget_multiplier"] <= 150 and costs == (F(1), F(27, 19), F(297, 190)) and
            not c["recovery"] and (c["severity"] is None or (c["severity"], c["duration"]) == REFERENCE))


def scenario_audit(protocol):
    FROZEN.init()
    rows = []
    for name, info in protocol["scenarios"].items():
        d = rhs_changes(FROZEN.BASE, FROZEN.OPENING, profile(name, info, FROZEN.BASE, FROZEN.OPENING))
        effect = compact(sorted(d.items()))
        rows.append(dict(label=LABEL, scenario=name, raw_events=compact(info["events"]), recovery_steps=info["recovery"],
                         nominal_resource_days=sum(e[2] for e in info["events"]),
                         effective_capacity_rows=sum(k[0]=="capacity" for k in d),
                         effective_receipt_rows=sum(k[0]=="receipt" for k in d),
                         effective_rhs_sha256=hashlib.sha256(effect.encode()).hexdigest(), effective_rhs=effect))
    write("scenario_effective_profiles.csv", rows)


def assemble():
    protocol = load()
    results = {n: read_result(n) for n in protocol["cases"]}
    expected_ablation = [(n, p) for n in protocol["ablation_anchors"] for p in POSITIONS]
    ablations = {(n, p): read_result(f"{n}__NO_{p}") for n, p in expected_ablation}
    for result in [*results.values(), *ablations.values()]:
        if result:
            validate(result)
    main = [full_row(c, results[n]) for n, c in protocol["cases"].items()]
    write("buffer_policy_full_grid.csv", main)
    def select(tag):
        return [r for r in main if tag in r["tags"].split("|")]
    b_rows = [r for r in main if {"BASE_BUDGET", "LOCATION_BUDGET"} & set(r["tags"].split("|"))]
    slopes = []
    for risk in dict.fromkeys(r["risk"] for r in b_rows):
        group = sorted((r for r in b_rows if r["risk"] == risk), key=lambda r: r["budget_multiplier"])
        for i, r in enumerate(group):
            p = group[i-1] if i else None
            delta = r["robust_on_time"]-p["robust_on_time"] if p and p["status"] == r["status"] == "EXACT_FINITE" else None
            if delta is not None:
                assert delta >= 0
            slopes.append(dict(**r, previous_budget=p["budget"] if p else "", delta_service=delta,
                secant_vehicles_per_budget_unit=str(F(delta)/(F(r["budget"])-F(p["budget"]))) if delta is not None else ""))
    write("buffer_policy_budget_sensitivity.csv", slopes)
    anchors = [r for r in select("LOCATION_BUDGET") if r["budget_multiplier"]==100]
    write("buffer_policy_risk_location.csv", anchors)
    for tag, stem in (("SEVERITY_DURATION", "severity_duration"), ("COST", "cost_sensitivity"),
                      ("GAMMA", "gamma_sensitivity"), ("RECOVERY", "recovery_sensitivity")):
        write(f"buffer_policy_{stem}.csv", select(tag))
    projection_rows, support_rows, op_rows = [], [], []
    for n, r in results.items():
        if not r:
            continue
        for side, a in r["projections"].items():
            projection_rows.append(dict(label=LABEL, case=n, axis=side.split("_")[0], direction=side.split("_")[1],
                value=a["value"], x_C=a["policy"][0], x_T=a["policy"][1], x_O=a["policy"][2], proof=a["proof"], log=a["log"]))
        for cl, s in r["joint_supports"].items():
            support_rows.append(dict(label=LABEL, case=n, policy_class=cl, possible=s["policy"] is not None,
                                     complete_policy=compact(s["policy"]), proof=s["proof"], log=s["log"]))
    for n, r in [*results.items(), *((f"{k}__NO_{p}", v) for (k, p), v in ablations.items())]:
        if not r or "operations" not in r:
            continue
        for scenario, op in r["operations"].items():
            op_rows.append(dict(label=LABEL, case=n, scenario=scenario, robust_worst=scenario in r["worst"],
                policy=compact(r["policy"]), scenario_on_time=r["verified"][scenario], **{
                    k: compact(v) if isinstance(v, (dict, list)) else v for k, v in op.items()}))
    write("buffer_policy_optimal_set_audit.csv", projection_rows)
    write("buffer_policy_joint_support_audit.csv", support_rows)
    write("buffer_policy_operational_audit.csv", op_rows)
    ab_rows = []
    for (n, p), r in ablations.items():
        full = results[n]
        z, z_no = full["objective"] if full else None, r["objective"] if r else None
        exact = r and full and r["status"] == full["status"] == "EXACT_FINITE"
        delta = z-z_no if exact else None
        assert delta is None or delta >= 0
        ab_rows.append(dict(label=LABEL, case=n, risk=protocol["cases"][n]["risk"], forbidden=p,
            full_objective=z, restricted_objective=z_no, delta=delta, full_policy=compact(full.get("policy")) if full else "",
            restricted_policy=compact(r.get("policy")) if r else "", restricted_cost=r.get("cost", "") if r else "",
            restricted_budget_slack=r.get("unused", "") if r else "",
            restricted_worst="|".join(r.get("worst", [])) if r else "", status=r["status"] if r else "NOT_RUN",
            run_json=f"runs/{n}__NO_{p}.json" if r else ""))
    write("buffer_ablation_by_environment.csv", ab_rows)
    write("risk_buffer_matching_matrix.csv", [
        dict(**r, joint_optimal_classes="|".join(cl for cl, rec in results[r["case"]]["joint_supports"].items()
             if rec["policy"] is not None) if results[r["case"]] else "",
             resource_days=sum(e[2] for e in protocol["scenarios"][r["scenarios"].split("|")[-1]]["events"]))
        for r in anchors])
    switches = switching_pairs(results)
    if switches:
        write("policy_switching_witness.csv", switches)
    else:
        write("policy_switching_witness.csv", [dict(label=LABEL, evidence="NO_CERTIFIED_DISJOINT_SUPPORT_SWITCH")])
    scenario_audit(protocol)
    return protocol, results, ablations, main, ab_rows, switches


def threshold_audit():
    path = HERE/"contingent_threshold_jobs.json"
    if not path.is_file():
        return False, 0
    design = json.loads(path.read_text(encoding="utf-8"))
    if not design["jobs"]:
        write("buffer_policy_cost_threshold_audit.csv", [dict(label="COST_SENSITIVITY_ONLY", decision=design["decision"])])
        return True, 0
    rows = []
    for job in design["jobs"]:
        r = read_result(job["case"])
        if r:
            validate(r)
        rows.append(dict(**full_row(job, r), local_axis=job["threshold_axis"], position=job["threshold_position"],
                         budget_offset=job["budget_offset"], decision=design["decision"]))
    write("buffer_policy_cost_threshold_audit.csv", rows)
    return all(r["status"]=="EXACT_FINITE" for r in rows), len(rows)


def main():
    freeze()
    protocol, results, ablations, rows, ab_rows, switches = assemble()
    threshold_done, threshold_n = threshold_audit()
    certified = sum(r["status"] == "EXACT_FINITE" for r in rows)
    ab_n = sum(r["status"] == "EXACT_FINITE" for r in ab_rows)
    strong = [s for s in switches if economic_reference(results[s["old_case"]]) and economic_reference(results[s["new_case"]])]
    conditional = {p: any(r and r["status"]=="EXACT_FINITE" and activity(r,p)=="REQUIRED" for r in results.values()) for p in POSITIONS}
    complete = certified == len(rows) and ab_n == len(ab_rows) and threshold_done
    moderate_downstream = any(r and r["status"]=="EXACT_FINITE" and economic_reference(r) and
                              any(activity(r, p)=="REQUIRED" for p in ("T", "O")) for r in results.values())
    if not complete:
        status = "INCONCLUSIVE_PHASE32P"
    elif all(conditional.values()) and moderate_downstream and strong:
        status = "PASS_ENDOGENOUS_BUFFER_SWITCHING_CONFIRMED"
    elif all(conditional.values()) and moderate_downstream:
        status = "PASS_ENDOGENOUS_VALUE_ASYMMETRIC"
    elif not moderate_downstream and any(conditional[p] for p in ("T", "O")):
        status = "HOLD_POLICY_SWITCH_ONLY_UNDER_EXTREME_PARAMETERS"
    elif all(r["T_activity"]==r["O_activity"]=="IMPOSSIBLE" for r in rows):
        status = "HOLD_XC_DOMINATES_REASONABLE_DOMAIN"
    else:
        status = "HOLD_MULTIPLE_OPTIMA_CONFUNDING"
    print(status, certified, "/", len(rows), "grid", ab_n, "/", len(ab_rows), "ablations",
          threshold_n, "refinements", len(switches), "strong witnesses", len(strong), "reference witnesses")
    if not REPORT.is_file() or not (HERE/"pytest_exit_code.txt").is_file():
        return
    assert int((HERE/"pytest_exit_code.txt").read_text(encoding="utf-8")) == 0
    pytest_out = (HERE/"pytest.txt").read_text(encoding="utf-8")
    test_n = int(re.search(r"(\d+) passed in", pytest_out)[1])
    for p in (TEST, *HERE.glob("*.py")):
        compile(p.read_bytes(), str(p), "exec")
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, encoding="utf-8").strip()
    recs = [s for r in [*results.values(), *ablations.values()] if r for s in r["solver_calls"]]
    audit = dict(status=status, label=LABEL, cost_label="COST_SENSITIVITY_ONLY",
        calibration_status="HOLD_UNCERTAINTY_CALIBRATION", e4_implemented=False, git_sha=sha,
        phase_inputs=protocol["previous"], source_zip_sha256=FROZEN.digest(FROZEN.SOURCE),
        instruction_sha256=protocol["instruction_sha256"], frozen_grid_sha256=FROZEN.digest(HERE/"frozen_policy_grid.json"),
        method="PLAIN_EXACT_CCG", projections="Certified full-scenario fixed-optimal-service integer programs",
        baseline=next(r for r in rows if r["case"]==BASELINE), planned_main=len(rows), certified_main=certified,
        planned_ablations=len(ab_rows), certified_ablations=ab_n, cost_refinements=threshold_n,
        threshold_audit_completed=threshold_done, strong_switch_witnesses=len(switches), reference_witnesses=len(strong),
        conditional_value=conditional, required_policy_cells={
            p: sum(r[f"{p}_activity"]=="REQUIRED" for r in rows) for p in POSITIONS},
        multioptimal_cells=sum(r["optimal_set_taxonomy"]=="MULTIPLE_OPTIMA" for r in rows),
        representative_class_counts={
            c: sum(r["representative_class"]==c for r in rows) for c in sorted({r["representative_class"] for r in rows})},
        python=platform.python_version(), gurobi="13.0.1", gurobi_license="Verified by complete integer solves",
        solver_parameters=dict(Threads=1, Seed=20261110, TimeLimit=180, MIPGap=0, MIPGapAbs=0,
            FeasibilityTol=1e-9, IntFeasTol=1e-9, OptimalityTol=1e-9, Presolve="AUTO"),
        maximum_solver_residual=max(s.get("residual", 0) for s in recs),
        tests_passed=test_n, tests_exit_code=0, test_command=pytest_out.splitlines()[0],
        initial_regression_issue="R1 service plateau initially conflated with identical RHS. Test corrected to check the extra t=73 receipt rows.",
        initial_regression_log="pytest_initial_failed.txt",
        solver_logs=sum(1 for p in (HERE/"logs").glob("*/*.log") if p.stat().st_size), stopped_after_phase32p=True)
    (HERE/"audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    manifest = HERE/"sha256_manifest.csv"
    files = [p for p in HERE.rglob("*") if p.is_file() and p!=manifest]+[REPORT, TEST]
    hashes = [dict(path=p.relative_to(ROOT).as_posix(), sha256=FROZEN.digest(p)) for p in sorted(files)]
    write(manifest.name, hashes)
    assert all(FROZEN.digest(ROOT/r["path"])==r["sha256"] for r in FROZEN.read(manifest))
    print("Manifest verified", len(hashes), "files")


if __name__ == "__main__":
    main()
