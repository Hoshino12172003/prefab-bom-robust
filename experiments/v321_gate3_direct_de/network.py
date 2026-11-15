"""One shared Gate 2C preparation block and a Gate 1 recourse block per trajectory."""

import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

GATE2C = Path(__file__).resolve().parents[1] / "v32_gate2c_joint_preparedness"
sys.path.insert(0, str(GATE2C))
from run_gate2c import prepare, audit as audit_prep, COST, KIT_COST, TOL
from numerical_certification import ASSEMBLY, solve_info
from prefab_v25.data import CELL, NOMINAL, receipts


class Operation:
    def __init__(self, base, states):
        self.base = base
        net = base.network
        self.states = states
        self.periods = net.periods
        self.arcs = {a.key: a for a in net.arcs}
        self.groups = {g.id: g for g in net.groups}
        self.due = {g.id: g.representative.due for g in net.groups}
        self.weight = {g.id: g.representative.weight for g in net.groups}
        self.demand = sum(len(g.orders) * self.weight[g.id] for g in net.groups)
        self.initial = {k: net.initial[k] for k in states}
        self.history = receipts(net, NOMINAL)
        self.nominal = {(*a.key, t): a.capacity[t] for a in net.arcs for t in self.periods}
        # Omit only departures with no use within the operating window, and late deliveries.
        self.keys = [(*a.key, p, t) for a in net.arcs for p in a.recipes for t in self.periods
                     if t + a.lead in self.periods and (a.key != ASSEMBLY or t <= self.due[p])]

    def bounds(self, preparation_limits):
        bounds = dict(self.base.network.inventory_bounds)
        for n,p in self.states.keys() - bounds.keys():
            # A finite operational technical ceiling. The preparation upper bound limits
            # opening stock; after reveal only nominal receipts can add to this ceiling.
            incoming = sum(a.capacity[t] for a in self.arcs.values() if n == a.destination and p in a.recipes
                           for t in self.periods if t + a.lead in self.periods)
            historical = sum(self.history.get((n,p,t), 0) for t in self.periods)
            bounds[n,p] = (0, preparation_limits[n,p][1] + incoming + historical)
        return bounds

    def add(self, model, tag, multipliers, opening, bounds, seat, pool):
        """Build a post-reveal block. Opening may be shared variables or fixed constants."""
        inv = model.addVars([(n,p,t) for n,p in self.states for t in self.periods], vtype=GRB.INTEGER, name=f"{tag}_I")
        flow = model.addVars(self.keys, vtype=GRB.INTEGER, name=f"{tag}_F")
        incoming, consumed = defaultdict(gp.LinExpr), defaultdict(gp.LinExpr)
        for (i,j,p,t), var in flow.items():
            arc = self.arcs[i,j]
            if (i,j) != ASSEMBLY:
                incoming[j,p,t+arc.lead] += var
            for child, q in arc.recipes[p]:
                if (i,child) in self.states:
                    consumed[i,child,t] += float(q)*var
        net = self.base.network
        for (i,j,t), capacity in self.nominal.items():
            total = flow.sum(i,j,"*",t)
            effective = capacity * multipliers.get((i,j,t), Fraction(1))
            model.addConstr(total <= int(effective), name=f"{tag}_capacity[{i},{j},{t}]")
            if (i,j,t) in net.group_caps:
                model.addConstr(total <= net.group_caps[i,j,t], name=f"{tag}_group[{i},{j},{t}]")
        for k, capacity in net.product_caps.items():
            if k in flow:
                model.addConstr(flow[k] <= capacity, name=f"{tag}_product[{','.join(map(str,k))}]")
        balances = {}
        for (n,p), (lower,upper) in bounds.items():
            previous = opening[n,p]
            for t in self.periods:
                k = n,p,t
                inv[k].LB, inv[k].UB = lower,upper
                balances[k] = model.addConstr(inv[k] == previous + self.history.get(k,0) + incoming[k] - consumed[k],
                                               name=f"{tag}_balance[{n},{p},{t}]")
                previous = inv[k]
        for t in self.periods:
            model.addConstr(gp.quicksum(inv[n,p,t] for n,p in seat) <= pool, name=f"{tag}_OEM_seat[{t}]")
        for g, group in self.groups.items():
            model.addConstr(flow.sum(*ASSEMBLY,g,"*") <= len(group.orders), name=f"{tag}_demand[{g}]")
        ot = gp.quicksum(self.weight[g] * var for (i,j,g,_),var in flow.items() if (i,j)==ASSEMBLY)
        return flow, inv, balances, ot

    def replay(self, model, block, opening, bounds, seat, pool, multipliers, run, scenario, evidence):
        flow, inv, _, expression = block
        ledger = dict(opening)
        arrivals, withdrawals, used, delivered = Counter(), Counter(), Counter(), Counter()
        delivered_weight = 0
        for (i,j,p,t), value in model.getAttr("X",flow).items():
            assert value >= -TOL and abs(round(value)-value) <= TOL
            a = self.arcs[i,j]
            used[i,j,t] += value
            assert value <= self.base.network.product_caps.get((i,j,p,t),value) + TOL
            if (i,j) == ASSEMBLY:
                assert t <= self.due[p]
                delivered[p] += value
                delivered_weight += self.weight[p] * value
            else:
                arrivals[j,p,t+a.lead] += value
            for child, coefficient in a.recipes[p]:
                withdrawals[i,child,t] += float(coefficient)*value
        assert all(v <= len(self.groups[g].orders)+TOL for g,v in delivered.items())
        max_cap, max_bal = 0,0
        for (i,j,t), nominal in self.nominal.items():
            mult = multipliers.get((i,j,t),Fraction(1))
            effective = float(nominal * mult)
            use = used[i,j,t]
            violation = max(0,use-effective)
            max_cap = max(max_cap,violation)
            assert use <= self.base.network.group_caps.get((i,j,t),use) + TOL
            evidence["scenario_capacity_audit"].append(dict(run=run, scenario=scenario, asset=f"{i}->{j}", period=t,
                nominal_capacity=nominal, disruption_multiplier=str(mult), effective_capacity=effective, actual_usage=use, violation=violation))
        stock = model.getAttr("X",inv)
        for t in self.periods:
            assert sum(stock[n,p,t] for n,p in seat) <= pool+TOL
            for (n,p),(lower,upper) in bounds.items():
                k = n,p,t
                actual = stock[k]
                residual = actual - (ledger[n,p] + self.history.get(k,0) + arrivals[k] - withdrawals[k])
                max_bal = max(max_bal,abs(residual))
                assert lower-TOL <= actual <= upper+TOL
                evidence["balance_audit"].append(dict(run=run, scenario=scenario, node=n, item=p, period=t,
                    opening=ledger[n,p], fixed_arrival=self.history.get(k,0), decision_arrival=arrivals[k],
                    recipe_withdrawal=withdrawals[k], closing=actual, residual=residual))
                ledger[n,p] = actual
        assert max(max_bal,max_cap,abs(expression.getValue()-delivered_weight)) <= TOL
        return round(delivered_weight),max_bal,max_cap


def solve(model, objective):
    model.setObjective(objective,GRB.MAXIMIZE)
    model.optimize()
    info = solve_info(model)
    info["exact"] = (model.Status==GRB.OPTIMAL and info["mip_gap"]==0 and
                     abs(info["objective"]-info["best_bound"])<=TOL and
                     max(info[k] for k in ("model_row_violation","model_bound_violation","integrality_error"))<=TOL)
    return info


def capital(operation, buffer):
    kit, remainder = divmod(next(q for (_,p),q in buffer.items() if p==CELL[0]),10)
    assert not remainder
    assert [next(q for (_,p),q in buffer.items() if p==item) for item in CELL] == [10*kit,6*kit,4*kit]
    return KIT_COST * kit + sum(COST[operation.states[k][0]]*q for k,q in buffer.items() if k[1] not in CELL)
