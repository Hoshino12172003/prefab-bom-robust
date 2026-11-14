from fractions import Fraction

import pytest

from prefab_v3.robust import Episode, UncertaintySet


PERIODS = tuple(range(61, 75))
SEVERITIES = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
CORE_DURATIONS = (4, 7, 11)


@pytest.mark.parametrize("gamma", (2, 4, 6))
@pytest.mark.parametrize("duration", CORE_DURATIONS)
def test_single_episode_consumes_its_duration(gamma, duration):
    validator = UncertaintySet(PERIODS, CORE_DURATIONS, SEVERITIES, gamma, 2)
    validator.validate((None, None, None))
    # Check both boundary starts and all core severities on the frozen validator.
    for start in (PERIODS[0], PERIODS[-1] - duration + 1):
        for severity in SEVERITIES:
            for slot in range(3):
                episodes = tuple(Episode(start, duration, severity) if i == slot else None
                                 for i in range(3))
                if duration <= gamma:
                    validator.validate(episodes)
                else:
                    with pytest.raises(ValueError, match="budget or concurrency"):
                        validator.validate(episodes)


@pytest.mark.parametrize("second_start", (61, 63, 65))
def test_two_minimum_core_episodes_exceed_gamma_six(second_start):
    validator = UncertaintySet(PERIODS, CORE_DURATIONS, SEVERITIES, 6, 2)
    episodes = (Episode(61, 4, SEVERITIES[0]), Episode(second_start, 4, SEVERITIES[0]), None)
    validator.validate((episodes[0], None, None))
    validator.validate((None, episodes[1], None))
    with pytest.raises(ValueError, match="budget or concurrency"):
        validator.validate(episodes)


def test_concurrency_is_separate_from_exposure_budget():
    validator = UncertaintySet(PERIODS, (1, 3, 5), SEVERITIES, 6, 2)
    three_days = Episode(61, 3, SEVERITIES[1])
    validator.validate((three_days, three_days, None))
    one_day = Episode(61, 1, SEVERITIES[1])
    with pytest.raises(ValueError, match="budget or concurrency"):
        validator.validate((one_day, one_day, one_day))
    validator.validate((one_day, one_day, Episode(62, 1, SEVERITIES[1])))


def test_recovery_tail_changes_factors_without_consuming_exposure():
    validator = UncertaintySet(PERIODS, CORE_DURATIONS, SEVERITIES, 4, 2, recovery_steps=2)
    episode = Episode(61, 4, SEVERITIES[2])
    validator.validate((episode, None, None))
    assert validator.factors(episode)[:7] == (
        Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4),
        Fraction(1, 2), Fraction(3, 4), Fraction(1),
    )
