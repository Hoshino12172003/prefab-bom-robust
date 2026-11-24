"""Closed prediction-time input types and ordered numeric feature contract."""
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite

from .manifest import MODEL_INSTANCE_ID, identity

FEATURE_VERSION = "v3.features.1.0.0"
PERIODS = tuple(range(61, 75))
COSTS = (Fraction(1), Fraction(27, 19), Fraction(297, 190))
BUDGET = Fraction(17388, 19)
CELL = ("componment_battery1", "componment_battery2", "componment_battery3")
BUFFER_STATES = (("battery-supplier_prod", CELL[0]), ("battery-supplier_inv", "BEV"), ("zp7", "BEV"))
RESOURCES = ("B_RECEIPT", "B_PROD", "B_SHIP", "ENGINE", "GEAR", "SEAT")
RESOURCE_ARCS = {
    "B_PROD": ("battery-supplier_prod", "battery-supplier_inv"),
    "B_SHIP": ("battery-supplier_inv", "zp7"),
    "ENGINE": ("engine-supplier_prod", "engine-supplier_inv"),
    "GEAR": ("gear-supplier_inv", "zp7"), "SEAT": ("seat-supplier_inv", "zp7"),
}


@dataclass(frozen=True)
class MasterStateV3:
    model_instance_id: str
    iteration_id: int
    policy: tuple
    active_rhs_ids: tuple
    ub: int
    lb_before_oracle: int | None
    budget: Fraction = BUDGET
    costs: tuple = COSTS
    run_id: str = "online"

    def __post_init__(self):
        if self.model_instance_id != MODEL_INSTANCE_ID or self.budget != BUDGET or self.costs != COSTS:
            raise ValueError("V3 model/budget/unit identity conflict")
        if type(self.iteration_id) is not int or self.iteration_id < 1:
            raise ValueError("Invalid iteration")
        if len(self.policy) != 3 or any(type(x) is not int or x < 0 for x in self.policy):
            raise ValueError("V3 requires three nonnegative integer buffers")
        if self.spent > self.budget or type(self.ub) is not int or not 0 <= self.ub <= 28000:
            raise ValueError("Infeasible budget or service upper bound")
        if self.lb_before_oracle is not None and (
                type(self.lb_before_oracle) is not int or not 0 <= self.lb_before_oracle <= self.ub):
            raise ValueError("Invalid prediction-time lower bound")
        if self.iteration_id == 1 and self.lb_before_oracle is not None:
            raise ValueError("First historical round has no initialized certified LB")
        if not self.active_rhs_ids or len(set(self.active_rhs_ids)) != len(self.active_rhs_ids):
            raise ValueError("Active RHS identities must be distinct and nonempty")

    @property
    def spent(self):
        return sum(c*x for c, x in zip(self.costs, self.policy))

    @property
    def state_id(self):
        return identity("state-", {"model": self.model_instance_id, "run": self.run_id, "iteration": self.iteration_id,
            "policy": self.policy, "active": sorted(self.active_rhs_ids), "ub": self.ub,
            "lb_before": self.lb_before_oracle, "budget": str(self.budget), "costs": list(map(str, self.costs))})


@dataclass(frozen=True)
class ScenarioV3:
    model_instance_id: str
    name: str
    representative: str
    rhs_id: str
    events: tuple
    changes: tuple


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    dtype: str
    unit: str
    formula: str
    source: str
    nullable: bool = False
    information_time: str = "after_master_before_oracle"


def validate_features(values, specs):
    if tuple(values) != tuple(s.name for s in specs):
        raise ValueError("Feature names/order conflict")
    for s in specs:
        v = values[s.name]
        if v is None:
            if not s.nullable:
                raise ValueError(f"Unexpected missing value: {s.name}")
        elif s.dtype == "int64" and type(v) is not int:
            raise ValueError(f"Expected integer: {s.name}")
        elif not isinstance(v, (int, float)) or not isfinite(v):
            raise ValueError(f"Expected finite numeric feature: {s.name}")
