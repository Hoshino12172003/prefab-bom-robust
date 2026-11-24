"""Deployable rule and training-catalog references, with no Oracle access at predict."""
from collections import defaultdict

import numpy as np

from ..policy_cv_protocol_v1 import require
from ..v3_feature_extractor.schema import RESOURCES
from .dataset import FEATURE_NAMES


class RuleBasedBaseline:
    def predict(self, batch):
        scores = []
        for row in batch.X:
            x = dict(zip(FEATURE_NAMES, row))
            burden = 0.0
            for resource in RESOURCES:
                prefix = f"risk_{resource}_"
                if x[prefix+"present"]:
                    severity, duration = x[prefix+"severity_loss"], x[prefix+"duration"]
                    effective = x[prefix+"mean_effective_loss_rate"] if x[prefix+"changed_rows"] else 0.0
                    require(np.isfinite([severity, duration, effective]).all(), "Incomplete present-resource rule inputs")
                    burden += (0.5*severity+0.5*effective)*duration/14
            scores.append(-burden)
        return np.array(scores)


class CatalogHistoryBaseline:
    def __init__(self):
        self.mean_by_rhs = None

    def fit(self, batch, Q, *, fold):
        require(self.mean_by_rhs is None and set(batch.sample_ids) == set(fold.training_ids), "Catalog fit must use exactly fold training data")
        require(len(Q) == len(batch.sample_ids) and np.isfinite(Q).all(), "Invalid training Q")
        pairs = defaultdict(set)
        for policy, rhs, q in zip(batch.policy_ids, batch.rhs_ids, Q):
            pairs[policy, rhs].add(float(q))
        require(all(len(v) == 1 for v in pairs.values()), "Repeated train policy/RHS has conflicting exact Q")
        values = defaultdict(list)
        for (_, rhs), q in pairs.items():
            values[rhs].append(next(iter(q)))
        self.mean_by_rhs = {rhs: float(np.mean(v)) for rhs, v in values.items()}
        # Unseen-in-training catalog entry: only the training-policy/RHS grand mean.
        self.fallback = float(np.mean([next(iter(q)) for q in pairs.values()]))
        self.fit_sample_ids = tuple(batch.sample_ids)
        return self

    def predict(self, batch):
        require(self.mean_by_rhs is not None, "Catalog baseline is unfitted")
        return np.array([self.mean_by_rhs.get(rhs, self.fallback) for rhs in batch.rhs_ids])
