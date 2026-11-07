"""Run from the repository root: python -m examples.run_acceptance."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from examples.independent_check import flow_residuals, joint_family_case, plan_residuals, scenarios, solve
from prefab_bom_robust.examples import example_a, example_b
from prefab_bom_robust.solvers import solve_ccg, solve_direct, solve_nominal, solve_phase1
from prefab_bom_robust.uncertainty import joint_extreme_points
from gurobipy import GRB


def check_case(d, expected):
    audit_scenarios = scenarios(d)
    production_scenarios = joint_extreme_points(d.S, d.V, d.Gamma2, d.Gamma3)
    assert len(audit_scenarios) == len(production_scenarios)
    assert all(risk in production_scenarios for risk in audit_scenarios)
    independent = solve(d, audit_scenarios)
    tol = 1e-7
    assert independent["status"] == GRB.OPTIMAL
    assert max(abs(independent["lb"]-expected), abs(independent["ub"]-expected), independent["residual"]) <= tol
    output = {"instance": d.name, "vertices": audit_scenarios, "projected": independent}
    for method in (solve_direct, solve_ccg):
        result = method(d)
        assert result.status == "OPTIMAL" and result.certified_optimal
        assert max(abs(result.lower_bound-expected), abs(result.upper_bound-expected),
                   abs(result.objective-expected), result.worst_gap, result.max_violation) <= tol
        plan = result.plan
        investment, rows = plan_residuals(d, plan)
        fixed = solve(d, audit_scenarios, fixed=plan)
        assert fixed["status"] == GRB.OPTIMAL
        assert abs(fixed["ub"]-expected) <= tol
        keys = ("q", "t", "g", "w", "u")
        nominal = flow_residuals(d, plan, d.zero_scenario(),
                                 {key: result.flows[f"nominal_{key}"] for key in keys}, nominal=True)
        assert abs(investment+nominal["purchase"]-result.objective) <= tol
        nominal_lp = solve_nominal(d, plan)
        assert nominal_lp.certified_optimal and abs(nominal_lp.objective-nominal["purchase"]) <= tol
        master_scenarios = production_scenarios if method is solve_direct else [
            d.zero_scenario(), *(step["scenario_added"] for step in result.iterations if step["scenario_added"] is not None)
        ]
        actual_blocks = [
            flow_residuals(d, plan, risk, {key: result.flows[f"sc{i}_{key}"] for key in keys})
            for i, risk in enumerate(master_scenarios)
        ]
        replays = []
        for risk in audit_scenarios:
            phase = solve_phase1(d, plan, *risk)
            assert phase.certified_optimal and phase.objective <= tol
            replays.append(flow_residuals(d, plan, risk, phase.flows))
        all_flows = [nominal, *actual_blocks, *replays]
        max_residual = max([*rows.values(), *(max(block["rows"].values()) for block in all_flows)])
        assert max_residual <= tol
        output[method.__name__] = {
            "status": result.status, "lb": result.lower_bound, "ub": result.upper_bound,
            "mip_gap": result.mip_gap, "solver_seconds": result.solver_runtime, "wall_seconds": result.runtime,
            "worst_gap": result.worst_gap, "gurobi_residual": result.max_violation,
            "arithmetic_residual": max_residual, "plan": asdict(plan), "first_stage_rows": rows,
            "nominal": nominal, "investment": investment, "fixed_plan_projected": fixed,
            "actual_master_blocks": actual_blocks, "all_vertex_delivery_audits": replays,
            "iterations": [{**step, "plan": asdict(step["plan"])} for step in result.iterations],
        }
    return output


if __name__ == "__main__":
    for data, optimum in ((example_a(), 4), (example_b(), 0.5), (joint_family_case(), 6)):
        print(json.dumps(check_case(data, optimum)))
