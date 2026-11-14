# V2.5 冻结数学规格 v2：来源语义与时间适用范围

本规格只覆盖已冻结的第 61–74 期、原始需求和四条认证情景的六个回归实例。原 XLSB、风险轨迹、认证预算和既有数据文件保持原字节。`source_parameter_semantics.csv` 给出参数的单位语义、对象、时间范围及约束映射。上述三项语义缺一时，参数不具备进入正式规格的资格。 [参数语义表](../artifacts/v25_phase110_20261110_201422/source_parameter_semantics.csv) · [范围清单](../artifacts/v25_phase110_20261110_201422/scope_manifest.json)

## 1. 集合、日历与参数

- $T=\{61,\ldots,74\}$。12 节点、11 弧、出弧品项、操作、BOM 和配置来自公开 XLSB。生产能力、运输能力和订单日历限各自来源索引，不作周期延拓。
- $q_{a,p,t}^{\omega}$ 是弧 $a=(i,j)$ 在期 $t$ 发运的品项 $p$ 数量，$L_a$ 为原弧提前期。$I_{n,p,t}^{\omega}$ 是期末库存。$e_{n,p,t}^{\omega}$ 只在 `nodes_inflow` 允许的键创建。开放式流入变量属于 `MODEL_ADAPTATION`，外部供给量没有独立的逐期来源上限，仍受相应库存和下游弧约束。
- $g$ 是按交付节点、BOM、到期日 $d_g$ 和单位服务权重严格等价的订单组。$D_g$ 为组内 VIN 数，$y_{g,t}^{\omega}$ 为交付。28,000 VIN 聚成 1,286 组，含 BEV 3,003 辆。风险作用于共同的上游资源，计划流仅按部件 SKU 或组列示。源实例没有独立 VIN 权重、成本、优先级、限流或初始状态系数。
- 数量决策是非负整数。DE 共同服务下界 $\rho$ 是 $[0,1]$ 内连续变量。每个情景拥有自己的运营决策，第一阶段缓冲相同。

## 2. 容量和生产计划的不同约束

正式容量行直接使用原 XLSB 的 `capacity_c_ijt`：

$$
\sum_{p\in P_a} q_{a,p,t}^{\omega}\le C^{\mathrm{XLSB}}_{a,t}\,\gamma^{\omega}_{a,t}.
$$

每个合格出弧品项的系数是 1。$C^{\mathrm{XLSB}}_{a,t}$ 的单位是该弧的 **model flow-capacity units per period**。电芯上游弧的 2,058 是第 67、74 期三种组件共享的发运上限，余期为 0。该数值没有独立的实物包装换算依据。只有通过 SKU 齐套条件和 BOM 才能推导完整包上界。例如可用组件向量 $R$ 至多形成 $\min_i\lfloor R_i/a_i\rfloor$ 套，$a=(10,6,4)$。若只知道组件总量，则 $\lfloor(\sum_i R_i)/20\rfloor$ 是较松上界。

历史 `5/21` 行同比例写法已标为 `DEPRECATED_ALGEBRAIC_NORMALIZATION`。原论文表 7 的示例值仅作 `SOURCE_PAPER_CROSSCHECK`。正式表述为：“Computational capacities are taken from the published XLSB dataset. The values reported in Table 7 of the source paper are retained as a source-paper cross-check.” [原论文 Eq. (2)、表 7](https://www.researchgate.net/publication/343539617_Optimisation_model_for_multi-item_multi-echelon_supply_chains_with_nested_multi-level_products)

计划流表与弧容量并列，仅在各自源键存在时使用：

$$
q_{a,p,t}^{\omega}\le U^{\mathrm{prod}}_{a,p,t},\qquad
\sum_{p\in P_a}q_{a,p,t}^{\omega}\le U^{\mathrm{group}}_{a,t}.
$$

这是对原论文式（17）所示固定承诺形式的 `MODEL_ADAPTATION`。XLSB 的 `max_flow_*` 字段按上限执行，缺行没有额外的计划上限，既不补零也不补等式。已列的上限仅覆盖 engine/gear 生产弧第 61–70 期。D60 第 65 期 XLSB 上限是 22，论文示例等式为 40。二者无法按同一个数值承诺作逐行等同。 [计划流审计](../artifacts/v25_phase110_20261110_201422/planned_flow_semantics_audit.csv)

## 3. 配方、期末库存与历史流水

对异品项变换，当 `beta=1` 时使用 $a_{a,p,c}=q_{pc}/out$，不叠加 generic input。电池包生产只扣 `10/6/4` 三种组件，一次合计 20。XLSB 的 49 条 $m=c$ 单位行从制造 BOM 中排除。`operations` 中同组的 1∶1 移库关系由原操作字段生成，发运期扣起点的同一品项，到货期增加终点的同一品项。它是流量转移，原料转换配方不含自耗项。

期末库存等式如下，其中 $h$ 是窗前发运计算出的当期可用到货，$R$ 是本期及窗内较早发运的按期到货，$Y$ 是实际交付的库存扣减：

$$
I_{n,c,t}^{\omega}=I_{n,c,t-1}^{\omega}+h_{n,c,t}^{\omega}+e_{n,c,t}^{\omega}
+R_{n,c,t}^{\omega}-\sum_{a=(n,j),p}a_{a,p,c}q_{a,p,t}^{\omega}-Y_{n,c,t}^{\omega}.
$$

期 $t$ 发运只在 $t+L_a$ 到终点。电芯上游 20 期，电池包生产和到 OEM 各 1 期。发动机两弧各 1 期，齿轮两弧各 2 期，座椅材料上游 23 期，座椅生产及运送和 OEM 装配为 0 期。零提前期可同一期净额结转，本模型不进一步规定日内顺序。库存上下界仅在 `initial_inventories` 有相应字段的键使用，将其用于操作期属于 V2.5 的 `MODEL_ADAPTATION`。

第 60 期开盘状态由源库存加缓冲组成。缺失的键在冻结运行中由加载器补零，标为 `MISSING_NOT_ZERO_CERTIFIED`。来源缺行不能当成真实零库存证据。历史 `initial_flows` 记录为窗前的固定发运，按 `departure + L` 到货，范围可超过 74。不得使用未来容量倒验历史发运、缩放历史量或回写风险损失。L1 认证情景只在明确指定到货期改变可用比例，属于 **usable-arrival / quality-loss shock**。L2/L3 只影响各自发运弧当期容量 RHS。 [初始与历史语义](../artifacts/v25_phase110_20261110_201422/initial_state_semantics_audit.csv) · [逐弧提前期](../artifacts/v25_phase110_20261110_201422/lead_time_audit.csv)

## 4. 缓冲、成本和服务目标

$x_{\mathrm{cell\_kit}}$ 是 **balanced battery-cell-component buffer / kit-equivalent component buffer**。每单位在包厂开盘库存增加 `(10,6,4)`。T1 Pack 与 OEM Pack 分别在其库存节点每单位增加一个电池包。三个位置的系数和作用对象固定，当前变量无法独立决定三个 SKU 的配比。冻结预算约束为 $\sum_k c_k x_k\le B$。

$c_T=c_O=8756$ USD／包，OEM positioning premium 为零，全部只作 `CERTIFICATION_ONLY`。OEM 位置在同价下可能因路径较短和规避下游瓶颈而享有可达性优势。正式管理实验处于 `HOLD_FINAL_POSITION_COST_CALIBRATION`，须有外部成本依据或明确的区间敏感性设计才可解除。本阶段无新校准。

每组 $\sum_t y_{g,t}^{\omega}\le D_g$。名义目标最大化 $\sum_{g,t\le d_g} y_{g,t}/28000$。DE 最大化 $\rho$，并要求每个情景的同一服务分数不低于 $\rho$。到期前的交付计入服务，迟交可消耗库存但没有按期目标收益。该目标是 V2.5 的 `MODEL_ADAPTATION`。原论文的 order shortfall、rescheduling deviation、unassigned capacity 与库存／流量目标权重属于来源背景。

## 5. 执行和禁止外推

正式认证沿用 `OptimalityTol=1e-9`、零 MIP 间隙、严格预算、独立物料上界及可行见证。第 61–74 期的源日历不能推导 $c_{t+14}=c_t$。55 期 settling time 只属于来源的数据生成仿真。Phase 1.8 是实验诊断，Phase 1.9 当前解释为 `HOLD_LONG_RUN_EXTRAPOLATION_UNSUPPORTED`。860 的物理单位和第 59 期生产状态仍未识别，正式状态为 **`SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED`**。
