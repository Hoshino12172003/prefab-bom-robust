# V3 Phase 3.2D-2 多 BOM 不确定性证据与 Γ 审计

**结论** `HOLD_GAMMA_SEMANTICS_CONFLICT`

冻结模型按活跃资源日计 Γ。将核心时长设为 4、7、11 日，并要求 Γ∈{2,4,6} 时，7 和 11 日均超预算，任意两个核心事件至少需要 8 个资源日。即使把时长网格解释为筛选前的候选域，筛选后仍没有联合多分支事件。第 F 项因此触发停止。 [Γ 语义、公式及边界测试](../artifacts/v3_phase32d2_20261112_132513/gamma_semantics_audit.md)

## 外部事件与适用范围

- **Aisin，1997-02-01。** 现场访谈研究记录 P-valve 产能几乎全失、2–3 日 JIT 库存和 Toyota 大范围停线。火灾后第 5 日已有两厂重开，第 6 日开始收到协作供应商的合格阀件，第 9 日集团工厂回到灾前产量。用数日级整车复产及替代生产作为量级与机制依据。 [东京大学现场研究，第 4、11 页](https://merc.e.u-tokyo.ac.jp/mmrc/dp/pdf/MMRC433_2013.pdf)
- **Toyota/Aichi Steel，2016-01-08。** 知多厂事故造成零件短缺，Toyota 日本整车装配线 2 月 8–13 日停产并于 2 月 15 日复工。厂方和整车厂公告支持事故、停线和复工日期，行业协会报道补充发动机、变速箱、底盘的专用钢用途。该时间线支持周级整车停线，钢厂本身的修复时间须单独计量。 [Aichi Steel 事故公告](https://www.aichi-steel.co.jp/ENGLISH/news_item/topics20160122-3.pdf) · [Toyota 复工确认](https://global.toyota/en/detail/11138722) · [AIST 材料用途](https://www.aist.org/japanese-steelmaker-restarts-damaged-bar-mill)
- **Ford/Meridian，2018-05-02。** 镁合金件供应商火灾后，Ford 将模具修复并转移至替代地点。Ford 报告 Dearborn F-150 停线略逾一周并安排 5 月 18 日复产，当地报道援引 Ford 当日确认复产。该观察仅适用于 Dearborn F-150 产线。 [Ford 公告的 SEC 附件](https://www.sec.gov/Archives/edgar/data/37996/000003799618000047/exhibit99to516188k.htm) · [当日复产报道](https://www.clickondetroit.com/automotive/2018/05/18/ford-says-f-150-truck-production-is-back-on-line-at-dearborn-truck-plant/)
- **Renesas Naka，2021-03-19。** N3 线 4 月 17 日恢复生产，5 月底产能约为灾前的 88%，6 月 24 日回到灾前水平。7 月 29 日电话会称出货量仍约为灾前的 90%。证据支持跨规划窗口的持续中断、渐进恢复以及产能与出货时点的差异。 [Renesas 产能公告](https://www.renesas.com/en/about/press-room/update-9-notice-regarding-semiconductor-manufacturing-factory-naka-factory-fire-production-capacity) · [季度报告](https://www.renesas.com/en/document/rep/earnings-report-2nd-quarter-ended-june-30-2021?ir_ts=1714754334656) · [电话会纪要](https://www.renesas.com/en/document/ppt/2021-2q-presentation-minutes-and-qa)

四起事件用作外部量级和恢复机制证据。Quetschlich 工作簿和历史开窗另有出处。外部事件无法识别 Volkswagen/Quetschlich 的历史中断参数、变速箱或座椅的发生概率及分支相关性。 [逐来源证据表](../artifacts/v3_phase32d2_20261112_132513/external_disruption_evidence.csv) · [Quetschlich 公开数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1)

## 参数证据

| 参数 | 证据等级及适用范围 |
|---|---|
| 14 期窗口 | `SOURCE_CASE`，使用第 61–74 期历史开窗 |
| 25%、50%、75% | `STANDARDIZED_STRESS_LEVEL`，分别为中度、较大和严重的部分损失 |
| 100% | `SENSITIVITY_ONLY`，仅在 `EXTREME_SENSITIVITY` 设计中使用 |
| 4、7、11 日 | `EXTERNAL_INCIDENT_ANCHORED`，分别表示短时、约一周、接近窗口尺度的持续中断。档位以 14 期窗口为尺度，无事件分布分位数估计 |
| `ABRUPT_RECOVERY` | `EXTERNAL_INCIDENT_ANCHORED`，快速恢复仅锚定机制。沿用既有规则，活跃期结束后恢复至正常比例 |
| `GRADUAL_RECOVERY` | `SENSITIVITY_ONLY`，沿用既有两步尾部 \(1-2s/3,1-s/3,1\)，无 Renesas 曲线拟合 |
| Γ∈{2,4,6} | `SENSITIVITY_ONLY`，用途为 `ROBUSTNESS_SENSITIVITY`，无真实 Γ 概率分布估计 |

冻结资源日使用单位计数。分支权重、起始概率及相关性标为 `UNCALIBRATED`。本轮没有引入分支权重或更改预算、时长。 [完整参数分类](../artifacts/v3_phase32d2_20261112_132513/parameter_evidence_classification.csv)

## 实际核验范围

使用原验证器执行 14 个回归用例，全部通过。D-1 的 287,443 条轨迹及 38,527 个有效 RHS 对应冻结的电池链，时长为 1、3、5 日。数值作为经哈希核验的历史证据引用，本轮生成的多 BOM 轨迹和 Gurobi 优化调用均为 0。第 H–W 项尚无本轮运行证据。 [机器审计](../artifacts/v3_phase32d2_20261112_132513/audit.json) · [测试日志](../artifacts/v3_phase32d2_20261112_132513/pytest.txt) · [停止记录](../artifacts/v3_phase32d2_20261112_132513/implicit_separation_gate.md)
