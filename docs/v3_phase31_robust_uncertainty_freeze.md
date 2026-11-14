# V3 Phase 3.1 两阶段规格与校准门

**HOLD_UNCERTAINTY_CALIBRATION**

两阶段数学规格、组合候选集、全网接口和历史压力诊断已交付。正式前瞻开盘库存、分日正常到货以及相关计划承诺仍缺乏独立证据，无法冻结正式风险参数。公开数据目录及 Phase 3.0 复现均指向历史案例。历史 t60 已含短缺，当前证据不能识别正常反事实或 860 的物理恢复量。 [两阶段规格](v3_two_stage_robust_model.md) · [公开数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1)

## 参数证据

审计覆盖权威来源、参数映射及可迁移性。Bertsimas–Sim 支持预算化不确定性的设计思路，当前 \(\Gamma\) 的定义另由连续事件模型给出。Ackermann 等人的 2024 年研究支持多产品、分期供应风险的建模。丰田 2024 年披露发动机解除出货限制与复工为不同日期。2026 年披露的巴西事件中，整车工厂约两个月后恢复，发动机异地生产约四个月后恢复。UNCTAD 2024 年的 42% 指苏伊士船舶通行量下降，不能用于该 T1→OEM 弧标定。上述证据支持事件持续与恢复机制，缺少本网络分母与联合暴露。 [预算不确定性](https://doi.org/10.1287/opre.1030.0065) · [分期供应](https://doi.org/10.1007/s43069-024-00333-9) · [丰田 2024](https://global.toyota/en/newsroom/corporate/40490625.html) · [丰田 2026](https://global.toyota/pages/global_toyota/ir/financial-results/2026_3q_presentation_2_en.pdf) · [UNCTAD 2024](https://unctad.org/news/red-sea-crisis-and-implications-for-trade-facilitation-africa)

历史诊断沿用 BatPaC 候选成本比 \(27/19\)，组件单位成本 1，OEM 位置溢价固定为 10% 敏感性点。三档预算为 215、644、1,073 个 T1 Pack 的归一化费用。候选 \(\Gamma=6\) 允许两个三日事件或一个五日和一个一日事件，敏感性为 0、3、9。严重度、时长与并发限制均属实验设计。 [风险资源](../artifacts/v3_phase31_20261111_193210/risk_resource_catalog.csv) · [参数血缘与证据等级](../artifacts/v3_phase31_20261111_193210/uncertainty_parameter_provenance.csv)

## 候选规模

| 活跃资源日上限 | 状态模式 | 含严重度轨迹 | 突变恢复下历史有效 RHS |
|---:|---:|---:|---:|
| 0 | 1 | 1 | 1 |
| 3 | 3,397 | 79,237 | 12,961 |
| 6 | 12,655 | 287,443 | 38,527 |
| 9 | 35,611 | 894,295 | 74,788 |

基准并发为 2。合法区间只发生一次，正严重度和单调恢复可由剩余比例轨迹识别。右端项经每 SKU 收货量及整数弧能力重算后再去重。Γ=6 的渐进恢复产生 68,521 个历史有效 RHS。仅第 66、73 期有历史 L1 到货。Γ=6 有 8,220 个无法通过单资源支持扩大而继续满足候选约束的模式。这是结构极大模式计数，精确最坏服务包络规模仍待识别。 [规模审计](../artifacts/v3_phase31_20261111_193210/uncertainty_set_size_audit.csv) · [历史暴露](../artifacts/v3_phase31_20261111_193210/source_L1_exposure.csv)

## 全网历史诊断

60 项开放及禁用全网优化、20 项固定政策比较、1 项三情景 Direct DE 均达到 OPTIMAL，整数矩阵复核残差为 0。三情景展开有 227,434 个整数变量，服务最优 26,889，等于独立的单情景上界。

| 预算 Pack 当量 | 条件 NR | L1 新增压力 | L2 新增压力 | L3 新增压力 | L1+L3 |
|---:|---:|---:|---:|---:|---:|
| 215 | 26,753 | 26,279 | 26,753 | 26,753 | 26,279 |
| 644 | 27,363 | 26,889 | 27,363 | 27,363 | 26,889 |
| 1,073 | 27,917 | 27,498 | 27,917 | 27,887 | 27,498 |

禁用 \(x_C\)、\(x_T\)、\(x_O\) 分别在 15/15、3/15、1/15 个历史条件下减少准时交付，最大下降 451、12、49 辆。这些正效应支持继续保留三位置。正式前瞻 NR 和正式禁用值尚缺输入。 [预算、损失与禁用明细](../artifacts/v3_phase31_20261111_193210/full_model_buffer_ablation.csv) · [三情景证书](../artifacts/v3_phase31_20261111_193210/selected_scenario_de_validation.csv)

## 算法准入

完整模型类存在整数 BOM 齐套耦合，历史特例在所审纯准时出库目标下仍可精确化简。非电池 JIT 见证与独立整数前缀证书匹配全部 81 次全网 Direct 结果。该发现与 Phase 3.0 原五权重目标的换单反例相容。前瞻数据能否保持可化简条件仍待核查。 [上游定义](../artifacts/v3_phase31_20261111_193210/upstream_buffer_flexibility_audit.md) · [完整可约性证明](../artifacts/v3_phase31_20261111_193210/full_model_reducibility_audit_phase31.md) · [C&CG 预审](../artifacts/v3_phase31_20261111_193210/ccg_structural_justification.md)

已停在 Phase 3.1。 [机器审计](../artifacts/v3_phase31_20261111_193210/audit.json) · [SHA-256](../artifacts/v3_phase31_20261111_193210/sha256_manifest.csv)
