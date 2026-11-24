from pathlib import Path

from scenario_agent.portable import portable_replay_root
from scenario_agent.training.dataset import TrainingDataset
from scenario_agent.v3_feature_extractor import load_standardized_v3


def test_portable_root_preserves_legacy_checkout():
    root=Path(__file__).resolve().parents[1]
    legacy=root/"artifacts/v3_phase31r_20261111_202237/design.py"
    before=legacy.read_bytes()
    with portable_replay_root(root) as replay:
        data=TrainingDataset(replay)
        network=load_standardized_v3(replay,data.data)
        assert len(network.tables["nodes"])==12
        assert len(data.features)==576
    assert legacy.read_bytes()==before
