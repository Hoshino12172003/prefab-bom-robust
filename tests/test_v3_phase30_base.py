import csv
import json
from fractions import Fraction
from pathlib import Path

import gurobipy as gp
import pytest
from gurobipy import GRB

from prefab_v25.data import Arc, CELL, Group, Network, NOMINAL, Order, OEM, PACK, PROD, T1, receipts
from prefab_v25.source import load_tables
from prefab_v3.base import ASSEMBLY, Base, add_block, operation_recipes, source_base
from prefab_v3.interface import BudgetedUncertainty, Disruption, Effect, RegularState, add_master, add_scenario_block

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"artifacts/v3_phase30_20261111_104032"
SOURCE = Path("external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip")


@pytest.fixture(scope="module")
def full():
    tables = load_tables(SOURCE)
    base,_ = source_base(tables)
    return tables,base


def test_full_source_network_vins_and_distinct_planning_caps(full):
    tables,base = full
    n = base.network
    assert len(tables["products"])==28049 and len(n.arcs)==11 and len(n.periods)==14
    assert {x for a in n.arcs for x in a.key}=={r[0] for r in tables["nodes"]}
    arc = {a.key:a for a in n.arcs}
    for i,j,lead,_ in tables["arcs"]:
        assert arc[i,j].lead==lead
    for i,j,t,c in tables["capacity_at_arc"]:
        assert arc[i,j].capacity[t]==c
    assert len(n.product_caps)==365 and len(n.group_caps)==20
    assert n.product_caps["engine-supplier_prod","engine-supplier_inv","D60",65]==22
    vins = {o.vin:(o.node,1,o.due) for g in n.groups for o in g.orders}
    assert vins=={p:(node,q,t) for node,p,q,t in tables["demands"]}
    assert len(vins)==28000 and sum(len(g.orders) for g in n.groups if (PACK,1) in g.representative.bom)==3003


def test_bom_override_source_and_simultaneous_generic():
    items = {"raw":"X","left":"Y","right":"Z"}
    arcs = [("plant","left_store",1,"Y"),("plant","right_store",1,"Z")]
    operations = [("plant","X","Y",99,1,4,1),("plant","X","Z",4,1,4,0)]
    recipes,links = operation_recipes(operations,arcs,items,{"left":[("raw",4)]})
    assert recipes["plant","left_store"]["left"]==(("raw",2),)
    assert recipes["plant","right_store"]["right"]==(("raw",2),)
    assert links==(((("plant","left_store","left"),1),(("plant","right_store","right"),1)),)
    period = 61
    net = Network((period,),tuple(Arc(i,j,lead,{period:2},recipes[i,j]) for i,j,lead,_ in arcs),
                  (),{("plant","raw"):4},(),(),{},{},{})
    products = items|{PACK:"battery"}|dict.fromkeys(CELL,"battery_component")
    base = Base(net,products,dict.fromkeys(products,0),links)
    with gp.Model() as model:
        model.Params.OutputFlag=0
        b = add_block(model,base,"joint",scheduled_equalities={("plant","left_store","left",61):1})
        model.setObjective(b.loss)
        model.optimize()
        assert model.Status==GRB.OPTIMAL
        assert b.flow["plant","right_store","right",61].X==1
        assert b.inventory["plant","raw",61].X==0


def test_source_initial_flows_and_nested_bom(full):
    tables,base = full
    net = base.network
    assert net.historical==tables["initial_flows"]
    assert sum(1 for m,c,_ in tables["BOM"] if m==c)==49
    assert all(net.initial[n,p]==q for n,p,q,*_ in tables["initial_inventories"])
    assert net.inventory_bounds[OEM,PACK]==(0,99999)
    by_arc = {a.key:a for a in net.arcs}
    assert by_arc[PROD,T1].recipes[PACK]==tuple(zip(CELL,(10,6,4)))
    assert by_arc[T1,OEM].recipes[PACK]==((PACK,1),)
    assert all(by_arc[ASSEMBLY].recipes[g.id]==g.representative.bom for g in net.groups)
    assert all(receipts(net,NOMINAL)[PROD,c,66]>0 for c in CELL)
    source = RegularState(net.initial,receipts(net,NOMINAL),"t60")
    with pytest.raises(ValueError,match="historical stressed"):
        source.validate(base)
    via_dispatch = RegularState.from_dispatches(base,net.initial,
        [(i,j,p,int(t),int(q)) for i,j,p,t,q in net.historical],"t60")
    assert via_dispatch.arrivals==source.arrivals


def test_full_replication_integer_evidence_and_rescheduling():
    run = json.loads((OUT/"replication_run.json").read_text(encoding="utf-8"))
    cases = {r["case"]:r for r in run["results"]}
    a,b = cases["A_NO_RESCHEDULE"],cases["B_RESCHEDULE_FIG10"]
    assert all(r["status"]=="OPTIMAL" and r["objective"]==r["bound"] and r["gap"]==0 for r in cases.values())
    assert all(r["max_exact_balance_residual"]==r["max_solver_residual"]==0 for r in cases.values())
    assert all(r["objective"]==sum(v for k,v in r.items() if k.startswith("penalty_")) for r in cases.values())
    assert all(r["integers"]==r["variables"] for r in cases.values())
    assert (a["delivered"],a["bev_shortfall"],a["nonbev_delivered"])==(26448,1552,24997)
    assert a["assembly_early"]==a["assembly_late"]==0
    assert b["assembly_early"]>0 and b["oem_unassigned"]==1552
    assert b["penalty_unassigned"]==200*1552
    with (OUT/"B_RESCHEDULE_FIG10_VIN_schedule.csv").open(encoding="utf-8-sig",newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows)==len({r["vin"] for r in rows})==28000
    assert sum(r["bev"]=="True" for r in rows)==3003


def test_prospective_buffers_and_complete_recourse_interface():
    periods = (61,62,63)
    engine = "engine"
    groups = tuple(Group(p,(Order(p,ASSEMBLY[1],63,recipe),)) for p,recipe in (
        ("V1",((engine,1),(PACK,1))),("V2",((engine,1),(PACK,1))),("V3",((engine,1),))))
    arcs = (Arc(T1,OEM,1,{61:0,62:1,63:0},{PACK:((PACK,1),)}),
            Arc(*ASSEMBLY,0,dict.fromkeys(periods,2),{g.id:g.representative.bom for g in groups}))
    network = Network(periods,arcs,groups,{},(),(),{},{},{})
    products = {PACK:"battery",engine:"engine",**dict.fromkeys(CELL,"battery_component"),
                **{g.id:"car" for g in groups}}
    base = Base(network,products,dict.fromkeys(products,0),())
    state = RegularState(dict.fromkeys(network.state_keys(),0)|{(OEM,engine):3,(T1,PACK):1},{},
                         "Synthetic positive regular stock for interface regression")
    effect = Effect("L3","arc_capacity",(T1,OEM),62,Fraction(1),1)
    event = ("arc_capacity",(T1,OEM),62)
    nominal = Disruption("NR")
    disrupted = Disruption("L3",(effect,),frozenset({event}))
    BudgetedUncertainty(frozenset({event}),1).validate(disrupted)
    with pytest.raises(ValueError,match="budget"):
        BudgetedUncertainty(frozenset({event}),0).validate(disrupted)
    with gp.Model() as model:
        model.Params.OutputFlag=0
        x,z,blocks = add_master(model,base,state,(1,1,1),1,[nominal,disrupted],lambda b:b.outflow.sum())
        for var,value in zip(x,(0,0,1)):
            var.LB=var.UB=value
        model.setObjective(z,GRB.MAXIMIZE)
        model.optimize()
        assert model.Status==GRB.OPTIMAL and z.X==2
        assert blocks["L3"].regular_opening[T1,PACK]==1
        assert blocks["L3"].protection_opening[OEM,PACK].getValue()==1
        assert blocks["L3"].flow[T1,OEM,PACK,62].X==0
        assert all(v.VType==GRB.INTEGER for b in blocks.values() for family in
                   (b.flow,b.inventory,b.shortfall,b.outflow,b.unassigned) for v in family.values())
    with gp.Model() as model:
        model.Params.OutputFlag=0
        b = add_scenario_block(model,base,state,(0,0,1),nominal)
        model.setObjective(b.outflow.sum(),GRB.MAXIMIZE)
        model.optimize()
        assert model.Status==GRB.OPTIMAL and model.ObjVal==3
