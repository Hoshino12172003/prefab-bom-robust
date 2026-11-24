# 逐字段未来信息泄漏审计

结论：**84/84字段时点审计PASS**；未发现本轮Oracle结果进入特征。独立的关联切分检查为BLOCK，因此总体训练准入仍BLOCK。

检查实际源码及其已冻结哈希、字段规范、Master状态构造和原JSON指针；不只搜索特征名称。所有行再次调用现有ScenarioFeatureExtractorV3.extract，没有另一套特征计算。静态图可达性只表示潜在暴露，不是由Q拟合的影响量。

| feature_name | source | formula | information_timestamp | leakage_risk | audit_result |
|---|---|---|---|---|---|
| network_nodes | XLSB + pinned source_base | len(nodes) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| network_arcs | XLSB + pinned source_base | len(arcs) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| network_recipes | XLSB + pinned source_base | sum(len(arc.recipes)) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| network_recipe_inputs | XLSB + pinned source_base | sum(len(recipe)) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| network_order_count | XLSB + pinned source_base | sum(cohort sizes) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| network_configuration_count | XLSB + pinned source_base | distinct direct BOM signatures excluding due | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| network_horizon | XLSB + pinned source_base | len(periods) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| scenario_event_count | raw_events | len(raw_events) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| scenario_changed_rows | verified signature | len(integer changes) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| scenario_is_nominal_rhs | verified signature | integer signature is empty | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_RECEIPT_present | raw_events + original capacity/receipts | resource in events | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_RECEIPT_severity_loss | raw_events + original capacity/receipts | event severity loss | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_RECEIPT_start_offset | raw_events + original capacity/receipts | start-61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_RECEIPT_duration | raw_events + original capacity/receipts | duration | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_RECEIPT_changed_rows | raw_events + original capacity/receipts | effective changed rows of resource | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_RECEIPT_mean_effective_loss_rate | raw_events + original capacity/receipts | mean((nominal-effective)/nominal) over changed positive-nominal rows | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_PROD_present | raw_events + original capacity/receipts | resource in events | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_PROD_severity_loss | raw_events + original capacity/receipts | event severity loss | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_PROD_start_offset | raw_events + original capacity/receipts | start-61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_PROD_duration | raw_events + original capacity/receipts | duration | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_PROD_changed_rows | raw_events + original capacity/receipts | effective changed rows of resource | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_PROD_mean_effective_loss_rate | raw_events + original capacity/receipts | mean((nominal-effective)/nominal) over changed positive-nominal rows | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_SHIP_present | raw_events + original capacity/receipts | resource in events | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_SHIP_severity_loss | raw_events + original capacity/receipts | event severity loss | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_SHIP_start_offset | raw_events + original capacity/receipts | start-61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_SHIP_duration | raw_events + original capacity/receipts | duration | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_SHIP_changed_rows | raw_events + original capacity/receipts | effective changed rows of resource | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_B_SHIP_mean_effective_loss_rate | raw_events + original capacity/receipts | mean((nominal-effective)/nominal) over changed positive-nominal rows | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_ENGINE_present | raw_events + original capacity/receipts | resource in events | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_ENGINE_severity_loss | raw_events + original capacity/receipts | event severity loss | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_ENGINE_start_offset | raw_events + original capacity/receipts | start-61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_ENGINE_duration | raw_events + original capacity/receipts | duration | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_ENGINE_changed_rows | raw_events + original capacity/receipts | effective changed rows of resource | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_ENGINE_mean_effective_loss_rate | raw_events + original capacity/receipts | mean((nominal-effective)/nominal) over changed positive-nominal rows | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_GEAR_present | raw_events + original capacity/receipts | resource in events | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_GEAR_severity_loss | raw_events + original capacity/receipts | event severity loss | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_GEAR_start_offset | raw_events + original capacity/receipts | start-61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_GEAR_duration | raw_events + original capacity/receipts | duration | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_GEAR_changed_rows | raw_events + original capacity/receipts | effective changed rows of resource | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_GEAR_mean_effective_loss_rate | raw_events + original capacity/receipts | mean((nominal-effective)/nominal) over changed positive-nominal rows | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_SEAT_present | raw_events + original capacity/receipts | resource in events | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_SEAT_severity_loss | raw_events + original capacity/receipts | event severity loss | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_SEAT_start_offset | raw_events + original capacity/receipts | start-61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_SEAT_duration | raw_events + original capacity/receipts | duration | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_SEAT_changed_rows | raw_events + original capacity/receipts | effective changed rows of resource | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_SEAT_mean_effective_loss_rate | raw_events + original capacity/receipts | mean((nominal-effective)/nominal) over changed positive-nominal rows | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_reachable_skus | V3 recipe graph | distinct non-car SKU reachable by 74 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_reachable_orders | V3 recipe graph + due | sum(cohort sizes reachable before due) | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_reachable_configs | V3 BOM | distinct BOM of exposed cohorts | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_first_delivery_period | V3 recipe graph + due | min potential arrival among exposed cohorts | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_61 | V3 demand + graph | any exposed cohort due=61 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_62 | V3 demand + graph | any exposed cohort due=62 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_63 | V3 demand + graph | any exposed cohort due=63 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_64 | V3 demand + graph | any exposed cohort due=64 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_65 | V3 demand + graph | any exposed cohort due=65 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_66 | V3 demand + graph | any exposed cohort due=66 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_67 | V3 demand + graph | any exposed cohort due=67 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_68 | V3 demand + graph | any exposed cohort due=68 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_69 | V3 demand + graph | any exposed cohort due=69 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_70 | V3 demand + graph | any exposed cohort due=70 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_71 | V3 demand + graph | any exposed cohort due=71 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_72 | V3 demand + graph | any exposed cohort due=72 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_73 | V3 demand + graph | any exposed cohort due=73 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| risk_due_74 | V3 demand + graph | any exposed cohort due=74 | static_inputs_available_before_oracle | LOW_STATIC | PASS |
| master_iteration | MasterStateV3 | iteration_id | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_C | MasterStateV3 | policy[0] | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_T | MasterStateV3 | policy[1] | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_O | MasterStateV3 | policy[2] | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| master_active_count | MasterStateV3 | len(active_rhs_ids) | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| master_budget | MasterStateV3 | 17388/19 | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| master_remaining_budget | MasterStateV3 | budget-sum(cost[i]*policy[i]) | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| master_ub | MasterStateV3 | current exact Master upper | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| master_lb_before | MasterStateV3 | previous certified lower; first round NULL | previous_iteration_certified_LB_before_current_oracle; NULL_at_first_round | CONTROLLED_TEMPORAL | PASS |
| master_lb_initialized | MasterStateV3 | lb_before is not NULL | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| scenario_already_active | scenario + Master | scenario.RHS in active RHS | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_C_timed_exposed_orders | V3 recipes/lead + events + policy | exposed cohorts intersect cohorts reachable from buffer at 61 before due | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_C_units_per_exposed_order | V3 recipes/lead + events + policy | buffer quantity / timed exposed orders; no feasibility claim | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_C_bypassed_battery_resources | V3 recipes/lead + events + policy | count present battery risks at or upstream of buffer injection | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_T_timed_exposed_orders | V3 recipes/lead + events + policy | exposed cohorts intersect cohorts reachable from buffer at 61 before due | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_T_units_per_exposed_order | V3 recipes/lead + events + policy | buffer quantity / timed exposed orders; no feasibility claim | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_T_bypassed_battery_resources | V3 recipes/lead + events + policy | count present battery risks at or upstream of buffer injection | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_O_timed_exposed_orders | V3 recipes/lead + events + policy | exposed cohorts intersect cohorts reachable from buffer at 61 before due | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_O_units_per_exposed_order | V3 recipes/lead + events + policy | buffer quantity / timed exposed orders; no feasibility claim | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |
| buffer_O_bypassed_battery_resources | V3 recipes/lead + events + policy | count present battery risks at or upstream of buffer injection | after_current_master_before_current_oracle | CONTROLLED_TEMPORAL | PASS |

## 动态字段证据

Master政策/active/UB只从对应iterations[offset]读取。第k>1轮LB严格取同run iterations[k−2].lower，即前轮已认证值；322条首轮保持NULL，254条为前轮LB。state_id与原标准层一致。检查当前/后续结果字段的读访问及函数参数，禁止本轮Q、最坏集合、added_scenario、运行时间、NodeCount和本轮lower进入提取器。

is_worst、is_violating、actual_disruption_loss和demand_shortfall只在y中。样本ID、RHS哈希、重复次数和源码路径只在关联层。X不包含它们。master_lb_initialized及风险present标志是当前可知的缺失/不适用信息，不是事后标签。

CONTROLLED_TEMPORAL表示该字段依赖前序求解历史，应在切分时保持同run和关联组；它不是本轮未来信息泄漏，也不证明训练/测试独立。关联图全部连通，跨partition泄漏审计为NOT_EVALUABLE_NO_VALID_SPLIT；未签发无关联泄漏的正式切分。
