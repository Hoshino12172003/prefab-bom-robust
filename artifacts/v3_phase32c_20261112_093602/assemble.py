"""Independent replay, paired benchmark aggregation, and acceptance evidence."""
import csv
import json
import re
import statistics
import subprocess
from collections import defaultdict

import gurobipy as gp
import numpy as np

import run_e4 as run
from structure import reach
from profile_runs import rhs_changes

HERE, ROOT = run.HERE,run.ROOT
LABEL = "STRESS_TEST_ONLY"
DOC = ROOT/"docs/v3_phase32c_e4_enhanced_ccg.md"
PROOF = ROOT/"docs/e4_bound_proof.md"
TEST = ROOT/"tests/test_v3_phase32c_e4.py"


def write(name, rows):
    rows = list(rows)
    if not rows:
        return
    with (HERE/name).open("w",encoding="utf-8-sig",newline="") as f:
        out = csv.DictWriter(f,list(rows[0]))
        out.writeheader()
        out.writerows(rows)


def dump(name, value):
    (HERE/name).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")


def replay(prunes):
    """Reconstruct original scenario matrices and test stored common vectors."""
    grouped = defaultdict(list)
    for r in prunes:
        grouped[r["scenario"],tuple(r["policy"])].append(r)
    verified = set()
    with run.FROZEN.env() as env:
        for (n,x), rows in grouped.items():
            with gp.Model(env=env) as model:
                b = run.plain.add_recourse_block(model,run.BASE,"recourse",run.PROFILES[n],x)
                model.update()
                A, rhs, senses = run.FROZEN.matrix_rows(model)
                lo, hi = (np.asarray(model.getAttr(attr)) for attr in ("LB","UB"))
                checks = {}
                for r in rows:
                    witness, sha = r["witness"], r["witness_sha256"]
                    assert run.FROZEN.digest(HERE/witness)==sha
                    if sha not in checks:
                        with np.load(HERE/witness,allow_pickle=False) as source:
                            v = source["solution"]
                        assert v.dtype.kind=="i" and v.shape==(model.NumVars,)
                        assert np.all(lo<=v) and np.all(v<=hi)
                        lhs = A@v
                        assert np.all(lhs[senses=="="]==rhs[senses=="="])
                        assert np.all(lhs[senses=="<"]<=rhs[senses=="<"])
                        assert np.all(lhs[senses==">"]>=rhs[senses==">"])
                        checks[sha] = run.grid.prior.selected_quantity(b,run.BASE,v)
                    assert checks[sha]==r["lower"]
                    r["independent_matrix_replay"] = True
                    verified.add((n,x,sha))
    return len(verified)


def benchmark_rows(data):
    summaries, times, repeatability = [], [], []
    for _, r in sorted(data.items()):
        records = r["records"]
        parts = defaultdict(list)
        for s in records:
            key = s["tag"]
            phase = ("MASTER" if key.startswith("MP_") else "DIRECT" if key=="DE" else
                     "FINAL_VERIFY" if key.startswith("verify__") else
                     "COMMON_WITNESS" if "__meet__" in key else "INDIVIDUAL_ORACLE")
            parts[phase].append(s)
        cheap = sum(a["bound_seconds"] for a in r["oracles"])
        solve_time = lambda phase: sum(s.get("wall_seconds",0) for s in parts[phase])
        oracle = (sum(a["wall_seconds"] for a in r["oracles"]) if r["method"]=="E4"
                  else sum(it["oracle_seconds"] for it in r["iterations"]))
        group = dict(label=LABEL,case=r["name"],scenario_count=len(r["scenarios"]),style=r["style"],
                     repeat=r["repeat"],method=r["method"])
        summary = dict(**group,status=r["status"],objective=r["objective"],policy=r.get("policy"),
            iterations=len(r["iterations"]),final_blocks=len(r.get("selected",[])),
            full_recourse_solves=sum(len(parts[k]) for k in ("FINAL_VERIFY","INDIVIDUAL_ORACLE","COMMON_WITNESS")),
            oracle_individual_solves=len(parts["INDIVIDUAL_ORACLE"]),common_integer_solves=len(parts["COMMON_WITNESS"]),
            cheap_bound_calls=sum(len(a["rows"]) for a in r["oracles"]),cheap_bound_seconds=cheap,
            oracle_seconds=oracle,master_seconds=solve_time("MASTER"),direct_seconds=solve_time("DIRECT"),
            final_exhaustive_solves=len(parts["FINAL_VERIFY"]),final_seconds=r.get("verification_seconds"),
            wall_seconds=r["wall_seconds"],peak_working_set_bytes=r["peak_bytes"],core=r["affinity"],
            largest_integers=max(s["integers"] for s in records),largest_constraints=max(s["constraints"] for s in records),
            total_BB_nodes=sum(s["nodes"] for s in records),error=r.get("error",""))
        summaries.append(summary)
        for phase, values in parts.items():
            if values:
                times.append(dict(**group,phase=phase,calls=len(values),wall_seconds=solve_time(phase),
                    model_build_seconds=sum(s["build_seconds"] for s in values),
                    gurobi_seconds=sum(s["solver_seconds"] for s in values)))
        if r["oracles"]:
            times.append(dict(**group,phase="CHEAP_BOM_BOUNDS",calls=summary["cheap_bound_calls"],
                              wall_seconds=cheap,model_build_seconds=0,gurobi_seconds=0))
    for n in (16,32,38):
        for m in ("PLAIN","E4","DE"):
            subset = [r for r in summaries if r["case"]==str(n) and r["method"]==m and (m=="DE" or r["style"]=="single")]
            if not subset:
                continue
            walls = [r["wall_seconds"] for r in subset]
            decisions = []
            if m=="E4":
                for r in subset:
                    o = data[str(n),r["style"],r["repeat"],m]["oracles"]
                    decisions.append(tuple(tuple(sorted((row["scenario"],row["decision"]) for row in a["rows"])) for a in o))
            repeatability.append(dict(label=LABEL,n=n,method=m,completed=len(subset),exact=sum(r["status"]=="EXACT_FINITE" for r in subset),
                median_wall_s=statistics.median(walls),min_wall_s=min(walls),max_wall_s=max(walls),
                objective_consistent=len({r["objective"] for r in subset})==1,
                policy_consistent=len({str(r["policy"]) for r in subset})==1,
                pruning_consistent=len(set(decisions))==1 if decisions else "",
                core_assignments=[r["core"] for r in subset]))
    write("e4_vs_plain_vs_direct.csv",summaries)
    write("e4_runtime_breakdown.csv",times)
    write("e4_repeatability.csv",repeatability)
    return summaries,repeatability


def risk_summary(data):
    catalog = run.grid.load()["scenarios"]
    existing = run.FROZEN.read(run.grid.prior.FROZEN/"multi_bom_scenario_catalog.csv")
    events = {r["scenario_id"]:json.loads(r["episode_details"]) for r in existing}
    events.update({n:r["events"] for n,r in catalog.items()})
    counts = defaultdict(lambda: [0,0,0,0])
    reach_data = {}
    for r in data.values():
        for a in r["oracles"]:
            for row in a["rows"]:
                name = row["scenario"]
                e = events[name]
                branches = sorted({"BATTERY" if s[0].startswith("B_") else s[0] for s in e})
                family = "JOINT" if len(branches)>1 else branches[0] if branches else "NR"
                if name not in reach_data:
                    reach_data[name] = reach(run.BASE,rhs_changes(run.BASE,run.FROZEN.OPENING,run.PROFILES[name]))["due_groups"]
                keys = [("TIMING",family,"|".join(branches),"|".join(str(s[3]) for s in e),
                         "|".join(str(s[2]) for s in e),"|".join(str(s[1]) for s in e),reach_data[name]),
                        ("EXCLUSIVE_FAMILY",family,"","","","","")]
                keys += [("BRANCH_MEMBERSHIP",b,b,"","","","") for b in branches]
                for key in keys:
                    v = counts[key]
                    v[0] += 1
                    v[1] += row["decision"]=="PRUNED_STRICT"
                    v[2] += row["decision"]=="BOUND_EXACT"
                    v[3] += row["decision"]=="INDIVIDUAL_MILP"
    write("e4_risk_family_analysis.csv",(dict(label=LABEL,scope=k[0],family=k[1],branches=k[2],severity=k[3],
        duration=k[4],onset=k[5],direct_due_date_overlap=k[6],candidates=v[0],strict_pruned=v[1],
        bound_exact=v[2],individual_MILP=v[3],prune_rate=v[1]/v[0]) for k,v in sorted(counts.items())))


def main():
    frozen = run.verify_frozen()
    run.init()
    samples = [row for n in run.VALIDATION for row in run.read(HERE/"runs"/f"{n}.json")["rows"]]
    old = run.FROZEN.read(run.grid.PHASE_B/"reachability_safe_bounds.csv")
    refs = {(f"probe_{r['policy_id']}",r["scenario"]):int(r["exact_service"]) for r in old}
    assert all(r["exact"]==refs.get((r["policy_id"],r["scenario"]),r["exact"]) for r in samples)
    write("e4_bound_validation.csv",(dict(label=LABEL,**r) for r in samples))
    data = {}
    for f in (HERE/"runs").glob("*.json"):
        r = run.read(f)
        if "method" in r:
            data[r["name"],r["style"],r["repeat"],r["method"]] = r
    efficiency, certificates, cross, regions = [],[],[],[]
    false = mismatch = 0
    for (n,style,rep,method), r in sorted(data.items()):
        if method!="E4":
            continue
        control = data.get((n,style,rep,"PLAIN"),{})
        for a in r["oracles"]:
            k = a["iteration"]
            tag = f"oracle_{k:02d}__"
            other = {s["tag"][len(tag):]:s["q"] for s in control.get("records",[])
                     if s["tag"].startswith(tag) and s["status"]==2}
            paired = (len(other)==len(r["scenarios"]) and len(control.get("iterations",[]))>=k and
                      control["iterations"][k-1]["policy"]==a["policy"])
            plain_q = min(other.values()) if paired else None
            plain_ties = sorted(s for s,q in other.items() if q==plain_q) if paired else []
            wrong = paired and (plain_q!=a["worst"] or plain_ties!=a["ties"])
            mismatch += wrong
            cross.append(dict(label=LABEL,case=n,style=style,repeat=rep,iteration=k,policy=a["policy"],
                same_policy_exhaustive=paired,plain_worst=plain_q,e4_worst=a["worst"],plain_ties=plain_ties,
                e4_ties=a["ties"],match=paired and not wrong))
            inc = None
            counts = defaultdict(int)
            for row in a["rows"]:
                assert row["incumbent"]==inc
                state = row["decision"]
                counts[state] += 1
                if state=="PRUNED_STRICT":
                    assert row["lower"]>inc
                    false += paired and other[row["scenario"]]<=inc
                if state=="BOUND_EXACT":
                    assert row["lower"]==row["upper"]==row["value"]
                if state!="INDIVIDUAL_MILP":
                    if paired:
                        assert row["lower"]<=other[row["scenario"]]<=row["upper"]
                    ev = row["evidence"]
                    certificates.append(dict(label=LABEL,case=n,style=style,repeat=rep,iteration=k,policy=a["policy"],
                        scenario=row["scenario"],bound_type=row["proof"],lower=row["lower"],upper=row["upper"],
                        pack_upper=row["pack_upper"],seat_upper=row["seat_upper"],incumbent=inc,
                        condition="L>INCUMBENT" if state=="PRUNED_STRICT" else "L=U",
                        disposition=state,proof_status="EXACT_INTEGER_WITNESS",pair=row["pair"],
                        independent_full_value=other.get(row["scenario"]) if paired else None,
                        witness=ev["witness"],witness_sha256=ev["witness_sha256"],log=ev["log"],
                        independent_matrix_replay=False))
                if row["value"] is not None:
                    inc = min(inc,row["value"]) if inc is not None else row["value"]
            assert inc==a["worst"]
            count = len(a["rows"])
            milps = a["individual"]+a["common"]
            assert a["individual"]==counts["INDIVIDUAL_MILP"]
            log_prefix = f"E4_{k:02d}__"
            jobs = [s for s in r["records"] if s["tag"].startswith(log_prefix)]
            common_seconds = sum(s["wall_seconds"] for s in jobs if "__meet__" in s["tag"])
            individual_seconds = sum(s["wall_seconds"] for s in jobs if "__meet__" not in s["tag"])
            bound_seconds = a["bound_seconds"]+common_seconds
            efficiency.append(dict(label=LABEL,case=n,style=style,repeat=rep,iteration=k,candidate=count,
                bound_exact=counts["BOUND_EXACT"],pruned=counts["PRUNED_STRICT"],individual_MILP=a["individual"],
                common_MILP=a["common"],total_MILP=milps,prune_rate=counts["PRUNED_STRICT"]/count,
                tight_sandwich_candidates=sum(row["lower"]==row["upper"] and row["decision"]!="INDIVIDUAL_MILP" for row in a["rows"]),
                solve_reduction=1-milps/count,cheap_bound_seconds=a["bound_seconds"],common_bound_seconds=common_seconds,
                total_bound_seconds=bound_seconds,remaining_individual_MILP_seconds=individual_seconds,
                oracle_other_seconds=a["wall_seconds"]-bound_seconds-individual_seconds,e4_oracle_seconds=a["wall_seconds"],
                plain_oracle_seconds=control["iterations"][k-1]["oracle_seconds"] if paired else None))
    unique_replays = replay(certificates)
    write("e4_iteration_crosscheck.csv",cross)
    write("e4_pruning_certificate.csv",certificates)
    write("e4_oracle_efficiency.csv",efficiency)
    summaries,repeats = benchmark_rows(data)
    risk_summary(data)
    for name,key in (("C_ONLY","4"),("C_T","region_CT"),("C_T_O","region_CTO")):
        archived = run.CASES["region_C" if key=="4" else key]
        for style in ("single","two"):
            p = data.get((key,style,1,"PLAIN"),{})
            e = data.get((key,style,1,"E4"),{})
            q = data.get((key,"direct",1,"DE"),{})
            if e:
                regions.append(dict(label=LABEL,region=name,environment=archived["source"],style=style,
                    frozen_policy=archived["source_policy"],returned_policy=e.get("policy"),
                    frozen_objective=archived["source_objective"],plain=p.get("objective"),e4=e.get("objective"),
                    direct=q.get("objective"),full_verification=len(e["verified"]),
                    saved_oracle_solves=sum(x["candidate"]-x["total_MILP"] for x in efficiency
                                           if x["case"]==key and x["style"]==style and x["repeat"]==1)))
    for name,probe,region in (("C_ONLY","probe_C","region_C"),("C_T","probe_CT","region_CT"),
                             ("C_T_O","probe_CTO","region_CTO")):
        r = run.read(HERE/"runs"/f"{probe}.json")
        rows = r["rows"]
        actual = {x["scenario"]:x["exact"] for x in rows}
        profiles = {n:run.PROFILES[n] for n in actual}
        values = {s["tag"].split("__",1)[1]:s for s in r["records"]}
        policy = run.CASES[probe]["source_policy"]
        def recorded(n, _, __):
            return values[n]["q"],values[n]
        ans = run.e4.separate(profiles,run.PREFIX,policy,recorded)
        assert ans.worst==min(actual.values()) and ans.ties==tuple(sorted(n for n,q in actual.items() if q==ans.worst))
        for row in ans.rows:
            assert row["lower"]<=actual[row["scenario"]]<=row["upper"]
        regions.append(dict(label=LABEL,region=name,environment=f"FIXED_POLICY_PROBE_18_FROM_{run.CASES[region]['source']}",
            style="REPLAY_EXACT_SOLVES",frozen_policy=policy,returned_policy=policy,frozen_objective=None,
            plain=min(actual.values()),e4=ans.worst,direct=None,full_verification=len(actual),
            saved_oracle_solves=len(actual)-ans.individual_solves-ans.common_solves))
    write("e4_policy_region_validation.csv",regions)
    ref = {str(n):26465 if n<=16 else 21775 for n in run.SIZES}
    ref.update({n:run.CASES[n]["source_objective"] for n in ("region_CT","region_CTO")})
    assert all(r["objective"]==ref[r["name"]] and set(r["verified"])==set(r["scenarios"]) and
               min(r["verified"].values())==r["objective"] for r in data.values() if r["status"]=="EXACT_FINITE")
    opt = sum(r["status"]=="EXACT_FINITE" for r in data.values())
    ncheck = sum(r["same_policy_exhaustive"] for r in cross)
    critical = [r for r in repeats if r["method"] in ("PLAIN","E4")]
    medians = {(r["n"],r["method"]):r["median_wall_s"] for r in critical}
    paired_gains = {str(n):1-medians[n,"E4"]/medians[n,"PLAIN"] for n in (16,32,38)
                    if (n,"E4") in medians and (n,"PLAIN") in medians}
    validations = sum(r["violation"] for r in samples)
    policy_effect = all(r["saved_oracle_solves"]>0 for r in regions if r["style"]=="REPLAY_EXACT_SOLVES")
    scale_effect = all(r["solve_reduction"]>0 for r in efficiency if r["case"] in set(map(str,run.SIZES)))
    if validations:
        status = "HOLD_E4_BOUND_INVALID"
    elif false:
        status = "HOLD_E4_FALSE_PRUNING"
    elif mismatch:
        status = "HOLD_E4_ORACLE_MISMATCH"
    elif len(data)!=58 or any(r["status"]!="EXACT_FINITE" for r in data.values() if r["method"]!="DE") or ncheck!=len(cross):
        status = "INCONCLUSIVE_PHASE32C"
    elif not policy_effect:
        status = "PASS_E4_EXACT_BUT_POLICY_SPECIFIC"
    elif not scale_effect:
        status = "PASS_E4_EXACT_BUT_SCALE_SPECIFIC"
    else:
        # A robust timing claim requires a positive median and a paired majority at all three sizes.
        speed = all(g>0 for g in paired_gains.values()) and all(
            sum(data[str(n),"single",r,"E4"]["wall_seconds"]<data[str(n),"single",r,"PLAIN"]["wall_seconds"]
                for r in (1,2,3))>=2 for n in (16,32,38))
        status = "PASS_BTB_CCG_EXACT_AND_EFFECTIVE" if speed else "PASS_E4_EXACT_BUT_RUNTIME_GAIN_WEAK"
    certificate = dict(status=status,scope="FINITE_SCENARIO_EXACT_E4_CCG",label=LABEL,
        bound_samples=len(samples),bound_violation_count=validations,false_pruning_count=false,
        oracle_mismatches=mismatch,exact_paired_rounds=ncheck,full_method_runs=len(data),exact_method_runs=opt,
        full_matrix_replays=unique_replays,certified_non_individual_scenarios=len(certificates),
        strict_pruning_count=sum(r["disposition"]=="PRUNED_STRICT" for r in certificates),
        all_six_scales_reduce_milps=scale_effect,all_three_policy_compositions_reduce_on_common_probe=policy_effect,
        expected_objectives=ref,single_start_median_wall_gain=paired_gains,region_comparisons=regions,
        incumbent_direction="Exact evaluated scenario service is an upper bound on min Q; strict L > incumbent preserves ties",
        final_verification="Fresh exhaustive integer recourse on the complete finite family")
    dump("e4_exactness_certificate.json",certificate)
    print(status,len(data),"runs",ncheck,"matched rounds",len(certificates),"proofs",paired_gains,flush=True)
    if not DOC.is_file() or not (HERE/"pytest_exit_code.txt").is_file():
        return
    assert int((HERE/"pytest_exit_code.txt").read_text())==0
    testlog = (HERE/"pytest.txt").read_text(encoding="utf-8")
    tests = int(re.search(r"(\d+) passed in",testlog)[1])
    subprocess.run(["git","diff","--check"],cwd=ROOT,check=True)
    sha = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,encoding="utf-8").strip()
    dump("audit.json",dict(**certificate,git_sha=sha,frozen_inputs=frozen,instruction_sha256=run.FROZEN.digest(run.INPUT),
        source_zip_sha256=run.FROZEN.digest(run.FROZEN.SOURCE),tests_passed=tests,uncertainty_calibration="HOLD_UNCERTAINTY_CALIBRATION",
        excluded_sizes=[64,128],max_unique_catalog=38,terminal_stage="PHASE32C",
        solver_logs=sum(1 for p in (HERE/"logs").glob("*/*.log") if p.stat().st_size)))
    manifest = HERE/"sha256_manifest.csv"
    files = [p for p in HERE.rglob("*") if p.is_file() and p!=manifest]+[DOC,PROOF,TEST,ROOT/"src/prefab_v3/e4_ccg.py"]
    rows = [dict(path=p.relative_to(ROOT).as_posix(),sha256=run.FROZEN.digest(p)) for p in sorted(files)]
    write(manifest.name,rows)
    assert all(run.FROZEN.digest(ROOT/r["path"])==r["sha256"] for r in run.FROZEN.read(manifest))
    print("Manifest verified",len(rows))


if __name__=="__main__":
    main()
