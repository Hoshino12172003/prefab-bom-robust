from itertools import product
from contextlib import ExitStack
from math import isfinite
from pathlib import Path
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from prefab_bom_robust.uncertainty import _vertex_count, budget_extreme_points, ExactEnumerationUnavailable
from .model import TOL, block, first_stage, values
from .audit import audit
from prefab_bom_robust.uncertainty import validate_point


def vertices(d, cap=256):
    groups = (("eta",d.S,"Gamma2"), ("xi",d.V,"Gamma3"), ("theta",d.O,"GammaO"))
    count = 1
    for _,nodes,budget in groups:
        count *= _vertex_count(nodes, min(len(nodes),d.val(budget)))
    if count > cap:
        raise ExactEnumerationUnavailable(f"{count} exceeds {cap}; no exact separation available")
    layers = [budget_extreme_points(nodes,min(len(nodes),d.val(budget))) for _,nodes,budget in groups]
    return [dict(zip(("eta","xi","theta"),p)) for p in product(*layers)]


def run_model(d, risks, fixed=None, phase=False, logfile=None, time_limit=30, cuts=False):
    d.validate()
    for risk in risks:
        for layer,nodes,budget in (("eta",d.S,"Gamma2"),("xi",d.V,"Gamma3"),("theta",d.O,"GammaO")):
            validate_point(risk[layer],nodes,d.val(budget))
    start = perf_counter()
    try:
        with gp.Model("V21") as m, ExitStack() as stack:
            m.Params.OutputFlag = 0
            m.Params.LogToConsole = 0
            if logfile:
                m.Params.OutputFlag = 1
            stream = stack.enter_context(Path(logfile).open("w",encoding="utf-8")) if logfile else None
            def log_callback(model,where):
                if where == GRB.Callback.MESSAGE:
                    stream.write(model.cbGet(GRB.Callback.MSG_STRING))
            m.Params.DualReductions = 0
            m.Params.Threads = 1
            m.Params.Seed = 20261107
            m.Params.TimeLimit = time_limit
            m.Params.MIPGap = m.Params.MIPGapAbs = 0
            m.Params.FeasibilityTol = m.Params.OptimalityTol = m.Params.IntFeasTol = 1e-9
            z, pre = first_stage(m,d,fixed)
            if phase:
                # Fixed first-stage binary decisions are constants in this LP.
                for var in z["y"].values():
                    var.VType = GRB.CONTINUOUS
                modes = [("phase",risks[0])]
            else:
                modes = [("nominal",d.zero()), *(("service",w) for w in risks)]
            blocks = [block(m,d,z,w,mode,f"scenario{i}") for i,(mode,w) in enumerate(modes)]
            cut_count = 0
            if cuts:
                from .cuts import add_cuts
                cut_count = add_cuts(m,d,z,vertices(d))
            m.setObjective(gp.quicksum(blocks[0][2].values()) if phase else pre+blocks[0][4])
            m.optimize(log_callback if stream else None)
            status = {2:"OPTIMAL",3:"INFEASIBLE",4:"INF_OR_UNBOUNDED",5:"UNBOUNDED",
                      9:"TIME_LIMIT",12:"NUMERIC"}.get(m.Status,f"STATUS_{m.Status}")
            result = {"status":status,"certified":False,"wall_seconds":perf_counter()-start,
                      "solver_seconds":m.Runtime,"peak_gb":m.MaxMemUsed,"cut_count":cut_count,
                      "lb":None,"ub":None,"gap":None,"flows":[]}
            if m.IsMIP and isfinite(m.ObjBound):
                result["lb"] = m.ObjBound
            if m.SolCount:
                result.update(objective=m.ObjVal, plan=values(z),
                              gurobi_residual=max(m.ConstrVio,m.BoundVio,m.IntVio if m.IsMIP else 0))
            if status == "OPTIMAL":
                result["lb"] = m.ObjBound if m.IsMIP else m.ObjVal
                result["gap"] = m.MIPGap if m.IsMIP else 0
                for (mode,w),(v,u,sigma,cash,op) in zip(modes,blocks):
                    flow = values(v)
                    flow["u"] = {(p,):var.X for p,var in u.items()}
                    flow["sigma"] = {(h,):var.X for h,var in sigma.items()}
                    residual = audit(d,result["plan"],w,flow,mode)
                    result["flows"].append({"mode":mode,"risk":w,"values":flow,
                                            "cash":cash.getValue(),"economic":op.getValue(),
                                            "audit":residual})
                result["residual"] = max([result["gurobi_residual"],
                                          *(max(f["audit"].values()) for f in result["flows"])])
                result["certified"] = result["residual"] <= TOL and abs(m.ObjVal-result["lb"])<=TOL
                if not result["certified"]:
                    result["status"] = "AUDIT_FAILED"
                if phase:
                    result["capacity_duals"] = {c.ConstrName:c.Pi for c in m.getConstrs()
                                                if any(tag in c.ConstrName for tag in ("_T3_","_T2_","_O_"))}
            result["wall_seconds"] = perf_counter()-start
            return result
    except gp.GurobiError as exc:
        return {"status":"LICENSE_ERROR" if exc.errno==10009 else "GUROBI_ERROR",
                "certified":False,"message":str(exc),"wall_seconds":perf_counter()-start}


def phase1(d,plan,risk,**kwargs):
    return run_model(d,[risk],fixed=plan,phase=True,**kwargs)


def separate(d,plan,all_risks,directory=None):
    worst = -1
    witness = None
    records = []
    for i,risk in enumerate(all_risks):
        log = directory/f"SP_{i}.log" if directory else None
        result = phase1(d,plan,risk,logfile=log)
        records.append(result)
        if not result["certified"]:
            return {"certified":False,"status":result["status"],"records":records}
        if result["objective"] > worst:
            worst, witness = result["objective"], risk
    return {"certified":True,"worst":worst,"risk":witness,"records":records}


def direct(d,cap=256,directory=None):
    start = perf_counter()
    risks = vertices(d,cap)
    result = run_model(d,risks,logfile=directory/"MP.log" if directory else None)
    if result["certified"]:
        sep = separate(d,result["plan"],risks,directory)
        result["separation"] = sep
        result["certified"] = sep["certified"] and sep["worst"] <= TOL
        if result["certified"]:
            result["ub"] = result["objective"]
        else:
            result["status"] = sep.get("status","SEPARATION_VIOLATION")
    result["wall_seconds"] = perf_counter()-start
    return result


def ccg(d,cap=256,directory=None,cuts=False,rank=False,max_iterations=100):
    start = perf_counter()
    risks = vertices(d,cap)
    active = [d.zero()]
    history = []
    for iteration in range(max_iterations):
        folder = directory/str(iteration) if directory else None
        if folder:
            folder.mkdir(parents=True,exist_ok=True)
        master = run_model(d,active,logfile=folder/"MP.log" if folder else None,cuts=cuts)
        record = {"iteration":iteration+1,"master":master}
        history.append(record)
        if not master["certified"]:
            master.update(history=history[:-1],total_seconds=perf_counter()-start)
            return master
        # Order only. Every extreme point remains in the certified search.
        if rank:
            guide = phase1(d,master["plan"],d.zero(),logfile=folder/"guide.log" if folder else None)
            record["guide"] = guide
            if not guide["certified"]:
                return {"status":guide["status"],"certified":False,"history":history,"ub":None}
            search = sorted(risks,key=lambda w: score(d,w,guide["capacity_duals"]),reverse=True)
        else:
            search = risks
        sep = separate(d,master["plan"],search,folder)
        record["separation"] = sep
        if not sep["certified"]:
            return {"status":sep["status"],"certified":False,"history":history,"ub":None}
        if sep["worst"] <= TOL:
            return {"status":"OPTIMAL","certified":True,"objective":master["objective"],
                    "lb":master["lb"],"ub":master["objective"],"gap":master["gap"],
                    "plan":master["plan"],"worst":sep["worst"],"history":history,
                    "iterations":iteration+1,"total_seconds":perf_counter()-start}
        if sep["risk"] in active:
            return {"status":"DUPLICATE_VIOLATION","certified":False,"history":history,"ub":None}
        active.append(sep["risk"])
    return {"status":"ITERATION_LIMIT","certified":False,"history":history,"ub":None}


def score(d,w,duals):
    dual_score = sum(abs(price)*(
        d.val("C",k,t)*d.val("delta",k)*w["xi"][d.node[k]]
        if name==f"scenario0_T3_{k}_{t}" else 0)
        for name,price in duals.items() for k in d.K for t in d.periods)
    return dual_score + sum(sum(d.val("A2",j,p)*d.val("b",k,s,j) for p in d.M for s,j in d.E)
               *sum(d.val("C",k,t) for t in d.periods)*d.val("delta",k)*w["xi"][d.node[k]]
               for k in d.K) + sum(w["eta"].values()) + sum(w["theta"].values())
