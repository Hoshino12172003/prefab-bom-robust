from copy import deepcopy
from itertools import product
import random

import pytest
import gurobipy as gp
from gurobipy import GRB

from prefab_bom_robust.data import FirstStagePlan
from prefab_bom_robust.examples import example_a, example_b, sufficient_inventory
from prefab_bom_robust.solvers import _safe_optimize, certify_plan, solve_ccg, solve_direct, solve_nominal, solve_phase1, status_name
from prefab_bom_robust.uncertainty import ExactEnumerationUnavailable, budget_extreme_points, joint_extreme_points


TOL = 1e-6


def zero_plan(d):
    return FirstStagePlan({j: 0 for j in d.J}, {k: 0 for k in d.K}, {k: 0 for k in d.K})


def test_T01_basic_feasibility_and_sufficient_inventory():
    d = sufficient_inventory(); result = solve_nominal(d, zero_plan(d))
    assert result.status == "OPTIMAL" and result.objective == pytest.approx(0)
    assert result.flows["w"]["p"] == pytest.approx(1)
    assert result.max_violation <= TOL


def test_T02_bom_component_specific_bottleneck():
    d = example_a(); d.Gamma3 = 0; d.I0 = {"jh": 2, "jl": 0}; d.Cbar = {"k1": 0}; d.alpha = {"HV": 0, "LV": 0}
    plan = FirstStagePlan({"jh": 0, "jl": 0}, {"k1": 0}, {"k1": 0})
    p = solve_phase1(d, plan, *d.zero_scenario())
    assert p.flows["w"]["lv1"] == pytest.approx(0)


def test_T03_shared_t3_pool_not_duplicated():
    d = example_a(); d.Gamma3 = 0; d.Cbar = {"k1": 1}; d.alpha = {"HV": 1, "LV": 1}
    p = solve_phase1(d, zero_plan(d), *d.zero_scenario())
    assert p.objective == pytest.approx(1)
    assert sum(p.flows["t"].values()) <= 1 + TOL


def test_T04_backup_contract_reservation_activation_and_arcs():
    d = example_b(); eta, xi = d.zero_scenario()
    no_contract = solve_phase1(d, zero_plan(d), eta, xi)
    assert sum(no_contract.flows["g"].values()) == pytest.approx(0)
    reserved = FirstStagePlan({"j": 0}, {"k": 1}, {"k": 0.5})
    no_loss = solve_phase1(d, reserved, eta, xi)
    assert sum(no_loss.flows["g"].values()) == pytest.approx(0)
    loss = solve_phase1(d, reserved, eta, {"v": 0.5})
    assert sum(loss.flows["g"].values()) <= 0.5 + TOL
    with pytest.raises(ValueError, match="contract-linked"):
        solve_phase1(d, FirstStagePlan({"j": 0}, {"k": 0}, {"k": 0.5}), eta, {"v": 0.5})
    bad = deepcopy(d); bad.B_arc = {("k", "missing")}
    with pytest.raises(ValueError): bad.validate()


def test_T05_nominal_requires_full_orders():
    d = example_b(); d.Cbar = {"k": 0}; d.I0 = {"j": 0}
    assert solve_nominal(d, zero_plan(d)).status == "INFEASIBLE"


def test_T06_family_guarantees_are_simultaneous():
    d = example_a(); d.Gamma3 = 0; d.Cbar = {"k1": 1}; d.alpha = {"HV": 1, "LV": 1}
    joint = solve_phase1(d, zero_plan(d), *d.zero_scenario())
    assert joint.objective == pytest.approx(1)
    for target in ("HV", "LV"):
        one = deepcopy(d); one.alpha = {"HV": 0, "LV": 0}; one.alpha[target] = 1
        assert solve_phase1(one, zero_plan(one), *one.zero_scenario()).objective == pytest.approx(0)


@pytest.mark.parametrize("gamma,expected,has_fraction", [(0, 1, False), (0.5, 3, True), (1, 3, False),
                                                           (1.5, 5, True), (2, 4, False)])
def test_T07_continuous_budget_vertices(gamma, expected, has_fraction):
    pts = budget_extreme_points(("a", "b"), gamma)
    assert len(pts) == expected
    assert any(any(0 < v < 1 for v in p.values()) for p in pts) is has_fraction
    assert all(sum(p.values()) <= gamma + TOL for p in pts)


def test_T08_integer_continuous_equals_binary_budget():
    d = example_a(); plan = zero_plan(d)
    continuous = certify_plan(d, plan).worst_gap
    binary = max(solve_phase1(d, plan, {s: 0 for s in d.S}, {"v1": z}).objective for z in (0, 1))
    assert continuous == pytest.approx(binary)


def test_T09_pre_budget_monotonicity():
    values = []
    for budget in (4, 5):
        d = example_a(); d.B_pre = budget; values.append(solve_direct(d).objective)
    assert values[1] <= values[0] + TOL


def test_T10_risk_set_monotonicity():
    plan = FirstStagePlan({"j": 0}, {"k": 0}, {"k": 0})
    gaps = []
    costs = []
    for gamma in (0, 0.5, 1):
        d = example_b(); d.Gamma3 = gamma
        gaps.append(certify_plan(d, plan).worst_gap); costs.append(solve_direct(d).objective)
    assert gaps == sorted(gaps) and costs == sorted(costs)


def test_T11_alpha_monotonicity():
    costs = []
    for alpha in (0.5, 1.0):
        d = example_b(); d.alpha = {"HV": alpha}; costs.append(solve_direct(d).objective)
    assert costs[1] + TOL >= costs[0]


def test_T12_cost_accounting_once_and_activation_only():
    d = example_b(); result = solve_direct(d)
    investment = 2 * result.plan.x["j"] + result.plan.r["k"]
    assert result.objective == pytest.approx(investment)
    assert result.objective == pytest.approx(0.5)
    assert result.plan.y["k"] == 1


def test_T13_infeasible_is_reported():
    d = example_b(); d.Xbar = {"j": 0}; d.Rbar = {"k": 0}; d.Gamma3 = 1
    result = solve_direct(d)
    assert result.status == "INFEASIBLE" and not result.certified_optimal


@pytest.mark.parametrize("factory,expected", [(example_a, 4.0), (example_b, 0.5)])
def test_T14_direct_and_ccg_agree(factory, expected):
    d = factory(); direct = solve_direct(d); ccg = solve_ccg(d)
    assert direct.certified_optimal and ccg.certified_optimal
    assert direct.objective == pytest.approx(expected)
    assert ccg.objective == pytest.approx(direct.objective)
    assert direct.worst_gap <= TOL and ccg.worst_gap <= TOL


def test_T15_seeded_random_legal_instances_direct_equals_ccg():
    rng = random.Random(20261103)
    for _ in range(5):
        d = example_b()
        d.Cbar = {"k": rng.uniform(0.8, 1.3)}
        d.delta = {"k": rng.uniform(0.2, 1.0)}
        d.Gamma3 = rng.choice([0.0, 0.5, 1.0])
        d.cI = {"j": rng.uniform(1.2, 3.0)}
        d.cR = {"k": rng.uniform(0.5, 1.1)}
        d.validate()
        direct, ccg = solve_direct(d), solve_ccg(d)
        assert direct.status == ccg.status
        if direct.status == "OPTIMAL":
            assert direct.objective == pytest.approx(ccg.objective, abs=1e-6)


def test_T16_status_and_exactness_guards():
    assert status_name(GRB.INFEASIBLE) == "INFEASIBLE"
    assert status_name(GRB.UNBOUNDED) == "UNBOUNDED"
    assert status_name(GRB.INF_OR_UNBD) == "INF_OR_UNBOUNDED"
    assert status_name(GRB.TIME_LIMIT) == "TIME_LIMIT"
    assert status_name(GRB.NUMERIC) == "NUMERIC"
    class NoLicense:
        def optimize(self):
            raise gp.GurobiError(10009, "No Gurobi license found")
    assert _safe_optimize(NoLicense())[0] == "LICENSE_ERROR"
    with pytest.raises(ExactEnumerationUnavailable, match="当前没有可用"):
        joint_extreme_points(("a", "b"), ("x", "y"), 2, 2, max_scenarios=1)


def test_parameter_physical_consistency_rejects_illegal_b():
    d = example_b(); d.N = set()
    with pytest.raises(ValueError, match="positive b"):
        d.validate()
