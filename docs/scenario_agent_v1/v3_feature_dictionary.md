# V3 统一特征字典

特征版本：`v3.features.1.0.0`。实现目录：`src/scenario_agent/v3_feature_extractor/`。本字典由当前 `extractor.SPECS` 逐项读取生成，顺序与接口输出、feature_manifest_v3.json严格一致，共84个原始数值字段：网络7、风险57、Master10、交互10。

所有字段信息时点固定为 `after_master_before_oracle`。int64表示Python整数（布尔特征编码0/1），float64表示有限数值；NULL表示不适用或尚未初始化，不把NULL写成原始0。输出版本和model_instance_id在FeatureVectorV3元数据中，不作为数值特征。

| 序号 | 固定字段名 | 类型 | 单位 | 可NULL | 公式 | 来源 |
|---:|---|---|---|---|---|---|
| 1 | network_nodes | int64 | location_count | 否 | len(nodes) | XLSB + pinned source_base |
| 2 | network_arcs | int64 | arc_count | 否 | len(arcs) | XLSB + pinned source_base |
| 3 | network_recipes | int64 | recipe_count | 否 | sum(len(arc.recipes)) | XLSB + pinned source_base |
| 4 | network_recipe_inputs | int64 | input_term_count | 否 | sum(len(recipe)) | XLSB + pinned source_base |
| 5 | network_order_count | int64 | vehicle | 否 | sum(cohort sizes) | XLSB + pinned source_base |
| 6 | network_configuration_count | int64 | configuration_count | 否 | distinct direct BOM signatures excluding due | XLSB + pinned source_base |
| 7 | network_horizon | int64 | period | 否 | len(periods) | XLSB + pinned source_base |
| 8 | scenario_event_count | int64 | event_count | 否 | len(raw_events) | raw_events |
| 9 | scenario_changed_rows | int64 | RHS_row_count | 否 | len(integer changes) | verified signature |
| 10 | scenario_is_nominal_rhs | int64 | boolean | 否 | integer signature is empty | verified signature |
| 11 | risk_B_RECEIPT_present | int64 | boolean | 否 | resource in events | raw_events + original capacity/receipts |
| 12 | risk_B_RECEIPT_severity_loss | float64 | fraction | 是 | event severity loss | raw_events + original capacity/receipts |
| 13 | risk_B_RECEIPT_start_offset | int64 | period | 是 | start-61 | raw_events + original capacity/receipts |
| 14 | risk_B_RECEIPT_duration | int64 | period | 是 | duration | raw_events + original capacity/receipts |
| 15 | risk_B_RECEIPT_changed_rows | int64 | RHS_row_count | 否 | effective changed rows of resource | raw_events + original capacity/receipts |
| 16 | risk_B_RECEIPT_mean_effective_loss_rate | float64 | fraction | 是 | mean((nominal-effective)/nominal) over changed positive-nominal rows | raw_events + original capacity/receipts |
| 17 | risk_B_PROD_present | int64 | boolean | 否 | resource in events | raw_events + original capacity/receipts |
| 18 | risk_B_PROD_severity_loss | float64 | fraction | 是 | event severity loss | raw_events + original capacity/receipts |
| 19 | risk_B_PROD_start_offset | int64 | period | 是 | start-61 | raw_events + original capacity/receipts |
| 20 | risk_B_PROD_duration | int64 | period | 是 | duration | raw_events + original capacity/receipts |
| 21 | risk_B_PROD_changed_rows | int64 | RHS_row_count | 否 | effective changed rows of resource | raw_events + original capacity/receipts |
| 22 | risk_B_PROD_mean_effective_loss_rate | float64 | fraction | 是 | mean((nominal-effective)/nominal) over changed positive-nominal rows | raw_events + original capacity/receipts |
| 23 | risk_B_SHIP_present | int64 | boolean | 否 | resource in events | raw_events + original capacity/receipts |
| 24 | risk_B_SHIP_severity_loss | float64 | fraction | 是 | event severity loss | raw_events + original capacity/receipts |
| 25 | risk_B_SHIP_start_offset | int64 | period | 是 | start-61 | raw_events + original capacity/receipts |
| 26 | risk_B_SHIP_duration | int64 | period | 是 | duration | raw_events + original capacity/receipts |
| 27 | risk_B_SHIP_changed_rows | int64 | RHS_row_count | 否 | effective changed rows of resource | raw_events + original capacity/receipts |
| 28 | risk_B_SHIP_mean_effective_loss_rate | float64 | fraction | 是 | mean((nominal-effective)/nominal) over changed positive-nominal rows | raw_events + original capacity/receipts |
| 29 | risk_ENGINE_present | int64 | boolean | 否 | resource in events | raw_events + original capacity/receipts |
| 30 | risk_ENGINE_severity_loss | float64 | fraction | 是 | event severity loss | raw_events + original capacity/receipts |
| 31 | risk_ENGINE_start_offset | int64 | period | 是 | start-61 | raw_events + original capacity/receipts |
| 32 | risk_ENGINE_duration | int64 | period | 是 | duration | raw_events + original capacity/receipts |
| 33 | risk_ENGINE_changed_rows | int64 | RHS_row_count | 否 | effective changed rows of resource | raw_events + original capacity/receipts |
| 34 | risk_ENGINE_mean_effective_loss_rate | float64 | fraction | 是 | mean((nominal-effective)/nominal) over changed positive-nominal rows | raw_events + original capacity/receipts |
| 35 | risk_GEAR_present | int64 | boolean | 否 | resource in events | raw_events + original capacity/receipts |
| 36 | risk_GEAR_severity_loss | float64 | fraction | 是 | event severity loss | raw_events + original capacity/receipts |
| 37 | risk_GEAR_start_offset | int64 | period | 是 | start-61 | raw_events + original capacity/receipts |
| 38 | risk_GEAR_duration | int64 | period | 是 | duration | raw_events + original capacity/receipts |
| 39 | risk_GEAR_changed_rows | int64 | RHS_row_count | 否 | effective changed rows of resource | raw_events + original capacity/receipts |
| 40 | risk_GEAR_mean_effective_loss_rate | float64 | fraction | 是 | mean((nominal-effective)/nominal) over changed positive-nominal rows | raw_events + original capacity/receipts |
| 41 | risk_SEAT_present | int64 | boolean | 否 | resource in events | raw_events + original capacity/receipts |
| 42 | risk_SEAT_severity_loss | float64 | fraction | 是 | event severity loss | raw_events + original capacity/receipts |
| 43 | risk_SEAT_start_offset | int64 | period | 是 | start-61 | raw_events + original capacity/receipts |
| 44 | risk_SEAT_duration | int64 | period | 是 | duration | raw_events + original capacity/receipts |
| 45 | risk_SEAT_changed_rows | int64 | RHS_row_count | 否 | effective changed rows of resource | raw_events + original capacity/receipts |
| 46 | risk_SEAT_mean_effective_loss_rate | float64 | fraction | 是 | mean((nominal-effective)/nominal) over changed positive-nominal rows | raw_events + original capacity/receipts |
| 47 | risk_reachable_skus | int64 | SKU_count | 否 | distinct non-car SKU reachable by 74 | V3 recipe graph |
| 48 | risk_reachable_orders | int64 | vehicle | 否 | sum(cohort sizes reachable before due) | V3 recipe graph + due |
| 49 | risk_reachable_configs | int64 | configuration_count | 否 | distinct BOM of exposed cohorts | V3 BOM |
| 50 | risk_first_delivery_period | int64 | period_index | 是 | min potential arrival among exposed cohorts | V3 recipe graph + due |
| 51 | risk_due_61 | int64 | boolean | 否 | any exposed cohort due=61 | V3 demand + graph |
| 52 | risk_due_62 | int64 | boolean | 否 | any exposed cohort due=62 | V3 demand + graph |
| 53 | risk_due_63 | int64 | boolean | 否 | any exposed cohort due=63 | V3 demand + graph |
| 54 | risk_due_64 | int64 | boolean | 否 | any exposed cohort due=64 | V3 demand + graph |
| 55 | risk_due_65 | int64 | boolean | 否 | any exposed cohort due=65 | V3 demand + graph |
| 56 | risk_due_66 | int64 | boolean | 否 | any exposed cohort due=66 | V3 demand + graph |
| 57 | risk_due_67 | int64 | boolean | 否 | any exposed cohort due=67 | V3 demand + graph |
| 58 | risk_due_68 | int64 | boolean | 否 | any exposed cohort due=68 | V3 demand + graph |
| 59 | risk_due_69 | int64 | boolean | 否 | any exposed cohort due=69 | V3 demand + graph |
| 60 | risk_due_70 | int64 | boolean | 否 | any exposed cohort due=70 | V3 demand + graph |
| 61 | risk_due_71 | int64 | boolean | 否 | any exposed cohort due=71 | V3 demand + graph |
| 62 | risk_due_72 | int64 | boolean | 否 | any exposed cohort due=72 | V3 demand + graph |
| 63 | risk_due_73 | int64 | boolean | 否 | any exposed cohort due=73 | V3 demand + graph |
| 64 | risk_due_74 | int64 | boolean | 否 | any exposed cohort due=74 | V3 demand + graph |
| 65 | master_iteration | int64 | iteration_count | 否 | iteration_id | MasterStateV3 |
| 66 | buffer_C | int64 | complete_cell_kit | 否 | policy[0] | MasterStateV3 |
| 67 | buffer_T | int64 | Pack | 否 | policy[1] | MasterStateV3 |
| 68 | buffer_O | int64 | Pack | 否 | policy[2] | MasterStateV3 |
| 69 | master_active_count | int64 | RHS_count | 否 | len(active_rhs_ids) | MasterStateV3 |
| 70 | master_budget | float64 | normalized_investment | 否 | 17388/19 | MasterStateV3 |
| 71 | master_remaining_budget | float64 | normalized_investment | 否 | budget-sum(cost[i]*policy[i]) | MasterStateV3 |
| 72 | master_ub | int64 | vehicle | 否 | current exact Master upper | MasterStateV3 |
| 73 | master_lb_before | int64 | vehicle | 是 | previous certified lower; first round NULL | MasterStateV3 |
| 74 | master_lb_initialized | int64 | boolean | 否 | lb_before is not NULL | MasterStateV3 |
| 75 | scenario_already_active | int64 | boolean | 否 | scenario.RHS in active RHS | scenario + Master |
| 76 | buffer_C_timed_exposed_orders | int64 | vehicle | 否 | exposed cohorts intersect cohorts reachable from buffer at 61 before due | V3 recipes/lead + events + policy |
| 77 | buffer_C_units_per_exposed_order | float64 | Pack_equivalent_per_vehicle | 是 | buffer quantity / timed exposed orders; no feasibility claim | V3 recipes/lead + events + policy |
| 78 | buffer_C_bypassed_battery_resources | int64 | resource_count | 否 | count present battery risks at or upstream of buffer injection | V3 recipes/lead + events + policy |
| 79 | buffer_T_timed_exposed_orders | int64 | vehicle | 否 | exposed cohorts intersect cohorts reachable from buffer at 61 before due | V3 recipes/lead + events + policy |
| 80 | buffer_T_units_per_exposed_order | float64 | Pack_equivalent_per_vehicle | 是 | buffer quantity / timed exposed orders; no feasibility claim | V3 recipes/lead + events + policy |
| 81 | buffer_T_bypassed_battery_resources | int64 | resource_count | 否 | count present battery risks at or upstream of buffer injection | V3 recipes/lead + events + policy |
| 82 | buffer_O_timed_exposed_orders | int64 | vehicle | 否 | exposed cohorts intersect cohorts reachable from buffer at 61 before due | V3 recipes/lead + events + policy |
| 83 | buffer_O_units_per_exposed_order | float64 | Pack_equivalent_per_vehicle | 是 | buffer quantity / timed exposed orders; no feasibility claim | V3 recipes/lead + events + policy |
| 84 | buffer_O_bypassed_battery_resources | int64 | resource_count | 否 | count present battery risks at or upstream of buffer injection | V3 recipes/lead + events + policy |

## 结构与交互的解释边界

- reachable采用从任一投入传播的潜在影响路径，表示风险可能沿BOM到达，不是多投入AND物料平衡的充分条件；不用于剪枝或服务认证。
- risk_reachable_orders按1286个cohort的实际订单数加权，必须到达日期≤该cohort due；不是受扰必然损失订单数。
- buffer_C/T/O_timed_exposed_orders分别从生产端完整套件、T1 Pack、OEM Pack在第61期注入的位置出发，按原lead计算与风险暴露组的交集；这是结构支持订单数，不计容量竞争、真实缺货或排程。
- C套件固定为10/6/4三种电芯；以任一电芯的相同时序路径表示完整套件的物料路径，前提由原配方哈希及10/6/4测试锁定。不能用于任意不成套库存。
- buffer_*_units_per_exposed_order=q/N，q是完整套件/Pack的一辆BEV物料等价量，N为上述交集订单数；N=0保持NULL。这不是满足N个订单的可行比例，不进行“100%覆盖”判断。
- bypassed_battery_resources以收货、Pack生产、Pack运输三位置为0/1/2，C/T/O注入为0/1/2；统计 present 且风险位置≤注入位置的电池资源个数。它表示注入库存不经过该受扰环节，不能声称完全消除该风险。ENGINE/GEAR/SEAT不算为电池缓冲直接绕过资源。
- mean_effective_loss_rate对变化的正名义RHS行求无权平均，逐资源分别计算，无变化时NULL。固定收货电芯与Pack、座椅不跨单位相加。

## 缺失与预处理

缺席的资源事件其severity/start/duration为NULL；present=0。名义场景event_count/changed_rows为真实0，first_delivery及交互分母0时仍NULL。322条首轮Master LB为NULL，另外254条读前轮lower；绝不读取本轮事后lower。

FeaturePreprocessorV3独立于提取器：ridge模式训练折内按列均值插补并按总体标准差缩放，tree模式仅按同一训练折均值插补。两者都附加84个缺失指示，共168个转换列。全缺失列用计算基准0+缺失flag，原始数据仍NULL；常量列scale=1。fit只允许显式training_split_id且一次，预测transform不更新状态。转换阶段没有对576条拟合预处理参数；交付的是unfitted contract。

## 尚未实现

inventory_exposure没有充分冻结的定义，未输出虚构数值。可行缓冲缓解量、实际缺货/流量、恢复积压、经济成本、GNN、在线Agent决策和模型训练均未实现。Oracle Q、求解时间、节点、最终最坏集合和本轮事后LB仅在标签/审计层，不在84特征中。

