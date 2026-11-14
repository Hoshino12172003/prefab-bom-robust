# V2.5 Phase 1.7 参数依据与论文表述边界

> **DEPRECATED_ALGEBRAIC_NORMALIZATION（Phase 1.10）**。下表 5/21 仅用于解释旧容量行。现行求解使用原 XLSB 容量，论文示例仅作对照。 [现行规格](v25_model_spec_v2_source_semantics_corrected.md)

阅读目标为复现，输入为完整出版版论文和作者数据。核查重点为方程、源字段和复现缺口。该案例的对象是含三类电芯 SKU 的多层级汽车供应网络，条件是第 59 期质量事件，观测边界是第 60 期库存与在途快照。公开证据可复现原始短缺后的输入，事故撤销所需的物料向量和状态分配仍缺少来源。 [出版版 DOI](https://doi.org/10.1016/j.ejor.2020.08.005) · [作者数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1)

## 论文可用参数依据表

| 参数及值 | 单位 | 原始定位或公式 | 证据等级 | 论文正文使用 | 敏感性 |
|---|---|---|---|---|---|
| 短缺期 59 | 日索引 | p.151 表 3 | `DIRECT_PAPER` | 可写案例时点 | 否 |
| 短缺量 860 | 原文单位未注明 | p.151 表 3 `s` | `DIRECT_PAPER` | 可原样引用，注明单位未注明 | 若作为物理量则先识别单位 |
| 短缺单位 | 未识别 | §3、§4.6–4.7、XLSB，无 `s` 到物理流的映射 | `SUPPORTED_INFERENCE` | 可披露识别缺口 | 候选均未准入 |
| 质量原因与受影响组 `battery_component` | 类别 | p.151 §4.2、表 3；XLSB 组拼作 `battery_componment` | `DIRECT_PAPER` | 可写案例事实 | 否 |
| 首受影响节点，包厂生产端 | 节点 | p.151 表 3 `battery-supplier_prodt`；网络对应 `battery-supplier_prod` | `DIRECT_PAPER` | 可写案例事实 | 否 |
| BEV 包电芯配方 10/6/4 | 各 SKU 件/包 | `BOM` 行 87051–87053 | `DIRECT_DATA` | 可写公开案例 BOM | 否 |
| 总电芯用量 20 | 件/包 | `10+6+4`；`operations` 行 14 及 §4.4 交叉核对 | `EXACT_DERIVED` | 可写推导 | 否 |
| 电芯上游运输 20 | 日 | `arcs` 行 12；表 7 | `DIRECT_DATA` | 可写案例模型参数 | 否 |
| 包生产 1 | 日 | `arcs` 行 9；表 7 | `DIRECT_DATA` | 可写案例模型参数 | 否 |
| T1→OEM 运输 1 | 日 | `arcs` 行 7；表 7 | `DIRECT_DATA` | 可写案例模型参数 | 否 |
| 包生产和 T1→OEM 容量 294、294 | 包/日 | `capacity_at_arc` 行 100–113、30–43，`t=61…74` | `DIRECT_DATA` | 可写公开案例期内容量 | 不外推 `t=59` |
| 论文示例包生产和 T1→OEM 容量 70、70 | 电池项/期 | p.153 表 7，题注 `p=6` | `DIRECT_PAPER` | 可写示例容量 | 外推须另列假设 |
| 论文示例上游容量 490；XLSB 正产能 2058 | 相应容量单位/期 | §4.4 和表 7；XLSB `t=67,74` | `DIRECT_PAPER`／`DIRECT_DATA` | 可分列两种口径 | 否 |
| 第 60 期包厂电芯 930/558/372 | 分 SKU 件 | `initial_inventories` 行 77–79 | `DIRECT_DATA` | 可写受短缺影响的公开快照 | 否 |
| 第 60 期 T1 Pack 0 | 包 | 无显式库存行，模型对缺省状态补零 | `EXACT_DERIVED` | 可写模型状态，注明缺省规则 | 否 |
| 第 60 期 OEM Pack 52 | 包 | `initial_inventories` 行 2 | `DIRECT_DATA` | 可写公开快照 | 否 |
| 电芯发运第 46/53/60 期，分别 `(9470,5682,3788)`、`(4220,2532,1688)`、`(4240,2544,1696)` | 分 SKU 件 | `initial_flows` 行 48–56 | `DIRECT_DATA` | 可写原始发运 | 否 |
| 上述批次到货 66/73/80 | 日索引 | `46/53/60 + 20` | `EXACT_DERIVED` | 可写推导 | 否 |
| 第 60 期生产/运输发运 159/200，第 61 期到 T1/OEM | 包 | `initial_flows` 行 73/2；发运期加对应提前期 1 | `DIRECT_DATA`／`EXACT_DERIVED` | 可写发运和推导到货 | 否 |
| 第 39 期可能发运、第 59 期可能到货 | 日索引 | `46−7=39`、`39+20=59`，无对应原始电芯行 | `SUPPORTED_INFERENCE` | 仅作为时间线假说 | 若投入模型需独立证据 |
| Clean 恢复向量 `Δ` | 分 SKU 件，未识别 | 无同一事故批次的前后配对或生成器规则 | `SUPPORTED_INFERENCE` | 只写未识别 | 待准入后分析 |
| `r` 与其区间 | 包，未识别 | 表 7 及 XLSB 无 `t=59` 产能或冻结生产计划 | `SUPPORTED_INFERENCE` | 只写未识别 | 是，须先有状态依据 |
| 若将 70 外推为 `r` 上界 | 包/日，未采用 | 论文窗口示例的外推 | `SCENARIO_ASSUMPTION` | 只能写为未采用的情景设定 | 若采用须敏感性 |
| 容量行换算 `5/21` | 无量纲 | `70/294=490/2058`，`κq≤κC ⇔ q≤C` | `EXACT_DERIVED` | 可写本模型期内等价缩放 | 不用于 860 或库存换算 |

逐个 SKU、容量弧、短缺候选以及条件公式的完整记录见 [parameter_provenance.csv](../artifacts/v25_phase17_20261110_163116/parameter_provenance.csv)。其中 A 的 43 套上界和 B 的 `(8600,5160,3440)` 各自只在其单位假设成立时有效。图 11(a) 的 `1/50` 只表示库存绘图比例，也不能用作事故单位换算。表 7 的两个 70 未提供第 59 期可用余量。若以后使用转换敏感性，需为 `Δ`、`r`、第 60 期发运与库存安排各自登记来源，确保只有未用电芯和到达 T1 的包进入状态，避免重复补回同一批物料。

## 论文表述

- **原论文／数据事实**。`The public case dataset represents simulated variations grounded in system exports and an automotive case study.` 原论文 §4.7 和表 8 说明实际订单池、系统导出、案例访谈和面向对象仿真的作用，并指出部分库存和在途原始记录并不完备。 [原论文全文](https://www.researchgate.net/publication/343539617_Optimisation_model_for_multi-item_multi-echelon_supply_chains_with_nested_multi-level_products)
- **本文确定性推导**。`Derived from the source BOM and observed shipment quantities.` 适用于 20 件配方合计、由提前期推得的到货时点和容量行的等价缩放。
- **本文反事实构造**。只有在明确登记输入与假设、通过准入后才适用 `source-constrained counterfactual reconstruction family`。`SUPPORTED_INFERENCE` 和 `SCENARIO_ASSUMPTION` 均不得用作企业实测库存、丢失批量或第 59 期产能的表述。本轮尚无可用的反事实状态。
