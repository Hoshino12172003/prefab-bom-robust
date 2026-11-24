# Scenario Agent V1 正式训练数据审计

最终状态：**BLOCK（正式切分与基准训练准入）**。特征、标签和未来时点检查通过；不宣称正式数据集整体验收通过。

数据目录：`experiments/scenario_agent_v1/data/v3/`。只新增本轮产物；原始Excel、JSON、标准层、统一提取器和原manifest未覆盖。没有优化、模型训练或预处理fit。

## 核验结果

| 检查 | 结果 |
|---|---|
| queries | PASS 576/576 |
| complete_ranking_groups | PASS 33/33 |
| policy_rhs_pairs | PASS 148 retained |
| raw_feature_matrix | PASS 576 x 84, fixed order, IDs excluded |
| first_round_lb | PASS 322 NULL |
| previous_certified_lb | PASS 254 |
| worst_and_dense_ties | PASS independent recomputation |
| strict_violation | PASS same-round UB, 1e-6 |
| nominal_loss | PASS 356 available / 220 NULL |
| future_information | PASS 84 field/code/time checks |
| strict_train_validation_test_split | BLOCK one association component |
| cross_partition_leakage | NOT_EVALUABLE_NO_VALID_SPLIT |
| baseline_training | BLOCK |
| preprocessor | UNFITTED |

X为576×84，字段完全按原feature_manifest顺序，无ID列。y以sample_id和X_data_row关联X的1-based数据行（不含表头），保存原文件SHA/JSON指针。group_manifest为33行完整组，并保存成员行号、sample_ids和实际候选集。

完整group_key由(run_id, iteration_id, master_state_id, candidate_set_hash, objective_version)内容寻址。candidate_set_hash包括模型ID及排序后的(scenario_id,effective_rhs_id)集合，不含访问顺序或目标值。候选集合严格与该run的原benchmark/names核对。

## 标签口径

主标签在各组有限候选集合中取Q最小值，全部并列最坏为1；dense_rank只依赖Q，不用字典序拆分并列。严格违反使用同轮Master UB及Q < UB−1e−6。实际损失只用同轮、同政策NR精确基准；356条可用、220条缺失。demand_shortfall=28000−Q是需求服务缺口，并非中断损失。标签不是全目录最坏认证。

关联图有33个组、528条边、1个连通分量。全部组共享4个RHS。其共同代表场景为DE_ENGINE_61、DE_GEAR_61、DE_ENGINE_68、DE_GEAR_68；33组任意两组都相关联。

即使只考虑(policy,RHS)与同run关联，组件数也记录在split_manifest，不以弱化约束强行制造分割。嵌套/相等候选集合的每对关系与政策族均留档。训练/验证/测试分配全部为空、每组partition=null；不能把空测试集解释为无泄漏测试通过。

## 替代验证方案与停止边界

当前没有可运行的严格组件级holdout或GroupKFold。应先获得额外不相连的完整目录/运行组件，再按组件划分训练、验证、测试；重复种子不产生新独立组件。现有数据可做描述性或组内拟合检查，但不得报告为独立留出性能。Leave-policy-family-out仍共享RHS，违反本任务约束；仅可作为今后另行批准的条件泛化协议，当前未执行。单网络不支持跨网络泛化声明。

预处理规范已冻结但未拟合，mean/scale/counts均为null。任何正式fit和基准模型训练均BLOCK。完成本次文件构建不等于获得训练准入。
