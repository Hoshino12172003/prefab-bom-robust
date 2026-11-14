"""Integer recourse with source operations and a shared pre-risk buffer."""
from collections import defaultdict
from math import isfinite
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

from .data import BUFFER_EFFECTS, BUFFER_NAMES, NOMINAL, receipts

TOL = 1e-7


def initial_state(network, buffers):
    state = {key: network.initial.get(key, 0) for key in network.state_keys()}
    for quantity, effects in zip(buffers, BUFFER_EFFECTS):
        for key, coefficient in effects:
            state[key] += coefficient * quantity
    return state


def _block(model, network, scenario, state, historical, prefix):
    periods = network.periods
    inventory = model.addVars([(*key, t) for key in state for t in periods],
                              vtype=GRB.INTEGER, name=f"{prefix}_I")
    supply = model.addVars([(*key, t) for key in network.external for t in periods],
                           vtype=GRB.INTEGER, name=f"{prefix}_in")
    dispatch = model.addVars([(*arc.key, item, t) for arc in network.arcs
                              for item in arc.recipes for t in periods],
                             vtype=GRB.INTEGER, name=f"{prefix}_q")
    service = model.addVars([(g.id, t) for g in network.groups for t in periods],
                            vtype=GRB.INTEGER, name=f"{prefix}_y")
    changes = defaultdict(gp.LinExpr)
    for arc in network.arcs:
        for t in periods:
            total = gp.quicksum(dispatch[(*arc.key, item, t)] for item in arc.recipes)
            model.addConstr(total <= float(arc.capacity[t]*scenario.factor(arc.key,t)))
            group_cap = network.group_caps.get((*arc.key,t))
            if group_cap is not None:
                model.addConstr(total <= group_cap)
            for item, recipe in arc.recipes.items():
                key = (*arc.key,item,t)
                q = dispatch[key]
                if key in network.product_caps:
                    model.addConstr(q <= network.product_caps[key])
                for child, coefficient in recipe:
                    changes[arc.origin,child,t] -= coefficient*q
                if t+arc.lead in periods:
                    changes[arc.destination,item,t+arc.lead] += q
    weighted = gp.LinExpr()
    for g in network.groups:
        order = g.representative
        model.addConstr(gp.quicksum(service[g.id,t] for t in periods) <= len(g.orders))
        for t in periods:
            y = service[g.id,t]
            changes[order.node,g.id,t] -= y
            if t <= order.due:
                weighted += order.weight*y
    for node,item in state:
        last = state[node,item]
        for t in periods:
            key = (node,item,t)
            model.addConstr(inventory[key] == last + historical.get(key,0)
                            + supply.get(key,0) + changes[key])
            last = inventory[key]
            if (node,item) in network.inventory_bounds:
                last.LB, last.UB = network.inventory_bounds[node,item]
    return inventory, supply, dispatch, service, weighted


def _audit(network, scenario, state, inventory, supply, dispatch, service):
    """Replay scheduled shipments and BOM consumption using numeric ledgers."""
    balance = dict(state)
    arrival = receipts(network, scenario)
    transit = defaultdict(int)
    max_balance = 0
    max_capacity = 0
    for t in network.periods:
        for node,item in balance:
            key = (node,item,t)
            balance[node,item] += arrival.get(key,0) + supply.get(key,0) + transit[key]
        for arc in network.arcs:
            total = 0
            for item, recipe in arc.recipes.items():
                key = (*arc.key,item,t)
                quantity = dispatch[key]
                total += quantity
                max_capacity = max(max_capacity, quantity-network.product_caps.get(key,quantity))
                for child, coefficient in recipe:
                    balance[arc.origin,child] -= coefficient*quantity
                if arc.lead == 0:
                    balance[arc.destination,item] += quantity
                else:
                    transit[arc.destination,item,t+arc.lead] += quantity
            allowed = arc.capacity[t]*scenario.factor(arc.key,t)
            max_capacity = max(max_capacity, float(total-allowed),
                               total-network.group_caps.get((*arc.key,t),total))
        for g in network.groups:
            balance[g.representative.node,g.id] -= service[g.id,t]
        for (node,item), quantity in balance.items():
            minimum, maximum = network.inventory_bounds.get((node,item),(0,float("inf")))
            max_balance = max(max_balance, abs(inventory[node,item,t]-quantity),
                              minimum-quantity, quantity-maximum)
    order_residual = max([0, *(sum(service[g.id,t] for t in network.periods)-len(g.orders)
                               for g in network.groups)])
    on_time = sum(g.representative.weight*service[g.id,t] for g in network.groups
                  for t in network.periods if t <= g.representative.due)
    return {"max_balance_residual": max_balance, "max_capacity_residual": max_capacity,
            "max_order_residual": order_residual, "weighted_on_time": on_time}


def _solve(network, scenarios, budget, costs, de, fixed_buffers=None, time_limit=30, log=None,
           threads=1, formal=None):
    if network.source_sha256 is not None:
        from .formal import frozen_runs
        if formal is None:
            raise ValueError("paper-scale solve requires the frozen paper_scale_v2 manifest")
        payload, run_id = formal
        if not any((run.id, run.de, run.budget, run.costs, run.scenarios) ==
                   (run_id, de, budget, costs, scenarios) for run in frozen_runs(payload)) or fixed_buffers is not None:
            raise ValueError("requested run is outside the frozen matrix")
    if len(costs) != 3 or any(not isfinite(c) or c <= 0 for c in costs):
        raise ValueError("three positive finite buffer costs required")
    if not isfinite(budget) or budget < 0 or network.demand_weight <= 0:
        raise ValueError("nonnegative budget and positive demand required")
    if not scenarios or len({s.name for s in scenarios}) != len(scenarios):
        raise ValueError("finite scenario list must be nonempty with unique names")
    for scenario in scenarios:
        scenario.validate(network.periods)
    historical = [receipts(network, scenario) for scenario in scenarios]
    if fixed_buffers is not None and (
        len(fixed_buffers) != 3 or any(type(v) is not int or v < 0 for v in fixed_buffers)
    ):
        raise ValueError("three nonnegative integer fixed buffers required")
    with gp.Model("V25_DE" if de else "V25_nominal") as model:
        model.Params.OutputFlag = 0
        model.Params.LogToConsole = 0
        if log is not None:
            model.Params.OutputFlag = 1
        model.Params.Threads = threads
        model.Params.Seed = 20261110
        model.Params.MIPGap = model.Params.MIPGapAbs = 0
        model.Params.FeasibilityTol = model.Params.IntFeasTol = 1e-9
        model.Params.TimeLimit = time_limit
        buffers = [model.addVar(vtype=GRB.INTEGER, name=name) for name in BUFFER_NAMES]
        model.addConstr(gp.quicksum(c*x for c,x in zip(costs,buffers)) <= budget)
        if fixed_buffers is not None:
            for var, value in zip(buffers,fixed_buffers):
                var.LB = var.UB = value
        state = initial_state(network, buffers)
        blocks = [_block(model,network,scenario,state,arrivals,f"s{i}")
                  for i,(scenario,arrivals) in enumerate(zip(scenarios,historical))]
        if de:
            rho = model.addVar(lb=0,ub=1,name="rho")
            for block in blocks:
                model.addConstr(block[-1] >= network.demand_weight*rho)
            model.setObjective(rho, GRB.MAXIMIZE)
        else:
            model.setObjective(blocks[0][-1]/network.demand_weight, GRB.MAXIMIZE)

        def log_callback(m, where):
            if where == GRB.Callback.MESSAGE:
                stream.write(m.cbGet(GRB.Callback.MSG_STRING))

        if log is None:
            model.optimize()
        else:
            with Path(log).open("w",encoding="utf-8") as stream:
                model.optimize(log_callback)
        result = {"status": {2:"OPTIMAL",3:"INFEASIBLE",9:"TIME_LIMIT"}.get(model.Status,str(model.Status)),
                  "seconds": model.Runtime, "certified": False, "variables": model.NumVars,
                  "integer_variables": model.NumIntVars, "constraints": model.NumConstrs,
                  "nodes": model.NodeCount, "solutions": model.SolCount, "threads": threads,
                  "time_limit_seconds": time_limit}
        if not model.SolCount:
            return result
        result.update(objective=model.ObjVal, bound=model.ObjBound, gap=model.MIPGap)
        raw_buffers = [x.X for x in buffers]
        result["buffers"] = dict(zip(BUFFER_NAMES,map(round,raw_buffers)))
        result["budget_residual"] = max(0, sum(c*x for c,x in zip(costs,raw_buffers))-budget)
        numeric_state = initial_state(network,raw_buffers)
        result["quality_residual"] = max(model.ConstrVio,model.BoundVio,model.IntVio,result["budget_residual"])
        result["scenarios"] = {}
        for scenario, block in zip(scenarios,blocks):
            inventory, supply, dispatch, service = [{k:v.X for k,v in variables.items()} for variables in block[:4]]
            audit = _audit(network,scenario,numeric_state,inventory,supply,dispatch,service)
            audit["service_ratio"] = audit["weighted_on_time"]/network.demand_weight
            audit["rho_residual"] = max(0, model.ObjVal-audit["service_ratio"])
            result["quality_residual"] = max(result["quality_residual"],
                                             *(v for k,v in audit.items() if k.endswith("_residual")))
            result["scenarios"][scenario.name] = {
                **audit,"initial":numeric_state, "inventory":inventory,"dispatch":dispatch,
                "supply":supply,"deliveries":service,
            }
        result["certified"] = (model.Status == GRB.OPTIMAL and abs(model.ObjVal-model.ObjBound) <= TOL
                               and result["quality_residual"] <= TOL)
        return result


def nominal(network, budget, costs, **kwargs):
    return _solve(network,(NOMINAL,),budget,costs,de=False,**kwargs)


def extensive(network, scenarios, budget, costs, **kwargs):
    return _solve(network,tuple(scenarios),budget,costs,de=True,**kwargs)
