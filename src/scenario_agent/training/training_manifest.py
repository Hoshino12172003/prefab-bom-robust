"""Write V1 training specifications and a solver-free, estimator-free preflight."""
import argparse
from dataclasses import replace
import importlib.metadata
import json
from pathlib import Path

import numpy as np

from ..policy_cv_protocol_v1 import HISTORY_FIELDS, require
from ..v3_feature_extractor import load_standardized_v3, MasterStateV3
from ..v3_feature_extractor.historical import historical_records
from ..v3_feature_extractor.manifest import MODEL_INSTANCE_ID, digest, identity
from ..v3_feature_extractor.scenario_features import load_scenarios
from ..v3_feature_extractor.schema import RESOURCES
from .dataset import ConservativeFeatureView, FEATURE_NAMES, TrainingDataset
from .fold_loader import PolicyFoldLoader
from .preprocessing import FoldPreprocessor
from .regression_models import GB_FIXED, GB_GRID, RIDGE_GRID, make_regressor


def configs(dataset):
    training = dict(version="v1.training.1", scope=dataset.outer["scope"], target="Q_exact", target_unit="vehicle",
        feature_view="v1.conservative78.1", feature_order=list(FEATURE_NAMES), input_hashes=dataset.input_hashes,
        outer_policy_folds=5, inner_policy_folds=20, default_mode="preflight_only",
        regression_grids=dict(ridge=list(RIDGE_GRID), gradient_boosting=list(GB_GRID)), gradient_boosting_fixed=GB_FIXED,
        ridge_fixed=dict(fit_intercept=True, solver="svd"),
        selection=dict(metric="worst_recall_at_1", order="maximize", aggregation="groups macro within each inner validation policy, then equal mean of four policies",
            parameter_ties="first candidate in frozen grid order", early_stopping=False,
            previous_protocol_refinement="current task specifies Recall@1 rather than top1-hit; all exact worst ties retained; old protocol unchanged"),
        preprocessing=dict(fit_scope="exactly this inner/outer training fold; fresh state per fold/refit",
            imputation="training mean; all-training-missing mean=0 plus missing flag; variance after imputation; zero scale=1",
            ridge="standardize 78 numeric columns, append 78 missing flags", tree="impute without scaling, append 78 missing flags",
            output_dimensions=156, categorical_fit=False, category_dictionary=dict(resources=list(RESOURCES), due_periods=list(range(61,75))),
            unknown_category="reject unknown resource/period/model through existing V3 extractor; no inferred category IDs"),
        repeated_supervision="keep every query; weight each training (policy,RHS) pair equally via inverse repeat counts, normalized mean weight=1; training-fold counts only",
        evaluation=dict(metrics=["worst_recall_at_1", "worst_recall_at_3", "mean_reciprocal_rank", "kendall_tau_b", "mae", "rmse", "prediction_sort_seconds"],
            recall="number of ALL tied worst scenarios retrieved / total tied worst scenarios",
            mrr="reciprocal of first exact-worst rank", kendall="tau-b on raw exact Q and predicted score; constant input -> NULL, report undefined count",
            predicted_ties="ascending score then scenario name solely for deterministic ordering",
            aggregation="complete group -> policy macro -> equal outer-policy macro; five folds reported separately",
            timing="transform + predict + group sorting only; excludes evaluation labels and metrics",
            oracle_reference="hindsight only, never deployed, fit or hyperparameter selection"),
        excluded_supervision=["is_violating", "actual_disruption_loss", "dense_rank"],
        is_worst_use="group-level ranking evaluation only", policy_id_use="grouping/partition/repeat weights only; never a feature",
        scope_blocks=["UNSEEN_RHS_GENERALIZATION_BLOCKED", "CROSS_NETWORK_GENERALIZATION_BLOCKED"],
        dependencies={name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn", "pyxlsb")})
    baseline = dict(version="v1.baselines.1",
        A_rule=dict(class_name="RuleBasedBaseline", fitted=False, Oracle_data_used=False, output_unit="dimensionless_negative_burden",
            formula="score=-sum_resources[(0.5*severity_loss+0.5*mean_effective_loss_rate)*duration/14]",
            missing_semantics="absent resource contributes 0; present resource with zero changed RHS rows has effective loss=0; other present inputs required",
            assumptions="equal resource weights and 50/50 severity/effective loss chosen before any model evaluation; descriptive heuristic, not additive physical production loss",
            required_columns=[f"risk_{r}_{f}" for r in RESOURCES for f in ("present", "severity_loss", "duration", "changed_rows", "mean_effective_loss_rate")],
            order="ascending score", mae_rmse="NOT_APPLICABLE_no_vehicle_Q_prediction"),
        B_catalog=dict(class_name="CatalogHistoryBaseline", fit_scope="current training fold only",
            formula="mean exact Q across distinct training-policy/effective-RHS pairs for that RHS",
            repeats="same-policy/RHS repeated calls aggregate once; all original queries retained",
            unknown_rhs="training-only grand mean across distinct policy/RHS pairs; fixed before validation",
            keys="effective_rhs_id for lookup only, never continuous numeric input", output_unit="vehicle"),
        C_ridge=dict(class_name="sklearn.linear_model.Ridge", target="Q_exact", selection="nested policy CV", alpha=list(RIDGE_GRID)),
        D_gradient_boosting=dict(class_name="sklearn.ensemble.GradientBoostingRegressor", target="Q_exact", grid=list(GB_GRID), fixed=GB_FIXED),
        oracle_hindsight_reference=dict(deployable=False, baseline=False, selection_use=False), pairwise_ranking="DEFERRED")
    return training, baseline


def replay_and_isolation(dataset, *, progress=print):
    from ..portable import portable_replay_root
    with portable_replay_root(dataset.root) as replay:
        network = load_standardized_v3(replay, replay / "experiments/scenario_agent_v1/data/v3")
        scenarios = load_scenarios(network)
        *_, contexts, _ = historical_records(network, scenarios)
    view = ConservativeFeatureView()
    all_rhs = tuple(sorted({s.rhs_id for s in scenarios.values()}))
    for index, (sid, scenario, state) in enumerate(contexts, 1):
        actual = tuple(view.extract(network, scenario, state).values())
        require(actual == dataset.features[sid], f"Historical 78-column parity failure: {sid}")
        # Change every history source and identity while preserving legitimate physical policy/budget.
        perturbed = replace(state, iteration_id=state.iteration_id+7, active_rhs_ids=all_rhs,
                            ub=28000, lb_before_oracle=0, run_id="history-isolation-probe")
        require(view.extract(network, scenario, perturbed) == dict(zip(FEATURE_NAMES, actual)),
                f"Excluded history indirectly entered retained features: {sid}")
        if index % 96 == 0:
            progress(f"Replay and history isolation: {index}/576", flush=True)
    future = MasterStateV3(MODEL_INSTANCE_ID, 1, (100,100,0), (scenarios["NR"].rhs_id,), 28000, None)
    future_values = view.extract(network, scenarios["B_RECEIPT_1"], future)
    require(tuple(future_values) == FEATURE_NAMES, "Future input schema conflict")
    return dict(historical_replay_pass=576, excluded_history_perturbation_pass=576,
        future_unseen_policy=list(future.policy), future_input="PASS_SAME_EXTRACTOR_AND_VIEW",
        source_review="hash-pinned raw sources: retained Master inputs only policy,budget,spent; retained interactions only network,scenario,policy",
        excluded_sources=["iteration_id", "active_rhs_ids", "ub", "lb_before_oracle", "run_id"],
        excluded_fields=list(HISTORY_FIELDS), indirect_history_dependency_detected=False,
        extractor_calls=1153, raw_feature_generation="ScenarioFeatureExtractorV3.extract only")


def fold_preflight(dataset, loader):
    records = []
    for fold in (*loader.outer, *loader.inner):
        train, heldout = dataset.batch(fold.training_ids), dataset.batch(fold.heldout_ids)
        prep = FoldPreprocessor().fit(train, fold=fold)
        state_before = identity("prep-", prep.state)
        for mode in ("ridge", "tree"):
            prep.transform(train, mode)
            prep.transform(heldout, mode)
        require(state_before == identity("prep-", prep.state), "Transform mutated fit state")
        records.append(dict(fold_id=fold.fold_id, outer_id=fold.outer_id, kind=fold.kind,
            outer_test_policy=next(f["test_policy"] for f in dataset.outer["outer_folds"] if f["fold_id"] == fold.outer_id),
            heldout_policy=list(dataset.groups[fold.heldout_group_keys[0]]["policy"]),
            training_sample_ids=list(fold.training_ids), heldout_sample_ids=list(fold.heldout_ids),
            training_stats=fold.training_stats, heldout_stats=fold.heldout_stats,
            preprocessing_fit_sample_ids=prep.state["fit_sample_ids"], preprocessing_state_sha256=state_before,
            all_training_missing_columns=prep.state["all_missing_columns"], training_only_fit=True,
            finite_transform_both_modes=True, transformed_dimensions=156, state_exported=False,
            estimator_fit_calls=0, estimator_prediction_calls=0))
    return records


def run_preflight(root, output=None, *, progress=print):
    root = Path(root).resolve()
    output = Path(output).resolve() if output else root / "experiments/scenario_agent_v1/training/v1"
    names = ("conservative_feature_manifest_v1.json", "training_config_v1.json", "baseline_config_v1.json",
             "nested_cv_execution_manifest.json", "preflight_report.md")
    require(not any((output/n).exists() for n in names), "Refuse overwrite of training preflight outputs")
    dataset = TrainingDataset(root)
    loader = PolicyFoldLoader(dataset)
    replay = replay_and_isolation(dataset, progress=progress)
    records = fold_preflight(dataset, loader)
    training, baselines = configs(dataset)
    # Constructor/API feasibility only. No estimator.fit or estimator.predict invocation.
    for model, grid in (("ridge", RIDGE_GRID), ("gradient_boosting", GB_GRID)):
        for params in grid:
            make_regressor(model, params)
    source_hashes = {p.relative_to(root).as_posix(): digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    execution = dict(status="PREFLIGHT_GO_FOR_FUTURE_BASELINE_TRAINING", mode="PREFLIGHT_ONLY",
        formal_model_training_performed=False, estimator_fit_calls=0, estimator_prediction_calls=0, optimization_calls=0,
        preprocessing_fit_calls=25, fitted_preprocessing_exported=False,
        actual_inner_model_CV_run=False, actual_outer_model_evaluation_run=False,
        inner_status="20 folds loaded; fold-only preprocessing/transform executed; estimator path tested with non-learning doubles only",
        outer_status="5 folds loaded; fold-only preprocessing/transform executed; no test model predictions or performance reported",
        replay_and_isolation=replay, fold_preflight=records, input_sha256=dataset.input_hashes,
        implementation_sha256=source_hashes, model_constructor_checks=8, constructors_fitted=False,
        future_training_entry="scenario_agent.training.nested_cv.run_nested_cv(dataset, allow_training=True)",
        future_training_authorization="requires a new explicit training instruction; current entrypoint only preflights",
        expected_future_estimator_fits=dict(ridge=85, gradient_boosting=85), expected_outer_predictions_per_model=5,
        source_preserved=True, unseen_rhs_status="BLOCKED_WITH_CURRENT_576_DATA", cross_network_status="BLOCKED_SINGLE_NETWORK")
    payloads = [dataset.feature_manifest(), training, baselines]
    execution["specification_sha256"] = {n: identity("spec-", p) for n,p in zip(names[:3], payloads)}
    report = render_report(execution, training)
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in zip(names, [*payloads, execution, report]):
        with (output/name).open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+"\n" if isinstance(payload, dict) else payload)
    for name, expected in dataset.input_hashes.items():
        require(digest(dataset.data/name) == expected, f"Original input changed: {name}")
    return execution


def render_report(execution, training):
    text = "# Scenario Agent V1 训练管线预检\n\n"
    text += "结论：**PREFLIGHT_GO_FOR_FUTURE_BASELINE_TRAINING**，仅限固定V3网络、known-catalog/unseen-policy、Q_exact回归后组内排序。未训练正式模型、未运行Gurobi、未修改C&CG。\n\n"
    text += "## 验收\n\n78列与冻结Policy CV的名称、顺序、类型、单位和NULL规则一致；不覆盖84列X。适配器只投影ScenarioFeatureExtractorV3.extract输出，无第二套特征公式。576次重放逐字段一致；576次同时扰动iteration/active/UB/LB/run身份，78列保持一致。新(100,100,0) policy通过同一接口。\n\n"
    text += "25个折分别在精确训练样本集合上拟合预处理统计；Ridge和树分支变换均为有限值，heldout transform不改变状态。预检仅在内存拟合25份统计，未导出正式已拟合预处理器。回归器输入为78列数值+78列既有规则的缺失指示，共156列；六个排除字段及其缺失标记均不出现。不存在新原始特征或身份列。\n\n"
    text += "## 每折样本与最坏正例\n\n| 类型 | 外层test policy | heldout policy | train政策 | train/test组 | train/test查询 | train/test worst正例 |\n|---|---|---|---:|---|---|---|\n"
    for r in execution["fold_preflight"]:
        a,b=r["training_stats"],r["heldout_stats"]
        # IDs remain provenance, not feature values.
        text += f"| {r['kind']} | {r['outer_test_policy']} | {r['heldout_policy']} | {a['policy_count']} | {a['group_count']}/{b['group_count']} | {a['query_count']}/{b['query_count']} | {a['is_worst_positive']}/{b['is_worst_positive']} |\n"
    text += "\n外层5折、内层20折均保持完整排序组，同policy/RHS、重复原始调用和同policy别名不跨集合。两个内层折RHS训练覆盖24/38；Catalog基准的缺训练RHS固定使用训练policy/RHS总均值。最小inner train为3个policy、4组、96查询；浅树网格的最小叶样本为8或16，树深1或2，叶数至多4，50棵树。\n\n"
    text += "## 基准与监督防火墙\n\nA规则基准仅用静态severity、有效损失率、duration；等权无量纲负burden，权重在评价前固定，非物理产量损失，不计算MAE/RMSE。B目录历史只用训练折Q，按不同训练policy/RHS聚合均值，重复调用不增加独立监督权重。C Ridge使用四个正alpha；D GB使用四个浅树参数组合，无early stopping。正式回归拟合按训练折policy/RHS重复次数反比加权，原576查询全部保留。\n\n"
    text += "外层test没有参与标准化、插补、编码、特征选择、参数选择或早停；正式执行时内层3 train/1 validation选参，参数锁定后以4个outer train policy重拟合，再对outer test各模型预测一次。is_worst只作组内评价；is_violating不训练；actual_disruption_loss不作目标。Oracle精确排序仅为单独标识的hindsight reference。\n\n"
    text += "## 指标冻结\n\nRecall@k=检出的并列最坏数/全部并列最坏数（k=1,3），并列最坏不压成单标签。MRR取首个真实最坏的倒数位置；Tau-b按原Q与预测分数的并列计算，常量导致未定义时保留NULL并报告数量。预测分数并列仅按scenario名称确定展示顺序。MAE/RMSE仅用于以vehicle为单位预测Q的B/C/D。每完整组计算，再组内政策宏平均、五政策等权汇总；排序耗时计transform+predict+sorting，排除标签和指标计算。\n\n"
    text += "本任务按最新要求将内层选择指标明确为Worst-case Recall@1，旧协议的top1-hit定义与文件不覆盖。只有5个历史policy、915占多数查询，OEM缓冲恒0；结果不能解释成576个独立实验、未见RHS、新风险机制或跨网络泛化。原BLOCK结论继续保留。\n\n"
    text += "## 执行范围与复现\n\n实际完成：5+20折加载、25次折内预处理fit及双分支变换、576重放+576历史隔离检查、8个估计器构造检查。**正式估计器fit=0、predict=0；真实20折模型CV尚未运行。** 控制流由不学习的测试替身验证，不能当作正式模型结果。\n\n"
    text += "源码目录src/scenario_agent/training/，未来入口nested_cv.run_nested_cv默认拒绝训练，只有新任务显式授权后才传allow_training=True。配置与execution manifest保留输入/实现SHA-256、训练样本清单、预处理状态摘要；旧数据、旧协议与原提取器保持原字节。\n\n"
    text += "预检命令：`$env:PYTHONPATH='src'; python -m scenario_agent.training.training_manifest`（只允许新输出目录）；验证：`python -m pytest tests/test_scenario_training_pipeline_v1.py`。依赖版本冻结在training_config_v1.json；正式训练前不修改网格或以外层结果反馈调参。\n"
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_preflight(args.root, args.output)
    print(json.dumps({k: result[k] for k in ("status", "estimator_fit_calls", "preprocessing_fit_calls", "optimization_calls")}, indent=2))


if __name__ == "__main__":
    main()
