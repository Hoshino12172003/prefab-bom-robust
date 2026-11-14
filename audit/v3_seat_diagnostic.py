"""Independent one-scenario Seat preparation diagnostics."""

from collections import Counter
import os

import gurobipy as gp
from gurobipy import GRB

from v3_audit_context import OUT, ROOT, SOURCE, dump, load, terminal, verify_inputs, write
from prefab_v3.base import Weights, add_block
from prefab_v3.e4_ccg import SEAT
from prefab_v3.robust import on_time, protection_inventory
from prefab_v25.data import OEM


def run_case(env, base, policy, profile, case, mode, assumed_prep=None):
    network = base.network
    t1 = network.periods[0]
    supply_arc = next(a for a in network.arcs if a.key == SEAT)
    prod_arc = next(a for a in network.arcs if a.key == ("seat-supplier_prod", SEAT[0]))
    skus = tuple(sorted(supply_arc.recipes))
    assert prod_arc.lead == supply_arc.lead == 0
    assert all(supply_arc.recipes[p] == ((p,1),) for p in skus)
    assert all(len(prod_arc.recipes[p]) == 1 and prod_arc.recipes[p][0][1] == 1 for p in skus)
    assert all((OEM,p) not in network.initial or network.initial[OEM,p] == 0 for p in skus)
    assert not any(n == OEM and p in skus for n,p,_ in profile[0])
    assert all((OEM,p) not in network.external for p in skus)
    gross = {p:network.initial[prod_arc.origin,prod_arc.recipes[p][0][0]] for p in skus}
    assert sum(gross.values()) == 6000
    stages = []
    with gp.Model(case, env=env) as model:
        SOURCE.configure(model, seconds=120)
        path = OUT / "logs" / f"{case}.log"
        path.parent.mkdir(exist_ok=True)
        path.write_text("",encoding="utf-8")
        model.Params.LogFile = os.path.relpath(path, ROOT)
        stock, make, ship = {}, {}, {}
        regular, buffers = dict(network.initial), protection_inventory(policy)
        if mode != "baseline":
            stock = {p:model.addVar(vtype=GRB.INTEGER,ub=gross[p] if assumed_prep else 0,name=f"pre_{p}")
                     for p in skus}
            make = {p:model.addVar(vtype=GRB.INTEGER,ub=gross[p],name=f"make_{p}") for p in skus}
            ship = {p:model.addVar(vtype=GRB.INTEGER,ub=gross[p],name=f"ship_{p}") for p in skus}
            for p in skus:
                # Zero leads allow a single pre-reveal slot only if residual
                # capacity for that slot is independently available.
                model.addConstr(make[p] == ship[p],name=f"supplier_no_overnight_staging_{p}")
                model.addConstr(ship[p] == stock[p],name=f"pre_reveal_arrival_{p}")
                child, units = prod_arc.recipes[p][0]
                key = prod_arc.origin,child
                regular[key] -= float(units)*make[p]
                model.addConstr(regular[key]>=0,name=f"existing_component_stock_{p}")
                buffers[OEM,p] = stock[p]
            cap = assumed_prep or 0
            model.addConstr(gp.quicksum(make.values())<=cap,name="preparation_production_capacity")
            model.addConstr(gp.quicksum(ship.values())<=cap,name="preparation_transport_capacity")
            model.addConstr(gp.quicksum(stock.values())<=cap,name="preparation_oem_storage_capacity")
        block = add_block(model,base,"recourse",Weights(0,0,0,0,0),reschedule=True,regular=regular,
                          fixed_receipts=profile[0],arc_factors=profile[1],protection=buffers)
        if assumed_prep:
            # Only the hypothetical prepositioned stock may carry forward.
            # Other post-reveal Seat deliveries remain same-period JIT.
            for p in skus:
                prior = stock[p]
                for t in network.periods:
                    inv = block.inventory[OEM,p,t]
                    inv.UB = assumed_prep
                    model.addConstr(inv<=prior,name=f"no_post_reveal_replenishment_of_buffer_{p}_{t}")
                    prior = inv
            for t in network.periods:
                model.addConstr(gp.quicksum(block.inventory[OEM,p,t] for p in skus)<=assumed_prep)
        score = on_time(block,base)
        complete = gp.quicksum(block.outflow.values())
        qty = gp.quicksum(stock.values())

        def solve(label, expression, sense=GRB.MAXIMIZE):
            model.setObjective(expression,sense)
            model.optimize()
            assert model.Status==GRB.OPTIMAL and model.ObjVal==model.ObjBound and model.MIPGap==0, (case,label,model.Status)
            v,res = SOURCE.exact_vector(model,SOURCE.matrix_rows(model))
            objective = int(model.ObjVal)
            assert objective == model.ObjVal
            stages.append(dict(stage=label,objective=objective,bound=model.ObjBound,gap=model.MIPGap,
                               status="OPTIMAL",solver_residual=res,matrix_residual=0,seconds=model.Runtime))
            return objective,v

        if case == "C4_MIN_PLUS_ONE":
            model.addConstr(score>=11776,name="one_extra_on_time_vehicle")
            required,_ = solve("minimum_preposition_for_one_more",qty,GRB.MINIMIZE)
            model.addConstr(qty==required)
        z,_ = solve("max_on_time",score)
        if case == "C0":
            assert z == 11775, "Frozen C0 not reproduced, stop before counterfactuals"
        model.addConstr(score==z)
        total,v = solve("max_total_given_on_time",complete)
        if assumed_prep:
            model.addConstr(complete==total)
            _,v = solve("min_stock_given_service",qty,GRB.MINIMIZE)
        chosen = {p:int(v[stock[p].index]) if p in stock else 0 for p in skus}
        assert sum(chosen.values()) <= (assumed_prep or 0)
        assert all(chosen[p] <= gross[p] for p in skus)
        assert sum(int(v[var.index]) for var in block.outflow.values()) == total
        seat_dispatch = {str(t):sum(int(v[block.flow[(*SEAT,p,t)].index]) for p in skus) for t in network.periods}
        by_period = {str(t):{p:int(v[block.inventory[OEM,p,t].index]) for p in skus} for t in network.periods}
        affected_periods = [t for t in network.periods if (*SEAT,t) in profile[1]]
        prefix = sum(int(supply_arc.capacity[t]*profile[1][(*SEAT,t)]) for t in affected_periods)
        prefix_bound = prefix+sum(chosen.values())+2000*(len(network.periods)-len(affected_periods))
        assert z <= prefix_bound
        return dict(case=case,scenario_rhs="16106127360",scope=mode,
            preparation_certification="BASELINE" if mode=="baseline" else
                                      "THEORETICAL_ONLY" if assumed_prep else "NOT_CERTIFIED_POSITIVE_STOCK",
            known_OEM_maximum=0 if mode=="baseline" else None,
            assumed_preproduction_and_transport_each=assumed_prep,assumed_oem_storage=assumed_prep,
            on_time=z,total_completed=total,shortage_on_time_fixed_scenario=network.demand_weight-z,
            uncompleted_at_horizon=network.demand_weight-total,required_preposition=sum(chosen.values()),
            certified_positive_preposition=0,**chosen,incremental_inventory_cost=None if assumed_prep else 0,
            additional_transport_cost=None if assumed_prep else 0,
            unit_inventory_cost_status="MISSING",unit_transport_cost_status="MISSING",
            cost_status="MISSING" if assumed_prep else "ZERO_INCREMENT_ZERO_ACTIVITY",
            seat_prefix_upper=prefix_bound,remaining_bottleneck="SEAT_PREFIX_BOUND_TIGHT" if z==prefix_bound else
                "SEAT_PREFIX_BOUND_NOT_TIGHT",log=path.relative_to(ROOT).as_posix(),
            stages=stages,inventory_by_period=by_period,seat_dispatch_by_period=seat_dispatch)


def main():
    identity = verify_inputs()
    _, base = load()
    dump("v3_input_provenance.json",identity)
    policy,profile,_ = terminal()
    with SOURCE.env() as env:
        rows = [run_case(env,base,policy,profile,"C0","baseline")]
        for case,mode in (("C1","pre_reveal_path_only"),("C2","finite_sku_caps_unknown"),
                          ("C3","physical_storage_maximum_unknown")):
            rows.append(run_case(env,base,policy,profile,case,mode))
        rows.append(run_case(env,base,policy,profile,"C4","theoretical_opening_stock_conversion",6000))
        rows.append(run_case(env,base,policy,profile,"C4_MIN_PLUS_ONE","theoretical_minimum",6000))
    assert all(r["on_time"]==11775 and r["required_preposition"]==0 for r in rows[:4])
    assert rows[-1]["on_time"]>=11776 and rows[-1]["required_preposition"]==1
    write("v3_seat_oem_preposition_counterfactual.csv",
          ({k:v for k,v in r.items() if k not in ("stages","inventory_by_period","seat_dispatch_by_period")} for r in rows))
    dump("v3_seat_oem_preposition_detail.json",dict(gurobi=gp.gurobi.version(),policy=policy,
                                                  full_domain_runs=0,results=rows))
    for row in rows:
        print(row["case"],row["on_time"],row["total_completed"],row["required_preposition"],flush=True)


if __name__ == "__main__":
    main()
