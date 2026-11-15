# V3.2.1 Gate 2C 重新认证

**Gate 2C `PASS`，`READY_FOR_GATE3 = TRUE`。** 该结论基于 V3.2.1 修正后的认证规则。Gate 3 未启动。 [V3.2.1 规格补充](V3.2.1_Gate2C_Certification_Supplement.md)

## 原模型与历史证据

本轮以 Draft PR #3 的 `1acb8872bedf99de5bed1e8d94ffbae2190cd7f2` 为基线。联合模型构造函数、准备期物料网络、91 个候选位置和情景网格原样保留。代表性联合模型的 LP 和 MPS 解压后均与 V3.2 停点归档逐字节一致，107 个联合问题的目标值均与原运行一致。

V3.2 的 C2C-07/C2C-10 判据过度限制了认证。原 C2C-07 跨库容情景比较，原 C2C-10 拆分强制联动的电芯变量。原报告及失败证据完整保留，包括 22 条 C2C-07 和 12 条 C2C-10 失败记录。 [原失败证据](../experiments/v32_gate2c_joint_preparedness/evidence/gate2c_bmax_crosscheck.csv)

## 重跑结果

| 检查 | 状态 | 证据 |
| --- | --- | --- |
| C2C-01、02 | PASS | 逐解核对原料来源、合法弧、到货时点及 SKU 配方。各节点、物料、期独立重放守恒，最大残差 0。 |
| C2C-03、04 | PASS | 共享生产和运输能力、逐状态库存上限的最大违约均为 0。两种 Engine SKU 各自可形成 4,200 件，同时固定为各 4,200 件时，Gurobi 复证不可行。 |
| C2C-05、06 | PASS | 每个联合解满足三类电芯 10:6:4。逐期核对四种 OEM Seat SKU 的共享库容，最大违约为 0。 |
| C2C-07（修正） | PASS | 100 个不同物理情景。每个情景求 88 个普通位置和 1 个完整 kit 的投影，共 8,900 个最优投影、9,100 条位置上界。107 个联合解的 9,737 项逐位置检查全部通过。 |
| C2C-08、09 | PASS | 80 项 α 和 20 项 H 单调性对比全部通过。 |
| C2C-10（修正） | PASS | 旧情景的五个 H 共求解 445 个投影问题，复现全部 455 项冻结位置上界。H=2、20、21、22、23 的完整电芯 kit 上界分别为 0、14、29、44、58。 |

全部 107 个联合问题均为 Gurobi `OPTIMAL`，MIP gap 为 0，独立重放残差、共享能力、物理守恒、库存、OEM Seat 库容及整数性最大违约均为 0。求解与审计合计 60.33 秒。以 H=23、α=1、δ=0.5、仅技术上界的 OEM Seat 最大化为例，1,000 件缓冲与相同库容情景下的上界比较。诊断预算案使用同物理情景的无预算投影，预算收紧后的可行域包含关系保证该上界有效。 [新版证据](../experiments/v32_gate2c_joint_preparedness/evidence_v321/)

## 准入与复现

Gate 0、Gate 1、Gate 2A、Gate 2B gross 的证据已核对。当前全部 C2C-01–10 通过。`EMPIRICAL_RESIDUAL_CAPACITY = NOT_IDENTIFIED`。五个 T1 位置的真实物理库容和正 δ 所代表的 OEM Seat 扩容仍属于未验证的情景参数。

Python 3.12.7、Gurobi 13.0.1。原版与修订版的 8 项证据回归全部通过。配置、输入哈希、有效库容情景、逐解证书、压缩求解日志和模型文件见新版证据。求解日志发布副本已去除本机路径及许可证标识。

```powershell
$env:PYTHONPATH = 'src'
python experiments/v32_gate2c_joint_preparedness/run_gate2c.py --bundle '<V31_Codex_Inputs.zip>' --xlsb '<original.xlsb>' --out '<new-output-directory>'
python -m pytest tests/test_v32_gate2c_evidence.py tests/test_v321_gate2c_evidence.py -q
```
