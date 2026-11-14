"""Run predeclared finite Direct DE levels only after the witness gate passes."""
import json
import os
import subprocess
import sys
from time import perf_counter

import gurobipy as gp
import psutil
from gurobipy import GRB

import run_matrix as run
from design import COSTS,HERE,LABEL,ROOT,de_scenarios


def early_witness():
    values={s:{r["policy_id"]:int(r["Q_direct"]) for r in run.read(HERE/"runs"/f"{s}.csv")}
            for s in ("B_RECEIPT_1","S_1","BS")}
    return any(q<min(values["B_RECEIPT_1"][x],values["S_1"][x]) for x,q in values["BS"].items())


def solve(count):
    run.init()
    base,opening=run.BASE,run.OPENING
    selected=de_scenarios()[:count]
    profiles=[run.data_for(s,opening,base) for s in selected]
    supports=[frozenset(factors) for _,factors in profiles]
    assert len(set(supports))==count and all(len(keys)==2 for keys in supports)
    log=HERE/"logs"/f"DE_{count:02d}.log"
    log.write_text("",encoding="utf-8")
    start=perf_counter()
    with run.env() as e,gp.Model(f"DE_{count:02d}",env=e) as model:
        run.configure(model,seconds=90)
        model.Params.SoftMemLimit=3
        model.Params.LogFile=os.path.relpath(log)
        x=run.add_stage_one(model,COSTS,644*COSTS[1])
        z=model.addVar(vtype=GRB.INTEGER,ub=28000,name="worst")
        blocks={}
        for s,(arrivals,factors) in zip(selected,profiles):
            b=run.add_block(model,base,s.name,run.Weights(0,0,0,0,0),reschedule=True,
                fixed_receipts=arrivals,arc_factors=factors,protection=run.protection_inventory(x))
            blocks[s.name]=b
            model.addConstr(z<=run.on_time(b,base))
        model.setObjective(z,GRB.MAXIMIZE)
        model.update()
        opt_start=perf_counter()
        model.optimize()
        opt_wall=perf_counter()-opt_start
        status={GRB.OPTIMAL:"OPTIMAL",GRB.TIME_LIMIT:"TIME_LIMIT",GRB.MEM_LIMIT:"MEM_LIMIT"}.get(
            model.Status,str(model.Status))
        q=gap=portfolio=solver_residual=""
        if model.SolCount:
            vector,solver_residual=run.exact_vector(model,run.matrix_rows(model))
            q=int(vector[z.index])
            portfolio=tuple(int(vector[v.index]) for v in x)
            actual=[sum(int(vector[b.outflow[g.id,t].index]) for g in base.network.groups
                        for t in base.network.periods if t<=g.representative.due) for b in blocks.values()]
            assert q<=min(actual)
            gap=model.MIPGap
            if status=="OPTIMAL":
                assert q==min(actual)==model.ObjVal==model.ObjBound and gap==0
        info=psutil.Process().memory_info()
        result=dict(label=LABEL,scenario_count=count,scenarios="|".join(s.name for s in selected),
            matrix_distinct_incomparable_rhs=count,integers=model.NumIntVars,constraints=model.NumConstrs,
            nonzeros=model.NumNZs,peak_working_set_bytes=info.peak_wset,gurobi_peak_gb=model.MaxMemUsed,
            wall_s=perf_counter()-start,optimize_wall_s=opt_wall,solver_seconds=model.Runtime,
            nodes=int(model.NodeCount),status=status,Q=q,bound=model.ObjBound,gap=gap,portfolio=portfolio,
            solver_residual=solver_residual,integer_matrix_replay=bool(model.SolCount),
            time_limit_s=90,soft_memory_gb=3,presolve="AUTO",log=log.relative_to(HERE).as_posix())
    (HERE/f"de_{count:02d}_result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


def main():
    assert early_witness(),"DE requires a certified multi-BOM witness"
    rows=[]
    for count in (4,8,16):
        subprocess.run([sys.executable,"-B",__file__,str(count)],cwd=ROOT,check=True)
        rows.append(json.loads((HERE/f"de_{count:02d}_result.json").read_text(encoding="utf-8")))
        run.write("direct_de_multi_bom_scaling.csv",rows)
        print(f"DE {count}: {rows[-1]['status']}",flush=True)


if __name__=="__main__":
    if len(sys.argv)>1:
        solve(int(sys.argv[1]))
    else:
        main()
