# V2.5 Phase 1.8 网络参数依据

> **INTERPRETATION_CORRECTION（Phase 1.10）**。55 期仅是原研究数据生成仿真的 settling time。下文的 56 期及循环容量日历属于历史诊断协议，不能用来证明 V2.5 暖机收敛、周期稳态或正式时域充分。 [现行规格](v25_model_spec_v2_source_semantics_corrected.md)

本阶段的 **Source-Calibrated Nominal Baseline** 是实验初始状态。结构和流量上限来自公开案例，初始状态由本项目的无新增扰动暖机生成。原论文 §4.7 将公开数据描述为基于系统导出及案例研究的仿真变体。 [原论文全文](https://www.researchgate.net/publication/343539617_Optimisation_model_for_multi-item_multi-echelon_supply_chains_with_nested_multi-level_products) · [Mendeley 数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1)

## 1. Network topology

原 XLSB `nodes` 为 12 节点、`arcs` 为 11 弧。行级出处、原始值和用法在 [参数溯源 CSV](../artifacts/v25_phase18_20261110_181931/network_parameter_provenance.csv) 中。所有弧的容量日历均为 `capacity_at_arc` 中第 61–74 期，暖机和正式期只重编号。下列拓扑、原始产品组和提前期均为 `DIRECT_DATA`，可作为公开案例参数发表，未对其做敏感性变更。 [拓扑清单](../artifacts/v25_phase18_20261110_181931/network_topology.csv)

| 起点 | 终点 | 产品组 | 提前期（日） |
|---|---|---|---:|
| `zp7` | `zp8` | `car` | 0 |
| `gear-supplier_inv` | `zp7` | `gear` | 2 |
| `engine-supplier_inv` | `zp7` | `engine` | 1 |
| `gear-supplier_prod` | `gear-supplier_inv` | `gear` | 2 |
| `engine-supplier_prod` | `engine-supplier_inv` | `engine` | 1 |
| `battery-supplier_inv` | `zp7` | `battery` | 1 |
| `seat-supplier_inv` | `zp7` | `seat` | 0 |
| `battery-supplier_prod` | `battery-supplier_inv` | `battery` | 1 |
| `seat-supplier_prod` | `seat-supplier_inv` | `seat` | 0 |
| `seat-supplier_trans` | `seat-supplier_prod` | `seat_componment` | 23 |
| `battery-supplier_trans` | `battery-supplier_prod` | `battery_componment` | 20 |

## 2. BOM

BEV Pack 的原始三项用量为 `10 / 6 / 4` 件每包，来源为 `BOM` 第 87051–87053 行，等级 `DIRECT_DATA`。`20 = 10+6+4` 件每包属于 `EXACT_DERIVED`，与 `operations` 第 14 行和论文 §4.4 交叉一致。其余配方由同一 `compile_network` 读入，逐 VIN 等价聚合时保留 BOM。可按上述证据级别刊载。

## 3. Lead times

电池路径原始提前期为上游电芯运输 20 日，包生产到 T1 1 日，T1 到 OEM 1 日。路径对应 `arcs` 第 12、9、7 行，原论文表 7 一致。等级 `DIRECT_DATA`，直接刊载原案例值。终态在途的剩余时间采用 `d + lead − 56`，等级 `EXACT_DERIVED`。

## 4. Capacities

物理容量以 `capacity_at_arc` 原行的数量为准。电池包生产、运输在 61–74 期均为 294 包/期，电芯上游在原第 67、74 期为 2,058 组件流量单位/期，其余为 0，整车装配每期 2,000 辆，等级 `DIRECT_DATA`。原论文 §4.4、表 7 给出示例容量 490、70、70、2,000，等级 `DIRECT_PAPER`。可分列两种口径。两条比率 `70/294 = 490/2058 = 5/21` 属于 `EXACT_DERIVED`，仅说明双方同时缩放容量不等式时的等价性。本阶段采用相对时点 1–56 或 1–14，直接使用物理容量、SKU 和组流量上限，不采用 5/21 缩放物理量。容量和流量上限日历统一为 `61+(t−1) mod 14`，该外推日历属 `EXPERIMENTAL_PROTOCOL`。

## 5. Demand

原 `demands` 逐 VIN 提供节点、数量和到期日，等级 `DIRECT_DATA`。共 28,000 VIN、3,003 BEV、1,286 个严格等价组，等级 `EXACT_DERIVED`。群组键为交付节点、到期日、单位权重和原始 BOM。正式 14 期对所有偏移都使用原始自然顺序。订单身份在复制周期和正式批次各自命名，原始配置、数量和相对到期日不作变换。

## 6. Warm-up length

原论文 §4.7 在考虑暂态与安全系数后报告 55 期 settling time，等级 `DIRECT_PAPER`。本研究选 56 期，因它是严格大于 55 的最小完整 14 期倍数，等级 `EXPERIMENTAL_PROTOCOL`。可按此区分来源和设计。未改变暖机长度做敏感性分析。

## 7. Demand cycling rule

对暖机期 `t` 和偏移 `s`，原需求日为 `61+(t−1+s) mod 14`，在 56 期内完整重放四遍。每个日内的全部 VIN 同步移动，品类比例不变。此循环及唯一订单前缀属 `EXPERIMENTAL_PROTOCOL`，14 偏移构成循环起点敏感性。保留 Phase 1.6 的整段订单上限和服务目标。到期日前的交付计入目标，迟交可以发生但没有按期目标贡献。未完成订单不会在每个 14 期边界被重置、复制为 backlog 或强制交付。暖机结束后将其作为暖机历史登记，正式期启用独立新订单。 [需求逐期映射](../artifacts/v25_phase18_20261110_181931/warmup_demand_mapping.csv)

## 8. Initialization seed

第 60 期公开库存与截至该期已发、尚未到货的历史流用作初始化种子。原数量属于 `DIRECT_DATA`，到货时点由发运加提前期推得，等级 `EXACT_DERIVED`，采用原快照作种子属于 `EXPERIMENTAL_PROTOCOL`。原库存、在途与安全库存边界都由既有编译器读入。未对种子做敏感性分析。

## 9. No-disruption definition

到货、生产、运输乘子各为 1，B0 新增保护缓冲为零。等级 `EXPERIMENTAL_PROTOCOL`。暖机期间新发运全部受源弧容量、BOM 和时序约束。模型外生流入只在原 `nodes_inflow` 允许的位置使用，没有新增注入位置或历史事故补丁。

## 10. Baseline extraction

暖机末日 `I[n,item,56]` 原值转为正式 `t=0`，仍在途的 `q` 按剩余时间登记。超过 14 日到达的流保留在状态文件，正式 14 期只接收会在窗内到达的记录。未完成暖机订单登记但不转为新需求，旧订单专属完工存货保留实体数量且保持原身份。此交接方式为 `EXPERIMENTAL_PROTOCOL`，其中时间平移属于 `EXACT_DERIVED`。源变量标识与回放证据允许复现。

## 11. Phase-offset robustness

暖机偏移 0–13 均使用相同的原材料、容量日历、B0 与模型。NB00 由 `s=0` 预先指定，其余均用于稳健性。各 offset 接续的正式订单自然序列一致。描述性分类在初始求解阶段单独冻结。服务率极差达到 1 个百分点，或均值非零的电池位置指标 CV 达到 10%，标记为有偏移敏感性。阈值、选择规则与总体标准差口径均属于 `EXPERIMENTAL_PROTOCOL`。 [偏移分类规则](../artifacts/v25_phase18_20261110_181931/stability_classification_policy.json)

## 12. Remaining assumptions

56 期满足协议长度，有限期按期服务目标对某些末端库存与窗外发运存在多解。固定求解环境和证书停止规则可复现所选解，证书不主张末端状态唯一或达到周期稳态。偏移差异可以同时反映到期日相位和最优终态多解。种子、周期长度、容量日历和末端规则的其他设定均没有做敏感性分析。与历史短缺嵌入状态的差异用于描述不同起点的模型结果。
