"""Archive a single-instance four-method comparison with exactness checks."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from solver import METHODS
from archive_evidence import safe_copy
from common import TOL, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    root=args.out
    root.mkdir(parents=True)
    (root/".gitattributes").write_bytes(b"* -text\n")
    configs={}
    results={}
    for name in METHODS:
        src=args.runs/name
        dest=root/name
        dest.mkdir()
        for file in sorted(src.iterdir()):
            if file.suffix in (".json",".log") and file.name!="raw.log":
                safe_copy(file,dest/file.name)
        configs[name]=json.loads((dest/"config.json").read_bytes())
        results[name]=json.loads((dest/"result.json").read_bytes())
    for key in ("input_sha256","protocol_sha256","protocol_manifest_sha256","platform","solver_parameters","budget_cents","gamma","python","gurobi"):
        assert all(c[key]==configs["plain"][key] for c in configs.values()),key
    plain=results["plain"]
    fields=("ot","tau","cost_ticks")
    comparison=[]
    for name,r in results.items():
        comparable=plain["status"]==r["status"]=="PASS"
        match=comparable and all(plain[key]==r[key] for key in fields)
        exact=match and r["mip_gap"]==0 and r["max_residual"]<=TOL
        row={k:r.get(k) for k in ("status",*fields,"wall_seconds","master_seconds","oracle_seconds","oracle_milps",
            "replay_milps","replay_seconds","peak_rss_bytes","mip_gap","max_residual")}
        comparison.append(dict(method=name,**row,exact_agreement=exact,
            wall_speedup=plain["wall_seconds"]/r["wall_seconds"] if exact else None,
            oracle_calls_reduction=1-r["oracle_milps"]/plain["oracle_milps"] if exact else None))
    with (root/"comparison.csv").open("w",encoding="utf8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]),lineterminator="\n")
        w.writeheader()
        w.writerows(comparison)
    write_json(root,"audit.json",dict(status="PASS_DIAGNOSTIC" if all(r["exact_agreement"] for r in comparison) else "BLOCKED",
        comparisons=comparison, instances=1, timing_repetitions=1, learning_ranking="BLOCKED_NO_INDEPENDENT_REPLICATION"))
    paths=sorted(file for file in root.rglob("*") if file.is_file())
    (root/"sha256.txt").write_bytes("".join(
        f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.relative_to(root).as_posix()}\n" for file in paths).encode())


if __name__=="__main__":
    main()
