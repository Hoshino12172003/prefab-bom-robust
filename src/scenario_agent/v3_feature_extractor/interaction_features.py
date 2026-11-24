"""Physically indexed structural interactions, not recourse-loss predictions."""
from .network_features import reach, risk_reach, due_groups
from .schema import BUFFER_STATES, FeatureSpec

SPECS = [FeatureSpec("scenario_already_active", "int64", "boolean", "scenario.RHS in active RHS", "scenario + Master")]
for position in "CTO":
    for name, dtype, unit, formula, nullable in (
        ("timed_exposed_orders", "int64", "vehicle", "exposed cohorts intersect cohorts reachable from buffer at 61 before due", False),
        ("units_per_exposed_order", "float64", "Pack_equivalent_per_vehicle", "buffer quantity / timed exposed orders; no feasibility claim", True),
        ("bypassed_battery_resources", "int64", "resource_count", "count present battery risks at or upstream of buffer injection", False),
    ):
        SPECS.append(FeatureSpec(f"buffer_{position}_{name}", dtype, unit, formula, "V3 recipes/lead + events + policy", nullable))
SPECS = tuple(SPECS)


def extract(network, scenario, state):
    exposed = due_groups(network, risk_reach(network, scenario))
    out = {"scenario_already_active": int(scenario.rhs_id in state.active_rhs_ids)}
    stages = {"B_RECEIPT": 0, "B_PROD": 1, "B_SHIP": 2}
    for index, (position, key, quantity) in enumerate(zip("CTO", BUFFER_STATES, state.policy)):
        # C uses a COMPLETE 10/6/4 kit; all three cells share the same timing path.
        supported = due_groups(network, reach(network, {key: 61}))
        count = sum(len(exposed[g].orders) for g in exposed.keys() & supported.keys())
        out.update({f"buffer_{position}_timed_exposed_orders": count,
            f"buffer_{position}_units_per_exposed_order": quantity/count if count else None,
            f"buffer_{position}_bypassed_battery_resources": sum(
                resource in stages and stages[resource] <= index for resource, *_ in scenario.events)})
    return out
