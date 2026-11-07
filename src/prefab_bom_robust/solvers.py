from dataclasses import dataclass, field
from functools import wraps
from math import isfinite
from time import perf_counter
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from .data import FirstStagePlan, ModelData
from .uncertainty import joint_extreme_points, validate_point

CERT_TOL = 1e-7


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
    lower_bound: float | None = None
    upper_bound: float | None = None
    mip_gap: float | None = None
    solver_runtime: float | None = None


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
        return _error_status(exc), str(exc)


def _error_status(exc):
    if exc.errno == GRB.Error.NO_LICENSE or "license" in str(exc).lower():
        return "LICENSE_ERROR"
    return "GUROBI_ERROR"


def _guard_model_errors(solve):
    @wraps(solve)
    def guarded(*args, **kwargs):
        start = perf_counter()
        try:
            return solve(*args, **kwargs)
        except gp.GurobiError as exc:
            return SolveResult(status=_error_status(exc), message=str(exc), runtime=perf_counter() - start)
    return guarded


def _model(name: str, output: bool, time_limit: float | None = None) -> gp.Model:
    model = gp.Model(name)
    model.Params.OutputFlag = int(output)
    model.Params.DualReductions = 0
    model.Params.FeasibilityTol = 1e-9
    model.Params.IntFeasTol = 1e-9
    model.Params.OptimalityTol = 1e-9
    model.Params.MIPGap = 0
    model.Params.MIPGapAbs = 0
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    return model


def _max_violation(model: gp.Model) -> float:
    return max(model.ConstrVio, model.BoundVio, model.IntVio if model.IsMIP else 0.0)


def _solve_result(model, start):
    status, message = _safe_optimize(model)
    result = SolveResult(status=status, runtime=perf_counter() - start, message=message)
    if status in {"LICENSE_ERROR", "GUROBI_ERROR"}:
        return result
    result.solver_runtime = model.Runtime
    if model.IsMIP and isfinite(model.ObjBound):
        result.lower_bound = model.ObjBound
    if model.SolCount:
        result.upper_bound = model.ObjVal
        result.max_violation = _max_violation(model)
        if model.IsMIP and isfinite(model.MIPGap):
            result.mip_gap = model.MIPGap
    if status == "OPTIMAL":
        result.objective = model.ObjVal
        if not model.IsMIP:
            result.lower_bound = result.objective
        values = (result.lower_bound, result.upper_bound, result.max_violation)
        result.certified_optimal = (
            all(v is not None and isfinite(v) for v in values)
            and abs(result.upper_bound - result.lower_bound) <= CERT_TOL
            and result.max_violation <= CERT_TOL
        )
        if not result.certified_optimal:
            result.status = "NUMERICAL_VALIDATION_FAILED"
    return result


def _validate_plan(d: ModelData, plan: FirstStagePlan, tol: float = 1e-9) -> None:
    if set(plan.x) != set(d.J) or set(plan.y) != set(d.K) or set(plan.r) != set(d.K):
        raise ValueError("first-stage plan keys do not match J/K")
    if any(not isfinite(plan.x[j]) or not -tol <= plan.x[j] <= d.Xbar[j] + tol for j in d.J):
        raise ValueError("first-stage inventory violates its bounds")
    if any(plan.y[k] not in (0, 1) for k in d.K):
        raise ValueError("first-stage contract decisions must be binary")
    if any(not isfinite(plan.r[k]) or not -tol <= plan.r[k] <= d.Rbar[k] * plan.y[k] + tol for k in d.K):
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


@_guard_model_errors
def solve_nominal(d: ModelData, plan: FirstStagePlan, output: bool = False) -> SolveResult:
    d.validate(); _validate_plan(d, plan); start = perf_counter(); model = _model("nominal", output)
    x = {j: float(plan.x[j]) for j in d.J}; r = {k: 0.0 for k in d.K}
    eta, xi = d.zero_scenario()
    rec = _add_recourse(model, d, x, r, eta, xi, "nom", phase1=False, require_full=True)
    model.setObjective(rec["op_cost"], GRB.MINIMIZE)
    result = _solve_result(model, start)
    if result.certified_optimal:
        result.flows = {key: _values(rec[key]) for key in ("q", "t", "g", "w", "u")}
    return result


@_guard_model_errors
def solve_phase1(d: ModelData, plan: FirstStagePlan, eta: dict[str, float], xi: dict[str, float],
                 output: bool = False) -> SolveResult:
    d.validate(); _validate_plan(d, plan)
    validate_point(eta, d.S, d.Gamma2); validate_point(xi, d.V, d.Gamma3)
    start = perf_counter(); model = _model("phase1", output)
    rec = _add_recourse(model, d, plan.x, plan.r, eta, xi, "p1", phase1=True)
    model.setObjective(gp.quicksum(rec["sigma"][h] for h in d.H), GRB.MINIMIZE)
    result = _solve_result(model, start)
    if result.certified_optimal:
        result.worst_gap = model.ObjVal
        result.flows = {key: _values(rec[key]) for key in ("q", "t", "g", "w", "u", "sigma")}
    return result


@_guard_model_errors
def _solve_master(d: ModelData, scenarios, output=False, time_limit=None) -> SolveResult:
    start = perf_counter(); model = _model("master", output, time_limit)
    x, y, r, investment = _add_first_stage(model, d)
    zero_eta, zero_xi = d.zero_scenario()
    nominal = _add_recourse(model, d, x, {k: 0.0 for k in d.K}, zero_eta, zero_xi, "nom", False, True)
    recourses = [
        _add_recourse(model, d, x, r, eta, xi, f"sc{idx}", False)
        for idx, (eta, xi) in enumerate(scenarios)
    ]
    model.setObjective(investment + nominal["op_cost"], GRB.MINIMIZE)
    result = _solve_result(model, start)
    if result.certified_optimal:
        result.plan = FirstStagePlan(_values(x), {k: int(round(y[k].X)) for k in d.K}, _values(r))
        try:
            _validate_plan(d, result.plan)
        except ValueError as exc:
            result.status = "NUMERICAL_VALIDATION_FAILED"
            result.certified_optimal = False
            result.message = str(exc)
            return result
        for index, rec in enumerate([nominal, *recourses]):
            prefix = "nominal" if index == 0 else f"sc{index-1}"
            for key in ("q", "t", "g", "w", "u"):
                result.flows[f"{prefix}_{key}"] = _values(rec[key])
    return result


def _separate(d, plan, scenarios):
    start = perf_counter()
    worst = -1.0; worst_sc = None; max_res = 0.0
    solver_runtime = 0.0
    for eta, xi in scenarios:
        check = solve_phase1(d, plan, eta, xi)
        if not check.certified_optimal:
            return SolveResult(status=check.status, message=check.message, runtime=perf_counter()-start)
        max_res = max(max_res, check.max_violation or 0.0)
        solver_runtime += check.solver_runtime or 0.0
        if check.objective > worst:
            worst, worst_sc = check.objective, (eta, xi)
    return SolveResult(status="OPTIMAL", objective=worst, worst_gap=worst, worst_scenario=worst_sc,
                       certified_optimal=True, max_violation=max_res, runtime=perf_counter()-start,
                       solver_runtime=solver_runtime)


def certify_plan(d: ModelData, plan: FirstStagePlan, max_scenarios: int = 10000) -> SolveResult:
    d.validate()
    scenarios = joint_extreme_points(d.S, d.V, d.Gamma2, d.Gamma3, max_scenarios)
    return _separate(d, plan, scenarios)


def solve_direct(d: ModelData, max_scenarios: int = 10000, output: bool = False) -> SolveResult:
    start = perf_counter()
    d.validate(); scenarios = joint_extreme_points(d.S, d.V, d.Gamma2, d.Gamma3, max_scenarios)
    result = _solve_master(d, scenarios, output)
    if result.certified_optimal and result.plan:
        cert = _separate(d, result.plan, scenarios)
        result.worst_gap = cert.worst_gap; result.worst_scenario = cert.worst_scenario
        result.max_violation = max(result.max_violation or 0.0, cert.max_violation or 0.0)
        result.solver_runtime = (result.solver_runtime or 0.0) + (cert.solver_runtime or 0.0)
        result.certified_optimal = cert.certified_optimal and cert.worst_gap <= CERT_TOL
        if not result.certified_optimal:
            result.status = cert.status if not cert.certified_optimal else "NUMERICAL_VALIDATION_FAILED"
            result.message = cert.message or "Full separation did not certify the plan"
    if not result.certified_optimal:
        result.upper_bound = None
        result.mip_gap = None
    result.runtime = perf_counter() - start
    return result


def solve_ccg(d: ModelData, max_scenarios: int = 10000, tol: float = CERT_TOL,
              max_iterations: int = 100, output: bool = False) -> SolveResult:
    if not 0 <= tol <= CERT_TOL:
        raise ValueError(f"service tolerance must be in [0, {CERT_TOL}]")
    d.validate(); start = perf_counter(); all_scenarios = joint_extreme_points(
        d.S, d.V, d.Gamma2, d.Gamma3, max_scenarios)
    scenarios = [d.zero_scenario()]; trace = []
    solver_runtime = 0.0
    lower_bound = None
    for iteration in range(1, max_iterations + 1):
        master = _solve_master(d, scenarios, output)
        solver_runtime += master.solver_runtime or 0.0
        if master.lower_bound is not None:
            lower_bound = max(lower_bound, master.lower_bound) if lower_bound is not None else master.lower_bound
        if not master.certified_optimal or not master.plan:
            master.iterations = trace; master.runtime = perf_counter() - start
            master.solver_runtime = solver_runtime
            master.lower_bound = lower_bound
            master.upper_bound = master.mip_gap = None
            return master
        check = _separate(d, master.plan, all_scenarios)
        solver_runtime += check.solver_runtime or 0.0
        if not check.certified_optimal:
            return SolveResult(status=check.status, message=check.message, iterations=trace,
                               lower_bound=lower_bound, solver_runtime=solver_runtime,
                               runtime=perf_counter()-start)
        worst, worst_sc = check.worst_gap, check.worst_scenario
        added = worst > tol and worst_sc not in scenarios
        trace.append({"iteration": iteration, "master_objective": master.objective, "master_bound": master.lower_bound,
                      "plan": master.plan, "worst_gap": worst, "scenario_added": worst_sc if added else None,
                      "certified": worst <= tol})
        if worst <= tol:
            master.worst_gap = worst; master.worst_scenario = worst_sc; master.iterations = trace
            master.runtime = perf_counter() - start; master.certified_optimal = True
            master.max_violation = max(master.max_violation, check.max_violation)
            master.solver_runtime = solver_runtime
            master.lower_bound = lower_bound
            difference = abs(master.upper_bound - lower_bound)
            if difference > CERT_TOL:
                master.status = "NUMERICAL_VALIDATION_FAILED"
                master.certified_optimal = False
            master.mip_gap = difference / abs(master.upper_bound) if master.upper_bound else (
                float("inf") if difference else 0.0
            )
            return master
        if not added:
            return SolveResult(status="STALLED", objective=master.objective, plan=master.plan,
                               worst_gap=worst, worst_scenario=worst_sc, iterations=trace,
                               lower_bound=lower_bound, solver_runtime=solver_runtime,
                               runtime=perf_counter()-start, message="violating scenario already present")
        scenarios.append(worst_sc)
    return SolveResult(status="ITERATION_LIMIT", certified_optimal=False, iterations=trace,
                       lower_bound=lower_bound, solver_runtime=solver_runtime,
                       runtime=perf_counter()-start, message="C&CG iteration limit reached")
