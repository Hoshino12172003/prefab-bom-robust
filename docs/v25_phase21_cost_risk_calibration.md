# V2.5 Phase 2.1 成本与风险校准

Phase 2.1 使用 Phase 2.0 的 RSP-C 专用保护覆盖、原始 3,003 个 BEV VIN 和 14 期窗口。以下参数只服务于 `STRUCTURAL_DIAGNOSTIC_ONLY`。Phase 1.10 的模型适配与 Phase 2.0 的冻结规格继续作为上游依据。 [Phase 2.0 规格](v25_phase20_prospective_instance_spec.md)

## 归一化成本

`c_C=1` 表示一套平衡组件 kit 的 cell-content value。用 Argonne BatPaC 5.0 技术更新第 5 页同一 EV 示例的 Pack 和 cell 结果复算，两项约为 108 和 76 美元/kWh。两者相除得到 `r_PC=27/19≈1.42105`。分子分母在同一能量口径下，模型无需指定源案例车辆的 Pack kWh。BatPaC cell 层成本用于代理 kit-equivalent 价值，不能直接理解为三种源组件的单价或纯原材料成本。模型输入 `27/19` 保留公开舍入数字的精确商，经济意义仍为约 1.42。证据级别为 `EXTERNAL_MODEL_CALIBRATION`。 [NHTSA 收录的 BatPaC 5.0 更新](https://static.nhtsa.gov/nhtsa/downloads/CAFE/2023-NPRM-LD-2b3-2027-2035/Argonne-Databases/Documentation/BatPaC%205_2022_Summary%20of%20Updates%20%26%20Changes.pdf)

NHTSA 收录的 BatPaC 4.0 Figure 5 中，七个 NMC622-G EV 模型设计的 Pack/cell 比最小为 1.30，最大为 1.57。采用 `[1.30,1.57]` 作为模型支持的结构诊断区间。Argonne 5.0 手册 §3.3 另用同一模型的额定能量将 Pack 成本换算为每 kWh，两项复核的比约为 1.440 和 1.394。该范围来自外部工程模型设计，不能解读为 Volkswagen 实测范围、企业统计分布或置信区间。 [BatPaC 4.0 Figure 5](https://www.nhtsa.gov/file-downloads/download?p=nhtsa%2Fdownloads%2FCAFE%2F2021-NPRM-LD-2024-2026%2FArgonne+Databases%2FDocumentations%2FSummary+of+Updates+and+Changes+in+BatPaC+4+%28Oct+2020%29.pdf) · [Argonne BatPaC 5.0 手册](https://publications.anl.gov/anlpubs/2022/07/176234.pdf) · [逐项成本证据](../artifacts/v25_phase21_20261110_212532/battery_cost_ratio_evidence.csv)

## OEM 定位成本

用 `c_O=r_PC(1+δ_O)`，`δ_O≥0`。增量项可包含预先运输、处理、下游占位和持有。APQC 给出持有成本构成，ASCM 字典给出跨行业年持有成本占库存价值 10%–35% 的参考口径，CSCMP 及 FHWA 提供总体物流账户边界。检索未识别到匹配本源案例、运输路径和时窗的电池定位净增量。行业年持有率只作为 `PLAUSIBILITY_REFERENCE`，不能推导 `δ_O` 的点值或企业区间。将 `δ_O` 作为模型的 break-even threshold 参数，由预算和可履约整数政策推出临界值。管理位置成本保持待定。 [APQC](https://www.apqc.org/resources/benchmarking/open-standards-benchmarking/measures/inventory-carrying-cost-1000-revenue) · [ASCM 词典](https://learn.ascm.org/sfc/servlet.shepherd/document/download/069R3000006PlDHIA0?operationContext=S1) · [CSCMP 物流报告](https://cscmp.org/common/Uploaded%20files/2024%20State%20of%20Logistics%20Report%20-%20Executive%20summary.pdf) · [FHWA 成本口径](https://ops.fhwa.dot.gov/Freight/freight_analysis/econ_methods/lcdp_rep/index.htm) · [定位成本证据](../artifacts/v25_phase21_20261110_212532/position_cost_evidence.csv)

## 风险证据与诊断

源 XLSB 直接提供窗口和每日 294 Pack 的生产、运输能力。原案例的组件质量缺陷与 GM 公开召回提供 L1 机制依据，GM 复产通报支持供应生产可能中断，UNCTAD 的苏伊士航道监测说明运输通行量可能大幅下降。这些外部案例的部件、节点和路径与本文不同，未将其幅度或时长转移到本案例。 [源 XLSB](https://data.mendeley.com/datasets/pr3sdy5vp3/1) · [源论文](https://doi.org/10.1016/j.ejor.2020.08.005) · [NHTSA 召回](https://static.nhtsa.gov/odi/rcl/2020/RCLRPT-20V701-7125.PDF) · [GM 复产通报](https://static.nhtsa.gov/odi/rcl/2021/RCMN-21V650-0383.pdf) · [UNCTAD 航道证据](https://unctad.org/system/files/official-document/osginf2024d2_en.pdf)

| 诊断 | 作用位置 | 采用的数值和证据等级 |
|---|---|---|
| NOM | 无扰动对照 | 三层因子均为 1 |
| L1 | 风险揭示后 T1 预置组件的质量或可用性放行 | 全 14 期累计比例为 1/2，按整套配方放行 `floor(x_C/2)`。50% 与 14 期持续时间均为 `EXPERIMENTAL_STRESS_TEST` |
| L2 | Pack 生产共享容量 | 全 14 期 RHS 为 294×1/4，整数流实际至多 73/期。75% 与 14 期均为 `EXPERIMENTAL_STRESS_TEST` |
| L3 | T1→OEM Pack 运输共享容量 | 同一压力系数与窗口，施加于运输弧。75% 与 14 期均为 `EXPERIMENTAL_STRESS_TEST` |

L1 是 RSP-C 的 `MODEL_ADAPTATION`，针对已经定位的组件批次。保留 Phase 2.0 的整套配比取整，阶段二在第 1 期放行一部分且窗内不恢复。源上游 20 期提前期使窗内新发运无法在 14 期内到达，因此不把 L1 写成窗内发运能力冲击。三项压力参数特意覆盖整个物理窗口，以检查位置差异。最终情景的强度、持续期、恢复与风险频率仍没有校准，本轮未使用任何 `INTERPOLATED_SCENARIO`。 [风险证据表](../artifacts/v25_phase21_20261110_212532/risk_parameter_evidence.csv)

## 诊断保护尺度

源窗口平均需求 `3003/14=214.5`。按平均日需求向上取整，1、3、5 日保护尺度分别为 215、644、1,073，标记 `EXACT_DERIVED_FROM_SOURCE_DEMAND`。物理比较用 `x_C+x_T+x_O≤K`。经济诊断用 `B=r_PC K`，在给定比值和 K 下跨风险固定预算。比较比值端点时固定 T1 Pack 的采购当量 K，归一化金额随比值变化。由此得到的政策与定位阈值属于诊断设计。 [政策预审](v25_phase21_endogenous_buffer_pre_audit.md)
