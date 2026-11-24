"""Small, frozen search spaces; constructors do not fit estimators."""
from ..policy_cv_protocol_v1 import require

RIDGE_GRID = ({"alpha": 0.1}, {"alpha": 1.0}, {"alpha": 10.0}, {"alpha": 100.0})
GB_GRID = tuple(dict(max_depth=depth, min_samples_leaf=leaf) for depth in (1, 2) for leaf in (8, 16))
GB_FIXED = dict(n_estimators=50, learning_rate=0.05, max_leaf_nodes=4, loss="squared_error",
                subsample=1.0, n_iter_no_change=None, random_state=0)


def make_regressor(name, parameters):
    if name == "ridge":
        from sklearn.linear_model import Ridge
        require(parameters in RIDGE_GRID, "Unfrozen Ridge parameters")
        return Ridge(**parameters, fit_intercept=True, solver="svd")
    require(name == "gradient_boosting" and parameters in GB_GRID, "Unfrozen model/GB parameters")
    from sklearn.ensemble import GradientBoostingRegressor
    return GradientBoostingRegressor(**GB_FIXED, **parameters)
