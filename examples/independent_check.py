"""Small V1 audit oracle. No production solver or vertex builder is imported."""
from fractions import Fraction
from itertools import product
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from prefab_bom_robust.data import FirstStagePlan


def vertices(nodes, gamma):
    """Intersect the box edges and corners with the budget plane using rationals."""
    budget = Fraction(gamma)
    points = {corner for corner in product((0, 1), repeat=len(nodes)) if sum(corner) <= budget}
    for corner in product((0, 1), repeat=len(nodes)):
        remaining = budget - sum(corner)
        if 0 < remaining < 1:
            for index, value in enumerate(corner):
                if value == 0:
                    points.add(corner[:index] + (remaining,) + corner[index + 1:])
    return [dict(zip(nodes, map(float, point))) for point in sorted(points)]


def scenarios(d):
    return list(product(vertices(d.S, d.Gamma2), vertices(d.V, d.Gamma3)))


def solve(d, risks, fixed=None):
    """Independently solve the projected hard-service extensive form or fixed-plan replay."""
    start = perf_counter()
    d.validate()
    with gp.Model("projected_audit") as m:
        m.Params.OutputFlag = 0
        m.Params.MIPGap = m.Params.MIPGapAbs = 0
        m.Params.FeasibilityTol = m.Params.IntFeasTol = m.Params.OptimalityTol = 1e-9
        m.Params.DualReductions = 0
        x = {j: m.addVar(ub=d.Xbar[j]) for j in d.J}
        r = {k: m.addVar() for k in d.K}
        y = {k: m.addVar(vtype=GRB.BINARY) for k in d.K}
        investment = sum(d.cI[j] * x[j] for j in x) + sum(d.f[k]*y[k] + d.cR[k]*r[k] for k in r)
        m.addConstr(investment <= d.B_pre)
        for k in d.K:
            m.addConstr(r[k] <= d.Rbar[k] * y[k])
        if fixed is not None:
            for variables, values in ((x, fixed.x), (y, fixed.y), (r, fixed.r)):
                for key in variables:
                    m.addConstr(variables[key] == values[key])
        modes = [(True, {s: 0 for s in d.S}, {v: 0 for v in d.V})]
        modes.extend((False, eta, xi) for eta, xi in risks)
        for nominal, eta, xi in modes:
            q = {arc: m.addVar() for arc in sorted(d.E)}
            g = {arc: m.addVar(ub=0 if nominal else GRB.INFINITY) for arc in sorted(d.B_arc)}
            w = {p: d.D[p] if nominal else m.addVar(ub=d.D[p]) for p in d.M}
            needs = {arc: gp.LinExpr() for arc in sorted(d.N)}
            for (k, s, j), coefficient in d.b.items():
                if coefficient:
                    needs[k, s] += coefficient * q[s, j]
            for arc, backup in g.items():
                m.addConstr(backup <= needs[arc])
            for k in d.K:
                loss = d.Cbar[k] * d.delta[k] * xi[d.pool_node[k]]
                normal_used = gp.quicksum(needs[arc] - g.get(arc, 0) for arc in needs if arc[0] == k)
                backup_used = gp.quicksum(g[arc] for arc in g if arc[0] == k)
                m.addConstr(normal_used <= d.Cbar[k] - loss)
                m.addConstr(backup_used <= r[k])
                m.addConstr(backup_used <= loss)
            for s in d.S:
                m.addConstr(gp.quicksum(d.a[arc]*q[arc] for arc in q if arc[0] == s)
                            <= d.Kbar[s] - d.Kbar[s]*d.epsilon[s]*eta[s])
            for j in d.J:
                balance = x[j] + gp.quicksum(q[arc] for arc in q if arc[1] == j)
                m.addConstr(balance >= gp.quicksum(d.A[j, p]*w[p] for p in w) - d.I0[j])
            m.addConstr(gp.quicksum(d.tau[p]*w[p] for p in w) <= d.P)
            for h in d.H:
                products = [p for p in w if d.family[p] == h]
                m.addConstr(gp.quicksum(w[p] for p in products) >= d.alpha[h] * sum(d.D[p] for p in products))
            procurement = gp.quicksum(d.cQ[arc]*q[arc] for arc in q)
            activation = gp.quicksum(d.cA[arc]*g[arc] for arc in g)
            m.addConstr(procurement + activation <= d.E_op)
            if nominal:
                m.setObjective(investment + procurement)
        m.optimize()
        out = {"status": m.Status, "solver_seconds": m.Runtime, "wall_seconds": perf_counter() - start}
        if m.Status == GRB.OPTIMAL:
            out.update(lb=m.ObjBound, ub=m.ObjVal, gap=m.MIPGap, residual=max(m.ConstrVio, m.BoundVio, m.IntVio))
        return out


def plan_residuals(d, plan):
    investment = sum(d.cI[j]*plan.x[j] for j in d.J) + sum(
        d.f[k]*plan.y[k] + d.cR[k]*plan.r[k] for k in d.K
    )
    return investment, {
        "inventory_bounds": max(0, *(-plan.x[j] for j in d.J), *(plan.x[j]-d.Xbar[j] for j in d.J)),
        "binary": max(min(abs(y), abs(y-1)) for y in plan.y.values()),
        "reserve_link": max(0, *(-plan.r[k] for k in d.K),
                            *(plan.r[k]-d.Rbar[k]*plan.y[k] for k in d.K)),
        "pre_budget": max(0, investment-d.B_pre),
    }


def flow_residuals(d, plan, risk, flows, nominal=False):
    eta, xi = risk
    q, t, g, w, u = (flows[key] for key in ("q", "t", "g", "w", "u"))
    for actual, allowed in ((q, d.E), (t, d.N), (g, d.B_arc), (w, set(d.M)), (u, set(d.M))):
        assert actual.keys() == allowed
    purchase = sum(d.cQ[arc]*amount for arc, amount in q.items())
    activation = sum(d.cA[arc]*amount for arc, amount in g.items())
    rows = {"nonnegative": [-value for mapping in (q, t, g, w, u) for value in mapping.values()]}
    rows["assembly"] = [sum(d.tau[p]*w[p] for p in w) - d.P]
    rows["op_budget"] = [purchase + activation - d.E_op]
    rows["order_balance"] = [abs(w[p]+u[p]-d.D[p]) for p in w]
    rows["T2"] = [sum(d.a[arc]*q[arc] for arc in q if arc[0] == s) -
                  d.Kbar[s]*(1-d.epsilon[s]*eta[s]) for s in d.S]
    rows["T3"] = []
    rows["reserve"] = []
    rows["loss_only"] = []
    for k in d.K:
        loss = d.Cbar[k]*d.delta[k]*xi[d.pool_node[k]]
        activated = sum(g[arc] for arc in g if arc[0] == k)
        rows["T3"].append(sum(t[arc] for arc in t if arc[0] == k) - (d.Cbar[k]-loss))
        rows["reserve"].append(activated-plan.r[k])
        rows["loss_only"].append(activated-loss)
    inputs = {arc: 0.0 for arc in t}
    for (k, s, j), coeff in d.b.items():
        if coeff:
            inputs[k, s] += coeff*q[s, j]
    rows["upstream_input"] = [amount-t[arc]-g.get(arc, 0) for arc, amount in inputs.items()]
    rows["BOM"] = [sum(d.A[j, p]*w[p] for p in w) -
                   (d.I0[j]+plan.x[j]+sum(q[arc] for arc in q if arc[1] == j)) for j in d.J]
    delivery = {h: sum(w[p] for p in w if d.family[p] == h) for h in d.H}
    rows["joint_service"] = [d.alpha[h]*sum(d.D[p] for p in w if d.family[p] == h) -
                             delivery[h] for h in d.H]
    if nominal:
        rows["nominal_full"] = [abs(w[p]-d.D[p]) for p in w]
        rows["nominal_no_backup"] = list(g.values())
    return {"rows": {key: max([0.0, *values]) for key, values in rows.items()},
            "purchase": purchase, "activation": activation, "delivery": delivery}


def joint_family_case():
    from prefab_bom_robust.data import ModelData

    families = ("HV", "MV", "LV")
    items = (*families, "aux")
    return ModelData(
        H=families, M=families, J=items, S=families, V=("source",), K=("shared", "input2"),
        family={h: h for h in families}, pool_node={"shared": "source", "input2": "source"},
        E={(h, h) for h in families}, N={("shared", h) for h in families} | {("input2", "MV")},
        B_arc={("shared", "HV"), ("shared", "MV")},
        A={(j, h): int(j == h or (j, h) == ("aux", "HV")) for j in items for h in families},
        D=dict.fromkeys(families, 1), I0={j: int(j == "aux") for j in items},
        a={(h, h): 1 for h in families},
        b={("shared", h, h): 1 for h in families} | {("input2", "MV", "MV"): 1},
        Kbar={"HV": 1, "MV": 2, "LV": 2}, Cbar={"shared": 3, "input2": 2},
        epsilon=dict.fromkeys(families, 1), delta={"shared": 1, "input2": 1},
        Xbar={j: 0.5 if j == "HV" else 0 for j in items}, Rbar={"shared": 2, "input2": 0},
        cI=dict.fromkeys(items, 1), f={"shared": 1, "input2": 1}, cR={"shared": 2, "input2": 2},
        cQ={(h, h): 1 for h in families}, cA={("shared", "HV"): 2, ("shared", "MV"): 2},
        alpha=dict.fromkeys(families, 1), tau=dict.fromkeys(families, 1),
        P=3, B_pre=5, E_op=4.5, Gamma2=0.5, Gamma3=0.5, name="joint_HV_MV_LV",
    )
