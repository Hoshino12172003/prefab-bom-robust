from fractions import Fraction
from importlib import import_module
from pathlib import Path

import pytest


@pytest.fixture
def recovery_module(monkeypatch):
    root = Path(__file__).resolve().parents[1] / "experiments"
    monkeypatch.syspath_prepend(str(root / "v321_gate3_direct_de"))
    monkeypatch.syspath_prepend(str(root / "v33_gate36_recovery_objective"))
    return import_module("recovery")


def test_backlog_carries_open_order_through_tail(recovery_module):
    backlog = recovery_module.backlog_series
    assert backlog(2, 74, {71: 1}, 97) == [1] * 24
    assert backlog(2, 74, {74: 1, 75: 1}, 97) == [1] + [0] * 23
    assert sum(backlog(2, 74, {74: 1, 76: 1}, 97)) - sum(backlog(2, 74, {74: 1, 75: 1}, 97)) == 1


def test_equal_ot_secondary_chooses_earlier_late_delivery(recovery_module):
    gp = pytest.importorskip("gurobipy")
    backlog = recovery_module.backlog_series
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model(env=env) as model:
            choice = model.addVars((75, 77), vtype=gp.GRB.BINARY)
            model.addConstr(choice.sum() == 1)
            model.setObjective(sum(sum(backlog(2, 74, {74: 1, t: 1}, 97)) * v for t, v in choice.items()))
            model.optimize()
            assert model.Status == gp.GRB.OPTIMAL and model.MIPGap == 0
            assert choice[75].X == 1 and model.ObjVal == 1


def test_recovery_curve_crosses_demand_boundary(recovery_module):
    Event = import_module("event_catalog").Event
    asset = ("engine-supplier_prod", "engine-supplier_inv")
    periods = range(61, 98)
    e = Event("crossing", asset, "production", 74, 1, Fraction(2, 5), 2)
    profile = e.profile(periods)
    assert [profile.get((*asset, t), 1) for t in (74, 75, 76, 77, 97)] == [Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), 1, 1]
