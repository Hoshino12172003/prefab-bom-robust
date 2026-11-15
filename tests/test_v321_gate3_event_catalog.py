from fractions import Fraction
from importlib import import_module
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo / "experiments/v321_gate3_direct_de"))
    return import_module("event_catalog")


def test_event_days_recovery_and_budget_count(module):
    period = range(61, 75)
    event = next(e for e in module.EVENTS if e.id == "BAT_PROD")
    profile = event.profile(period)
    assert [profile[(*event.asset, t)] for t in range(64, 69)] == list(map(Fraction, ("0.4", "0.4", "0.4", "0.6", "0.8")))
    assert (*event.asset, 69) not in profile
    arcs = {e.asset for e in module.EVENTS}
    nominal = {(*arc, t): 100 for arc in arcs for t in period}
    tracks, mapping = module.enumerate_scenarios(module.EVENTS, 1, nominal, period)
    assert len(tracks) == len(mapping) == 9
    assert next(r for r in mapping if r["scenario"] == "BAT_PROD")["event_count"] == 1


def test_overlap_repeat_and_different_resource(module):
    events = {e.id: e for e in module.EVENTS}
    period = range(61, 75)
    assert module.compatibility((events["BAT_PROD"], events["BAT_PROD_ALT"]), period) == "OVERLAPPING_SAME_ASSET"
    assert module.compatibility((events["BAT_PROD"], events["BAT_PROD"]), period) == "DUPLICATE_EVENT"
    assert module.compatibility((events["BAT_PROD"], events["BAT_OEM"]), period) == "LEGAL"
    assert module.compatibility((events["BAT_PROD"], events["SEAT_PROD"]), period) == "LEGAL"


def test_equal_effective_capacity_dedup_maps_original_combination(module):
    ep = module.EVENTS[0]
    periods = range(61,75)
    # The event changes multipliers during zero capacity slots only.
    nominal = {(*ep.asset, t): int(t == 61) for t in periods}
    unique, mapping = module.enumerate_scenarios((ep,),1,nominal,periods)
    assert list(unique) == ["NOM"]
    assert mapping[1]["combination"] == ep.id and mapping[1]["scenario"] == "NOM" and mapping[1]["deduplicated"]
