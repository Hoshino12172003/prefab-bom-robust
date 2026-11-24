# 78列保守特征审计

以下顺序与conservative_feature_manifest_v1.json、冻结Policy CV逐项相等。该Manifest的name即feature_name，数组下标定义顺序；view_version为保守视图版本，raw_feature_version为原提取器版本。

视图版本：v1.conservative78.1；原特征版本：v3.features.1.0.0。

排除：master_iteration, master_active_count, master_ub, master_lb_before, master_lb_initialized, scenario_already_active。

ID列不进入X；buffer与剩余预算是合法物理输入。原78列数值与78个既有缺失标记构成156维回归输入，未添加未经审计的新物理特征。保留列源码依赖仅有静态网络/风险与policy/budget/spent；改变iteration/active/UB/LB/run后576条投影不变。

|order|feature_name|dtype|unit|source|missing rule|
|---:|---|---|---|---|---|
|1|network_nodes|int64|location_count|XLSB + pinned source_base|不允许NULL|
|2|network_arcs|int64|arc_count|XLSB + pinned source_base|不允许NULL|
|3|network_recipes|int64|recipe_count|XLSB + pinned source_base|不允许NULL|
|4|network_recipe_inputs|int64|input_term_count|XLSB + pinned source_base|不允许NULL|
|5|network_order_count|int64|vehicle|XLSB + pinned source_base|不允许NULL|
|6|network_configuration_count|int64|configuration_count|XLSB + pinned source_base|不允许NULL|
|7|network_horizon|int64|period|XLSB + pinned source_base|不允许NULL|
|8|scenario_event_count|int64|event_count|raw_events|不允许NULL|
|9|scenario_changed_rows|int64|RHS_row_count|verified signature|不允许NULL|
|10|scenario_is_nominal_rhs|int64|boolean|verified signature|不允许NULL|
|11|risk_B_RECEIPT_present|int64|boolean|raw_events + original capacity/receipts|不允许NULL|
|12|risk_B_RECEIPT_severity_loss|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|13|risk_B_RECEIPT_start_offset|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|14|risk_B_RECEIPT_duration|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|15|risk_B_RECEIPT_changed_rows|int64|RHS_row_count|raw_events + original capacity/receipts|不允许NULL|
|16|risk_B_RECEIPT_mean_effective_loss_rate|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|17|risk_B_PROD_present|int64|boolean|raw_events + original capacity/receipts|不允许NULL|
|18|risk_B_PROD_severity_loss|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|19|risk_B_PROD_start_offset|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|20|risk_B_PROD_duration|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|21|risk_B_PROD_changed_rows|int64|RHS_row_count|raw_events + original capacity/receipts|不允许NULL|
|22|risk_B_PROD_mean_effective_loss_rate|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|23|risk_B_SHIP_present|int64|boolean|raw_events + original capacity/receipts|不允许NULL|
|24|risk_B_SHIP_severity_loss|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|25|risk_B_SHIP_start_offset|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|26|risk_B_SHIP_duration|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|27|risk_B_SHIP_changed_rows|int64|RHS_row_count|raw_events + original capacity/receipts|不允许NULL|
|28|risk_B_SHIP_mean_effective_loss_rate|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|29|risk_ENGINE_present|int64|boolean|raw_events + original capacity/receipts|不允许NULL|
|30|risk_ENGINE_severity_loss|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|31|risk_ENGINE_start_offset|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|32|risk_ENGINE_duration|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|33|risk_ENGINE_changed_rows|int64|RHS_row_count|raw_events + original capacity/receipts|不允许NULL|
|34|risk_ENGINE_mean_effective_loss_rate|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|35|risk_GEAR_present|int64|boolean|raw_events + original capacity/receipts|不允许NULL|
|36|risk_GEAR_severity_loss|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|37|risk_GEAR_start_offset|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|38|risk_GEAR_duration|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|39|risk_GEAR_changed_rows|int64|RHS_row_count|raw_events + original capacity/receipts|不允许NULL|
|40|risk_GEAR_mean_effective_loss_rate|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|41|risk_SEAT_present|int64|boolean|raw_events + original capacity/receipts|不允许NULL|
|42|risk_SEAT_severity_loss|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|43|risk_SEAT_start_offset|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|44|risk_SEAT_duration|int64|period|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|45|risk_SEAT_changed_rows|int64|RHS_row_count|raw_events + original capacity/receipts|不允许NULL|
|46|risk_SEAT_mean_effective_loss_rate|float64|fraction|raw_events + original capacity/receipts|NULL保留；训练折均值+缺失标记|
|47|risk_reachable_skus|int64|SKU_count|V3 recipe graph|不允许NULL|
|48|risk_reachable_orders|int64|vehicle|V3 recipe graph + due|不允许NULL|
|49|risk_reachable_configs|int64|configuration_count|V3 BOM|不允许NULL|
|50|risk_first_delivery_period|int64|period_index|V3 recipe graph + due|NULL保留；训练折均值+缺失标记|
|51|risk_due_61|int64|boolean|V3 demand + graph|不允许NULL|
|52|risk_due_62|int64|boolean|V3 demand + graph|不允许NULL|
|53|risk_due_63|int64|boolean|V3 demand + graph|不允许NULL|
|54|risk_due_64|int64|boolean|V3 demand + graph|不允许NULL|
|55|risk_due_65|int64|boolean|V3 demand + graph|不允许NULL|
|56|risk_due_66|int64|boolean|V3 demand + graph|不允许NULL|
|57|risk_due_67|int64|boolean|V3 demand + graph|不允许NULL|
|58|risk_due_68|int64|boolean|V3 demand + graph|不允许NULL|
|59|risk_due_69|int64|boolean|V3 demand + graph|不允许NULL|
|60|risk_due_70|int64|boolean|V3 demand + graph|不允许NULL|
|61|risk_due_71|int64|boolean|V3 demand + graph|不允许NULL|
|62|risk_due_72|int64|boolean|V3 demand + graph|不允许NULL|
|63|risk_due_73|int64|boolean|V3 demand + graph|不允许NULL|
|64|risk_due_74|int64|boolean|V3 demand + graph|不允许NULL|
|65|buffer_C|int64|complete_cell_kit|MasterStateV3|不允许NULL|
|66|buffer_T|int64|Pack|MasterStateV3|不允许NULL|
|67|buffer_O|int64|Pack|MasterStateV3|不允许NULL|
|68|master_budget|float64|normalized_investment|MasterStateV3|不允许NULL|
|69|master_remaining_budget|float64|normalized_investment|MasterStateV3|不允许NULL|
|70|buffer_C_timed_exposed_orders|int64|vehicle|V3 recipes/lead + events + policy|不允许NULL|
|71|buffer_C_units_per_exposed_order|float64|Pack_equivalent_per_vehicle|V3 recipes/lead + events + policy|NULL保留；训练折均值+缺失标记|
|72|buffer_C_bypassed_battery_resources|int64|resource_count|V3 recipes/lead + events + policy|不允许NULL|
|73|buffer_T_timed_exposed_orders|int64|vehicle|V3 recipes/lead + events + policy|不允许NULL|
|74|buffer_T_units_per_exposed_order|float64|Pack_equivalent_per_vehicle|V3 recipes/lead + events + policy|NULL保留；训练折均值+缺失标记|
|75|buffer_T_bypassed_battery_resources|int64|resource_count|V3 recipes/lead + events + policy|不允许NULL|
|76|buffer_O_timed_exposed_orders|int64|vehicle|V3 recipes/lead + events + policy|不允许NULL|
|77|buffer_O_units_per_exposed_order|float64|Pack_equivalent_per_vehicle|V3 recipes/lead + events + policy|NULL保留；训练折均值+缺失标记|
|78|buffer_O_bypassed_battery_resources|int64|resource_count|V3 recipes/lead + events + policy|不允许NULL|
