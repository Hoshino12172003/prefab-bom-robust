"""Supplement the existing preflight, preserving its original specifications and evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
from time import perf_counter

import numpy as np

from ..policy_cv_protocol_v1 import require
from ..v3_feature_extractor.manifest import digest, identity
from .baselines import CatalogHistoryBaseline, RuleBasedBaseline
from .dataset import FEATURE_NAMES, FEATURE_SPECS, TrainingDataset
from .fold_loader import PolicyFoldLoader
from .preprocessing import FoldPreprocessor
from .training_manifest import configs, replay_and_isolation


def partition_statistics(dataset, ids):
    batch = dataset.batch(ids)
    Q = dataset.targets(ids)
    groups = [dataset.groups[k] for k in dict.fromkeys(batch.group_keys)]
    columns = []
    for i, spec in enumerate(FEATURE_SPECS):
        col = batch.X[:, i]
        values = [None if np.isnan(v) else float(v) for v in col]
        counts = Counter(values)
        modal_fraction = max(counts.values())/len(col)
        observed = col[~np.isnan(col)]
        columns.append(dict(feature_name=spec.name, missing=int(np.isnan(col).sum()),
            missing_fraction=float(np.isnan(col).mean()), distinct_including_null=len(counts),
            constant=len(counts) == 1, near_constant=len(counts) > 1 and modal_fraction >= 0.95,
            modal_fraction=modal_fraction, observed_constant=len(set(observed)) == 1,
            all_missing=len(observed) == 0))
    return dict(policy_count=len(set(batch.policy_ids)), policy_ids=sorted(set(batch.policy_ids)),
        policies=[list(p) for p in sorted({dataset.groups[k]["policy"] for k in batch.group_keys})],
        group_count=len(groups), query_count=len(ids),
        Q_exact=dict(min=float(Q.min()), max=float(Q.max()), mean=float(Q.mean()), std=float(Q.std()),
            quantiles=np.quantile(Q,[0,0.25,0.5,0.75,1]).tolist(),
            value_counts=dict(sorted(Counter(map(int,Q)).items()))),
        is_worst_positive=sum(int(dataset.labels_by_id[s]["is_worst"]) for s in ids),
        tied_worst_groups=sum(int(g["worst_count"]) > 1 for g in groups),
        informative_ranking_groups=sum(len({r["Q_exact"] for r in g["rows"]}) > 1 for g in groups),
        candidate_size_distribution=dict(sorted(Counter(int(g["candidate_count"]) for g in groups).items())),
        missing_cells=sum(c["missing"] for c in columns), feature_statistics=columns,
        constant_features=[c["feature_name"] for c in columns if c["constant"]],
        near_constant_features=[c["feature_name"] for c in columns if c["near_constant"]])


def eligibility(train):
    reasons = []
    if not train["informative_ranking_groups"]:
        reasons.append("NO_INFORMATIVE_RANKING_GROUP")
    if train["Q_exact"]["min"] == train["Q_exact"]["max"]:
        reasons.append("CONSTANT_TARGET")
    return reasons


def run_audit(root, output=None, reports=None):
    root = Path(root).resolve()
    output = Path(output) if output else root/"experiments/scenario_agent_v1/training/v1"
    reports = Path(reports) if reports else root/"docs/scenario_agent_v1/training"
    names = ("training_pipeline_preflight.md", "fold_statistics.md", "conservative_feature_audit.md")
    require(not (output/"pipeline_audit_v1.json").exists() and not any((reports/n).exists() for n in names),
            "Refuse overwrite of supplemental audit")
    dataset = TrainingDataset(root)
    loader = PolicyFoldLoader(dataset)
    expected_train, expected_base = configs(dataset)
    # Existing specifications remain byte-identical; do not silently rebuild an old approved file.
    for name, expected in (("conservative_feature_manifest_v1.json",dataset.feature_manifest()),
                           ("training_config_v1.json",expected_train),("baseline_config_v1.json",expected_base)):
        require(json.loads((output/name).read_text(encoding="utf-8")) == expected, f"Specification conflict: {name}")
    before = {name:digest(output/name) for name in ("conservative_feature_manifest_v1.json", "training_config_v1.json", "baseline_config_v1.json")}
    replay = replay_and_isolation(dataset)
    rows = []
    for fold in (*loader.outer, *loader.inner):
        train = partition_statistics(dataset,fold.training_ids)
        heldout = partition_statistics(dataset,fold.heldout_ids)
        reasons = eligibility(train)
        start = perf_counter()
        prep = FoldPreprocessor().fit(dataset.batch(fold.training_ids),fold=fold)
        fit_seconds = perf_counter()-start
        state = identity("prep-",prep.state)
        start = perf_counter()
        for mode in ("ridge","tree"):
            prep.transform(dataset.batch(fold.training_ids),mode)
            prep.transform(dataset.batch(fold.heldout_ids),mode)
        transform_seconds = perf_counter()-start
        require(identity("prep-",prep.state) == state, "Heldout transform changed preprocessing state")
        require(len(train["feature_statistics"]) == 78, "Feature dimension conflict")
        rows.append(dict(fold_id=fold.fold_id, outer_id=fold.outer_id, kind=fold.kind,
            outer_test_policy=next(f["test_policy"] for f in dataset.outer["outer_folds"] if f["fold_id"] == fold.outer_id),
            train=train, heldout=heldout, status="BLOCK" if reasons else "PASS", block_reasons=reasons,
            preprocessing_fit_seconds=fit_seconds, preprocessing_transform_seconds=transform_seconds,
            preprocessing_fit_sample_ids=list(prep.state["fit_sample_ids"]),
            heldout_sample_ids=list(fold.heldout_ids), finite_transforms=True, state_unchanged=True))
    # Computability only: no metric evaluation and no heldout-Q access in baseline computation.
    baseline_checks = []
    for fold in loader.outer:
        train, test = dataset.batch(fold.training_ids), dataset.batch(fold.heldout_ids)
        rule = RuleBasedBaseline()
        start = perf_counter()
        rule_scores = rule.predict(test)
        rule_seconds = perf_counter()-start
        catalog = CatalogHistoryBaseline().fit(train,dataset.targets(fold.training_ids),fold=fold)
        start = perf_counter()
        catalog_scores = catalog.predict(test)
        catalog_seconds = perf_counter()-start
        require(np.isfinite(rule_scores).all() and np.isfinite(catalog_scores).all(), "Baseline not computable")
        baseline_checks.append(dict(fold_id=fold.fold_id, rule_computable=True, catalog_computable=True,
            rule_prediction_seconds=rule_seconds, catalog_prediction_seconds=catalog_seconds,
            catalog_test_Q_read=False, ranking_performance_computed=False))
    go = all(r["status"] == "PASS" for r in rows)
    result = dict(version="v1.preflight.supplement.1", status="TRAINING_PIPELINE_GO" if go else "NO-GO",
        ridge="RIDGE_ELIGIBLE" if go else "BLOCKED", gradient_boosting="GRADIENT_BOOSTING_ELIGIBLE" if go else "BLOCKED",
        pairwise="PAIRWISE_RANKING_DEFERRED", near_constant_rule="modal fraction >=0.95 including NULL; exclude exact constants",
        constant_policy="diagnostic only; no feature dropped or chosen using heldout statistics",
        outer_test_statistics_use="retrospective audit only, never fitting/selection", folds=rows,
        replay=replay, baselines=baseline_checks, estimator_fit_calls=0, estimator_prediction_calls=0,
        baseline_dictionary_aggregations=5, baseline_prediction_calls=10, optimization_calls=0,
        preprocessing_fit_calls=25, preprocessing_states_exported=False,
        actual_model_cv_run=False, model_performance_reported=False,
        unseen_rhs="BLOCKED_WITH_CURRENT_576_DATA", cross_network="BLOCKED_SINGLE_NETWORK",
        input_sha256=dataset.input_hashes, preserved_specification_sha256=before)
    documents = render_documents(result,dataset)
    reports.mkdir(parents=True,exist_ok=True)
    for name, text in zip(names,documents):
        with (reports/name).open("x",encoding="utf-8") as stream:
            stream.write(text)
    result["report_sha256"] = {n:digest(reports/n) for n in names}
    result["implementation_sha256"] = {p.relative_to(root).as_posix():digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    with (output/"pipeline_audit_v1.json").open("x",encoding="utf-8") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write("\n")
    execution_path = output/"nested_cv_execution_manifest.json"
    previous = json.loads(execution_path.read_text(encoding="utf-8"))
    archive = output/"archive_before_supplement"
    require(not archive.exists(), "Audit archive already exists")
    archive.mkdir()
    shutil.copy2(execution_path,archive/execution_path.name)
    # Add new evidence while retaining original preflight records in this manifest and its archive.
    previous.update(implementation_sha256=result["implementation_sha256"],
        supplemental_audit=dict(path="pipeline_audit_v1.json",sha256=digest(output/"pipeline_audit_v1.json"),status=result["status"]),
        previous_execution_manifest_sha256=digest(archive/execution_path.name))
    execution_path.write_text(json.dumps(previous,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for name,sha in before.items():
        require(digest(output/name)==sha,"Frozen specification modified")
    return result


def render_documents(result,dataset):
    intro = (f"# 训练管线补充预检\n\n{result['status']}；{result['ridge']}；{result['gradient_boosting']}；PAIRWISE_RANKING_DEFERRED。\n\n"
        "78列原始规范保持冻结；六个排除字段及其缺失指示不进入模型。历史与未来均调用ScenarioFeatureExtractorV3.extract后投影。"
        "576重放与576历史扰动检查通过，25折只在各自训练样本fit预处理，heldout只transform。\n\n"
        "Rule与Catalog-history在五个外层折均可计算；后者只聚合外层训练Q，不读取测试Q。规则分数无vehicle单位，MAE/RMSE不适用。"
        "Catalog按不同训练policy/RHS均值聚合，重复原始调用保留。Ridge正alpha四候选，GB深1/2、叶样本8/16、最多4叶、50棵树；只由内层CV选择。\n\n"
        "Recall@1/3保留全部并列最坏，MRR取首个最坏，tau-b保留真实Q并列且未定义值为NULL；预测同分可按名称确定展示顺序，不拆分真实Q标签。"
        "指标按完整组再按policy宏平均。预处理、预测和排序时间分开记录，不能解释为C&CG提速。\n\n"
        "本次只执行预处理与基准可计算性检查：Ridge/GB fit=0、predict=0、Gurobi=0；不报告模型性能。"
        "嵌套模型执行路径此前经非学习替身测试，真实模型CV尚未运行。is_violating不训练；actual_disruption_loss不作监督；Oracle排序仅作hindsight参考。\n\n"
        "全部50个分区的Q分布和78列诊断见fold_statistics.md及pipeline_audit_v1.json。近常量阈值为包括NULL的众数占比≥95%，严格常量另列；"
        "这些统计仅作审计，不据测试统计删特征或调参。常量不自动BLOCK：固定网络的结构常量属预期，零方差scale=1；全缺失训练列以0及缺失标记处理。"
        "无有效组、目标常量、维度错误、拟合失败或泄漏必须BLOCK。\n\n"
        "旧84列、旧切分BLOCK及两份Policy CV清单均保持原字节；三份既有训练规范也保持原字节。execution manifest更新前版本保存在archive_before_supplement/。"
        "unseen-RHS与cross-network保持BLOCK；只有5个历史policy，不把576查询当独立实验单位。\n\n"
        "复现：python -m scenario_agent.training.audit。已有补充输出拒绝覆盖。源码、原始输入及文档哈希保存在补充JSON。\n")
    stats = "# 25折可训练性统计\n\n数值均为实际数据审计，未用于拟合或选择。train/heldout分别展示。近常量定义：众数占比≥95%（含NULL）且非严格常量。\n\n"
    stats += "|kind|outer test|heldout policy|train policies|groups train/held|queries train/held|worst+ train/held|ties train/held|status|\n|---|---|---|---:|---|---|---|---|---|\n"
    for r in result["folds"]:
        a,b=r["train"],r["heldout"]
        stats += f"|{r['kind']}|{r['outer_test_policy']}|{b['policies']}|{a['policy_count']}|{a['group_count']}/{b['group_count']}|{a['query_count']}/{b['query_count']}|{a['is_worst_positive']}/{b['is_worst_positive']}|{a['tied_worst_groups']}/{b['tied_worst_groups']}|{r['status']}|\n"
    for r in result["folds"]:
        stats += f"\n## {r['kind']} outer={r['outer_test_policy']} heldout={r['heldout']['policies']}\n\n"
        stats += f"预处理fit={r['preprocessing_fit_seconds']:.6f}s；两分支train/heldout变换合计={r['preprocessing_transform_seconds']:.6f}s。\n"
        for label in ("train","heldout"):
            s=r[label]
            stats += f"\n### {label}\n\nQ分布：{json.dumps(s['Q_exact'],ensure_ascii=False)}\n\n候选数分布：{s['candidate_size_distribution']}；缺失单元格={s['missing_cells']}。\n\n"
            stats += f"常量：{', '.join(s['constant_features']) or '无'}\n\n近常量：{', '.join(s['near_constant_features']) or '无'}\n\n"
            stats += "|feature|missing|modal fraction|constant|near constant|all missing|\n|---|---:|---:|---|---|---|\n"
            for c in s["feature_statistics"]:
                stats += f"|{c['feature_name']}|{c['missing']}|{c['modal_fraction']:.6f}|{c['constant']}|{c['near_constant']}|{c['all_missing']}|\n"
    feature = "# 78列保守特征审计\n\n以下顺序与conservative_feature_manifest_v1.json、冻结Policy CV逐项相等。该Manifest的name即feature_name，数组下标定义顺序；view_version为保守视图版本，raw_feature_version为原提取器版本。\n\n"
    manifest=dataset.feature_manifest()
    feature += f"视图版本：{manifest['view_version']}；原特征版本：{manifest['raw_feature_version']}。\n\n"
    feature += "排除："+", ".join(manifest["excluded_fields"])+"。\n\n"
    feature += "ID列不进入X；buffer与剩余预算是合法物理输入。原78列数值与78个既有缺失标记构成156维回归输入，未添加未经审计的新物理特征。保留列源码依赖仅有静态网络/风险与policy/budget/spent；改变iteration/active/UB/LB/run后576条投影不变。\n\n"
    feature += "|order|feature_name|dtype|unit|source|missing rule|\n|---:|---|---|---|---|---|\n"
    for i,s in enumerate(FEATURE_SPECS,1):
        feature += f"|{i}|{s.name}|{s.dtype}|{s.unit}|{s.source}|{'NULL保留；训练折均值+缺失标记' if s.nullable else '不允许NULL'}|\n"
    return intro,stats,feature


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[3])
    args=parser.parse_args()
    print(run_audit(args.root)["status"])
