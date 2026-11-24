# V3 标准化数据层验收报告

日期：2026-11-23。仓库 `D:/chatgpt/供给侧BOM/prefab-bom-robust`。数据目录 `experiments/scenario_agent_v1/data/v3/`。

## 1. 身份与边界

model_instance_id为：

`v3-063f9d24e1c1a6ba5c57978d02402520059aa7b83aedf720078b1363cad5327d`

由V3源XLSB、规范化模型规格、历史构造和配置文件的固定SHA-256内容寻址产生。Git HEAD为`02143f46cab6e6a173a0f495e21b20d21311096f`；由于原工作树含未提交内容，另保存实际文件摘要，不能只用HEAD代表代码版本。

ZIP SHA-256：`dec8343a2c63f434452efc3e9ec31fac2f81f508b77baeb9a80b3b8035595ed5`。XLSB SHA-256：`1ea0bcdea3225d308be913c9ca0f377585e1863847c78d6e8eec10b6de82889e`。

使用V3历史61–74期、原容量/库存与三缓冲政策、ABRUPT风险、最坏准时交付目标。V3.3准备过程、91维政策、库存池、75–97期尾窗、积压和成本没有用于替代V3数据。本次没有导入或运行Gurobi，也没有训练模型、拟合正式预处理器或接入C&CG。

## 2. 数据层与数量

| 文件 | 粒度 | 行数/验收结果 |
|---|---|---:|
| network_nodes_v3.csv | 物理地点 | 12 |
| network_arcs_v3.csv | 物理主要弧 | 11 |
| arc_periods_v3.csv | 弧×时期；含额外流量上限 | 154 |
| bom_relations_raw.csv | 原mother/child关系 | 87059 |
| bom_recipes_v3.csv | 编译后的(arc,output)配方 | 1377 |
| bom_recipe_inputs_v3.csv | 配方投入项，精确分子/分母 | 3979 |
| scenario_catalog_v3.csv | 名称情景及原始事件/有效签名 | 40名称、38有效RHS |
| master_snapshots_v3.csv | run×iteration的Oracle前状态 | 33 |
| oracle_calls_v3.csv | 实际分离查询 | 576 |
| oracle_labels_v3.csv | 同查询的精确目标与排序标签 | 576 |
| sample_manifest_v3.csv | 主键/来源/重复组合关联 | 576 |

另交付source_workbook_v3.json，无损保留12表的列名及所有原始行；preprocessing_contract_v3.json明确unfitted；feature_manifest_v3.json保存源文件、25份历史JSON、实现代码和所有数据输出的摘要、单位、字段顺序与公式。

49条自身约定保留原始BOM行号、is_identity_convention及exclude_manufacturing_self_loop处理记录。制造图排除这些自环后通过DAG检查；运输同SKU1:1配方继续保留，不误删为自耗回路。历史编译函数在固定哈希后仅执行纯数据定义及编译函数，未执行模型构造。

## 3. 12张XLSB工作表映射

所有12表都原样保存在source_workbook_v3.json，columns给原列名，tables给原顺序行。标准CSV中的source_row为Excel行号，从2开始。

| 源表 | 标准层位置和字段映射 |
|---|---|
| products | source_workbook；product_p→SKU ID，group_g→arcs.output_group/recipes.output_group，size保留原值；cohort输出通过original_mother_ids_json回溯VIN |
| nodes | network_nodes.node_id；节点角色、in/out_degree由原拓扑派生 |
| nodes_inflow | nodes.external_skus_json，另完整保留资格表；不是补货数量 |
| arcs | network_arcs：starting/ending→origin/destination，lead→lead_periods，group→output_group |
| capacity_at_arc | arc_periods：period_t→period，capacity→capacity，来源行完整保留 |
| max_flow_product_per_arc | arc_periods.product_flow_caps_json按SKU保留planned_flow；缺项无额外上限，不是0容量 |
| max_flow_group_per_arc | arc_periods.group_flow_cap及has_group_flow_cap；不能与原capacity相加 |
| operations | recipes.source_operation_rows_json及纯编译规则；输入/输出组和alpha/beta在source_workbook保留 |
| BOM | bom_relations_raw保存全部行；recipes.source_bom_rows_json及inputs系数建立原始→编译映射 |
| demands | 原VIN/due全量保存在source_workbook，compiled cohort在recipes.original_mother_ids_json保持成员对应；图暴露按订单数及due计算 |
| initial_inventories | 原82条及上下界保存在source_workbook；源编译器生成完整状态基底，默认0不冒充原始记录 |
| initial_flows | 原117条保存在source_workbook；按dispatch+lead恢复106个V3窗口内到货键，用于风险RHS复核 |

Network类没有nodes属性；12地点从源nodes表获取。1421个完整状态与91个内部非整车状态仍是不同粒度，不能混成地点数。

## 4. 历史状态与标签

读取A9份、B16份原始n*.json，逐一与原归档清单SHA-256匹配；仅选evaluation/tag=oracle_XX。Master/Verify/Direct/Pilot不进入首选样本。

每行保留oracle_call_id、run_id、master_state_id、effective_rhs_id、policy_rhs_id、source_file_sha256、json_pointer和原日志路径。run_id基于源相对路径+原字节摘要；call_id基于原文件身份+JSON数组指针，重复运行不合并。

33个完整组共576条。322条首轮LB保持空CSV单元格+lb_initialized=false；254条使用前轮已认证lower。UB取本轮已解Master。不会将本轮Oracle完成后的lower写入预测输入。

148个policy/RHS组合保留原调用，sample_manifest记录组合重复次数，不能当576个独立监督样本或多个网络。已检验重复组合的精确Q无冲突。所有40风险名称均核验有效签名；ES/GS分别映射对应代表，原名称保留。

oracle_labels独立保存Q、并列最坏、dense rank、严格违反、总服务缺口和有名义基准时的中断损失。356条具备同轮同政策NR基准，另220条disruption_loss为空。B的best_bound/gap来自固定代码强制精确相等断言，标derived_from_pinned_exact_assertion；A标direct，来源不混淆。

## 5. 单位、原始与转换值

数量按原SKU/产品组单位，car为辆，Pack为包，C为完整电芯套件。BOM系数为input_sku_unit/output_sku_unit，分子/分母精确保留。容量为对应输出组单位/期；初始库存和历史发运按SKU计。不同SKU/组数量不跨单位直接加总。

时间为period/period_index，不擅自标小时。V3预算使用规范化投资单位，成本(1,27/19,297/190)，预算17388/19，剩余精确分数保留在CSV；提取器才转数值。收货期=发运期+lead；有效风险量=floor(nominal×(1−severity_loss))。

CSV布尔为true/false、NULL为空单元格、嵌套数组为JSON、分数为精确字符串。ID/哈希/指针只关联，不作为连续特征。9个缺原库存行状态采用原代码默认0，保留来源层与实现哈希，不声称原Excel实测0。成本/库存暴露等未记录项不生成伪数据。

## 6. 复现和下一阶段

在仓库根目录执行，输出路径必须不存在，以保护既有产物：

```powershell
$env:PYTHONPATH='src'
python -B -m scenario_agent.v3_feature_extractor.build --source-zip 'E:\文献阅读\论文写作\prefab\数据\Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip' --out experiments/scenario_agent_v1/data/v3_new_run
```

所有哈希/关联/数量检查在写出前执行，冲突抛错停止，不自动修补或覆写。当前交付目录已通过输出和代码摘要复核。

结论：BOM完整恢复，576条查询完整关联，40名称完整映射到38RHS；可以进入正式训练集构建阶段。仍需另行冻结训练/验证拆分与预处理fit范围；本次未生成最终X/y矩阵，没有训练性能或泛化结论。
