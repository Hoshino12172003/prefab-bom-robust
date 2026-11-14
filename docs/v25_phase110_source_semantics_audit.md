# V2.5 Phase 1.10 来源参数语义、适用范围与规格审计

**`PASS_WITH_EXPLICIT_MODEL_ADAPTATIONS`**

本轮重新核对出版版论文、哈希锁定的原 XLSB 及 Phase 1.6 证据。现行模型直接使用 XLSB 容量，源数据和六个冻结回归配置保留原值。计划流上限、缺省库存、同品项移库表示和按期服务目标的来源边界已写入冻结规格。 [现行冻结规格](v25_model_spec_v2_source_semantics_corrected.md) · [原论文全文](https://www.researchgate.net/publication/343539617_Optimisation_model_for_multi-item_multi-echelon_supply_chains_with_nested_multi-level_products) · [作者数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1)

## 已确认的来源事实

- 12 节点、11 弧及 154 行 `capacity_at_arc` 覆盖原第 61–74 期。原论文式（2）限制弧上全部允许品项的发运总和。电芯上游弧第 67、74 期共享上限各为 2,058，余期为 0。约束单位为该弧每期模型流量容量单位。完整套数由 BOM 和各 SKU 可用量导出，不能反用作原始容量单位。表 7 的 490／70／70／2,000 是示例，仅用于交叉核对。 [容量语义逐行表](../artifacts/v25_phase110_20261110_201422/capacity_semantics_audit.csv)
- `BOM` 有 49 条 `m=c` 的单位行。历史代码读取它们并在 86 个弧–品项上将其用于同品项发运扣账，到货增加同一品项。没有一条形成包生产或整车制造的自耗。现行编译器显式排除这 49 条制造 BOM 输入，从原 `operations` 的同组 1∶1 操作生成同一移库系数。去掉全部 49 条后的整网编译结果一致。BEV 包的 `beta=1` 使用 `10+6+4=20`，generic 20 不再参与这条运算的加总。 [BOM 语义逐行表](../artifacts/v25_phase110_20261110_201422/bom_semantics_audit.csv)
- 开盘库存原表有 82 条，适用于第 60 期。117 条历史流水发运在第 39、46、53、59、60 期，由弧提前期推得 106 条到达第 61–74 期，最晚到第 83 期。L1 认证场景只在第 66 期将三项可用到货 `9470/5682/3788` 变为 `4735/2841/1894`，发运记录仍是原值。20 日上游、1 日包生产与 1 日 T1→OEM 时点逐弧匹配。零提前期允许同一期净结转。 [期初状态](../artifacts/v25_phase110_20261110_201422/initial_state_semantics_audit.csv) · [提前期](../artifacts/v25_phase110_20261110_201422/lead_time_audit.csv)
- 28,000 VIN、3,003 BEV 和 1,286 组通过回读。每组的交付节点、BOM、到期日、单位权重一致。没有 VIN 专属的初始量、计划流、来源资格、非零运输尺度或成本／优先级系数。所有风险由其共享的上游约束传导。 [每日需求](../artifacts/v25_phase110_20261110_201422/demand_calendar.csv) · [逐组等价审计](../artifacts/v25_phase110_20261110_201422/aggregation_semantics_audit.csv)

## 被撤销的解释

- `DEPRECATED_ALGEBRAIC_NORMALIZATION` 撤销历史 5/21 行写法在正式模型中的使用。旧写法对 LHS 和 RHS 同乘正因子，并未把原 XLSB 变成采用表 7 示例物理容量的网络。表 7 只作 `SOURCE_PAPER_CROSSCHECK`。两处来源数值比例的形成过程没有验证依据。
- Phase 1.9 的现行状态为 `HOLD_LONG_RUN_EXTRAPOLATION_UNSUPPORTED`。61–74 期容量和需求只直接支持原短期窗口。205 辆 BEV 和 25,202 辆总交付仅是**在假设这两个日历联合无限重复的实验系统中**得到的条件上界，不能据此判断来源企业网络的长期供给能力。计算、日志范围和原历史标签按字节保存，现行解释写入单独的更正记录。 [Phase 1.9 状态重标](../artifacts/v25_phase110_20261110_201422/phase19_disposition.json) · [时间适用范围](../artifacts/v25_phase110_20261110_201422/time_scope_audit.csv)
- 原论文 55 期指数据生成仿真的 settling time。Phase 1.8 的两份报告均已添加 `INTERPRETATION_CORRECTION`。56 期是本项目的有限暖机诊断协议，不能证明优化收敛、稳态或时域充分。NB00 保留为诊断，正式名义基线仍未建立。

## 明确保留的模型适配与未识别项

原论文 §4.6 式（17）明确示范以等式固定供应商计划生产。XLSB 两个 `max_flow_*` 表分别含 365 条产品和 20 条产品组记录，覆盖发动机与齿轮生产弧第 61–70 期。V2.5 将记录作为附加上限，这是已公开的 `MODEL_ADAPTATION`。按约束形式，固定承诺替换为计划上限。由于 D60 第 65 期的论文等式为 40，XLSB 行 163 为 22，不能宣称两份材料提供完全相同的承诺量，也不能据此推断原作者程序中全部记录的执行方式。缺行不会产生额外上限。 [计划流审计](../artifacts/v25_phase110_20261110_201422/planned_flow_semantics_audit.csv)

初始表的缺行零值在公开说明和论文式（3）中没有得到明确确认。现有 1,339 个缺行库存键继续按冻结加载器补零，全部标记 `MISSING_NOT_ZERO_CERTIFIED`，包括 T1 的 BEV。该规则只用于保持认证实例的可复现性。现有外部流入资格以及将明示的库存上下界施加于操作期，也在规格中明示其模型处理。

按期交付最大化属于本文目标。原论文的订单缺口、重排偏差、未用产能、库存及流量权重属于不同的模型目标背景。`x_cell_kit` 定义为 **balanced battery-cell-component buffer / kit-equivalent component buffer**。它每单位固定增加 `(10,6,4)`，无法进行独立 SKU 配比选择。

同价 T1/OEM Pack 成本 8,756 USD 和零 OEM positioning premium 为 `CERTIFICATION_ONLY`。管理实验仍受 `HOLD_FINAL_POSITION_COST_CALIBRATION` 阻断。860 的单位和第 59 期状态保持未识别。正式 clean 基线状态为 `SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED`。

## 原容量回归认证

Gurobi 13.0.1 在 `OptimalityTol=1e-9`、零间隙条件下重新求解全部六个实例，无起点注入。逐行对照 Phase 1.6 的历史 MPS，只有 504 条预期的电池容量行同比例差异。变量名、域、目标、其余约束及 RHS 均完全相同。最终源代码重建的矩阵与本轮导出 MPS 逐项一致。

| 冻结实例 | Gurobi 容差内按期量 | 严格预算最优量 | 运行秒数 |
|---|---:|---:|---:|
| nominal B0 | 26,448 | **26,448** | 0.787 |
| nominal B20 | 26,472 | **26,472** | 0.795 |
| nominal B50 | 26,509 | **26,508** | 0.606 |
| nominal B100 | 26,570 | **26,569** | 0.480 |
| DE B0 | 25,974 | **25,974** | 5.666 |
| DE B50 | 26,035 | **26,034** | 9.477 |

严格证书以旧可行向量独立代入本次原容量矩阵，复核全部约束、变量界、整数性、严格预算和目标，逐项残差为零。该下界与独立物料及严格预算上界闭合。三个边界实例的数值结果各多一辆，来自 Phase 1.6 已识别的预算小数容差差异。六个严格最优值保持一致。73 项 V2.5 相关回归通过，含 7 项本轮新增。 [回归 CSV](../artifacts/v25_phase110_20261110_201422/phase16_regression_after_semantic_cleanup.csv) · [容量行等价](../artifacts/v25_phase110_20261110_201422/capacity_row_equivalence.csv) · [最终代码与模型矩阵一致性](../artifacts/v25_phase110_20261110_201422/final_source_matrix_identity.csv) · [pytest 日志](../artifacts/v25_phase110_20261110_201422/pytest_regression.txt)

## 历史结果适用性

| 历史证据 | 当前用途 |
|---|---|
| Phase 1.6 六个严格证书 | 原 14 期冻结 V2.5 短窗模型认证，已用原容量重证 |
| 原 Phase 1 求解器上界 | 历史档案，受 Phase 1.6 已识别的错误低界约束 |
| Phase 1.5 比较和 B100 | 历史机制及可行解诊断，适用于当时配置 |
| Phase 1.7 | 保留 `HOLD_SHORTAGE_UNIT_UNIDENTIFIED` |
| Phase 1.8 | 有限暖机诊断，无正式 baseline 地位 |
| Phase 1.9 | 联合无限循环假设下的条件性容量诊断，现行 `HOLD_LONG_RUN_EXTRAPOLATION_UNSUPPORTED` |

原注释前的文档和变更前的代码已按历史哈希留存。Git 基线为 `02143f46cab6e6a173a0f495e21b20d21311096f`。本阶段优化只用于六个冻结回归实例，完成后停止。 [机器可读审计](../artifacts/v25_phase110_20261110_201422/audit.json) · [SHA-256 清单](../artifacts/v25_phase110_20261110_201422/sha256_manifest.json)
