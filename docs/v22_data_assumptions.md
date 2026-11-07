# V2.2 数据审计与假设

## 编码前六项审计

| 问题 | V2.1 实际结构与本次处理 |
|---|---|
| 是否有工序1 BOM | 已有 A1、A2、A，逐项验证 A1+A2=A。继承现有合成划分 |
| 风险前地点有无组件 | lots 中 kind=I、index=(j,a) 为实际厂内期初组件。新增采购 x 在原模型中已定义为风险前到位 |
| x 能否用于预装配 | 可以，按原定义。available_before_risk=False 时拒绝该预装配输入 |
| 已有 WIP 如何计订单 | Wa 为配置专用厂内 WIP，经工序2和实际交付进入 D 的平衡。p 上限扣除现有 Wa。Wo/PW 继续由各自原有流平衡管理 |
| 是否有风险前能力数据 | 无企业实测值。采用明示合成 P_pre 和 tau_pre，示例单位能力为1 |
| 是否有 WIP 存放容量数据 | 无企业实测值。新增合成 Wcap_pre、v_WIP，只限制风险开始前的厂内 WIP |

真实备用资格、工艺路线、容量和采购到位时间仍需要业务来源支持。所有新增示例都是 D 级合成数据。

## 单位和验证

- p、Winit、W0post 为配置 product-unit，Ipre/x 为 component-unit。
- A1 为 component-unit / product-unit。tau_pre 为 pre-work-unit / product-unit，P_pre 为 pre-work-unit。
- v_WIP 为 WIP-space-unit / product-unit，Wcap_pre 为 WIP-space-unit。
- c_preasm、h_preWIP 为 currency / product-unit。h_preWIP 对风险前准备区间一次计费，窗口内持有费另按 period 计。
- 参数按完整产品索引逐项给出。数量、容量和费用有限非负，能力与空间消耗系数严格正。已有 Wa 必须可放入 Wcap_pre。

模型不从“在第1期到达”的在途量借用风险前物料，也不把外协 WIP 默认搬入厂内。实物批次 ID 和 V2.1 去重逻辑保留。

## 微型参数

扩展沿用 V2.1 的4期、正跨节点提前期、两工序 A/B、风险预算 Gamma2=0.5、Gamma3=1、GammaO=0.5，共12个极点。tau_pre=v_WIP=1。新风险前加工费常用0.2，准备区间持有/处理费0.05，高成本例加工费10。

三个例子分别展示已有工序1能力充足、风险后工序1完全不可用、以及两种配置竞争唯一一单位风险前通用组件。第三例保留正的 B 新增库存上限2，供库存与备用策略对照，A 的新增上限为0，以明确检验通用组件的锁定效应。

上述参数用于可手算验证，未作为真实设备成本或产能标定。原两组 V2.1 认证例回归时仅增加显式的预装配参数并固定 p=0。
