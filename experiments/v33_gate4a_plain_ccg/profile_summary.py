"""Summarize the measured Gate 4A performance without running optimization."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean


def read(folder, name):
    path = folder / f"gate4a_{name}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def profile(folder):
    verdict = json.loads((folder / "gate4a_summary.json").read_bytes())
    iterations = read(folder, "iteration_profile")
    oracle = read(folder, "oracle_profile")
    lex = read(folder, "lexicographic_profile")
    replays = read(folder, "final_replay")
    de = [r for r in verdict["results"] if r["method"] == "DIRECT_DE"]
    cases = {}
    for run in verdict["results"]:
        if run["method"] != "CCG":
            continue
        name = run["case"]
        history = [r for r in iterations if r["run"] == name]
        sequence = ["NOM", *(r["added"] for r in history if r["added"])]
        assert len(sequence) == len(set(sequence))
        timed = {part:sum(float(r[f"{part}_seconds"]) for r in history) for part in ("master", "oracle")}
        solves = [r for r in oracle if r["run"].startswith(f"{name}_i")]
        tiers = [r for r in lex if r["run"].startswith(f"{name}_i")]
        groups = {}
        for kind in ("nominal", "single", "double"):
            group = [r for r in solves if ("nominal" if r["scenario"]=="NOM" else "double" if "+" in r["scenario"] else "single")==kind]
            if group:
                groups[kind]=dict(solves=len(group),mean_seconds=mean(float(r["runtime_seconds"]) for r in group),
                                  max_seconds=max(float(r["runtime_seconds"]) for r in group))
        comparable = [r for r in history if r["recovery_worst"]]
        final = [r for r in replays if r["run"]==f"{name}_independent_replay"]
        critical={}
        if run["status"]=="PASS":
            for level,key in (("service","ot"),("backlog","tau")):
                stage=[r for r in final if r["level"]==level]
                critical[level] = [r["scenario"] for r in stage if round(float(r["objective"]))==run[key]]
            holding=[r for r in final if r["level"]=="economics"]
            worst_holding=max(float(r["objective"]) for r in holding)
            critical["economics"]=[r["scenario"] for r in holding if float(r["objective"])==worst_holding]
        cases[name]=dict(status=run["status"],completed_iterations=len(history),discovered=sequence,
            certified_master=run.get("master_scenarios"),risk_repeats=sum(r["repeat_winner"]=="True" for r in history),
            comparable_worst_iterations=len(comparable),different_recovery_worst=sum(r["oracle_winner"]!=r["recovery_worst"] for r in comparable),
            master_variables=[int(r["master_variables"]) for r in history],master_constraints=[int(r["master_constraints"]) for r in history],
            master_nonzeros=[int(r["master_nonzeros"]) for r in history],
            master_wall_seconds=timed["master"],oracle_wall_seconds=timed["oracle"],
            master_level_seconds={tier:sum(float(r["runtime_seconds"]) for r in tiers if r["level"]==tier)
                    for tier in ("service","backlog","economics")},
            oracle_milps=len(solves),independent_replay_milps=len(final),final_critical_scenarios=critical,
            oracle_jobs_by_event_count=groups,peak_rss_bytes=run["peak_rss_bytes"],
            end_to_end_wall_seconds=run["wall_seconds"])
    master = sum(r["master_wall_seconds"] for r in cases.values())
    separation = sum(r["oracle_wall_seconds"] for r in cases.values())
    return dict(cases=cases,direct=de,master_seconds_completed=master,oracle_seconds_completed=separation,
                oracle_share_completed=separation/(master+separation) if master+separation else None,
                resource_stops=Counter(r.get("stop",{}).get("solver_status","OTHER") if isinstance(r.get("stop"),dict) else "OTHER"
                                       for r in verdict["results"] if r["status"]!="PASS"),
                peak_rss_bytes=verdict["peak_rss_bytes"])


def retain_unfinished_discoveries(folder, report):
    rows=read(folder,"scenario_discovery")
    history=read(folder,"iteration_profile")
    for r in rows:
        r["final_certificate_status"]="PASS"
        r["holding_cost_critical_in_full_replay"]=r["scenario"] in report["cases"][r["run"]]["final_critical_scenarios"]["economics"]
    for name, case in report["cases"].items():
        if case["status"]=="PASS":
            continue
        events=[r for r in history if r["run"]==name]
        if not events:
            continue
        old=events[0]
        for i,s in [(0,"NOM"),*((int(r["iteration"]),r["added"]) for r in events if r["added"])]:
            atoms=s.split("+") if s!="NOM" else []
            rows.append(dict(run=name,budget_cents=old["budget_cents"],gamma=old["gamma"],iteration=i,scenario=s,
                families=";".join(a.rsplit("_",1)[0] for a in atoms),levels=";".join(a.rsplit("_",1)[1] for a in atoms),
                primary_critical="",secondary_critical="",repeated_later=any(int(r["iteration"])>i and r["oracle_winner"]==s for r in events),
                remained_binding_in_final_master="",final_full_replay_rank="",final_certificate_status=case["status"]))
    if rows:
        unique={(r["run"],r["scenario"]):r for r in rows}
        with (folder/"gate4a_scenario_discovery.csv").open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
            w.writeheader()
            w.writerows(unique.values())


def write_partial_comparisons(folder):
    comparisons=read(folder,"direct_de_comparison")
    cases=json.loads((folder/"gate4a_summary.json").read_bytes())["results"]
    stages={(r["run"],r["level"]):r for r in read(folder,"lexicographic_profile")}
    if not comparisons:
        return
    for row in comparisons:
        name=row["case"]
        ccg=next(r for r in cases if r["case"]==name and r["method"]=="CCG")
        for tier, key in (("service","ot"),("backlog","tau"),("economics","cost_ticks")):
            result=stages.get((name+"_DE",tier),{})
            row[f"DE_{tier}_status"]=result.get("solver_status")
            row[f"DE_{tier}_incumbent"]=result.get("objective")
            row[f"DE_{tier}_best_bound"]=result.get("best_bound")
            row[f"DE_{tier}_gap"]=result.get("mip_gap")
            row[f"{tier}_exact_comparison"]=(float(result["objective"])==ccg[key]
                if key in ccg and result.get("exact")=="True" else "NOT_CERTIFIED")
    fields=list(dict.fromkeys(k for row in comparisons for k in row))
    with (folder/"gate4a_direct_de_comparison.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(comparisons)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    result=profile(args.folder)
    retain_unfinished_discoveries(args.folder,result)
    write_partial_comparisons(args.folder)
    (args.folder/"gate4a_profile_summary.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
