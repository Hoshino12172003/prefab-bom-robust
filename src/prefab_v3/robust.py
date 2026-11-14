"""Combinatorial disruption trajectories and complete V3 scenario blocks."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

import gurobipy as gp
from gurobipy import GRB

from prefab_v25.data import BUFFER_EFFECTS, CELL, PROD, PRODUCTION_ARC, TRANSPORT_ARC
from .base import Weights, add_block
from .interface import add_stage_one

RESOURCE_IDS = ("L1_CELL_RECEIPTS", "L2_PACK_PRODUCTION", "L3_PACK_TRANSPORT")


@dataclass(frozen=True)
class Episode:
    start: int
    duration: int
    severity: Fraction


@dataclass(frozen=True)
class UncertaintySet:
    """One contiguous episode per resource, with a resource-period budget."""

    periods: tuple
    durations: tuple
    severities: tuple
    gamma: int
    concurrency: int
    recovery_steps: int = 0

    def __post_init__(self):
        if not self.periods or self.periods != tuple(range(self.periods[0], self.periods[-1]+1)):
            raise ValueError("periods must form a nonempty consecutive calendar")
        if not self.durations or self.durations != tuple(sorted(set(self.durations))) or any(
                type(d) is not int or not 1 <= d <= len(self.periods) for d in self.durations):
            raise ValueError("durations must be ordered unique positive feasible integers")
        if not self.severities or self.severities != tuple(sorted(set(self.severities))) or any(
                not isinstance(s, Fraction) or not 0 < s <= 1 for s in self.severities):
            raise ValueError("severities must be ordered unique positive fractions")
        if type(self.gamma) is not int or self.gamma < 0 or type(self.concurrency) is not int or not (
                1 <= self.concurrency <= len(RESOURCE_IDS)):
            raise ValueError("invalid disruption budget or concurrency")
        if type(self.recovery_steps) is not int or self.recovery_steps < 0:
            raise ValueError("invalid recovery length")

    def intervals(self):
        return tuple((start, duration) for duration in self.durations for start in self.periods
                     if start+duration-1 <= self.periods[-1])

    def feasible_masks(self):
        """Enumerate feasible z supports for audit, independently of severity."""
        masks = (0, *((((1 << d)-1) << (t-self.periods[0])) for t,d in self.intervals()))
        for selected in product(masks, repeat=len(RESOURCE_IDS)):
            if self.feasible_mask_tuple(selected):
                yield selected

    def feasible_mask_tuple(self, masks):
        if sum(m.bit_count() for m in masks) > self.gamma:
            return False
        if self.concurrency == 2:
            return not (masks[0] & masks[1] & masks[2])
        if self.concurrency == 1:
            return sum(m.bit_count() for m in masks) == (masks[0]|masks[1]|masks[2]).bit_count()
        return True

    def validate(self, episodes):
        if len(episodes) != len(RESOURCE_IDS):
            raise ValueError("one episode slot per declared resource")
        masks = []
        for e in episodes:
            if e is None:
                masks.append(0)
            elif (e.start,e.duration) not in self.intervals() or e.severity not in self.severities:
                raise ValueError("ineligible episode")
            else:
                masks.append(((1 << e.duration)-1) << (e.start-self.periods[0]))
        if not self.feasible_mask_tuple(masks):
            raise ValueError("trajectory exceeds its disruption budget or concurrency")

    def factors(self, episode):
        """Return remaining availability for all dates, including recovery."""
        if episode is None:
            return (Fraction(1),)*len(self.periods)
        result = []
        for t in self.periods:
            offset = t-episode.start
            if 0 <= offset < episode.duration:
                factor = 1-episode.severity
            elif episode.duration <= offset < episode.duration+self.recovery_steps:
                recovery_day = offset-episode.duration+1
                factor = 1-episode.severity*(1-Fraction(recovery_day,self.recovery_steps+1))
            else:
                factor = Fraction(1)
            result.append(factor)
        return tuple(result)

    def attenuation(self, episodes, arrivals):
        self.validate(episodes)
        l1,l2,l3 = (dict(zip(self.periods,self.factors(e))) for e in episodes)
        available = {key:(int(q*l1[key[2]]) if key[:1]==(PROD,) and key[1] in CELL else q)
                     for key,q in arrivals.items()}
        factors = {(*arc,t):f for arc,series in ((PRODUCTION_ARC,l2),(TRANSPORT_ARC,l3))
                   for t,f in series.items() if f!=1}
        return available,factors


def on_time(block, base):
    return gp.quicksum(block.outflow[g.id,t] for g in base.network.groups
                       for t in base.network.periods if t<=g.representative.due)


def protection_inventory(x):
    if len(x) != 3:
        raise ValueError("three buffer decisions required")
    return {key:amount*variable for variable,entries in zip(x,BUFFER_EFFECTS) for key,amount in entries}


def add_recourse(model, base, state, uncertainty, episodes, x, prefix):
    state.validate(base)
    if uncertainty.periods != base.network.periods:
        raise ValueError("risk and operational periods differ")
    arrivals,factors = uncertainty.attenuation(episodes,state.arrivals)
    return add_block(model,base,prefix,Weights(0,0,0,0,0),reschedule=True,
                     regular=state.inventory,fixed_receipts=arrivals,protection=protection_inventory(x),
                     arc_factors=factors,external_limits=state.external_limits,
                     scheduled_equalities=state.scheduled_equalities)


def add_selected_scenarios(model, base, state, costs, budget, uncertainty, scenarios):
    """Build the finite direct validation model for caller-selected trajectories."""
    if not scenarios or len({name for name,_ in scenarios}) != len(scenarios):
        raise ValueError("scenario names must be unique and nonempty")
    x = add_stage_one(model,costs,budget)
    guarantee = model.addVar(lb=0,ub=base.network.demand_weight,name="guaranteed_on_time")
    blocks = {}
    for name,episodes in scenarios:
        block = add_recourse(model,base,state,uncertainty,episodes,x,name)
        blocks[name] = block
        model.addConstr(guarantee<=on_time(block,base))
    model.setObjective(guarantee,GRB.MAXIMIZE)
    return x,guarantee,blocks
