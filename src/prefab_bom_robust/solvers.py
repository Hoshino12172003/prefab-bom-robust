from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from .data import FirstStagePlan, ModelData
from .uncertainty import joint_extreme_points, validate_point


@dataclass
class SolveResult:
    status: str
    objective: float | None = None
    certified_optimal: bool = False
    plan: FirstStagePlan | None = None
    flows: dict[str, dict[Any, float]] = field(default_factory=dict)
    max_violation: float | None = None
    runtime: float = 0.0
    worst_gap: float | None = None
    worst_scenario: tuple[dict[str, float], dict[str, float]] | None = None
    iterations: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


def status_name(status: int) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL", GRB.INFEASIBLE: "INFEASIBLE", GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBOUNDED", GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.NUMERIC: "NUMERIC", GRB.INTERRUPTED: "INTERRUPTED",
    }.get(status, f"STATUS_{status}")


def _safe_optimize(model: gp.Model) -> tuple[str, str]:
    try:
        model.optimize()
        return status_name(model.Status), ""
    except gp.GurobiError as exc:
        text = str(exc)
        kind = "LICENSE_ERROR" if "license" in text.lower() else "GUROBI_ERROR"
        return kind, text


def _model(name: str, output: bool, time_limit: float | None = None) -> gp.Model:
    model = gp.Model(name)
    model.Params.OutputFlag = int(output)
    model.Params.DualReductions = 0
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    return model


def _max_violation(model: gp.Model) -> float:
    violation = 0.0
    for c in model.getConstrs():
        if c.Sense == "=":
            violation = max(violation, abs(c.Slack))
        else:
            violation = max(violation, max(0.0, -c.Slack))
    return violation


def _validate_plan(d: ModelData, plan: FirstStagePlan, tol: float = 1e-9) -> None:
    if set(plan.x) != set(d.J) or set(plan.y) != set(d.K) or set(plan.r) != set(d.K):
        raise ValueError("first-stage plan keys do not match J/K")
    if any(plan.x[j] < -tol or plan.x[j] > d.Xbar[j] + tol for j in d.J):
        raise ValueError("first-stage inventory violates its bounds")
    if any(plan.y[k] not in (0, 1) for k in d.K):
        raise ValueError("first-stage contract decisions must be binary")
    if any(plan.r[k] < -tol or plan.r[k] > d.Rbar[k] * plan.y[k] + tol for k in d.K):
        raise ValueError("first-stage reserve violates contract-linked bounds")
    cost = sum(d.cI[j] * plan.x[j] for j in d.J) + sum(
        d.f[k] * plan.y[k] + d.cR[k] * plan.r[k] for k in d.K
    )
    if cost > d.B_pre + tol:
        raise ValueError("first-stage plan violates B_pre")


def _add_first_stage(model: gp.Model, d: ModelData):
    x = model.addVars(d.J, lb=0, name="x")
    y = model.addVars(d.K, vtype=GRB.BINARY, name="y")
    r = model.addVars(d.K, lb=0, name="r")
    for j in d.J:
        model.addConstr(x[j] <= d.Xbar[j], name=f"x_cap[{j}]")
    for k in d.K:
        model.addConstr(r[k] <= d.Rbar[k] * y[k], name=f"reserve_link[{k}]")
    investment = gp.quicksum(d.cI[j] * x[j] for j in d.J) + gp.quicksum(
        d.f[k] * y[k] + d.cR[k] * r[k] for k in d.K
    )
    model.addConstr(investment <= d.B_pre, name="pre_budget")
    return x, y, r, investment


def _add_recourse(model: gp.Model, d: ModelData, x, r, eta: dict[str, float], xi: dict[str, float],
                  prefix: str, phase1: bool, require_full: bool = False):
    q = model.addVars(list(d.E), lb=0, name=f"{prefix}_q")
    t = model.addVars(list(d.N), lb=0, name=f"{prefix}_t")
    g = model.addVars(list(d.B_arc), lb=0, name=f"{prefix}_g")
    w = model.addVars(d.M, lb=0, name=f"{prefix}_w")
    u = model.addVars(d.M, lb=0, name=f"{prefix}_u")
    sigma = model.addVars(d.H, lb=0, name=f"{prefix}_sigma") if phase1 else None
    for s in d.S:
        model.addConstr(gp.quicksum(d.a[s, j] * q[s, j] for ss, j in d.E if ss == s)
                        <= d.Kbar[s] * (1 - d.epsilon[s] * eta[s]), name=f"{prefix}_t2cap[{s}]")
    for k in d.K:
        model.addConstr(gp.quicksum(t[k, s] for kk, s in d.N if kk == k)
                        <= d.Cbar[k] * (1 - d.delta[k] * xi[d.pool_node[k]]), name=f"{prefix}_t3cap[{k}]")
        model.addConstr(gp.quicksum(g[k, s] for kk, s in d.B_arc if kk == k) <= r[k],
                        name=f"{prefix}_reserve[{k}]")
        loss = d.Cbar[k] * d.delta[k] * xi[d.pool_node[k]]
        model.addConstr(gp.quicksum(g[k, s] for kk, s in d.B_arc if kk == k) <= loss,
                        name=f"{prefix}_loss_only[{k}]")
    for k, s in d.N:
        need = gp.quicksum(d.b.get((k, s, j), 0.0) * q[s, j] for ss, j in d.E if ss == s)
        backup = g[k, s] if (k, s) in d.B_arc else 0.0
        model.addConstr(need <= t[k, s] + backup, name=f"{prefix}_input[{k},{s}]")
    for j in d.J:
        model.addConstr(gp.quicksum(d.A[j, m] * w[m] for m in d.M)
                        <= d.I0[j] + x[j] + gp.quicksum(q[s, j] for s, jj in d.E if jj == j),
                        name=f"{prefix}_bom[{j}]")
    model.addConstr(gp.quicksum(d.tau[m] * w[m] for m in d.M) <= d.P, name=f"{prefix}_assembly")
    for m in d.M:
        model.addConstr(w[m] + u[m] == d.D[m], name=f"{prefix}_order[{m}]")
        if require_full:
            model.addConstr(w[m] == d.D[m], name=f"{prefix}_full[{m}]")
    op_cost = gp.quicksum(d.cQ[s, j] * q[s, j] for s, j in d.E) + gp.quicksum(
        d.cA[k, s] * g[k, s] for k, s in d.B_arc
    )
    model.addConstr(op_cost <= d.E_op, name=f"{prefix}_op_budget")
    for h in d.H:
        delivered = gp.quicksum(w[m] for m in d.M if d.family[m] == h)
        rhs = d.alpha[h] * d.family_demand(h)
        if phase1:
            model.addConstr(delivered + sigma[h] >= rhs, name=f"{prefix}_service[{h}]")
        elif not require_full:
            model.addConstr(delivered >= rhs, name=f"{prefix}_service[{h}]")
    return {"q": q, "t": t, "g": g, "w": w, "u": u, "sigma": sigma, "op_cost": op_cost}


def _values(container) -> dict[Any, float]:
    return {key: var.X for key, var in container.items()}


def solve_nominal(d: ModelData, plan: FirstStagePlan, output: bool = False) -> SolveResult:
    d.validate(); _validate_plan(d, plan); start = perf_counter(); model = _model("nominal", output)
    x = {j: float(plan.x[j]) for j in d.J}; r = {k: 0.0 for k in d.K}
    eta, xi = d.zero_scenario()
    rec = _add_recourse(model, d, x, r, eta, xi, "nom", phase1=False, require_full=True)
    model.setObjective(rec["op_cost"], GRB.MINIMIZE)
    status, message = _safe_optimize(model)
    result = SolveResult(status=status, certified_optimal=status == "OPTIMAL", runtime=perf_counter()-start, message=message)
    if status == "OPTIMAL":
        result.objective = model.ObjVal; result.max_violation = _max_violation(model)
        result.flows = {key: _values(rec[key]) for key in ("q", "t", "g", "w", "u")}
    return result


def solve_phase1(d: ModelData, plan: FirstStagePlan, eta: dict[str, float], xi: dict[str, float],
                 output: bool = False) -> SolveResult:
    d.validate(); _validate_plan(d, plan)
    validate_point(eta, d.S, d.Gamma2); validate_point(xi, d.V, d.Gamma3)
    start = perf_counter(); model = _model("phase1", output)
    rec = _add_recourse(model, d, plan.x, plan.r, eta, xi, "p1", phase1=True)
    model.setObjective(gp.quicksum(rec["sigma"][h] for h in d.H), GRB.MINIMIZE)
    status, message = _safe_optimize(model)
    result = SolveResult(status=status, certified_optimal=status == "OPTIMAL", runtime=perf_counter()-start, message=message)
    if status == "OPTIMAL":
        result.objective = model.ObjVal; result.worst_gap = model.ObjVal; result.max_violation = _max_violation(model)
        result.flows = {key: _values(rec[key]) for key in ("q", "t", "g", "w", "u", "sigma")}
    return result


def _solve_master(d: ModelData, scenarios, output=False, time_limit=None) -> SolveResult:
    start = perf_counter(); model = _model("master", output, time_limit)
    x, y, r, investment = _add_first_stage(model, d)
    zero_eta, zero_xi = d.zero_scenario()
    nominal = _add_recourse(model, d, x, {k: 0.0 for k in d.K}, zero_eta, zero_xi, "nom", False, True)
    for idx, (eta, xi) in enumerate(scenarios):
        _add_recourse(model, d, x, r, eta, xi, f"sc{idx}", False)
    model.setObjective(investment + nominal["op_cost"], GRB.MINIMIZE)
    status, message = _safe_optimize(model)
    result = SolveResult(status=status, certified_optimal=status == "OPTIMAL", runtime=perf_counter()-start, message=message)
    if status == "OPTIMAL":
        result.objective = model.ObjVal; result.max_violation = _max_violation(model)
        result.plan = FirstStagePlan(_values(x), {k: int(round(y[k].X)) for k in d.K}, _values(r))
        result.flows = {f"nominal_{key}": _values(nominal[key]) for key in ("q", "t", "w", "u")}
    return result


def certify_plan(d: ModelData, plan: FirstStagePlan, max_scenarios: int = 10000) -> SolveResult:
    start = perf_counter(); scenarios = joint_extreme_points(d.S, d.V, d.Gamma2, d.Gamma3, max_scenarios)
    worst = -1.0; worst_sc = None; max_res = 0.0
    for eta, xi in scenarios:
        check = solve_phase1(d, plan, eta, xi)
        if not check.certified_optimal:
            return SolveResult(status=check.status, message=check.message, runtime=perf_counter()-start)
        max_res = max(max_res, check.max_violation or 0.0)
        if check.objective is not None and check.objective > worst + 1e-10:
            worst, worst_sc = check.objective, (eta, xi)
    return SolveResult(status="OPTIMAL", objective=worst, worst_gap=worst, worst_scenario=worst_sc,
                       certified_optimal=True, max_violation=max_res, runtime=perf_counter()-start)


def solve_direct(d: ModelData, max_scenarios: int = 10000, output: bool = False) -> SolveResult:
    d.validate(); scenarios = joint_extreme_points(d.S, d.V, d.Gamma2, d.Gamma3, max_scenarios)
    result = _solve_master(d, scenarios, output)
    if result.certified_optimal and result.plan:
        cert = certify_plan(d, result.plan, max_scenarios)
        result.worst_gap = cert.worst_gap; result.worst_scenario = cert.worst_scenario
        result.max_violation = max(result.max_violation or 0.0, cert.max_violation or 0.0)
        result.certified_optimal = cert.certified_optimal and (cert.worst_gap or 0.0) <= 1e-7
    return result


def solve_ccg(d: ModelData, max_scenarios: int = 10000, tol: float = 1e-7,
              max_iterations: int = 100, output: bool = False) -> SolveResult:
    d.validate(); start = perf_counter(); all_scenarios = joint_extreme_points(
        d.S, d.V, d.Gamma2, d.Gamma3, max_scenarios)
    scenarios = [d.zero_scenario()]; trace = []
    for iteration in range(1, max_iterations + 1):
        master = _solve_master(d, scenarios, output)
        if not master.certified_optimal or not master.plan:
            master.iterations = trace; master.runtime = perf_counter() - start
            return master
        worst = -1.0; worst_sc = None
        for scenario in all_scenarios:
            check = solve_phase1(d, master.plan, *scenario)
            if not check.certified_optimal:
                return SolveResult(status=check.status, message=check.message, iterations=trace,
                                   runtime=perf_counter()-start)
            if check.objective is not None and check.objective > worst + 1e-10:
                worst, worst_sc = check.objective, scenario
        added = worst > tol and worst_sc not in scenarios
        trace.append({"iteration": iteration, "master_objective": master.objective,
                      "plan": master.plan, "worst_gap": worst, "scenario_added": worst_sc if added else None,
                      "certified": worst <= tol})
        if worst <= tol:
            master.worst_gap = worst; master.worst_scenario = worst_sc; master.iterations = trace
            master.runtime = perf_counter() - start; master.certified_optimal = True
            return master
        if not added:
            return SolveResult(status="STALLED", objective=master.objective, plan=master.plan,
                               worst_gap=worst, worst_scenario=worst_sc, iterations=trace,
                               runtime=perf_counter()-start, message="violating scenario already present")
        scenarios.append(worst_sc)
    return SolveResult(status="ITERATION_LIMIT", certified_optimal=False, iterations=trace,
                       runtime=perf_counter()-start, message="C&CG iteration limit reached")
