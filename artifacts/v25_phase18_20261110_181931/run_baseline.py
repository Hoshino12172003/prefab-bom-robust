"""Phase 1.8 source-calibrated baseline. Reuse the frozen integer nominal block."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]

import gurobipy as gp
from gurobipy import GRB
from examples.run_v25_formal import check_exact_budget
from prefab_v25.data import (BUFFER_NAMES, CELL, COMPONENT_ARC, Group, NOMINAL, OEM, PACK,
                             PROD, PRODUCTION_ARC, T1, TRANSPORT_ARC)
from prefab_v25.formal import frozen_runs, manifest_bytes
from prefab_v25.model import _block, initial_state
from prefab_v25.source import compile_network, load_tables, verified_bytes

SOURCE = Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
PAPER = Path('external_inputs/Optimisation model for multi-item multi-echelon supply chain.pdf')
REQUEST = Path('private_inputs/attachment/已粘贴的文本.txt')
FORMAL = ROOT/'artifacts/v25_formal_20261110'
P16 = ROOT/'artifacts/v25_phase16_20261110_160104'
SHA = '02143f46cab6e6a173a0f495e21b20d21311096f'
LENGTH, W = 14, 56
DOI, DATA = '10.1016/j.ejor.2020.08.005', '10.17632/pr3sdy5vp3.1'
ARRAYS = ('inventory', 'supply', 'dispatch', 'service')
MAIN = 'NB00'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def csv_file(path, rows, fields=None):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mapping(t, offset):
    return 61+(t-1+offset)%LENGTH


def horizon(source, length, offset, label, stock):
    """One equivalent order group for each original group and repeated cycle."""
    periods = tuple(range(1, length+1))
    groups = []
    for t in periods:
        old_t = mapping(t, offset)
        for g in source.groups:
            if g.representative.due == old_t:
                prefix = f'{label}_{t:02d}'
                orders = tuple(replace(o,vin=f'{prefix}_{o.vin}',due=t) for o in g.orders)
                groups.append(Group(f'{prefix}_{g.id}', orders))
    product_caps, group_caps = {}, {}
    for t in periods:
        old_t = mapping(t, 0)
        product_caps.update({(*key[:-1],t):q for key,q in source.product_caps.items() if key[-1]==old_t})
        group_caps.update({(*key[:-1],t):q for key,q in source.group_caps.items() if key[-1]==old_t})
    arcs = tuple(replace(a, capacity={t:a.capacity[mapping(t,0)] for t in periods},
                         recipes={g.id:g.representative.bom for g in groups} if ('zp7','zp8') == a.key else a.recipes)
                 for a in source.arcs)
    original_cars = next(a for a in source.arcs if a.key==('zp7','zp8'))
    assert all(original_cars.recipes[g.id] == g.representative.bom for g in source.groups)
    assert all(key[-2] not in original_cars.recipes for key in source.product_caps)
    return replace(source,periods=periods,arcs=arcs,groups=tuple(groups),initial=stock,historical=(),
                   product_caps=product_caps,group_caps=group_caps)


def seed_stock(source):
    old_cars = {g.id for g in source.groups}
    assert all(q==0 for (_,item),q in source.initial.items() if item in old_cars)
    return {key:q for key,q in source.initial.items() if key[1] not in old_cars}


def seed_pipeline(source):
    leads = {a.key:a.lead for a in source.arcs}
    return [(i,j,item,dispatch,lead,dispatch+lead-60,q)
            for i,j,item,dispatch,q in source.historical for lead in (leads[i,j],)
            if dispatch+lead>60 and q]


def arrival_map(pipeline, length):
    result = defaultdict(int)
    for _,dest,item,_,_,remaining,q in pipeline:
        assert remaining > 0
        if remaining <= length:
            result[dest,item,remaining] += q
    return dict(result)


def terminal_pipeline(network, dispatch, inherited):
    end = network.periods[-1]
    assert all(r[5] <= end for r in inherited), 'unexpired seed must retain its own identity'
    result = [(a.origin,a.destination,item,t,a.lead,t+a.lead-end,q)
              for a in network.arcs for item in a.recipes for t in network.periods
              if t+a.lead>end and (q:=dispatch.get((*a.key,item,t),0))]
    assert len(result)==len({r[:4] for r in result})
    return result


def integer_value(v):
    x = v.X
    rounded = round(x)
    assert abs(x-rounded)<=1e-8 and rounded>=0, (v.VarName,x)
    return rounded


def ledger(network, arrivals, arrays):
    """Audit all model rows using physical integer units and a separate event ledger."""
    inv, supply, flow, delivered = arrays
    eligible=set(network.external)
    assert all(key[:2] in eligible and key[-1] in network.periods for key in supply)
    assert all(type(v) is int and v>=0 for array in arrays for v in array.values())
    state = initial_state(network,(0,0,0))
    changes = defaultdict(int,arrivals)
    for arc in network.arcs:
        for t in network.periods:
            total = 0
            for item, recipe in arc.recipes.items():
                q = flow.get((*arc.key,item,t),0)
                assert q<=network.product_caps.get((*arc.key,item,t),q)
                total += q
                if q:
                    if t+arc.lead in network.periods:
                        changes[arc.destination,item,t+arc.lead] += q
                    for child,c in recipe:
                        changes[arc.origin,child,t] -= c*q
            assert total<=min(arc.capacity[t],network.group_caps.get((*arc.key,t),total))
    counts, terminal_orders = Counter(), []
    for group in network.groups:
        o = group.representative
        done = on_time = 0
        for t in network.periods:
            q = delivered.get((group.id,t),0)
            if q:
                changes[o.node,group.id,t] -= q
            done += q
            if t<=o.due:
                on_time += q
        assert done<=len(group.orders) and o.weight==1
        bev = (PACK,1) in o.bom
        counts['bev' if bev else 'non_bev'] += on_time
        counts['late'] += done-on_time
        terminal_orders.append(dict(group=group.id,due=o.due,demand=len(group.orders),on_time=on_time,
                                    late=done-on_time,undelivered=len(group.orders)-done,carry_to_formal=False))
    for t in network.periods:
        for node,item in state:
            key=(node,item,t)
            state[node,item] += changes.get(key,0)+supply.get(key,0)
            lb,ub=network.inventory_bounds.get((node,item),(0,math.inf))
            assert state[node,item]==inv.get(key,0) and lb<=state[node,item]<=ub, key
    return state, counts, terminal_orders


def configure(model, logfile):
    model.Params.LogToConsole=0
    model.Params.LogFile=os.path.relpath(logfile)
    model.Params.Threads=4
    model.Params.Seed=20261110
    model.Params.MIPGap=model.Params.MIPGapAbs=0
    model.Params.FeasibilityTol=model.Params.IntFeasTol=model.Params.OptimalityTol=1e-9


def supply_projection_bounds(network, arrivals):
    """Finite upper bounds for an equivalent optimum, used only to validate an LP bound."""
    external = set(network.external)
    incoming, uses = Counter(), Counter()
    for a in network.arcs:
        cap = sum(a.capacity.values())
        for item,recipe in a.recipes.items():
            incoming[a.destination,item] += cap
            for child,qty in recipe:
                uses[a.origin,child] += cap*qty
    for (n,i,_),q in arrivals.items():
        incoming[n,i] += q
    for group in network.groups:
        uses[group.representative.node,group.id] += len(group.orders)
    supply_cap={key:uses[key]+network.inventory_bounds.get(key,(0,math.inf))[0] for key in external}
    # Clipping any individual external injection to this cap preserves lower stock
    # bounds thereafter: it alone covers every possible remaining use plus min stock.
    inventory_cap={key:network.initial.get(key,0)+incoming[key]+len(network.periods)*supply_cap.get(key,0)
                   for key in network.state_keys()}
    return supply_cap,inventory_cap


def exact_lp_upper(model, network, block, arrivals, path, certificate=None):
    """Use LP multipliers only as candidates; validate a rigorous rational upper bound."""
    scale = 10**10
    with model.relax() as lp:
        lp.Params.LogFile=os.path.relpath(path)
        lp.setObjective(lp.getObjective()*network.demand_weight,GRB.MAXIMIZE)
        lp.optimize()
        assert lp.Status==GRB.OPTIMAL
        multipliers=lp.getAttr('Pi')
        lp_value=lp.ObjVal
    supply_cap,inventory_cap=supply_projection_bounds(network,arrivals)
    upper=[0]*model.NumVars
    inv,supply,flow,service,weighted=block
    capacities={a.key:a.capacity for a in network.arcs}
    order_count={g.id:len(g.orders) for g in network.groups}
    for key,v in inv.items(): upper[v.index]=inventory_cap[key[:2]]
    for key,v in supply.items(): upper[v.index]=supply_cap[key[:2]]
    for key,v in flow.items(): upper[v.index]=capacities[key[:2]][key[-1]]
    for key,v in service.items(): upper[v.index]=order_count[key[0]]
    remainder=[0]*model.NumVars
    for i in range(weighted.size()):
        coefficient=weighted.getCoeff(i)
        assert coefficient==1
        remainder[weighted.getVar(i).index]+=scale
    total=0
    nonzero_rows=[]
    for row,pi in zip(model.getConstrs(),multipliers):
        p=round(pi*scale)
        p=max(0,p) if row.Sense=='<' else min(0,p) if row.Sense=='>' else p
        if not p:
            continue
        assert row.RHS==int(row.RHS)
        total += p*int(row.RHS)
        if certificate is not None:
            nonzero_rows.append([row.ConstrName,p,int(row.RHS)])
        expr=model.getRow(row)
        for i in range(expr.size()):
            index=expr.getVar(i).index
            if upper[index]==0:
                continue
            coefficient=expr.getCoeff(i)
            assert coefficient==int(coefficient)
            remainder[index] -= p*int(coefficient)
    correction=sum(max(0,r)*u for r,u in zip(remainder,upper))
    proof=dict(method='exact rational LP multiplier bound with valid variable upper corrections',
               lp_solver_value=lp_value, numerator=total+correction, denominator=scale,
               correction_numerator=correction, integer_upper=(total+correction)//scale)
    if certificate is not None:
        corrections=[[v.VarName,r,u] for v,r,u in zip(model.getVars(),remainder,upper) if r>0 and u]
        save(certificate,dict(**proof,nonzero_rows=nonzero_rows,reduced_coefficient_corrections=corrections))
    return proof


def reachable_bev(network, arrivals):
    arcs={a.key:a for a in network.arcs}
    cell_lead=arcs[COMPONENT_ARC].lead
    downstream=arcs[PRODUCTION_ARC].lead+arcs[TRANSPORT_ARC].lead
    if cell_lead+downstream < len(network.periods):
        return None
    last=network.periods[-1]
    kits=min((network.initial.get((PROD,item),0)+sum(arrivals.get((PROD,item,t),0)
                for t in network.periods if t+downstream<=last))//coef
                for item,coef in arcs[PRODUCTION_ARC].recipes[PACK])
    return kits + sum(network.initial.get((node,PACK),0)+sum(arrivals.get((node,PACK,t),0)
               for t in network.periods if t+lead<=last) for node,lead in ((T1,1),(OEM,0)))


def warmup_material_upper(network, arrivals):
    """Valid optimistic count bound, independent of solver cuts and tolerances."""
    arcs={a.key:a for a in network.arcs}
    upstream=arcs[COMPONENT_ARC]
    last=network.periods[-1]
    tail=arcs[PRODUCTION_ARC].lead+arcs[TRANSPORT_ARC].lead
    assert {k for k in network.external if k[1] in (*CELL,PACK)} == {(upstream.origin,c) for c in CELL}
    assert {a.key for a in network.arcs if set(a.recipes)&set((*CELL,PACK))}=={COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC}
    cells=sum(network.initial.get((PROD,c),0) for c in CELL)
    cells+=sum(q for (n,i,t),q in arrivals.items() if n==PROD and i in CELL and t+tail<=last)
    cells+=sum(cap for t,cap in upstream.capacity.items() if t+upstream.lead+tail<=last)
    bom_total=sum(c for _,c in arcs[PRODUCTION_ARC].recipes[PACK])
    packs=sum(network.initial.get((node,PACK),0)+sum(arrivals.get((node,PACK,t),0)
               for t in network.periods if t+lead<=last) for node,lead in ((T1,1),(OEM,0)))
    bev_demand=sum(len(g.orders) for g in network.groups if (PACK,1) in g.representative.bom)
    upper=network.demand_weight-bev_demand+min(bev_demand,packs+cells//bom_total)
    return dict(integer_upper=upper, cell_units_upper=cells, existing_reachable_packs=packs,
                non_bev_demand=network.demand_weight-bev_demand)


def solve(network, pipeline, run, out, formal):
    arrivals=arrival_map(pipeline,len(network.periods))
    with gp.Model(out.name) as model:
        configure(model,out.with_suffix('.log'))
        buffers=[model.addVar(vtype=GRB.INTEGER,name=n) for n in BUFFER_NAMES]
        model.addConstr(gp.quicksum(c*x for c,x in zip(run.costs,buffers))<=run.budget)
        block=_block(model,network,NOMINAL,initial_state(network,buffers),arrivals,'s0')
        model.setObjective(block[-1]/network.demand_weight,GRB.MAXIMIZE)
        warm_bound=None if formal else warmup_material_upper(network,arrivals)
        if warm_bound:
            # Stop only at an independently established integer optimum. Formal
            # solves keep the original zero-gap protocol and no objective stop.
            model.Params.BestObjStop=math.nextafter(warm_bound['integer_upper']/network.demand_weight,-math.inf)
        print('START',out.name,flush=True)
        model.optimize()
        result=dict(status=int(model.Status),runtime=model.Runtime,work=model.Work,
                    variables=model.NumVars,integer_variables=model.NumIntVars,constraints=model.NumConstrs,
                    nodes=model.NodeCount)
        assert (model.Status==GRB.OPTIMAL and model.MIPGap<=1e-10 or
                warm_bound is not None and model.Status==GRB.USER_OBJ_LIMIT),result
        arrays=[]
        for variables in block[:4]:
            raw=model.getAttr('X',list(variables.values()))
            assert all(abs(v-round(v))<=1e-8 and round(v)>=0 for v in raw)
            arrays.append({k:round(v) for k,v in zip(variables,raw) if round(v)})
        stock,counts,orders=ledger(network,arrivals,arrays)
        count=counts['bev']+counts['non_bev']
        assert abs(model.ObjVal-count/network.demand_weight)<=1e-9
        result.update(status_name='OPTIMAL' if model.Status==GRB.OPTIMAL else 'USER_OBJ_LIMIT',
                      objective=model.ObjVal,bound=model.ObjBound,mip_gap=model.MIPGap,
                      on_time=count,bev=counts['bev'],non_bev=counts['non_bev'],late=counts['late'],
                      service_rate=count/network.demand_weight,material_balance_residual=0,
                      max_gurobi_residual=max(model.ConstrVio,model.BoundVio,model.IntVio),certified=True,
                      buffers=dict(zip(BUFFER_NAMES,map(integer_value,buffers))))
        check_exact_budget(run,result)
        assert result['certified'] and result['max_gurobi_residual']<=1e-8 and not any(result['buffers'].values())
        if warm_bound:
            assert count==warm_bound['integer_upper'], (count,warm_bound)
            result['independent_upper']=warm_bound
            result['independent_exact_certificate']=True
        reachable=reachable_bev(network,arrivals)
        if formal:
            bev_demand=sum(len(g.orders) for g in network.groups if (PACK,1) in g.representative.bom)
            material_upper=network.demand_weight-bev_demand+min(bev_demand,reachable)
            if material_upper==count:
                proof=dict(method='independent BEV material plus non-BEV demand bound',integer_upper=material_upper)
            else:
                proof=exact_lp_upper(model,network,block,arrivals,out.with_name(out.name+'_LP.log'))
            result.update(physical_upper=material_upper,independent_upper=proof,
                          independent_exact_certificate=proof['integer_upper']==count,
                          feasible_witness=count)
        end_pipeline=terminal_pipeline(network,arrays[2],pipeline) if not formal else []
        with gzip.GzipFile(filename=str(out.with_suffix('.json.gz')),mode='wb',mtime=0) as raw:
            raw.write(json.dumps({name:[[list(k),v] for k,v in a.items()] for name,a in zip(ARRAYS,arrays)},
                                 separators=(',',':')).encode('utf8'))
        print('END',out.name,count,result.get('independent_exact_certificate'),flush=True)
        return result,stock,end_pipeline,orders,arrays


def pack_state(rows, pipeline):
    inv_kit=min(rows.get((PROD,i),0)//q for i,q in zip(CELL,(10,6,4)))
    return dict(total_inventory=sum(rows.values()), battery_component_kit_equivalent=inv_kit,
                t1_pack=rows.get((T1,PACK),0),oem_pack=rows.get((OEM,PACK),0),
                total_in_transit=sum(r[-1] for r in pipeline))


def export_case(label, stock, pipeline, orders, warm, formal, arrays, net):
    out=HERE/label
    csv_file(out/'state.csv',[dict(offset=label,node=n,item=i,baseline_t=0,quantity=q,
                                warmup_t=W,source_var=f's0_I[{n},{i},{W}]') for (n,i),q in stock.items()])
    fields=('offset','origin','destination','item','warmup_dispatch_t','lead_time','warmup_arrival_t',
            'remaining_lead','formal_arrival_t','in_formal_window','quantity','source_var')
    transit=[dict(zip(fields,(label,i,j,item,t,lead,t+lead,remaining,remaining,remaining<=LENGTH,q,
                              f's0_q[{i},{j},{item},{t}]'))) for i,j,item,t,lead,remaining,q in pipeline]
    csv_file(out/'in_transit.csv',transit,fields)
    csv_file(out/'retired_orders.csv',orders)
    trajectory=[dict(period=t,**{f'cell{i+1}':arrays[0].get((PROD,c,t),0) for i,c in enumerate(CELL)},
                     T1_pack=arrays[0].get((T1,PACK,t),0),OEM_pack=arrays[0].get((OEM,PACK,t),0)) for t in net.periods]
    csv_file(out/'formal_battery_trajectory.csv',trajectory)
    health=dict(no_negative_stock=True,no_duplicate_transit=True,no_warmup_order_carry=True,
                raw_formal_order_pattern=True,from_solved_state=True)
    summary=dict(offset=label,warmup=warm,formal=formal,terminal=pack_state(stock,pipeline),health=health,
                 reachable_bev_supply=reachable_bev(net,arrival_map(pipeline,LENGTH)))
    save(out/'summary.json',summary)
    return summary


def protocol(source,tables):
    assert len(tables['nodes'])==12 and len(source.arcs)==11 and source.demand_weight==28000
    assert W==4*LENGTH and W>55 and W-LENGTH<=55
    assert NOMINAL.arrival==NOMINAL.production==NOMINAL.transport=={}
    manifest=dict(title='Source-Calibrated Nominal Baseline',git_sha=SHA,workbook_sha256=source.source_sha256,
        settling_periods_paper=55,warmup_periods=W,cycle=LENGTH,offsets=list(range(LENGTH)),main_baseline=MAIN,
        no_disruption_multipliers=dict(arrival=1,production=1,transport=1),budget=0,
        capacity_calendar='repeat original 61–74 in natural order for all offsets; raw physical units',
        formal_order_calendar='original natural order for every offset',seed='original t60 stock and fixed in-transit; initialization only',
        order_policy='same Phase 1.6 total group delivery cap, late allowed with zero on-time credit inside warmup; separate new formal orders',
        terminal_policy='all inventory and positive unfinished pipeline kept; warmup demand closed at formal boundary',
        objective='same weighted on-time service ratio as Phase 1.6; no secondary objective',
        solver=dict(threads=4,seed=20261110,OptimalityTol=1e-9,FeasibilityTol=1e-9,IntFeasTol=1e-9,MIPGap=0,MIPGapAbs=0))
    path=HERE/'baseline_manifest.json'
    if path.exists(): assert json.loads(path.read_text(encoding='utf8'))==manifest
    else: save(path,manifest)
    return manifest


def read_warmup(network,pipeline,out):
    """Recover a finished warm-up witness when an ensuing formal audit needs retry."""
    with gzip.open(out/'warmup.json.gz','rt',encoding='utf8') as f:
        arrays=[{tuple(k):v for k,v in a} for a in json.load(f).values()]
    stock,counts,orders=ledger(network,arrival_map(pipeline,W),arrays)
    if (out/'warmup_result.json').is_file():
        result=json.loads((out/'warmup_result.json').read_text(encoding='utf8'))
        assert result['on_time']==counts['bev']+counts['non_bev']
        return result,stock,terminal_pipeline(network,arrays[2],pipeline),orders
    log=(out/'warmup.log').read_text(encoding='utf8')
    best,bound,gap=re.findall(r'Best objective (\S+), best bound (\S+), gap (\S+)%',log)[-1]
    seconds=float(re.findall(r'Explored \d+ nodes .* in ([\d.]+) seconds',log)[-1])
    assert 'Optimal solution found' in log and float(gap)==0
    count=counts['bev']+counts['non_bev']
    assert abs(float(best)-count/network.demand_weight)<=1e-9 and abs(float(bound)-float(best))<=1e-9
    result=dict(status=2,status_name='OPTIMAL',objective=float(best),bound=float(bound),mip_gap=0,runtime=seconds,
                on_time=count,bev=counts['bev'],non_bev=counts['non_bev'],late=counts['late'],
                service_rate=count/network.demand_weight,material_balance_residual=0,certified=True,
                buffers=dict.fromkeys(BUFFER_NAMES,0),exact_budget_residual_usd=0,
                recovery='original solver log plus exact replay of completed warmup vector')
    return result,stock,terminal_pipeline(network,arrays[2],pipeline),orders


def preserve_attempt(out,name):
    previous=out/f'{name}.log'
    if previous.exists():
        index=1
        while (out/f'{name}_attempt{index}.log').exists():
            index+=1
        previous.rename(out/f'{name}_attempt{index}.log')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offsets',nargs='*',type=int,default=list(range(LENGTH)))
    args=parser.parse_args()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SHA
    tables=load_tables(SOURCE)
    source,_=compile_network(tables)
    protocol(source,tables)
    run=frozen_runs(manifest_bytes(FORMAL/'manifest.json'))[0]
    stock0,pipeline0=seed_stock(source),seed_pipeline(source)
    for offset in args.offsets:
        assert 0<=offset<LENGTH
        label=f'NB{offset:02d}'
        out=HERE/label
        if (out/'summary.json').is_file():
            continue
        out.mkdir(exist_ok=True)
        warm_net=horizon(source,W,offset,'W'+label,stock0)
        assert len(warm_net.groups)==5144 and warm_net.demand_weight==112000
        if (out/'warmup.json.gz').is_file():
            warm,stock,pipeline,orders=read_warmup(warm_net,pipeline0,out)
        else:
            preserve_attempt(out,'warmup')
            warm,stock,pipeline,orders,_=solve(warm_net,pipeline0,run,out/'warmup',False)
            save(out/'warmup_result.json',warm)
        for name in ('formal','formal_LP'):
            preserve_attempt(out,name)
        # All finished, warmup-specific stock remains physically in place but is
        # inert because the new VIN groups have disjoint identifiers.
        formal_net=horizon(source,LENGTH,0,'F'+label,{key:q for key,q in stock.items() if q})
        assert {g.id for g in warm_net.groups}.isdisjoint(g.id for g in formal_net.groups)
        assert formal_net.demand_weight==28000
        formal,_,_,_,arrays=solve(formal_net,pipeline,run,out/'formal',True)
        export_case(label,stock,pipeline,orders,warm,formal,arrays,formal_net)


if __name__=='__main__':
    main()
