"""One frozen anchor-budget case, four independently timed variants."""

import argparse
import json
import platform
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from solver import METHODS, solve
import baseline
from archive_evidence import safe_copy
from common import SETTINGS, frozen_inputs, gp, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle","xlsb","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--method",choices=METHODS,required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True)
    op, nominal, protocol, scenarios, meta = frozen_inputs(args.xlsb,args.bundle)
    budget = protocol["budget"]["reference_anchor_cents"]
    archive = Path(__file__).resolve().parents[1]/"v33_gate4a_plain_ccg/evidence/gate4a_bmax.json"
    assert budget in json.loads(archive.read_bytes())["budget_grid_cents"]
    write_json(out,"config.json",dict(**(meta | {"algorithm":args.method}), gamma=1, budget_cents=budget,
        platform=platform.platform(), purpose="DIAGNOSTIC_ONE_CASE_ABLATION"))
    evidence = defaultdict(list)
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile",str(out/"raw.log"))
        env.start()
        started = perf_counter()
        try:
            result = solve(env,op,nominal,scenarios[1],budget,args.method,out,evidence)
        except baseline.Incomplete as failure:
            result = dict(status="BLOCKED",stop=failure.row)
        except (AssertionError,gp.GurobiError) as failure:
            result = dict(status="BLOCKED",stop=type(failure).__name__,details=str(failure))
        result.update(method=args.method, wall_seconds=perf_counter()-started,
            peak_rss_bytes=baseline.memory(), oracle_milps=len(evidence["oracle"]),
            replay_milps=len(evidence["replay"]),
            master_seconds=sum(row["master_seconds"] for row in evidence["iterations"]),
            oracle_seconds=sum(row["oracle_seconds"] for row in evidence["iterations"]),
            mip_gap=max((row["mip_gap"] for key in ("lexicographic_profile","replay")
                     for row in evidence[key] if row["mip_gap"] is not None),default=None))
    for key, rows in evidence.items():
        write_json(out,key+".json",rows)
    safe_copy(out/"raw.log",out/"gurobi.log")
    write_json(out,"result.json",result)
    print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
