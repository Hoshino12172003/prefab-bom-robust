"""Audit source resource incidence and identify exact service witnesses."""
import gzip
import json
import os
import sys
from collections import defaultdict

import gurobipy as gp
from gurobipy import GRB

import run_matrix as run
from design import (ARCS,COSTS,F,HERE,KS,LABEL,PERIODS,PRIOR,SOURCE,Scenario,de_scenarios,
                    overlap_scenarios,scenarios)

DATASET="https://doi.org/10.17632/pr3sdy5vp3.1"
PAPER="https://doi.org/10.1016/j.ejor.2020.08.005"
ENGINE="https://global.toyota/pages/global_toyota/ir/financial-results/2026_3q_presentation_2_en.pdf"
SEAT="https://investors.adient.com/~/media/Files/A/Adient-IR/documents/form-10k-2024.pdf"
SELECTED={
    "B_RECEIPT":("PRIMARY","A;E",PAPER,"Regular cell-lot yield affects BEV configurations through one Pack mother"),
    "B_PROD":("PRIMARY","A;E",DATASET,"Pack conversion capacity couples all dependent BEV configurations"),
    "B_SHIP":("BATTERY_CONTROL","A;E",DATASET,"Existing third battery risk level kept as isolated benchmark"),
    "ENGINE":("PRIMARY","A;B;E",ENGINE,"Common engine processing capacity; external disruption precedent"),
    "GEAR":("PRIMARY","A;C;E",DATASET,"Common timed gear delivery across distinct source SKUs"),
    "SEAT":("PRIMARY","A;C;D;E",SEAT,"Zero-lead JIT/JIS seat delivery exposes all VIN configurations"),
}


def source_catalog(tables):
    parent=defaultdict(set)
    children=defaultdict(set)
    items={}
    for p,g,_ in tables["products"]:
        items[p]=g
    for m,c,_ in tables["BOM"]:
        if m!=c:
            parent[c].add(m)
            children[m].add(c)
    demand={p:t for _,p,_,t in tables["demands"]}
    configs={p:tuple(sorted(children[p])) for p in demand}
    selected=[]
    rows=[]
    arc_ids={value:key for key,value in ARCS.items()}
    specs=[(arc_ids.get((i,j),f"{i}->{j}"),g,(i,j),int(lead)) for i,j,lead,g in tables["arcs"]]
    specs.append(("B_RECEIPT","battery_componment",("battery-supplier_trans","battery-supplier_prod"),20))
    opening={(n,p) for n,p,*_ in tables["initial_inventories"]}
    history={(j,p) for _,j,p,*_ in tables["initial_flows"]}
    for rid,group,arc,lead in specs:
        sku={p for p,g in items.items() if g==group}
        direct=set().union(*(parent[p] for p in sku))
        used=set().union(*(children[p] for p in sku))
        frontier=set(sku)
        seen=set(sku)
        while frontier:
            frontier=set().union(*(parent[p] for p in frontier))-seen
            seen.update(frontier)
        vins=seen & demand.keys()
        distinct={configs[p] for p in vins}
        cap=[int(q) for i,j,_,q in tables["capacity_at_arc"] if (i,j)==arc]
        planned=sum((i,j)==arc for i,j,*_ in tables["max_flow_product_per_arc"])+sum(
            (i,j)==arc for i,j,*_ in tables["max_flow_group_per_arc"])
        status,criteria,source,reason=SELECTED.get(rid,("CATALOG_ONLY","",DATASET,
            "Source resource retained in the physical model; no additional shock selected"))
        flags=[]
        if rid!="B_RECEIPT" and len(sku)>1:
            flags.append("SHARED_CAPACITY_COUPLING")
        if all(len(parent[p])==1 for p in sku):
            flags.append("NO_CROSS_PRODUCT_FLEXIBILITY")
        if group=="seat_componment":
            flags.append("PER_SKU_PARENT_COUNT_RECORDED")
        row=dict(resource_id=rid,group=group,node_arc="->".join(arc),
            echelon="OEM" if group=="car" else "T2_TO_T1" if "trans" in arc[0] and group.endswith("componment") else
            "T1_TO_OEM" if arc[1]=="zp7" else "T1",
            upstream_downstream_role="fixed arrival availability" if rid=="B_RECEIPT" else
            "OEM assembly" if group=="car" else "delivery" if arc[1]=="zp7" or "trans" in arc[0] else "processing",
            number_of_VINs_affected=len(vins),number_of_distinct_vehicle_configurations_affected=len(distinct),
            number_of_mother_items=len(direct),number_of_child_items=len(used),
            distinct_exposed_SKUs=len(sku),max_direct_mothers_per_SKU=max(map(lambda p:len(parent[p]),sku)),
            shared_across_multiple_VINs=len(vins)>1,shared_across_multiple_configs=len(distinct)>1,
            due_date_groups=len({demand[p] for p in vins}),lead_time=lead,
            capacity=("dated historical receipts" if rid=="B_RECEIPT" else f"{min(cap)}..{max(cap)}"),
            planned_flow_presence=planned>0,planned_rows=planned,
            inventory_presence=any((n,p) in opening for n in arc for p in sku),
            initial_flow_presence=any((n,p) in history for n in arc for p in sku),
            evidence_class="SOURCE_CASE_ANCHORED",
            evidence_source=source,qualification="|".join(flags),business_interpretation=reason,status=status,
            screening_criteria=criteria)
        rows.append(row)
        if rid in SELECTED:
            selected.append(row)
    run.write("multi_bom_risk_candidate_catalog.csv",rows)
    run.write("selected_multi_bom_risk_resources.csv",selected)


def write_scenario_catalog():
    rows=[]
    for s,role in [*((s,"MATRIX_INITIAL") for s in scenarios()),
                   *((s,"OVERLAP_SENSITIVITY") for s in overlap_scenarios()),
                   *((s,"DE_SCALING") for s in de_scenarios())]:
        branches={e.resource if not e.resource.startswith("B_") else "BATTERY" for e in s.events}
        rows.append(dict(scenario_id=s.name,role=role,branch_count=len(branches),exposure_resource_days=s.exposure,
            admissible_Gamma="|".join(str(g) for g in (2,4,6) if s.exposure<=g),
            episode_details=json.dumps([(e.resource,e.start,e.duration,str(e.severity)) for e in s.events]),
            isolated_controls="|".join(s.isolated),recovery="ABRUPT",label=LABEL))
    run.write("multi_bom_scenario_catalog.csv",rows)


def battery_calculator(base):
    sys.path.insert(0,str(PRIOR))
    from audit_historical_reduction import nonbattery_certificate,service_bound
    from prefab_v3.robust import Episode,UncertaintySet
    nonbattery_certificate(base)
    u=UncertaintySet(PERIODS,(1,4),(F(1,2),),4,2)
    opening=run.receipts(base.network,run.NOMINAL)
    def value(s,x):
        by_resource={e.resource:e for e in s.events}
        episodes=tuple(Episode(e.start,e.duration,e.severity) if e else None for e in
                       (by_resource.get(k) for k in ("B_RECEIPT","B_PROD","B_SHIP")))
        return service_bound(base,u,opening,episodes,x)
    return value


def check_lp(base,s,row):
    x=tuple(int(row[p]) for p in ("x_C","x_T","x_O"))
    arrivals,factors=run.data_for(s,run.receipts(base.network,run.NOMINAL),base)
    name=f"LP_{s.name}__{row['policy_id']}"
    log=HERE/"logs"/f"{name}.log"
    log.write_text("",encoding="utf-8")
    with run.env() as env,gp.Model(name,env=env) as model:
        run.configure(model)
        b=run.add_block(model,base,s.name,run.Weights(0,0,0,0,0),reschedule=True,
            fixed_receipts=arrivals,arc_factors=factors,protection=run.protection_inventory(x))
        model.setObjective(run.on_time(b,base),GRB.MAXIMIZE)
        model.update()
        with model.relax() as relaxed:
            relaxed.Params.LogFile=os.path.relpath(log)
            relaxed.optimize()
            assert relaxed.Status==GRB.OPTIMAL and relaxed.ObjVal+1e-7>=int(row["Q_direct"])
            return dict(label=LABEL,scenario_id=s.name,policy_id=row["policy_id"],Q_direct=row["Q_direct"],
                        LP_upper_bound=relaxed.ObjVal,LP_gap=relaxed.ObjVal-int(row["Q_direct"]),
                        seconds=relaxed.Runtime,log=log.relative_to(HERE).as_posix())


def audit():
    tables=run.load_tables(SOURCE)
    base,_=run.source_base(tables)
    source_catalog(tables)
    write_scenario_catalog()
    catalog={s.name:s for s in [*scenarios(),*overlap_scenarios()]}
    raw=[r for name in catalog for r in run.read(HERE/"runs"/f"{name}.csv")]
    q={(r["scenario_id"],r["policy_id"]):int(r["Q_direct"]) for r in raw}
    assert len(raw)==len(q)==480
    prefix=battery_calculator(base)
    rows,witness=[],[]
    for r in raw:
        s=catalog[r["scenario_id"]]
        pid=r["policy_id"]
        actual=int(r["Q_direct"])
        pr=prefix(s,tuple(int(r[p]) for p in ("x_C","x_T","x_O")))
        parts={i:q[i,pid] for i in s.isolated}
        if not any(not e.resource.startswith("B_") for e in s.events):
            assert pr==actual
        minimum=min(parts.values(),default=actual)
        nominal=q["NR",pid]
        additive=nominal-sum(nominal-v for v in parts.values())
        assert actual<=minimum and actual<=pr
        row=dict(**r,Q_battery_prefix=pr,prefix_overestimate=pr-actual,
            isolated_service=json.dumps(parts),Q_independent_min=minimum,
            min_overestimate=minimum-actual,Q_additive_loss_prediction=additive,additive_error=additive-actual)
        rows.append(row)
        if minimum>actual or additive!=actual:
            witness.append(row)
    run.write("fixed_policy_multi_bom_service_audit.csv",rows)
    assert any(r["min_overestimate"]>0 for r in witness)
    # Carry both a simple threshold witness and the strongest observed overlap errors.
    picks=[next(r for r in witness if r["scenario_id"]=="BS" and r["policy_id"]=="K644_C")]
    for sid in ("BES","B_PROD_E_S","BS_OVERLAP","BG_OVERLAP","BGS_OVERLAP"):
        candidates=[r for r in witness if r["scenario_id"]==sid]
        if candidates:
            picks.append(max(candidates,key=lambda r:(abs(r["additive_error"]),r["min_overestimate"])))
    picks.append(next(r for r in witness if r["scenario_id"]=="BGS_OVERLAP" and r["policy_id"]=="K644_C"))
    def plan(s,p):
        with gzip.open(HERE/"witness"/f"{s}.json.gz","rt",encoding="utf-8") as f:
            return json.load(f)[p]
    all_witness,details=[],[]
    lookup={(r["scenario_id"],r["policy_id"]):r for r in rows}
    for r in picks:
        sid,pid=r["scenario_id"],r["policy_id"]
        joint=plan(sid,pid)
        reference=catalog[sid].isolated[0]
        isolated=plan(reference,pid)
        ids=[]
        for g,j,i in zip(base.network.groups,joint["group_on_time"],isolated["group_on_time"]):
            if i==j:
                continue
            ids.append(g.id)
            vins=[o.vin for o in g.orders]
            details.append(dict(label=LABEL,scenario_id=sid,policy_id=pid,comparison_isolated=reference,
                group=g.id,due_period=g.representative.due,full_bom=json.dumps(g.representative.bom),
                isolated_on_time=i,joint_on_time=j,delta=j-i,cohort_size=len(vins),
                selected_VIN_example=vins[0] if j else "",rejected_on_time_VIN_example=vins[j] if j<len(vins) else "",
                joint_early_assembly=r["early_assembly"],joint_late_outflow=r["late_outflow"],
                isolated_early_assembly=lookup[reference,pid]["early_assembly"],
                isolated_late_outflow=lookup[reference,pid]["late_outflow"],interpretation="one optimal allocation; VINs interchangeable within exact cohort"))
        all_witness.append(dict(label=LABEL,scenario_id=sid,policy_id=pid,x_C=r["x_C"],x_T=r["x_T"],x_O=r["x_O"],
            isolated_service=r["isolated_service"],direct_optimum=r["Q_direct"],
            simple_min=r["Q_independent_min"],min_discrepancy=r["min_overestimate"],
            simple_additive=r["Q_additive_loss_prediction"],additive_discrepancy=r["additive_error"],
            affected_vin_groups="|".join(ids),resource_competition="|".join(catalog[sid].isolated),
            binding_constraints="|".join(joint["saturated_capacity"]),
            chosen_rejected_vins="See vin_competition_audit.csv",optimum_log=r["log"]))
    run.write("nonseparability_witness.csv",all_witness)
    run.write("vin_competition_audit.csv",details)
    lp=[check_lp(base,catalog[r["scenario_id"]],r) for r in picks]
    run.write("LP_relaxation_audit.csv",lp)
    print("matrix rows",len(rows),"joint min failures",sum(r["min_overestimate"]>0 for r in rows),
          "additive failures",sum(r["additive_error"]!=0 for r in rows),"LP gaps",sum(r["LP_gap"]>1e-7 for r in lp))


if __name__=="__main__":
    audit()
