# V3 全 BOM 状态转换审计

## 数据及口径

原始 XLSB 有 28,049 个品项、12 个节点、11 条弧、15 条 operation 和 87,059 条 BOM 记录。49 条 BOM 自指行系数均为 1，不作为制造投入。同品项的生产状态转移与运输由 operation 和弧恢复。XLSB 的汽车实例所有 `alpha` 为 0。生产和运输容量均按弧共享，CSV 的每条依赖边重复显示该弧容量，不能按边相加。 [源数据](https://data.mendeley.com/datasets/pr3sdy5vp3/1) · [转换图](v3_state_transition_graph.csv)

每条边由原始投入 SKU、投入节点、产出 SKU 和产出节点确定。投入与产出数量按单单位产出计。对 VIN 重新展开并逐项与源 BOM 比较，保留了 28,000 VIN、104 个完整 BOM 签名、1,286 个含到期日的等价组。图含 115,096 条边，其中 87,003 条是整车投入边，93 条是其他弧的投入或移库边，28,000 条是 VIN 出库边。最后一类来自 `zp8` 和 `demands`，没有创建客户运输弧。 [V3 配方编译](../src/prefab_v3/base.py#L15) · [分组键](../src/prefab_v25/data.py#L40)

| 分支 | 源模型状态与工艺 | 源提前期 |
|---|---|---|
| Battery | 三 SKU 由 T2 发运到 T1 生产节点。每个 Pack 必须投入 Cell1/2/3 的 10/6/4。其后是 T1 成品态和 OEM Pack 态 | 20 + 1 + 1 |
| Seat | 四 SKU 的上游组件发往座椅生产。每个成品 Seat 只消耗对应的一件组件，产出到供应商库存节点，再同 SKU 运往 OEM | 23 + 0 + 0 |
| Engine | 29 个同 SKU 从生产节点进入成品库存，再运往 OEM。源外采资格在生产节点，公开表没有零件级装配树 | 1 + 1 |
| Gear | 8 个同 SKU 从生产节点进入成品库存，再运往 OEM。源外采资格在生产节点，公开表没有附加加工层 | 2 + 2 |
| Vehicle | 每 VIN 恰好一件指定发动机、一件指定变速箱和一件指定座椅。3,003 个 BEV 还需要一件 Pack。按 VIN 配方生产后才可出库 | 总装为 0 |

实际编译的 Battery 包输入为 10/6/4。通用 operation 行的 20 不再作为额外投入。Seat 为 Q2J←componment_seat1、Q4H←componment_seat2、Q4P←componment_seat3、Q1A←componment_seat4。校验逐 VIN 保留各 SKU，不把同组替代。原始模型对 `beta=1` 以个别 BOM 数量取代通用投入。 [原论文](https://doi.org/10.1016/j.ejor.2020.08.005) · [配方校验脚本](v3_inventory_audit.py)

## 守恒与时序

沿弧发出一单位产出时，在发出期扣除配方投入，在发出期加提前期时增加对应产出。运输扣除和增加的是同一 SKU。0 日 lead 支持同一期制造、配送、装配，资料没有日内顺序，不能认证风险揭示前几小时内一定有可用槽位。窗前流水只按原 lead 到货一次。OEM Seat 的期末库存零约束来自源案例的 JIT/JIS 设定。 [模型流量与库存等式](../src/prefab_v3/base.py#L163) · [历史到货](../src/prefab_v25/data.py#L125)

原始计划表分别含 Engine 和 Gear 生产弧产品及组的上限，D4 未把它们接成固定排程。Seat 没有固定生产计划行。记录中没有可用于反推多一级发动机或变速箱零件库存的资料。
