"""Project the shared raw extractor, with labels and identifiers kept outside X."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np

from ..policy_cv_protocol_v1 import HISTORY_FIELDS, load_inputs, require
from ..v3_feature_extractor import ScenarioFeatureExtractorV3
from ..v3_feature_extractor.extractor import FeatureVectorV3, SPECS
from ..v3_feature_extractor.manifest import MODEL_INSTANCE_ID, digest
from ..v3_feature_extractor.schema import FEATURE_VERSION, validate_features

VIEW_VERSION = "v1.conservative78.1"
FEATURE_SPECS = tuple(s for s in SPECS if s.name not in HISTORY_FIELDS)
FEATURE_NAMES = tuple(s.name for s in FEATURE_SPECS)
POLICY_PROTOCOL_SHA256 = {
    "split_manifest_policy_cv_v1.json": "8c9135328ae3b875a9184c4d1014aae0e53ebc0a3b5f12a88373c695328d0fcc",
    "nested_cv_protocol_v1.json": "8ea2cd507ee9dd51993a1027c0673660a2fa157d7943b1b874ffbfb7ffd87cc9",
}


class ConservativeFeatureView:
    feature_names = FEATURE_NAMES
    specs = FEATURE_SPECS

    def project(self, vector):
        require(vector.model_instance_id == MODEL_INSTANCE_ID and vector.feature_version == FEATURE_VERSION,
                "Raw feature/model version conflict")
        raw = vector.as_dict()
        validate_features(raw, SPECS)
        result = {name: raw[name] for name in self.feature_names}
        validate_features(result, self.specs)
        return result

    def extract(self, network, scenario, master_state):
        # This is the only raw feature computation for both replay and future callers.
        return self.project(ScenarioFeatureExtractorV3().extract(network, scenario, master_state))


@dataclass(frozen=True)
class FeatureBatch:
    X: np.ndarray
    sample_ids: tuple
    group_keys: tuple
    policy_ids: tuple
    rhs_ids: tuple
    scenario_ids: tuple
    feature_names: tuple = FEATURE_NAMES

    def __post_init__(self):
        require(self.feature_names == FEATURE_NAMES and self.X.shape == (len(self.sample_ids), 78),
                "Expected ordered conservative 78-column matrix")
        require(len(set(self.sample_ids)) == len(self.sample_ids) > 0, "Empty/duplicate feature batch")
        require(all(len(v) == len(self.sample_ids) for v in
                    (self.group_keys, self.policy_ids, self.rhs_ids, self.scenario_ids)), "Metadata length conflict")
        require(not np.isinf(self.X).any(), "Infinite feature value")
        for i, spec in enumerate(FEATURE_SPECS):
            col = self.X[:, i]
            require(spec.nullable or not np.isnan(col).any(), f"Unexpected NULL: {spec.name}")
            if spec.dtype == "int64":
                values = col[~np.isnan(col)]
                require(np.equal(values, np.floor(values)).all(), f"Noninteger feature: {spec.name}")


class TrainingDataset:
    def __init__(self, root, data=None):
        self.root = Path(root).resolve()
        self.data = Path(data).resolve() if data else self.root / "experiments/scenario_agent_v1/data/v3"
        X, labels, groups, self.raw_manifest, self.input_hashes = load_inputs(self.root, self.data)
        self.outer = json.loads((self.data / "split_manifest_policy_cv_v1.json").read_text(encoding="utf-8"))
        self.inner = json.loads((self.data / "nested_cv_protocol_v1.json").read_text(encoding="utf-8"))
        base_hashes = dict(self.input_hashes)
        for name, manifest in (("split_manifest_policy_cv_v1.json", self.outer), ("nested_cv_protocol_v1.json", self.inner)):
            require(digest(self.data/name) == POLICY_PROTOCOL_SHA256[name], "Frozen policy protocol SHA-256 conflict")
            require(manifest["original_inputs_sha256"] == base_hashes, "Policy CV input hashes changed")
            require(manifest["protocol_code_sha256"] == digest(self.root / "src/scenario_agent/policy_cv_protocol_v1.py"),
                    "Frozen policy CV implementation changed")
            require(manifest["primary_feature_view"]["selected_feature_order"] == list(FEATURE_NAMES), "Frozen 78-column order conflict")
            require(manifest["primary_feature_view"]["excluded_fields"] == list(HISTORY_FIELDS), "History exclusions changed")
            self.input_hashes[name] = digest(self.data / name)
        self.groups = {g["group_key"]: g for g in groups}
        self.labels_by_id = {r["sample_id"]: r for r in labels}
        self.meta = {}
        self.features = {}
        view = ConservativeFeatureView()
        for group in groups:
            for row in group["rows"]:
                sid = row["sample_id"]
                values = {}
                for spec in SPECS:
                    value = X[int(row["X_data_row"])-1][spec.name]
                    values[spec.name] = None if value == "" else (int(value) if spec.dtype == "int64" else float(value))
                selected = view.project(FeatureVectorV3(MODEL_INSTANCE_ID, FEATURE_VERSION, values))
                self.features[sid] = tuple(selected.values())
                self.meta[sid] = (group["group_key"], group["policy_id"], row["effective_rhs_id"], row["scenario_id"])

    def batch(self, sample_ids):
        ids = tuple(sample_ids)
        require(set(ids) <= self.features.keys(), "Unknown sample")
        columns = tuple(zip(*(self.meta[sid] for sid in ids))) if ids else ((),)*4
        X = np.array([self.features[sid] for sid in ids], dtype=float)
        X.setflags(write=False)
        return FeatureBatch(X, ids, *columns)

    def targets(self, sample_ids):
        # No rank, UB, is_violating or disruption-loss target is exposed to regressors.
        return np.array([float(self.labels_by_id[sid]["Q_exact"]) for sid in sample_ids])

    def feature_manifest(self):
        return dict(view_version=VIEW_VERSION, model_instance_id=MODEL_INSTANCE_ID, raw_feature_version=FEATURE_VERSION,
            raw_columns=84, selected_columns=78, feature_fields=[asdict(s) for s in FEATURE_SPECS],
            excluded_fields=list(HISTORY_FIELDS), source_hashes=self.input_hashes,
            extractor="ScenarioFeatureExtractorV3.extract", adapter="ConservativeFeatureView.project",
            original_X_modified=False, new_raw_features_added=False,
            missing_rule="raw NULL retained; fold-training mean imputation plus fixed 78 missing indicators in preprocessing",
            transformed_feature_names=list(FEATURE_NAMES)+[n+"__missing" for n in FEATURE_NAMES])
