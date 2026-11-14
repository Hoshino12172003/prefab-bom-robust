"""Run the source-case deterministic gate and replay its integer solution."""
import csv
import gzip
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"src"))
from prefab_v25.data import CELL,PACK,PROD,T1
from prefab_v25.source import load_tables
from prefab_v3.base import ASSEMBLY,Weights,add_block,source_base

SOURCE=Path("external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip")
CASES=(("A_NO_RESCHEDULE",False,Weights()),
       ("A_NO_RESCHEDULE_FIG10_ETA0",False,replace(Weights(),unassigned=0)),
       ("B_RESCHEDULE_FIG10",True,Weights()),
       ("B_RESCHEDULE_TEXT_ETA0",True,replace(Weights(),unassigned=0)))


def write(name,rows):
    with (HERE/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def integer_values(model,block):
    vectors={}
    for name in ("flow","inventory","external","shortfall","outflow","unassigned"):
        values=model.getAttr("X",getattr(block,name))
        integers={k:round(v) for k,v in values.items()}
        assert all(n>=0 and abs(n-values[k])<=1e-7 for k,n in integers.items())
        vectors[name]=integers
    return vectors


def replay(base,block,v,weights,reschedule,name):
    net=base.network
    t_set=net.periods
    f,inv,ext,os_,of,uc=(v[k] for k in ("flow","inventory","external","shortfall","outflow","unassigned"))
    ledger=Counter(block.regular_opening)
    assert not block.protection_opening
    changes=Counter(block.receipts)
    changes.update(ext)
    utilization={}
    for a in net.arcs:
        for t in t_set:
            total=0
            for p,recipe in a.recipes.items():
                k=(*a.key,p,t)
                q=f[k]
                total+=q
                assert q<=net.product_caps.get(k,q)
                changes[a.destination,p,t+a.lead]+=q
                for child,qty in recipe:
                    changes[a.origin,child,t]-=q*qty
            assert total<=min(a.capacity[t],net.group_caps.get((*a.key,t),a.capacity[t]))
            if a.key==ASSEMBLY:
                assert total+uc[t]==a.capacity[t]
                utilization[t]=total
    delivery_rows=[]
    early=late=on_due=bev_short=assembly_early=assembly_late=0
    due_delivered,bev_due_delivered,bev_due_short=Counter(),Counter(),Counter()
    deviation=0
    for g in net.groups:
        due=g.representative.due
        bev=(PACK,1) in g.representative.bom
        assembly=[t for t in t_set for _ in range(f[(*ASSEMBLY,g.id,t)])]
        dates=[t for t in t_set for _ in range(of[g.id,t])]
        assert len(assembly)==len(dates)==len(g.orders)-os_[g.id,due]
        assert all(a<=d for a,d in zip(assembly,dates))
        for t in t_set:
            changes[g.representative.node,g.id,t]-=of[g.id,t]
            if t!=due:
                assert os_[g.id,t]==0
                if not reschedule:
                    assert of[g.id,t]==f[(*ASSEMBLY,g.id,t)]==0
        for i,o in enumerate(g.orders):
            a,d=(assembly[i],dates[i]) if i<len(dates) else (None,None)
            delivery_rows.append(dict(case=name,vin=o.vin,order_group=g.id,bev=bev,promised=due,
                                      assembly=a,delivery=d,shortfall=d is None))
            if d is None:
                bev_short+=bev
                bev_due_short[due]+=bev
                continue
            deviation+=abs(d-due)
            early+=d<due
            late+=d>due
            assembly_early+=a<due
            assembly_late+=a>due
            on_due+=d==due
            due_delivered[d]+=1
            bev_due_delivered[d]+=bev
    for t in t_set:
        for n,p in net.state_keys():
            ledger[n,p]+=changes[n,p,t]
            lo,hi=net.inventory_bounds.get((n,p),(0,float("inf")))
            if n==ASSEMBLY[0] and base.products[p]=="seat":
                hi=0
            assert lo<=ledger[n,p]==inv[n,p,t]<=hi
    timeline=[]
    for t in t_set:
        timeline.append(dict(case=name,period=t,assembly=utilization[t],unassigned=uc[t],
            assembly_utilization=utilization[t]/(utilization[t]+uc[t]),
            deliveries=due_delivered[t],bev_deliveries=bev_due_delivered[t],bev_shortfall_due_cohort=bev_due_short[t],
            component_1=inv[PROD,CELL[0],t],component_2=inv[PROD,CELL[1],t],component_3=inv[PROD,CELL[2],t],
            t1_pack=inv.get((T1,PACK,t),0),oem_pack=inv[ASSEMBLY[0],PACK,t],
            pack_produced=f[PROD,T1,PACK,t],pack_shipped=f[T1,ASSEMBLY[0],PACK,t]))
    components=dict(flow=weights.flow*sum(f.values()),inventory=weights.inventory*sum(inv.values()),
        shortfall=weights.shortfall*sum(os_.values()),deviation=weights.deviation*deviation,
        unassigned=weights.unassigned*sum((t_set[-1]-t+1)*uc[t] for t in t_set))
    write(f"{name}_VIN_schedule.csv",delivery_rows)
    with gzip.open(HERE/f"{name}_integer_solution.json.gz","wt",encoding="utf-8") as out:
        json.dump({family:[[key,q] for key,q in values.items() if q] for family,values in v.items()},out)
    result=dict(delivered=sum(of.values()),bev_delivered=3003-bev_short,bev_shortfall=bev_short,
        nonbev_delivered=sum(of.values())-(3003-bev_short),on_due=on_due,early=early,late=late,
        assembly_early=assembly_early,assembly_late=assembly_late,
        total_abs_delivery_deviation=deviation,order_shortfall=sum(os_.values()),
        oem_utilization=sum(utilization.values())/(sum(utilization.values())+sum(uc.values())),
        oem_unassigned=sum(uc.values()),max_exact_balance_residual=0,
        **{f"penalty_{k}":value for k,value in components.items()})
    return result,timeline


def solve(base,name,reschedule,weights,env):
    with gp.Model(name,env=env) as model:
        model.Params.LogToConsole=0
        log=HERE/"logs"/f"{name}.log"
        log.write_text("",encoding="utf-8")
        model.Params.LogFile=os.path.relpath(log)
        model.Params.Threads=4
        model.Params.Seed=20261110
        model.Params.OptimalityTol=model.Params.FeasibilityTol=model.Params.IntFeasTol=1e-9
        model.Params.MIPGap=model.Params.MIPGapAbs=0
        model.Params.TimeLimit=120
        block=add_block(model,base,"qu",weights,reschedule)
        model.setObjective(block.loss,GRB.MINIMIZE)
        model.optimize()
        status={GRB.OPTIMAL:"OPTIMAL",GRB.TIME_LIMIT:"TIME_LIMIT",GRB.INFEASIBLE:"INFEASIBLE"}.get(
            model.Status,str(model.Status))
        result=dict(case=name,target="XLSB_REPLICATION_TARGET",rescheduling=reschedule,
                    weight_flow=weights.flow,weight_inventory=weights.inventory,weight_shortfall=weights.shortfall,
                    weight_deviation=weights.deviation,weight_unassigned=weights.unassigned,status=status,
                    variables=model.NumVars,constraints=model.NumConstrs,integers=model.NumIntVars,
                    seconds=model.Runtime,node_count=model.NodeCount,flow_variables=len(block.flow),
                    inventory_variables=len(block.inventory),shortfall_variables=len(block.shortfall),
                    outflow_variables=len(block.outflow),unassigned_variables=len(block.unassigned),
                    external_variables=len(block.external),log=f"logs/{name}.log")
        timeline=[]
        if model.SolCount:
            residual=max(model.ConstrVio,model.BoundVio,model.IntVio)
            assert residual<=1e-7
            ledger,timeline=replay(base,block,integer_values(model,block),weights,reschedule,name)
            exact=sum(v for k,v in ledger.items() if k.startswith("penalty_"))
            assert abs(model.ObjVal-exact)<=1e-7
            result.update(objective=exact,bound=model.ObjBound,gap=model.MIPGap,
                          max_solver_residual=residual,**ledger)
        print(name,status,result.get("objective"),result.get("bev_shortfall"),flush=True)
        return result,timeline


def main():
    tables=load_tables(SOURCE)
    base,audit=source_base(tables)
    (HERE/"logs").mkdir(exist_ok=True)
    rows,timeline=[],[]
    with gp.Env() as env:
        for name,reschedule,weights in CASES:
            r,t=solve(base,name,reschedule,weights,env)
            rows.append(r)
            timeline.extend(t)
    (HERE/"replication_run.json").write_text(json.dumps(dict(results=rows,source=audit,gurobi=gp.gurobi.version()),
        indent=2)+"\n",encoding="utf-8")
    if timeline:
        write("replication_timeline.csv",timeline)


if __name__=="__main__":
    main()
