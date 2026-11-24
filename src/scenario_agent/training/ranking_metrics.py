"""Full-group metrics; exact ground-truth ties remain ties."""
from collections import defaultdict

import numpy as np

from ..policy_cv_protocol_v1 import require


def rank_groups(batch, predictions):
    scores = np.asarray(predictions, dtype=float)
    require(scores.shape == (len(batch.sample_ids),) and np.isfinite(scores).all(), "Invalid predictions")
    groups = defaultdict(list)
    for i, key in enumerate(batch.group_keys):
        groups[key].append(i)
    # Identity is used only to make PREDICTED score ties reproducible, never as a model feature.
    return {key: sorted(indices, key=lambda i: (scores[i], batch.scenario_ids[i])) for key, indices in groups.items()}


def group_metrics(Q, predictions, *, orders=None, in_Q_units=True):
    from scipy.stats import kendalltau
    Q, predictions = np.asarray(Q, dtype=float), np.asarray(predictions, dtype=float)
    require(Q.ndim == 1 and Q.shape == predictions.shape and len(Q) >= 2, "Invalid ranking group")
    require(np.isfinite(Q).all() and np.isfinite(predictions).all(), "Nonfinite ranking input")
    order = list(orders) if orders is not None else list(np.argsort(predictions, kind="stable"))
    worst = set(np.flatnonzero(Q == Q.min()).tolist())
    tau = float(kendalltau(Q, predictions, variant="b").statistic)
    error = predictions-Q
    return dict(worst_recall_at_1=len(set(order[:1]) & worst)/len(worst),
        worst_recall_at_3=len(set(order[:3]) & worst)/len(worst),
        mean_reciprocal_rank=1/min(j+1 for j, i in enumerate(order) if i in worst),
        kendall_tau_b=tau if np.isfinite(tau) else None,
        mae=float(np.mean(np.abs(error))) if in_Q_units else None,
        rmse=float(np.sqrt(np.mean(error**2))) if in_Q_units else None,
        worst_tie_count=len(worst), candidate_count=len(Q))


METRICS = ("worst_recall_at_1", "worst_recall_at_3", "mean_reciprocal_rank", "kendall_tau_b", "mae", "rmse")


def macro_average(rows):
    return {name: dict(value=float(np.mean(valid)) if (valid := [r[name] for r in rows if r[name] is not None]) else None,
                       valid_groups=len(valid), undefined_groups=len(rows)-len(valid)) for name in METRICS}


def evaluate_predictions(batch, Q, predictions, *, in_Q_units=True, orders=None):
    orders = rank_groups(batch, predictions) if orders is None else orders
    rows, policies = [], defaultdict(list)
    for key, order in orders.items():
        indices = [i for i, k in enumerate(batch.group_keys) if k == key]
        require(len({batch.policy_ids[i] for i in indices}) == 1, "Group mixes policies")
        local = {global_i: local_i for local_i, global_i in enumerate(indices)}
        result = group_metrics(np.asarray(Q)[indices], np.asarray(predictions)[indices],
                               orders=[local[i] for i in order], in_Q_units=in_Q_units)
        row = dict(group_key=key, policy_id=batch.policy_ids[indices[0]], **result)
        rows.append(row)
        policies[row["policy_id"]].append(row)
    by_policy = {p: macro_average(values) for p, values in policies.items()}
    policy_macro = {name: float(np.mean(v)) if (v := [s[name]["value"] for s in by_policy.values()
                         if s[name]["value"] is not None]) else None for name in METRICS}
    return dict(groups=rows, by_policy=by_policy, policy_macro=policy_macro,
                regression_metrics_note="Q units" if in_Q_units else "NOT_APPLICABLE_dimensionless_rule_score")
