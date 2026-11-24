"""The one raw feature implementation for historical and future prediction use."""
from dataclasses import dataclass
from types import MappingProxyType

from . import network_features, scenario_features, master_features, interaction_features
from .manifest import MODEL_INSTANCE_ID
from .schema import FEATURE_VERSION, MasterStateV3, validate_features

SPECS = (network_features.SPECS + scenario_features.SPECS + master_features.SPECS + interaction_features.SPECS)


@dataclass(frozen=True)
class FeatureVectorV3:
    model_instance_id: str
    feature_version: str
    values: object

    def as_dict(self):
        return dict(self.values)


class ScenarioFeatureExtractorV3:
    specs = SPECS
    feature_names = tuple(s.name for s in SPECS)
    feature_version = FEATURE_VERSION

    def extract(self, network, scenario, master_state):
        if (network.model_instance_id != MODEL_INSTANCE_ID or network.model_version != "V3_HISTORICAL_SERVICE"
                or scenario.model_instance_id != MODEL_INSTANCE_ID or not isinstance(master_state, MasterStateV3)
                or master_state.model_instance_id != MODEL_INSTANCE_ID):
            raise ValueError("V3/V3.3 feature identity conflict")
        if scenario_features.rhs_hash(scenario_features.signature(network, scenario.events)) != scenario.rhs_id:
            raise ValueError("Scenario input/RHS conflict")
        if scenario_features.signature(network, scenario.events) != scenario.changes:
            raise ValueError("Scenario changed-row conflict")
        values = {**network_features.extract(network), **scenario_features.extract(network, scenario),
                  **master_features.extract(master_state), **interaction_features.extract(network, scenario, master_state)}
        validate_features(values, self.specs)
        return FeatureVectorV3(MODEL_INSTANCE_ID, FEATURE_VERSION, MappingProxyType(values))
