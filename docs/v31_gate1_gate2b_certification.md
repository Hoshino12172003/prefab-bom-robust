# V3.1 Gate 1 与 Gate 2B 认证记录

| 检查 | 状态 | 当前证据 |
| --- | --- | --- |
| G1-01 来源数据与候选全集 | PASS | 作者原 XLSB 包含 28,049 个品项、49 个非车品项、28,000 个 VIN 和 11 条弧。从原表独立恢复出 91 个内部状态，与现有 loader 的键集完全相同。Gate 0 工作簿和同一键集的逐项对照仍为 BLOCKED。 |
| G1-02 精确聚合 | PASS | 逐 VIN 从原始 BOM 和需求恢复等价类。到期日、交付节点、完整 BOM 签名和成员集合均与 loader 一致。聚合前后均为 28,000，得到 1,286 组。 |
| G1-03 历史在途 | PASS | 按 `arrival = dispatch + lead` 独立映射 117 条历史发运记录。运营期开窗内的 67,739 单位到货逐键与现有 loader 一致。原始数量完整保留。V3.1 模型矩阵待核验。 |
| G1-04 缺失的 9 个库存表状态 | PASS | 已逐项识别，见下表。旧构造器中有 5 个状态未显式设置库存上限，该构造器直接用于本轮为 BLOCKED。 |
| G1-05 逐行平衡残差 | NOT_TESTED | 需取得 V3.1 规格并求解。 |
| G1-06 来源 BOM | PASS | Pack 三种电芯投入分别为 10、6、4。四种 Seat 逐 SKU 对应一种组件且比例 1:1。Engine 和 Gear 来源操作为同 SKU 1:1，未引入子 BOM。车辆 BOM 与所有组签名一致。 |
| G1-07 容量 | NOT_TESTED | 原表与 loader 的弧能力、产品上限、组上限及 82 条库存界限已逐键匹配。求解后分类型违约审计待执行。 |
| G1-08 全局最优、整数性、求解日志及模型 | BLOCKED | 数值求解依赖最终 V3.1 规格。Python 3.12.7 和 Gurobi 13.0.1 的许可证环境可启动。无本轮正式目标值、上下界、gap 或残差。 |
| G2B-01 准备期模型 | BLOCKED | 尚缺最终规格中准备期名义能力映射、起始状态以及可用物料的定义。 |
| G2B-02 时间阈值源数据交叉检查 | PASS | 从外部投入节点出发的完整 BOM 路径在 H=1、2、4、20、21、22、23 累计可达 29、66、74、77、78、79、91 个状态。此检查仅传播工艺提前期。 |
| G2B-02 数量阈值和 G2B-03 `Bmax` | NOT_TESTED | 暂无准备期 MILP 及相应最优性证据。 |
| G2B-04 gross 和 residual 量 | BLOCKED | XLSB 仅提供 t=61–74 的逐期弧能力，没有 t=60 前的准备期能力、正常业务计划及同期占用。Gate 1 的 t=61–74 名义运营结果无法直接证明 t=60 之前的剩余能力。 |

## 9 个不在原始库存表中的内部状态

| 节点 | 物料 | Gate 1 库存上限 |
| --- | --- | --- |
| `battery-supplier_inv` | `BEV` | 0 |
| `seat-supplier_inv` | `Q1A`, `Q2J`, `Q4H`, `Q4P` | 各 0 |
| `zp7` | `Q1A`, `Q2J`, `Q4H`, `Q4P` | 各 0 |

旧 V3 构造器只显式将 `zp7` 的四个 Seat 设为零库存。库存表中缺失的另外 5 个状态在旧构造器中缺少有限库存上界。当前分支只增加读取及核对代码，原始数据、正式模型和历史结果文件保持原样。

## 缺失的权威材料

- `V3.1_Final_Mathematical_Specification_全BOM鲁棒缓冲配置模型.docx`。当前附件只有验收指令，本机找到的规格为标注含不确定事项的 V3 v0.1。
- `V3.1_Gate0_Gate2_Certification_Audit.xlsx`。本机找到的是 V3 的 49 物料与 91 位置初审表。
- `v31_gate1_nominal_certification.py`。找到旧 V3 的基模构造器，等价性需依最终规格审核。

原始 `2020_dataset_OfAutomotiveProductionNetwork.xlsb` 已从作者发布页下载并验证，SHA-256 为 `1ea0bcdea3225d308be913c9ca0f377585e1863847c78d6e8eec10b6de82889e`。 [作者数据页](https://data.mendeley.com/datasets/pr3sdy5vp3/1)

## 可复现证据

在仓库根目录以安装了 `gurobipy` 和 `pyxlsb==1.0.10` 的环境运行。来源工作簿由调用方提供本机路径。

```powershell
$env:PYTHONPATH = 'src'
python experiments/v31_gate1_gate2b_certification/source_preflight.py '原始XLSB完整路径' --out experiments/v31_gate1_gate2b_certification
```

实跑来源预检和 Python 语法检查退出码均为 0。[来源预检 JSON](../experiments/v31_gate1_gate2b_certification/source_preflight.json) 记录输入哈希、基础提交、预检脚本哈希、环境和耗时。[逐状态交叉检查 CSV](../experiments/v31_gate1_gate2b_certification/gate2b_reachability_crosscheck.csv) 含 637 行，逐阈值汇总与 JSON 一致。`tests/test_v3_phase30_base.py` 的 5 项历史回归均通过，退出码 0，其中两个微型测试使用 Gurobi。回归时把已核验的原始工作簿封装到测试查找的 ZIP 路径。V3.1 正式求解次数为 0。

**Gate 1 和 Gate 2B 均为 BLOCKED。** 待取得权威输入、验证 Gate 1 的全局最优性和残差，并完成 Gate 2B 的数量形成性检查后再判定 Gate 3。
