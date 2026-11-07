from math import nextafter, nan
from dataclasses import replace

import gurobipy as gp
import pytest
from gurobipy import GRB

from prefab_bom_robust import solvers
from examples.independent_check import joint_family_case, scenarios, solve, vertices
from examples.run_acceptance import check_case
from prefab_bom_robust.data import FirstStagePlan
from prefab_bom_robust.examples import example_a, example_b
from prefab_bom_robust import uncertainty
from prefab_bom_robust.uncertainty import budget_extreme_points, validate_point


@pytest.mark.parametrize('gamma', [nextafter(1.0, 0.0), 1e-13, nextafter(1.0, 2.0)])
def test_fractional_vertices_arbitrarily_close_to_integer(gamma):
    points = {tuple(p.values()) for p in budget_extreme_points(('a', 'b'), gamma)}
    expected = {(0, 0), (gamma, 0), (0, gamma)} if gamma < 1 else {
        (0, 0), (1, 0), (0, 1), (1, gamma - 1), (gamma - 1, 1),
    }
    assert points == expected


def test_invalid_numeric_inputs():
    d = example_b()
    d.b['k', 's', 'j'] = -1
    with pytest.raises(ValueError):
        d.validate()
    with pytest.raises(ValueError):
        validate_point({'v': nan}, ('v',), 0.5)


def test_residual_ignores_positive_service_surplus():
    with gp.Model() as m:
        m.Params.OutputFlag = 0
        x = m.addVar(lb=1, ub=1)
        m.addConstr(x >= 0.5)
        m.optimize()
        assert m.Status == GRB.OPTIMAL
        assert solvers._max_violation(m) == pytest.approx(0)


def test_license_error_during_model_creation(monkeypatch):
    def fail(*args, **kwargs):
        raise gp.GurobiError(10009, 'No Gurobi license found')

    monkeypatch.setattr(solvers, '_model', fail)
    result = solvers.solve_direct(example_b())
    assert result.status == 'LICENSE_ERROR'
    assert not result.certified_optimal


@pytest.mark.parametrize("count", range(1, 5))
def test_vertices_match_independent_box_edge_intersections(count):
    nodes = tuple(map(str, range(count)))
    for gamma in (0, 0.1, 0.5, 1, nextafter(1., 0.), count-0.25, count):
        assert {tuple(p.values()) for p in budget_extreme_points(nodes, gamma)} == {
            tuple(p.values()) for p in vertices(nodes, gamma)
        }


def test_scenario_cap_checks_before_materializing(monkeypatch):
    def forbidden(*args):
        pytest.fail("oversized enumeration reached vertex materialization")

    monkeypatch.setattr(uncertainty, "budget_extreme_points", forbidden)
    with pytest.raises(uncertainty.ExactEnumerationUnavailable, match="threshold"):
        uncertainty.joint_extreme_points(tuple(map(str, range(30))), ("v",), 30, 0, max_scenarios=10)


@pytest.mark.parametrize("factory,objective", [(example_a, 4), (example_b, 0.5), (joint_family_case, 6)])
def test_projected_gurobi_and_arithmetic_residuals(factory, objective):
    check_case(factory(), objective)


def test_same_scenario_three_families_cannot_splice_plans():
    d = joint_family_case()
    # Isolate competition here. The separate joint-risk solve below also binds T2.
    eta = dict.fromkeys(d.S, 0)
    xi = {"source": 0.5}
    plan = FirstStagePlan(dict.fromkeys(d.J, 0), {"shared": 1, "input2": 0}, {"shared": 1, "input2": 0})
    assert solvers.solve_phase1(d, plan, eta, xi).objective == pytest.approx(0.5)
    assert solve(d, [(eta, xi)], fixed=plan)["status"] == GRB.INFEASIBLE
    for h in d.H:
        isolated = replace(d, alpha={family: int(family == h) for family in d.H})
        assert solvers.solve_phase1(isolated, plan, eta, xi).objective == pytest.approx(0)
    robust = solvers.solve_ccg(d).plan
    joint = solvers.solve_phase1(d, robust, {**eta, "HV": 0.5}, xi)
    assert joint.flows["w"] == pytest.approx({"HV": 1, "MV": 1, "LV": 1})
    assert sum(joint.flows["g"].values()) == pytest.approx(1)
    assert sum(val for (k, _), val in joint.flows["t"].items() if k == "shared") == pytest.approx(1.5)


def test_bom_auxiliary_and_activation_fee_are_binding():
    d = joint_family_case()
    no_aux = replace(d, I0=dict.fromkeys(d.J, 0))
    too_little_cash = replace(d, E_op=4.49)
    for invalid in (no_aux, too_little_cash):
        assert solvers.solve_direct(invalid).status == "INFEASIBLE"
        assert solvers.solve_ccg(invalid).status == "INFEASIBLE"
        assert solve(invalid, scenarios(invalid))["status"] == GRB.INFEASIBLE


def test_backup_cannot_expand_normal_capacity_or_exceed_reserve():
    d = replace(example_b(), D={"p": 2}, P=2, Gamma3=1)
    plan = FirstStagePlan({"j": 0}, {"k": 1}, {"k": 0.75})
    no_loss = solvers.solve_phase1(d, plan, {"s": 0}, {"v": 0})
    assert no_loss.objective == pytest.approx(1)
    assert no_loss.flows["g"]["k", "s"] == pytest.approx(0)
    full_loss = solvers.solve_phase1(d, plan, {"s": 0}, {"v": 1})
    assert full_loss.objective == pytest.approx(1.25)
    assert full_loss.flows["g"]["k", "s"] == pytest.approx(0.75)


def test_real_time_limit_and_failed_separation_cannot_certify(monkeypatch):
    d = example_b()
    timed = solvers._solve_master(d, [], time_limit=0)
    assert timed.status == "TIME_LIMIT" and not timed.certified_optimal
    monkeypatch.setattr(solvers, "solve_phase1", lambda *args: solvers.SolveResult(status="NUMERIC"))
    for method in (solvers.solve_direct, solvers.solve_ccg):
        result = method(d)
        assert result.status == "NUMERIC" and not result.certified_optimal
        assert result.upper_bound is None and result.mip_gap is None
