import pytest

from prefab_v3.implicit_ccg import OracleError, WorstScenario, generate
from prefab_v3.plain_ccg import BoundError, MasterSolution


def worst(q, scenario, exact=True, frontier=0):
    return WorstScenario(q, scenario, exact, frontier, {})


def test_maximization_bounds_match_explicit_robust_optimum():
    values = {"A": (10, 2, 7), "B": (8, 6, 5), "C": (7, 7, 6)}
    def master(active, _):
        indices = [ord(s)-ord("A") for s in active]
        return max((MasterSolution(min(q[i] for i in indices), (p,), {}) for p, q in values.items()),
                   key=lambda mp: mp.objective)
    def oracle(policy, _):
        q, s = min((q, "ABC"[i]) for i, q in enumerate(values[policy[0]]))
        return worst(q, s)
    result = generate(("A",), 3, master, oracle)
    answer = max(map(min, values.values()))
    assert result["objective"] == answer == 6
    assert all(row["lower"] <= answer <= row["upper"] for row in result["iterations"])
    assert [r["upper"] for r in result["iterations"]] == [10, 7, 6]
    assert [r["added_scenario"] for r in result["iterations"]] == ["B", "C", ""]


@pytest.mark.parametrize("certificate", (worst(10, "B", False), worst(10, "B", True, 1)))
def test_open_frontier_cannot_close_the_gap(certificate):
    with pytest.raises(OracleError, match="unresolved"):
        generate(("A",), 2, lambda *_: MasterSolution(10, (0,), {}), lambda *_: certificate)


def test_active_scenario_cannot_be_a_strict_violation():
    with pytest.raises(BoundError, match="active scenario"):
        generate(("A",), 2, lambda *_: MasterSolution(10, (0,), {}), lambda *_: worst(9, "A"))


def test_oracle_value_above_master_is_rejected():
    with pytest.raises(BoundError, match="upper bound"):
        generate(("A",), 2, lambda *_: MasterSolution(10, (0,), {}), lambda *_: worst(11, "B"))


def test_increasing_master_upper_bound_is_rejected():
    with pytest.raises(BoundError, match="upper bound"):
        generate(("A",), 2, lambda _, k: MasterSolution(9+k, (0,), {}), lambda *_: worst(9, "B"))
