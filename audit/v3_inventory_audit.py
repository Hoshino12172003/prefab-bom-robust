"""Full item-node census, source-state transitions, and preparation evidence."""

import json
from collections import Counter, defaultdict
from fractions import Fraction

from v3_audit_context import SOURCE, dump, load, write
from prefab_v25.data import BUFFER_EFFECTS, CELL, OEM, PACK


NODE_TYPE = {"zp7":"OEM_ASSEMBLY_INPUT","zp8":"OEM_FINISHED_VEHICLE_OUTFLOW"}
CALIBRATION = {key: (str(cost), unit) for effects,cost,unit in zip(
    BUFFER_EFFECTS, (Fraction(1),Fraction(27,19),Fraction(297,190)),
    ("balanced_cell_kit_10_6_4","T1_pack","OEM_pack"),strict=True) for key,_ in effects}
RISK = {
    ("battery-supplier_trans","battery-supplier_prod"):"B_RECEIPT:fixed_cell_arrivals",
    ("battery-supplier_prod","battery-supplier_inv"):"B_PROD:production",
    ("battery-supplier_inv","zp7"):"B_SHIP:transport",
    ("seat-supplier_inv","zp7"):"SEAT:transport",
    ("gear-supplier_inv","zp7"):"GEAR:transport",
    ("engine-supplier_prod","engine-supplier_inv"):"ENGINE:production",
}


def text_arcs(arcs):
    return "|".join("->".join(a.key) for a in arcs)


def compact(mapping):
    return json.dumps(mapping,ensure_ascii=False,separators=(",",":"))


def main():
    tables, base = load()
    net = base.network
    items = {p:g for p,g,_ in tables["products"]}
    nodes = tuple(n for n, in tables["nodes"])
    raw_inventory = {(n,p):(int(q),int(ub)) for n,p,q,_,ub,_ in tables["initial_inventories"]}
    raw_edges = {(i,j):g for i,j,_,g in tables["arcs"]}
    parents,children,links,incoming,outgoing = (defaultdict(set),defaultdict(set),defaultdict(set),
                                               defaultdict(list),defaultdict(list))
    identity = set()
    raw_bom = {}
    for parent,child,qty in tables["BOM"]:
        if parent==child:
            assert qty==1
            identity.add(parent)
        else:
            parents[child].add(parent)
            children[parent].add(child)
            assert (parent,child) not in raw_bom
            raw_bom[parent,child] = int(qty)
    group_of = {str(o.vin):g.id for g in net.groups for o in g.orders}
    assert len(group_of)==28000 and len(items)==28049 and len(nodes)==12
    # Expand the exact VIN groups back to original item IDs for the audit.
    arcs = {a.key:a for a in net.arcs}
    ass = arcs["zp7","zp8"]
    transitions = []
    for arc in net.arcs:
        is_assembly = arc.key==ass.key
        recipes = ({str(o.vin):ass.recipes[g.id] for g in net.groups for o in g.orders}
                   if is_assembly else arc.recipes)
        for output, recipe in recipes.items():
            assert recipe
            incoming[arc.destination,output].append((arc,recipe))
            links[arc.destination,output].add("IN:"+"->".join(arc.key))
            for item,coef in recipe:
                assert coef.denominator==1 and coef>0
                outgoing[arc.origin,item].append(arc)
                links[arc.origin,item].add("OUT:"+"->".join(arc.key))
                if is_assembly:
                    assert raw_bom[output,item] == coef
                transitions.append((arc,item,output,coef))
    for n,p in net.external:
        links[n,p].add("SOURCE_EXTERNAL_INFLOW")
    for _,n,p,_,_ in net.historical:
        links[n,p].add("HISTORICAL_RECEIPT_TARGET")
    for g in net.groups:
        for o in g.orders:
            links[o.node,str(o.vin)].add("ORDER_OUTFLOW")
    assert sum(len(g.orders) for g in net.groups)==28000
    for g in net.groups:
        recipe = ass.recipes[g.id]
        count = Counter(items[p] for p,q in recipe for _ in range(int(q)))
        assert all(count[k]==1 for k in ("engine","gear","seat")) and count["battery"] in (0,1)
        assert all(o.bom==tuple(sorted(recipe)) and o.due==g.representative.due for o in g.orders)
    assert arcs["battery-supplier_prod","battery-supplier_inv"].recipes[PACK]==tuple(zip(CELL,(10,6,4)))
    assert all(arcs[f"{b}-supplier_prod",f"{b}-supplier_inv"].recipes[p]==((p,1),)
               for b in ("engine","gear") for p,g in items.items() if g==b)
    assert len({(a.key,p,o) for a,p,o,_ in transitions})==len(transitions)

    def downstream(a, p):
        return list(dict.fromkeys(b.key for b in outgoing[a.destination,p] if b.origin!="zp7"))

    def transition_rows():
        for a,p,o,q in transitions:
            downstream_keys=downstream(a,o)
            kind = ("ASSEMBLY" if a.key==ass.key else
                    "TRANSPORT_SAME_SKU" if a.origin.endswith(("_trans","_inv")) else
                    "PRODUCTION_SAME_SKU_STATE" if p==o else "PRODUCTION_COMPONENT_CONVERSION")
            yield dict(input_item=p,output_item=o,operation_node=a.origin,
                operation_type=kind,operation_destination=a.destination, input_quantity=int(q),output_quantity=1,
                operation_lead_time=a.lead,operation_capacity_by_period=compact(a.capacity),
                production_lead_time=a.lead if not kind.startswith("TRANSPORT") else None,
                production_capacity=min(a.capacity.values()) if not kind.startswith("TRANSPORT") else None,
                inventory_location=a.destination,downstream_transport_arcs="|".join("->".join(k) for k in downstream_keys),
                transport_lead_time=a.lead if kind.startswith("TRANSPORT") else
                                    "|".join(str(arcs[k].lead) for k in downstream_keys),
                compatible_BOM_groups=group_of.get(o,raw_edges[a.key]),
                source="XLSB operations; BOM; arcs; capacity_at_arc")
        for g in net.groups:
            for o in g.orders:
                yield dict(input_item=o.vin,output_item=o.vin,operation_node=o.node,
                    operation_type="CUSTOMER_OUTFLOW",operation_destination="",
                    input_quantity=1,output_quantity=1,operation_lead_time=None,operation_capacity_by_period="",
                    production_lead_time=None,production_capacity=None,inventory_location=o.node,
                    downstream_transport_arcs="",transport_lead_time=None,compatible_BOM_groups=g.id,
                    source="XLSB operations(zp8) and demands; V3 order balance; no customer transport arc")

    stats,candidates = Counter(),[]
    def eligibility():
        for item,group in items.items():
            parent = sorted(parents[item])
            child = sorted(children[item])
            # Large reverse joins have their full membership in the graph and
            # raw BOM. Compact references prevent hundreds of repeated MB.
            parent_display = "|".join(parent) if len(parent)<=50 else f"SEE_GRAPH:input_item={item};count={len(parent)}"
            for node in nodes:
                key = node,item
                q, ub = raw_inventory.get(key,(None,None))
                jit = node==OEM and group=="seat"
                model_key = (node,group_of.get(item,item)) in net.initial
                storage = 0 if jit else ub
                if group=="car":
                    allowed = "INELIGIBLE"
                    feasibility = "ORDER_SPECIFIC_FINISHED_STATE" if links[key] else "NO_NETWORK_STATE"
                    reason = "VIN-specific order output outside material buffer eligibility"
                elif not links[key] and key not in raw_inventory:
                    allowed,feasibility,reason = "INELIGIBLE","NO_NETWORK_STATE","No qualified item-node operation or stock state"
                elif jit or ub==0:
                    allowed,feasibility,reason = "INELIGIBLE","ZERO_BASELINE_CAPACITY","Source-case JIT zero at OEM"
                elif ub is not None:
                    allowed,feasibility,reason = "ELIGIBLE","SOURCE_MODEL_STORAGE","Opening and ceiling explicitly listed"
                elif key in CALIBRATION or incoming[key]:
                    allowed,feasibility,reason = "CONDITIONAL","WAREHOUSE_CAPACITY_UNVERIFIED","Reachable state but no source storage ceiling"
                else:
                    allowed,feasibility,reason = "UNKNOWN","BUFFER_STORAGE_UNVERIFIED","Flow-through or purchase state with no warehouse evidence"
                extended = "CONDITIONAL" if jit and incoming[key] else allowed
                row = dict(item_id=item,item_group=group,node_id=node,
                    node_type=NODE_TYPE.get(node,node.rsplit("_",1)[-1].upper()),
                    initial_inventory=q,model_opening=net.initial.get((node,group_of.get(item,item))) if model_key else None,
                    maximum_inventory=ub,storage_capacity=storage,
                    storage_capacity_evidence="TRANSFORM" if jit else "DIRECT" if ub is not None else "MISSING",
                    associated_operations="|".join(sorted(links[key])),
                    BOM_parent=parent_display,BOM_parent_count=len(parent),BOM_children="|".join(child),
                    raw_identity_row=item in identity,physical_storage_feasibility=feasibility,
                    buffer_eligibility=allowed,extended_eligibility=extended,
                    E_base_certified=allowed=="ELIGIBLE",E_base_conditional=allowed=="CONDITIONAL",
                    E_extended_certified=extended=="ELIGIBLE",E_extended_conditional=extended=="CONDITIONAL",
                    evidence_source="XLSB products/nodes/BOM/operations/arcs/initial_inventories/nodes_inflow; V3 source_base",
                    exclusion_reason=reason,extended_condition="Verified OEM rack/area and risk-preparation capacity" if jit else "")
                stats[group,allowed,extended]+=1
                if extended in ("ELIGIBLE","CONDITIONAL"):
                    candidates.append(row)
                yield row
    write("v3_buffer_eligibility.csv",eligibility())
    write("v3_state_transition_graph.csv",transition_rows())
    write("v3_buffer_eligibility_summary.csv",
          (dict(item_group=g,baseline=b,extended=e,count=n) for (g,b,e),n in sorted(stats.items())))
    for name in ("E_base","E_extended"):
        write(f"v3_{name}.csv",(r for r in candidates if r[f"{name}_certified"] or r[f"{name}_conditional"]))
    economics,reachability,portfolio = [],[],[]
    for row in candidates:
        node,item,group=(row[k] for k in ("node_id","item_id","item_group"))
        key=node,item
        # A path is a material dependency tree. Record every required input,
        # not only a shortest single input edge.
        def upstream(k):
            if k in net.external:
                return dict(state=k,entry="SOURCE_EXTERNAL",lead=0,arcs=[])
            a,recipe = incoming[k][0]
            inputs=[upstream((a.origin,p)) for p,q in recipe]
            return dict(state=k,operation="->".join(a.key),capacity_61_74=a.capacity,
                lead=a.lead+max(x["lead"] for x in inputs),
                arcs=[a.key,*dict.fromkeys(k for x in inputs for k in x["arcs"])],
                inputs=[dict(item=p,qty=int(q),path=v) for (p,q),v in zip(recipe,inputs,strict=True)])
        path=upstream(key)
        path_arcs=[arcs[k] for k in path["arcs"]]
        production=[a for a in path_arcs if a.origin.endswith("_prod")]
        transport=[a for a in path_arcs if a.origin.endswith(("_trans","_inv"))]
        children_at_source = [(a,p,q) for a in production for p,q in
                              (a.recipes.get(item,()) or (a.recipes[PACK] if PACK in a.recipes else ()))]
        available_positive=(row["initial_inventory"] or 0)>0
        reference,unit=CALIBRATION.get(key,(None,None))
        ext_jit=row["buffer_eligibility"]=="INELIGIBLE"
        risks=[RISK[a.key] for a in path_arcs if a.key in RISK]
        economics.append(dict(node_id=node,item_id=item,item_group=group,
            K_np=row["storage_capacity"],K_np_basis=row["storage_capacity_evidence"],
            K_np_physical_verified=None,K_np_physical_basis="MISSING",
            c_np=None,c_np_basis="MISSING",h_np=None,h_np_basis="MISSING",c_prod=None,c_prod_basis="MISSING",
            c_trans=None,c_trans_basis="MISSING",reference_cost=reference,reference_cost_basis="CALIBRATE" if reference else "MISSING",
            reference_cost_unit=unit,reference_cost_source="D4 preflight.json normalized experimental cost" if reference else "",
            lead_prod=sum(a.lead for a in production) if production else None,
            lead_prod_basis="TRANSFORM" if production else "MISSING",
            lead_trans=sum(a.lead for a in transport) if transport else None,
            lead_trans_basis="TRANSFORM" if transport else "MISSING",
            prep_capacity=None,prep_capacity_basis="MISSING",
            trans_capacity=None,trans_capacity_basis="MISSING",
            operational_capacity_61_74=compact({"->".join(a.key):a.capacity for a in path_arcs}),
            operational_capacity_basis="DIRECT",extension_requires_new_storage=ext_jit))
        known = row["initial_inventory"]
        reachability.append(dict(node_id=node,item_id=item,item_group=group,
            network_path="STRUCTURALLY_REACHABLE",source_to_position_lead=path["lead"],lead_basis="TRANSFORM",
            path_and_inputs=compact(path),latest_source_start_for_t60=60-path["lead"],
            risk_reveal_t=61,last_pre_reveal_t=60,window_data="XLSB capacity only t61–74",
            observed_opening=known,existing_stock_status="CERTIFIED_AS_OBSERVED" if available_positive else
                                  "NO_POSITIVE_OBSERVED_STOCK" if known is not None else "MISSING",
            in_window_fixed_receipt=compact({t:q for (n,p,t),q in SOURCE.OPENING.items() if (n,p)==key}),
            upstream_opening_for_known_recipes=compact({f"{a.origin}:{p}":raw_inventory.get((a.origin,p),(None,None))[0]
                                                       for a,p,q in children_at_source}),
            additional_prep="NOT_CERTIFIED",quantity_certified_additional=0,physical_maximum=None,
            prep_calendar_status="MISSING",upstream_incremental_material_status="NOT_CERTIFIED",
            prep_production_status="NOT_CERTIFIED",prep_transport_status="NOT_CERTIFIED",
            intermediate_storage_status="NO_CERTIFIED_PRE_REVEAL_HEADROOM",
            final_storage_status="MISSING_PHYSICAL_CAPACITY",
            missing="pre-t61 timing/calendar; uncommitted upstream stock; spare production/transport; physical storage",
            exposure_bypassed_if_stock_already_in_place="|".join(risks),
            active_D4_seat_exposure_bypassed=key==(OEM,item) and group=="seat"))
        portfolio.append(dict(branch=group,material_state=item,node=node,eligible=row["buffer_eligibility"],
            extended=row["extended_eligibility"],capacity=row["storage_capacity"],capacity_basis=row["storage_capacity_evidence"],
            cost=None,cost_basis="MISSING",normalized_reference=reference,prep_feasible="NOT_CERTIFIED",
            D4_exposure="BYPASSES_ACTIVE_SEAT_DELIVERY_IF_CERTIFIED" if ext_jit else
                        "UPSTREAM_OF_ACTIVE_SEAT_DELIVERY" if group in ("seat","seat_componment") else
                        "NO_DIRECT_EFFECT_ON_ACTIVE_SEAT_CAP",
            other_frozen_risk_bypass="|".join(risks)))
    write("v3_buffer_economic_feasibility.csv",economics)
    write("v3_preparation_reachability.csv",reachability)
    write("v3_buffer_portfolio.csv",portfolio)
    summary = dict(items=len(items),nodes=len(nodes),item_node_rows=sum(stats.values()),
        network_arcs=len(arcs),raw_operations=len(tables["operations"]),raw_bom_rows=len(tables["BOM"]),
        self_identity_bom_rows=len(identity),expanded_graph_rows=len(transitions)+28000,
        vin_groups=len(net.groups),unique_vehicle_signatures=len({g.representative.bom for g in net.groups}),
        bev=sum(len(g.orders) for g in net.groups if (PACK,1) in g.representative.bom),
        baseline=dict(Counter({b:sum(n for (g,i,e),n in stats.items() if i==b) for _,b,_ in stats})),
        extended=dict(Counter({e:sum(n for (g,b,i),n in stats.items() if i==e) for _,_,e in stats})),
        audited_economic_candidates=len(candidates),positive_additional_preparation_certified=0,
        missing_cost_entries=len(candidates),raw_inventory_rows=len(raw_inventory))
    dump("v3_inventory_audit_summary.json",summary)
    print(compact(summary),flush=True)


if __name__=="__main__":
    main()
