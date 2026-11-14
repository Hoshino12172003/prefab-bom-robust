from fractions import Fraction
from itertools import combinations

import pytest

from prefab_v3.event_budget import Event, EventBudget
from prefab_v3.robust import Episode


B, G, S = "B_RECEIPT", "GEAR", "SEAT"
BUDGET = EventBudget((B, "B_PROD", "B_SHIP", G, S, "ENGINE"), tuple(range(61, 75)))


def event(r, start, duration, severity=Fraction(1, 2)):
    return Event(r, Episode(start, duration, severity))


def test_a_battery_seven_days_at_gamma_one():
    assert BUDGET.validate((event(B, 61, 7),), 1) == 7


def test_b_seat_eleven_days_at_gamma_one():
    assert BUDGET.validate((event(S, 64, 11),), 1) == 11


def test_c_overlapping_battery_gear_at_gamma_two():
    pair = (event(B, 61, 4), event(G, 61, 4))
    assert BUDGET.validate(pair, 2) == 8
    with pytest.raises(ValueError, match="daily concurrency"):
        BUDGET.validate(pair, 2, concurrency=1)


def test_d_three_seven_day_events_with_and_without_triple_overlap():
    first = (event(B, 61, 7), event(G, 61, 7))
    assert BUDGET.validate(first + (event(S, 68, 7),), 3) == 21
    overlap = first + (event(S, 67, 7),)
    with pytest.raises(ValueError, match="daily concurrency"):
        BUDGET.validate(overlap, 3)
    assert BUDGET.validate(overlap, 3, concurrency=3) == 21


@pytest.mark.parametrize("pair", tuple(combinations((B, G, S), 2)))
def test_e_joint_families_rejected_at_gamma_one(pair):
    with pytest.raises(ValueError, match="event count"):
        BUDGET.validate(tuple(event(r, 61, 4) for r in pair), 1)


def test_exposure_is_diagnostic_and_resources_are_unique():
    assert BUDGET.validate((), 1) == 0
    assert BUDGET.validate((event(B, 61, 11), event(G, 61, 11)), 2) == 22
    with pytest.raises(ValueError, match="duplicate or unknown"):
        BUDGET.validate((event(B, 61, 4), event(B, 65, 4)), 2)
    with pytest.raises(ValueError, match="duplicate or unknown"):
        BUDGET.validate((event("unknown", 61, 4),), 1)


@pytest.mark.parametrize("bad", (
    event(B, 65, 11), event(B, 60, 4), event(B, 61, 5),
    event(B, 61, 4, Fraction(1)), Event(B, Episode(61, 4, Fraction(1, 2)), "GRADUAL_RECOVERY"),
))
def test_only_frozen_core_choices(bad):
    with pytest.raises(ValueError, match="ineligible episode"):
        BUDGET.validate((bad,), 1)
