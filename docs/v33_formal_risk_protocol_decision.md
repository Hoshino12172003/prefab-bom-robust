# V3.3 风险协议冻结决策

审计对象为优化实验中的风险稳健性、案例证据与可复现性。选择发生在协议冻结阶段。正式优化调用数为 0。

## 事件选择和证据

核心五个资产由 BOM 分支和生产／运输机制覆盖确定。每资产只保留两个压力档位，沿用已有 Phase 3.2D-2 材料中的 25%／75% 标准化损失及 4／7 期压力尺度。4 期取数日中断尺度，7 期取约一周尺度。两个恢复时段来自已认证的逐期恢复表达。各资产起点沿用 Gate 3 日历。冻结选择未读取当前任何正式目标值。 [旧协议证据记录](v3_phase32d2_multibom_uncertainty_calibration.md)

外部事件支撑量级与机制。Aisin 的现场研究提供数日恢复的观察，Toyota 公告记录约一周的装配停线后按期复工，Ford 披露供应商火灾后特定整车产线停线略逾一周。Renesas 公告记录产能逐步恢复。五条源资产上的真实可用率、冲击持续期及恢复参数均无法由上述案例识别。正式表述为 `literature-anchored stress-test scenario`，数值证据等级为 `SCENARIO`。企业参数及经验敏感性保留为 `UNRESOLVED`。 [Aisin 现场研究](https://merc.e.u-tokyo.ac.jp/mmrc/dp/pdf/MMRC433_2013.pdf) · [Toyota 公告](https://global.toyota/en/detail/11138722) · [Ford SEC 附件](https://www.sec.gov/Archives/edgar/data/37996/000003799618000047/exhibit99to516188k.htm) · [Renesas 公告](https://www.renesas.com/en/about/press-room/update-9-notice-regarding-semiconductor-manufacturing-factory-naka-factory-fire-production-capacity)

Gate 3.5 记录作为响应背景。4 期档位介于已跑过的 3、5 期之间，7 期、25% 可用率介于同持续期的 20% 与 40% 可用率之间。冻结档位自身的 V3.3 服务效果留待正式实验。两个上游事件在需求窗口后才可能到货，保留补充用途并未计入核心风险集。 [逐参数记录](../experiments/configs/formal_event_parameter_evidence.csv)

## 尾窗基线决策

三个口径均为尾窗情景延拓。`CALENDAR_REPEAT` 保留已认证的 14 期排班、运输集中日及零发运日，能沿用 Gate 3.6 的基线解释。`MEAN_EXTENSION` 保持平均水平但取消日历起伏，用于检验结论对时间分布的依赖。`CONSERVATIVE_EXTENSION` 采用含零均值的固定 75%，统一检验低尾窗能力。75% 作为预注册情景参数。第 75–97 期真实名义能力缺少观测，三种口径均保留该证据边界。 [尾窗 CSV](../experiments/configs/tail_capacity_protocol.csv) · [Gate 3.6 认证](v33_gate36_certification.md)

## 主张与证据

| 主张 | 已有证据 | 未解决事项 |
| --- | --- | --- |
| 五条资源覆盖目标供应链机制 | 来源 XLSB 逐弧容量的认证映射，正式目录逐项核查 | 资产实际发生频率与依赖关系 |
| 压力情景有可解释的时间尺度 | 上述案例和旧压力协议，Gate 3.5 网格作为上下文 | 特定工厂参数与冻结档位自身的 V3.3 响应 |
| 恢复指标与尾窗输入可复现 | 既有回放、精确式和三种预先冻结的尾窗定义 | 历史后续排班和未来观察能力 |
| 预算幅度与物理规模对应 | 同一准备可行域的联合资本上界规则，29-kit 可查参考价 | 未来计算 `Bmax` 并报告服务响应区间 |
| 三级经济比较口径可追溯 | Gate 3.6 估值、持有、资本口径 | 加急、加班、扩容及增量运营成本继续缺证 |

## 静态验收

| 检查 | 状态 | 核验内容 |
| --- | --- | --- |
| P-01 | PASS | Git 对比认证基线的模型、准备代码和历史证据，4,208 个共同阶段一变量和 91 个期初状态与 Gate 3.6 一致。 |
| P-02 | PASS | 五条主资产及两条补充资产全部匹配来源网络。 |
| P-03 | PASS | 每项事件参数有证据等级、来源与解释，资产级实证缺口单独留存。 |
| P-04 | PASS | `availability` 是正式输入，损失率为派生值。 |
| P-05 | PASS | 三种尾窗的 Γ 容量向量集均严格嵌套。 |
| P-06 | PASS | 规则只依赖事件身份、资源、档位和时间，包含恢复期，顺序交换不改变合法性。 |
| P-07 | PASS | 按完整精确容量向量去重，保留原组合映射。 |
| P-08 | PASS | 23 期最长路径与 97 期末由 Gate 3.6 证据复核。 |
| P-09 | PASS | 一主两敏感性预注册，容量口径只影响尾窗。 |
| P-10 | PASS | 标准恢复指标及附带 KPI 沿用 V3.3，无新增目标。 |
| P-11 | PASS | 缺失经济项明确标为 `MISSING / NOT_INCLUDED`。 |
| P-12 | PASS | 档位来源与选择规则固定，生成器为静态代码，正式优化调用为零。 |

三种尾窗下，Γ=0、1、2 的原始／合法／去重后场景数依次为 `1/1/1`、`11/11/11`、`56/51/51`。Γ=2 各剔除五对同资产不同档位组合。预算上界和响应断点留待有授权的后续流程。 [静态审计 JSON](../experiments/configs/v33_formal_risk_static_audit.json) · [精确轨迹映射](../experiments/configs/formal_scenario_dedup_map.csv)

`FORMAL_RISK_PROTOCOL_FROZEN = TRUE`，`READY_FOR_GATE4 = TRUE`。Gate 4 未执行。

```powershell
python -S -m experiments.configs.audit_v33_formal_risk_protocol
python -m pytest tests/test_v33_formal_risk_protocol.py -q
```
