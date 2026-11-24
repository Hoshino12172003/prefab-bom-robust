"""Guarded future training loop; the preflight entrypoint never invokes it."""
from time import perf_counter
from collections import Counter
import json

import numpy as np

from ..policy_cv_protocol_v1 import require
from .baseline_models import CatalogHistoryBaseline, RuleBasedBaseline
from .fold_loader import PolicyFoldLoader
from .preprocessing import FoldPreprocessor
from .ranking_metrics import evaluate_predictions, rank_groups
from .regression_models import GB_GRID, RIDGE_GRID, make_regressor


def training_weights(batch):
    counts = Counter(zip(batch.policy_ids, batch.rhs_ids))
    weights = np.array([1/counts[key] for key in zip(batch.policy_ids, batch.rhs_ids)])
    return weights/weights.mean()


def _evaluate(dataset, batch, predict, *, in_Q_units=True, preprocessor=None, mode=None):
    preprocessing_seconds = 0.0
    inputs = batch
    if preprocessor is not None:
        start = perf_counter()
        inputs = preprocessor.transform(batch, mode)
        preprocessing_seconds = perf_counter()-start
    start = perf_counter()
    scores = predict(inputs)
    prediction_seconds = perf_counter()-start
    start = perf_counter()
    orders = rank_groups(batch, scores)
    sorting_seconds = perf_counter()-start
    result = evaluate_predictions(batch, dataset.targets(batch.sample_ids), scores,
                                  in_Q_units=in_Q_units, orders=orders)
    result.update(preprocessing_seconds=preprocessing_seconds, prediction_seconds=prediction_seconds,
                  sorting_seconds=sorting_seconds,
                  prediction_sort_seconds=preprocessing_seconds+prediction_seconds+sorting_seconds)
    result["timing_scope"] = "separate transform/predict/sort wall time; excludes label access and metrics; not C&CG speedup"
    return result


def run_nested_cv(dataset, *, configuration=None, allow_training=False, model_factory=None):
    require(allow_training, "Training disabled: this task permits preflight only; future training requires explicit allow_training=True")
    from .training_manifest import configs
    if configuration is None:
        path = dataset.root / "experiments/scenario_agent_v1/training/v1/training_config_v1.json"
        configuration = json.loads(path.read_text(encoding="utf-8"))
    require(configuration == configs(dataset)[0], "Frozen training configuration/input/dependency conflict")
    factory = model_factory if model_factory is not None else make_regressor
    loader = PolicyFoldLoader(dataset)
    results, artifacts = [], {}
    for outer in loader.outer:
        cached = []
        for fold in loader.for_outer(outer.fold_id):
            train, validation = dataset.batch(fold.training_ids), dataset.batch(fold.heldout_ids)
            prep = FoldPreprocessor().fit(train, fold=fold)
            cached.append((fold, train, validation, prep, dataset.targets(fold.training_ids)))
        selected, selections = {}, {}
        for name, grid, mode in (("ridge", RIDGE_GRID, "ridge"), ("gradient_boosting", GB_GRID, "tree")):
            candidate_scores = []
            for params in grid:
                inner_scores = []
                for fold, train, validation, prep, Q in cached:
                    estimator = factory(name, dict(params))
                    estimator.fit(prep.transform(train, mode), Q, sample_weight=training_weights(train))
                    scores = estimator.predict(prep.transform(validation, mode))
                    metrics = evaluate_predictions(validation, dataset.targets(fold.heldout_ids), scores)
                    inner_scores.append(dict(fold_id=fold.fold_id, score=metrics["policy_macro"]["worst_recall_at_1"]))
                candidate_scores.append(dict(parameters=dict(params), inner=inner_scores,
                                             mean_score=float(np.mean([r["score"] for r in inner_scores]))))
            # Frozen grid order breaks parameter-selection ties; test labels are never consulted.
            winner = max(candidate_scores, key=lambda row: row["mean_score"])
            selected[name], selections[name] = winner["parameters"], candidate_scores
        train, test = dataset.batch(outer.training_ids), dataset.batch(outer.heldout_ids)
        Q_train = dataset.targets(outer.training_ids)
        prep = FoldPreprocessor().fit(train, fold=outer)
        models = {}
        # Lock BOTH models before accessing any outer-test supervision.
        for name, mode in (("ridge", "ridge"), ("gradient_boosting", "tree")):
            estimator = factory(name, selected[name])
            estimator.fit(prep.transform(train, mode), Q_train, sample_weight=training_weights(train))
            models[name] = (estimator, mode)
            artifacts[outer.fold_id, name] = dict(model=estimator, preprocessor=prep, mode=mode,
                                                  parameters=selected[name], training_sample_ids=outer.training_ids)
        catalog = CatalogHistoryBaseline().fit(train, Q_train, fold=outer)
        metrics = {"rule_based": _evaluate(dataset, test, RuleBasedBaseline().predict, in_Q_units=False),
                   "catalog_history": _evaluate(dataset, test, catalog.predict)}
        artifacts[outer.fold_id, "catalog_history"] = catalog
        for name, (estimator, mode) in models.items():
            metrics[name] = _evaluate(dataset, test, estimator.predict, preprocessor=prep, mode=mode)
        # Ground-truth ordering is reported separately and has no deployment or selection role.
        truth = dataset.targets(outer.heldout_ids)
        reference = evaluate_predictions(test, truth, truth)
        results.append(dict(outer_fold_id=outer.fold_id, test_policy_ids=sorted(set(test.policy_ids)),
            selected_parameters=selected, inner_selection=selections, models=metrics,
            oracle_hindsight_reference=dict(deployable=False, selection_use=False, evaluation=reference)))
    aggregate = {name: {metric: float(np.mean(v)) if (v := [r["models"][name]["policy_macro"][metric]
                       for r in results if r["models"][name]["policy_macro"][metric] is not None]) else None
                       for metric in results[0]["models"][name]["policy_macro"]} for name in results[0]["models"]}
    return dict(outer_folds=results, equal_policy_macro=aggregate, independent_experimental_units=5), artifacts
