"""Solve the 20-by-21 historical stress matrix using the frozen V3 base."""
import csv
import gzip
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
from pathlib import Path

import gurobipy as gp
import numpy as np
from gurobipy import GRB

from design import (ARCS,COSTS,F,HERE,KS,LABEL,PERIODS,PHASE30,PRIOR,ROOT,SOURCE,
                    policies,scenarios)
sys.path.insert(0,str(ROOT/"src"))
from prefab_v25.data import CELL,NOMINAL,PROD,receipts
from prefab_v25.source import load_tables
from prefab_v3.base import ASSEMBLY,Weights,add_block,source_base
from prefab_v3.interface import add_stage_one
from prefab_v3.robust import on_time,protection_inventory

BASE=OPENING=None


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write(name,rows):
    rows=list(rows)
    with (HERE/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def verify_frozen():
    out={}
    for source in (PHASE30,PRIOR):
        manifest=source/"sha256_manifest.csv"
        rows=read(manifest)
        assert all(digest(ROOT/r["path"])==r["sha256"] for r in rows)
        out[source.name]={"entries":len(rows),"manifest_sha256":digest(manifest)}
    evidence=json.loads((PRIOR/"audit.json").read_text(encoding="utf-8"))
    assert digest(SOURCE)==evidence["source_zip_sha256"]
    return out


def init():
    global BASE,OPENING
    BASE,_=source_base(load_tables(SOURCE))
    assert BASE.network.demand_weight==28000
    OPENING=receipts(BASE.network,NOMINAL)


def data_for(s,opening,base):
    arrivals=dict(opening)
    factors={}
    capacities={a.key:a.capacity for a in base.network.arcs}
    for event in s.events:
        dates=range(event.start,event.start+event.duration)
        if event.resource=="B_RECEIPT":
            for key,value in opening.items():
                if key[0]==PROD and key[1] in CELL and key[2] in dates:
                    arrivals[key]=int(value*(1-event.severity))
        else:
            arc=ARCS[event.resource]
            for t in dates:
                raw=capacities[arc][t]
                if raw:
                    factors[(*arc,t)]=F(int(raw*(1-event.severity)),raw)
    return arrivals,factors


def env():
    e=gp.Env(empty=True)
    e.setParam("LogToConsole",0)
    e.start()
    return e


def configure(model,seconds=45):
    model.Params.LogToConsole=0
    model.Params.Threads=1
    model.Params.Seed=20261110
    model.Params.OptimalityTol=model.Params.FeasibilityTol=model.Params.IntFeasTol=1e-9
    model.Params.MIPGap=model.Params.MIPGapAbs=0
    model.Params.TimeLimit=seconds


def exact_vector(model,rows):
    raw=np.asarray(model.getAttr("X"))
    integer=np.rint(raw)
    residual=max(model.ConstrVio,model.BoundVio,model.IntVio,float(np.max(np.abs(raw-integer))))
    assert residual<=1e-7
    assert np.all(integer>=np.asarray(model.getAttr("LB"))) and np.all(integer<=np.asarray(model.getAttr("UB")))
    matrix,rhs,senses=rows
    lhs=matrix@integer
    assert np.all(lhs[senses=="="]==rhs[senses=="="])
    assert np.all(lhs[senses=="<"]<=rhs[senses=="<"])
    assert np.all(lhs[senses==">"]>=rhs[senses==">"])
    return integer,residual


def matrix_rows(model):
    return model.getA(),np.asarray(model.getAttr("RHS")),np.asarray(model.getAttr("Sense"))


def snapshot(base,block,s,vector,factors):
    groups=base.network.groups
    cap_by_arc={a.key:a for a in base.network.arcs}
    selected=[]
    early=late=0
    for g in groups:
        due=g.representative.due
        on=sum(int(vector[block.outflow[g.id,t].index]) for t in PERIODS if t<=due)
        early+=sum(int(vector[block.flow[(*ASSEMBLY,g.id,t)].index]) for t in PERIODS if t<due)
        late+=sum(int(vector[block.outflow[g.id,t].index]) for t in PERIODS if t>due)
        selected.append(on)
    saturated=[]
    for (i,j,t),factor in factors.items():
        a=cap_by_arc[i,j]
        cap=int(a.capacity[t]*factor)
        used=sum(int(vector[block.flow[i,j,p,t].index]) for p in a.recipes)
        if used==cap:
            saturated.append(f"{i}->{j}@{t}:{cap}")
    for t in PERIODS:
        if not vector[block.unassigned[t].index]:
            saturated.append(f"OEM@{t}")
    return selected,early,late,saturated


def solve_scenario(s):
    assert BASE is not None
    arrivals,factors=data_for(s,OPENING,BASE)
    result=[]
    solutions={}
    with env() as e,gp.Model(s.name,env=e) as model:
        configure(model)
        x=add_stage_one(model,COSTS,max(KS)*COSTS[1])
        block=add_block(model,BASE,s.name,Weights(0,0,0,0,0),reschedule=True,
                        fixed_receipts=arrivals,arc_factors=factors,protection=protection_inventory(x))
        model.setObjective(on_time(block,BASE),GRB.MAXIMIZE)
        model.update()
        rows=matrix_rows(model)
        for k,pid,policy in policies():
            spend=sum(a*b for a,b in zip(COSTS,policy))
            assert spend<=k*COSTS[1]
            model.reset()
            for var,value in zip(x,policy):
                var.LB=var.UB=value
            log=HERE/"logs"/f"{s.name}__{pid}.log"
            log.write_text("",encoding="utf-8")
            model.Params.LogFile=os.path.relpath(log)
            model.optimize()
            assert model.Status==GRB.OPTIMAL,(s.name,pid,model.Status)
            vector,residual=exact_vector(model,rows)
            counts,early,late,saturated=snapshot(BASE,block,s,vector,factors)
            q=sum(counts)
            assert q==model.ObjVal==model.ObjBound and model.MIPGap==0
            assert tuple(int(vector[v.index]) for v in x)==policy
            solutions[pid]={"group_on_time":counts,"saturated_capacity":saturated}
            result.append(dict(label=LABEL,scope="HISTORICAL_STRESSED_STATE",scenario_id=s.name,policy_id=pid,
                pack_equivalent_budget=k,budget=str(k*COSTS[1]),spend=str(spend),
                x_C=policy[0],x_T=policy[1],x_O=policy[2],Q_direct=q,bound=int(model.ObjBound),gap=model.MIPGap,
                status="OPTIMAL",early_assembly=early,late_outflow=late,seconds=model.Runtime,nodes=int(model.NodeCount),
                integer_variables=model.NumIntVars,constraints=model.NumConstrs,solver_residual=residual,
                exact_matrix_residual=0,log=log.relative_to(HERE).as_posix()))
    with gzip.open(HERE/"witness"/f"{s.name}.json.gz","wt",encoding="utf-8") as f:
        json.dump(solutions,f,separators=(",",":"))
    write(Path("runs")/f"{s.name}.csv",result)
    return s.name


def main():
    verify_frozen()
    for sub in ("logs","runs","witness"):
        (HERE/sub).mkdir(exist_ok=True)
    catalog=scenarios()
    with ProcessPoolExecutor(max_workers=4,initializer=init) as pool:
        for name in pool.map(solve_scenario,catalog):
            print(f"{name}: 20 fixed policies certified",flush=True)
    rows=[r for s in catalog for r in read(HERE/"runs"/f"{s.name}.csv")]
    assert len(rows)==420
    write("direct_fixed_raw.csv",rows)
    verify_frozen()


if __name__=="__main__":
    main()
