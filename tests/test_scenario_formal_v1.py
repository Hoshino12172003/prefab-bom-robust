"""View isolation and frozen protocol checks before formal training."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from scenario_agent.training.dataset import FEATURE_NAMES, FEATURE_SPECS, TrainingDataset
from scenario_agent.training.fold_loader import PolicyFoldLoader
from scenario_agent.training.formal import ViewPreprocessor, feature_views, freeze


def test_views_exclude_graph_and_identity():
    views=feature_views()
    assert [len(x) for x in views.values()]==[39,44,78]
    for s in FEATURE_SPECS:
        if s.name in views["Risk-only"]:
            assert "graph" not in s.source and "BOM" not in s.source
    assert not {"policy_id","scenario_id","effective_rhs_id","run_id"}&set(views["Full-78"])


def test_nonselected_features_cannot_affect_model_input():
    dataset=TrainingDataset(Path(__file__).resolve().parents[1])
    fold=PolicyFoldLoader(dataset).inner[0]
    batch=dataset.batch(fold.training_ids)
    for view in ("Risk-only","Risk+Master"):
        a=ViewPreprocessor(view).fit(batch,fold=fold)
        X=batch.X.copy()
        indices=[i for i,n in enumerate(FEATURE_NAMES) if n not in feature_views()[view]]
        X[:,indices]+=10000
        other=replace(batch,X=X)
        b=ViewPreprocessor(view).fit(other,fold=fold)
        for mode in ("ridge","tree"):
            assert np.array_equal(a.transform(batch,mode),b.transform(other,mode))


def test_protocol_freeze_no_overwrite(tmp_path):
    dataset=TrainingDataset(Path(__file__).resolve().parents[1])
    out=tmp_path/"formal"
    protocol=freeze(dataset,out)
    assert protocol["expected_estimator_fits"]==510
    assert protocol["learning_rate_grid"]==[0.05]
    assert protocol["outer_test_model_selection"] is False
    with pytest.raises(ValueError,match="Refuse overwrite"):
        freeze(dataset,out)


def test_view_preprocessor_serialization(tmp_path):
    import joblib
    dataset=TrainingDataset(Path(__file__).resolve().parents[1])
    fold=PolicyFoldLoader(dataset).inner[0]
    batch=dataset.batch(fold.training_ids)
    prep=ViewPreprocessor("Risk-only").fit(batch,fold=fold)
    path=tmp_path/"prep.joblib"
    joblib.dump(prep,path)
    loaded=joblib.load(path)
    assert np.array_equal(prep.transform(batch,"ridge"),loaded.transform(batch,"ridge"))
