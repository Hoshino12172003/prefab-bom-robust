"""Conservative pipeline preflight, with no learned estimator ever fitted."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from scenario_agent.training import nested_cv
from scenario_agent.training.baseline_models import CatalogHistoryBaseline, RuleBasedBaseline
from scenario_agent.training.dataset import ConservativeFeatureView, FEATURE_NAMES, FEATURE_SPECS, FeatureBatch, TrainingDataset
from scenario_agent.training.fold_loader import PolicyFoldLoader
from scenario_agent.training.preprocessing import FoldPreprocessor
from scenario_agent.training.ranking_metrics import evaluate_predictions, group_metrics, rank_groups
from scenario_agent.training.regression_models import GB_FIXED, GB_GRID, RIDGE_GRID, make_regressor
from scenario_agent.training.training_manifest import configs, run_preflight
from scenario_agent.v3_feature_extractor.manifest import digest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def dataset():
    return TrainingDataset(ROOT)


@pytest.fixture(scope="module")
def loader(dataset):
    return PolicyFoldLoader(dataset)


@pytest.fixture(scope="module")
def preflight(tmp_path_factory):
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import GradientBoostingRegressor

    def forbidden(*args, **kwargs):
        raise AssertionError("No estimator fit/predict permitted in preflight")

    output = tmp_path_factory.mktemp("training-preflight")
    with pytest.MonkeyPatch.context() as mp:
        for cls in (Ridge, GradientBoostingRegressor):
            mp.setattr(cls, "fit", forbidden)
            mp.setattr(cls, "predict", forbidden)
        execution = run_preflight(ROOT, output)
    return output, execution


def test_frozen_78_columns_types_units_and_no_identity(dataset):
    assert len(FEATURE_NAMES) == 78
    assert list(FEATURE_NAMES) == dataset.outer["primary_feature_view"]["selected_feature_order"]
    original = {s["name"]: s for s in dataset.raw_manifest["feature_fields"]}
    for spec in FEATURE_SPECS:
        assert spec.unit == original[spec.name]["unit"] and spec.dtype == original[spec.name]["dtype"]
        assert spec.nullable == original[spec.name]["nullable"]
    assert not {"policy_id", "run_id", "master_state_id", "Q_exact", "is_worst", "effective_rhs_id"} & set(FEATURE_NAMES)
    manifest = dataset.feature_manifest()
    assert len(manifest["transformed_feature_names"]) == 156
    for name in manifest["excluded_fields"]:
        assert name not in FEATURE_NAMES and name+"__missing" not in manifest["transformed_feature_names"]


def test_576_replay_and_indirect_history_isolation(preflight):
    replay = preflight[1]["replay_and_isolation"]
    assert replay["historical_replay_pass"] == replay["excluded_history_perturbation_pass"] == 576
    assert replay["extractor_calls"] == 1153
    assert replay["future_unseen_policy"] == [100,100,0]
    assert replay["indirect_history_dependency_detected"] is False


def test_all_folds_execute_only_their_preprocessing(preflight, dataset):
    execution = preflight[1]
    assert len(execution["fold_preflight"]) == execution["preprocessing_fit_calls"] == 25
    assert sum(r["kind"] == "outer" for r in execution["fold_preflight"]) == 5
    assert sum(r["kind"] == "inner" for r in execution["fold_preflight"]) == 20
    for row in execution["fold_preflight"]:
        assert set(row["preprocessing_fit_sample_ids"]) == set(row["training_sample_ids"])
        assert not set(row["training_sample_ids"]) & set(row["heldout_sample_ids"])
        assert row["finite_transform_both_modes"] and not row["state_exported"]
    assert execution["estimator_fit_calls"] == execution["estimator_prediction_calls"] == execution["optimization_calls"] == 0
    for name, expected in execution["input_sha256"].items():
        assert digest(dataset.data/name) == expected


def test_preprocessor_statistics_transform_and_roundtrip(dataset, loader, tmp_path):
    fold = loader.inner[0]
    train, val = dataset.batch(fold.training_ids), dataset.batch(fold.heldout_ids)
    prep = FoldPreprocessor().fit(train, fold=fold)
    observed = (~np.isnan(train.X)).sum(axis=0)
    mean = np.divide(np.nansum(train.X, axis=0), observed, out=np.zeros(78), where=observed > 0)
    assert np.allclose(prep.state["mean"], mean)
    before = json.dumps(prep.state, sort_keys=True)
    extreme = val.X.copy()
    extreme[:, 0] += 1000000
    transformed = prep.transform(replace(val, X=extreme), "ridge")
    assert json.dumps(prep.state, sort_keys=True) == before
    assert transformed.shape == (len(val.sample_ids),156) and np.isfinite(transformed).all()
    assert np.array_equal(transformed[:,78:], np.isnan(val.X))
    prep.save(tmp_path/"prep.json")
    restored = FoldPreprocessor.load(tmp_path/"prep.json")
    assert np.array_equal(prep.transform(val,"ridge"), restored.transform(val,"ridge"))
    assert np.array_equal(prep.transform(val,"tree"), restored.transform(val,"tree"))


def test_fit_rejects_wrong_fold_refit_and_bad_feature_schema(dataset, loader):
    fold = loader.inner[0]
    train, val = dataset.batch(fold.training_ids), dataset.batch(fold.heldout_ids)
    with pytest.raises(ValueError, match="exactly this fold"):
        FoldPreprocessor().fit(val, fold=fold)
    prep = FoldPreprocessor().fit(train, fold=fold)
    with pytest.raises(ValueError, match="Fit once"):
        prep.fit(train, fold=fold)
    with pytest.raises(ValueError, match="unfitted"):
        FoldPreprocessor().transform(val,"tree")
    with pytest.raises(ValueError, match="78-column"):
        replace(train, feature_names=tuple(reversed(FEATURE_NAMES)))


def synthetic_batch(dataset, ids, policies, rhs):
    seed = dataset.batch([next(iter(dataset.features))])
    X = np.repeat(seed.X, len(ids), axis=0)
    return FeatureBatch(X, tuple(ids), tuple("g"+p for p in policies), tuple(policies), tuple(rhs), tuple(ids))


def test_all_missing_column_baseline_is_flagged_not_silent(dataset):
    batch = synthetic_batch(dataset, ["a","b"], ["p","p"], ["r","r"])
    X = batch.X.copy()
    index = FEATURE_NAMES.index("risk_B_RECEIPT_severity_loss")
    X[:,index] = np.nan
    batch = replace(batch, X=X)
    fold = SimpleNamespace(training_ids=batch.sample_ids, heldout_ids=("v",), fold_id="synthetic")
    prep = FoldPreprocessor().fit(batch, fold=fold)
    out = prep.transform(batch,"tree")
    assert np.array_equal(out[:,index], [0,0]) and np.array_equal(out[:,78+index], [1,1])
    assert "risk_B_RECEIPT_severity_loss" in prep.state["all_missing_columns"]


def test_rule_uses_only_audited_static_inputs(dataset):
    sid = next(s for s in dataset.features if dataset.labels_by_id[s]["scenario_id"] == "NR")
    batch = dataset.batch([sid])
    assert RuleBasedBaseline().predict(batch)[0] == 0
    X = batch.X.copy()
    for name, value in (("present",1),("severity_loss",0.5),("duration",2),("changed_rows",1),("mean_effective_loss_rate",0.25)):
        X[0,FEATURE_NAMES.index("risk_B_RECEIPT_"+name)] = value
    risk = replace(batch,X=X)
    score = RuleBasedBaseline().predict(risk)[0]
    assert score == pytest.approx(-(0.5*0.5+0.5*0.25)*2/14)
    # Physical buffer and remaining budget cannot enter this STATIC heuristic.
    X[0,FEATURE_NAMES.index("buffer_C")] = 123
    X[0,FEATURE_NAMES.index("master_remaining_budget")] = 456
    assert RuleBasedBaseline().predict(replace(batch,X=X))[0] == score


def test_catalog_mean_is_train_only_alias_aware_and_repeat_balanced(dataset):
    batch = synthetic_batch(dataset,["a","b","c"],["p1","p1","p2"],["r","r","r"])
    fold = SimpleNamespace(training_ids=batch.sample_ids, heldout_ids=("t",))
    model = CatalogHistoryBaseline().fit(batch, np.array([10,10,30]),fold=fold)
    test = synthetic_batch(dataset,["t","u"],["p3","p3"],["r","new"])
    assert np.array_equal(model.predict(test), [20,20])
    assert model.mean_by_rhs == {"r":20}
    with pytest.raises(ValueError, match="exactly fold"):
        CatalogHistoryBaseline().fit(test,np.array([999,999]),fold=fold)
    weights = nested_cv.training_weights(batch)
    assert weights[:2].sum() == weights[2]
    assert weights.mean() == 1


def test_grid_constructors_have_no_fitting_or_early_stopping():
    for params in RIDGE_GRID:
        estimator = make_regressor("ridge",params)
        assert estimator.alpha > 0 and estimator.solver == "svd"
        assert not hasattr(estimator,"coef_")
    for params in GB_GRID:
        estimator = make_regressor("gradient_boosting",params)
        assert estimator.max_depth <= 2 and estimator.max_leaf_nodes <= 4 and estimator.min_samples_leaf >= 8
        assert estimator.n_iter_no_change is None and not hasattr(estimator,"estimators_")
    with pytest.raises(ValueError,match="Unfrozen"):
        make_regressor("ridge",{"alpha":0})


def test_metrics_keep_all_worst_ties_and_tau_b():
    result = group_metrics([1,1,2,3],[0,3,1,2])
    assert result["worst_recall_at_1"] == result["worst_recall_at_3"] == 0.5
    assert result["mean_reciprocal_rank"] == 1 and result["worst_tie_count"] == 2
    assert result["kendall_tau_b"] == pytest.approx(1/np.sqrt(30))
    assert result["mae"] == 1.25 and result["rmse"] == pytest.approx(np.sqrt(7/4))
    assert group_metrics([1,2],[0,0])["kendall_tau_b"] is None
    assert group_metrics([1,1],[0,1])["kendall_tau_b"] is None
    assert group_metrics([1,2],[0,1],in_Q_units=False)["mae"] is None


def test_group_macro_and_prediction_ties_are_deterministic(dataset):
    batch = synthetic_batch(dataset,["b","a","d","c"],["p1","p1","p2","p2"],["r"]*4)
    scores = np.zeros(4)
    orders = rank_groups(batch,scores)
    assert [batch.scenario_ids[i] for i in orders["gp1"]] == ["a","b"]
    results = evaluate_predictions(batch, np.array([1,1,3,2]), scores, in_Q_units=False)
    assert len(results["groups"]) == 2
    assert results["policy_macro"]["worst_recall_at_1"] == 0.75
    assert results["by_policy"]["p1"]["kendall_tau_b"]["undefined_groups"] == 1


def test_real_training_entry_is_disabled_by_default(dataset):
    with pytest.raises(ValueError,match="Training disabled"):
        nested_cv.run_nested_cv(dataset)


def test_nested_control_flow_with_nonlearning_doubles_only(dataset, loader, monkeypatch):
    # Exercise the actual orchestration, but replace every learning model (including catalog).
    current = {}
    events = []
    real_fit, real_transform = FoldPreprocessor.fit, FoldPreprocessor.transform
    real_targets = dataset.targets
    outer_by_id = {f.fold_id:f for f in loader.outer}

    def prep_fit(self,batch,*,fold):
        current["outer"] = outer_by_id[fold.outer_id]
        return real_fit(self,batch,fold=fold)

    def transform(self,batch,mode):
        current["batch"] = batch
        return real_transform(self,batch,mode)

    class NonLearningRegressor:
        def __init__(self,name,parameters):
            self.name = name

        def fit(self,X,Q,*,sample_weight):
            batch = current["batch"]
            outer = current["outer"]
            assert not set(batch.sample_ids) & set(outer.heldout_ids)
            assert np.array_equal(Q,real_targets(batch.sample_ids))
            assert np.allclose(sample_weight,nested_cv.training_weights(batch))
            self.outer_id = outer.fold_id
            events.append(("fit",self.name,outer.fold_id,tuple(batch.sample_ids)))
            return self

        def predict(self,X):
            batch = current["batch"]
            events.append(("predict",self.name,self.outer_id,tuple(batch.sample_ids)))
            return np.zeros(len(X))  # Fixed score, no learned parameter.

    class NonLearningCatalog:
        def fit(self,batch,Q,*,fold):
            assert set(batch.sample_ids) == set(fold.training_ids)
            return self

        def predict(self,batch):
            return np.zeros(len(batch.sample_ids))

    def target_firewall(ids):
        outer = current.get("outer")
        if outer and set(ids) & set(outer.heldout_ids):
            final_fits = [e for e in events if e[0] == "fit" and e[2] == outer.fold_id and set(e[3]) == set(outer.training_ids)]
            assert {e[1] for e in final_fits} == {"ridge","gradient_boosting"}
        return real_targets(ids)

    monkeypatch.setattr(FoldPreprocessor,"fit",prep_fit)
    monkeypatch.setattr(FoldPreprocessor,"transform",transform)
    monkeypatch.setattr(dataset,"targets",target_firewall)
    monkeypatch.setattr(nested_cv,"CatalogHistoryBaseline",NonLearningCatalog)
    results, artifacts = nested_cv.run_nested_cv(dataset,configuration=configs(dataset)[0],allow_training=True,model_factory=NonLearningRegressor)
    assert len(results["outer_folds"]) == 5 and len(artifacts) == 15
    for outer in loader.outer:
        for name in ("ridge","gradient_boosting"):
            fits = [e for e in events if e[:3] == ("fit",name,outer.fold_id)]
            predicts = [e for e in events if e[:3] == ("predict",name,outer.fold_id) and set(e[3]) == set(outer.heldout_ids)]
            assert len(fits) == 17 and len(predicts) == 1
    assert sum(e[0] == "fit" for e in events) == 170  # Interface calls to doubles, NOT learned fits.


def test_five_deliverables_provenance_no_overwrite(preflight, dataset):
    output, execution = preflight
    assert {p.name for p in output.iterdir()} == {"conservative_feature_manifest_v1.json","training_config_v1.json",
        "baseline_config_v1.json","nested_cv_execution_manifest.json","preflight_report.md"}
    assert execution["actual_inner_model_CV_run"] is execution["actual_outer_model_evaluation_run"] is False
    assert execution["source_preserved"] and not execution["fitted_preprocessing_exported"]
    with pytest.raises(ValueError,match="Refuse overwrite"):
        run_preflight(ROOT,output)
    for rel, sha in execution["implementation_sha256"].items():
        assert digest(ROOT/rel) == sha


def test_loader_rejects_partition_tampering(dataset):
    from copy import deepcopy
    modified = deepcopy(dataset)
    part = modified.inner["inner_folds"][0]["training"]
    part["sample_ids"][0] = modified.inner["inner_folds"][0]["validation"]["sample_ids"][0]
    with pytest.raises(ValueError, match="split|Repeated|count"):
        PolicyFoldLoader(modified)


def test_training_rejects_modified_config_before_any_fit(dataset):
    config = configs(dataset)[0]
    config["regression_grids"]["ridge"] = [{"alpha":0}]
    with pytest.raises(ValueError, match="Frozen training configuration"):
        nested_cv.run_nested_cv(dataset,configuration=config,allow_training=True)


def test_dataset_rejects_policy_protocol_hash_drift(dataset, tmp_path):
    import shutil
    for name in dataset.input_hashes:
        shutil.copy2(dataset.data/name,tmp_path/name)
    with (tmp_path/"split_manifest_policy_cv_v1.json").open("a",encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(ValueError,match="Frozen policy protocol SHA-256"):
        TrainingDataset(ROOT,tmp_path)


def test_solver_is_not_imported_by_data_or_training_interfaces():
    code = """
import sys
class Guard:
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0]=='gurobipy':raise AssertionError('Gurobi import prohibited')
sys.meta_path.insert(0,Guard())
from pathlib import Path
from scenario_agent.training.dataset import TrainingDataset
from scenario_agent.training.fold_loader import PolicyFoldLoader
from scenario_agent.v3_feature_extractor import load_standardized_v3
from scenario_agent.portable import portable_replay_root
data=TrainingDataset(Path.cwd());PolicyFoldLoader(data)
with portable_replay_root(data.root) as root:
 load_standardized_v3(root,root/'experiments/scenario_agent_v1/data/v3')
"""
    result = subprocess.run([sys.executable,"-c",code],cwd=ROOT,text=True,capture_output=True)
    assert result.returncode == 0, result.stderr
