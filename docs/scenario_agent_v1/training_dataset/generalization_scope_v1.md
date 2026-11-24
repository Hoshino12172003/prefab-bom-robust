# Scenario Agent V1 泛化目标冻结

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
