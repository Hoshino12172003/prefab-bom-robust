"""Read-only operating-plan and material-cut audits for Gate 3.5."""

from collections import Counter, defaultdict
from fractions import Fraction

import gurobipy as gp

from network import ASSEMBLY, CELL, TOL, solve
from numerical_certification import kind


def recourse(env, op, bounds, seat, pool, b, profile, label):
    opening = {k: q + b.get(k, 0) for k, q in op.initial.items()}
    with gp.Model(label, env=env) as model:
        block = op.add(model, "audit", profile, opening, bounds, seat, pool)
        info = solve(model, block[-1])
        assert info["exact"], (label, info)
        ot, balance, capacity = op.replay(model, block, opening, bounds, seat, pool, profile,
                                         label, label, defaultdict(list))
        assert abs(ot - info["objective"]) <= TOL
        flows = model.getAttr("X", block[0])
        stock = model.getAttr("X", block[1])
    usage, delivered = Counter(), Counter()
    for (i,j,p,t), q in flows.items():
        usage[i,j,t] += q
        if (i,j) == ASSEMBLY:
            delivered[p,t] += q
    return dict(on_time=ot, service=ot/op.demand, balance_residual=balance, capacity_violation=capacity, **info), flows, stock, usage, delivered


def nominal_bottlenecks(op, bounds, seat, pool, solution, policy):
    _, flows, stock, usage, _ = solution
    skus = defaultdict(set)
    for (i,j,p,t), q in flows.items():
        if q > TOL:
            skus[i,j,t].add(p)

    def entry(category, resource, t, limit, used, products):
        slack = limit - used
        assert slack >= -TOL
        return dict(policy=policy, category=category, resource=resource, period=t, nominal_capacity=limit,
                    actual_usage=used, slack=slack, utilization=used/limit if limit else "",
                    binding=abs(slack)<=TOL, relevant_products=";".join(sorted(products)))

    for (i,j,t), limit in op.nominal.items():
        arc = op.arcs[i,j]
        category = "final_assembly" if (i,j)==ASSEMBLY else kind(arc)
        products = skus[i,j,t] if category == "final_assembly" else arc.recipes
        yield entry(category, f"{i}->{j}", t, limit, usage[i,j,t], products)
    net = op.base.network
    for (i,j,p,t), limit in net.product_caps.items():
        yield entry("max_flow_product", f"{i}->{j}:{p}", t, limit, flows.get((i,j,p,t),0), [p])
    for (i,j,t), limit in net.group_caps.items():
        yield entry("max_flow_group", f"{i}->{j}", t, limit, usage[i,j,t], op.arcs[i,j].recipes)
    for (n,p,t), q in stock.items():
        yield entry("inventory_upper", f"{n}:{p}", t, bounds[n,p][1], q, [p])
    for t in op.periods:
        yield entry("inventory_shared", "zp7:Seat", t, pool, sum(stock[n,p,t] for n,p in seat), [p for _,p in seat])


def battery_cut(op, nominal, alpha, horizon):
    prod, inv, oem = "battery-supplier_prod", "battery-supplier_inv", "zp7"
    inbound = ("battery-supplier_trans", prod)
    pack = (prod, inv)
    to_oem = (inv, oem)
    horizon_end = op.periods[-1]
    cell_last = horizon_end - op.arcs[pack].lead - op.arcs[to_oem].lead
    assert op.periods[0] + op.arcs[inbound].lead > cell_last
    source_stocks = [op.initial[prod,p] for p in CELL]
    usable_arrivals = [sum(op.history.get((prod,p,t),0) for t in op.periods if t <= cell_last) for p in CELL]
    late_arrivals = [sum(op.history.get((prod,p,t),0) for t in op.periods if t > cell_last) for p in CELL]
    recipe = dict(op.arcs[pack].recipes["BEV"])
    kit_opening = min(int(q//recipe[p]) for p,q in zip(CELL,source_stocks))
    kit_arrivals = min(int(q//recipe[p]) for p,q in zip(CELL,usable_arrivals))
    assert all(q == kit_opening * recipe[p] for p,q in zip(CELL,source_stocks))
    assert all(q == kit_arrivals * recipe[p] for p,q in zip(CELL,usable_arrivals))
    gross_pack = {n:op.initial[n,"BEV"] + sum(op.history.get((n,"BEV",t),0) for t in op.periods
                 if t <= horizon_end - (op.arcs[to_oem].lead if n == inv else 0)) for n in (inv,oem)}
    slots = max(0,horizon-op.arcs[inbound].lead+1)
    prep_capacity = int(alpha*nominal[inbound])
    prep_kit_bound = slots * prep_capacity // sum(recipe.values())
    bev_demand = sum(len(g.orders) for g in op.groups.values() if ("BEV",1) in g.representative.bom)
    base_bev_cap = kit_opening + kit_arrivals + sum(gross_pack.values())
    return dict(cell_last_usable=cell_last, cell_opening=source_stocks, cell_usable_receipts=usable_arrivals,
                cell_late_receipts=late_arrivals, historical_pack_at_oem=gross_pack[oem], historical_pack_at_t1=gross_pack[inv],
                opening_kits=kit_opening, usable_receipt_kits=kit_arrivals, bev_demand=bev_demand,
                nonbev_demand=op.demand-bev_demand, nominal_bev_bound=base_bev_cap,
                nominal_on_time_bound=op.demand-bev_demand+base_bev_cap, prep_slots=slots, prep_cell_units_per_slot=prep_capacity,
                prep_total_cells=slots*prep_capacity, prep_kit_bound=int(prep_kit_bound),
                positive_on_time_bound=int(op.demand-bev_demand+base_bev_cap+prep_kit_bound))


def period_effect(op, event, nominal_usage, event_usage):
    for k, rate in event.profile(op.periods).items():
        cap = op.nominal[k] * rate
        use = event_usage[k]
        structurally_active = any((i,j,t) == k for i,j,_,t in op.keys)
        yield dict(period=k[-1], multiplier=str(rate), nominal_capacity=op.nominal[k], nominal_usage=nominal_usage[k],
                   effective_capacity=float(cap), integer_capacity=int(cap), event_usage=use,
                   horizon_eligible=structurally_active,
                   nominal_witness_excluded=nominal_usage[k] > int(cap)+TOL,
                   disruption_binds=structurally_active and int(cap)<op.nominal[k] and abs(use-int(cap))<=TOL)
