# Policy LOPO 可辨识性与可训练性审计

主排序结论：**POLICY_GENERALIZATION_GO，仅限冻结的78列保守视图**。原84列文件不修改；完整84列CV与辅助违反分类不获GO。此为协议可执行性预审，不是已训练、已取得性能或可部署的结论。

## 外层五折

| test policy | train policies | train/test组 | train/test查询 | train/test worst正例 | train/test violating正例 | train/test RHS数 | test RHS训练覆盖 | train/test并列组 |
|---|---:|---|---|---|---|---|---|---|
| [0, 345, 0] | 4 | 32/1 | 552/24 | 52/1 | 98/0 | 38/24 | 100.0% | 20/0 |
| [0, 350, 0] | 4 | 30/3 | 482/94 | 50/3 | 98/0 | 38/38 | 100.0% | 20/0 |
| [337, 0, 0] | 4 | 31/2 | 528/48 | 51/2 | 98/0 | 38/24 | 100.0% | 20/0 |
| [354, 0, 0] | 4 | 32/1 | 552/24 | 52/1 | 98/0 | 38/24 | 100.0% | 20/0 |
| [915, 0, 0] | 4 | 7/26 | 190/386 | 7/46 | 0/98 | 38/38 | 100.0% | 0/20 |

所有主排序fold训练池都有完整组、最坏正反例和非恒定Q，内部训练至少3个policy。Ridge需正正则化；不能将84/78列与小样本简单比较后声称普通无正则回归可辨识。各fold候选集合大小分布、最坏并列规模和RHS覆盖详细记录在JSON。

- 测试[0, 345, 0]：训练候选大小分布{4: 5, 8: 5, 16: 10, 24: 8, 32: 2, 38: 2}；测试{24: 1}；缓冲数值超出训练范围字段[]。
- 测试[0, 350, 0]：训练候选大小分布{4: 5, 8: 5, 16: 10, 24: 8, 32: 1, 38: 1}；测试{24: 1, 32: 1, 38: 1}；缓冲数值超出训练范围字段['buffer_T']。
- 测试[337, 0, 0]：训练候选大小分布{4: 5, 8: 5, 16: 10, 24: 7, 32: 2, 38: 2}；测试{24: 2}；缓冲数值超出训练范围字段[]。
- 测试[354, 0, 0]：训练候选大小分布{4: 5, 8: 5, 16: 10, 24: 8, 32: 2, 38: 2}；测试{24: 1}；缓冲数值超出训练范围字段[]。
- 测试[915, 0, 0]：训练候选大小分布{24: 5, 32: 1, 38: 1}；测试{4: 5, 8: 5, 16: 10, 24: 4, 32: 1, 38: 1}；缓冲数值超出训练范围字段['buffer_C']。

五个外层测试fold的RHS训练标签覆盖均为100%。两个内层fold同时留出(0,350,0)与(915,0,0)，即外层test/内层validation分别为这两个policy时，inner train仅覆盖validation RHS的24/38（63.2%）；其余14个仍属于事前已知目录，但无该inner train监督值。其余内层fold覆盖100%。不能把该差异改称未见场景或新风险泛化。

## 内层二十折

| outer test | inner validation | train组/查询 | validation组/查询 | primary | violation fit/evaluation |
|---|---|---|---|---|---|
| [0, 345, 0] | [0, 350, 0] | 29/458 | 3/94 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [0, 345, 0] | [337, 0, 0] | 30/504 | 2/48 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [0, 345, 0] | [354, 0, 0] | 31/528 | 1/24 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [0, 345, 0] | [915, 0, 0] | 6/166 | 26/386 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/GO |
| [0, 350, 0] | [0, 345, 0] | 29/458 | 1/24 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [0, 350, 0] | [337, 0, 0] | 28/434 | 2/48 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [0, 350, 0] | [354, 0, 0] | 29/458 | 1/24 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [0, 350, 0] | [915, 0, 0] | 4/96 | 26/386 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/GO |
| [337, 0, 0] | [0, 345, 0] | 30/504 | 1/24 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [337, 0, 0] | [0, 350, 0] | 28/434 | 3/94 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [337, 0, 0] | [354, 0, 0] | 30/504 | 1/24 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [337, 0, 0] | [915, 0, 0] | 5/142 | 26/386 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/GO |
| [354, 0, 0] | [0, 345, 0] | 31/528 | 1/24 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [354, 0, 0] | [0, 350, 0] | 29/458 | 3/94 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [354, 0, 0] | [337, 0, 0] | 30/504 | 2/48 | GO | GO/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [354, 0, 0] | [915, 0, 0] | 6/166 | 26/386 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/GO |
| [915, 0, 0] | [0, 345, 0] | 6/166 | 1/24 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [915, 0, 0] | [0, 350, 0] | 4/96 | 3/94 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [915, 0, 0] | [337, 0, 0] | 5/142 | 2/48 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/BLOCK_NO_TWO_HELDOUT_CLASSES |
| [915, 0, 0] | [354, 0, 0] | 6/166 | 1/24 | GO | BLOCK_NO_TWO_TRAIN_CLASSES/BLOCK_NO_TWO_HELDOUT_CLASSES |

全部98条违反正例集中于(915,0,0)。外层留出它时训练违反正例为0；内层留出它时同样无法拟合二分类。其他policy的test违反正例为0，不能报告可比较的正类召回/AUC。因此is_violating仅保留审计，不进行完整嵌套CV辅助分类。

同一policy/RHS的Q无冲突；但16个组合的dense_rank变化（316行），2个组合的is_worst变化（52行），9个组合的is_violating变化（134行）。这是有限候选集/UB条件的真实差异，不是脏标签，原记录不删除。基于定义而非test性能，冻结未来Ridge/GB基线为Q_exact回归、组内预测Q升序；is_worst与dense_rank仅作组内评估，不直接作为无候选上下文的混合分类目标。

## Policy身份与合法动态输入

X不含policy_id/master_state_id/run_id等身份列。buffer_C/T组合能区分5个历史policy，master_remaining_budget也在本样本中逐policy恒定且唯一；它们是合法物理/经济派生输入，保留，但小样本下仍可能被记忆。LOPO确保测试policy的完整缓冲组合未参加训练，不能据此宣称跨网络或跨资产配置泛化。网络计数和预算是共享常量，不能区分policy。逐policy全部常量字段清单在identifiability_audit中。

## 调用时点正确不等于policy-held-out安全

6组、166查询的previous LB来自另一policy（均为915→其他policy的历史转移）。同run还可能通过active、UB和iteration带入前序选择信息。为严格隔离外层test监督，所有fold事前固定排除master_iteration、master_active_count、master_ub、master_lb_before、master_lb_initialized、scenario_already_active，共保留78列。该排除基于来源因果关系，不用test性能做特征选择。

原84列文件与原特征实现保持原字节；本任务未生成新特征或训练矩阵。现有预处理器固定84列，未来必须实现并单独核验78列适配器/版本后才可fit；当前只冻结协议。训练policy和Master数量仍是历史自适应产生的选择样本，故只验证本固定网络目录内的条件排序，不证明独立运行或因果性能。

预处理、编码、缺失统计、任何拟合式特征选择只能用inner train。内层验证policy用于调参；外层test严禁参与fit、选择或早停。最终按选定超参数在四个outer train policy重新fit，然后只对test transform/evaluate。组内宏平均后按policy等权汇总，重复调用不当作独立网络。原split_manifest_v1.json及原BLOCK报告均保留。

## 证据与复现

数据来源为experiments/scenario_agent_v1/data/v3/下的X_features_v1.csv、y_labels_v1.csv、group_manifest_v1.csv、master_snapshots_v3.csv与两份原manifest。新JSON冻结全部输入SHA-256、当前协议脚本SHA-256、逐字段84项来源审查，以及6个跨policy历史组的原JSON路径/哈希/iteration指针。加载时复核25份历史JSON和原提取器代码哈希。

历史LB递推见src/scenario_agent/v3_feature_extractor/historical.py的historical_records；Master字段见master_features.py的extract；active衍生字段见interaction_features.py的extract；固定84列预处理见preprocessing.py的FeaturePreprocessorV3。所有原文件保持不变。

复现协议命令（仅在四个新输出不存在时运行）：`$env:PYTHONPATH='src'; python -m scenario_agent.policy_cv_protocol_v1`。已有输出会拒绝覆盖。确定性验证：`python -m pytest tests/test_scenario_policy_cv_v1.py`，不执行模型或优化器。
