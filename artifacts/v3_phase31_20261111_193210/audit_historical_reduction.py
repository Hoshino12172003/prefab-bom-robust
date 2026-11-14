"""Independent service certificate for historical pure-service diagnostics."""
import gzip
import json
from collections import Counter

from run_diagnostics import (CELL,F,HERE,NOMINAL,PACK,PERIODS,PROD,PRODUCTION_ARC,ROOT,SOURCE,TRANSPORT_ARC,
                             Episode,candidate,load_tables,read,receipts,source_base,write)
from prefab_v25.data import COMPONENT_ARC,OEM,T1
from prefab_v3.base import ASSEMBLY


def nonbattery_certificate(base):
    path=ROOT/"artifacts/v25_phase20_20261110_203851/FULL28000_witness.json.gz"
    with gzip.open(path,"rt",encoding="utf-8") as f:
        witness=json.load(f)
    net=base.network
    battery={PACK,*CELL}
    arcs=[a for a in net.arcs if a.key not in (ASSEMBLY,COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC)]
    seat_arc=("seat-supplier_inv",OEM)
    seat_items={p for p,g in base.products.items() if g=="seat"}
    flow={tuple(k):q for k,q in witness["dispatch"]}
    external={tuple(k):q for k,q in witness["supply"]}
    keys={(a.destination,p) for a in arcs for p in a.recipes}
    keys|={(a.origin,c) for a in arcs for recipe in a.recipes.values() for c,_ in recipe}
    due,orders=Counter(),Counter()
    for g in net.groups:
        t=g.representative.due
        orders[t]+=len(g.orders)
        for child,units in g.representative.bom:
            if child not in battery:
                due[OEM,child,t]+=len(g.orders)*units
    # Move early seat inventory back across the zero-lead supplier arc.
    assembly=next(a for a in net.arcs if a.key==ASSEMBLY)
    assert all(orders[t]<=assembly.capacity[t] for t in PERIODS)
    assert all(net.initial.get((OEM,p),0)==0 and (seat_arc[0],p) not in net.inventory_bounds
               for p in seat_items)
    old_receipts=receipts(net,NOMINAL)
    assert not any(n==OEM and p in seat_items and q for (n,p,_),q in old_receipts.items())
    changes=Counter({k:v for k,v in old_receipts.items() if k[:2] in keys})
    for key,q in external.items():
        assert key[:2] in net.external and key[:2] in keys and q>=0
        changes[key]+=q
    for a in arcs:
        for t in PERIODS:
            total=0
            for p,recipe in a.recipes.items():
                key=(*a.key,p,t)
                q=due[OEM,p,t] if a.key==seat_arc else flow.get(key,0)
                assert 0<=q<=net.product_caps.get(key,q)
                total+=q
                changes[a.destination,p,t+a.lead]+=q
                for child,qty in recipe:
                    changes[a.origin,child,t]-=qty*q
            assert total<=min(a.capacity[t],net.group_caps.get((*a.key,t),a.capacity[t]))
    ledger={key:net.initial.get(key,0) for key in keys}
    margins=[]
    for t in PERIODS:
        for key in keys:
            n,p=key
            at=(*key,t)
            ledger[key]+=changes[at]-due[at]
            lo,hi=net.inventory_bounds.get(key,(0,float("inf")))
            assert lo<=ledger[key]<=hi
            if n==OEM and p in seat_items:
                assert ledger[key]==0
            if n==OEM and p not in seat_items and hi!=float("inf"):
                margin=hi-ledger[key]-sum(due[OEM,p,s] for s in PERIODS)
                assert margin>=0
                margins.append(margin)
    return dict(full_vin_nonbattery_JIT=True,raw_witness=str(path.relative_to(ROOT)),zero_lead_seat_redispatch=True,
                min_OEM_nonseat_headroom_after_subset_bound=min(margins),shared_assembly_max_due=max(orders.values()))


def service_bound(base,u,opening,episodes,x):
    net=base.network
    arrival,factors=u.attenuation(episodes,opening)
    caps={a.key:a.capacity for a in net.arcs}
    due=Counter()
    for g in net.groups:
        if (PACK,1) in g.representative.bom:
            due[g.representative.due]+=len(g.orders)
    assert sum(due.values())==3003
    assert net.inventory_bounds[OEM,PACK]==(0,99999)
    assert (T1,PACK) not in net.inventory_bounds
    assert all(net.inventory_bounds[PROD,p]==(0,99999) for p in CELL)
    assert not any(p==PACK or (p in CELL and n!=COMPONENT_ARC[0]) for n,p in net.external)
    assert not any(k[:2] in (COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC)
                   for k in (*net.product_caps,*net.group_caps))
    assert next(a.lead for a in net.arcs if a.key==COMPONENT_ARC)>len(PERIODS)
    assert all(a.lead==1 for a in net.arcs if a.key in (PRODUCTION_ARC,TRANSPORT_ARC))
    c,t1,o=x
    recipe=(10,6,4)
    cells=[net.initial[PROD,p]+coef*c for p,coef in zip(CELL,recipe)]
    prod=ship=cumulative_due=miss=0
    t1_supply=net.initial[T1,PACK]+t1
    oem_supply=net.initial[OEM,PACK]+o
    for t in PERIODS:
        cells=[q+arrival.get((PROD,p,t),0) for p,q in zip(CELL,cells)]
        t1_supply+=arrival.get((T1,PACK,t),0)
        oem_supply+=arrival.get((OEM,PACK,t),0)
        cumulative_due+=due[t]
        miss=max(miss,cumulative_due-oem_supply-ship)
        assert max(cells)<99999 and oem_supply+ship<99999
        ship=min(ship+int(caps[TRANSPORT_ARC][t]*factors.get((*TRANSPORT_ARC,t),1)),t1_supply+prod)
        prod=min(prod+int(caps[PRODUCTION_ARC][t]*factors.get((*PRODUCTION_ARC,t),1)),
                 min(q//a for q,a in zip(cells,recipe)))
    return net.demand_weight-miss


def main():
    base,_=source_base(load_tables(SOURCE))
    witness=nonbattery_certificate(base)
    opening=receipts(base.network,NOMINAL)
    u=candidate()
    cases=json.loads((HERE/"diagnostic_run.json").read_text(encoding="utf-8"))["diagnostic_scenarios"]
    cases={name:tuple(Episode(e[0],e[1],F(e[2])) if e else None for e in es) for name,es in cases.items()}
    archived=[r for name in ("full_model_buffer_ablation","historical_fixed_policy_scenario_audit",
                             "selected_scenario_de_validation") for r in read(HERE/f"{name}.csv")]
    rows=[]
    for r in archived:
        x=tuple(int(r[key]) for key in ("x_C","x_T","x_O"))
        by_case={sid:service_bound(base,u,opening,cases[sid],x) for sid in r["scenario_ids"].split("|")}
        exact=min(by_case.values())
        assert exact==int(r["Q"]),(r["case"],exact,r["Q"])
        rows.append(dict(case=r["case"],fixed_policy=str(x),direct_Q=r["Q"],conditional_exact_Q=exact,
                         scenario_max_service=json.dumps(by_case),residual=0,log=r["log"]))
    write("historical_fixed_policy_reduction_check.csv",rows)
    witness["all_diagnostics_replayed"]=len(rows)
    (HERE/"historical_reduction_proof_checks.json").write_text(json.dumps(witness,indent=2)+"\n",encoding="utf-8")
    print(f"{len(rows)} full historical Direct optima match conditional certificate")


if __name__=="__main__":
    main()
