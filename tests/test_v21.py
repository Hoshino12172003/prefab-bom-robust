from copy import deepcopy
from itertools import product
from math import nextafter
import random
import pytest
import gurobipy as gp
from gurobipy import GRB

from prefab_v21.data import zero_plan
from prefab_v21.examples import micro
from prefab_v21.solvers import ccg, direct, phase1, run_model, vertices
from prefab_v21.audit import audit
from prefab_bom_robust.uncertainty import ExactEnumerationUnavailable, budget_extreme_points
from examples.independent_check import vertices as edge_vertices


def insured(d):
    z=zero_plan(d)
    z["y"]["k",]=1
    z["r"]["k",]=len(d.M)
    return z


@pytest.mark.parametrize("change",["bom","lead","lot","overorder","late","storage","arc","nan"])
def test_G0_rejects_inconsistent_data(change):
    d=micro()
    if change=="bom": d.p["A1"]["B","HV"]=1
    if change=="lead": d.leads["g"]["k","s1"]=0
    if change=="lot": d.lots.append(deepcopy(d.lots[0]))
    if change=="overorder": d.lots.append({"id":"pf","kind":"PF","index":("HV",2),"amount":2})
    if change=="late": d.lots.append({"id":"pf","kind":"PF","index":("HV",5),"amount":1})
    if change=="storage": d.enable_storage_capacity=True
    if change=="arc": d.NB.add(("k","bad"))
    if change=="nan": d.p["cI"]["B","a"]=float("nan")
    with pytest.raises(ValueError): d.validate()


def test_G1_actual_nominal_full_flow():
    d=micro()
    r=run_model(d,[],fixed=zero_plan(d))
    assert r["certified"] and r["status"]=="OPTIMAL"
    v=r["flows"][0]["values"]
    assert sum(v["ell"].values())==pytest.approx(1)
    assert v["q"]["s0","B",2]==pytest.approx(1)
    assert sum(v["g"].values())==pytest.approx(0)
    assert r["flows"][0]["economic"] > r["flows"][0]["cash"]


@pytest.mark.parametrize("case,expected",[
    ("backup_only_arc",0),("no_supply",1),("late_backup",1),
    ("external_down",2),("late_wip",2),("late_customer",3),
    ("upstream_pipeline",0),("component_pipeline",0),("wip_pipeline",0),("customer_pipeline",0),
])
def test_G2_delays_external_and_pipeline(case,expected):
    d=micro(three=case in {"external_down","late_wip","late_customer"})
    z=insured(d); w=d.zero(); w["xi"]["v"]=1
    if case=="no_supply": z=zero_plan(d)
    if case=="late_backup": d.leads["g"]["k","s1"]=2
    if case=="external_down": w["theta"]["o"]=1; d.p["GammaO"][()]=1
    if case=="late_wip": d.leads["h"]={key:2 for key in d.EO}
    if case=="late_customer": d.leads["e"]={key:2 for key in d.leads["e"]}
    kinds={"upstream_pipeline":("P3",("k","s0",2)),
           "component_pipeline":("P2",("B","a",3)),
           "wip_pipeline":("PW",("HV",3)),
           "customer_pipeline":("PF",("HV",4))}
    if case in kinds:
        kind,index=kinds[case]
        d.lots.append({"id":"pipeline","kind":kind,"index":index,"amount":1})
        z=zero_plan(d)
        if case=="wip_pipeline":
            d.lots.append({"id":"initial_B","kind":"I","index":("B","a"),"amount":1})
    r=phase1(d,z,w)
    assert r["certified"]
    assert r["objective"]==pytest.approx(expected,abs=1e-7)


def test_G2_zero_actions_complete_recourse_and_cash_not_holding():
    d=micro()
    d.p["Eop"][()]=0
    for key in d.costs["I"]: d.costs["I"][key]=100
    d.lots.append({"id":"pipeline","kind":"P2","index":("B","o",1),"amount":20})
    r=phase1(d,zero_plan(d),d.zero())
    assert r["certified"] and r["objective"]==pytest.approx(1)
    assert r["flows"][0]["cash"]==0
    assert r["flows"][0]["economic"]>0


def test_G3_independent_edge_vertices_all_layers_and_cap():
    for n in range(5):
        nodes=tuple(map(str,range(n)))
        for gamma in sorted({0,n,min(n,0.5),min(n,1),max(0,n-0.5),min(n,nextafter(1.,0.))}):
            assert {tuple(v.values()) for v in budget_extreme_points(nodes,gamma)} == {
                tuple(v.values()) for v in edge_vertices(nodes,gamma)}
    d=micro(three=True)
    assert len(vertices(d))==12
    assert d.zero() in vertices(d)
    with pytest.raises(ExactEnumerationUnavailable): vertices(d,cap=1)


def test_G3_vertices_against_independent_gurobi_linear_objectives():
    rng=random.Random(20261107)
    for n in range(1,5):
        nodes=tuple(map(str,range(n)))
        for gamma in (0,0.5,1,n-0.5,n):
            for _ in range(3):
                coefficients=[rng.uniform(-2,2) for _ in nodes]
                with gp.Model() as m:
                    m.Params.OutputFlag=0
                    x=m.addVars(n,ub=1)
                    m.addConstr(gp.quicksum(x.values())<=gamma)
                    m.setObjective(gp.quicksum(c*x[i] for i,c in enumerate(coefficients)),GRB.MAXIMIZE)
                    m.optimize()
                    assert m.Status==GRB.OPTIMAL
                    exact=max(sum(coefficients[i]*point[key] for i,key in enumerate(nodes))
                              for point in budget_extreme_points(nodes,gamma))
                    assert exact==pytest.approx(m.ObjVal,abs=1e-7)


def test_G4_G5_three_families_two_operations_shared_resource():
    d=micro(three=True)
    a,b=direct(d),ccg(d)
    assert a["certified"] and b["certified"]
    assert a["objective"]==pytest.approx(b["objective"],abs=1e-7)
    assert a["lb"]==pytest.approx(a["ub"],abs=1e-7)
    assert b["lb"]==pytest.approx(b["ub"],abs=1e-7)
    for result in (a,b):
        for w in vertices(d):
            sp=phase1(d,result["plan"],w)
            assert sp["certified"] and sp["objective"]<=1e-7
    mutated=deepcopy(a["flows"][0]["values"])
    mutated["ell"]["HV",1]=1
    assert max(audit(d,a["plan"],d.zero(),mutated,"nominal").values()) >= 1


def test_independent_named_plan_witness_cost_and_total_reserve():
    d=micro()
    z=insured(d)
    w=d.zero(); w["xi"]["v"]=1
    r=phase1(d,z,w)
    assert r["certified"] and r["objective"]<=1e-7
    assert sum(r["flows"][0]["values"]["g"].values())==pytest.approx(1)
    z["r"]["k",]=0.5
    assert phase1(d,z,w)["objective"]==pytest.approx(0.5)


def test_infeasible_time_limit_license_status(monkeypatch):
    d=micro()
    d.p["X"]={key:0 for key in d.p["X"]}
    d.p["Rmax"]["k",]=0
    assert direct(d)["status"]=="INFEASIBLE"
    assert ccg(d)["status"]=="INFEASIBLE"
    d=micro()
    limited=run_model(d,[],time_limit=0)
    assert limited["status"]=="TIME_LIMIT" and not limited["certified"]
    def fail(*args,**kwargs):
        raise gp.GurobiError(10009,"license unavailable")
    monkeypatch.setattr(gp,"Model",fail)
    result=run_model(d,[])
    assert result["status"]=="LICENSE_ERROR" and not result["certified"]


def test_joint_families_cannot_splice_resource():
    d=micro(three=True); z=insured(d); z["r"]["k",]=1
    w=d.zero(); w["xi"]["v"]=1
    assert phase1(d,z,w)["objective"]==pytest.approx(2)
    for h in d.M:
        isolated=deepcopy(d)
        isolated.p["alpha"]={(p,):int(p==h) for p in d.M}
        assert phase1(isolated,z,w)["objective"]==pytest.approx(0)


def test_gate_failure_prevents_exact_status(monkeypatch):
    import prefab_v21.solvers as s
    monkeypatch.setattr(s,"phase1",lambda *a,**kw:{"certified":False,"status":"TIME_LIMIT"})
    for method in (s.direct,s.ccg):
        result=method(micro())
        assert not result["certified"] and result["status"]=="TIME_LIMIT"
        assert result.get("ub") is None


def test_G6_cover_cut_independent_feasible_grid_and_late_counterexample():
    from prefab_v21.cuts import certificates, expression, reachable_expression
    d=micro()
    certs=list(certificates(d))
    assert len(certs)==1
    for x,r in product((0,0.5,1),repeat=2):
        z=insured(d); z["x"]["B","a"]=x; z["r"]["k",]=r
        feasible=True
        for w in vertices(d):
            sp=phase1(d,z,w)
            assert sp["certified"]
            if sp["objective"]>1e-7: feasible=False
        if feasible:
            assert all(expression(d,z,w,c)+1e-7>=c["lhs"] for c in certs for w in vertices(d))
            assert all(reachable_expression(d,z,w,c)+1e-7>=c["lhs"] for c in certs for w in vertices(d))
    w=d.zero(); w["xi"]["v"]=1
    assert expression(d,zero_plan(d),w,certs[0]) < certs[0]["lhs"]
    d.leads["g"]["k","s1"]=2
    z=insured(d)
    assert expression(d,z,w,certs[0]) >= certs[0]["lhs"]
    assert phase1(d,z,w)["objective"]==pytest.approx(1)
    assert reachable_expression(d,z,w,certs[0])+1e-7 < certs[0]["lhs"]
    d.p["b"]["k","s1","B"]=0
    assert list(certificates(d))==[]


def test_G2_shared_T3_risk_hits_two_complementary_resource_pools():
    d=micro()
    d.K=("k","k2"); d.node["k2"]="v"
    d.N.add(("k2","s0")); d.NB.add(("k2","s1"))
    for group in ("C","G"):
        d.p[group].update({("k2",t):d.val(group,"k",t) for t in d.periods})
    for group in ("delta","Rmax","f","cR"):
        d.p[group]["k2",]=d.val(group,"k")
    for s in d.S: d.p["b"]["k2",s,"B"]=1
    d.leads["t"]["k2","s0"]=1; d.leads["g"]["k2","s1"]=1
    d.costs["g"]["k2","s1"]=0.3
    d.costs["R"]["k2","s0"]=d.costs["R"]["k2","s1"]=0.01
    d.validate()
    z=insured(d); w=d.zero(); w["xi"]["v"]=1
    assert phase1(d,z,w)["objective"]==pytest.approx(1)
    z["y"]["k2",]=1; z["r"]["k2",]=1
    result=phase1(d,z,w)
    assert result["certified"] and result["objective"]<=1e-7
