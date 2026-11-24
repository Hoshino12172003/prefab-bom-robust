"""Features read exclusively from a prediction-time Master snapshot."""
from .schema import FeatureSpec

SPECS = tuple(FeatureSpec(n, dtype, unit, formula, "MasterStateV3", nullable) for n, dtype, unit, formula, nullable in (
    ("master_iteration", "int64", "iteration_count", "iteration_id", False),
    ("buffer_C", "int64", "complete_cell_kit", "policy[0]", False),
    ("buffer_T", "int64", "Pack", "policy[1]", False),
    ("buffer_O", "int64", "Pack", "policy[2]", False),
    ("master_active_count", "int64", "RHS_count", "len(active_rhs_ids)", False),
    ("master_budget", "float64", "normalized_investment", "17388/19", False),
    ("master_remaining_budget", "float64", "normalized_investment", "budget-sum(cost[i]*policy[i])", False),
    ("master_ub", "int64", "vehicle", "current exact Master upper", False),
    ("master_lb_before", "int64", "vehicle", "previous certified lower; first round NULL", True),
    ("master_lb_initialized", "int64", "boolean", "lb_before is not NULL", False),
))


def extract(state):
    return dict(zip((s.name for s in SPECS), (state.iteration_id, *state.policy, len(state.active_rhs_ids),
        float(state.budget), float(state.budget-state.spent), state.ub, state.lb_before_oracle,
        int(state.lb_before_oracle is not None))))
