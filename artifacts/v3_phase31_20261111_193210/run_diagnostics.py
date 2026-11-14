"""Historical-state full-network diagnostics and exact candidate-set counts."""
import csv
import json
import os
import sys
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
from pathlib import Path

import gurobipy as gp
import numpy as np
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(ROOT/"src"))
from prefab_v25.data import CELL,NOMINAL,PACK,PROD,PRODUCTION_ARC,TRANSPORT_ARC,receipts
from prefab_v25.source import load_tables
from prefab_v3.base import Weights,add_block,source_base
from prefab_v3.interface import add_stage_one
from prefab_v3.robust import Episode,UncertaintySet,on_time,protection_inventory

PRIOR = ROOT/"artifacts/v3_phase30_20261111_104032"
SOURCE = Path("external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip")
PERIODS = tuple(range(61,75))
SEVERITIES = (F(1,4),F(1,2),F(3,4))
DURATIONS = (1,3,5)
BUDGETS = (215,644,1073)
COSTS = (F(1),F(27,19),F(297,190))
LABEL = "HISTORICAL_STRESSED_STATE_DIAGNOSTIC"
NR = (None,None,None)


def read(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write(name,rows):
    rows = list(rows)
    with (HERE/name).open("w",encoding="utf-8-sig",newline="") as f:
        writer = csv.DictWriter(f,list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def frozen():
    entries = read(PRIOR/"sha256_manifest.csv")
    assert all(digest(ROOT/r["path"])==r["sha256"] for r in entries)
    status = json.loads((PRIOR/"audit.json").read_text(encoding="utf-8"))
    assert status["status"]=="PASS_FULL_BASE_WITH_DOCUMENTED_APPLICATION_DIFFERENCES"
    assert digest(SOURCE)==next(h for p,h in status["source_hashes"].items() if p.endswith(".zip"))
    return len(entries)


def candidate(gamma=6, recovery=0, concurrency=2, durations=DURATIONS):
    return UncertaintySet(PERIODS,durations,SEVERITIES,gamma,concurrency,recovery)


def size_rows(base,opening):
    arc_caps = {a.key:a.capacity for a in base.network.arcs}
    rows = []
    for gamma,recovery,concurrency,durations in [
            *((g,r,2,DURATIONS) for g,r in product((0,3,6,9),(0,2))),
            (6,0,1,DURATIONS),(6,0,3,DURATIONS),(6,0,2,(1,)),(6,0,2,(1,2,3,4,5))]:
        u = candidate(gamma,recovery,concurrency,durations)
        options = {0:[None]}
        for t,d in u.intervals():
            mask = ((1<<d)-1)<<(t-PERIODS[0])
            options[mask]=[Episode(t,d,s) for s in SEVERITIES]
        expansions = {m:[other for other in options if other!=m and m&other==m]
                      for m in options}
        patterns = list(u.feasible_masks())
        maximal = 0
        rhs_signatures = set()
        cache = {}
        for i in range(3):
            for choices in options.values():
                for e in choices:
                    factors = dict(zip(PERIODS,u.factors(e)))
                    if i==0:
                        signature = tuple(int(q*factors[t]) for (n,p,t),q in sorted(opening.items())
                                          if n==PROD and p in CELL)
                    else:
                        arc = (PRODUCTION_ARC,TRANSPORT_ARC)[i-1]
                        signature = tuple(int(arc_caps[arc][t]*factors[t]) for t in PERIODS)
                    cache[i,e]=signature
        trajectories = 0
        for masks in patterns:
            stronger = any(u.feasible_mask_tuple((*masks[:i],m,*masks[i+1:]))
                           for i,old in enumerate(masks) for m in expansions[old])
            maximal += not stronger
            for selected in product(*(options[m] for m in masks)):
                trajectories += 1
                rhs_signatures.add(tuple(cache[i,e] for i,e in enumerate(selected)))
        # Positive severity and a strictly increasing recovery tail uniquely identify each episode.
        assert trajectories==sum(len(SEVERITIES)**sum(bool(m) for m in masks) for masks in patterns)
        rows.append(dict(gamma_resource_days=gamma,concurrency=concurrency,allowed_durations="|".join(map(str,durations)),
            recovery_steps=recovery,z_patterns=len(patterns),explicit_trajectories=trajectories,
            unique_factor_trajectories=trajectories,historical_unique_effective_rhs=len(rhs_signatures),
            maximal_z_patterns_at_max_severity=maximal,nonredundancy_basis="support inclusion; not exact service-envelope size"))
    return rows


def solved(model,x,blocks,z,base):
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"uncertified {model.ModelName}: {model.Status}")
    raw=np.asarray(model.getAttr("X"))
    rounded=np.rint(raw)
    residual=max(model.ConstrVio,model.BoundVio,model.IntVio,float(np.max(np.abs(raw-rounded))))
    assert residual<=1e-7
    assert np.all(rounded>=np.asarray(model.getAttr("LB"))) and np.all(rounded<=np.asarray(model.getAttr("UB")))
    lhs=model.getA()@rounded
    rhs=np.asarray(model.getAttr("RHS"))
    sense=np.asarray(model.getAttr("Sense"))
    assert np.all(lhs[sense=="<"]<=rhs[sense=="<"])
    assert np.all(lhs[sense==">"]>=rhs[sense==">"])
    assert np.all(lhs[sense=="="]==rhs[sense=="="])
    service = {name:sum(int(rounded[b.outflow[g.id,t].index]) for g in base.network.groups
                     for t in PERIODS if t<=g.representative.due) for name,b in blocks.items()}
    portfolio = tuple(int(rounded[v.index]) for v in x)
    q = min(service.values())
    assert q==round(z.X) and abs(model.ObjBound-q)<=1e-7 and abs(model.ObjVal-q)<=1e-7 and model.MIPGap==0
    return dict(Q=q,bound=int(round(model.ObjBound)),x_C=portfolio[0],x_T=portfolio[1],x_O=portfolio[2],
        normalized_spend=str(sum(a*b for a,b in zip(COSTS,portfolio))),scenario_service=json.dumps(service),
        status="OPTIMAL",runtime_s=model.Runtime,gap=model.MIPGap,max_solver_residual=residual,
        exact_matrix_residual=0,variables=model.NumVars,integers=model.NumIntVars,constraints=model.NumConstrs)


def solve(env,base,opening,u,k,scenarios,exclude=None,fixed=None):
    name = f"K{k}_"+"_".join(scenarios)+(f"_NO_{exclude}" if exclude is not None else "_OPEN")
    if fixed is not None:
        name += "_FIXED_"+"_".join(map(str,fixed))
    log = HERE/"logs"/f"{name}.log"
    log.write_text("",encoding="utf-8")
    with gp.Model(name,env=env) as model:
        model.Params.LogToConsole=0
        model.Params.LogFile=os.path.relpath(log)
        model.Params.Threads=4
        model.Params.Seed=20261110
        model.Params.TimeLimit=60
        model.Params.MIPGap=model.Params.MIPGapAbs=0
        model.Params.OptimalityTol=model.Params.FeasibilityTol=model.Params.IntFeasTol=1e-9
        budget=k*COSTS[1]
        x=add_stage_one(model,COSTS,budget)
        if exclude is not None:
            x[exclude].UB=0
        if fixed is not None:
            for variable,value in zip(x,fixed):
                variable.LB=variable.UB=value
        z=model.addVar(vtype=GRB.INTEGER,ub=28000,name="Q")
        blocks={}
        for sid,episodes in scenarios.items():
            arrivals,factors=u.attenuation(episodes,opening)
            b=add_block(model,base,sid,Weights(0,0,0,0,0),reschedule=True,fixed_receipts=arrivals,
                        protection=protection_inventory(x),arc_factors=factors)
            blocks[sid]=b
            model.addConstr(z<=on_time(b,base))
        model.setObjective(z,GRB.MAXIMIZE)
        result=solved(model,x,blocks,z,base)
        assert F(result["normalized_spend"])<=budget
        return dict(scope=LABEL,case=name,scenario_ids="|".join(scenarios),T1_pack_budget_equivalents=k,
                    normalized_budget=str(budget),excluded_position=("" if exclude is None else ("x_C","x_T","x_O")[exclude]),
                    log=log.relative_to(HERE).as_posix(),**result)


def main():
    hashes=frozen()
    tables=load_tables(SOURCE)
    base,audit=source_base(tables)
    assert base.network.demand_weight==28000
    opening=receipts(base.network,NOMINAL)
    write("uncertainty_set_size_audit.csv",size_rows(base,opening))
    write("source_L1_exposure.csv",[
        dict(period=t,**{item:opening.get((PROD,item,t),0) for item in CELL}) for t in PERIODS])
    shock=Episode(64,3,F(1,2))
    scenarios={"NR":NR,"L1":(shock,None,None),"L2":(None,shock,None),"L3":(None,None,shock),
               "L1_L3":(Episode(66,1,F(1,2)),None,shock)}
    (HERE/"logs").mkdir(exist_ok=True)
    u=candidate()
    rows=[]
    with gp.Env() as env:
        env.setParam("LogToConsole",0)
        for k in BUDGETS:
            for sid,episodes in scenarios.items():
                result=solve(env,base,opening,u,k,{sid:episodes})
                q=result["Q"]
                q_nr=q if sid=="NR" else nr
                if sid=="NR":
                    nr=q
                assert q<=q_nr
                rows.append(dict(**result,Q_NR=q_nr,risk_loss=q_nr-q,ablation_loss=0))
                for excluded in range(3):
                    result=solve(env,base,opening,u,k,{sid:episodes},excluded)
                    assert result["Q"]<=q
                    rows.append(dict(**result,Q_NR=q_nr,risk_loss=q_nr-result["Q"],ablation_loss=q-result["Q"]))
                write("full_model_buffer_ablation.csv",rows)
                print(k,sid,q,flush=True)
        sample = solve(env,base,opening,u,BUDGETS[1],{s:scenarios[s] for s in ("NR","L1","L3")})
    upper=min(r["Q"] for r in rows if r["T1_pack_budget_equivalents"]==BUDGETS[1]
              and not r["excluded_position"] and r["scenario_ids"] in ("NR","L1","L3"))
    assert sample["Q"]<=upper
    write("selected_scenario_de_validation.csv",[dict(**sample,independent_single_scenario_upper=upper)])
    assert frozen()==hashes
    (HERE/"diagnostic_run.json").write_text(json.dumps(dict(optimizer_calls=len(rows)+1,
        source_vins=28000,source_products=audit["sheet_rows"]["products"],verified_phase30_entries=hashes,
        source_xlsb_sha256=audit["source_sha256"],source_zip_sha256=digest(SOURCE),
        budgets=list(BUDGETS),costs=list(map(str,COSTS)),diagnostic_scenarios={s:[
            (e.start,e.duration,str(e.severity)) if e else None for e in es] for s,es in scenarios.items()},
        gurobi_version=gp.gurobi.version()),indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
