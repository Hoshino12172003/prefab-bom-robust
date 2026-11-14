# V3.1 Gate 1 与 Gate 2B 数值认证

**Gate 1 `PASS` · Gate 2B gross `PASS` · Gate 2B residual `BLOCKED`.** Gate 2B 的总体结论为 `BLOCKED`，当前不具备进入 Gate 3 的条件。

本轮使用最终规格 DOCX、Gate 0/2 XLSX 和参考脚本。工作簿的 91 项位置、物料组和最短提前期与从作者 XLSB 恢复的结果逐键一致。仓库原有预检记录保留，验证实现独立放在 `experiments/`。 [规格与实现核对](v31_gate1_gate2b_spec_reconciliation.md)

## Gate 1

| 五个库容未核实位置的处理 | 状态 | 按期交付 | Gurobi best bound | MIP gap | 求解用时 | 节点数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 零库存基准 | OPTIMAL | 26,448 | 26,448 | 0 | 0.239 s | 1 |
| 合法流量技术上界 | OPTIMAL | 26,448 | 26,448.000000000004 | 0 | 0.552 s | 1 |

两案均可行且最优值一致，服务率为 94.4571%，未按期交付 1,552 辆。技术上界案允许四种 T1 Seat 各 29,400 件、T1 Pack 3,981 件。上界由可在期内到达的弧能力及固定到货加总所得，属于技术模型值。两案允许不同的逐期交付和库存路径。

28,000 VIN 精确聚合为 1,286 组。原始 117 条历史发送逐条保留，106 条在第 61–74 期到货，11 条在运营窗之后到货。两案各复核 1,274 行内部库存平衡。最大绝对平衡残差、生产和运输能力违约、`max_flow_product`、`max_flow_group`、库存上下界违约及整数性误差均为 0。参考脚本按原样使用同一 XLSB 独立求解零库存案，同样获得 26,448、gap 0。 [Gate 1 证据](../experiments/v31_gate1_gate2b_certification/numerical/gate1_summary.json)

## Gate 2B

| 准备期 H | 结构时间可达 | 可形成正库存 | `Bmax` 最优证书 |
| ---: | ---: | ---: | ---: |
| 2 | 66 | 66 | 91/91 |
| 20 | 77 | 77 | 91/91 |
| 21 | 78 | 78 | 91/91 |
| 22 | 79 | 79 | 91/91 |
| 23 | 91 | 87 | 91/91 |

基准 `eta=1`。弧能力按第 61–74 期含零的 14 期算术均值计算。两条长提前期运输弧的均值分别为电芯 294 单位/期、Seat 组件 2,100 件/期。全部 455 项求解均为 OPTIMAL、gap 0，整数性和约束违约均为 0。独立路径上界核验逐项得到相同整数值。求解器时间合计约 2.328 s，Gate 2B 整段用时约 6.567 s。`Bmax` 是单位置的投影上界，同一分支多个 SKU 会共享能力。 [逐弧能力](../experiments/v31_gate1_gate2b_certification/numerical/gate2b_arc_capacity_mapping.csv) · [全位置结果](../experiments/v31_gate1_gate2b_certification/numerical/gate2b_buffer_formation_limits.csv) · [路径上界证明表](../experiments/v31_gate1_gate2b_certification/numerical/gate2b_path_bound_verification.csv)

- **Engine / Gear**。Engine T1 和 OEM 在 H=2 已能备货。Gear T1 在 H=2 已能备货，OEM Gear 需要 H≥4。T1 上界由生产弧决定，OEM 上界由生产与运输两段的共同节拍决定。H=23 时，各 SKU 的单独上界依次为 Engine T1 48,300、OEM 46,200，Gear T1 46,200、OEM 42,000。
- **Battery**。电芯 H=20 首次形成 14 个完整 kit，即 140、84、56 单位。T1 Pack 在 H=21 首次形成 14 件，OEM Pack 在 H=22 首次形成 14 件。H=23 时三项分别为 58 个 kit、44 件、29 件。上界由 20 期上游运输、294 单位/期与 20 单位的完整 BOM kit 共同决定，Pack 加工和运输各再引入一期。
- **Seat**。23 期运输决定最早可达。H=23 时，四种 Seat 组件各可单独形成 2,100 件，四种 T1 成品各可单独形成 2,100 件，受上游运输和 T1 生产的同量级能力限制。四种 OEM Seat 在时间上可达，当前 JIT 情景下 `K=0`，因此 `Bmax=0`。

T1 Pack 和四个 T1 Seat 的正数量依赖有限流量技术上界，真实库容缺证据。其余带源表上限的状态也应核对物理库容，尤其是 `99999` 的模型占位值。OEM Seat 扩容情景需要额外明确总容量与 SKU 的共享规则。Gate 2B 的资源记录区分单个最优解中的紧约束和路径证明中的限制资源。

正常准备期业务流和库容占用均缺少可靠的 t=60 前记录。第 61–74 期名义解无法验证之前的业务占用。因此 residual 状态为 `RESIDUAL_CAPACITY_NOT_CERTIFIED`。需在 Gate 3 前确认准备期能力与来源假设、库存情景及剩余能力的处理。H=23 为全网络提前期基准。

## 复现与证据

使用 Python 3.12.7、Gurobi 13.0.1、`pyxlsb==1.0.10`、`openpyxl`。两个 Gate 的 JSON 记录了执行时的代码 SHA、五项输入哈希、求解参数及用时。

```powershell
$env:PYTHONPATH = 'src'
$runner = 'experiments/v31_gate1_gate2b_certification'
python "$runner/numerical_certification.py" --xlsb '<original.xlsb>' --bundle '<V31_Codex_Inputs.zip>' --out '<new-evidence-dir>' --eta 1
python "$runner/verify_gross_bounds.py" '<new-evidence-dir>'
```

实跑两个脚本、Python 语法检查、参考脚本和 5 项 `tests/test_v3_phase30_base.py` 回归，退出码均为 0。发布证据包含 LP 压缩副本、MPS、解、逐期交付、逐行守恒、容量与整数审计、日志及 SHA-256。公开日志仅替换文件路径和许可证相关信息。原始工作簿、规格 ZIP、解释性附件与未脱敏日志留在本机。
