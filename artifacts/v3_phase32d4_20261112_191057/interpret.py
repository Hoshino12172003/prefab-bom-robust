"""Rebuild exact worst-case witnesses and audit service bottlenecks by SKU and VIN cohort."""

from collections import Counter

import gurobipy as gp
import numpy as np
from gurobipy import GRB

from prefab_v3 import plain_ccg
from prefab_v3.base import ASSEMBLY
from prefab_v3.e4_ccg import Prefix, SEAT
from prefab_v25.data import OEM

from run import HERE, SOURCE, Coordinates, certified_event, frozen_catalog, read
from recourse import Recourse


def main():
    SOURCE.init()
    coords = Coordinates()
    net = SOURCE.BASE.network
    arcs = {a.key:a for a in net.arcs}
    capacity_rows, bom_rows, group_rows, events = [], [], [], []
    prefix = Prefix(SOURCE.BASE)
    with SOURCE.env() as env:
        for gamma in (1,2,3):
            out = HERE / f"outer/G{gamma}"
            r = read(out / "result.json")
            final, x = r["final_oracle"], tuple(r["policy"])
            code, profile, exposure = certified_event(coords, final)
            arrivals, factors = profile
            with np.load(out / "final_oracle/worst_witness.npz") as witness:
                vector = witness["vector"]
                assert int(witness["rhs_id"]) == int(code)
            checker = Recourse(env,SOURCE.BASE,SOURCE.OPENING,coords,x,HERE / "interpret" / f"G{gamma}")
            try:
                checker.matrix_check(vector,checker.rhs(coords.code_profile(int(code))))
                assert vector[checker.objective_idx].sum() == r["objective"]
                block = checker.block
                due = Counter()
                seats = arcs[SEAT].recipes
                for g in net.groups:
                    d = g.representative.due
                    due[d] += len(g.orders)
                    q = sum(int(vector[block.outflow[g.id,t].index]) for t in net.periods if t<=d)
                    assembly_bom = dict(g.representative.bom)
                    seat = next(p for p in seats if assembly_bom.get(p,0))
                    group_rows.append(dict(gamma=gamma,cohort=g.id,due=d,orders=len(g.orders),on_time=q,
                        gap=len(g.orders)-q,seat_sku=seat,seat_units_per_vehicle=assembly_bom[seat],
                        exposure_class="STRUCTURAL_SEAT_BOM_REACH"))
                limiting = []
                supplied, due_prefix = 0, 0
                for t in net.periods:
                    seat_cap = int(arcs[SEAT].capacity[t]*factors.get((*SEAT,t),1))
                    supplied += min(arcs[ASSEMBLY].capacity[t],seat_cap+sum(arrivals.get((OEM,p,t),0) for p in seats))
                    due_prefix += due[t]
                    if net.demand_weight-due_prefix+supplied==r["objective"]:
                        limiting.append(t)
                    for arc_key in (SEAT,ASSEMBLY):
                        cap = int(arcs[arc_key].capacity[t]*factors.get((*arc_key,t),1))
                        used = sum(int(vector[block.flow[(*arc_key,p,t)].index]) for p in arcs[arc_key].recipes)
                        capacity_rows.append(dict(gamma=gamma,arc="->".join(arc_key),period=t,capacity=cap,
                                                   used=used,slack=cap-used,binding=cap==used))
                    for p in sorted(seats):
                        use = sum(int(vector[block.flow[(*ASSEMBLY,g.id,t)].index])
                                  for g in net.groups if (p,1) in g.representative.bom)
                        stock = int(vector[block.inventory[OEM,p,t].index])
                        incoming = int(vector[block.flow[(*SEAT,p,t)].index])+arrivals.get((OEM,p,t),0)
                        assert stock==0 and use==incoming
                        bom_rows.append(dict(gamma=gamma,node=OEM,sku=p,period=t,received=incoming,
                                             consumed=use,closing_inventory=stock,
                                             binding_positive_flow=use>0,mechanism="JIT_ZERO_STOCK_BOM_BALANCE"))
                assert limiting and prefix.upper(profile,x)[1]==r["objective"]
                assert sum(row["on_time"] for row in group_rows if row["gamma"]==gamma)==r["objective"]
                nominal = coords.nominal
                for event in final["worst_event_details"]:
                    atom=coords.by_id[event["event_id"]]
                    effect = sum(a!=b for a,b in zip(atom.profile,nominal,strict=True))
                    events.append(dict(gamma=gamma,rhs=code,exposure_resource_days=exposure,
                        limiting_prefix="|".join(map(str,limiting)),affected_vin_groups=len(net.groups) if effect else 0,
                        affected_vins=net.demand_weight if effect else 0,effective_rhs_rows=effect,
                        **event))
            finally:
                checker.close()
    for name,rows in (("gamma_worst_event_comparison.csv",events),("binding_capacity_rows.csv",capacity_rows),
                      ("binding_bom_components.csv",bom_rows),("affected_vin_groups.csv",group_rows)):
        frozen_catalog.write(HERE / name,rows)
    print("Verified worst-event matrix, capacity and JIT BOM evidence for Gamma 1/2/3",flush=True)


if __name__=="__main__":
    main()
