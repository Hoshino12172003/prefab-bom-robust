from copy import deepcopy
from itertools import product
import random
import pytest

from prefab_v21 import solvers as old
from prefab_v21.examples import micro
from prefab_v22 import solvers as new
from prefab_v22.audit import audit, mapped_data
from prefab_v22.data import zero_plan
from prefab_v22.examples import extend, no_value, time_bottleneck, flexibility

TOL = 1e-7


def fixed(d, pre=0):
    z=zero_plan(d)
    z["y"]["k",]=1
    z["r"]["k",]=len(d.M)
    z["p"]["HV",]=pre
    return z


@pytest.mark.parametrize("three", [False,True])
def test_P01_P14_zero_preassembly_regression(three):
    base=micro(three)
    d=extend(base)
    zeros={(m,):0 for m in d.M}
    assert new.vertices(d)==old.vertices(base)
    for old_method,new_method in ((old.direct,new.direct),(old.ccg,new.ccg)):
        a=old_method(base)
        b=new_method(d,fixed_pre=zeros)
        assert a["certified"] and b["certified"]
        for key in ("objective","lb","ub","gap"):
            assert a[key]==pytest.approx(b[key],abs=TOL)
        # Compare actual nominal per-period flows in addition to bounds and residuals.
        av=a["flows"][0] if old_method is old.direct else a["history"][-1]["master"]["flows"][0]
        bv=b["flows"][0] if new_method is new.direct else b["history"][-1]["master"]["flows"][0]
        for group in av["values"]:
            assert av["values"][group]==pytest.approx(bv["values"][group],abs=TOL)
        assert audit(d,b["plan"],bv["risk"],bv["values"],"nominal")==pytest.approx(
            {key:0 for key in audit(d,b["plan"],bv["risk"],bv["values"],"nominal")},abs=TOL)


def test_P02_P09_material_and_WIP_mapping_each_vertex():
    d=time_bottleneck()
    z=fixed(d,1)
    replay=mapped_data(d,z)
    assert replay.stock("I","A","a")==pytest.approx(0)
    assert replay.stock("Wa","HV")==pytest.approx(1)
    for w in new.vertices(d):
        result=new.phase1(d,z,w)
        assert result["certified"] and result["objective"]<=TOL
        assert result["initial_states"]["Ipre"]["A","a"]==pytest.approx(0)
        assert result["initial_states"]["W0post"]["HV",]==pytest.approx(1)
        flow=result["flows"][0]["values"]
        assert sum(flow["a"].values())==pytest.approx(0)
        assert sum(flow["b"].values())==pytest.approx(1)
        corrupted=deepcopy(flow)
        corrupted["I"]["A","a",1]+=1
        assert max(audit(d,z,w,corrupted,"phase").values())>=1


@pytest.mark.parametrize("restriction",["material","capacity","space","order"])
def test_P03_P04_P05_P06_preassembly_bounds(restriction):
    d=time_bottleneck()
    z=fixed(d,1)
    if restriction=="material":
        d.base.lots=[]
        # Post-risk pipeline is excluded from preassembly even though it arrives in period 1.
        d.base.lots=[{"id":"arrives_later","kind":"P2","index":("A","a",1),"amount":1}]
    if restriction=="capacity": d.P_pre=0.5
    if restriction=="space": d.Wcap_pre=0.5
    if restriction=="order":
        d.base.lots.append({"id":"existing_wip","kind":"Wa","index":("HV",),"amount":0.5})
        d.Wcap_pre=2
    result=new.phase1(d,z,d.zero())
    assert result["status"]=="INFEASIBLE" and not result["certified"]


@pytest.mark.parametrize("failure",["stage2_material","stage2_capacity","customer_lead"])
def test_P07_P08_preassembly_is_not_finished_delivery(failure):
    d=time_bottleneck()
    if failure=="stage2_material":
        d.base.p["K"]={idx:0 for idx in d.base.p["K"]}
    if failure=="stage2_capacity":
        d.base.p["P2"]={idx:0 for idx in d.base.p["P2"]}
    if failure=="customer_lead": d.base.leads["e"]["HV",]=2
    result=new.phase1(d,fixed(d,1),d.zero())
    assert result["certified"] and result["objective"]==pytest.approx(1)


def test_P10_P11_shared_decision_and_cost_counting():
    d=time_bottleneck()
    # Force purchase of A before preassembly, so procurement timing is exercised.
    d.base.lots=[]
    d.base.p["X"]["A","a"]=1
    d.base.p["cI"]["A","a"]=2
    result=new.direct(d)
    assert result["certified"]
    assert result["plan"]["p"]["HV",]==pytest.approx(1)
    assert result["plan"]["x"]["A","a"]==pytest.approx(1)
    breakdown=result["cost_breakdown"]
    assert breakdown["preassembly"]==pytest.approx(0.25)
    assert breakdown["original_pre"]==pytest.approx(3.5)
    assert breakdown["objective"]==pytest.approx(5.27)
    assert all(block["audit"]["pre_material"]<=TOL for block in result["flows"])
    assert all(block["audit"]["Wa_balance"]<=TOL for block in result["flows"])


@pytest.mark.parametrize("factory,expected,pre",[
    (no_value,3.12,0), (time_bottleneck,3.27,1), (flexibility,5.89,1)])
def test_P12_P13_P15_analytic_instances(factory,expected,pre):
    d=factory()
    a,b=new.direct(d),new.ccg(d)
    assert a["certified"] and b["certified"]
    for result in (a,b):
        assert result["objective"]==pytest.approx(expected,abs=TOL)
        assert result["plan"]["p"]["HV",]==pytest.approx(pre,abs=TOL)
        assert result["ub"]==pytest.approx(result["lb"],abs=TOL)
    baseline=old.direct(d.base)
    if baseline["certified"]:
        assert a["objective"]<=baseline["objective"]+TOL
    else:
        assert baseline["status"]=="INFEASIBLE"


def test_P12_zero_capacity_matches_old_optimum():
    d=extend(micro(),capacity=0,cost=0)
    result=new.direct(d)
    assert result["certified"]
    assert result["plan"]["p"]["HV",]==pytest.approx(0)
    assert result["objective"]==pytest.approx(3.12)


def test_P13_common_component_lock_in():
    d=flexibility()
    good=fixed(d,1)
    bad=fixed(d,0)
    bad["p"]["MV",]=1
    w=d.zero()
    a=new.phase1(d,good,w)
    b=new.phase1(d,bad,w)
    assert a["certified"] and a["objective"]<=TOL
    assert b["certified"] and b["objective"]==pytest.approx(0.5)
    both=fixed(d,1)
    both["p"]["MV",]=1
    assert new.phase1(d,both,w)["status"]=="INFEASIBLE"
    optimum=new.direct(d)
    assert optimum["cost_breakdown"]==pytest.approx(
        {"original_pre":2.5,"preassembly":0.25,"cash":3.1,"holding":0.04,"objective":5.89},abs=TOL)


def test_P16_seeded_legal_properties():
    rng=random.Random(20261107)
    for _ in range(5):
        d=extend(micro(),capacity=rng.choice((0,0.5,1)),cost=rng.uniform(0,1))
        d.base.p["Gamma3"][()]=rng.choice((0,0.5,1))
        d.base.p["GammaO"][()]=rng.choice((0,0.5,1))
        d.validate()
        a,b=new.direct(d),new.ccg(d)
        assert a["certified"] and b["certified"]
        assert a["objective"]==pytest.approx(b["objective"],abs=TOL)
        assert a["objective"]<=old.direct(d.base)["objective"]+TOL


def test_invalid_inputs_preserve_zero_preassembly_feasibility():
    for group in ("P_pre","Wcap_pre","available_before_risk","c_preasm"):
        d=extend(micro())
        if group=="available_before_risk": d.available_before_risk=False
        elif group=="c_preasm": d.c_preasm["HV",]=-1
        else: setattr(d,group,float("nan"))
        with pytest.raises(ValueError): d.validate()
    d=extend(micro())
    d.base.lots.append({"id":"existing","kind":"Wa","index":("HV",),"amount":0.5})
    d.Wcap_pre=0.25
    with pytest.raises(ValueError,match="p=0"): d.validate()


def test_unverified_SP_cannot_certify(monkeypatch):
    monkeypatch.setattr(new,"phase1",lambda *args,**kw:{"status":"TIME_LIMIT","certified":False})
    for method in (new.direct,new.ccg):
        result=method(no_value())
        assert not result["certified"] and result["status"]=="TIME_LIMIT"
        assert result.get("ub") is None


def test_reproved_cuts_with_preconsumption_and_deadlines():
    from prefab_v21.cuts import certificates, expression, reachable_expression
    from prefab_v22.model import StateView
    d=time_bottleneck()
    d.base.p["A1"]["B","HV"]=0.5
    d.base.p["A"]["B","HV"]=1.5
    d.base.lots.append({"id":"pre_B","kind":"I","index":("B","a"),"amount":0.5})
    cert=list(certificates(d.base))[0]
    for p,x,r in product((0,0.5,1), repeat=3):
        plan=fixed(d,p)
        plan["x"]["B","a"]=x
        plan["r"]["k",]=r
        view=StateView(d,plan["p"])
        for w in new.vertices(d):
            result=new.phase1(d,plan,w)
            assert result["certified"]
            if result["objective"]<=TOL:
                assert expression(view,plan,w,cert)+TOL>=cert["lhs"]
                assert reachable_expression(view,plan,w,cert)+TOL>=cert["lhs"]
    plan=fixed(d,1)
    w=d.zero(); w["xi"]["v"]=1
    assert expression(StateView(d,plan["p"]),plan,w,cert)==pytest.approx(1)
    d.base.leads["g"]["k","s1"]=2
    assert reachable_expression(StateView(d,plan["p"]),plan,w,cert)<cert["lhs"]
    assert new.phase1(d,plan,w)["objective"]==pytest.approx(1)


@pytest.mark.parametrize("factory", [no_value,time_bottleneck,flexibility])
def test_reproved_cuts_do_not_change_extensive_optimum(factory):
    d=factory()
    a,b=new.direct(d),new.ccg(d,cuts=True)
    assert a["certified"] and b["certified"]
    assert a["objective"]==pytest.approx(b["objective"],abs=TOL)
