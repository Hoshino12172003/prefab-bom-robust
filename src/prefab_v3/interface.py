"""Prospective two-stage interfaces for the full source-model block."""
from dataclasses import dataclass, field, replace
from fractions import Fraction
from math import lcm

import gurobipy as gp
from gurobipy import GRB

from prefab_v25.data import BUFFER_EFFECTS, NOMINAL, receipts
from .base import add_block


@dataclass(frozen=True)
class RegularState:
    inventory: dict
    arrivals: dict
    evidence: str
    external_limits: dict = field(default_factory=dict)
    scheduled_equalities: dict = field(default_factory=dict)

    @classmethod
    def from_dispatches(cls, base, inventory, dispatches, evidence, **kwargs):
        network = base.network
        qualified = {(a.origin,a.destination,p) for a in network.arcs for p in a.recipes}
        dispatches = tuple(dispatches)
        if any((i,j,p) not in qualified or type(t) is not int or type(q) is not int or q<0
               for i,j,p,t,q in dispatches):
            raise ValueError("invalid prospective historical dispatch")
        arrivals = receipts(replace(network,historical=dispatches),NOMINAL)
        return cls(inventory,arrivals,evidence,**kwargs)

    def validate(self, base):
        if not self.evidence.strip():
            raise ValueError("prospective regular state requires provenance")
        network = base.network
        keys = set(network.state_keys())
        if set(self.inventory) != keys:
            raise ValueError("prospective inventory must enumerate every active state key")
        if self.inventory == network.initial and self.arrivals == receipts(network,NOMINAL):
            raise ValueError("prospective regular state equals the historical stressed snapshot")
        if any((n,p) not in keys or t not in network.periods for n,p,t in self.arrivals):
            raise ValueError("invalid prospective in-transit receipt key")
        for data in (self.inventory,self.arrivals,self.external_limits,self.scheduled_equalities):
            if any(type(v) is not int or v<0 for v in data.values()):
                raise ValueError("regular quantities must be nonnegative integers")
        if any((n,p) not in network.external or t not in network.periods for n,p,t in self.external_limits):
            raise ValueError("invalid regular external supply limit")
        arcs = {a.key:a for a in network.arcs}
        if any((i,j) not in arcs or p not in arcs[i,j].recipes or t not in network.periods
               for i,j,p,t in self.scheduled_equalities):
            raise ValueError("invalid scheduled equality")


@dataclass(frozen=True)
class Effect:
    layer: str
    target_kind: str
    target: tuple
    start: int
    severity: Fraction
    duration: int
    recovery: tuple = ()

    def path(self, periods):
        severity = Fraction(str(self.severity))
        recovery = tuple(Fraction(str(x)) for x in self.recovery)
        if not 0 <= severity <= 1 or self.start not in periods or type(self.duration) is not int or self.duration<1:
            raise ValueError("invalid severity or timing")
        if any(not 0<=x<=1 for x in recovery) or tuple(sorted(recovery))!=recovery or (
                recovery and recovery[0]<1-severity):
            raise ValueError("recovery must be nondecreasing from the disrupted factor")
        return {t: (1-severity if t<self.start+self.duration else recovery[t-self.start-self.duration]
                    if t-self.start-self.duration<len(recovery) else Fraction(1))
                for t in periods if t>=self.start}


@dataclass(frozen=True)
class Disruption:
    name: str
    effects: tuple = ()
    active: frozenset = frozenset()


@dataclass(frozen=True)
class BudgetedUncertainty:
    """Finite activation schema with optional calibration supplied by callers."""
    eligible: frozenset
    gamma: int | None = None

    def validate(self, scenario):
        if not scenario.active <= self.eligible:
            raise ValueError("unrecognized resource-period activation")
        required = {(effect.target_kind,effect.target,effect.start) for effect in scenario.effects}
        if required != scenario.active:
            raise ValueError("activation and effect records differ")
        if self.gamma is not None and (type(self.gamma) is not int or self.gamma<0 or len(scenario.active)>self.gamma):
            raise ValueError("invalid disruption budget")


def add_stage_one(model, costs, budget):
    costs = tuple(Fraction(str(c)) for c in costs)
    budget = Fraction(str(budget))
    if len(costs)!=3 or min(costs)<=0 or budget<0:
        raise ValueError("three positive costs and nonnegative budget required")
    x = tuple(model.addVar(vtype=GRB.INTEGER,name=name) for name in ("x_C","x_T","x_O"))
    scale = lcm(budget.denominator,*(c.denominator for c in costs))
    model.addConstr(gp.quicksum(int(scale*c)*v for c,v in zip(costs,x))<=int(scale*budget),name="investment_budget")
    return x


def add_scenario_block(model, base, state, x, scenario, *, combine_factors=None, **kwargs):
    """Build one full recourse block under a shared policy or a fixed policy."""
    state.validate(base)
    periods = base.network.periods
    arc_keys = {a.key for a in base.network.arcs}
    factors = {}
    arrivals = dict(state.arrivals)
    limits = dict(state.external_limits)
    paths = {}
    for effect in scenario.effects:
        if effect.target_kind not in ("arc_capacity","regular_receipt","external_cap"):
            raise ValueError("unsupported risk mechanism")
        if effect.target_kind=="arc_capacity" and effect.target not in arc_keys:
            raise ValueError("unrecognized risk arc")
        if effect.target_kind=="regular_receipt" and effect.target not in {
                (n,p) for n,p,_ in state.arrivals}:
            raise ValueError("unrecognized regular arrival target")
        if effect.target_kind=="external_cap" and effect.target not in base.network.external:
            raise ValueError("unrecognized external supply target")
        for t,factor in effect.path(periods).items():
            if factor == 1:
                continue
            key = effect.target_kind,(*effect.target,t)
            if key in paths:
                if combine_factors is None:
                    raise ValueError("overlapping effects require a caller-supplied composition rule")
                factor = Fraction(str(combine_factors(paths[key],factor)))
                if not 0<=factor<=1:
                    raise ValueError("invalid combined disruption factor")
            paths[key] = factor
    for (kind,key),factor in paths.items():
        if kind=="arc_capacity":
            factors[key]=factor
        elif kind=="regular_receipt":
            if key in arrivals:
                arrivals[key]=int(arrivals[key]*factor)
        elif kind=="external_cap":
            if key not in limits:
                raise ValueError("risk on external supply requires a regular supply limit")
            limits[key]=int(limits[key]*factor)
    if len(x)!=3:
        raise ValueError("three protection variables required")
    protection = {key:coef*value for value,entries in zip(x,BUFFER_EFFECTS) for key,coef in entries}
    return add_block(model,base,scenario.name,regular=state.inventory,fixed_receipts=arrivals,
                     protection=protection,arc_factors=factors,external_limits=limits,
                     scheduled_equalities=state.scheduled_equalities,**kwargs)


def add_master(model, base, state, costs, budget, scenarios, score, **kwargs):
    """Attach selected scenario blocks and a common lower bound on caller-defined service."""
    if not scenarios or len({s.name for s in scenarios})!=len(scenarios):
        raise ValueError("selected scenarios must be nonempty and uniquely named")
    x=add_stage_one(model,costs,budget)
    guarantee=model.addVar(lb=-GRB.INFINITY,name="guaranteed_service")
    blocks={}
    for s in scenarios:
        block=add_scenario_block(model,base,state,x,s,**kwargs)
        blocks[s.name]=block
        model.addConstr(guarantee<=score(block))
    return x,guarantee,blocks
