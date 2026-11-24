"""Freeze policy-held-out nested CV; never fit, optimize, or rewrite the old split."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .v3_feature_extractor.manifest import digest, identity

# Fixed before model fitting, based on historical provenance, not validation performance.
HISTORY_FIELDS = ("master_iteration", "master_active_count", "master_ub",
                  "master_lb_before", "master_lb_initialized", "scenario_already_active")
SCOPE = "Known-catalog, unseen-master-policy/state ranking"
OLD_SPLIT_SHA = "f2e0001452daf351316d9d208e568941821437dafb8c70ae39d8ffdc03556565"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def load_inputs(root, data):
    names = ("X_features_v1.csv", "y_labels_v1.csv", "group_manifest_v1.csv",
             "split_manifest_v1.json", "feature_manifest_v3.json", "training_dataset_manifest.json",
             "master_snapshots_v3.csv", "preprocessing_spec_v1.json")
    before = {n: digest(data / n) for n in names}
    require(before["split_manifest_v1.json"] == OLD_SPLIT_SHA, "Original blocked split changed")
    original = json.loads((data / "training_dataset_manifest.json").read_text(encoding="utf-8"))
    for rel, expected in original["outputs"].items():
        require(digest(root / rel) == expected, f"Dataset artifact changed: {rel}")
    for rel, expected in original["historical_sources"].items():
        require(digest(root / rel) == expected, f"Historical source changed: {rel}")
    features = json.loads((data / "feature_manifest_v3.json").read_text(encoding="utf-8"))
    require(before["feature_manifest_v3.json"] == original["original_feature_manifest_sha256"], "Feature manifest changed")
    for rel, expected in features["extractor_code_sha256"].items():
        require(digest(root / rel) == expected, f"Feature source changed: {rel}")
    X, labels, groups = (read_csv(data / n) for n in names[:3])
    require(len(X) == len(labels) == 576 and len(groups) == 33, "Dataset count conflict")
    require(list(X[0]) == [s["name"] for s in features["feature_fields"]] and len(X[0]) == 84, "84-feature schema conflict")
    require(len({r["sample_id"] for r in labels}) == 576, "Duplicate original sample")
    require(len({r["policy_rhs_id"] for r in labels}) == 148, "policy/RHS identity conflict")
    by_group = defaultdict(list)
    for row in labels:
        require(row["sample_id"] == row["oracle_call_id"], "Original query identity conflict")
        by_group[row["group_key"]].append(row)
    for group in groups:
        require(group["complete"] == group["exact"] == "true", "Nonexact/incomplete group")
        require(group["objective_version"] == "V3_on_time_count", "Objective version conflict")
        group["policy"] = tuple(json.loads(group["policy_json"]))
        group["policy_id"] = identity("policy-", group["policy"])
        group["rows"] = by_group[group["group_key"]]
        require(len(group["rows"]) == int(group["candidate_count"]), "Incomplete ranking group")
        require({r["sample_id"] for r in group["rows"]} == set(json.loads(group["sample_ids_json"])), "Group member conflict")
        for row in group["rows"]:
            require(row["model_instance_id"] == features["model_instance_id"]
                    and row["objective_version"] == group["objective_version"], "Model/group version conflict")
            x = X[int(row["X_data_row"])-1]
            require(tuple(int(x[n]) for n in ("buffer_C", "buffer_T", "buffer_O")) == group["policy"], "Policy/X mismatch")
    policies = sorted({g["policy"] for g in groups})
    require(policies == [(0,345,0), (0,350,0), (337,0,0), (354,0,0), (915,0,0)], "Policy universe changed")
    return X, labels, groups, features, before


def stats(groups):
    rows = [r for g in groups for r in g["rows"]]
    rhs = sorted({r["effective_rhs_id"] for r in rows})
    return dict(policy_count=len({g["policy"] for g in groups}), group_count=len(groups), query_count=len(rows),
        is_worst_positive=sum(int(r["is_worst"]) for r in rows),
        is_violating_positive=sum(int(r["is_violating"]) for r in rows),
        distinct_Q=len({r["Q_exact"] for r in rows}),
        candidate_size_distribution=dict(sorted(Counter(int(g["candidate_count"]) for g in groups).items())),
        groups_with_tied_worst=sum(int(g["worst_count"]) > 1 for g in groups),
        worst_tie_size_distribution=dict(sorted(Counter(int(g["worst_count"]) for g in groups).items())),
        effective_rhs_count=len(rhs), catalog_effective_rhs_count=38, effective_rhs_catalog_coverage=len(rhs)/38,
        effective_rhs_ids=rhs)


def partition(groups):
    return dict(policy_ids=sorted({g["policy_id"] for g in groups}), policies=[list(p) for p in sorted({g["policy"] for g in groups})],
        group_keys=[g["group_key"] for g in groups], sample_ids=[r["sample_id"] for g in groups for r in g["rows"]],
        stats=stats(groups))


def separation_audit(train, heldout):
    left = [r for g in train for r in g["rows"]]
    right = [r for g in heldout for r in g["rows"]]
    for key in ("sample_id", "oracle_call_id", "policy_rhs_id"):
        require(not {r[key] for r in left} & {r[key] for r in right}, f"Cross-policy duplicate: {key}")
    require(not {g["policy"] for g in train} & {g["policy"] for g in heldout}, "Held-out policy in training")
    require(not {g["group_key"] for g in train} & {g["group_key"] for g in heldout}, "Ranking group split")
    source_identity = lambda rows: {(r["source_file_sha256"], r["json_pointer"]) for r in rows}
    require(not source_identity(left) & source_identity(right), "Original JSON call crosses partitions")
    # A physical RHS may repeat across DIFFERENT policies. Aliases within the SAME policy remain together.
    aliases = lambda rows: {(g["policy"], r["effective_rhs_id"]) for g in rows for r in g["rows"]}
    require(not aliases(train) & aliases(heldout), "Same-policy RHS/alias crosses partitions")
    train_rhs, test_rhs = {r["effective_rhs_id"] for r in left}, {r["effective_rhs_id"] for r in right}
    return dict(status="PASS", policy_rhs_overlap=0, original_call_overlap=0, same_policy_alias_overlap=0,
        whole_groups=True, shared_rhs_permitted=True, shared_rhs_count=len(train_rhs & test_rhs),
        test_rhs_with_training_labels_fraction=len(train_rhs & test_rhs)/len(test_rhs),
        catalog_known_test_rhs_without_training_labels=sorted(test_rhs-train_rhs),
        shared_run_ids=sorted({g["run_id"] for g in train} & {g["run_id"] for g in heldout}))


def trainability(train, heldout):
    a, b = stats(train), stats(heldout)
    primary = (a["policy_count"] >= 3 and a["group_count"] > 0 and b["group_count"] > 0
        and a["query_count"] >= 2 and 0 < a["is_worst_positive"] < a["query_count"]
        and b["is_worst_positive"] > 0 and a["distinct_Q"] >= 2
        and all(int(g["candidate_count"]) >= 2 for g in train+heldout))
    # Distinguish a valid PRIMARY ranking fold from an unidentifiable auxiliary classifier.
    auxiliary_fit = 0 < a["is_violating_positive"] < a["query_count"]
    auxiliary_eval = 0 < b["is_violating_positive"] < b["query_count"]
    return dict(primary_ranking="GO" if primary else "BLOCK", fitted=False,
        primary_minimum_rule="3+ train policies, complete nonempty groups with 2+ candidates, both worst classes and 2+ Q values in train",
        ridge_identifiability="positive regularization alpha required; n>feature_count is not required for regularized Ridge",
        tree_feasibility="future depth/leaf grid must be feasible for the smallest inner training fold",
        auxiliary_violation_fit="GO" if auxiliary_fit else "BLOCK_NO_TWO_TRAIN_CLASSES",
        auxiliary_violation_evaluation="GO" if auxiliary_eval else "BLOCK_NO_TWO_HELDOUT_CLASSES",
        statistical_strength="EXPLORATORY_FIVE_POLICIES_NOT_LARGE_SAMPLE_EVIDENCE")


def identifiability(X, groups):
    forbidden = {"policy_id", "master_state_id", "run_id", "sample_id", "oracle_call_id", "effective_rhs_id"}
    require(not forbidden & X[0].keys(), "Identity field in X")
    per_policy = {}
    for p in sorted({g["policy"] for g in groups}):
        rows = [X[int(r["X_data_row"])-1] for g in groups if g["policy"] == p for r in g["rows"]]
        constants = {name: next(iter(v)) for name in X[0] if len(v := {r[name] for r in rows}) == 1}
        per_policy[identity("policy-", p)] = dict(policy=list(p), constant_fields=constants)
    constant_all = set.intersection(*(set(v["constant_fields"]) for v in per_policy.values()))
    unique_proxies = [name for name in sorted(constant_all)
        if len({v["constant_fields"][name] for v in per_policy.values()}) == 5]
    by_run = defaultdict(dict)
    for g in groups:
        by_run[g["run_id"]][int(g["iteration_id"])] = g
    cross = []
    for g in groups:
        prev = by_run[g["run_id"]].get(int(g["iteration_id"])-1)
        if prev and prev["policy"] != g["policy"]:
            cross.append(dict(group_key=g["group_key"], queries=len(g["rows"]),
                preceding_policy=list(prev["policy"]), current_policy=list(g["policy"]),
                preceding_group_key=prev["group_key"], run_id=g["run_id"],
                source_file=g["rows"][0]["source_file"], source_file_sha256=g["rows"][0]["source_file_sha256"],
                current_iteration_json_pointer=f"/iterations/{int(g['iteration_id'])-1}",
                preceding_iteration_json_pointer=f"/iterations/{int(prev['iteration_id'])-1}",
                reason="master_lb_before is a certified statistic of the preceding policy Q; active/UB/iteration also encode adaptive run history"))
    return dict(direct_identity_columns_in_X=[], per_policy_constants=per_policy,
        individually_policy_identifying_constant_fields=unique_proxies,
        combined_identifier=dict(fields=["buffer_C", "buffer_T"], distinct_combinations=5,
            interpretation="legitimate physical input, not arbitrary identity token; memorization still possible"),
        legal_dynamic_proxies_retained=["buffer_C", "buffer_T", "buffer_O", "master_remaining_budget"],
        cross_policy_history_groups=cross, cross_policy_history_queries=sum(r["queries"] for r in cross),
        raw_84_view_status="BLOCK_FOR_STRICT_OUTER_TEST_LABEL_EXCLUSION_WITH_SHARED_RUNS",
        excluded_history_fields=list(HISTORY_FIELDS),
        exclusion_reason="causal provenance rule frozen before tuning, not fitted feature selection; original 84-column X remains unchanged")


def label_context_audit(labels):
    pairs = defaultdict(list)
    for row in labels:
        pairs[row["policy_rhs_id"]].append(row)
    variation = {}
    for field in ("Q_exact", "dense_rank", "is_worst", "is_violating"):
        varying = [rows for rows in pairs.values() if len({r[field] for r in rows}) > 1]
        variation[field] = dict(varying_policy_rhs_pairs=len(varying), affected_query_rows=sum(map(len, varying)))
    require(variation["Q_exact"]["varying_policy_rhs_pairs"] == 0, "Inconsistent exact policy/RHS objectives")
    return dict(fields=variation,
        interpretation="Q is policy/RHS invariant; rank and worst depend on candidate set, violation depends on current UB",
        frozen_primary_training_target="Q_exact regression, ascending predicted Q for within-group ranking",
        evaluation_labels="is_worst and dense_rank are group-scoped, not pooled context-free training targets",
        test_label_access="these are requested retrospective integrity diagnostics, not performance-based tuning")


def build_policy_cv(root, data, reports):
    root, data, reports = Path(root).resolve(), Path(data).resolve(), Path(reports).resolve()
    outputs = [data/"split_manifest_policy_cv_v1.json", data/"nested_cv_protocol_v1.json",
               reports/"policy_cv_audit.md", reports/"generalization_scope_v1.md"]
    require(not any(p.exists() for p in outputs), "Refuse overwrite of policy CV deliverables")
    X, labels, groups, feature_manifest, before = load_inputs(root, data)
    audit = identifiability(X, groups)
    policies = sorted({g["policy"] for g in groups})
    folds, inner_folds = [], []
    for test_policy in policies:
        train = [g for g in groups if g["policy"] != test_policy]
        test = [g for g in groups if g["policy"] == test_policy]
        fid = identity("outer-", test_policy)
        fold = dict(fold_id=fid, test_policy=list(test_policy), training_pool=partition(train), test=partition(test),
                    partition_audit=separation_audit(train, test), trainability=trainability(train, test))
        # Check numeric policy support without fitting a scaler or looking at model performance.
        fold["buffer_test_outside_train_range"] = [name for i, name in enumerate(("buffer_C","buffer_T","buffer_O"))
            if test_policy[i] < min(g["policy"][i] for g in train) or test_policy[i] > max(g["policy"][i] for g in train)]
        folds.append(fold)
        for validation_policy in sorted({g["policy"] for g in train}):
            inner_train = [g for g in train if g["policy"] != validation_policy]
            validation = [g for g in train if g["policy"] == validation_policy]
            require({g["policy"] for g in inner_train+validation} & {test_policy} == set(), "Outer test entered inner loop")
            inner_folds.append(dict(outer_fold_id=fid, outer_test_policy=list(test_policy), validation_policy=list(validation_policy),
                training=partition(inner_train), validation=partition(validation),
                partition_audit=separation_audit(inner_train, validation), trainability=trainability(inner_train, validation),
                preprocessing_fit_sample_ids=[r["sample_id"] for g in inner_train for r in g["rows"]]))
    primary_go = all(f["trainability"]["primary_ranking"] == "GO" for f in folds+inner_folds)
    # The five outer test partitions must cover every original sample exactly once.
    heldout_ids = [sid for f in folds for sid in f["test"]["sample_ids"]]
    require(len(heldout_ids) == len(set(heldout_ids)) == 576, "Outer test coverage conflict")
    feature_order = [s["name"] for s in feature_manifest["feature_fields"]]
    safe_order = [n for n in feature_order if n not in HISTORY_FIELDS]
    require(len(safe_order) == 78, "Safe feature view drift")
    common = dict(protocol_version="v1.policy_cv.1", scope=SCOPE, model_instance_id=feature_manifest["model_instance_id"],
        feature_version=feature_manifest["feature_version"], original_inputs_sha256=before,
        protocol_code_sha256=digest(Path(__file__)),
        original_unseen_rhs_split_status="BLOCKED_WITH_CURRENT_576_DATA", original_split_preserved=True,
        policy_generalization="POLICY_GENERALIZATION_GO" if primary_go else "NO-GO",
        primary_feature_view=dict(raw_columns=84, selected_columns=78, selected_feature_order=safe_order,
            excluded_fields=list(HISTORY_FIELDS), original_X_modified=False,
            selection="fixed causal provenance exclusion before any tuning"),
        primary_task="regress Q_exact and rank ascending within each complete finite candidate group; is_worst is an evaluation label",
        auxiliary_is_violating="NO-GO_FOR_COMPLETE_NESTED_CV", fitted=False, optimization_calls=0,
        model_training_calls=0, unseen_rhs_generalization="UNSEEN_RHS_GENERALIZATION_BLOCKED",
        cross_network_generalization="CROSS_NETWORK_GENERALIZATION_BLOCKED")
    split = dict(**common, outer_folds=folds, identifiability_audit=audit,
        exact_policy_count=5, query_count=576, group_count=33, policy_rhs_pairs=148,
        label_context_audit=label_context_audit(labels),
        alias_rule="same-policy effective-RHS and original calls stay together; RHS sharing across different policies is permitted",
        raw_84_protocol_status=audit["raw_84_view_status"])
    original_audit = json.loads((data/"training_dataset_manifest.json").read_text(encoding="utf-8"))["feature_leakage_audit"]
    split["feature_policy_leakage_audit"] = [dict(record,
        policy_cv_use="EXCLUDE_HISTORY" if record["feature_name"] in HISTORY_FIELDS else "RETAIN",
        policy_cv_reason="may encode held-out policy supervision through shared-run history" if record["feature_name"] in HISTORY_FIELDS
            else "static or physical policy/budget input; no Oracle outcome dependency") for record in original_audit]
    nested = dict(**common, inner_folds=inner_folds, outer_test_labels_use="audit counts and final one-shot evaluation only, never tuning",
        preprocessing=dict(fit="inner training samples only", validation="transform with saved inner-training state",
            feature_selection="fixed 78-column causal view; any future learned selection fit on inner training only",
            hyperparameter_selection="choose by mean of the four validation-policy group-macro scores within the outer pool",
            final_refit="after selection, fit fresh preprocessing/model on the four outer-training policies only",
            outer_test="transform only with outer-training state; no fit, early stopping, model/feature choice or missing-value statistics",
            persistence="record outer/inner fold IDs, training sample hashes, selected columns, encoding dictionary and preprocessing state",
            existing_preprocessor_compatibility="current FeaturePreprocessorV3 expects all 84 columns; future selected-column adapter/version is REQUIRED before any fitting; not implemented in this protocol task"),
        metrics=dict(primary="group-macro top1 hit among ALL tied worst scenarios; lower predicted Q scores first",
            secondary=["NDCG with binary is_worst relevance", "worst Recall@1/3/5", "pairwise concordance excluding equal-Q pairs"],
            inner_aggregation="mean within validation policy over full groups, then equal mean over 4 validation policies",
            outer_aggregation="equal mean of 5 held-out-policy scores; report all folds separately",
            predicted_score_ties="stable scenario ID for reproducible presentation only; ground-truth dense ties remain unchanged",
            repeated_calls="preserve whole groups; any training reweighting uses only training-fold (policy,RHS) repeat counts"),
        future_hyperparameter_rules=dict(ridge="strictly positive alpha; grid frozen before outer evaluations",
            gradient_boosting="small fixed depth/leaf grid validated against minimum inner-training size; no outer-test early stopping",
            early_stopping="disabled for V1; neither inner validation nor outer test may be used for early stopping"),
        label_firewall=dict(inner_train="labels permitted for fit", inner_validation="labels permitted only for inner scoring/selection",
            outer_test="Q/rank/is_worst/is_violating unavailable to training and selection code",
            audit_statistics="all-policy counts here are retrospective protocol diagnostics, NOT hyperparameter evidence"))
    report = render_audit(split, nested)
    scope = render_scope(split)
    reports.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(outputs, (split, nested, report, scope)):
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+"\n" if isinstance(payload, dict) else payload)
    require(before == {n: digest(data/n) for n in before}, "Original artifacts changed during protocol generation")
    return split, nested


def render_audit(split, nested):
    text = "# Policy LOPO 可辨识性与可训练性审计\n\n"
    text += "主排序结论：**POLICY_GENERALIZATION_GO，仅限冻结的78列保守视图**。原84列文件不修改；完整84列CV与辅助违反分类不获GO。此为协议可执行性预审，不是已训练、已取得性能或可部署的结论。\n\n"
    text += "## 外层五折\n\n| test policy | train policies | train/test组 | train/test查询 | train/test worst正例 | train/test violating正例 | train/test RHS数 | test RHS训练覆盖 | train/test并列组 |\n|---|---:|---|---|---|---|---|---|---|\n"
    for f in split["outer_folds"]:
        a, b = f["training_pool"]["stats"], f["test"]["stats"]
        text += f"| {f['test_policy']} | {a['policy_count']} | {a['group_count']}/{b['group_count']} | {a['query_count']}/{b['query_count']} | {a['is_worst_positive']}/{b['is_worst_positive']} | {a['is_violating_positive']}/{b['is_violating_positive']} | {a['effective_rhs_count']}/{b['effective_rhs_count']} | {f['partition_audit']['test_rhs_with_training_labels_fraction']:.1%} | {a['groups_with_tied_worst']}/{b['groups_with_tied_worst']} |\n"
    text += "\n所有主排序fold训练池都有完整组、最坏正反例和非恒定Q，内部训练至少3个policy。Ridge需正正则化；不能将84/78列与小样本简单比较后声称普通无正则回归可辨识。各fold候选集合大小分布、最坏并列规模和RHS覆盖详细记录在JSON。\n\n"
    for f in split["outer_folds"]:
        text += f"- 测试{f['test_policy']}：训练候选大小分布{f['training_pool']['stats']['candidate_size_distribution']}；测试{f['test']['stats']['candidate_size_distribution']}；缓冲数值超出训练范围字段{f['buffer_test_outside_train_range']}。\n"
    text += "\n五个外层测试fold的RHS训练标签覆盖均为100%。两个内层fold同时留出(0,350,0)与(915,0,0)，即外层test/内层validation分别为这两个policy时，inner train仅覆盖validation RHS的24/38（63.2%）；其余14个仍属于事前已知目录，但无该inner train监督值。其余内层fold覆盖100%。不能把该差异改称未见场景或新风险泛化。\n\n"
    text += "## 内层二十折\n\n| outer test | inner validation | train组/查询 | validation组/查询 | primary | violation fit/evaluation |\n|---|---|---|---|---|---|\n"
    for f in nested["inner_folds"]:
        a,b,t=f["training"]["stats"],f["validation"]["stats"],f["trainability"]
        text += f"| {f['outer_test_policy']} | {f['validation_policy']} | {a['group_count']}/{a['query_count']} | {b['group_count']}/{b['query_count']} | {t['primary_ranking']} | {t['auxiliary_violation_fit']}/{t['auxiliary_violation_evaluation']} |\n"
    text += "\n全部98条违反正例集中于(915,0,0)。外层留出它时训练违反正例为0；内层留出它时同样无法拟合二分类。其他policy的test违反正例为0，不能报告可比较的正类召回/AUC。因此is_violating仅保留审计，不进行完整嵌套CV辅助分类。\n\n"
    text += "同一policy/RHS的Q无冲突；但16个组合的dense_rank变化（316行），2个组合的is_worst变化（52行），9个组合的is_violating变化（134行）。这是有限候选集/UB条件的真实差异，不是脏标签，原记录不删除。基于定义而非test性能，冻结未来Ridge/GB基线为Q_exact回归、组内预测Q升序；is_worst与dense_rank仅作组内评估，不直接作为无候选上下文的混合分类目标。\n\n"
    text += "## Policy身份与合法动态输入\n\nX不含policy_id/master_state_id/run_id等身份列。buffer_C/T组合能区分5个历史policy，master_remaining_budget也在本样本中逐policy恒定且唯一；它们是合法物理/经济派生输入，保留，但小样本下仍可能被记忆。LOPO确保测试policy的完整缓冲组合未参加训练，不能据此宣称跨网络或跨资产配置泛化。网络计数和预算是共享常量，不能区分policy。逐policy全部常量字段清单在identifiability_audit中。\n\n"
    text += "## 调用时点正确不等于policy-held-out安全\n\n6组、166查询的previous LB来自另一policy（均为915→其他policy的历史转移）。同run还可能通过active、UB和iteration带入前序选择信息。为严格隔离外层test监督，所有fold事前固定排除master_iteration、master_active_count、master_ub、master_lb_before、master_lb_initialized、scenario_already_active，共保留78列。该排除基于来源因果关系，不用test性能做特征选择。\n\n"
    text += "原84列文件与原特征实现保持原字节；本任务未生成新特征或训练矩阵。现有预处理器固定84列，未来必须实现并单独核验78列适配器/版本后才可fit；当前只冻结协议。训练policy和Master数量仍是历史自适应产生的选择样本，故只验证本固定网络目录内的条件排序，不证明独立运行或因果性能。\n\n"
    text += "预处理、编码、缺失统计、任何拟合式特征选择只能用inner train。内层验证policy用于调参；外层test严禁参与fit、选择或早停。最终按选定超参数在四个outer train policy重新fit，然后只对test transform/evaluate。组内宏平均后按policy等权汇总，重复调用不当作独立网络。原split_manifest_v1.json及原BLOCK报告均保留。\n"
    text += "\n## 证据与复现\n\n数据来源为experiments/scenario_agent_v1/data/v3/下的X_features_v1.csv、y_labels_v1.csv、group_manifest_v1.csv、master_snapshots_v3.csv与两份原manifest。新JSON冻结全部输入SHA-256、当前协议脚本SHA-256、逐字段84项来源审查，以及6个跨policy历史组的原JSON路径/哈希/iteration指针。加载时复核25份历史JSON和原提取器代码哈希。\n\n历史LB递推见src/scenario_agent/v3_feature_extractor/historical.py的historical_records；Master字段见master_features.py的extract；active衍生字段见interaction_features.py的extract；固定84列预处理见preprocessing.py的FeaturePreprocessorV3。所有原文件保持不变。\n\n复现协议命令（仅在四个新输出不存在时运行）：`$env:PYTHONPATH='src'; python -m scenario_agent.policy_cv_protocol_v1`。已有输出会拒绝覆盖。确定性验证：`python -m pytest tests/test_scenario_policy_cv_v1.py`，不执行模型或优化器。\n"
    return text


def render_scope(split):
    return """# Scenario Agent V1 泛化目标冻结

## Scope A — 当前可验证

**Known-catalog, unseen-master-policy/state ranking.** 固定V3网络、61–74期模型和已知风险目录；未参与训练的完整first-stage policy作为外层测试，已知effective RHS可跨不同policy出现。相同(policy,effective_rhs)、原始调用及同policy别名必须在同一集合，完整排序组不拆分。

主排序协议为POLICY_GENERALIZATION_GO，限定78列事前冻结的保守输入视图、五外层policy折及每折四个内层policy折。本任务未fit预处理器或训练模型；GO仅表示主排序协议具备数据条件。原84列不修改；完整84列在跨policy历史依赖下暂BLOCK。辅助违反分类因正例只集中在915 policy，完整嵌套CV为NO-GO。

未来基线的目标冻结为Q_exact回归后组内升序排序；组内is_worst/dense_rank用于评价。相同policy/RHS的Q一致，而最坏标签依赖有限候选集合，不能把不同组的is_worst当作无上下文的等价二分类监督。

在线对应：Master给出新缓冲数量后，对目录内候选重新排序。保留合法buffer数量和预算派生值，拒绝policy_id等编号进入X。该验证不等于未见整段自适应运行；历史选择偏差、5个policy极少、915占大多数查询及数值外推必须披露。buffer_O全为0，无法验证正OEM缓冲或未见缓冲位置组合的效果。

## Scope B — 当前不可验证

Unseen-RHS generalization: **BLOCKED_WITH_CURRENT_576_DATA**。原split_manifest_v1.json保持原字节及原BLOCK，不撤销、不覆盖。33个完整组共享4个RHS，无法按RHS完全隔离形成非空train/validation/test。

未见effective RHS、新风险机制、跨供应链网络均不能从本协议得到泛化结论。只有一个来源网络，仍为UNSEEN_RHS_GENERALIZATION_BLOCKED和CROSS_NETWORK_GENERALIZATION_BLOCKED；未来需要新增独立风险/网络数据及相应分组协议。

不能将Scope A结果称为unseen-scenario generalization、cross-network generalization或new-disruption-type generalization。已知目录中部分RHS在某fold缺训练标签，也不能据此重新命名整体研究目标。

## 新旧协议关系与监督防火墙

新协议明确允许不同policy共享RHS，替代的仅是Scope A的分组条件，原Scope B的严格BLOCK继续有效。5个外层test policy的Q、rank、is_worst、is_violating仅可用于事后审计和最终一次评估；不得用于标准化、编码、缺失统计、调参、特征选择、模型选择或早停。6个历史过程字段事前排除，以避免held-out policy的前序Oracle标签经LB/active/UB进入训练视图。

内层仅使用四个outer train policy，做3 train + 1 validation；所有fit在inner train，最终重拟合也只用outer train。原始576查询、33组、148个policy/RHS组合全部保留，折ID/样本列表/组列表和每折诊断均写入新JSON；不修改原数据、正式C&CG或特征实现。
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--data", type=Path, default=Path("experiments/scenario_agent_v1/data/v3"))
    parser.add_argument("--reports", type=Path, default=Path("docs/scenario_agent_v1/training_dataset"))
    args = parser.parse_args()
    split, nested = build_policy_cv(args.root, args.data, args.reports)
    print(json.dumps(dict(policy_generalization=split["policy_generalization"], outer_folds=len(split["outer_folds"]),
        inner_folds=len(nested["inner_folds"]), auxiliary=split["auxiliary_is_violating"],
        unseen_rhs=split["unseen_rhs_generalization"], cross_network=split["cross_network_generalization"]), indent=2))


if __name__ == "__main__":
    main()
