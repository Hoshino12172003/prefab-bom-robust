"""Test a one-dimensional due-prefix relaxation against exact joint service."""
import os
from collections import Counter

import gurobipy as gp
from gurobipy import GRB

import run_matrix as run
from design import HERE, LABEL, PERIODS, scenarios


def prefixes(base, opening, scenario, x):
    arrivals, factors = run.data_for(scenario, opening, base)
    log = HERE / "logs" / f"scalar_prefix_{scenario.name}__K644_C.log"
    log.write_text("", encoding="utf-8")
    with run.env() as env, gp.Model(scenario.name, env=env) as model:
        run.configure(model)
        model.Params.LogFile = os.path.relpath(log)
        block = run.add_block(model, base, scenario.name, run.Weights(0, 0, 0, 0, 0),
                              reschedule=True, fixed_receipts=arrivals, arc_factors=factors,
                              protection=run.protection_inventory(x))
        cohorts = base.network.groups
        by_due = {due: gp.quicksum(block.outflow[g.id, t] for g in cohorts
                                   if g.representative.due == due for t in PERIODS if t <= due)
                  for due in PERIODS}
        cumulative = gp.LinExpr()
        bounds = {}
        for due in PERIODS:
            cumulative += by_due[due]
            model.setObjective(cumulative, GRB.MAXIMIZE)
            model.optimize()
            assert model.Status == GRB.OPTIMAL and model.MIPGap == 0
            bounds[due] = round(model.ObjVal)
            assert bounds[due] == model.ObjVal == model.ObjBound
        return bounds


def main():
    run.verify_frozen()
    run.init()
    base, opening = run.BASE, run.OPENING
    x = (915, 0, 0)
    net = base.network
    protection = run.protection_inventory(x)
    receiving_headroom = []
    for item in run.CELL:
        key = run.PROD, item
        assert key not in net.external
        inflow_bound = sum(sum(a.capacity.values()) for a in net.arcs if a.destination == run.PROD
                           and item in a.recipes)
        total = net.initial[key] + protection[key] + inflow_bound + sum(
            quantity for (node, sku, _), quantity in opening.items() if (node, sku) == key)
        receiving_headroom.append(net.inventory_bounds[key][1] - total)
    assert min(receiving_headroom) >= 0
    selected = {s.name: s for s in scenarios()}
    bounds = [prefixes(base, opening, selected[key], x) for key in ("B_RECEIPT_1", "S_1")]
    direct = next(int(r["Q_direct"]) for r in run.read(HERE/"runs/BS.csv") if r["policy_id"] == "K644_C")
    daily_demand = Counter()
    for group in base.network.groups:
        daily_demand[group.representative.due] += len(group.orders)
    rows = []
    relaxed = 0
    for t in PERIODS:
        upper = min(b[t] for b in bounds)
        assert relaxed <= upper
        relaxed = min(upper, relaxed + daily_demand[t])
        rows.append(dict(label=LABEL, policy_id="K644_C", scenario_id="BS", due_period=t,
                         due_demand=daily_demand[t], isolated_battery_prefix_optimum=bounds[0][t],
                         isolated_seat_prefix_optimum=bounds[1][t], scalar_covering_dp=relaxed,
                         exact_joint_total=direct, restored_receipts_storage_headroom=min(receiving_headroom)))
    run.write("scalar_covering_prefix_dp.csv", rows)
    print(f"Scalar covering DP {relaxed}; exact joint {direct}; difference {relaxed-direct}")


if __name__ == "__main__":
    main()
