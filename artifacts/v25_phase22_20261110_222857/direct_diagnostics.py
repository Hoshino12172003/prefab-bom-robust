"""Direct scenario-expanded MILP and independent certificate replay."""
import json
import os
import subprocess
import sys
from dataclasses import replace
from time import perf_counter

import gurobipy as gp
import numpy as np
import psutil
from gurobipy import GRB

from design import (DEMAND,F,HERE,NR,ONE,ROOT,RAW,RATIO,SCALES,TOTAL,benchmark_family,
                    exact_cover,fixed_service,prices,prior)
from prefab_v25.data import CELL,NOMINAL,OEM,PACK,PROD,T1,Scenario,receipts

TIME_LIMIT=60
SOFT_MEM_GB=2


def replicate(network,n):
    if n==1:
        return network
    # Parallel lanes pooled by physical stage, with exact configured-order aggregation.
    groups=tuple(replace(g,orders=tuple(replace(o,vin=f'{o.vin}#R{i}')
                         for i in range(1,n+1) for o in g.orders)) for g in network.groups)
    arcs=tuple(replace(a,capacity={t:n*q for t,q in a.capacity.items()}) for a in network.arcs)
    return replace(network,groups=groups,arcs=arcs,initial={key:n*q for key,q in network.initial.items()},
        historical=tuple((*row[:-1],n*row[-1]) for row in network.historical),
        product_caps={key:n*q for key,q in network.product_caps.items()},
        group_caps={key:n*q for key,q in network.group_caps.items()},
        inventory_bounds={key:(n*lo,n*hi) for key,(lo,hi) in network.inventory_bounds.items()})


def build(network,profiles,k,r,premium,fixed=None,allow_t1=True,env=None):
    model=gp.Model('phase22_direct',env=env)
    model.Params.Threads=1
    model.Params.Seed=0
    model.Params.TimeLimit=TIME_LIMIT
    model.Params.SoftMemLimit=SOFT_MEM_GB
    model.Params.LogToConsole=0
    model.Params.MIPGap=model.Params.MIPGapAbs=0
    model.Params.OptimalityTol=model.Params.FeasibilityTol=model.Params.IntFeasTol=1e-9
    x=tuple(model.addVar(vtype=GRB.INTEGER,name=name) for name in ('x_C','x_T','x_O'))
    if fixed is not None:
        for var,value in zip(x,fixed):
            var.LB=var.UB=int(value)
    if not allow_t1:
        x[1].UB=0
    c,t1,o=x
    z=model.addVar(vtype=GRB.INTEGER,ub=network.demand_weight,name='Z')
    scale,coef=prices(r,premium)
    model.addConstr(gp.LinExpr(coef,x)<=int(r*k*scale),name='budget')
    initial=network.initial|{(T1,PACK):t1,(OEM,PACK):o}
    background=receipts(network,NOMINAL)
    blocks=[]
    for i,profile in enumerate(profiles):
        factors=profile.factors
        release=model.addVars(network.periods,vtype=GRB.INTEGER,name=f's{i}_K_release')
        last=0
        incoming=background.copy()
        for j,t in enumerate(network.periods):
            a=factors[0][j]
            remainder=a.numerator*c-a.denominator*release[t]
            model.addConstr(remainder>=0)
            model.addConstr(remainder<=a.denominator-1)
            for component,bom in zip(CELL,(10,6,4)):
                incoming[PROD,component,t]=bom*(release[t]-last)
            last=release[t]
        risk=Scenario(profile.name,{},dict(zip(network.periods,factors[1])),dict(zip(network.periods,factors[2])))
        block=prior.prior._block(model,network,risk,initial,incoming,f's{i}')
        inventory,_,_,_,service=block
        for t in network.periods:
            for component,bom in zip(CELL,(10,6,4)):
                model.addConstr(inventory[PROD,component,t]+bom*(c-release[t])<=network.inventory_bounds[PROD,component][1])
        model.addConstr(z<=service,name=f's{i}_guarantee')
        blocks.append((release,service))
    model.setObjective(z,GRB.MAXIMIZE)
    model.update()
    return model,x,z,blocks


def run_direct(name,network,profiles,k,r,premium,n,*,fixed=None,allow_t1=True,env=None,expected=None):
    if expected is None:
        expected=exact_cover(profiles,k,r,premium,n,allow_t1)[0] if fixed is None else min(
            fixed_service(p,fixed,n) for p in profiles)
    start=perf_counter()
    model,x,z,blocks=build(network,profiles,k,r,premium,fixed,allow_t1,env)
    path=HERE/'logs'/f'{name}.log'
    model.Params.LogFile=os.path.relpath(path)
    model.message(f'STRUCTURAL_DIAGNOSTIC_ONLY {name} scenarios={len(profiles)} replicas={n}')
    # No warm start from the analytical oracle in the DE comparison.
    opt_start=perf_counter()
    model.optimize()
    optimize_wall=perf_counter()-opt_start
    labels={GRB.OPTIMAL:'OPTIMAL',GRB.TIME_LIMIT:'TIME_LIMIT',GRB.MEM_LIMIT:'MEM_LIMIT',
            GRB.INFEASIBLE:'INFEASIBLE',GRB.NUMERIC:'NUMERIC'}
    status=labels.get(model.Status,str(model.Status))
    q=xval=gap=residual=integer_residual=realized=None
    bound=None
    if model.SolCount:
        vals=np.asarray(model.getAttr('X'))
        ints=np.rint(vals).astype(np.int64)
        residual=max(model.ConstrVio,model.BoundVio,model.IntVio,float(np.max(np.abs(vals-ints))))
        assert residual<=1e-7
        matrix=model.getA()
        assert np.all(matrix.data==np.rint(matrix.data))
        lhs=matrix@ints
        rhs=np.asarray(model.getAttr('RHS'))
        senses=np.asarray(model.getAttr('Sense'))
        assert np.all(lhs[senses=='<']<=rhs[senses=='<'])
        assert np.all(lhs[senses=='>']>=rhs[senses=='>'])
        assert np.all(lhs[senses=='=']==rhs[senses=='='])
        assert np.all(ints>=np.asarray(model.getAttr('LB'))) and np.all(ints<=np.asarray(model.getAttr('UB')))
        integer_residual=0
        xval=tuple(int(ints[v.index]) for v in x)
        q=int(ints[z.index])
        scale,coef=prices(r,premium)
        assert sum(a*v for a,v in zip(coef,xval))<=int(r*k*scale)
        assert (fixed is None or xval==fixed) and (allow_t1 or xval[1]==0)
        realized=[]
        for p,(release,service) in zip(profiles,blocks):
            assert all(int(ints[release[t].index])==int(g*xval[0])
                       for t,g in zip(network.periods,p.factors[0]))
            value=int(round(service.getValue()))
            assert q<=value<=fixed_service(p,xval,n)
            realized.append(value)
        gap=float(model.MIPGap)
        bound=float(model.ObjBound)
        assert q<=expected<=bound+1e-7
        if status=='OPTIMAL':
            assert q==expected and abs(bound-q)<=1e-7 and gap==0 and min(realized)==q
    memory=psutil.Process().memory_info()
    result=dict(case_id=name,replicas=n,scenario_count=len(profiles),scenario_ids='|'.join(p.name for p in profiles),
        budget=str(r*k),variables=model.NumVars,binaries=model.NumBinVars,integer_variables=model.NumIntVars,
        constraints=model.NumConstrs,nonzeros=model.NumNZs,wall_s=perf_counter()-start,optimize_wall_s=optimize_wall,
        gurobi_runtime_s=model.Runtime,nodes=model.NodeCount,process_peak_working_set_bytes=memory.peak_wset,
        gurobi_peak_gb=model.MaxMemUsed,status=status,objective=q,objective_bound=bound,gap=gap,
        independent_exact_bound=int(expected),max_solver_residual=residual,rounded_matrix_residual=integer_residual,
        portfolio=str(xval),realized_scenario_service=json.dumps(realized),threads=1,seed=0,presolve='AUTO',
        time_limit_s=TIME_LIMIT,soft_mem_limit_gb=SOFT_MEM_GB,log=path.relative_to(HERE).as_posix())
    model.dispose()
    return result


def benchmark_one(case):
    family,_=benchmark_family()
    _,n,profiles,_=next(row for row in family if row[0]==case)
    start=perf_counter()
    network,_=prior.prior.load_prospective()
    network=replicate(network,n)
    assert network.demand_weight==TOTAL*n
    with gp.Env() as env:
        result=run_direct(case,network,profiles,n*SCALES[5],RATIO,F(1,10),n,env=env)
    result['worker_elapsed_s']=perf_counter()-start
    (HERE/f'{case}_metrics.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    benchmark_one(sys.argv[1])
