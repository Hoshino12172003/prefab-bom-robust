import csv
from fractions import Fraction as F
from pathlib import Path

import gurobipy as gp
import pytest
from gurobipy import GRB

from prefab_v25.data import Arc,CELL,Group,Network,Order,OEM,PACK,PROD,T1,TRANSPORT_ARC
from prefab_v3.base import ASSEMBLY,Base,Weights,add_block
from prefab_v3.interface import RegularState
from prefab_v3.robust import Episode,UncertaintySet,add_selected_scenarios,on_time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/v3_phase31_20261111_193210"


def records(name):
    with (OUT/f"{name}.csv").open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def test_episode_budget_contiguity_concurrency_and_recovery():
    u=UncertaintySet(tuple(range(61,67)),(1,3),(F(1,2),),3,2,2)
    e=Episode(61,1,F(1,2))
    assert u.factors(e)==(F(1,2),F(2,3),F(5,6),F(1),F(1),F(1))
    assert (0,0,0) in set(u.feasible_masks())
    with pytest.raises(ValueError,match="budget"):
        u.validate((e,e,e))
    with pytest.raises(ValueError,match="budget"):
        u.validate((Episode(61,3,F(1,2)),e,None))
    with pytest.raises(ValueError,match="ineligible"):
        u.validate((Episode(65,3,F(1,2)),None,None))
    available,caps=u.attenuation((e,e,None),{(PROD,CELL[0],61):9,("elsewhere",CELL[0],61):9})
    assert available[PROD,CELL[0],61]==4 and available["elsewhere",CELL[0],61]==9
    assert len(caps)==3


def test_candidate_counts_and_exact_rhs_deduplication():
    rows=records("uncertainty_set_size_audit")
    normal=next(r for r in rows if (r["gamma_resource_days"],r["concurrency"],r["allowed_durations"],r["recovery_steps"])
                ==("6","2","1|3|5","0"))
    assert (normal["z_patterns"],normal["explicit_trajectories"],normal["historical_unique_effective_rhs"])==(
        "12655","287443","38527")
    for r in rows:
        assert 1<=int(r["historical_unique_effective_rhs"])<=int(r["unique_factor_trajectories"])
        assert 1<=int(r["maximal_z_patterns_at_max_severity"])<=int(r["z_patterns"])


def test_selected_scenarios_share_investment_and_preserve_normal_stock():
    periods=(61,62,63)
    groups=tuple(Group(str(i),(Order(str(i),"zp8",63,bom),)) for i,bom in enumerate(
        (((PACK,1),("engine",1)),((PACK,1),("engine",1)),(("engine",1),))))
    arcs=(Arc(T1,OEM,1,{61:0,62:1,63:0},{PACK:((PACK,1),)}),
          Arc(*ASSEMBLY,0,dict.fromkeys(periods,2),{g.id:g.representative.bom for g in groups}))
    net=Network(periods,arcs,groups,{},(),(),{},{},{})
    products={PACK:"battery","engine":"engine",**dict.fromkeys(CELL,"component"),**{g.id:"car" for g in groups}}
    base=Base(net,products,dict.fromkeys(products,0),())
    state=RegularState(dict.fromkeys(net.state_keys(),0)|{(OEM,"engine"):3,(T1,PACK):1},{},
                       "Synthetic normal stock for Phase 3.1 regression")
    u=UncertaintySet(periods,(1,),(F(1),),1,1)
    shock=(None,None,Episode(62,1,F(1)))
    with gp.Model() as model:
        model.Params.OutputFlag=0
        x,z,blocks=add_selected_scenarios(model,base,state,(1,1,1),1,u,[("NR",(None,)*3),("L3",shock)])
        for variable,value in zip(x,(0,0,1)):
            variable.LB=variable.UB=value
        model.optimize()
        assert model.Status==GRB.OPTIMAL and z.X==2
        assert blocks["L3"].regular_opening[T1,PACK]==1
        assert blocks["L3"].protection_opening[OEM,PACK].getValue()==1
        assert blocks["L3"].flow[(*TRANSPORT_ARC,PACK,62)].X==0


def test_nested_bom_competition_is_not_an_integral_min_cost_flow():
    # Four triples in a parity design. Any two orders share a scarce SKU.
    triples=((0,0,0),(0,1,1),(1,0,1),(1,1,0))
    groups=tuple(Group(f"vin{i}",(Order(f"vin{i}","zp8",61,
        ((f"e{a}",1),(f"g{b}",1),(f"s{c}",1),(PACK,1))),)) for i,(a,b,c) in enumerate(triples))
    arcs=(Arc("seats",OEM,0,{61:2},{"s0":(("s0",1),),"s1":(("s1",1),)}),
          Arc(*ASSEMBLY,0,{61:2},{g.id:g.representative.bom for g in groups}))
    opening={(OEM,p):1 for p in ("e0","e1","g0","g1")}
    opening.update({("seats","s0"):1,("seats","s1"):1,(OEM,PACK):2})
    net=Network((61,),arcs,groups,opening,(),(),{},{},{})
    products={"e0":"engine","e1":"engine","g0":"gear","g1":"gear","s0":"seat","s1":"seat",
              PACK:"battery",**dict.fromkeys(CELL,"component"),**{g.id:"car" for g in groups}}
    base=Base(net,products,dict.fromkeys(products,0),())
    with gp.Model() as model:
        model.Params.OutputFlag=0
        block=add_block(model,base,"test",Weights(0,0,0,0,0))
        model.setObjective(on_time(block,base),GRB.MAXIMIZE)
        model.optimize()
        assert model.Status==GRB.OPTIMAL and model.ObjVal==1
        with model.relax() as lp:
            lp.optimize()
            assert lp.Status==GRB.OPTIMAL and lp.ObjVal==2


def test_full_network_ablation_and_selected_direct_expansion():
    rows=records("full_model_buffer_ablation")
    assert len(rows)==60
    opened={(r["T1_pack_budget_equivalents"],r["scenario_ids"]):int(r["Q"]) for r in rows if not r["excluded_position"]}
    for r in rows:
        budget,scenario,q=r["T1_pack_budget_equivalents"],r["scenario_ids"],int(r["Q"])
        assert r["scope"]=="HISTORICAL_STRESSED_STATE_DIAGNOSTIC"
        assert r["status"]=="OPTIMAL" and q==int(r["bound"]) and r["exact_matrix_residual"]=="0"
        assert q<=opened[budget,scenario] and int(r["risk_loss"])==opened[budget,"NR"]-q
        assert int(r["ablation_loss"])==opened[budget,scenario]-q
        if r["excluded_position"]:
            assert r[r["excluded_position"]]=="0"
    selected,=records("selected_scenario_de_validation")
    assert selected["status"]=="OPTIMAL" and int(selected["Q"])<=int(selected["independent_single_scenario_upper"])
    assert int(selected["integers"])>3*75000


def test_historical_conditional_exactness_covers_all_direct_runs():
    rows=records("historical_fixed_policy_reduction_check")
    assert len(rows)==len({r["case"] for r in rows})==81
    assert all(r["direct_Q"]==r["conditional_exact_Q"] and r["residual"]=="0" for r in rows)
