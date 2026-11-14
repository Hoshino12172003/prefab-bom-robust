"""Structural diagnostic only: fixed due-day withdrawals on the three nonbattery chains."""
import csv
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))

import gurobipy as gp
from gurobipy import GRB
from prefab_v25.data import CELL, COMPONENT_ARC, NOMINAL, OEM, PACK, PRODUCTION_ARC, TRANSPORT_ARC, receipts
from prefab_v25.source import compile_network, load_tables

SOURCE=Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
LABEL='STRUCTURAL_DIAGNOSTIC_ONLY'
BATTERY_ITEMS={*CELL,PACK}
BATTERY_ARCS={COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC}
ASSEMBLY=(OEM,'zp8')


def write(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def due_requirements(groups):
    withdrawals,vehicles=Counter(),Counter()
    for group in groups:
        order=group.representative
        vehicles[order.due]+=len(group.orders)
        for item,units in order.bom:
            if item not in BATTERY_ITEMS:
                withdrawals[OEM,item,order.due]+=units*len(group.orders)
    return withdrawals,vehicles


def build(network,model,withdrawals,vehicles):
    arcs=[a for a in network.arcs if a.key not in BATTERY_ARCS|{ASSEMBLY}]
    assembly=next(a for a in network.arcs if a.key==ASSEMBLY)
    assert all(vehicles[t]<=assembly.capacity[t] for t in network.periods)
    stock_keys={(a.origin,c) for a in arcs for recipe in a.recipes.values() for c,_ in recipe}
    stock_keys.update((a.destination,p) for a in arcs for p in a.recipes)
    external=sorted(k for k in network.external if k in stock_keys)
    periods=network.periods
    history=receipts(network,NOMINAL)
    inventory=model.addVars([(*key,t) for key in sorted(stock_keys) for t in periods],vtype=GRB.INTEGER,name='I')
    supply=model.addVars([(*key,t) for key in external for t in periods],vtype=GRB.INTEGER,name='e')
    flow=model.addVars([(*a.key,p,t) for a in arcs for p in a.recipes for t in periods],vtype=GRB.INTEGER,name='q')
    events=defaultdict(gp.LinExpr)
    for a in arcs:
        for t in periods:
            model.addConstr(gp.quicksum(flow[(*a.key,p,t)] for p in a.recipes)<=a.capacity[t])
            if (*a.key,t) in network.group_caps:
                model.addConstr(gp.quicksum(flow[(*a.key,p,t)] for p in a.recipes)<=network.group_caps[(*a.key,t)])
            for p,recipe in a.recipes.items():
                key=(*a.key,p,t)
                q=flow[key]
                if key in network.product_caps:
                    model.addConstr(q<=network.product_caps[key])
                for c,units in recipe:
                    events[a.origin,c,t]-=units*q
                if t+a.lead in periods:
                    events[a.destination,p,t+a.lead]+=q
    for key in sorted(stock_keys):
        previous=network.initial[key]
        for t in periods:
            at=(*key,t)
            value=inventory[at]
            model.addConstr(value==previous+history.get(at,0)+supply.get(at,0)+events[at]-withdrawals[at])
            if key in network.inventory_bounds:
                value.LB,value.UB=network.inventory_bounds[key]
            previous=value
    return inventory,supply,flow,stock_keys,arcs,history


def verify(network,withdrawals,parts):
    iv,sp,fl,keys,arcs,history=parts
    arrays=[]
    for variables in (iv,sp,fl):
        values={key:round(v.X) for key,v in variables.items()}
        assert all(q>=0 and abs(q-variables[k].X)<=1e-9 for k,q in values.items())
        arrays.append(values)
    inventory,supply,flow=arrays
    state={k:network.initial[k] for k in keys}
    changes=Counter()
    for a in arcs:
        for t in network.periods:
            total=0
            for p,recipe in a.recipes.items():
                key=(*a.key,p,t)
                q=flow[key]; total+=q
                assert q<=network.product_caps.get(key,q)
                for c,units in recipe:
                    changes[a.origin,c,t]-=units*q
                changes[a.destination,p,t+a.lead]+=q
            assert total<=min(a.capacity[t],network.group_caps.get((*a.key,t),a.capacity[t]))
    rows=[]
    for t in network.periods:
        for n,p in sorted(keys):
            at=(n,p,t)
            state[n,p]+=history.get(at,0)+supply.get(at,0)+changes[at]-withdrawals[at]
            lo,hi=network.inventory_bounds.get((n,p),(0,float('inf')))
            assert lo<=state[n,p]==inventory[at]<=hi
            if n==OEM and p in ('D83','G1Z','Q2J','Q4H'):
                rows.append(dict(period=t,item=p,withdrawal=withdrawals[at],opening=state[n,p]-history.get(at,0)-changes[at]+withdrawals[at],
                                 history=history.get(at,0),planned_receipt=changes[at],closing=state[n,p]))
    return arrays,rows


def solve(network,scope,groups):
    withdrawals,vehicles=due_requirements(groups)
    with gp.Model('Phase20_'+scope) as model:
        model.Params.LogToConsole=0
        model.Params.LogFile=os.path.relpath(HERE/f'{scope}.log')
        model.Params.Threads=1
        model.Params.OptimalityTol=model.Params.FeasibilityTol=model.Params.IntFeasTol=1e-9
        model.Params.MIPGap=model.Params.MIPGapAbs=0
        model.Params.DualReductions=0
        parts=build(network,model,withdrawals,vehicles)
        model.optimize()
        feasible=model.Status==GRB.OPTIMAL
        if feasible:
            arrays,rows=verify(network,withdrawals,parts)
            write(HERE/f'{scope}_selected_parts_ledger.csv',rows)
            with gzip.GzipFile(filename=str(HERE/f'{scope}_witness.json.gz'),mode='wb',mtime=0) as f:
                f.write(json.dumps({name:[[list(k),v] for k,v in a.items() if v]
                                    for name,a in zip(('inventory','supply','dispatch'),arrays)},separators=(',',':')).encode())
        return dict(scope=scope,label=LABEL,vehicles=sum(vehicles.values()),status=int(model.Status),
                    fixed_due_withdrawals_feasible=feasible,exact_material_residual=0 if feasible else None,
                    max_solver_residual=max(model.ConstrVio,model.BoundVio,model.IntVio) if feasible else None,
                    variables=model.NumVars,constraints=model.NumConstrs,seconds=model.Runtime)


def main():
    network,_=compile_network(load_tables(SOURCE))
    bev=tuple(g for g in network.groups if (PACK,1) in g.representative.bom)
    cases=[]
    for scope,groups in (('BEV3003',bev),('FULL28000',network.groups)):
        result=solve(network,scope,groups)
        cases.append(result)
        (HERE/'non_battery_diagnostic.json').write_text(json.dumps(cases,indent=2)+'\n',encoding='utf8')
        print(result,flush=True)


if __name__=='__main__':
    main()
