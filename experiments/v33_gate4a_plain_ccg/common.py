"""Frozen input loading and the exact preparation-capital ceiling."""

import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = "d7918025268d3b5a9bb5b48484bd43e164a83c9e"
sys.path.insert(0, str(HERE.parent / "v33_gate36_recovery_objective"))
from run_gate36 import H, ALPHA, DELTA, STORAGE, SETTINGS, CELL, COST, TOL, Recovery, audit_prep, capital, identities, load_tables, prepare, stationary_capacities
from numerical_certification import solve_info
from run_gate2c import sha256, write_csv, write_json
from experiments.configs.audit_v33_formal_risk_protocol import CONFIG, Event, budget_grid, read_csv, subsets


def frozen_inputs(xlsb, bundle):
    root = CONFIG.parent
    for row in read_csv(root / "v33_formal_risk_sha256_manifest.csv"):
        path = ROOT / row["path"]
        assert path.stat().st_size == int(row["bytes"]) and sha256(path) == row["sha256"], row["path"]
    protocol = json.loads(CONFIG.read_bytes())
    status = json.loads((root / "v33_formal_risk_static_audit.json").read_bytes())
    assert status["READY_FOR_GATE4"] and status["FORMAL_RISK_PROTOCOL_FROZEN"]
    assert protocol["tail"]["baseline"] == "CALENDAR_REPEAT"
    assert protocol["budget"]["reference_profile"] == dict(H=H,alpha=str(ALPHA),delta=str(DELTA),storage=STORAGE)
    tables = load_tables(xlsb)
    base, states, meta = identities(tables,bundle,xlsb)
    op = Recovery(base,states)
    assert op.periods[-1]==97 and len(states)==91 and op.demand==28000
    _, rows = stationary_capacities(tables,Fraction(1))
    nominal = {(r["origin"],r["destination"]):Fraction(r["stationary_nominal_exact"]) for r in rows}
    core = [r for r in read_csv(root / "formal_event_catalog.csv") if r["scope"] == "CORE"]
    for row in core:
        for key in ("start","duration","recovery"):
            row[key] = int(row[key])
    events = {r["event_id"]: Event(r["event_id"],tuple(r["asset"].split("->")),r["asset_type"],r["start"],r["duration"],
              Fraction(r["availability"]),r["recovery"]).profile(op.periods) for r in core}
    scenarios = {}
    archived = read_csv(root / "formal_scenario_dedup_map.csv")
    for gamma in (1,2):
        _, mapping = subsets(core,gamma,op.nominal)
        expected = [r for r in archived if r["tail_protocol"]=="CALENDAR_REPEAT" and int(r["gamma"])==gamma]
        assert [{k:str(v) for k,v in r.items()} for r in mapping]==[{k:v for k,v in r.items() if k!="tail_protocol"} for r in expected]
        scenarios[gamma] = {r["combination"]:{k:v for atom in r["combination"].split("+") for k,v in events.get(atom,{}).items()}
                            for r in mapping if r["canonical_scenario"]==r["combination"]}
    assert [len(scenarios[g]) for g in (1,2)]==[11,51]
    meta.update(protocol_sha256=sha256(CONFIG),protocol_manifest_sha256=sha256(root/"v33_formal_risk_sha256_manifest.csv"),
                protocol_commit=BASELINE,tail="CALENDAR_REPEAT",solver_parameters=SETTINGS,
                algorithm="PLAIN_EXACT_CCG",manual_start=False,parallel_oracle=False)
    return op,nominal,protocol,scenarios,meta


def exact(model, expression, sense):
    model.setObjective(expression,sense)
    model.optimize()
    info=solve_info(model)
    info["exact"]=(model.Status==GRB.OPTIMAL and info["mip_gap"]==0 and
                   abs(info["objective"]-info["best_bound"])<=TOL and
                   max(info[k] for k in ("model_row_violation","model_bound_violation","integrality_error"))<=TOL)
    return info


def dimensions(model):
    return {"variables":model.NumVars,"constraints":model.NumConstrs,"nonzeros":model.NumNZs}


def bmax(env, op, nominal, protocol, out):
    with gp.Model("Gate4A_Bmax",env=env) as model:
        prep=prepare(model,op.base,op.states,H,nominal,ALPHA,DELTA,STORAGE)
        info=exact(model,prep[-1],GRB.MAXIMIZE)
        assert info["exact"],info
        ceiling=round(info["objective"])
        b={k:round(v.X) for k,v in prep[6].items()}
        residual,_,_=audit_prep(model,prep,H)
        assert ceiling==capital(op,b)
        info.update(**dimensions(model),bmax_cents=ceiling,prep_max_residual=residual)
        model.write(str(out/"bmax.lp.gz"))
        model.write(str(out/"bmax.mps.gz"))
    cfg=protocol["budget"]
    grid=budget_grid(ceiling,cfg,cfg["reference_profile"])
    write_csv(out,"formal_budget_grid.csv",[dict(budget_cents=v,budget_usd=v/100,reference_anchor=v==cfg["reference_anchor_cents"],
                                               certification_case=v in (0,ceiling//2,ceiling)) for v in grid])
    info.update(budget_grid_cents=grid,anchor_included=cfg["reference_anchor_cents"] in grid,
                preparation_profile=cfg["reference_profile"],buffer=[[n,p,q] for (n,p),q in b.items() if q])
    write_json(out,"gate4a_bmax.json",info)
    print("BMAX",ceiling,grid,flush=True)
    return ceiling
