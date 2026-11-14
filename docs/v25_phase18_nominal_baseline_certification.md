# V2.5 Phase 1.8 Source-Calibrated Nominal Baseline 认证

> **INTERPRETATION_CORRECTION（Phase 1.10）**。下文保留当时的诊断运行与状态标签。原论文 55 期是数据生成仿真的 settling time。56 期是本诊断的实验协议，不能据此认定 V2.5 收敛、达到稳态或优化时域充分。NB00 不作为论文的正式名义基线。 [现行规格](v25_model_spec_v2_source_semantics_corrected.md)

**`PASS_BASELINE_CERTIFIED_WITH_PHASE_SENSITIVITY`**

本阶段在 `02143f46cab6e6a173a0f495e21b20d21311096f` 的源模型上构造实验起点。网络、配方、容量、提前期与订单结构来自原始 XLSB。暖机期以不受额外扰动的模型推进状态，末端库存和在途从求解向量提取。它的含义是基于公开案例构造的有限暖机实验状态，证据范围不包含某个历史事故前的库存。 [原论文全文](https://www.researchgate.net/publication/343539617_Optimisation_model_for_multi-item_multi-echelon_supply_chains_with_nested_multi-level_products) · [原作者数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1) · [参数依据](v25_phase18_network_parameter_evidence.md)

## 冻结设计和时序

- 原论文 §4.7 给出 55 期 settling time。本项目使用严格大于 55 的最小完整 14 期倍数 56。四个周期各有 28,000 个 VIN，其中 3,003 个 BEV。14 个 offset 仅改变需求日循环起点，容量及 SKU／组流量上限始终按原 61–74 期自然日历重复。正式期各候选均用原始自然需求顺序。
- 暖机从公开 `t=60` 库存和未到货发运开始。所有风险乘子为 1。B0 保持零新增保护缓冲。电芯上游按原容量和 20 期提前期发运，未向下游人工注入物料。
- 采用 Phase 1.6 的整段整数名义模型和相同的按期服务目标。到期日仍与原周期的位置对应。迟交在 56 期窗口内可以发生，但不计入按期目标。跨周期不自动清除或复制需求，原来每个独立订单组的总交付上限保持有效。正式期启用新的 VIN／组身份，旧订单保留在暖机审计清单。旧订单专属成品库存保留在物理状态中，不能用于新订单。
- 暖机结束的所有 `I[n,item,56]` 进入正式 `t=0`。每个仍在途的 `q` 具有唯一的弧、SKU 和发运期，正式到货日等于暖机发运日加提前期再减 56。窗外在途仍保留在状态清单中，正式 14 期仅接收窗内到货。
- NB00 由自然顺序预先指定。正式实验没有按服务率挑选 offset。 [冻结清单](../artifacts/v25_phase18_20261110_181931/baseline_manifest.json) · [需求映射](../artifacts/v25_phase18_20261110_181931/warmup_demand_mapping.csv) · [重编号核验](../artifacts/v25_phase18_20261110_181931/time_reindex_audit.csv)

## 最优性认证

暖机的独立物料上界对全部 offset 一致。包生产端初始和可及时到货的历史电芯共 `37,720` 件。新的电芯需经过 `20+1+1` 期；能在第 56 期前到达整车环节的原始正容量日为暖机第 7、14、21、28 日，合计最多 `4×2,058=8,232` 件。两类来源合计至多 `floor((37,720+8,232)/20)=2,297` 个新包。加原始可达的 `52+159+200=411` 个包，BEV 按期量至多 `2,708`；非 BEV 最多 `4×24,997=99,988`，故总上界 `102,696`。约束未要求假设每个新批次都按 BOM 比例装运。

起初的求解器试跑使用全局零间隙停止。部分试跑在达到上述整数上界后仍对小于一辆的根松弛差距分支。最终 14 个偏移使用相同的暖机证书停止规则，`BestObjStop` 为独立整数上界对应的比例。求解器若按目标停止，保留其原状态 `USER_OBJ_LIMIT`，同时要求完整整数向量逐行回读后达到数学上界。停止规则不改变目标、物料或变量域。试跑与中断日志另行保存。

正式 14 期全部使用 Phase 1.6 的 `OptimalityTol=1e-9`、严格预算、零相对／绝对 MIP 间隙及零物料残差。正式求解没有目标停止。每次都把完整解向量作为可行见证，并用独立上界闭合。电池物料上界与非 BEV 订单数之和若不足以闭合，使用 LP 对偶乘子作为候选证据，将其有理数化，检查符号后逐行乘加，并对残余系数使用有物理证明的有限上界作非负修正。证明使用的有限供给上界只用于验证，未加入求解模型。由此得到整数交付上界，和可行向量直接比较。 [运行协议](../artifacts/v25_phase18_20261110_181931/warmup_execution_protocol.json) · [完整日志](../artifacts/v25_phase18_20261110_181931/gurobi_logs.zip)

## NB00 与 14 个偏移结果

14 个暖机均达到独立上界 **102,696 / 112,000**，其中 BEV 2,708、非 BEV 99,988。14 个正式实例均为 Gurobi `OPTIMAL`、MIP 间隙 0、严格预算余量为零、整数物料平衡残差 0，且独立上界等于各自的可行按期量。

| 实例 | 总需求 | BEV 按期 | 非 BEV 按期 | 总按期 | 按期率 |
|---|---:|---:|---:|---:|---:|
| NB00 B0 | 28,000 | 0 | 8,242 | **8,242** | **29.4357%** |
| 既有 stressed B0 | 28,000 | 1,451 | 24,997 | 26,448 | 94.4571% |

NB00 正式整数求解用时约 0.262 秒。可行下界与独立全局上界均为 8,242，精确预算支出为 0，三个缓冲均为 0。暖机终态的包厂三类电芯为 `2064 / 6 / 0`，齐套量为 0，T1 和 OEM 包库存均为 0。唯一的未到货发运是第 35 期的 14,700 件座椅组件 `componment_seat1`，经 23 期提前期在正式第 2 期到货。第 1–14 期新电芯发运无法走完 20 日上游和 2 日下游，因而无可达 BEV 包。此结论基于所导出的终态。NB00 与 stressed 相差 −18,206 辆，是两个不同初始状态在同一模型下的差异，无法归因于历史事故数量。 [主基线在途](../artifacts/v25_phase18_20261110_181931/nominal_baseline_in_transit.csv) · [主基线独立上界证据](../artifacts/v25_phase18_20261110_181931/NB00/independent_dual.json)

偏移后的正式服务率最小 27.6429%（NB13），最大 53.6250%（NB04），均值 39.5467%，中位数 37.8821%，总体标准差 8.7284 个百分点，极差 25.9821 个百分点。各候选 T1 和 OEM 包库存、完整套数及正式期可达 BEV 供给均为 0。14 组总在途均为 14,700，按不同 SKU 汇总的总库存介于 13,527 和 31,067 之间。对均值为零的指标，CV 按清单记为 `NA`。正式窗口对暖机相位明显敏感，也受有限暖机目标允许的末端多解影响。 [14 组结果](../artifacts/v25_phase18_20261110_181931/phase_offset_baselines.csv) · [各指标完整统计](../artifacts/v25_phase18_20261110_181931/phase_offset_stability.csv)

## 输出索引

- [主基线库存](../artifacts/v25_phase18_20261110_181931/nominal_baseline_state.csv) · [主基线在途](../artifacts/v25_phase18_20261110_181931/nominal_baseline_in_transit.csv) · [正式电池库存轨迹](../artifacts/v25_phase18_20261110_181931/nominal_baseline_battery_trajectory.csv)
- [NB00 正式 B0](../artifacts/v25_phase18_20261110_181931/NB00_formal_B0.json) · [14 个偏移摘要](../artifacts/v25_phase18_20261110_181931/phase_offset_baselines.csv) · [偏移统计](../artifacts/v25_phase18_20261110_181931/phase_offset_stability.csv)
- [机器可读审计与全部输入输出哈希](../artifacts/v25_phase18_20261110_181931/audit.json) · [回归测试日志](../artifacts/v25_phase18_20261110_181931/pytest_regression.txt)

各 offset 的 `warmup.json.gz` 与 `formal.json.gz` 保存整数非零分量，缺省为零。终态和正式结果可用原始 XLSB、清单及脚本重放。Phase 1.8 的 15 项新增回归与 Phase 1.6、1.7 的 23 项相关回归合计 **38 通过、0 失败**。旧归档和 Phase 1.6 六份严格证书通过哈希复核。审计在 Phase 1.8 结束。

```powershell
python artifacts/v25_phase18_20261110_181931/prepare_evidence.py
python artifacts/v25_phase18_20261110_181931/run_baseline.py
python -m pytest -vv tests/test_v25_phase18_nominal_baseline.py tests/test_v25_formal_witness_regression.py tests/test_v25_phase17_provenance.py
python artifacts/v25_phase18_20261110_181931/finalize_baseline.py
```
