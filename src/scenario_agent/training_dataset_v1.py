"""Materialize V1 X/y and audit group connectivity without fitting or forced splits."""
import argparse
import ast
import csv
import json
from collections import defaultdict
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

from .v3_feature_extractor import ScenarioFeatureExtractorV3, load_standardized_v3
from .v3_feature_extractor import network_features, scenario_features, master_features, interaction_features
from .v3_feature_extractor.build import write_csv
from .v3_feature_extractor.extractor import SPECS
from .v3_feature_extractor.historical import historical_records
from .v3_feature_extractor.manifest import MODEL_INSTANCE_ID, check_hash, digest, identity
from .v3_feature_extractor.schema import FEATURE_VERSION, RESOURCES

OBJECTIVE = "V3_on_time_count"
DATA_FILES = ("X_features_v1.csv", "y_labels_v1.csv", "group_manifest_v1.csv",
              "split_manifest_v1.json", "preprocessing_spec_v1.json", "training_dataset_manifest.json")
REPORT_FILES = ("training_dataset_audit.md", "leakage_audit.md")
FORBIDDEN = {"oracle_objective", "Q_exact", "oracle_worst", "worst_ties", "added_scenario",
             "solver_runtime_s", "solver_seconds", "node_count", "NodeCount", "lower", "lb_after_oracle"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_feature_sources(root, feature_manifest):
    require(feature_manifest["feature_fields"] == [asdict(s) for s in SPECS], "Feature specification drift")
    for rel, expected in feature_manifest["extractor_code_sha256"].items():
        check_hash(root / rel, expected)
    modules = (network_features, scenario_features, master_features, interaction_features)
    allowed_state = {"iteration_id", "policy", "active_rhs_ids", "budget", "spent", "ub", "lb_before_oracle"}
    results = []
    for module in modules:
        path = Path(module.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Audit the actual feature functions AND graph/signature helpers, not just descriptive column names.
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name != "load_scenarios"]
        for function in functions:
            for node in ast.walk(function):
                if isinstance(node, ast.Attribute):
                    require(node.attr not in FORBIDDEN, f"Future outcome access: {path.name}:{node.lineno}")
                    if isinstance(node.value, ast.Name) and node.value.id == "state":
                        require(node.attr in allowed_state, f"Unknown Master feature source: {node.attr}")
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    require(node.value not in FORBIDDEN, f"Future outcome key: {path.name}:{node.lineno}")
        for spec in module.SPECS:
            require(spec.name not in FORBIDDEN and spec.information_time == "after_master_before_oracle",
                    f"Feature information-time conflict: {spec.name}")
            dynamic = module in (master_features, interaction_features)
            timestamp = "static_inputs_available_before_oracle"
            if dynamic:
                timestamp = "after_current_master_before_current_oracle"
            if spec.name == "master_lb_before":
                timestamp = "previous_iteration_certified_LB_before_current_oracle; NULL_at_first_round"
            results.append(dict(feature_name=spec.name, source=spec.source, formula=spec.formula,
                information_timestamp=timestamp, leakage_risk="CONTROLLED_TEMPORAL" if dynamic else "LOW_STATIC",
                audit_result="PASS", source_code=path.relative_to(root).as_posix(),
                source_code_sha256=digest(path), nullable=spec.nullable, dtype=spec.dtype, unit=spec.unit))
    require([r["feature_name"] for r in results] == [s.name for s in SPECS], "Leakage audit field/order mismatch")
    return results


def label_group(records, upper):
    """Labels are scoped to this complete finite candidate group, never the entire catalog."""
    require(len({r["scenario_id"] for r in records}) == len(records), "Repeated query inside ranking group")
    q = {r["scenario_id"]: r["Q_exact"] for r in records}
    require(all(type(v) is int and 0 <= v <= 28000 for v in q.values()), "Nonexact Q label")
    worst = min(q.values())
    ranks = {v: i+1 for i, v in enumerate(sorted(set(q.values())))}
    return {name: dict(Q_exact=value, U_k=upper, dense_rank=ranks[value], is_worst=int(value == worst),
        is_violating=int(value < upper-1e-6),
        actual_disruption_loss=q["NR"]-value if "NR" in q else None,
        demand_shortfall=28000-value, label_source="exact_milp",
        label_scope="this_group_finite_candidate_set") for name, value in q.items()}


def components(group_ids, edges, reasons=None):
    adjacency = {g: set() for g in group_ids}
    for e in edges:
        if reasons is None or set(e["reasons"]) & set(reasons):
            adjacency[e["left"]].add(e["right"])
            adjacency[e["right"]].add(e["left"])
    unseen, found = set(group_ids), []
    while unseen:
        frontier, part = [min(unseen)], set()
        while frontier:
            g = frontier.pop()
            if g not in part:
                part.add(g)
                frontier.extend(adjacency[g]-part)
        unseen -= part
        found.append(sorted(part))
    return sorted(found, key=lambda v: v[0])


def split_preflight(groups):
    """Conservative association graph. Never split a connected component."""
    edges, nested = [], []
    for a, b in combinations(groups, 2):
        rhs_a, rhs_b = set(a["effective_rhs_ids_json"]), set(b["effective_rhs_ids_json"])
        shared = sorted(rhs_a & rhs_b)
        reasons = []
        if shared:
            reasons.append("shared_effective_rhs_including_aliases")
            if a["policy_json"] == b["policy_json"]:
                reasons.append("shared_policy_effective_rhs")
        if a["run_id"] == b["run_id"]:
            reasons.append("same_run")
        relation = "equal" if rhs_a == rhs_b else "strict_nested" if rhs_a < rhs_b or rhs_b < rhs_a else None
        if relation:
            nested.append(dict(left=a["group_key"], right=b["group_key"], relation=relation))
            reasons.append("nested_candidate_sets")
        if a["policy_family"] == b["policy_family"]:
            reasons.append("same_buffer_location_policy_family")
        if reasons:
            edges.append(dict(left=a["group_key"], right=b["group_key"], reasons=reasons, shared_rhs_ids=shared))
    ids = [g["group_key"] for g in groups]
    parts = components(ids, edges)
    common = sorted(set.intersection(*(set(g["effective_rhs_ids_json"]) for g in groups)))
    # Only one component is available in the audited cohort; no arbitrary allocation is permitted.
    blocked = len(parts) < 3
    require(blocked, "Association graph changed: a new split protocol needs review before allocation")
    return dict(status="BLOCK", reason="ONE_CONNECTED_COMPONENT_NO_NONEMPTY_THREE_WAY_GROUP_SPLIT",
        constraints=["complete_groups_indivisible", "same_policy_rhs_no_cross_partition",
            "same_rhs_aliases_no_cross_partition", "same_run_linkage", "nested_candidates_review",
            "policy_location_family_review"],
        group_count=len(groups), connected_component_count=len(parts), components=parts,
        edge_count=len(edges), edges=edges, nested_candidate_relations=nested,
        common_rhs_to_all_groups=common,
        policy_rhs_plus_run_component_count=len(components(ids, edges, ["shared_policy_effective_rhs", "same_run"])),
        same_rhs_only_component_count=len(components(ids, edges, ["shared_effective_rhs_including_aliases"])),
        partitions=dict(train=[], validation=[], test=[]),
        group_assignments={g: None for g in ids},
        cross_partition_leakage_status="NOT_EVALUABLE_NO_VALID_SPLIT",
        leakage_free_split_certified=False, preprocessing_fit_permitted=False, baseline_training_ready=False,
        alternatives=[
            "Hold out entire association components after collecting independent complete candidate catalogs/runs; current one-component data cannot run component-level CV.",
            "Current data may support descriptive/in-sample checks only, never reported as held-out performance.",
            "Leave-policy-family-out reuses RHS across folds and violates the current strict protocol; it would require a separately approved conditional-generalization protocol.",
        ], independent_networks=1, cross_network_generalization_supported=False)


def preprocessing_spec(fields):
    names = [f["name"] for f in fields]
    binary = [f["name"] for f in fields if f["unit"] == "boolean"]
    return dict(version="v1.preprocessing.spec.1", feature_version=FEATURE_VERSION, fitted=False,
        fit_status="BLOCK_UNTIL_VALID_GROUP_SPLIT", implementation="FeaturePreprocessorV3",
        feature_order=names, feature_schema=fields, numeric_columns=[n for n in names if n not in binary],
        binary_columns=binary, raw_categorical_columns=[],
        encoding_dictionaries=dict(binary={"false": 0, "true": 1},
            risk_resource=list(RESOURCES),
            resource_encoding="fixed six multi-hot/present fields already in raw features; no ordinal resource ID"),
        unknown_category_policy="ERROR_STOP; no new columns, silent all-zero encoding or ordinal IDs",
        id_columns_in_X=[], row_linkage="X data row number joins y_labels.sample_id; X has exactly 84 fields",
        missing=dict(raw="NULL/empty CSV cell", first_round_lb="NULL + master_lb_initialized=0",
            processed="training-fold observed mean + appended missing flag for every raw feature",
            all_missing_training_column="numeric baseline 0 plus missing flag; raw stays NULL",
            validation_test="use saved training-fold parameters only"),
        ridge=dict(imputation="training-fold mean", scaling="population std after mean imputation, all 84 numeric/encoded columns",
            zero_variance="scale=1", fit_scope="training_partition_only"),
        gradient_boosting=dict(imputation="same training-fold mean", scaling="none", fit_scope="training_partition_only"),
        transformed_feature_order=names+[n+"__missing" for n in names],
        parameters=dict(mean=None, scale=None, observed_counts=None),
        prediction="load saved preprocessor then transform only; fit/refit forbidden")


def _reports(root, data, audit, feature_audit, split, groups):
    counts = audit["checks"]
    text = "# Scenario Agent V1 正式训练数据审计\n\n"
    text += "最终状态：**BLOCK（正式切分与基准训练准入）**。特征、标签和未来时点检查通过；不宣称正式数据集整体验收通过。\n\n"
    text += "数据目录：`experiments/scenario_agent_v1/data/v3/`。只新增本轮产物；原始Excel、JSON、标准层、统一提取器和原manifest未覆盖。没有优化、模型训练或预处理fit。\n\n"
    text += "## 核验结果\n\n| 检查 | 结果 |\n|---|---|\n"
    for key, value in counts.items():
        text += f"| {key} | {value} |\n"
    text += f"\nX为576×84，字段完全按原feature_manifest顺序，无ID列。y以sample_id和X_data_row关联X的1-based数据行（不含表头），保存原文件SHA/JSON指针。group_manifest为33行完整组，并保存成员行号、sample_ids和实际候选集。\n\n"
    text += "完整group_key由(run_id, iteration_id, master_state_id, candidate_set_hash, objective_version)内容寻址。candidate_set_hash包括模型ID及排序后的(scenario_id,effective_rhs_id)集合，不含访问顺序或目标值。候选集合严格与该run的原benchmark/names核对。\n\n"
    text += "## 标签口径\n\n主标签在各组有限候选集合中取Q最小值，全部并列最坏为1；dense_rank只依赖Q，不用字典序拆分并列。严格违反使用同轮Master UB及Q < UB−1e−6。实际损失只用同轮、同政策NR精确基准；356条可用、220条缺失。demand_shortfall=28000−Q是需求服务缺口，并非中断损失。标签不是全目录最坏认证。\n\n"
    text += f"关联图有{split['group_count']}个组、{split['edge_count']}条边、{split['connected_component_count']}个连通分量。全部组共享{len(split['common_rhs_to_all_groups'])}个RHS。其共同代表场景为DE_ENGINE_61、DE_GEAR_61、DE_ENGINE_68、DE_GEAR_68；33组任意两组都相关联。\n\n"
    text += "即使只考虑(policy,RHS)与同run关联，组件数也记录在split_manifest，不以弱化约束强行制造分割。嵌套/相等候选集合的每对关系与政策族均留档。训练/验证/测试分配全部为空、每组partition=null；不能把空测试集解释为无泄漏测试通过。\n\n"
    text += "## 替代验证方案与停止边界\n\n当前没有可运行的严格组件级holdout或GroupKFold。应先获得额外不相连的完整目录/运行组件，再按组件划分训练、验证、测试；重复种子不产生新独立组件。现有数据可做描述性或组内拟合检查，但不得报告为独立留出性能。Leave-policy-family-out仍共享RHS，违反本任务约束；仅可作为今后另行批准的条件泛化协议，当前未执行。单网络不支持跨网络泛化声明。\n\n"
    text += "预处理规范已冻结但未拟合，mean/scale/counts均为null。任何正式fit和基准模型训练均BLOCK。完成本次文件构建不等于获得训练准入。\n"
    leakage = "# 逐字段未来信息泄漏审计\n\n"
    leakage += "结论：**84/84字段时点审计PASS**；未发现本轮Oracle结果进入特征。独立的关联切分检查为BLOCK，因此总体训练准入仍BLOCK。\n\n"
    leakage += "检查实际源码及其已冻结哈希、字段规范、Master状态构造和原JSON指针；不只搜索特征名称。所有行再次调用现有ScenarioFeatureExtractorV3.extract，没有另一套特征计算。静态图可达性只表示潜在暴露，不是由Q拟合的影响量。\n\n"
    leakage += "| feature_name | source | formula | information_timestamp | leakage_risk | audit_result |\n|---|---|---|---|---|---|\n"
    for r in feature_audit:
        leakage += "| " + " | ".join(str(r[k]).replace("|", "/") for k in (
            "feature_name", "source", "formula", "information_timestamp", "leakage_risk", "audit_result")) + " |\n"
    leakage += "\n## 动态字段证据\n\nMaster政策/active/UB只从对应iterations[offset]读取。第k>1轮LB严格取同run iterations[k−2].lower，即前轮已认证值；322条首轮保持NULL，254条为前轮LB。state_id与原标准层一致。检查当前/后续结果字段的读访问及函数参数，禁止本轮Q、最坏集合、added_scenario、运行时间、NodeCount和本轮lower进入提取器。\n\n"
    leakage += "is_worst、is_violating、actual_disruption_loss和demand_shortfall只在y中。样本ID、RHS哈希、重复次数和源码路径只在关联层。X不包含它们。master_lb_initialized及风险present标志是当前可知的缺失/不适用信息，不是事后标签。\n\n"
    leakage += "CONTROLLED_TEMPORAL表示该字段依赖前序求解历史，应在切分时保持同run和关联组；它不是本轮未来信息泄漏，也不证明训练/测试独立。关联图全部连通，跨partition泄漏审计为NOT_EVALUABLE_NO_VALID_SPLIT；未签发无关联泄漏的正式切分。\n"
    return {"training_dataset_audit.md": text, "leakage_audit.md": leakage}


def build_training_dataset(root, data, reports):
    root, data, reports = Path(root).resolve(), Path(data).resolve(), Path(reports).resolve()
    targets = [data / n for n in DATA_FILES] + [reports / n for n in REPORT_FILES]
    require(not any(p.exists() for p in targets), "Refuse overwrite: one or more V1 deliverables already exist")
    manifest_path = data / "feature_manifest_v3.json"
    feature_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_audit = audit_feature_sources(root, feature_manifest)
    network = load_standardized_v3(root, data)
    scenarios = scenario_features.load_scenarios(network)
    snapshots, calls, old_labels, samples, contexts, historical_sources = historical_records(network, scenarios)
    # Existing standardized layers must agree byte-for-byte on the original call identities.
    with (data / "oracle_calls_v3.csv").open(encoding="utf-8", newline="") as f:
        require([r["oracle_call_id"] for r in csv.DictReader(f)] == [r["oracle_call_id"] for r in calls],
                "Original call order/identity conflict")
    rows_by_state, context_by_call = defaultdict(list), {call_id: (scenario, state) for call_id, scenario, state in contexts}
    for row in calls:
        rows_by_state[row["master_state_id"]].append(row)
    X, y, groups = [], [], []
    group_by_state = {}
    for snapshot in snapshots:
        gid = snapshot["master_state_id"]
        records = rows_by_state[gid]
        candidates = snapshot["candidate_scenarios_json"]
        require(len(records) == len(candidates) and {r["scenario_id"] for r in records} == set(candidates),
                "Incomplete ranking candidate set")
        policy = [snapshot[k] for k in ("x_C", "x_T", "x_O")]
        require(all(context_by_call[r["oracle_call_id"]][1].policy == tuple(policy) for r in records), "Mixed group policies")
        require(all(r["solver_status"] == "OPTIMAL" and r["mip_gap"] == 0 for r in records), "Uncertified group result")
        q_records = [dict(scenario_id=r["scenario_id"], Q_exact=r["best_bound"]) for r in records]
        labels = label_group(q_records, snapshot["ub_before_oracle"])
        candidate_hash = identity("candidates-", [MODEL_INSTANCE_ID, sorted((n, scenarios[n].rhs_id) for n in candidates)])
        group_key = identity("group-", [snapshot["run_id"], snapshot["iteration_id"], gid, candidate_hash, OBJECTIVE])
        group = dict(group_key=group_key, run_id=snapshot["run_id"], iteration_id=snapshot["iteration_id"],
            master_state_id=gid, candidate_set_hash=candidate_hash, objective_version=OBJECTIVE,
            policy_json=policy, policy_family="".join(n for n, v in zip("CTO", policy) if v > 0) or "ZERO",
            candidate_count=len(candidates), candidates_json=candidates,
            effective_rhs_ids_json=sorted(scenarios[n].rhs_id for n in candidates),
            W_exact=min(v["Q_exact"] for v in labels.values()), U_k=snapshot["ub_before_oracle"],
            worst_count=sum(v["is_worst"] for v in labels.values()),
            worst_scenarios_json=sorted(n for n, v in labels.items() if v["is_worst"]),
            sample_ids_json=[], X_data_rows_json=[], complete=True, exact=True)
        groups.append(group)
        group_by_state[gid] = (group, labels)
    old_by_call = {r["oracle_call_id"]: r for r in old_labels}
    extractor = ScenarioFeatureExtractorV3()
    for index, row in enumerate(calls, 1):
        call_id = row["oracle_call_id"]
        scenario, state = context_by_call[call_id]
        vector = extractor.extract(network, scenario, state)
        require(list(vector.values) == [s.name for s in SPECS], "X feature order drift")
        X.append(vector.as_dict())
        group, labels = group_by_state[state.state_id]
        label = labels[scenario.name]
        old = old_by_call[call_id]
        require((label["Q_exact"], label["dense_rank"], label["is_worst"], label["is_violating"],
                 label["actual_disruption_loss"], label["demand_shortfall"]) ==
                (old["oracle_objective"], old["dense_risk_rank"], old["is_worst"], old["is_strict_violation"],
                 old["disruption_loss"], old["service_shortfall"]), "Independent label recomputation conflict")
        y.append(dict(sample_id=call_id, X_data_row=index, oracle_call_id=call_id, group_key=group["group_key"],
            **label, model_instance_id=MODEL_INSTANCE_ID, objective_version=OBJECTIVE, policy_rhs_id=row["policy_rhs_id"],
            effective_rhs_id=row["effective_rhs_id"], scenario_id=scenario.name,
            source_file=row["source_file"], source_file_sha256=row["source_file_sha256"], json_pointer=row["json_pointer"]))
        group["sample_ids_json"].append(call_id)
        group["X_data_rows_json"].append(index)
    require((len(X), len(groups), len({r["policy_rhs_id"] for r in y}), len({r["sample_id"] for r in y})) == (576, 33, 148, 576), "Dataset identity/count conflict")
    require(sum(v["master_lb_before"] is None for v in X) == 322, "First-round NULL LB conflict")
    require(all(v["master_lb_initialized"] == int(v["master_lb_before"] is not None) for v in X), "LB missing flag conflict")
    require(sum(r["actual_disruption_loss"] is not None for r in y) == 356, "Nominal loss availability conflict")
    split = split_preflight(groups)
    spec = preprocessing_spec(feature_manifest["feature_fields"])
    checks = dict(queries="PASS 576/576", complete_ranking_groups="PASS 33/33", policy_rhs_pairs="PASS 148 retained",
        raw_feature_matrix="PASS 576 x 84, fixed order, IDs excluded", first_round_lb="PASS 322 NULL",
        previous_certified_lb="PASS 254", worst_and_dense_ties="PASS independent recomputation",
        strict_violation="PASS same-round UB, 1e-6", nominal_loss="PASS 356 available / 220 NULL",
        future_information="PASS 84 field/code/time checks", strict_train_validation_test_split="BLOCK one association component",
        cross_partition_leakage="NOT_EVALUABLE_NO_VALID_SPLIT", baseline_training="BLOCK", preprocessor="UNFITTED")
    audit = dict(status="BLOCK", baseline_training_ready=False, checks=checks,
        query_count=len(X), feature_count=len(SPECS), group_count=len(groups),
        pair_count=148, duplicate_original_call_ids=0,
        groups_with_tied_worst=sum(g["worst_count"] > 1 for g in groups),
        worst_positive_rows=sum(r["is_worst"] for r in y), violating_positive_rows=sum(r["is_violating"] for r in y),
        null_counts={s.name: sum(v[s.name] is None for v in X) for s in SPECS},
        label_scope="group finite candidates only", feature_information_leakage_detected=False)
    report_text = _reports(root, data, audit, feature_audit, split, groups)
    reports.mkdir(parents=True, exist_ok=True)
    write_csv(data / "X_features_v1.csv", X)
    write_csv(data / "y_labels_v1.csv", y)
    write_csv(data / "group_manifest_v1.csv", groups)
    for name, payload in (("split_manifest_v1.json", split), ("preprocessing_spec_v1.json", spec)):
        with (data / name).open("x", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    for name, text in report_text.items():
        with (reports / name).open("x", encoding="utf-8") as f:
            f.write(text)
    artifacts = [p for p in targets if p.name != "training_dataset_manifest.json"]
    manifest = dict(dataset_version="scenario-agent-v1.dataset.1", feature_version=FEATURE_VERSION,
        model_instance_id=MODEL_INSTANCE_ID, status="BLOCK", baseline_training_ready=False,
        audit=audit, feature_leakage_audit=feature_audit, fitted=False, optimization_calls=0, model_training_calls=0,
        original_feature_manifest_sha256=digest(manifest_path), historical_sources=historical_sources,
        implementation_sha256={Path(__file__).relative_to(root).as_posix(): digest(__file__)},
        row_linkage="X data row is 1-based excluding header; y.sample_id=oracle_call_id; group members link the same rows",
        outputs={(p.relative_to(root).as_posix() if p.is_relative_to(root) else p.as_posix()): digest(p) for p in artifacts},
        original_source_preserved=True, split_status=split["status"])
    with (data / "training_dataset_manifest.json").open("x", encoding="utf-8") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--data", type=Path, default=Path("experiments/scenario_agent_v1/data/v3"))
    parser.add_argument("--reports", type=Path, default=Path("docs/scenario_agent_v1/training_dataset"))
    args = parser.parse_args()
    result = build_training_dataset(args.root, args.data, args.reports)
    print(json.dumps(result["audit"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
