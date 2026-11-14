from dataclasses import replace
from itertools import product
from pathlib import Path

import pytest

from prefab_v25.data import (aggregate, expand, NOMINAL, Order, Scenario, receipts,
                            CELL, PACK, PROD, T1, OEM, TRANSPORT_ARC)
from prefab_v25.examples import micro, micro_risks, TOY_COSTS
from prefab_v25.model import initial_state, nominal, extensive
from prefab_v25.source import verified_bytes

TOL = 1e-7


def check(result, expected):
    assert result["certified"] and result["status"] == "OPTIMAL"
    assert result["objective"] == pytest.approx(expected,abs=TOL)
    assert result["objective"] == pytest.approx(result["bound"],abs=TOL)
    assert result["quality_residual"] <= TOL


def test_source_gate_before_workbook_parse(tmp_path):
    p = tmp_path/"invalid.xlsb"
    p.write_bytes(b"not the frozen workbook")
    with pytest.raises(ValueError,match="SHA-256"):
        verified_bytes(p)


def test_official_source_solve_is_blocked_before_optimizer():
    from prefab_v25.source import SOURCE_SHA256
    with pytest.raises(ValueError,match="frozen paper_scale_v2 manifest"):
        nominal(replace(micro(),source_sha256=SOURCE_SHA256),0,TOY_COSTS)


def test_frozen_manifest_matrix_and_rejects_tampering():
    from prefab_v25.formal import manifest_bytes, frozen_runs
    path = Path(__file__).resolve().parents[1]/"artifacts/v25_formal_20261110/manifest.json"
    payload = manifest_bytes(path)
    runs = frozen_runs(payload)
    assert [(run.id,run.budget) for run in runs] == [
        ("nominal_B0",0),("nominal_B20",175120),("nominal_B50",437800),
        ("nominal_B100",875600),("DE_B0",0),("DE_B50",437800)]
    assert all(run.costs==(7177.049180327869,8756,8756) for run in runs)
    nom,l1,l2,l3 = runs[-1].scenarios
    assert (nom.name,l1.name,l2.name,l3.name)==("NOM","L1_CERT","L2_CERT","L3_CERT")
    assert l1.arrival=={66:0.5}
    assert l2.production==l3.transport=={64:0.5,65:0.5,66:0.5}
    with pytest.raises(ValueError,match="SHA-256"):
        frozen_runs(payload.replace(b'"arrival_multiplier": 0.5',b'"arrival_multiplier": 0.6'))


def test_capacity_and_historical_flows_keep_source_units():
    d = micro()
    component = replace(d.arcs[0],capacity={60:2058,61:2058})
    pack = replace(d.arcs[1],capacity={61:294})
    assert component.capacity == {60:2058,61:2058}
    assert pack.capacity[61] == 294
    assert d.arcs[-1].capacity[61] == 2
    assert len(d.historical) == 3 and sum(row[-1] for row in d.historical) == 20


def test_historical_timing_and_L1_loss_are_local():
    d=micro()
    historical=d.historical + ((*TRANSPORT_ARC,PACK,60,2),)
    d=replace(d,historical=historical)
    expected={(PROD,item,61):q for item,q in zip(CELL,(10,6,4))}
    expected[OEM,PACK,61]=2
    assert receipts(d,NOMINAL)==expected
    l1=Scenario("half",{61:0.5},{},{})
    assert receipts(d,l1)[PROD,CELL[0],61]==5
    l3=Scenario("loss",{},{},{61:0})
    assert receipts(d,l3)==expected and d.historical==historical
    with pytest.raises(ValueError,match="fractional usable"):
        extensive(d,[Scenario("fractional",{61:0.13},{},{})],0,TOY_COSTS)


def test_zero_budget_nominal_and_singleton_DE():
    d=micro()
    direct=nominal(d,0,TOY_COSTS)
    finite=extensive(d,[Scenario("ones",{61:1},{62:1},{63:1})],0,TOY_COSTS)
    for result in (direct,finite):
        check(result,0.25)
        assert set(result["buffers"].values())=={0}
    assert direct["variables"]==direct["integer_variables"]
    assert finite["variables"]-finite["integer_variables"]==1


@pytest.mark.parametrize("buffers,due,ratio",[
    ((1,0,0),62,0), ((1,0,0),63,1),
    ((0,1,0),61,0), ((0,1,0),62,1), ((0,0,1),61,1),
])
def test_buffer_timing_chain(buffers,due,ratio):
    d=micro()
    g=d.groups[0]
    singleton=replace(g,orders=(replace(g.orders[0],due=due),))
    final=replace(d.arcs[-1],recipes={g.id:((PACK,1),)})
    d=replace(d,arcs=(*d.arcs[:-1],final),groups=(singleton,),historical=())
    r=nominal(d,4,TOY_COSTS,fixed_buffers=buffers)
    check(r,ratio)
    if buffers[0]:
        assert [r["scenarios"]["nominal"]["initial"][PROD,item] for item in CELL]==[10,6,4]


def test_short_one_component_prevents_pack():
    d=micro()
    initial={(PROD,item):q for item,q in zip(CELL,(10,6,3))}
    d=replace(d,historical=(),initial=initial)
    check(nominal(d,0,TOY_COSTS),0)


def test_group_expansion_and_objective_equivalence():
    d=micro()
    a=nominal(d,7,TOY_COSTS)
    b=nominal(micro(False),7,TOY_COSTS)
    check(a,0.75)
    check(b,a["objective"])
    schedule=a["scenarios"]["nominal"]["deliveries"]
    expanded={}
    for g in d.groups:
        expanded.update(expand(g,{t:round(schedule[g.id,t]) for t in d.periods}))
    assert len(expanded)==sum(schedule.values())
    assert sum(t<=o.due for g in d.groups for o in g.orders
               if (t:=expanded.get(o.vin)) is not None)==3
    a=Order("A","zp8",61,((PACK,1),))
    assert len(aggregate([a,replace(a,vin="B",weight=2),replace(a,vin="C",due=62),
                          replace(a,vin="D",bom=((PACK,2),))]))==4


def test_M3_independent_enumeration_and_shared_state():
    d=micro()
    risks=(NOMINAL,*micro_risks())
    budget=7
    r=extensive(d,risks,budget,TOY_COSTS)
    check(r,0.25)
    # Independent outer enumeration of every integer buffer tuple.
    candidates=[]
    for x in product(*(range(budget//c+1) for c in TOY_COSTS)):
        if sum(a*b for a,b in zip(x,TOY_COSTS))<=budget:
            q=[extensive(d,[s],budget,TOY_COSTS,fixed_buffers=x) for s in risks]
            assert all(v["certified"] for v in q)
            candidates.append(min(v["objective"] for v in q))
    assert max(candidates)==pytest.approx(r["objective"],abs=TOL)
    for scenario in r["scenarios"].values():
        assert scenario["initial"]==initial_state(d,tuple(r["buffers"].values()))
