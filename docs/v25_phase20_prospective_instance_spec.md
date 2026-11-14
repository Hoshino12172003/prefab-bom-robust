# V2.5 Phase 2.0 前瞻性实验实例规格

状态 `PASS_PROSPECTIVE_INSTANCE_SPEC_FROZEN`。实例是 **source-calibrated prospective planning instance**。研究问题是有限专用保护资源如何在源汽车网络上覆盖原始 BEV 订单。实验不估计真实事故前库存、恢复量或历史经营绩效。Phase 1.6、1.7、1.10 的证据和状态沿用。

## 需求、时间和物理参数

| 字段 | 冻结内容 |
|---|---|
| 主需求 | 原始 3,003 个 VIN，每个一辆，源需求节点和到期日保留 |
| 配置 | BEV/D83/G1Z/Q4H 有 2,436 辆，BEV/D83/G1Z/Q2J 有 567 辆，每项配置部件各一件 |
| 实验时间 | 风险在实验时刻 `τ=0` 揭示，源周期 `s=61,…,74` 映射为 `t=s−60` |
| 相对日需求 | 52、293、159、709、76、64、384、59、275、182、68、274、357、51 |
| 电池 SKU 与生产配方 | BEV，每个 Pack 用三种原始电池组件各 10、6、4 单位 |
| 电池三弧提前期 | 上游到 T1 生产为 20，T1 生产到 T1 库存为 1，T1 库存到 OEM 为 1 |
| 共享产能 | 上游第 7、14 日各 2,058 个组件输出单位，其余日为 0。Pack 生产与运输分别各 294 个 Pack 输出单位/日。OEM 装配为 2,000 辆/日 |
| 主绩效指标 | **BEV on-time fulfillment rate**，原始 VIN 中按期在 OEM 完成履约的车辆数除以 3,003 |
| 全网次指标 | 只有显式纳入全部 28,000 辆并求得车辆服务结果时，才计算全网服务率。本轮无此结果 |

保持 XLSB 的 BOM、原始弧、提前期、原始每日共享容量、源资格关系和库存边界。产能按原始弧输出单位实施。上游 2,058 是三种电池组件输出的**共享**上限，不能给各 SKU 各配一份，也不能解释为 2,058 个 Pack。源组件名称含原始拼写 `componment_battery1/2/3`。允许按需求节点、BOM、到期日和权重聚合完全相同的订单，但必须能无重复地展开至原始 VIN。证据列出每个 VIN 与每条弧的源周期和实验周期。 [源 XLSB](https://data.mendeley.com/datasets/pr3sdy5vp3/1) · [逐 VIN 数据](../artifacts/v25_phase20_20261110_203851/bev_orders.csv) · [机器规格](../artifacts/v25_phase20_20261110_203851/prospective_manifest.json)

## 主范围与非电池控制

采用 **RSP-C protective coverage experiment**，标记 `MODEL_ADAPTATION`。电池主研究对象保留所有 BEV 所需的发动机、变速箱、座椅及 OEM 装配约束。非电池背景的初始库存、在途、产能、合格外部流和产品/组计划流上限来自源案例，按 Phase 1.10 语义实施。它是条件性实验背景，不参与电池保护预算。源电池历史库存与历史发运不进入任何电池可用余额。 [正常供给协议审计](v25_phase20_regular_supply_protocol_audit.md) · [Phase 1.10 语义](v25_model_spec_v2_source_semantics_corrected.md)

Gurobi 13.0.1 的两项 `STRUCTURAL_DIAGNOSTIC_ONLY` MILP 均返回 `OPTIMAL`。诊断固定每一到期日的非电池 BOM 提取，并显式保留全支路库存平衡、合格补货、提前期、共享弧容量、计划流上限和 OEM 当日装配能力检查。每个实例 3,556 个整数变量、2,261 条模型约束，独立整数流账与求解器残差均为 0。

| 范围 | D83 | G1Z | Q2J | Q4H | 求解器时间（秒） |
|---|---:|---:|---:|---:|---:|
| 3,003 辆 BEV | 3,003 | 3,003 | 567 | 2,436 | 0.009 |
| 全部 28,000 辆 | 3,003 | 3,003 | 9,726 | 12,038 | 0.017 |

在给定源非电池背景下，两种范围均存在按原到期日配齐的非电池流。部分产品和日期的 OEM 期末库存等于零，这个见证不证明非电池约束在所有解中严格松弛，也不衡量电池或整车服务。主范围保留七条非电池供给、生产或运输弧和 OEM 装配。只保留三条电池弧的投影会删除非电池 BOM 提取与其产能、提前期和共享约束，只能称为 **battery-feasible BEV order fulfillment**。该投影不作为本规格的主实例。 [逐部件结构审计](../artifacts/v25_phase20_20261110_203851/non_battery_binding_audit.csv) · [两次诊断记录](../artifacts/v25_phase20_20261110_203851/non_battery_diagnostic.json)

## 阶段与履约口径

第一阶段在风险揭示前选择共同的整数 `x_C,x_T,x_O ≥ 0`，并承担一次专用保护预算。第二阶段按情景实施库存释放、非电池运营流、Pack 生产和运输、OEM 装配及 VIN 履约。提前期按发运至收货计时。现期发运耗用起点库存，只有在相对期 `t+lead` 才成为终点收货。OEM 装配消耗该 VIN 的完整 BOM，同期共享装配能力。情景运营必须用一套同时可行的流和库存；每个 VIN 最多履约一次，且仅在原到期日或之前完成时计入主指标。预注册未来稳健绩效以最坏情景的按期 BEV 整数计数为准，比例只作同一分母的呈现。 [变量及流账规格](v25_phase20_endogenous_buffer_definition.md)

RQ1 衡量给定预算下保护覆盖的上界、配置及边际变化。RQ2 比较风险位置和暴露路径变化时的可行政策集合。RQ3 检查该结构对成本比、提前期、近优损失和跨实例设计的稳定性。这些问题适用于保护覆盖机制，不能用来估计相对历史正常系统的增益。

## 复核与停止点

正式模型、成本校准、风险严重度/持续期/恢复曲线、正式预算以及政策实验均留待后续授权。历史 clean baseline 状态为 `SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED`。管理实验继续为 `HOLD_FINAL_POSITION_COST_CALIBRATION`。本轮执行两次结构性非电池诊断。主实例和算法求解调用均为 0。实际命令与证据见 [执行审计](../artifacts/v25_phase20_20261110_203851/audit.json) 和 [SHA-256 清单](../artifacts/v25_phase20_20261110_203851/sha256_manifest.csv)。

在仓库根目录可独立重验已保存的见证，不需要 Gurobi 或 XLSB。Python 3.12.7 与 pytest 9.1.1 下实测 9 项通过。结构诊断脚本另需 `gurobipy`、`pyxlsb` 和哈希匹配的源 ZIP，运行会写入诊断证据，复跑宜在独立副本中进行。

```powershell
python -m pytest -p no:cacheprovider -vv tests/test_v25_phase20_prospective_spec.py
```
