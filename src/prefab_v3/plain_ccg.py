"""Exact finite scenario-block generation with certified integer recourse."""
from dataclasses import dataclass
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from .base import Weights, add_block
from .interface import add_stage_one
from .robust import on_time, protection_inventory


TOLERANCE = 1e-6
TIE_BREAK = "Lexicographically smallest scenario ID among all exact worst ties"


class BoundError(RuntimeError):
    """The certified master and oracle contradict the bound invariants."""


@dataclass(frozen=True)
class MasterSolution:
    objective: int
    policy: tuple
    metrics: dict


@dataclass(frozen=True)
class Result:
    objective: int
    policy: tuple
    selected: tuple
    verified_services: dict
    iterations: tuple
    verification_seconds: float


def add_recourse_block(model, base, name, profile, policy):
    arrivals, factors = profile
    return add_block(model, base, name, Weights(0, 0, 0, 0, 0), reschedule=True,
                     fixed_receipts=arrivals, arc_factors=factors,
                     protection=protection_inventory(policy))


def build_master(model, base, profiles, selected, costs, budget):
    selected = tuple(selected)
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= profiles.keys():
        raise ValueError("master needs a nonempty set of distinct benchmark scenarios")
    policy = add_stage_one(model, costs, budget)
    eta = model.addVar(ub=base.network.demand_weight, vtype=GRB.INTEGER, name="eta")
    blocks = {}
    for name in selected:
        block = add_recourse_block(model, base, name, profiles[name], policy)
        blocks[name] = block
        model.addConstr(eta <= on_time(block, base), name=f"guarantee[{name}]")
    model.setObjective(eta, GRB.MAXIMIZE)
    return policy, eta, blocks


def generate(scenarios, initial, solve_master, solve_recourse):
    """Each callback must return a global integer optimum or raise."""
    names, selected = tuple(scenarios), tuple(initial)
    if not names or len(set(names)) != len(names):
        raise ValueError("benchmark needs distinct scenario IDs")
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(names):
        raise ValueError("initial blocks must be a nonempty subset of the benchmark")

    start = perf_counter()
    iterations = []
    upper = float("inf")
    lower = -1
    incumbent = None
    for k in range(1, len(names) - len(selected) + 2):
        before = perf_counter()
        master = solve_master(selected, k)
        after_master = perf_counter()
        services = {name: solve_recourse(name, master.policy, f"oracle_{k:02d}") for name in names}
        after_oracle = perf_counter()
        worst = min(services.values())
        ties = tuple(sorted(name for name, q in services.items() if q == worst))
        if master.objective > upper or any(services[name] < master.objective for name in selected):
            raise BoundError("master upper bound increased or exceeded selected-scenario recourse")
        upper = master.objective
        if worst > lower:
            lower, incumbent = worst, master.policy
        if lower > upper:
            raise BoundError("full-set incumbent lower bound exceeds master upper bound")
        gap = upper - lower
        added = ties[0] if gap > TOLERANCE else ""
        if added and (added in selected or worst >= master.objective):
            raise BoundError("the exact separating scenario does not strictly violate the master")
        iterations.append(dict(iteration=k, master_scenarios=selected, added_scenario=added,
                               policy=master.policy, mp_objective=master.objective, upper=upper,
                               oracle_worst=worst, worst_ties=ties, selected_tie=ties[0],
                               lower=lower, best_policy=incumbent, absolute_gap=gap,
                               relative_gap=gap / max(1, abs(upper)),
                               master_seconds=after_master-before, oracle_seconds=after_oracle-after_master,
                               total_seconds=after_oracle-start, **master.metrics))
        if gap <= TOLERANCE:
            start_verify = perf_counter()
            verified = {name: solve_recourse(name, incumbent, "verify") for name in names}
            if min(verified.values()) != lower:
                raise BoundError("fresh full-set verification differs from certified incumbent")
            return Result(lower, incumbent, selected, verified, tuple(iterations), perf_counter()-start_verify)
        selected += (added,)
    raise BoundError("the finite set was exhausted without bound closure")
