"""One fold's statistics, shared by Ridge and tree transforms; never global fit."""
import json
from pathlib import Path

import numpy as np

from ..policy_cv_protocol_v1 import require
from ..v3_feature_extractor.manifest import MODEL_INSTANCE_ID, canonical, identity
from .dataset import FEATURE_NAMES, VIEW_VERSION


class FoldPreprocessor:
    def __init__(self):
        self.state = None

    def fit(self, batch, *, fold):
        require(self.state is None, "Fit once; create a fresh preprocessor for every fold/refit")
        require(set(batch.sample_ids) == set(fold.training_ids), "Fit must use exactly this fold's training samples")
        require(not set(batch.sample_ids) & set(fold.heldout_ids), "Held-out sample in preprocessing fit")
        require(batch.feature_names == FEATURE_NAMES, "Preprocessing schema conflict")
        X = batch.X
        observed = (~np.isnan(X)).sum(axis=0)
        mean = np.divide(np.nansum(X, axis=0), observed, out=np.zeros(78), where=observed > 0)
        filled = np.where(np.isnan(X), mean, X)
        scale = np.sqrt(np.mean((filled-mean)**2, axis=0))
        scale[scale == 0] = 1.0
        self.state = dict(view_version=VIEW_VERSION, model_instance_id=MODEL_INSTANCE_ID, fold_id=fold.fold_id, feature_order=list(FEATURE_NAMES),
            fit_sample_ids=list(batch.sample_ids), fit_sample_ids_sha256=identity("samples-", sorted(batch.sample_ids)),
            mean=mean.tolist(), scale=scale.tolist(), observed_counts=observed.tolist(),
            all_missing_columns=[FEATURE_NAMES[i] for i in np.flatnonzero(observed == 0)],
            missing_rule="training mean; all-training-missing -> 0 with indicator=1; zero variance scale=1")
        return self

    def transform(self, batch, mode):
        require(self.state is not None, "Preprocessor is unfitted")
        require(mode in ("ridge", "tree") and batch.feature_names == tuple(self.state["feature_order"]), "Transform schema/mode conflict")
        mask = np.isnan(batch.X)
        result = np.where(mask, self.state["mean"], batch.X)
        if mode == "ridge":
            result = (result-self.state["mean"])/self.state["scale"]
        result = np.column_stack((result, mask.astype(float)))
        require(result.shape == (len(batch.sample_ids), 156) and np.isfinite(result).all(), "Invalid transformed matrix")
        return result

    def save(self, path):
        require(self.state is not None, "Cannot save an unfitted preprocessor")
        with Path(path).open("x", encoding="utf-8") as stream:
            stream.write(canonical(self.state)+"\n")

    @classmethod
    def load(cls, path):
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        require(state["view_version"] == VIEW_VERSION and state["model_instance_id"] == MODEL_INSTANCE_ID
                and state["feature_order"] == list(FEATURE_NAMES), "Saved preprocessor version/order conflict")
        require(all(len(state[k]) == 78 for k in ("mean", "scale", "observed_counts")), "Saved statistics length conflict")
        require(np.isfinite(state["mean"]).all() and np.isfinite(state["scale"]).all()
                and min(state["scale"]) > 0, "Invalid saved statistics")
        obj = cls()
        obj.state = state
        return obj
