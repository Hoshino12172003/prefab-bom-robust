"""Retain both attempts and select the exact-baseline evidence for reporting."""

import argparse
import csv
import gzip
import hashlib
import json
import re
from pathlib import Path

from profile_summary import profile, read, retain_unfinished_discoveries, write_partial_comparisons


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        writer=csv.DictWriter(f,fields,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def json_bytes(contents):
    return (json.dumps(contents,indent=2,ensure_ascii=False)+"\n").encode()


def safe_copy(source, target):
    data=source.read_bytes()
    if source.suffix==".log":
        log=data.decode("utf-8")
        log=re.sub(r'(?m)^Set parameter LogFile to value "[^"\r\n]*"',f'Set parameter LogFile to value "{target.name}"',log)
        log=re.sub(r"(?mi)^.*(?:licenseid|wlssecret|wlsaccessid|license .*expir|set parameter username).*$",
                   "[local license metadata redacted]",log)
        data=("".join(x.rstrip()+"\n" for x in log.splitlines())).encode()
    elif source.suffix!=".gz":
        data=data.replace(b"\r\n",b"\n")
    exposed=gzip.decompress(data) if source.suffix==".gz" else data
    assert not re.search(rb"(?i)[a-z]:[\\/](?:users|chatgpt)|WLS(?:ACCESSID|SECRET)|LicenseID|ghp_[a-z0-9]+|BEGIN [A-Z ]*PRIVATE KEY",exposed)
    target.write_bytes(data)


def archive(initial, retry, max_retry, out):
    attempts={"initial":initial,"integer_backlog_retry":retry,"integer_holding_retry":max_retry}
    folders={"initial":"initial_attempt","integer_backlog_retry":"integer_backlog_retry","integer_holding_retry":"integer_holding_retry"}
    reports={tag:json.loads((folder/"gate4a_summary.json").read_bytes()) for tag,folder in attempts.items()}
    configs={tag:json.loads((folder/"gate4a_config.json").read_bytes()) for tag,folder in attempts.items()}
    ceiling=reports["initial"]["bmax_cents"]
    assert all(r["bmax_cents"]==ceiling for r in reports.values())
    for tag,config in configs.items():
        for key in ("input_sha256","protocol_sha256","protocol_manifest_sha256","baseline","scenario_counts","solver_parameters"):
            assert config[key]==configs["initial"][key], (tag,key)
    assert {r["case"] for r in reports["integer_backlog_retry"]["results"]}=={"G2_MID","G2_ZERO","G2_MAX"}
    assert {r["case"] for r in reports["integer_holding_retry"]["results"]}=={"G2_MAX"}
    selected={}
    older=[]
    for tag, report in reports.items():
        for row in report["results"]:
            key=row["case"],row["method"]
            if tag!="initial":
                assert row["method"]=="CCG" and selected[key]["status"]!="PASS"
                older.append(selected[key])
            selected[key]=dict(attempt=tag,**row)
    fitted=list(selected.values())
    out.mkdir()
    (out/".gitattributes").write_bytes(b"* -text\n")
    for tag, src in attempts.items():
        dest=out/folders[tag]
        dest.mkdir()
        for file in sorted(src.iterdir()):
            if file.is_file():
                safe_copy(file,dest/file.name)
    for name in ("gate4a_bmax.json","formal_budget_grid.csv"):
        safe_copy(initial/name,out/name)
    # Direct DE uses the original model's objective envelopes rather than the fixed-policy oracle objectives.
    for name in ("iteration_profile","master_growth","lexicographic_profile","oracle_profile","scenario_discovery","final_replay","first_stage_solutions"):
        rows=[]
        for tag, folder in attempts.items():
            for r in read(folder,name):
                run=r["run"]
                case="_".join(run.split("_")[:2])
                method=r.get("method","DIRECT_DE" if "_DE" in run else "CCG")
                if selected[case,method]["attempt"]==tag:
                    rows.append(dict(attempt=tag,**r))
        if rows:
            write_rows(out/f"gate4a_{name}.csv",rows)
    by_key={(r["case"],r["method"]):r for r in fitted}
    comparisons=[]
    for case in ("G1_MID","G2_MID"):
        a=by_key[case,"CCG"]
        b=by_key[case,"DIRECT_DE"]
        comparable=a["status"]==b["status"]=="PASS"
        comparisons.append(dict(case=case,ccg_status=a["status"],de_status=b["status"],
           match=comparable and all(a[k]==b[k] for k in ("ot","tau","cost_ticks")),
           both_first_stages_feasible=comparable and max(a["max_residual"],b["max_residual"])<=1e-6))
    write_rows(out/"gate4a_direct_de_comparison.csv",comparisons)
    certified=all(r["status"]=="PASS" for r in fitted) and all(r["match"] and r["both_first_stages_feasible"] for r in comparisons)
    summary=dict(PLAIN_CCG_CERTIFIED=certified,bmax_cents=ceiling,results=fitted,comparisons=comparisons,
        peak_rss_bytes=max(r["peak_rss_bytes"] for r in reports.values()),
        superseded_attempts=older)
    (out/"gate4a_summary.json").write_bytes(json_bytes(summary))
    (out/"gate4a_config.json").write_bytes(json_bytes(configs))
    measured=profile(out)
    retain_unfinished_discoveries(out,measured)
    write_partial_comparisons(out)
    (out/"gate4a_profile_summary.json").write_bytes(json_bytes(measured))
    paths=sorted(p for p in out.rglob("*") if p.is_file())
    manifest=[dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    write_rows(out/"sha256_manifest.csv",manifest)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("initial","retry","max_retry","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    args=p.parse_args()
    archive(args.initial,args.retry,args.max_retry,args.out)
