"""Audit diagnostics and timing only; no regression estimator fits."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scenario_agent.training.audit import eligibility, partition_statistics
from scenario_agent.training.baselines import make_pairwise_ranker
from scenario_agent.training.dataset import TrainingDataset
from scenario_agent.training.fold_loader import PolicyFoldLoader
from scenario_agent.training.nested_cv import _evaluate


@pytest.fixture(scope="module")
def dataset():
    return TrainingDataset(Path(__file__).resolve().parents[1])


def test_all_25_fold_statistics_reconcile(dataset):
    loader=PolicyFoldLoader(dataset)
    for f in (*loader.outer,*loader.inner):
        for ids,known in ((f.training_ids,f.training_stats),(f.heldout_ids,f.heldout_stats)):
            s=partition_statistics(dataset,ids)
            assert s["query_count"]==known["query_count"]
            assert s["is_worst_positive"]==known["is_worst_positive"]
            assert sum(s["Q_exact"]["value_counts"].values())==len(ids)
            assert len(s["feature_statistics"])==78
            assert s["missing_cells"]==np.isnan(dataset.batch(ids).X).sum()
            assert s["Q_exact"]["min"]<s["Q_exact"]["max"]
        assert eligibility(partition_statistics(dataset,f.training_ids))==[]


def test_constant_target_and_no_ranking_groups_block():
    assert eligibility({"informative_ranking_groups":0,"Q_exact":{"min":7,"max":7}})==[
        "NO_INFORMATIVE_RANKING_GROUP","CONSTANT_TARGET"]


def test_near_constant_definition_includes_null(dataset,monkeypatch):
    fold=PolicyFoldLoader(dataset).outer[0]
    real=dataset.batch
    batch=real(fold.training_ids)
    X=batch.X.copy()
    X[:,0]=1
    X[0,0]=2
    # A nullable column with one observed value and otherwise missing.
    j=11
    X[:,j]=np.nan
    X[0,j]=0.5
    monkeypatch.setattr(dataset,"batch",lambda ids:SimpleNamespace(X=X,policy_ids=batch.policy_ids,group_keys=batch.group_keys))
    s=partition_statistics(dataset,fold.training_ids)
    assert s["feature_statistics"][0]["near_constant"]
    assert not s["feature_statistics"][0]["constant"]
    assert s["feature_statistics"][j]["near_constant"]
    assert s["feature_statistics"][j]["observed_constant"]


def test_prediction_and_preprocessing_timers_are_separate():
    batch=SimpleNamespace(sample_ids=("a","b"),group_keys=("g","g"),policy_ids=("p","p"),scenario_ids=("a","b"))
    ds=SimpleNamespace(targets=lambda ids:np.array([1,2]))
    prep=SimpleNamespace(transform=lambda b,mode:np.zeros((2,156)))
    out=_evaluate(ds,batch,lambda X:np.array([0,0]),preprocessor=prep,mode="ridge")
    assert out["prediction_sort_seconds"]==out["preprocessing_seconds"]+out["prediction_seconds"]+out["sorting_seconds"]
    assert all(out[k]>=0 for k in ("preprocessing_seconds","prediction_seconds","sorting_seconds"))
    with pytest.raises(NotImplementedError,match="PAIRWISE_RANKING_DEFERRED"):
        make_pairwise_ranker()
