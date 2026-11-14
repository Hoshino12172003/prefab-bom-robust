"""Phase 3.2A scenario-block bounds with a certified implicit oracle."""

from dataclasses import dataclass
from time import perf_counter

from .plain_ccg import BoundError, TOLERANCE


class OracleError(RuntimeError):
    """A proposed separation lacks a complete exact certificate."""


@dataclass(frozen=True)
class WorstScenario:
    value: int
    scenario: str
    exact: bool
    frontier_size: int
    metrics: dict


def generate(initial, rhs_count, master, oracle):
    selected = tuple(initial)
    if not selected or len(set(selected)) != len(selected) or len(selected) > rhs_count:
        raise ValueError("invalid initial scenario blocks")
    upper, lower, best = float("inf"), -1, None
    iterations = []
    for k in range(1, rhs_count-len(selected)+2):
        started = perf_counter()
        mp = master(selected, k)
        after_master = perf_counter()
        result = oracle(mp.policy, k)
        after_oracle = perf_counter()
        if not result.exact or result.frontier_size != 0:
            raise OracleError("oracle has an unresolved frontier")
        if mp.objective > upper or result.value > mp.objective:
            raise BoundError("invalid maximization upper bound")
        upper = mp.objective
        if result.value > lower:
            lower, best = result.value, mp.policy
        if lower > upper:
            raise BoundError("robust lower bound exceeds master upper bound")
        gap = upper-lower
        added = result.scenario if gap > TOLERANCE else ""
        if result.scenario in selected and result.value < mp.objective:
            raise BoundError("active scenario contradicts its master block")
        if added and result.value >= mp.objective:
            raise BoundError("worst scenario does not strictly violate the master")
        iterations.append(dict(iteration=k, master_scenarios=selected, policy=mp.policy,
                               upper=upper, lower=lower, best_policy=best, absolute_gap=gap,
                               oracle_worst=result.value, worst_scenario=result.scenario,
                               added_scenario=added, master_seconds=after_master-started,
                               oracle_seconds=after_oracle-after_master, **mp.metrics, **result.metrics))
        if gap <= TOLERANCE:
            return dict(objective=lower, policy=best, selected=selected, iterations=iterations)
        selected += (added,)
    raise BoundError("effective scenario limit reached without bound closure")
