# V3 Phase 3.0 完整基模恢复报告

**PASS_FULL_BASE_WITH_DOCUMENTED_APPLICATION_DIFFERENCES**

V3 恢复了公开汽车案例的 28,049 品项、28,000 VIN、12 节点、11 弧、87,059 BOM 表行、15 操作与 14 期。BEV 的 3,003 个 VIN 是重点风险报告子群。Gurobi 实际求解的完整案例有 75,810 个整数变量、23,019 条约束。订单按等价签名压缩为 1,286 组，结果展开至每辆车。显式 VIN 索引对应 1,571,794 个整数变量和 450,443 条约束，这两项为按活动键计算的规模。论文未公布可逐项对应的求解器矩阵维度。 [网络审计](../artifacts/v3_phase30_20261111_104032/full_network_scope_audit.csv) · [BOM 审计](../artifacts/v3_phase30_20261111_104032/full_bom_restoration_audit.csv) · [完整规格](v3_full_model_spec.md)

## 确定性复现门

| 公开 XLSB 运行 | η | 五项目标和 | 总出库 | BEV 缺口 | 提前装配 |
|---|---:|---:|---:|---:|---:|
| A 无重排，正文权重 | 200 | 7,617,462 | 26,448 | 1,552 | 0 |
| A 无重排，图示权重 | 0 | 5,058,662 | 26,448 | 1,552 | 0 |
| B 可重排，图示权重 | 200 | 5,360,953 | 26,448 | 1,552 | 7,044 |
| B 可重排，正文权重 | 0 | 5,047,053 | 26,448 | 1,552 | 4,187 |

四次均为 OPTIMAL，目标等于界，gap、求解器残差和独立整数物料残差均为 0。各次非 BEV 出库 24,997 辆，BEV 出库 1,451 辆，总体 OEM 装配利用率 94.46%。B 图示权重下，第 61–73 期每期装配 2,000 辆，第 74 期装配 448 辆，1,552 个空余名额集中在第 74 期。该运行已履约 VIN 全部在承诺日出库。提前装配与承诺日出库间的差量由 zp8 VIN 库存承担。 [目标与界](../artifacts/v3_phase30_20261111_104032/deterministic_replication_results.csv) · [逐期轨迹](../artifacts/v3_phase30_20261111_104032/replication_timeline.csv)

正文 §4.9 与图 10 的 η 对应关系相反，因此分别运行。A 的 1,552 缺口和 B 空余能力向期末集中符合论文比较方向。公开数据未提供论文原始 VIN 解，论文对延期订单的图示和本轮精确出库不能逐辆比对。复现使用原 t60 库存和在途，缺口由同一数据链求得。 [目标分类](../artifacts/v3_phase30_20261111_104032/replication_target_comparison.csv) · [论文](https://doi.org/10.1016/j.ejor.2020.08.005)

## 扩展接口与研究边界

基模通过后，双情景接口回归验证了固定正常库存与额外保护库存并存、整数追索、共同阶段一变量以及场景作用于运输弧。前瞻正式常规状态待独立证据。未来分离接口直接调用完整追索块。记录 CLASSICAL_BENDERS_NOT_DIRECTLY_APPLICABLE_WITH_INTEGER_RECOURSE。原文 §5 把计算问题、求解策略、启发式和分解列为未来研究方向。 [接口实现](../src/prefab_v3/interface.py) · [来源差异](../artifacts/v3_phase30_20261111_104032/source_vs_v3_model_diff.md)

同 BOM 的两个 VIN 交换日期时，电池与共享装配路径保持可行，日期偏差成本增加。不同座椅的 VIN 交换后，固定座椅来料会违反 JIT 平衡。电池库存路径不足以决定完整目标和可行性，其他可能的精确化简仍是开放问题。 [可约性审计](../artifacts/v3_phase30_20261111_104032/full_model_reducibility_audit.md)

Phase 2.0 至 2.2 归档定位为 FOCAL_BATTERY_MECHANISM_VALIDATION_MODEL。2.0 验证机制定义，2.1 验证内生缓冲结构，2.1A 验证多政策集合，2.1B 验证风险匹配，2.2 的可约性结论适用于焦点子模型。该证据作为开发记录与补充材料保留。 [机器审计](../artifacts/v3_phase30_20261111_104032/audit.json) · [SHA-256 清单](../artifacts/v3_phase30_20261111_104032/sha256_manifest.csv)
