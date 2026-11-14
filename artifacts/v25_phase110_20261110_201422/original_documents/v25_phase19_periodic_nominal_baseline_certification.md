# V2.5 Phase 1.9 周期名义基线准入审计

**`HOLD_SOURCE_NETWORK_LONG_RUN_CAPACITY_MISMATCH`**

原始 14 期网络的电芯长期吞吐不足以支撑原订单结构。第 17 节停止条件在建模前已经由独立整数上界证实。因此本阶段仅完成源数据、周期索引与容量预检，周期最优值、基线库存与在途、正式回放和 14 个联合偏移最优值均未生成。 [容量证书 CSV](../artifacts/v25_phase19_20261110_194850/periodic_capacity_sufficiency.csv) · [冻结准入清单](../artifacts/v25_phase19_20261110_194850/baseline_manifest.json)

## 来源与容量证据

重新读取原始 Mendeley XLSB 和出版版 §4.3–4.4、表 5–7。原 `capacity_at_arc` 的逐期日历、原始配方、12 节点与 11 条弧由现有编译器读入。原论文表 7 的数值只用于交叉核对。上游电芯在 XLSB 第 67、74 期各允许 2,058 件，其他 12 期为零。同一条弧的容量在该期由三种电芯共享。`nodes_inflow` 只允许电芯在该弧起点进入，包生产端、T1 和 OEM 没有额外的电芯或包外生入口。每个 BEV 消耗 1 个电池包，每包消耗 `10+6+4=20` 件。28,000 VIN 中共有 3,003 个 BEV。 [作者数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1) · [原论文全文](https://www.researchgate.net/publication/343539617_Optimisation_model_for_multi-item_multi-echelon_supply_chains_with_nested_multi-level_products) · [逐行参数溯源](../artifacts/v25_phase19_20261110_194850/periodic_network_parameter_provenance.csv)

| 环节 | 原始 14 期上限 | 全订单结构需要 | 总量判断 |
|---|---:|---:|---|
| 共享电芯上游运输 | 4,116 件 | 60,060 件 | 缺 55,944 件 |
| 电池包生产 | 4,116 包 | 3,003 包 | 总量足够，尚未检验时点 |
| T1→OEM 包运输 | 4,116 包 | 3,003 包 | 总量足够，尚未检验时点 |
| OEM 整车装配 | 28,000 辆 | 28,000 辆 | 总量相等，尚未检验时点 |

一个闭合周期内，各 SKU 的在途到货总量等于发运总量。把包厂、T1、OEM 的库存平衡分别对周期求和后，期初期末库存抵消，因而每周期可持续的 BEV 交付 **至多 205 辆（6.8265%）**，至少 2,798 辆 BEV 无法按期完成。即便 24,997 辆非 BEV 全部按期，整车按期量也 **至多 25,202 辆（90.0071%）**。这两个数是上界，尚无求解器最优值或可行见证。放宽周期闭合为跨若干周期的平均时，电芯约束仍只允许平均 205.8 包／14 期。有限额外库存只能暂时弥补缺口，无法提高长期吞吐。 [证明与周期索引](v25_phase19_periodic_model_spec.md)

## 跨期索引预检

使用精确的模到货公式、剩余时间队列和按绝对时点登记的事件账三路核对，覆盖 11 弧的原始日历形状及四个周期。以周期从 0 编号为例，20 日电芯弧的正容量日 7 发运后，在周期 1 第 13 日到达。第 14 日发运后在周期 2 第 6 日到达，在两个跨越的边界分别剩 20 日和 6 日。CSV 的 `quantity` 是原始共享容量标记，只用于逐期索引守恒检验。它不代表某个 SKU 的实际发运量。14 个联合平移逐日保留原需求与容量配对，容量证书相同，未计算平移后的优化目标。 [20 日索引审计](../artifacts/v25_phase19_20261110_194850/long_lead_cyclic_pipeline_audit.csv) · [联合平移预检](../artifacts/v25_phase19_20261110_194850/joint_phase_rotation_results.csv)

## Phase 1.8 与本轮的适用边界

Phase 1.8 的 NB00 仍是已有认证的有限暖机结果，接续期按期 8,242 辆、BEV 为 0。有限目标对暖机之后的配套物料缺少直接价值，允许末端消耗已有可用件而无需补齐对应的未来在途。周期约束在数学上排除借用开盘库存或在途的净下降，同时暴露长期补给总量的不足。Phase 1.9 当前没有可用的周期实验基线，因此不能用 25,202 作为新的求解结果与 NB00 作数值差。 [对照 CSV](../artifacts/v25_phase19_20261110_194850/phase18_vs_phase19_comparison.csv)

## 证据与停止

基线状态和在途 CSV 只有字段，回放表明确标注 `NOT_RUN_CAPACITY_GATE`。正式求解调用为 0，因此没有 LP/MPS 或求解器日志。14 项本轮回归通过，退出码为 0。Phase 1.6–1.8 的既有状态、证书及归档共 342 份文件通过哈希复核。Git 基线 `02143f46cab6e6a173a0f495e21b20d21311096f`。 [机器可读审计](../artifacts/v25_phase19_20261110_194850/audit.json) · [SHA-256 清单](../artifacts/v25_phase19_20261110_194850/sha256_manifest.json) · [回归测试日志](../artifacts/v25_phase19_20261110_194850/pytest_regression.txt)

```powershell
python artifacts/v25_phase19_20261110_194850/preflight.py
python -m pytest -vv tests/test_v25_phase19_periodic_preflight.py
```
