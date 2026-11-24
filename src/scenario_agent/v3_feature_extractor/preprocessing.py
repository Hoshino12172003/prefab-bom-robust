"""Separate, explicit fit/transform preprocessing; never fitted during conversion."""
import json
from math import sqrt
from pathlib import Path

from .extractor import SPECS
from .manifest import MODEL_INSTANCE_ID, canonical, identity
from .schema import FEATURE_VERSION, validate_features


class FeaturePreprocessorV3:
    def __init__(self, mode="ridge"):
        if mode not in ("ridge", "tree"):
            raise ValueError("Unknown preprocessing mode")
        self.mode = mode
        self.state = None

    @property
    def feature_names(self):
        names = tuple(s.name for s in SPECS)
        return names + tuple(n+"__missing" for n in names)

    def _raw(self, vector):
        if vector.feature_version != FEATURE_VERSION or vector.model_instance_id != MODEL_INSTANCE_ID:
            raise ValueError("Preprocessing feature/model version conflict")
        values = vector.as_dict()
        validate_features(values, SPECS)
        return tuple(values.values())

    def fit(self, vectors, *, training_split_id):
        if self.state is not None or not training_split_id:
            raise ValueError("Fit once with an explicit training split identity")
        rows = [self._raw(v) for v in vectors]
        if not rows:
            raise ValueError("Empty preprocessing training fold")
        columns = list(zip(*rows))
        centers, scales, counts = [], [], []
        for col in columns:
            observed = [float(v) for v in col if v is not None]
            mean = sum(observed)/len(observed) if observed else 0.0
            # NULL stays NULL in raw data; an all-missing training column uses a flagged numeric baseline.
            variance = sum((v-mean)**2 for v in observed)/len(col)
            centers.append(mean)
            scales.append(sqrt(variance) if variance else 1.0)
            counts.append(len(observed))
        self.state = dict(feature_version=FEATURE_VERSION, model_instance_id=MODEL_INSTANCE_ID,
            mode=self.mode, feature_names=[s.name for s in SPECS], training_split_id=training_split_id,
            training_rows_sha256=identity("rows-", rows), mean=centers, scale=scales, observed_counts=counts)
        return self

    def transform(self, vectors):
        if self.state is None:
            raise ValueError("Preprocessor is not fitted")
        result = []
        for vector in vectors:
            row = self._raw(vector)
            filled = [self.state["mean"][i] if v is None else float(v) for i, v in enumerate(row)]
            if self.mode == "ridge":
                filled = [(v-self.state["mean"][i])/self.state["scale"][i] for i, v in enumerate(filled)]
            result.append(tuple(filled + [int(v is None) for v in row]))
        return result

    def save(self, path):
        if self.state is None:
            raise ValueError("Cannot save fitted parameters before explicit training-fold fit")
        with Path(path).open("x", encoding="utf-8") as f:
            f.write(canonical(self.state)+"\n")

    @classmethod
    def load(cls, path):
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        if (state["feature_version"] != FEATURE_VERSION or state["model_instance_id"] != MODEL_INSTANCE_ID
                or state["feature_names"] != [s.name for s in SPECS]
                or any(len(state[k]) != len(SPECS) for k in ("mean", "scale", "observed_counts"))
                or any(v <= 0 for v in state["scale"])):
            raise ValueError("Saved preprocessing schema conflict")
        obj = cls(state["mode"])
        obj.state = state
        return obj
