# V3 全 BOM 缓冲资格与状态位置可行性审计

**最终状态 `PASS_WITH_CONDITIONS`。** 已完成四项审计，覆盖 **336,588 个 item × node** 和 **115,096 条状态转换或订单出库边**。固定 D4 情景的 C0 复现 **11,775** 辆。零增量是 C1–C3 目前可认证的边界。C4 的理论准备条件下可达 **17,250** 辆，但原资料缺少 OEM 库容及风险前余量，因此 **当前证据不允许进入正式 V3 重构**。

## 原网络与 BOM

原始 XLSB 有 28,049 个品项、12 个节点、11 条弧。第 60 期是观察到的状态，第 61–74 期提供需求与运营能力。28,000 个 VIN 对应 104 个完整 BOM 签名，按到期日、节点及权重压缩为 1,286 个等价组。每辆需要一个指定 Engine、Gear、Seat，3,003 个 BEV 还需要一件 Pack。Pack 用 10/6/4 三种 Cell，四种 Seat 各消耗一件对应组件。Engine、Gear 只有公开的同 SKU 生产状态转换，缺少可构造其上游零件子 BOM 的材料。 [原始数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1) · [工艺审计](../audit/v3_bom_operation_audit.md) · [全转换图](../audit/v3_state_transition_graph.csv)

## 全资格审计与候选集合

`ELIGIBLE` 仅表示原始模型口径支持该库存状态，库存表的 99,999 不能当作现场可用于增量缓冲的货位数。`CONDITIONAL` 表示网络上有状态与路径，尚需仓储或业务证据。`UNKNOWN` 表示存在作业或外部供货记录，但原资料不足以判定可否驻留库存。`INELIGIBLE` 包括缺少合格状态、VIN 成车不属于本轮物料缓冲范围，以及原案例 OEM Seat 零库存限制。源表缺行在原值列留空，冻结模型补零在独立列显示。 [资格全表](../audit/v3_buffer_eligibility.csv)

| 分支 | Baseline ELIGIBLE | Baseline CONDITIONAL | UNKNOWN | Baseline INELIGIBLE | 扩展新增 CONDITIONAL |
|---|---:|---:|---:|---:|---:|
| Battery Cell | 3 | 0 | 3 | 30 | 0 |
| Battery Pack | 1 | 1 | 0 | 10 | 0 |
| Engine | 58 | 0 | 29 | 261 | 0 |
| Gear | 16 | 0 | 8 | 72 | 0 |
| Seat 上游组件 | 4 | 0 | 4 | 40 | 0 |
| Seat 成品 | 0 | 4 | 0 | 44 | 4 |
| VIN 成车 | 0 | 0 | 0 | 336,000 | 0 |
| 合计 | **82** | **5** | **44** | **336,457** | **4** |

(E_{mathrm{base}}) 的已证资格为 82 个键，另附 5 个条件候选，含 T1 Pack 与四个 Seat 供应商成品库存键。(,E_{mathrm{extended}}) 的已证资格仍为 82 个，条件候选为 9 个，新增四个 OEM Seat SKU。它们有真实配送弧，但没有允许常备库存的物理证据。候选表保留两类标志，条件键不得作为正式可行变量直接加入。座椅生产节点的合法存储对象是四种上游组件。生产出的 Seat 直接进入供应商 `inv`，源图没有生产节点的成品 Seat 驻留态。 [资格分支统计](../audit/v3_buffer_eligibility_summary.csv) · [E_base](../audit/v3_E_base.csv) · [E_extended](../audit/v3_E_extended.csv) · [原论文 JIT/JIS 依据](https://doi.org/10.1016/j.ejor.2020.08.005)

## 容量、成本和风险前路径

对 91 个可审查键逐项登记 (K_{np},c_{np},h_{np},c_{m prod},c_{m trans},lead_{m prod},lead_{m trans},prep_capacity,trans_capacity)。`DIRECT` 只用于源表中可读量，`TRANSFORM` 标示路径合计及源案例库存规则，`CALIBRATE` 仅用于已有归一化实验成本，`MISSING` 为空值。五个 Battery 相关位置对应三个已有的参考费率，Cell 三 SKU 共享每套成本 1，T1 Pack 和 OEM Pack 分别为 27/19 和 297/190。它们是 D4 实验预算单位，无从分解为企业资本、持有、加工和运费。91 个键都缺少经验证的企业增量成本与现场增量库容。 [经济参数](../audit/v3_buffer_economic_feasibility.csv)

路径表逐位置追踪全部上游输入、节点、BOM 数量及运营容量。路径总 lead 取各并行投入的最长链再加共同加工、运输。以第 60 期末到位计，新上游 Cell 到 T1 最晚须在第 40 期起运，到 OEM Pack 的新料路径最晚第 38 期。新 Seat 组件到 OEM 的完整源路径为 23 期，最晚第 37 期起运。已有 Seat 组件的末两段可以同一期执行，仍需在第 61 期前安排可用的加工和运输槽位。Engine 到 OEM 为 2 期，Gear 为 4 期。源能力日历自 61 期才开始，历史发运和实存可证明已有状态，无法证明有额外的风险前生产、运输及中间储存余量。所有 91 个键的新增风险前备货均为 `NOT_CERTIFIED`。该标记表示证据不足，物理真实上限留空。 [逐键可达性](../audit/v3_preparation_reachability.csv)

## 统一 Buffer Portfolio

| Branch | Material state | Node | Eligible | Capacity | Cost | Prep feasible | D4 exposure |
|---|---|---|---|---|---|---|---|
| Battery | Cell 套件中的三 SKU | T1 prod | 是，源模型 | 各 SKU 99,999，实际未知 | 参考 1/套 | 增量未认证 | 在 Cell 固定收货风险下游，仍需 Pack 产运 |
| Battery | Pack | T1 inv | 有条件 | 未知 | 参考 27/19 | 增量未认证 | 已跨过 Cell 收货与 Pack 加工，仍暴露于 Pack 运输 |
| Battery | Pack | zp7 | 是，源模型 | 99,999，实际未知 | 参考 297/190 | 增量未认证 | 绕过电池三层风险，对 D4 Seat 情景的约束无直接作用 |
| Engine | 成品同 SKU | T1 inv / zp7 | 是，源模型 | 各 SKU 99,999，实际未知 | 缺失 | 增量未认证 | 两点均在发动机加工风险下游，Seat 仍受扰 |
| Gear | 成品同 SKU | T1 inv / zp7 | 是，源模型 | 各 SKU 99,999，实际未知 | 缺失 | 增量未认证 | 仅 OEM 库存跨过 Gear 运输风险，Seat 仍受扰 |
| Seat | 对应组件 | Seat prod | 是，源模型 | 各 SKU 99,999，实际未知 | 缺失 | 增量未认证 | Seat 末段受扰弧上游 |
| Seat | 对应成品 | Seat inv | 有条件 | 缺失 | 缺失 | 增量未认证 | 仍需经过受扰末段 |
| Seat | 对应成品 | zp7 | Baseline 排除，扩展有条件 | Baseline 0，扩展未知 | 缺失 | 增量未认证 | 若揭示前到位，可跨过受扰末段 |

当前无法认定某组合成本过高，或某候选的现场库容必然不足。OEM Seat 的 baseline 零库存是已知的模型排除条件。合法上游存储并不能替代足够提前期和当期剩余能力。 [逐键组合表](../audit/v3_buffer_portfolio.csv)

## D4 固定情景与四项审计的关系

| 对比 | 数值或证据 |
|---|---|
| 原 V3 Baseline | C0 精确复现 11,775 准时、11,775 总完成；按期缺口 16,225 |
| 全 BOM 合法缓冲候选 | 资格和路径已逐项审计，实际增量准备未获认证。保持原 OEM Seat 规则时，其他分支和 Seat 上游预置均无法突破固定 D4 末段约束给出的 11,775 上界 |
| 扩展 Seat OEM 预置 | C1–C3 的已认证子集仅含零新增，均为 11,775。有限 SKU 库容、可用运力与真实最大预置未验证 |
| 理论准备容量 | C4 在假定预生产、预运输及 OEM 库容各 6,000 时，按原 SKU 实际扣减现存上游组件，可得 17,250。达到该值最少需 5,475 件。一件预置可实现理论上的第一辆增量 |

第 71 期座椅前缀给出 (Y_{OT}le11775+B_s)。C4 的 17,250 是这个固定场景、已知毛组件池及理论准备条件下达到的值。扩展后的鲁棒最优值仍未知。由于该情景仍属于不确定集，它只给扩展后的固定政策鲁棒服务提供一个必要上界。 [独立诊断报告](../audit/v3_seat_oem_preposition_diagnostic.md) · [求解结果](../audit/v3_seat_oem_preposition_counterfactual.csv)

## 重构所需证据与模型建议

1. 现场应先核验 OEM 座椅可用工位、各 SKU 存储上限、共享货架或面积、装载兼容性及质量保存条件。来源证据齐备后才定义扩展的 (K_{np}) 和总库容。
2. 补齐风险前独立时间窗、上游净可用材料、承诺排产、生产和运输的剩余槽位、在途和中间库存约束。风险前形成量应由同一网络物料平衡推出，准备结束的库存作为所有风险情景共享的固定开盘量。
3. 用可核实的币种和日期校准资本、持有、加工、运输及准时交付价值。保留缺失状态，避免用已有归一化成本替代企业金额。完成这些证据后，方可认证扩展库存政策的可行性并重新评估正式鲁棒服务。

## 数值认证、复现和范围

原始数据证明网络、配方、开盘和 61–74 期能力。模型证明资格排除、物料路径、时序限制和固定场景前缀界。11,775、17,250、最少一件及最大结果所需 5,475 件来自固定情景完整整数求解。未来经济参数、现场可用库容和揭示前能力需要独立校准或企业验证。未修改正式模型、原 XLSB、BOM 或 D4 风险，未合并代码，未重跑 Γ=3 全域。

源 XLSB SHA-256 为 `1ea0bcdea3225d308be913c9ca0f377585e1863847c78d6e8eec10b6de82889e`。分支 `v2.5-phase1-numerical-certification`，HEAD `02143f46cab6e6a173a0f495e21b20d21311096f`。冻结 D4、D3、D-2R 分别核验 951、4,207、181 条清单记录。各配置 SHA-256、初始工作区状态及求解记录随报告保存。 [输入身份](../audit/v3_input_provenance.json) · [机器审计](../audit/v3_full_bom_audit.json) · [SHA-256](../audit/v3_sha256_manifest.csv)

使用现有 Python、Gurobi 13.0.1 与项目锁定的 pyxlsb 1.0.10。从仓库根目录执行。

    $env:PYTHONPATH = "src;$(Join-Path $env:TEMP 'prefab-phase32d2r-deps')"
    python -B audit/v3_seat_diagnostic.py
    python -B audit/v3_inventory_audit.py
    python -B audit/v3_verify_audit.py
