"""Additional independent DE check using the proved exact scenario cover."""

import argparse
from collections import defaultdict
from pathlib import Path

from solver import baseline, capacity_vectors, certify_cover
from archive_evidence import safe_copy
from common import SETTINGS, frozen_inputs, gp, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("bundle","xlsb","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--gamma",type=int,choices=(1,2),required=True)
    args=p.parse_args()
    op, nominal, _, scenarios, meta=frozen_inputs(args.xlsb,args.bundle)
    catalog=scenarios[args.gamma]
    ids, cover, _=certify_cover(capacity_vectors(op,catalog))
    picked={s:catalog[s] for s in ids}
    budget=11989002887
    out=args.out.resolve()
    out.mkdir(parents=True)
    write_json(out,"config.json",dict(**(meta | {"algorithm":"COVERED_DIRECT_DE"}), gamma=args.gamma,
        budget_cents=budget, coverage=cover, representative_count=len(picked)))
    evidence=defaultdict(list)
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile",str(out/"raw.log"))
        env.start()
        try:
            row=baseline.master(env,op,nominal,picked,budget,"covered_DE",out,evidence)
            replay=baseline.oracle(env,op,row,catalog,"covered_DE_replay",evidence["replay"],audit=True)
            assert replay["reason"]=="CERTIFIED"
            result=dict(status="PASS", **{key:row[key] for key in ("ot","tau","cost_ticks","max_residual")})
        except baseline.Incomplete as exc:
            result=dict(status="BLOCKED",stop=exc.row)
    for name,rows in evidence.items():
        write_json(out,name+".json",rows)
    safe_copy(out/"raw.log",out/"gurobi.log")
    write_json(out,"result.json",result)
    print(result,flush=True)


if __name__=="__main__":
    main()
