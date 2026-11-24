# 25折可训练性统计

数值均为实际数据审计，未用于拟合或选择。train/heldout分别展示。近常量定义：众数占比≥95%（含NULL）且非严格常量。

|kind|outer test|heldout policy|train policies|groups train/held|queries train/held|worst+ train/held|ties train/held|status|
|---|---|---|---:|---|---|---|---|---|
|outer|[0, 345, 0]|[[0, 345, 0]]|4|32/1|552/24|52/1|20/0|PASS|
|outer|[0, 350, 0]|[[0, 350, 0]]|4|30/3|482/94|50/3|20/0|PASS|
|outer|[337, 0, 0]|[[337, 0, 0]]|4|31/2|528/48|51/2|20/0|PASS|
|outer|[354, 0, 0]|[[354, 0, 0]]|4|32/1|552/24|52/1|20/0|PASS|
|outer|[915, 0, 0]|[[915, 0, 0]]|4|7/26|190/386|7/46|0/20|PASS|
|inner|[0, 345, 0]|[[0, 350, 0]]|3|29/3|458/94|49/3|20/0|PASS|
|inner|[0, 345, 0]|[[337, 0, 0]]|3|30/2|504/48|50/2|20/0|PASS|
|inner|[0, 345, 0]|[[354, 0, 0]]|3|31/1|528/24|51/1|20/0|PASS|
|inner|[0, 345, 0]|[[915, 0, 0]]|3|6/26|166/386|6/46|0/20|PASS|
|inner|[0, 350, 0]|[[0, 345, 0]]|3|29/1|458/24|49/1|20/0|PASS|
|inner|[0, 350, 0]|[[337, 0, 0]]|3|28/2|434/48|48/2|20/0|PASS|
|inner|[0, 350, 0]|[[354, 0, 0]]|3|29/1|458/24|49/1|20/0|PASS|
|inner|[0, 350, 0]|[[915, 0, 0]]|3|4/26|96/386|4/46|0/20|PASS|
|inner|[337, 0, 0]|[[0, 345, 0]]|3|30/1|504/24|50/1|20/0|PASS|
|inner|[337, 0, 0]|[[0, 350, 0]]|3|28/3|434/94|48/3|20/0|PASS|
|inner|[337, 0, 0]|[[354, 0, 0]]|3|30/1|504/24|50/1|20/0|PASS|
|inner|[337, 0, 0]|[[915, 0, 0]]|3|5/26|142/386|5/46|0/20|PASS|
|inner|[354, 0, 0]|[[0, 345, 0]]|3|31/1|528/24|51/1|20/0|PASS|
|inner|[354, 0, 0]|[[0, 350, 0]]|3|29/3|458/94|49/3|20/0|PASS|
|inner|[354, 0, 0]|[[337, 0, 0]]|3|30/2|504/48|50/2|20/0|PASS|
|inner|[354, 0, 0]|[[915, 0, 0]]|3|6/26|166/386|6/46|0/20|PASS|
|inner|[915, 0, 0]|[[0, 345, 0]]|3|6/1|166/24|6/1|0/0|PASS|
|inner|[915, 0, 0]|[[0, 350, 0]]|3|4/3|96/94|4/3|0/0|PASS|
|inner|[915, 0, 0]|[[337, 0, 0]]|3|5/2|142/48|5/2|0/0|PASS|
|inner|[915, 0, 0]|[[354, 0, 0]]|3|6/1|166/24|6/1|0/0|PASS|

## outer outer=[0, 345, 0] heldout=[[0, 345, 0]]

预处理fit=0.005862s；两分支train/heldout变换合计=0.005617s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26554.934782608696, "std": 929.9505379282646, "quantiles": [21775.0, 26465.0, 26798.0, 27050.0, 27363.0], "value_counts": {"21775": 12, "24200": 14, "25025": 12, "25413": 2, "25426": 6, "25430": 1, "25887": 6, "25900": 11, "25904": 3, "25991": 9, "26180": 4, "26193": 6, "26197": 2, "26311": 2, "26324": 8, "26328": 1, "26339": 4, "26352": 6, "26356": 2, "26465": 60, "26500": 13, "26758": 32, "26785": 22, "26798": 44, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 8, 32: 2, 38: 2}；缺失单元格=9200。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.775362|False|False|False|
|scenario_changed_rows|0|0.750000|False|False|False|
|scenario_is_nominal_rhs|0|0.978261|False|True|False|
|risk_B_RECEIPT_present|0|0.923913|False|False|False|
|risk_B_RECEIPT_severity_loss|510|0.923913|False|False|False|
|risk_B_RECEIPT_start_offset|510|0.923913|False|False|False|
|risk_B_RECEIPT_duration|510|0.923913|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.923913|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|510|0.923913|False|False|False|
|risk_B_PROD_present|0|0.971014|False|True|False|
|risk_B_PROD_severity_loss|536|0.971014|False|True|False|
|risk_B_PROD_start_offset|536|0.971014|False|True|False|
|risk_B_PROD_duration|536|0.971014|False|True|False|
|risk_B_PROD_changed_rows|0|0.971014|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|536|0.971014|False|True|False|
|risk_B_SHIP_present|0|0.992754|False|True|False|
|risk_B_SHIP_severity_loss|548|0.992754|False|True|False|
|risk_B_SHIP_start_offset|548|0.992754|False|True|False|
|risk_B_SHIP_duration|548|0.992754|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992754|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|548|0.992754|False|True|False|
|risk_ENGINE_present|0|0.554348|False|False|False|
|risk_ENGINE_severity_loss|306|0.554348|False|False|False|
|risk_ENGINE_start_offset|306|0.554348|False|False|False|
|risk_ENGINE_duration|306|0.554348|False|False|False|
|risk_ENGINE_changed_rows|0|0.554348|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|306|0.554348|False|False|False|
|risk_GEAR_present|0|0.557971|False|False|False|
|risk_GEAR_severity_loss|308|0.557971|False|False|False|
|risk_GEAR_start_offset|308|0.557971|False|False|False|
|risk_GEAR_duration|308|0.557971|False|False|False|
|risk_GEAR_changed_rows|0|0.557971|False|False|False|
|risk_GEAR_mean_effective_loss_rate|308|0.557971|False|False|False|
|risk_SEAT_present|0|0.855072|False|False|False|
|risk_SEAT_severity_loss|80|0.833333|False|False|False|
|risk_SEAT_start_offset|80|0.199275|False|False|False|
|risk_SEAT_duration|80|0.807971|False|False|False|
|risk_SEAT_changed_rows|0|0.807971|False|False|False|
|risk_SEAT_mean_effective_loss_rate|80|0.833333|False|False|False|
|risk_reachable_skus|0|0.384058|False|False|False|
|risk_reachable_orders|0|0.199275|False|False|False|
|risk_reachable_configs|0|0.746377|False|False|False|
|risk_first_delivery_period|12|0.199275|False|False|False|
|risk_due_61|0|0.800725|False|False|False|
|risk_due_62|0|0.721014|False|False|False|
|risk_due_63|0|0.579710|False|False|False|
|risk_due_64|0|0.543478|False|False|False|
|risk_due_65|0|0.630435|False|False|False|
|risk_due_66|0|0.760870|False|False|False|
|risk_due_67|0|0.840580|False|False|False|
|risk_due_68|0|0.978261|False|True|False|
|risk_due_69|0|0.978261|False|True|False|
|risk_due_70|0|0.978261|False|True|False|
|risk_due_71|0|0.978261|False|True|False|
|risk_due_72|0|0.978261|False|True|False|
|risk_due_73|0|0.978261|False|True|False|
|risk_due_74|0|0.978261|False|True|False|
|buffer_C|0|0.699275|False|False|False|
|buffer_T|0|0.829710|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.699275|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420290|False|False|False|
|buffer_C_units_per_exposed_order|12|0.282609|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.923913|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278986|False|False|False|
|buffer_T_units_per_exposed_order|12|0.813406|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.894928|False|False|False|
|buffer_O_timed_exposed_orders|0|0.199275|False|False|False|
|buffer_O_units_per_exposed_order|12|0.978261|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.887681|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26793.0, "mean": 26113.25, "std": 1112.0993379640147, "quantiles": [21775.0, 25895.0, 26423.5, 26793.0, 26793.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25421": 1, "25895": 3, "26188": 2, "26319": 1, "26347": 2, "26500": 1, "26793": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.291667|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## outer outer=[0, 350, 0] heldout=[[0, 350, 0]]

预处理fit=0.002333s；两分支train/heldout变换合计=0.005037s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26609.77593360996, "std": 906.531005711925, "quantiles": [21775.0, 26465.0, 26917.0, 27050.0, 27363.0], "value_counts": {"21775": 10, "24200": 11, "25025": 10, "25413": 2, "25421": 1, "25430": 1, "25887": 6, "25895": 3, "25904": 3, "25991": 9, "26180": 4, "26188": 2, "26197": 2, "26311": 2, "26319": 1, "26328": 1, "26339": 4, "26347": 2, "26356": 2, "26465": 60, "26500": 11, "26758": 32, "26785": 22, "26793": 11, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 8, 32: 1, 38: 1}；缺失单元格=7992。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.804979|False|False|False|
|scenario_changed_rows|0|0.790456|False|False|False|
|scenario_is_nominal_rhs|0|0.979253|False|True|False|
|risk_B_RECEIPT_present|0|0.939834|False|False|False|
|risk_B_RECEIPT_severity_loss|453|0.939834|False|False|False|
|risk_B_RECEIPT_start_offset|453|0.939834|False|False|False|
|risk_B_RECEIPT_duration|453|0.939834|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.939834|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|453|0.939834|False|False|False|
|risk_B_PROD_present|0|0.975104|False|True|False|
|risk_B_PROD_severity_loss|470|0.975104|False|True|False|
|risk_B_PROD_start_offset|470|0.975104|False|True|False|
|risk_B_PROD_duration|470|0.975104|False|True|False|
|risk_B_PROD_changed_rows|0|0.975104|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|470|0.975104|False|True|False|
|risk_B_SHIP_present|0|0.995851|False|True|False|
|risk_B_SHIP_severity_loss|480|0.995851|False|True|False|
|risk_B_SHIP_start_offset|480|0.995851|False|True|False|
|risk_B_SHIP_duration|480|0.995851|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995851|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|480|0.995851|False|True|False|
|risk_ENGINE_present|0|0.547718|False|False|False|
|risk_ENGINE_severity_loss|264|0.547718|False|False|False|
|risk_ENGINE_start_offset|264|0.547718|False|False|False|
|risk_ENGINE_duration|264|0.547718|False|False|False|
|risk_ENGINE_changed_rows|0|0.547718|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|264|0.547718|False|False|False|
|risk_GEAR_present|0|0.549793|False|False|False|
|risk_GEAR_severity_loss|265|0.549793|False|False|False|
|risk_GEAR_start_offset|265|0.549793|False|False|False|
|risk_GEAR_duration|265|0.549793|False|False|False|
|risk_GEAR_changed_rows|0|0.549793|False|False|False|
|risk_GEAR_mean_effective_loss_rate|265|0.549793|False|False|False|
|risk_SEAT_present|0|0.883817|False|False|False|
|risk_SEAT_severity_loss|56|0.863071|False|False|False|
|risk_SEAT_start_offset|56|0.197095|False|False|False|
|risk_SEAT_duration|56|0.840249|False|False|False|
|risk_SEAT_changed_rows|0|0.840249|False|False|False|
|risk_SEAT_mean_effective_loss_rate|56|0.863071|False|False|False|
|risk_reachable_skus|0|0.400415|False|False|False|
|risk_reachable_orders|0|0.197095|False|False|False|
|risk_reachable_configs|0|0.742739|False|False|False|
|risk_first_delivery_period|10|0.197095|False|False|False|
|risk_due_61|0|0.802905|False|False|False|
|risk_due_62|0|0.719917|False|False|False|
|risk_due_63|0|0.593361|False|False|False|
|risk_due_64|0|0.533195|False|False|False|
|risk_due_65|0|0.620332|False|False|False|
|risk_due_66|0|0.751037|False|False|False|
|risk_due_67|0|0.834025|False|False|False|
|risk_due_68|0|0.979253|False|True|False|
|risk_due_69|0|0.979253|False|True|False|
|risk_due_70|0|0.979253|False|True|False|
|risk_due_71|0|0.979253|False|True|False|
|risk_due_72|0|0.979253|False|True|False|
|risk_due_73|0|0.979253|False|True|False|
|risk_due_74|0|0.979253|False|True|False|
|buffer_C|0|0.800830|False|False|False|
|buffer_T|0|0.950207|False|True|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.800830|False|False|False|
|buffer_C_timed_exposed_orders|0|0.406639|False|False|False|
|buffer_C_units_per_exposed_order|10|0.323651|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.939834|False|False|False|
|buffer_T_timed_exposed_orders|0|0.280083|False|False|False|
|buffer_T_units_per_exposed_order|10|0.931535|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.914938|False|False|False|
|buffer_O_timed_exposed_orders|0|0.197095|False|False|False|
|buffer_O_units_per_exposed_order|10|0.979253|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.910788|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26160.957446808512, "std": 1029.3120085548323, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 3, "24200": 4, "25025": 3, "25426": 6, "25900": 11, "26193": 6, "26324": 8, "26352": 6, "26500": 3, "26798": 44}}

候选数分布：{24: 1, 32: 1, 38: 1}；缺失单元格=1616。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.595745|False|False|False|
|scenario_changed_rows|0|0.521277|False|False|False|
|scenario_is_nominal_rhs|0|0.968085|False|True|False|
|risk_B_RECEIPT_present|0|0.840426|False|False|False|
|risk_B_RECEIPT_severity_loss|79|0.840426|False|False|False|
|risk_B_RECEIPT_start_offset|79|0.840426|False|False|False|
|risk_B_RECEIPT_duration|79|0.840426|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.840426|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|79|0.840426|False|False|False|
|risk_B_PROD_present|0|0.946809|False|False|False|
|risk_B_PROD_severity_loss|89|0.946809|False|False|False|
|risk_B_PROD_start_offset|89|0.946809|False|False|False|
|risk_B_PROD_duration|89|0.946809|False|False|False|
|risk_B_PROD_changed_rows|0|0.946809|False|False|False|
|risk_B_PROD_mean_effective_loss_rate|89|0.946809|False|False|False|
|risk_B_SHIP_present|0|0.978723|False|True|False|
|risk_B_SHIP_severity_loss|92|0.978723|False|True|False|
|risk_B_SHIP_start_offset|92|0.978723|False|True|False|
|risk_B_SHIP_duration|92|0.978723|False|True|False|
|risk_B_SHIP_changed_rows|0|0.978723|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|92|0.978723|False|True|False|
|risk_ENGINE_present|0|0.595745|False|False|False|
|risk_ENGINE_severity_loss|56|0.595745|False|False|False|
|risk_ENGINE_start_offset|56|0.595745|False|False|False|
|risk_ENGINE_duration|56|0.595745|False|False|False|
|risk_ENGINE_changed_rows|0|0.595745|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.595745|False|False|False|
|risk_GEAR_present|0|0.606383|False|False|False|
|risk_GEAR_severity_loss|57|0.606383|False|False|False|
|risk_GEAR_start_offset|57|0.606383|False|False|False|
|risk_GEAR_duration|57|0.606383|False|False|False|
|risk_GEAR_changed_rows|0|0.606383|False|False|False|
|risk_GEAR_mean_effective_loss_rate|57|0.606383|False|False|False|
|risk_SEAT_present|0|0.702128|False|False|False|
|risk_SEAT_severity_loss|28|0.670213|False|False|False|
|risk_SEAT_start_offset|28|0.297872|False|False|False|
|risk_SEAT_duration|28|0.627660|False|False|False|
|risk_SEAT_changed_rows|0|0.627660|False|False|False|
|risk_SEAT_mean_effective_loss_rate|28|0.670213|False|False|False|
|risk_reachable_skus|0|0.287234|False|False|False|
|risk_reachable_orders|0|0.212766|False|False|False|
|risk_reachable_configs|0|0.765957|False|False|False|
|risk_first_delivery_period|3|0.212766|False|False|False|
|risk_due_61|0|0.787234|False|False|False|
|risk_due_62|0|0.723404|False|False|False|
|risk_due_63|0|0.510638|False|False|False|
|risk_due_64|0|0.595745|False|False|False|
|risk_due_65|0|0.680851|False|False|False|
|risk_due_66|0|0.808511|False|False|False|
|risk_due_67|0|0.872340|False|False|False|
|risk_due_68|0|0.968085|False|True|False|
|risk_due_69|0|0.968085|False|True|False|
|risk_due_70|0|0.968085|False|True|False|
|risk_due_71|0|0.968085|False|True|False|
|risk_due_72|0|0.968085|False|True|False|
|risk_due_73|0|0.968085|False|True|False|
|risk_due_74|0|0.968085|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.489362|False|False|False|
|buffer_C_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.840426|False|False|False|
|buffer_T_timed_exposed_orders|0|0.276596|False|False|False|
|buffer_T_units_per_exposed_order|3|0.276596|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.787234|False|False|False|
|buffer_O_timed_exposed_orders|0|0.212766|False|False|False|
|buffer_O_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.765957|False|False|False|

## outer outer=[337, 0, 0] heldout=[[337, 0, 0]]

预处理fit=0.002408s；两分支train/heldout变换合计=0.004854s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26575.617424242424, "std": 915.6892199732307, "quantiles": [21775.0, 26465.0, 26802.0, 27050.0, 27363.0], "value_counts": {"21775": 11, "24200": 13, "25025": 11, "25421": 1, "25426": 6, "25430": 1, "25895": 3, "25900": 11, "25904": 3, "25991": 9, "26188": 2, "26193": 6, "26197": 2, "26319": 1, "26324": 8, "26328": 1, "26347": 2, "26352": 6, "26356": 2, "26465": 60, "26500": 12, "26758": 32, "26793": 11, "26798": 44, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 2, 38: 2}；缺失单元格=8792。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.780303|False|False|False|
|scenario_changed_rows|0|0.753788|False|False|False|
|scenario_is_nominal_rhs|0|0.979167|False|True|False|
|risk_B_RECEIPT_present|0|0.924242|False|False|False|
|risk_B_RECEIPT_severity_loss|488|0.924242|False|False|False|
|risk_B_RECEIPT_start_offset|488|0.924242|False|False|False|
|risk_B_RECEIPT_duration|488|0.924242|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924242|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|488|0.924242|False|False|False|
|risk_B_PROD_present|0|0.971591|False|True|False|
|risk_B_PROD_severity_loss|513|0.971591|False|True|False|
|risk_B_PROD_start_offset|513|0.971591|False|True|False|
|risk_B_PROD_duration|513|0.971591|False|True|False|
|risk_B_PROD_changed_rows|0|0.971591|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|513|0.971591|False|True|False|
|risk_B_SHIP_present|0|0.992424|False|True|False|
|risk_B_SHIP_severity_loss|524|0.992424|False|True|False|
|risk_B_SHIP_start_offset|524|0.992424|False|True|False|
|risk_B_SHIP_duration|524|0.992424|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992424|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|524|0.992424|False|True|False|
|risk_ENGINE_present|0|0.553030|False|False|False|
|risk_ENGINE_severity_loss|292|0.553030|False|False|False|
|risk_ENGINE_start_offset|292|0.553030|False|False|False|
|risk_ENGINE_duration|292|0.553030|False|False|False|
|risk_ENGINE_changed_rows|0|0.553030|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|292|0.553030|False|False|False|
|risk_GEAR_present|0|0.556818|False|False|False|
|risk_GEAR_severity_loss|294|0.556818|False|False|False|
|risk_GEAR_start_offset|294|0.556818|False|False|False|
|risk_GEAR_duration|294|0.556818|False|False|False|
|risk_GEAR_changed_rows|0|0.556818|False|False|False|
|risk_GEAR_mean_effective_loss_rate|294|0.556818|False|False|False|
|risk_SEAT_present|0|0.856061|False|False|False|
|risk_SEAT_severity_loss|76|0.835227|False|False|False|
|risk_SEAT_start_offset|76|0.198864|False|False|False|
|risk_SEAT_duration|76|0.810606|False|False|False|
|risk_SEAT_changed_rows|0|0.810606|False|False|False|
|risk_SEAT_mean_effective_loss_rate|76|0.835227|False|False|False|
|risk_reachable_skus|0|0.386364|False|False|False|
|risk_reachable_orders|0|0.198864|False|False|False|
|risk_reachable_configs|0|0.746212|False|False|False|
|risk_first_delivery_period|11|0.198864|False|False|False|
|risk_due_61|0|0.801136|False|False|False|
|risk_due_62|0|0.721591|False|False|False|
|risk_due_63|0|0.579545|False|False|False|
|risk_due_64|0|0.543561|False|False|False|
|risk_due_65|0|0.630682|False|False|False|
|risk_due_66|0|0.761364|False|False|False|
|risk_due_67|0|0.840909|False|False|False|
|risk_due_68|0|0.979167|False|True|False|
|risk_due_69|0|0.979167|False|True|False|
|risk_due_70|0|0.979167|False|True|False|
|risk_due_71|0|0.979167|False|True|False|
|risk_due_72|0|0.979167|False|True|False|
|risk_due_73|0|0.979167|False|True|False|
|risk_due_74|0|0.979167|False|True|False|
|buffer_C|0|0.731061|False|False|False|
|buffer_T|0|0.776515|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.731061|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420455|False|False|False|
|buffer_C_units_per_exposed_order|11|0.295455|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924242|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278409|False|False|False|
|buffer_T_units_per_exposed_order|11|0.763258|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.895833|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198864|False|False|False|
|buffer_O_units_per_exposed_order|11|0.979167|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888258|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26785.0, "mean": 26106.583333333332, "std": 1110.017339078789, "quantiles": [21775.0, 25887.0, 26419.5, 26785.0, 26785.0], "value_counts": {"21775": 2, "24200": 2, "25025": 2, "25413": 2, "25887": 6, "26180": 4, "26311": 2, "26339": 4, "26500": 2, "26785": 22}}

候选数分布：{24: 2}；缺失单元格=816。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|44|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|44|0.916667|False|False|False|
|risk_B_RECEIPT_duration|44|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|44|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|46|0.958333|False|True|False|
|risk_B_PROD_start_offset|46|0.958333|False|True|False|
|risk_B_PROD_duration|46|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|46|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|48|1.000000|True|False|True|
|risk_B_SHIP_start_offset|48|1.000000|True|False|True|
|risk_B_SHIP_duration|48|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|48|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|28|0.583333|False|False|False|
|risk_ENGINE_start_offset|28|0.583333|False|False|False|
|risk_ENGINE_duration|28|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|28|0.583333|False|False|False|
|risk_GEAR_start_offset|28|0.583333|False|False|False|
|risk_GEAR_duration|28|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|8|0.791667|False|False|False|
|risk_SEAT_start_offset|8|0.208333|False|False|False|
|risk_SEAT_duration|8|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|8|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|2|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|2|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## outer outer=[354, 0, 0] heldout=[[354, 0, 0]]

预处理fit=0.007249s；两分支train/heldout变换合计=0.007142s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26554.608695652172, "std": 929.9818755813969, "quantiles": [21775.0, 26465.0, 26798.0, 27050.0, 27363.0], "value_counts": {"21775": 12, "24200": 14, "25025": 12, "25413": 2, "25421": 1, "25426": 6, "25887": 6, "25895": 3, "25900": 11, "25991": 9, "26180": 4, "26188": 2, "26193": 6, "26311": 2, "26319": 1, "26324": 8, "26339": 4, "26347": 2, "26352": 6, "26465": 60, "26500": 13, "26758": 32, "26785": 22, "26793": 11, "26798": 44, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 8, 32: 2, 38: 2}；缺失单元格=9200。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.775362|False|False|False|
|scenario_changed_rows|0|0.750000|False|False|False|
|scenario_is_nominal_rhs|0|0.978261|False|True|False|
|risk_B_RECEIPT_present|0|0.923913|False|False|False|
|risk_B_RECEIPT_severity_loss|510|0.923913|False|False|False|
|risk_B_RECEIPT_start_offset|510|0.923913|False|False|False|
|risk_B_RECEIPT_duration|510|0.923913|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.923913|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|510|0.923913|False|False|False|
|risk_B_PROD_present|0|0.971014|False|True|False|
|risk_B_PROD_severity_loss|536|0.971014|False|True|False|
|risk_B_PROD_start_offset|536|0.971014|False|True|False|
|risk_B_PROD_duration|536|0.971014|False|True|False|
|risk_B_PROD_changed_rows|0|0.971014|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|536|0.971014|False|True|False|
|risk_B_SHIP_present|0|0.992754|False|True|False|
|risk_B_SHIP_severity_loss|548|0.992754|False|True|False|
|risk_B_SHIP_start_offset|548|0.992754|False|True|False|
|risk_B_SHIP_duration|548|0.992754|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992754|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|548|0.992754|False|True|False|
|risk_ENGINE_present|0|0.554348|False|False|False|
|risk_ENGINE_severity_loss|306|0.554348|False|False|False|
|risk_ENGINE_start_offset|306|0.554348|False|False|False|
|risk_ENGINE_duration|306|0.554348|False|False|False|
|risk_ENGINE_changed_rows|0|0.554348|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|306|0.554348|False|False|False|
|risk_GEAR_present|0|0.557971|False|False|False|
|risk_GEAR_severity_loss|308|0.557971|False|False|False|
|risk_GEAR_start_offset|308|0.557971|False|False|False|
|risk_GEAR_duration|308|0.557971|False|False|False|
|risk_GEAR_changed_rows|0|0.557971|False|False|False|
|risk_GEAR_mean_effective_loss_rate|308|0.557971|False|False|False|
|risk_SEAT_present|0|0.855072|False|False|False|
|risk_SEAT_severity_loss|80|0.833333|False|False|False|
|risk_SEAT_start_offset|80|0.199275|False|False|False|
|risk_SEAT_duration|80|0.807971|False|False|False|
|risk_SEAT_changed_rows|0|0.807971|False|False|False|
|risk_SEAT_mean_effective_loss_rate|80|0.833333|False|False|False|
|risk_reachable_skus|0|0.384058|False|False|False|
|risk_reachable_orders|0|0.199275|False|False|False|
|risk_reachable_configs|0|0.746377|False|False|False|
|risk_first_delivery_period|12|0.199275|False|False|False|
|risk_due_61|0|0.800725|False|False|False|
|risk_due_62|0|0.721014|False|False|False|
|risk_due_63|0|0.579710|False|False|False|
|risk_due_64|0|0.543478|False|False|False|
|risk_due_65|0|0.630435|False|False|False|
|risk_due_66|0|0.760870|False|False|False|
|risk_due_67|0|0.840580|False|False|False|
|risk_due_68|0|0.978261|False|True|False|
|risk_due_69|0|0.978261|False|True|False|
|risk_due_70|0|0.978261|False|True|False|
|risk_due_71|0|0.978261|False|True|False|
|risk_due_72|0|0.978261|False|True|False|
|risk_due_73|0|0.978261|False|True|False|
|risk_due_74|0|0.978261|False|True|False|
|buffer_C|0|0.699275|False|False|False|
|buffer_T|0|0.786232|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.699275|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420290|False|False|False|
|buffer_C_units_per_exposed_order|12|0.282609|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.923913|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278986|False|False|False|
|buffer_T_units_per_exposed_order|12|0.771739|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.894928|False|False|False|
|buffer_O_timed_exposed_orders|0|0.199275|False|False|False|
|buffer_O_units_per_exposed_order|12|0.978261|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.887681|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26120.75, "std": 1114.446471347996, "quantiles": [21775.0, 25904.0, 26428.0, 26802.0, 26802.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25430": 1, "25904": 3, "26197": 2, "26328": 1, "26356": 2, "26500": 1, "26802": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## outer outer=[915, 0, 0] heldout=[[915, 0, 0]]

预处理fit=0.000987s；两分支train/heldout变换合计=0.004793s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26136.115789473683, "std": 1071.9934638759687, "quantiles": [21775.0, 25900.0, 26428.0, 26798.0, 26802.0], "value_counts": {"21775": 7, "24200": 8, "25025": 7, "25413": 2, "25421": 1, "25426": 6, "25430": 1, "25887": 6, "25895": 3, "25900": 11, "25904": 3, "26180": 4, "26188": 2, "26193": 6, "26197": 2, "26311": 2, "26319": 1, "26324": 8, "26328": 1, "26339": 4, "26347": 2, "26352": 6, "26356": 2, "26500": 7, "26785": 22, "26793": 11, "26798": 44, "26802": 11}}

候选数分布：{24: 5, 32: 1, 38: 1}；缺失单元格=3248。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.631579|False|False|False|
|scenario_changed_rows|0|0.594737|False|False|False|
|scenario_is_nominal_rhs|0|0.963158|False|True|False|
|risk_B_RECEIPT_present|0|0.878947|False|False|False|
|risk_B_RECEIPT_severity_loss|167|0.878947|False|False|False|
|risk_B_RECEIPT_start_offset|167|0.878947|False|False|False|
|risk_B_RECEIPT_duration|167|0.878947|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.878947|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|167|0.878947|False|False|False|
|risk_B_PROD_present|0|0.952632|False|True|False|
|risk_B_PROD_severity_loss|181|0.952632|False|True|False|
|risk_B_PROD_start_offset|181|0.952632|False|True|False|
|risk_B_PROD_duration|181|0.952632|False|True|False|
|risk_B_PROD_changed_rows|0|0.952632|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|181|0.952632|False|True|False|
|risk_B_SHIP_present|0|0.989474|False|True|False|
|risk_B_SHIP_severity_loss|188|0.989474|False|True|False|
|risk_B_SHIP_start_offset|188|0.989474|False|True|False|
|risk_B_SHIP_duration|188|0.989474|False|True|False|
|risk_B_SHIP_changed_rows|0|0.989474|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|188|0.989474|False|True|False|
|risk_ENGINE_present|0|0.589474|False|False|False|
|risk_ENGINE_severity_loss|112|0.589474|False|False|False|
|risk_ENGINE_start_offset|112|0.589474|False|False|False|
|risk_ENGINE_duration|112|0.589474|False|False|False|
|risk_ENGINE_changed_rows|0|0.589474|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|112|0.589474|False|False|False|
|risk_GEAR_present|0|0.594737|False|False|False|
|risk_GEAR_severity_loss|113|0.594737|False|False|False|
|risk_GEAR_start_offset|113|0.594737|False|False|False|
|risk_GEAR_duration|113|0.594737|False|False|False|
|risk_GEAR_changed_rows|0|0.594737|False|False|False|
|risk_GEAR_mean_effective_loss_rate|113|0.594737|False|False|False|
|risk_SEAT_present|0|0.768421|False|False|False|
|risk_SEAT_severity_loss|44|0.731579|False|False|False|
|risk_SEAT_start_offset|44|0.231579|False|False|False|
|risk_SEAT_duration|44|0.689474|False|False|False|
|risk_SEAT_changed_rows|0|0.689474|False|False|False|
|risk_SEAT_mean_effective_loss_rate|44|0.731579|False|False|False|
|risk_reachable_skus|0|0.310526|False|False|False|
|risk_reachable_orders|0|0.210526|False|False|False|
|risk_reachable_configs|0|0.757895|False|False|False|
|risk_first_delivery_period|7|0.210526|False|False|False|
|risk_due_61|0|0.789474|False|False|False|
|risk_due_62|0|0.715789|False|False|False|
|risk_due_63|0|0.547368|False|False|False|
|risk_due_64|0|0.568421|False|False|False|
|risk_due_65|0|0.652632|False|False|False|
|risk_due_66|0|0.778947|False|False|False|
|risk_due_67|0|0.852632|False|False|False|
|risk_due_68|0|0.963158|False|True|False|
|risk_due_69|0|0.963158|False|True|False|
|risk_due_70|0|0.963158|False|True|False|
|risk_due_71|0|0.963158|False|True|False|
|risk_due_72|0|0.963158|False|True|False|
|risk_due_73|0|0.963158|False|True|False|
|risk_due_74|0|0.963158|False|True|False|
|buffer_C|0|0.621053|False|False|False|
|buffer_T|0|0.494737|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.494737|False|False|False|
|buffer_C_timed_exposed_orders|0|0.452632|False|False|False|
|buffer_C_units_per_exposed_order|7|0.600000|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.878947|False|False|False|
|buffer_T_timed_exposed_orders|0|0.284211|False|False|False|
|buffer_T_units_per_exposed_order|7|0.363158|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.831579|False|False|False|
|buffer_O_timed_exposed_orders|0|0.210526|False|False|False|
|buffer_O_units_per_exposed_order|7|0.963158|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.821053|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26733.62694300518, "std": 801.1375175139253, "quantiles": [21775.0, 26758.0, 27050.0, 27050.0, 27363.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25991": 9, "26465": 60, "26500": 7, "26758": 32, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 4, 32: 1, 38: 1}；缺失单元格=6360。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.839378|False|False|False|
|scenario_changed_rows|0|0.821244|False|False|False|
|scenario_is_nominal_rhs|0|0.984456|False|True|False|
|risk_B_RECEIPT_present|0|0.945596|False|False|False|
|risk_B_RECEIPT_severity_loss|365|0.945596|False|False|False|
|risk_B_RECEIPT_start_offset|365|0.945596|False|False|False|
|risk_B_RECEIPT_duration|365|0.945596|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.945596|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|365|0.945596|False|False|False|
|risk_B_PROD_present|0|0.979275|False|True|False|
|risk_B_PROD_severity_loss|378|0.979275|False|True|False|
|risk_B_PROD_start_offset|378|0.979275|False|True|False|
|risk_B_PROD_duration|378|0.979275|False|True|False|
|risk_B_PROD_changed_rows|0|0.979275|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|378|0.979275|False|True|False|
|risk_B_SHIP_present|0|0.994819|False|True|False|
|risk_B_SHIP_severity_loss|384|0.994819|False|True|False|
|risk_B_SHIP_start_offset|384|0.994819|False|True|False|
|risk_B_SHIP_duration|384|0.994819|False|True|False|
|risk_B_SHIP_changed_rows|0|0.994819|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|384|0.994819|False|True|False|
|risk_ENGINE_present|0|0.538860|False|False|False|
|risk_ENGINE_severity_loss|208|0.538860|False|False|False|
|risk_ENGINE_start_offset|208|0.538860|False|False|False|
|risk_ENGINE_duration|208|0.538860|False|False|False|
|risk_ENGINE_changed_rows|0|0.538860|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|208|0.538860|False|False|False|
|risk_GEAR_present|0|0.541451|False|False|False|
|risk_GEAR_severity_loss|209|0.541451|False|False|False|
|risk_GEAR_start_offset|209|0.541451|False|False|False|
|risk_GEAR_duration|209|0.541451|False|False|False|
|risk_GEAR_changed_rows|0|0.541451|False|False|False|
|risk_GEAR_mean_effective_loss_rate|209|0.541451|False|False|False|
|risk_SEAT_present|0|0.896373|False|False|False|
|risk_SEAT_severity_loss|40|0.880829|False|False|False|
|risk_SEAT_start_offset|40|0.194301|False|False|False|
|risk_SEAT_duration|40|0.862694|False|False|False|
|risk_SEAT_changed_rows|0|0.862694|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.880829|False|False|False|
|risk_reachable_skus|0|0.417098|False|False|False|
|risk_reachable_orders|0|0.194301|False|False|False|
|risk_reachable_configs|0|0.740933|False|False|False|
|risk_first_delivery_period|6|0.194301|False|False|False|
|risk_due_61|0|0.805699|False|False|False|
|risk_due_62|0|0.722798|False|False|False|
|risk_due_63|0|0.595855|False|False|False|
|risk_due_64|0|0.531088|False|False|False|
|risk_due_65|0|0.619171|False|False|False|
|risk_due_66|0|0.751295|False|False|False|
|risk_due_67|0|0.834197|False|False|False|
|risk_due_68|0|0.984456|False|True|False|
|risk_due_69|0|0.984456|False|True|False|
|risk_due_70|0|0.984456|False|True|False|
|risk_due_71|0|0.984456|False|True|False|
|risk_due_72|0|0.984456|False|True|False|
|risk_due_73|0|0.984456|False|True|False|
|risk_due_74|0|0.984456|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.404145|False|False|False|
|buffer_C_units_per_exposed_order|6|0.404145|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.945596|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277202|False|False|False|
|buffer_T_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.924870|False|False|False|
|buffer_O_timed_exposed_orders|0|0.194301|False|False|False|
|buffer_O_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.919689|False|False|False|

## inner outer=[0, 345, 0] heldout=[[0, 350, 0]]

预处理fit=0.002502s；两分支train/heldout变换合计=0.004884s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26635.794759825327, "std": 886.8243879113692, "quantiles": [21775.0, 26465.0, 26917.0, 27050.0, 27363.0], "value_counts": {"21775": 9, "24200": 10, "25025": 9, "25413": 2, "25430": 1, "25887": 6, "25904": 3, "25991": 9, "26180": 4, "26197": 2, "26311": 2, "26328": 1, "26339": 4, "26356": 2, "26465": 60, "26500": 10, "26758": 32, "26785": 22, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 1, 38: 1}；缺失单元格=7584。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_T, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.812227|False|False|False|
|scenario_changed_rows|0|0.796943|False|False|False|
|scenario_is_nominal_rhs|0|0.980349|False|True|False|
|risk_B_RECEIPT_present|0|0.941048|False|False|False|
|risk_B_RECEIPT_severity_loss|431|0.941048|False|False|False|
|risk_B_RECEIPT_start_offset|431|0.941048|False|False|False|
|risk_B_RECEIPT_duration|431|0.941048|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.941048|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|431|0.941048|False|False|False|
|risk_B_PROD_present|0|0.975983|False|True|False|
|risk_B_PROD_severity_loss|447|0.975983|False|True|False|
|risk_B_PROD_start_offset|447|0.975983|False|True|False|
|risk_B_PROD_duration|447|0.975983|False|True|False|
|risk_B_PROD_changed_rows|0|0.975983|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|447|0.975983|False|True|False|
|risk_B_SHIP_present|0|0.995633|False|True|False|
|risk_B_SHIP_severity_loss|456|0.995633|False|True|False|
|risk_B_SHIP_start_offset|456|0.995633|False|True|False|
|risk_B_SHIP_duration|456|0.995633|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995633|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|456|0.995633|False|True|False|
|risk_ENGINE_present|0|0.545852|False|False|False|
|risk_ENGINE_severity_loss|250|0.545852|False|False|False|
|risk_ENGINE_start_offset|250|0.545852|False|False|False|
|risk_ENGINE_duration|250|0.545852|False|False|False|
|risk_ENGINE_changed_rows|0|0.545852|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|250|0.545852|False|False|False|
|risk_GEAR_present|0|0.548035|False|False|False|
|risk_GEAR_severity_loss|251|0.548035|False|False|False|
|risk_GEAR_start_offset|251|0.548035|False|False|False|
|risk_GEAR_duration|251|0.548035|False|False|False|
|risk_GEAR_changed_rows|0|0.548035|False|False|False|
|risk_GEAR_mean_effective_loss_rate|251|0.548035|False|False|False|
|risk_SEAT_present|0|0.886463|False|False|False|
|risk_SEAT_severity_loss|52|0.866812|False|False|False|
|risk_SEAT_start_offset|52|0.196507|False|False|False|
|risk_SEAT_duration|52|0.844978|False|False|False|
|risk_SEAT_changed_rows|0|0.844978|False|False|False|
|risk_SEAT_mean_effective_loss_rate|52|0.866812|False|False|False|
|risk_reachable_skus|0|0.403930|False|False|False|
|risk_reachable_orders|0|0.196507|False|False|False|
|risk_reachable_configs|0|0.742358|False|False|False|
|risk_first_delivery_period|9|0.196507|False|False|False|
|risk_due_61|0|0.803493|False|False|False|
|risk_due_62|0|0.720524|False|False|False|
|risk_due_63|0|0.593886|False|False|False|
|risk_due_64|0|0.532751|False|False|False|
|risk_due_65|0|0.620087|False|False|False|
|risk_due_66|0|0.751092|False|False|False|
|risk_due_67|0|0.834061|False|False|False|
|risk_due_68|0|0.980349|False|True|False|
|risk_due_69|0|0.980349|False|True|False|
|risk_due_70|0|0.980349|False|True|False|
|risk_due_71|0|0.980349|False|True|False|
|risk_due_72|0|0.980349|False|True|False|
|risk_due_73|0|0.980349|False|True|False|
|risk_due_74|0|0.980349|False|True|False|
|buffer_C|0|0.842795|False|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.842795|False|False|False|
|buffer_C_timed_exposed_orders|0|0.406114|False|False|False|
|buffer_C_units_per_exposed_order|9|0.340611|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.941048|False|False|False|
|buffer_T_timed_exposed_orders|0|0.279476|False|False|False|
|buffer_T_units_per_exposed_order|9|0.980349|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.917031|False|False|False|
|buffer_O_timed_exposed_orders|0|0.196507|False|False|False|
|buffer_O_units_per_exposed_order|9|0.980349|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.912664|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26160.957446808512, "std": 1029.3120085548323, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 3, "24200": 4, "25025": 3, "25426": 6, "25900": 11, "26193": 6, "26324": 8, "26352": 6, "26500": 3, "26798": 44}}

候选数分布：{24: 1, 32: 1, 38: 1}；缺失单元格=1616。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.595745|False|False|False|
|scenario_changed_rows|0|0.521277|False|False|False|
|scenario_is_nominal_rhs|0|0.968085|False|True|False|
|risk_B_RECEIPT_present|0|0.840426|False|False|False|
|risk_B_RECEIPT_severity_loss|79|0.840426|False|False|False|
|risk_B_RECEIPT_start_offset|79|0.840426|False|False|False|
|risk_B_RECEIPT_duration|79|0.840426|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.840426|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|79|0.840426|False|False|False|
|risk_B_PROD_present|0|0.946809|False|False|False|
|risk_B_PROD_severity_loss|89|0.946809|False|False|False|
|risk_B_PROD_start_offset|89|0.946809|False|False|False|
|risk_B_PROD_duration|89|0.946809|False|False|False|
|risk_B_PROD_changed_rows|0|0.946809|False|False|False|
|risk_B_PROD_mean_effective_loss_rate|89|0.946809|False|False|False|
|risk_B_SHIP_present|0|0.978723|False|True|False|
|risk_B_SHIP_severity_loss|92|0.978723|False|True|False|
|risk_B_SHIP_start_offset|92|0.978723|False|True|False|
|risk_B_SHIP_duration|92|0.978723|False|True|False|
|risk_B_SHIP_changed_rows|0|0.978723|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|92|0.978723|False|True|False|
|risk_ENGINE_present|0|0.595745|False|False|False|
|risk_ENGINE_severity_loss|56|0.595745|False|False|False|
|risk_ENGINE_start_offset|56|0.595745|False|False|False|
|risk_ENGINE_duration|56|0.595745|False|False|False|
|risk_ENGINE_changed_rows|0|0.595745|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.595745|False|False|False|
|risk_GEAR_present|0|0.606383|False|False|False|
|risk_GEAR_severity_loss|57|0.606383|False|False|False|
|risk_GEAR_start_offset|57|0.606383|False|False|False|
|risk_GEAR_duration|57|0.606383|False|False|False|
|risk_GEAR_changed_rows|0|0.606383|False|False|False|
|risk_GEAR_mean_effective_loss_rate|57|0.606383|False|False|False|
|risk_SEAT_present|0|0.702128|False|False|False|
|risk_SEAT_severity_loss|28|0.670213|False|False|False|
|risk_SEAT_start_offset|28|0.297872|False|False|False|
|risk_SEAT_duration|28|0.627660|False|False|False|
|risk_SEAT_changed_rows|0|0.627660|False|False|False|
|risk_SEAT_mean_effective_loss_rate|28|0.670213|False|False|False|
|risk_reachable_skus|0|0.287234|False|False|False|
|risk_reachable_orders|0|0.212766|False|False|False|
|risk_reachable_configs|0|0.765957|False|False|False|
|risk_first_delivery_period|3|0.212766|False|False|False|
|risk_due_61|0|0.787234|False|False|False|
|risk_due_62|0|0.723404|False|False|False|
|risk_due_63|0|0.510638|False|False|False|
|risk_due_64|0|0.595745|False|False|False|
|risk_due_65|0|0.680851|False|False|False|
|risk_due_66|0|0.808511|False|False|False|
|risk_due_67|0|0.872340|False|False|False|
|risk_due_68|0|0.968085|False|True|False|
|risk_due_69|0|0.968085|False|True|False|
|risk_due_70|0|0.968085|False|True|False|
|risk_due_71|0|0.968085|False|True|False|
|risk_due_72|0|0.968085|False|True|False|
|risk_due_73|0|0.968085|False|True|False|
|risk_due_74|0|0.968085|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.489362|False|False|False|
|buffer_C_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.840426|False|False|False|
|buffer_T_timed_exposed_orders|0|0.276596|False|False|False|
|buffer_T_units_per_exposed_order|3|0.276596|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.787234|False|False|False|
|buffer_O_timed_exposed_orders|0|0.212766|False|False|False|
|buffer_O_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.765957|False|False|False|

## inner outer=[0, 345, 0] heldout=[[337, 0, 0]]

预处理fit=0.002563s；两分支train/heldout变换合计=0.004913s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26597.634920634922, "std": 899.3643178606026, "quantiles": [21775.0, 26465.0, 26889.0, 27050.0, 27363.0], "value_counts": {"21775": 10, "24200": 12, "25025": 10, "25426": 6, "25430": 1, "25900": 11, "25904": 3, "25991": 9, "26193": 6, "26197": 2, "26324": 8, "26328": 1, "26352": 6, "26356": 2, "26465": 60, "26500": 11, "26758": 32, "26798": 44, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 6, 32: 2, 38: 2}；缺失单元格=8384。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.785714|False|False|False|
|scenario_changed_rows|0|0.757937|False|False|False|
|scenario_is_nominal_rhs|0|0.980159|False|True|False|
|risk_B_RECEIPT_present|0|0.924603|False|False|False|
|risk_B_RECEIPT_severity_loss|466|0.924603|False|False|False|
|risk_B_RECEIPT_start_offset|466|0.924603|False|False|False|
|risk_B_RECEIPT_duration|466|0.924603|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924603|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|466|0.924603|False|False|False|
|risk_B_PROD_present|0|0.972222|False|True|False|
|risk_B_PROD_severity_loss|490|0.972222|False|True|False|
|risk_B_PROD_start_offset|490|0.972222|False|True|False|
|risk_B_PROD_duration|490|0.972222|False|True|False|
|risk_B_PROD_changed_rows|0|0.972222|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|490|0.972222|False|True|False|
|risk_B_SHIP_present|0|0.992063|False|True|False|
|risk_B_SHIP_severity_loss|500|0.992063|False|True|False|
|risk_B_SHIP_start_offset|500|0.992063|False|True|False|
|risk_B_SHIP_duration|500|0.992063|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992063|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|500|0.992063|False|True|False|
|risk_ENGINE_present|0|0.551587|False|False|False|
|risk_ENGINE_severity_loss|278|0.551587|False|False|False|
|risk_ENGINE_start_offset|278|0.551587|False|False|False|
|risk_ENGINE_duration|278|0.551587|False|False|False|
|risk_ENGINE_changed_rows|0|0.551587|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|278|0.551587|False|False|False|
|risk_GEAR_present|0|0.555556|False|False|False|
|risk_GEAR_severity_loss|280|0.555556|False|False|False|
|risk_GEAR_start_offset|280|0.555556|False|False|False|
|risk_GEAR_duration|280|0.555556|False|False|False|
|risk_GEAR_changed_rows|0|0.555556|False|False|False|
|risk_GEAR_mean_effective_loss_rate|280|0.555556|False|False|False|
|risk_SEAT_present|0|0.857143|False|False|False|
|risk_SEAT_severity_loss|72|0.837302|False|False|False|
|risk_SEAT_start_offset|72|0.198413|False|False|False|
|risk_SEAT_duration|72|0.813492|False|False|False|
|risk_SEAT_changed_rows|0|0.813492|False|False|False|
|risk_SEAT_mean_effective_loss_rate|72|0.837302|False|False|False|
|risk_reachable_skus|0|0.388889|False|False|False|
|risk_reachable_orders|0|0.198413|False|False|False|
|risk_reachable_configs|0|0.746032|False|False|False|
|risk_first_delivery_period|10|0.198413|False|False|False|
|risk_due_61|0|0.801587|False|False|False|
|risk_due_62|0|0.722222|False|False|False|
|risk_due_63|0|0.579365|False|False|False|
|risk_due_64|0|0.543651|False|False|False|
|risk_due_65|0|0.630952|False|False|False|
|risk_due_66|0|0.761905|False|False|False|
|risk_due_67|0|0.841270|False|False|False|
|risk_due_68|0|0.980159|False|True|False|
|risk_due_69|0|0.980159|False|True|False|
|risk_due_70|0|0.980159|False|True|False|
|risk_due_71|0|0.980159|False|True|False|
|risk_due_72|0|0.980159|False|True|False|
|risk_due_73|0|0.980159|False|True|False|
|risk_due_74|0|0.980159|False|True|False|
|buffer_C|0|0.765873|False|False|False|
|buffer_T|0|0.813492|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.765873|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420635|False|False|False|
|buffer_C_units_per_exposed_order|10|0.309524|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924603|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277778|False|False|False|
|buffer_T_units_per_exposed_order|10|0.799603|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.896825|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198413|False|False|False|
|buffer_O_units_per_exposed_order|10|0.980159|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888889|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26785.0, "mean": 26106.583333333332, "std": 1110.017339078789, "quantiles": [21775.0, 25887.0, 26419.5, 26785.0, 26785.0], "value_counts": {"21775": 2, "24200": 2, "25025": 2, "25413": 2, "25887": 6, "26180": 4, "26311": 2, "26339": 4, "26500": 2, "26785": 22}}

候选数分布：{24: 2}；缺失单元格=816。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|44|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|44|0.916667|False|False|False|
|risk_B_RECEIPT_duration|44|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|44|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|46|0.958333|False|True|False|
|risk_B_PROD_start_offset|46|0.958333|False|True|False|
|risk_B_PROD_duration|46|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|46|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|48|1.000000|True|False|True|
|risk_B_SHIP_start_offset|48|1.000000|True|False|True|
|risk_B_SHIP_duration|48|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|48|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|28|0.583333|False|False|False|
|risk_ENGINE_start_offset|28|0.583333|False|False|False|
|risk_ENGINE_duration|28|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|28|0.583333|False|False|False|
|risk_GEAR_start_offset|28|0.583333|False|False|False|
|risk_GEAR_duration|28|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|8|0.791667|False|False|False|
|risk_SEAT_start_offset|8|0.208333|False|False|False|
|risk_SEAT_duration|8|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|8|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|2|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|2|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[0, 345, 0] heldout=[[354, 0, 0]]

预处理fit=0.002369s；两分支train/heldout变换合计=0.005314s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26574.670454545456, "std": 915.8083309162191, "quantiles": [21775.0, 26465.0, 26798.0, 27050.0, 27363.0], "value_counts": {"21775": 11, "24200": 13, "25025": 11, "25413": 2, "25426": 6, "25887": 6, "25900": 11, "25991": 9, "26180": 4, "26193": 6, "26311": 2, "26324": 8, "26339": 4, "26352": 6, "26465": 60, "26500": 12, "26758": 32, "26785": 22, "26798": 44, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 2, 38: 2}；缺失单元格=8792。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.780303|False|False|False|
|scenario_changed_rows|0|0.753788|False|False|False|
|scenario_is_nominal_rhs|0|0.979167|False|True|False|
|risk_B_RECEIPT_present|0|0.924242|False|False|False|
|risk_B_RECEIPT_severity_loss|488|0.924242|False|False|False|
|risk_B_RECEIPT_start_offset|488|0.924242|False|False|False|
|risk_B_RECEIPT_duration|488|0.924242|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924242|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|488|0.924242|False|False|False|
|risk_B_PROD_present|0|0.971591|False|True|False|
|risk_B_PROD_severity_loss|513|0.971591|False|True|False|
|risk_B_PROD_start_offset|513|0.971591|False|True|False|
|risk_B_PROD_duration|513|0.971591|False|True|False|
|risk_B_PROD_changed_rows|0|0.971591|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|513|0.971591|False|True|False|
|risk_B_SHIP_present|0|0.992424|False|True|False|
|risk_B_SHIP_severity_loss|524|0.992424|False|True|False|
|risk_B_SHIP_start_offset|524|0.992424|False|True|False|
|risk_B_SHIP_duration|524|0.992424|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992424|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|524|0.992424|False|True|False|
|risk_ENGINE_present|0|0.553030|False|False|False|
|risk_ENGINE_severity_loss|292|0.553030|False|False|False|
|risk_ENGINE_start_offset|292|0.553030|False|False|False|
|risk_ENGINE_duration|292|0.553030|False|False|False|
|risk_ENGINE_changed_rows|0|0.553030|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|292|0.553030|False|False|False|
|risk_GEAR_present|0|0.556818|False|False|False|
|risk_GEAR_severity_loss|294|0.556818|False|False|False|
|risk_GEAR_start_offset|294|0.556818|False|False|False|
|risk_GEAR_duration|294|0.556818|False|False|False|
|risk_GEAR_changed_rows|0|0.556818|False|False|False|
|risk_GEAR_mean_effective_loss_rate|294|0.556818|False|False|False|
|risk_SEAT_present|0|0.856061|False|False|False|
|risk_SEAT_severity_loss|76|0.835227|False|False|False|
|risk_SEAT_start_offset|76|0.198864|False|False|False|
|risk_SEAT_duration|76|0.810606|False|False|False|
|risk_SEAT_changed_rows|0|0.810606|False|False|False|
|risk_SEAT_mean_effective_loss_rate|76|0.835227|False|False|False|
|risk_reachable_skus|0|0.386364|False|False|False|
|risk_reachable_orders|0|0.198864|False|False|False|
|risk_reachable_configs|0|0.746212|False|False|False|
|risk_first_delivery_period|11|0.198864|False|False|False|
|risk_due_61|0|0.801136|False|False|False|
|risk_due_62|0|0.721591|False|False|False|
|risk_due_63|0|0.579545|False|False|False|
|risk_due_64|0|0.543561|False|False|False|
|risk_due_65|0|0.630682|False|False|False|
|risk_due_66|0|0.761364|False|False|False|
|risk_due_67|0|0.840909|False|False|False|
|risk_due_68|0|0.979167|False|True|False|
|risk_due_69|0|0.979167|False|True|False|
|risk_due_70|0|0.979167|False|True|False|
|risk_due_71|0|0.979167|False|True|False|
|risk_due_72|0|0.979167|False|True|False|
|risk_due_73|0|0.979167|False|True|False|
|risk_due_74|0|0.979167|False|True|False|
|buffer_C|0|0.731061|False|False|False|
|buffer_T|0|0.821970|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.731061|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420455|False|False|False|
|buffer_C_units_per_exposed_order|11|0.295455|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924242|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278409|False|False|False|
|buffer_T_units_per_exposed_order|11|0.806818|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.895833|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198864|False|False|False|
|buffer_O_units_per_exposed_order|11|0.979167|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888258|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26120.75, "std": 1114.446471347996, "quantiles": [21775.0, 25904.0, 26428.0, 26802.0, 26802.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25430": 1, "25904": 3, "26197": 2, "26328": 1, "26356": 2, "26500": 1, "26802": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[0, 345, 0] heldout=[[915, 0, 0]]

预处理fit=0.000888s；两分支train/heldout变换合计=0.006874s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26139.421686746988, "std": 1066.0296128313225, "quantiles": [21775.0, 25900.0, 26428.0, 26798.0, 26802.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25413": 2, "25426": 6, "25430": 1, "25887": 6, "25900": 11, "25904": 3, "26180": 4, "26193": 6, "26197": 2, "26311": 2, "26324": 8, "26328": 1, "26339": 4, "26352": 6, "26356": 2, "26500": 6, "26785": 22, "26798": 44, "26802": 11}}

候选数分布：{24: 4, 32: 1, 38: 1}；缺失单元格=2840。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.626506|False|False|False|
|scenario_changed_rows|0|0.584337|False|False|False|
|scenario_is_nominal_rhs|0|0.963855|False|True|False|
|risk_B_RECEIPT_present|0|0.873494|False|False|False|
|risk_B_RECEIPT_severity_loss|145|0.873494|False|False|False|
|risk_B_RECEIPT_start_offset|145|0.873494|False|False|False|
|risk_B_RECEIPT_duration|145|0.873494|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.873494|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|145|0.873494|False|False|False|
|risk_B_PROD_present|0|0.951807|False|True|False|
|risk_B_PROD_severity_loss|158|0.951807|False|True|False|
|risk_B_PROD_start_offset|158|0.951807|False|True|False|
|risk_B_PROD_duration|158|0.951807|False|True|False|
|risk_B_PROD_changed_rows|0|0.951807|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|158|0.951807|False|True|False|
|risk_B_SHIP_present|0|0.987952|False|True|False|
|risk_B_SHIP_severity_loss|164|0.987952|False|True|False|
|risk_B_SHIP_start_offset|164|0.987952|False|True|False|
|risk_B_SHIP_duration|164|0.987952|False|True|False|
|risk_B_SHIP_changed_rows|0|0.987952|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|164|0.987952|False|True|False|
|risk_ENGINE_present|0|0.590361|False|False|False|
|risk_ENGINE_severity_loss|98|0.590361|False|False|False|
|risk_ENGINE_start_offset|98|0.590361|False|False|False|
|risk_ENGINE_duration|98|0.590361|False|False|False|
|risk_ENGINE_changed_rows|0|0.590361|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|98|0.590361|False|False|False|
|risk_GEAR_present|0|0.596386|False|False|False|
|risk_GEAR_severity_loss|99|0.596386|False|False|False|
|risk_GEAR_start_offset|99|0.596386|False|False|False|
|risk_GEAR_duration|99|0.596386|False|False|False|
|risk_GEAR_changed_rows|0|0.596386|False|False|False|
|risk_GEAR_mean_effective_loss_rate|99|0.596386|False|False|False|
|risk_SEAT_present|0|0.759036|False|False|False|
|risk_SEAT_severity_loss|40|0.722892|False|False|False|
|risk_SEAT_start_offset|40|0.240964|False|False|False|
|risk_SEAT_duration|40|0.680723|False|False|False|
|risk_SEAT_changed_rows|0|0.680723|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.722892|False|False|False|
|risk_reachable_skus|0|0.307229|False|False|False|
|risk_reachable_orders|0|0.210843|False|False|False|
|risk_reachable_configs|0|0.759036|False|False|False|
|risk_first_delivery_period|6|0.210843|False|False|False|
|risk_due_61|0|0.789157|False|False|False|
|risk_due_62|0|0.716867|False|False|False|
|risk_due_63|0|0.542169|False|False|False|
|risk_due_64|0|0.572289|False|False|False|
|risk_due_65|0|0.656627|False|False|False|
|risk_due_66|0|0.783133|False|False|False|
|risk_due_67|0|0.855422|False|False|False|
|risk_due_68|0|0.963855|False|True|False|
|risk_due_69|0|0.963855|False|True|False|
|risk_due_70|0|0.963855|False|True|False|
|risk_due_71|0|0.963855|False|True|False|
|risk_due_72|0|0.963855|False|True|False|
|risk_due_73|0|0.963855|False|True|False|
|risk_due_74|0|0.963855|False|True|False|
|buffer_C|0|0.566265|False|False|False|
|buffer_T|0|0.566265|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.566265|False|False|False|
|buffer_C_timed_exposed_orders|0|0.457831|False|False|False|
|buffer_C_units_per_exposed_order|6|0.548193|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.873494|False|False|False|
|buffer_T_timed_exposed_orders|0|0.283133|False|False|False|
|buffer_T_units_per_exposed_order|6|0.415663|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.825301|False|False|False|
|buffer_O_timed_exposed_orders|0|0.210843|False|False|False|
|buffer_O_units_per_exposed_order|6|0.963855|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.813253|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26733.62694300518, "std": 801.1375175139253, "quantiles": [21775.0, 26758.0, 27050.0, 27050.0, 27363.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25991": 9, "26465": 60, "26500": 7, "26758": 32, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 4, 32: 1, 38: 1}；缺失单元格=6360。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.839378|False|False|False|
|scenario_changed_rows|0|0.821244|False|False|False|
|scenario_is_nominal_rhs|0|0.984456|False|True|False|
|risk_B_RECEIPT_present|0|0.945596|False|False|False|
|risk_B_RECEIPT_severity_loss|365|0.945596|False|False|False|
|risk_B_RECEIPT_start_offset|365|0.945596|False|False|False|
|risk_B_RECEIPT_duration|365|0.945596|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.945596|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|365|0.945596|False|False|False|
|risk_B_PROD_present|0|0.979275|False|True|False|
|risk_B_PROD_severity_loss|378|0.979275|False|True|False|
|risk_B_PROD_start_offset|378|0.979275|False|True|False|
|risk_B_PROD_duration|378|0.979275|False|True|False|
|risk_B_PROD_changed_rows|0|0.979275|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|378|0.979275|False|True|False|
|risk_B_SHIP_present|0|0.994819|False|True|False|
|risk_B_SHIP_severity_loss|384|0.994819|False|True|False|
|risk_B_SHIP_start_offset|384|0.994819|False|True|False|
|risk_B_SHIP_duration|384|0.994819|False|True|False|
|risk_B_SHIP_changed_rows|0|0.994819|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|384|0.994819|False|True|False|
|risk_ENGINE_present|0|0.538860|False|False|False|
|risk_ENGINE_severity_loss|208|0.538860|False|False|False|
|risk_ENGINE_start_offset|208|0.538860|False|False|False|
|risk_ENGINE_duration|208|0.538860|False|False|False|
|risk_ENGINE_changed_rows|0|0.538860|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|208|0.538860|False|False|False|
|risk_GEAR_present|0|0.541451|False|False|False|
|risk_GEAR_severity_loss|209|0.541451|False|False|False|
|risk_GEAR_start_offset|209|0.541451|False|False|False|
|risk_GEAR_duration|209|0.541451|False|False|False|
|risk_GEAR_changed_rows|0|0.541451|False|False|False|
|risk_GEAR_mean_effective_loss_rate|209|0.541451|False|False|False|
|risk_SEAT_present|0|0.896373|False|False|False|
|risk_SEAT_severity_loss|40|0.880829|False|False|False|
|risk_SEAT_start_offset|40|0.194301|False|False|False|
|risk_SEAT_duration|40|0.862694|False|False|False|
|risk_SEAT_changed_rows|0|0.862694|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.880829|False|False|False|
|risk_reachable_skus|0|0.417098|False|False|False|
|risk_reachable_orders|0|0.194301|False|False|False|
|risk_reachable_configs|0|0.740933|False|False|False|
|risk_first_delivery_period|6|0.194301|False|False|False|
|risk_due_61|0|0.805699|False|False|False|
|risk_due_62|0|0.722798|False|False|False|
|risk_due_63|0|0.595855|False|False|False|
|risk_due_64|0|0.531088|False|False|False|
|risk_due_65|0|0.619171|False|False|False|
|risk_due_66|0|0.751295|False|False|False|
|risk_due_67|0|0.834197|False|False|False|
|risk_due_68|0|0.984456|False|True|False|
|risk_due_69|0|0.984456|False|True|False|
|risk_due_70|0|0.984456|False|True|False|
|risk_due_71|0|0.984456|False|True|False|
|risk_due_72|0|0.984456|False|True|False|
|risk_due_73|0|0.984456|False|True|False|
|risk_due_74|0|0.984456|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.404145|False|False|False|
|buffer_C_units_per_exposed_order|6|0.404145|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.945596|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277202|False|False|False|
|buffer_T_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.924870|False|False|False|
|buffer_O_timed_exposed_orders|0|0.194301|False|False|False|
|buffer_O_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.919689|False|False|False|

## inner outer=[0, 350, 0] heldout=[[0, 345, 0]]

预处理fit=0.002239s；两分支train/heldout变换合计=0.004125s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26635.794759825327, "std": 886.8243879113692, "quantiles": [21775.0, 26465.0, 26917.0, 27050.0, 27363.0], "value_counts": {"21775": 9, "24200": 10, "25025": 9, "25413": 2, "25430": 1, "25887": 6, "25904": 3, "25991": 9, "26180": 4, "26197": 2, "26311": 2, "26328": 1, "26339": 4, "26356": 2, "26465": 60, "26500": 10, "26758": 32, "26785": 22, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 1, 38: 1}；缺失单元格=7584。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_T, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.812227|False|False|False|
|scenario_changed_rows|0|0.796943|False|False|False|
|scenario_is_nominal_rhs|0|0.980349|False|True|False|
|risk_B_RECEIPT_present|0|0.941048|False|False|False|
|risk_B_RECEIPT_severity_loss|431|0.941048|False|False|False|
|risk_B_RECEIPT_start_offset|431|0.941048|False|False|False|
|risk_B_RECEIPT_duration|431|0.941048|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.941048|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|431|0.941048|False|False|False|
|risk_B_PROD_present|0|0.975983|False|True|False|
|risk_B_PROD_severity_loss|447|0.975983|False|True|False|
|risk_B_PROD_start_offset|447|0.975983|False|True|False|
|risk_B_PROD_duration|447|0.975983|False|True|False|
|risk_B_PROD_changed_rows|0|0.975983|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|447|0.975983|False|True|False|
|risk_B_SHIP_present|0|0.995633|False|True|False|
|risk_B_SHIP_severity_loss|456|0.995633|False|True|False|
|risk_B_SHIP_start_offset|456|0.995633|False|True|False|
|risk_B_SHIP_duration|456|0.995633|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995633|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|456|0.995633|False|True|False|
|risk_ENGINE_present|0|0.545852|False|False|False|
|risk_ENGINE_severity_loss|250|0.545852|False|False|False|
|risk_ENGINE_start_offset|250|0.545852|False|False|False|
|risk_ENGINE_duration|250|0.545852|False|False|False|
|risk_ENGINE_changed_rows|0|0.545852|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|250|0.545852|False|False|False|
|risk_GEAR_present|0|0.548035|False|False|False|
|risk_GEAR_severity_loss|251|0.548035|False|False|False|
|risk_GEAR_start_offset|251|0.548035|False|False|False|
|risk_GEAR_duration|251|0.548035|False|False|False|
|risk_GEAR_changed_rows|0|0.548035|False|False|False|
|risk_GEAR_mean_effective_loss_rate|251|0.548035|False|False|False|
|risk_SEAT_present|0|0.886463|False|False|False|
|risk_SEAT_severity_loss|52|0.866812|False|False|False|
|risk_SEAT_start_offset|52|0.196507|False|False|False|
|risk_SEAT_duration|52|0.844978|False|False|False|
|risk_SEAT_changed_rows|0|0.844978|False|False|False|
|risk_SEAT_mean_effective_loss_rate|52|0.866812|False|False|False|
|risk_reachable_skus|0|0.403930|False|False|False|
|risk_reachable_orders|0|0.196507|False|False|False|
|risk_reachable_configs|0|0.742358|False|False|False|
|risk_first_delivery_period|9|0.196507|False|False|False|
|risk_due_61|0|0.803493|False|False|False|
|risk_due_62|0|0.720524|False|False|False|
|risk_due_63|0|0.593886|False|False|False|
|risk_due_64|0|0.532751|False|False|False|
|risk_due_65|0|0.620087|False|False|False|
|risk_due_66|0|0.751092|False|False|False|
|risk_due_67|0|0.834061|False|False|False|
|risk_due_68|0|0.980349|False|True|False|
|risk_due_69|0|0.980349|False|True|False|
|risk_due_70|0|0.980349|False|True|False|
|risk_due_71|0|0.980349|False|True|False|
|risk_due_72|0|0.980349|False|True|False|
|risk_due_73|0|0.980349|False|True|False|
|risk_due_74|0|0.980349|False|True|False|
|buffer_C|0|0.842795|False|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.842795|False|False|False|
|buffer_C_timed_exposed_orders|0|0.406114|False|False|False|
|buffer_C_units_per_exposed_order|9|0.340611|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.941048|False|False|False|
|buffer_T_timed_exposed_orders|0|0.279476|False|False|False|
|buffer_T_units_per_exposed_order|9|0.980349|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.917031|False|False|False|
|buffer_O_timed_exposed_orders|0|0.196507|False|False|False|
|buffer_O_units_per_exposed_order|9|0.980349|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.912664|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26793.0, "mean": 26113.25, "std": 1112.0993379640147, "quantiles": [21775.0, 25895.0, 26423.5, 26793.0, 26793.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25421": 1, "25895": 3, "26188": 2, "26319": 1, "26347": 2, "26500": 1, "26793": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.291667|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[0, 350, 0] heldout=[[337, 0, 0]]

预处理fit=0.002131s；两分支train/heldout变换合计=0.004345s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26665.428571428572, "std": 863.3157149616834, "quantiles": [21775.0, 26465.0, 26983.5, 27050.0, 27363.0], "value_counts": {"21775": 8, "24200": 9, "25025": 8, "25421": 1, "25430": 1, "25895": 3, "25904": 3, "25991": 9, "26188": 2, "26197": 2, "26319": 1, "26328": 1, "26347": 2, "26356": 2, "26465": 60, "26500": 9, "26758": 32, "26793": 11, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 6, 32: 1, 38: 1}；缺失单元格=7176。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.820276|False|False|False|
|scenario_changed_rows|0|0.804147|False|False|False|
|scenario_is_nominal_rhs|0|0.981567|False|True|False|
|risk_B_RECEIPT_present|0|0.942396|False|False|False|
|risk_B_RECEIPT_severity_loss|409|0.942396|False|False|False|
|risk_B_RECEIPT_start_offset|409|0.942396|False|False|False|
|risk_B_RECEIPT_duration|409|0.942396|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.942396|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|409|0.942396|False|False|False|
|risk_B_PROD_present|0|0.976959|False|True|False|
|risk_B_PROD_severity_loss|424|0.976959|False|True|False|
|risk_B_PROD_start_offset|424|0.976959|False|True|False|
|risk_B_PROD_duration|424|0.976959|False|True|False|
|risk_B_PROD_changed_rows|0|0.976959|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|424|0.976959|False|True|False|
|risk_B_SHIP_present|0|0.995392|False|True|False|
|risk_B_SHIP_severity_loss|432|0.995392|False|True|False|
|risk_B_SHIP_start_offset|432|0.995392|False|True|False|
|risk_B_SHIP_duration|432|0.995392|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995392|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|432|0.995392|False|True|False|
|risk_ENGINE_present|0|0.543779|False|False|False|
|risk_ENGINE_severity_loss|236|0.543779|False|False|False|
|risk_ENGINE_start_offset|236|0.543779|False|False|False|
|risk_ENGINE_duration|236|0.543779|False|False|False|
|risk_ENGINE_changed_rows|0|0.543779|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|236|0.543779|False|False|False|
|risk_GEAR_present|0|0.546083|False|False|False|
|risk_GEAR_severity_loss|237|0.546083|False|False|False|
|risk_GEAR_start_offset|237|0.546083|False|False|False|
|risk_GEAR_duration|237|0.546083|False|False|False|
|risk_GEAR_changed_rows|0|0.546083|False|False|False|
|risk_GEAR_mean_effective_loss_rate|237|0.546083|False|False|False|
|risk_SEAT_present|0|0.889401|False|False|False|
|risk_SEAT_severity_loss|48|0.870968|False|False|False|
|risk_SEAT_start_offset|48|0.195853|False|False|False|
|risk_SEAT_duration|48|0.850230|False|False|False|
|risk_SEAT_changed_rows|0|0.850230|False|False|False|
|risk_SEAT_mean_effective_loss_rate|48|0.870968|False|False|False|
|risk_reachable_skus|0|0.407834|False|False|False|
|risk_reachable_orders|0|0.195853|False|False|False|
|risk_reachable_configs|0|0.741935|False|False|False|
|risk_first_delivery_period|8|0.195853|False|False|False|
|risk_due_61|0|0.804147|False|False|False|
|risk_due_62|0|0.721198|False|False|False|
|risk_due_63|0|0.594470|False|False|False|
|risk_due_64|0|0.532258|False|False|False|
|risk_due_65|0|0.619816|False|False|False|
|risk_due_66|0|0.751152|False|False|False|
|risk_due_67|0|0.834101|False|False|False|
|risk_due_68|0|0.981567|False|True|False|
|risk_due_69|0|0.981567|False|True|False|
|risk_due_70|0|0.981567|False|True|False|
|risk_due_71|0|0.981567|False|True|False|
|risk_due_72|0|0.981567|False|True|False|
|risk_due_73|0|0.981567|False|True|False|
|risk_due_74|0|0.981567|False|True|False|
|buffer_C|0|0.889401|False|False|False|
|buffer_T|0|0.944700|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.889401|False|False|False|
|buffer_C_timed_exposed_orders|0|0.405530|False|False|False|
|buffer_C_units_per_exposed_order|8|0.359447|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.942396|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278802|False|False|False|
|buffer_T_units_per_exposed_order|8|0.928571|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.919355|False|False|False|
|buffer_O_timed_exposed_orders|0|0.195853|False|False|False|
|buffer_O_units_per_exposed_order|8|0.981567|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.914747|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26785.0, "mean": 26106.583333333332, "std": 1110.017339078789, "quantiles": [21775.0, 25887.0, 26419.5, 26785.0, 26785.0], "value_counts": {"21775": 2, "24200": 2, "25025": 2, "25413": 2, "25887": 6, "26180": 4, "26311": 2, "26339": 4, "26500": 2, "26785": 22}}

候选数分布：{24: 2}；缺失单元格=816。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|44|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|44|0.916667|False|False|False|
|risk_B_RECEIPT_duration|44|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|44|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|46|0.958333|False|True|False|
|risk_B_PROD_start_offset|46|0.958333|False|True|False|
|risk_B_PROD_duration|46|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|46|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|48|1.000000|True|False|True|
|risk_B_SHIP_start_offset|48|1.000000|True|False|True|
|risk_B_SHIP_duration|48|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|48|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|28|0.583333|False|False|False|
|risk_ENGINE_start_offset|28|0.583333|False|False|False|
|risk_ENGINE_duration|28|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|28|0.583333|False|False|False|
|risk_GEAR_start_offset|28|0.583333|False|False|False|
|risk_GEAR_duration|28|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|8|0.791667|False|False|False|
|risk_SEAT_start_offset|8|0.208333|False|False|False|
|risk_SEAT_duration|8|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|8|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|2|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|2|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[0, 350, 0] heldout=[[354, 0, 0]]

预处理fit=0.002149s；两分支train/heldout变换合计=0.004341s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26635.401746724892, "std": 886.899811298205, "quantiles": [21775.0, 26465.0, 26917.0, 27050.0, 27363.0], "value_counts": {"21775": 9, "24200": 10, "25025": 9, "25413": 2, "25421": 1, "25887": 6, "25895": 3, "25991": 9, "26180": 4, "26188": 2, "26311": 2, "26319": 1, "26339": 4, "26347": 2, "26465": 60, "26500": 10, "26758": 32, "26785": 22, "26793": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 1, 38: 1}；缺失单元格=7584。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.812227|False|False|False|
|scenario_changed_rows|0|0.796943|False|False|False|
|scenario_is_nominal_rhs|0|0.980349|False|True|False|
|risk_B_RECEIPT_present|0|0.941048|False|False|False|
|risk_B_RECEIPT_severity_loss|431|0.941048|False|False|False|
|risk_B_RECEIPT_start_offset|431|0.941048|False|False|False|
|risk_B_RECEIPT_duration|431|0.941048|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.941048|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|431|0.941048|False|False|False|
|risk_B_PROD_present|0|0.975983|False|True|False|
|risk_B_PROD_severity_loss|447|0.975983|False|True|False|
|risk_B_PROD_start_offset|447|0.975983|False|True|False|
|risk_B_PROD_duration|447|0.975983|False|True|False|
|risk_B_PROD_changed_rows|0|0.975983|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|447|0.975983|False|True|False|
|risk_B_SHIP_present|0|0.995633|False|True|False|
|risk_B_SHIP_severity_loss|456|0.995633|False|True|False|
|risk_B_SHIP_start_offset|456|0.995633|False|True|False|
|risk_B_SHIP_duration|456|0.995633|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995633|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|456|0.995633|False|True|False|
|risk_ENGINE_present|0|0.545852|False|False|False|
|risk_ENGINE_severity_loss|250|0.545852|False|False|False|
|risk_ENGINE_start_offset|250|0.545852|False|False|False|
|risk_ENGINE_duration|250|0.545852|False|False|False|
|risk_ENGINE_changed_rows|0|0.545852|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|250|0.545852|False|False|False|
|risk_GEAR_present|0|0.548035|False|False|False|
|risk_GEAR_severity_loss|251|0.548035|False|False|False|
|risk_GEAR_start_offset|251|0.548035|False|False|False|
|risk_GEAR_duration|251|0.548035|False|False|False|
|risk_GEAR_changed_rows|0|0.548035|False|False|False|
|risk_GEAR_mean_effective_loss_rate|251|0.548035|False|False|False|
|risk_SEAT_present|0|0.886463|False|False|False|
|risk_SEAT_severity_loss|52|0.866812|False|False|False|
|risk_SEAT_start_offset|52|0.196507|False|False|False|
|risk_SEAT_duration|52|0.844978|False|False|False|
|risk_SEAT_changed_rows|0|0.844978|False|False|False|
|risk_SEAT_mean_effective_loss_rate|52|0.866812|False|False|False|
|risk_reachable_skus|0|0.403930|False|False|False|
|risk_reachable_orders|0|0.196507|False|False|False|
|risk_reachable_configs|0|0.742358|False|False|False|
|risk_first_delivery_period|9|0.196507|False|False|False|
|risk_due_61|0|0.803493|False|False|False|
|risk_due_62|0|0.720524|False|False|False|
|risk_due_63|0|0.593886|False|False|False|
|risk_due_64|0|0.532751|False|False|False|
|risk_due_65|0|0.620087|False|False|False|
|risk_due_66|0|0.751092|False|False|False|
|risk_due_67|0|0.834061|False|False|False|
|risk_due_68|0|0.980349|False|True|False|
|risk_due_69|0|0.980349|False|True|False|
|risk_due_70|0|0.980349|False|True|False|
|risk_due_71|0|0.980349|False|True|False|
|risk_due_72|0|0.980349|False|True|False|
|risk_due_73|0|0.980349|False|True|False|
|risk_due_74|0|0.980349|False|True|False|
|buffer_C|0|0.842795|False|False|False|
|buffer_T|0|0.947598|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.842795|False|False|False|
|buffer_C_timed_exposed_orders|0|0.406114|False|False|False|
|buffer_C_units_per_exposed_order|9|0.340611|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.941048|False|False|False|
|buffer_T_timed_exposed_orders|0|0.279476|False|False|False|
|buffer_T_units_per_exposed_order|9|0.930131|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.917031|False|False|False|
|buffer_O_timed_exposed_orders|0|0.196507|False|False|False|
|buffer_O_units_per_exposed_order|9|0.980349|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.912664|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26120.75, "std": 1114.446471347996, "quantiles": [21775.0, 25904.0, 26428.0, 26802.0, 26802.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25430": 1, "25904": 3, "26197": 2, "26328": 1, "26356": 2, "26500": 1, "26802": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[0, 350, 0] heldout=[[915, 0, 0]]

预处理fit=0.000691s；两分支train/heldout变换合计=0.004232s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26111.791666666668, "std": 1111.6619869654126, "quantiles": [21775.0, 25895.0, 26428.0, 26785.0, 26802.0], "value_counts": {"21775": 4, "24200": 4, "25025": 4, "25413": 2, "25421": 1, "25430": 1, "25887": 6, "25895": 3, "25904": 3, "26180": 4, "26188": 2, "26197": 2, "26311": 2, "26319": 1, "26328": 1, "26339": 4, "26347": 2, "26356": 2, "26500": 4, "26785": 22, "26793": 11, "26802": 11}}

候选数分布：{24: 4}；缺失单元格=1632。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|88|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|88|0.916667|False|False|False|
|risk_B_RECEIPT_duration|88|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|88|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|92|0.958333|False|True|False|
|risk_B_PROD_start_offset|92|0.958333|False|True|False|
|risk_B_PROD_duration|92|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|92|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|96|1.000000|True|False|True|
|risk_B_SHIP_start_offset|96|1.000000|True|False|True|
|risk_B_SHIP_duration|96|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|96|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|56|0.583333|False|False|False|
|risk_ENGINE_start_offset|56|0.583333|False|False|False|
|risk_ENGINE_duration|56|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|56|0.583333|False|False|False|
|risk_GEAR_start_offset|56|0.583333|False|False|False|
|risk_GEAR_duration|56|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|56|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|16|0.791667|False|False|False|
|risk_SEAT_start_offset|16|0.208333|False|False|False|
|risk_SEAT_duration|16|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|16|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|4|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|0.500000|False|False|False|
|buffer_T|0|0.750000|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.500000|False|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|4|0.239583|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|4|0.718750|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|4|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26733.62694300518, "std": 801.1375175139253, "quantiles": [21775.0, 26758.0, 27050.0, 27050.0, 27363.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25991": 9, "26465": 60, "26500": 7, "26758": 32, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 4, 32: 1, 38: 1}；缺失单元格=6360。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.839378|False|False|False|
|scenario_changed_rows|0|0.821244|False|False|False|
|scenario_is_nominal_rhs|0|0.984456|False|True|False|
|risk_B_RECEIPT_present|0|0.945596|False|False|False|
|risk_B_RECEIPT_severity_loss|365|0.945596|False|False|False|
|risk_B_RECEIPT_start_offset|365|0.945596|False|False|False|
|risk_B_RECEIPT_duration|365|0.945596|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.945596|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|365|0.945596|False|False|False|
|risk_B_PROD_present|0|0.979275|False|True|False|
|risk_B_PROD_severity_loss|378|0.979275|False|True|False|
|risk_B_PROD_start_offset|378|0.979275|False|True|False|
|risk_B_PROD_duration|378|0.979275|False|True|False|
|risk_B_PROD_changed_rows|0|0.979275|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|378|0.979275|False|True|False|
|risk_B_SHIP_present|0|0.994819|False|True|False|
|risk_B_SHIP_severity_loss|384|0.994819|False|True|False|
|risk_B_SHIP_start_offset|384|0.994819|False|True|False|
|risk_B_SHIP_duration|384|0.994819|False|True|False|
|risk_B_SHIP_changed_rows|0|0.994819|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|384|0.994819|False|True|False|
|risk_ENGINE_present|0|0.538860|False|False|False|
|risk_ENGINE_severity_loss|208|0.538860|False|False|False|
|risk_ENGINE_start_offset|208|0.538860|False|False|False|
|risk_ENGINE_duration|208|0.538860|False|False|False|
|risk_ENGINE_changed_rows|0|0.538860|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|208|0.538860|False|False|False|
|risk_GEAR_present|0|0.541451|False|False|False|
|risk_GEAR_severity_loss|209|0.541451|False|False|False|
|risk_GEAR_start_offset|209|0.541451|False|False|False|
|risk_GEAR_duration|209|0.541451|False|False|False|
|risk_GEAR_changed_rows|0|0.541451|False|False|False|
|risk_GEAR_mean_effective_loss_rate|209|0.541451|False|False|False|
|risk_SEAT_present|0|0.896373|False|False|False|
|risk_SEAT_severity_loss|40|0.880829|False|False|False|
|risk_SEAT_start_offset|40|0.194301|False|False|False|
|risk_SEAT_duration|40|0.862694|False|False|False|
|risk_SEAT_changed_rows|0|0.862694|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.880829|False|False|False|
|risk_reachable_skus|0|0.417098|False|False|False|
|risk_reachable_orders|0|0.194301|False|False|False|
|risk_reachable_configs|0|0.740933|False|False|False|
|risk_first_delivery_period|6|0.194301|False|False|False|
|risk_due_61|0|0.805699|False|False|False|
|risk_due_62|0|0.722798|False|False|False|
|risk_due_63|0|0.595855|False|False|False|
|risk_due_64|0|0.531088|False|False|False|
|risk_due_65|0|0.619171|False|False|False|
|risk_due_66|0|0.751295|False|False|False|
|risk_due_67|0|0.834197|False|False|False|
|risk_due_68|0|0.984456|False|True|False|
|risk_due_69|0|0.984456|False|True|False|
|risk_due_70|0|0.984456|False|True|False|
|risk_due_71|0|0.984456|False|True|False|
|risk_due_72|0|0.984456|False|True|False|
|risk_due_73|0|0.984456|False|True|False|
|risk_due_74|0|0.984456|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.404145|False|False|False|
|buffer_C_units_per_exposed_order|6|0.404145|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.945596|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277202|False|False|False|
|buffer_T_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.924870|False|False|False|
|buffer_O_timed_exposed_orders|0|0.194301|False|False|False|
|buffer_O_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.919689|False|False|False|

## inner outer=[337, 0, 0] heldout=[[0, 345, 0]]

预处理fit=0.002414s；两分支train/heldout变换合计=0.004309s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26597.634920634922, "std": 899.3643178606026, "quantiles": [21775.0, 26465.0, 26889.0, 27050.0, 27363.0], "value_counts": {"21775": 10, "24200": 12, "25025": 10, "25426": 6, "25430": 1, "25900": 11, "25904": 3, "25991": 9, "26193": 6, "26197": 2, "26324": 8, "26328": 1, "26352": 6, "26356": 2, "26465": 60, "26500": 11, "26758": 32, "26798": 44, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 6, 32: 2, 38: 2}；缺失单元格=8384。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.785714|False|False|False|
|scenario_changed_rows|0|0.757937|False|False|False|
|scenario_is_nominal_rhs|0|0.980159|False|True|False|
|risk_B_RECEIPT_present|0|0.924603|False|False|False|
|risk_B_RECEIPT_severity_loss|466|0.924603|False|False|False|
|risk_B_RECEIPT_start_offset|466|0.924603|False|False|False|
|risk_B_RECEIPT_duration|466|0.924603|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924603|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|466|0.924603|False|False|False|
|risk_B_PROD_present|0|0.972222|False|True|False|
|risk_B_PROD_severity_loss|490|0.972222|False|True|False|
|risk_B_PROD_start_offset|490|0.972222|False|True|False|
|risk_B_PROD_duration|490|0.972222|False|True|False|
|risk_B_PROD_changed_rows|0|0.972222|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|490|0.972222|False|True|False|
|risk_B_SHIP_present|0|0.992063|False|True|False|
|risk_B_SHIP_severity_loss|500|0.992063|False|True|False|
|risk_B_SHIP_start_offset|500|0.992063|False|True|False|
|risk_B_SHIP_duration|500|0.992063|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992063|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|500|0.992063|False|True|False|
|risk_ENGINE_present|0|0.551587|False|False|False|
|risk_ENGINE_severity_loss|278|0.551587|False|False|False|
|risk_ENGINE_start_offset|278|0.551587|False|False|False|
|risk_ENGINE_duration|278|0.551587|False|False|False|
|risk_ENGINE_changed_rows|0|0.551587|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|278|0.551587|False|False|False|
|risk_GEAR_present|0|0.555556|False|False|False|
|risk_GEAR_severity_loss|280|0.555556|False|False|False|
|risk_GEAR_start_offset|280|0.555556|False|False|False|
|risk_GEAR_duration|280|0.555556|False|False|False|
|risk_GEAR_changed_rows|0|0.555556|False|False|False|
|risk_GEAR_mean_effective_loss_rate|280|0.555556|False|False|False|
|risk_SEAT_present|0|0.857143|False|False|False|
|risk_SEAT_severity_loss|72|0.837302|False|False|False|
|risk_SEAT_start_offset|72|0.198413|False|False|False|
|risk_SEAT_duration|72|0.813492|False|False|False|
|risk_SEAT_changed_rows|0|0.813492|False|False|False|
|risk_SEAT_mean_effective_loss_rate|72|0.837302|False|False|False|
|risk_reachable_skus|0|0.388889|False|False|False|
|risk_reachable_orders|0|0.198413|False|False|False|
|risk_reachable_configs|0|0.746032|False|False|False|
|risk_first_delivery_period|10|0.198413|False|False|False|
|risk_due_61|0|0.801587|False|False|False|
|risk_due_62|0|0.722222|False|False|False|
|risk_due_63|0|0.579365|False|False|False|
|risk_due_64|0|0.543651|False|False|False|
|risk_due_65|0|0.630952|False|False|False|
|risk_due_66|0|0.761905|False|False|False|
|risk_due_67|0|0.841270|False|False|False|
|risk_due_68|0|0.980159|False|True|False|
|risk_due_69|0|0.980159|False|True|False|
|risk_due_70|0|0.980159|False|True|False|
|risk_due_71|0|0.980159|False|True|False|
|risk_due_72|0|0.980159|False|True|False|
|risk_due_73|0|0.980159|False|True|False|
|risk_due_74|0|0.980159|False|True|False|
|buffer_C|0|0.765873|False|False|False|
|buffer_T|0|0.813492|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.765873|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420635|False|False|False|
|buffer_C_units_per_exposed_order|10|0.309524|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924603|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277778|False|False|False|
|buffer_T_units_per_exposed_order|10|0.799603|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.896825|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198413|False|False|False|
|buffer_O_units_per_exposed_order|10|0.980159|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888889|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26793.0, "mean": 26113.25, "std": 1112.0993379640147, "quantiles": [21775.0, 25895.0, 26423.5, 26793.0, 26793.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25421": 1, "25895": 3, "26188": 2, "26319": 1, "26347": 2, "26500": 1, "26793": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.291667|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[337, 0, 0] heldout=[[0, 350, 0]]

预处理fit=0.002253s；两分支train/heldout变换合计=0.004537s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26665.428571428572, "std": 863.3157149616834, "quantiles": [21775.0, 26465.0, 26983.5, 27050.0, 27363.0], "value_counts": {"21775": 8, "24200": 9, "25025": 8, "25421": 1, "25430": 1, "25895": 3, "25904": 3, "25991": 9, "26188": 2, "26197": 2, "26319": 1, "26328": 1, "26347": 2, "26356": 2, "26465": 60, "26500": 9, "26758": 32, "26793": 11, "26802": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 6, 32: 1, 38: 1}；缺失单元格=7176。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.820276|False|False|False|
|scenario_changed_rows|0|0.804147|False|False|False|
|scenario_is_nominal_rhs|0|0.981567|False|True|False|
|risk_B_RECEIPT_present|0|0.942396|False|False|False|
|risk_B_RECEIPT_severity_loss|409|0.942396|False|False|False|
|risk_B_RECEIPT_start_offset|409|0.942396|False|False|False|
|risk_B_RECEIPT_duration|409|0.942396|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.942396|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|409|0.942396|False|False|False|
|risk_B_PROD_present|0|0.976959|False|True|False|
|risk_B_PROD_severity_loss|424|0.976959|False|True|False|
|risk_B_PROD_start_offset|424|0.976959|False|True|False|
|risk_B_PROD_duration|424|0.976959|False|True|False|
|risk_B_PROD_changed_rows|0|0.976959|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|424|0.976959|False|True|False|
|risk_B_SHIP_present|0|0.995392|False|True|False|
|risk_B_SHIP_severity_loss|432|0.995392|False|True|False|
|risk_B_SHIP_start_offset|432|0.995392|False|True|False|
|risk_B_SHIP_duration|432|0.995392|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995392|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|432|0.995392|False|True|False|
|risk_ENGINE_present|0|0.543779|False|False|False|
|risk_ENGINE_severity_loss|236|0.543779|False|False|False|
|risk_ENGINE_start_offset|236|0.543779|False|False|False|
|risk_ENGINE_duration|236|0.543779|False|False|False|
|risk_ENGINE_changed_rows|0|0.543779|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|236|0.543779|False|False|False|
|risk_GEAR_present|0|0.546083|False|False|False|
|risk_GEAR_severity_loss|237|0.546083|False|False|False|
|risk_GEAR_start_offset|237|0.546083|False|False|False|
|risk_GEAR_duration|237|0.546083|False|False|False|
|risk_GEAR_changed_rows|0|0.546083|False|False|False|
|risk_GEAR_mean_effective_loss_rate|237|0.546083|False|False|False|
|risk_SEAT_present|0|0.889401|False|False|False|
|risk_SEAT_severity_loss|48|0.870968|False|False|False|
|risk_SEAT_start_offset|48|0.195853|False|False|False|
|risk_SEAT_duration|48|0.850230|False|False|False|
|risk_SEAT_changed_rows|0|0.850230|False|False|False|
|risk_SEAT_mean_effective_loss_rate|48|0.870968|False|False|False|
|risk_reachable_skus|0|0.407834|False|False|False|
|risk_reachable_orders|0|0.195853|False|False|False|
|risk_reachable_configs|0|0.741935|False|False|False|
|risk_first_delivery_period|8|0.195853|False|False|False|
|risk_due_61|0|0.804147|False|False|False|
|risk_due_62|0|0.721198|False|False|False|
|risk_due_63|0|0.594470|False|False|False|
|risk_due_64|0|0.532258|False|False|False|
|risk_due_65|0|0.619816|False|False|False|
|risk_due_66|0|0.751152|False|False|False|
|risk_due_67|0|0.834101|False|False|False|
|risk_due_68|0|0.981567|False|True|False|
|risk_due_69|0|0.981567|False|True|False|
|risk_due_70|0|0.981567|False|True|False|
|risk_due_71|0|0.981567|False|True|False|
|risk_due_72|0|0.981567|False|True|False|
|risk_due_73|0|0.981567|False|True|False|
|risk_due_74|0|0.981567|False|True|False|
|buffer_C|0|0.889401|False|False|False|
|buffer_T|0|0.944700|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.889401|False|False|False|
|buffer_C_timed_exposed_orders|0|0.405530|False|False|False|
|buffer_C_units_per_exposed_order|8|0.359447|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.942396|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278802|False|False|False|
|buffer_T_units_per_exposed_order|8|0.928571|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.919355|False|False|False|
|buffer_O_timed_exposed_orders|0|0.195853|False|False|False|
|buffer_O_units_per_exposed_order|8|0.981567|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.914747|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26160.957446808512, "std": 1029.3120085548323, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 3, "24200": 4, "25025": 3, "25426": 6, "25900": 11, "26193": 6, "26324": 8, "26352": 6, "26500": 3, "26798": 44}}

候选数分布：{24: 1, 32: 1, 38: 1}；缺失单元格=1616。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.595745|False|False|False|
|scenario_changed_rows|0|0.521277|False|False|False|
|scenario_is_nominal_rhs|0|0.968085|False|True|False|
|risk_B_RECEIPT_present|0|0.840426|False|False|False|
|risk_B_RECEIPT_severity_loss|79|0.840426|False|False|False|
|risk_B_RECEIPT_start_offset|79|0.840426|False|False|False|
|risk_B_RECEIPT_duration|79|0.840426|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.840426|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|79|0.840426|False|False|False|
|risk_B_PROD_present|0|0.946809|False|False|False|
|risk_B_PROD_severity_loss|89|0.946809|False|False|False|
|risk_B_PROD_start_offset|89|0.946809|False|False|False|
|risk_B_PROD_duration|89|0.946809|False|False|False|
|risk_B_PROD_changed_rows|0|0.946809|False|False|False|
|risk_B_PROD_mean_effective_loss_rate|89|0.946809|False|False|False|
|risk_B_SHIP_present|0|0.978723|False|True|False|
|risk_B_SHIP_severity_loss|92|0.978723|False|True|False|
|risk_B_SHIP_start_offset|92|0.978723|False|True|False|
|risk_B_SHIP_duration|92|0.978723|False|True|False|
|risk_B_SHIP_changed_rows|0|0.978723|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|92|0.978723|False|True|False|
|risk_ENGINE_present|0|0.595745|False|False|False|
|risk_ENGINE_severity_loss|56|0.595745|False|False|False|
|risk_ENGINE_start_offset|56|0.595745|False|False|False|
|risk_ENGINE_duration|56|0.595745|False|False|False|
|risk_ENGINE_changed_rows|0|0.595745|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.595745|False|False|False|
|risk_GEAR_present|0|0.606383|False|False|False|
|risk_GEAR_severity_loss|57|0.606383|False|False|False|
|risk_GEAR_start_offset|57|0.606383|False|False|False|
|risk_GEAR_duration|57|0.606383|False|False|False|
|risk_GEAR_changed_rows|0|0.606383|False|False|False|
|risk_GEAR_mean_effective_loss_rate|57|0.606383|False|False|False|
|risk_SEAT_present|0|0.702128|False|False|False|
|risk_SEAT_severity_loss|28|0.670213|False|False|False|
|risk_SEAT_start_offset|28|0.297872|False|False|False|
|risk_SEAT_duration|28|0.627660|False|False|False|
|risk_SEAT_changed_rows|0|0.627660|False|False|False|
|risk_SEAT_mean_effective_loss_rate|28|0.670213|False|False|False|
|risk_reachable_skus|0|0.287234|False|False|False|
|risk_reachable_orders|0|0.212766|False|False|False|
|risk_reachable_configs|0|0.765957|False|False|False|
|risk_first_delivery_period|3|0.212766|False|False|False|
|risk_due_61|0|0.787234|False|False|False|
|risk_due_62|0|0.723404|False|False|False|
|risk_due_63|0|0.510638|False|False|False|
|risk_due_64|0|0.595745|False|False|False|
|risk_due_65|0|0.680851|False|False|False|
|risk_due_66|0|0.808511|False|False|False|
|risk_due_67|0|0.872340|False|False|False|
|risk_due_68|0|0.968085|False|True|False|
|risk_due_69|0|0.968085|False|True|False|
|risk_due_70|0|0.968085|False|True|False|
|risk_due_71|0|0.968085|False|True|False|
|risk_due_72|0|0.968085|False|True|False|
|risk_due_73|0|0.968085|False|True|False|
|risk_due_74|0|0.968085|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.489362|False|False|False|
|buffer_C_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.840426|False|False|False|
|buffer_T_timed_exposed_orders|0|0.276596|False|False|False|
|buffer_T_units_per_exposed_order|3|0.276596|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.787234|False|False|False|
|buffer_O_timed_exposed_orders|0|0.212766|False|False|False|
|buffer_O_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.765957|False|False|False|

## inner outer=[337, 0, 0] heldout=[[354, 0, 0]]

预处理fit=0.002245s；两分支train/heldout变换合计=0.004615s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26597.277777777777, "std": 899.4167566843445, "quantiles": [21775.0, 26465.0, 26889.0, 27050.0, 27363.0], "value_counts": {"21775": 10, "24200": 12, "25025": 10, "25421": 1, "25426": 6, "25895": 3, "25900": 11, "25991": 9, "26188": 2, "26193": 6, "26319": 1, "26324": 8, "26347": 2, "26352": 6, "26465": 60, "26500": 11, "26758": 32, "26793": 11, "26798": 44, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 6, 32: 2, 38: 2}；缺失单元格=8384。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.785714|False|False|False|
|scenario_changed_rows|0|0.757937|False|False|False|
|scenario_is_nominal_rhs|0|0.980159|False|True|False|
|risk_B_RECEIPT_present|0|0.924603|False|False|False|
|risk_B_RECEIPT_severity_loss|466|0.924603|False|False|False|
|risk_B_RECEIPT_start_offset|466|0.924603|False|False|False|
|risk_B_RECEIPT_duration|466|0.924603|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924603|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|466|0.924603|False|False|False|
|risk_B_PROD_present|0|0.972222|False|True|False|
|risk_B_PROD_severity_loss|490|0.972222|False|True|False|
|risk_B_PROD_start_offset|490|0.972222|False|True|False|
|risk_B_PROD_duration|490|0.972222|False|True|False|
|risk_B_PROD_changed_rows|0|0.972222|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|490|0.972222|False|True|False|
|risk_B_SHIP_present|0|0.992063|False|True|False|
|risk_B_SHIP_severity_loss|500|0.992063|False|True|False|
|risk_B_SHIP_start_offset|500|0.992063|False|True|False|
|risk_B_SHIP_duration|500|0.992063|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992063|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|500|0.992063|False|True|False|
|risk_ENGINE_present|0|0.551587|False|False|False|
|risk_ENGINE_severity_loss|278|0.551587|False|False|False|
|risk_ENGINE_start_offset|278|0.551587|False|False|False|
|risk_ENGINE_duration|278|0.551587|False|False|False|
|risk_ENGINE_changed_rows|0|0.551587|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|278|0.551587|False|False|False|
|risk_GEAR_present|0|0.555556|False|False|False|
|risk_GEAR_severity_loss|280|0.555556|False|False|False|
|risk_GEAR_start_offset|280|0.555556|False|False|False|
|risk_GEAR_duration|280|0.555556|False|False|False|
|risk_GEAR_changed_rows|0|0.555556|False|False|False|
|risk_GEAR_mean_effective_loss_rate|280|0.555556|False|False|False|
|risk_SEAT_present|0|0.857143|False|False|False|
|risk_SEAT_severity_loss|72|0.837302|False|False|False|
|risk_SEAT_start_offset|72|0.198413|False|False|False|
|risk_SEAT_duration|72|0.813492|False|False|False|
|risk_SEAT_changed_rows|0|0.813492|False|False|False|
|risk_SEAT_mean_effective_loss_rate|72|0.837302|False|False|False|
|risk_reachable_skus|0|0.388889|False|False|False|
|risk_reachable_orders|0|0.198413|False|False|False|
|risk_reachable_configs|0|0.746032|False|False|False|
|risk_first_delivery_period|10|0.198413|False|False|False|
|risk_due_61|0|0.801587|False|False|False|
|risk_due_62|0|0.722222|False|False|False|
|risk_due_63|0|0.579365|False|False|False|
|risk_due_64|0|0.543651|False|False|False|
|risk_due_65|0|0.630952|False|False|False|
|risk_due_66|0|0.761905|False|False|False|
|risk_due_67|0|0.841270|False|False|False|
|risk_due_68|0|0.980159|False|True|False|
|risk_due_69|0|0.980159|False|True|False|
|risk_due_70|0|0.980159|False|True|False|
|risk_due_71|0|0.980159|False|True|False|
|risk_due_72|0|0.980159|False|True|False|
|risk_due_73|0|0.980159|False|True|False|
|risk_due_74|0|0.980159|False|True|False|
|buffer_C|0|0.765873|False|False|False|
|buffer_T|0|0.765873|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.765873|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420635|False|False|False|
|buffer_C_units_per_exposed_order|10|0.309524|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924603|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277778|False|False|False|
|buffer_T_units_per_exposed_order|10|0.753968|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.896825|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198413|False|False|False|
|buffer_O_units_per_exposed_order|10|0.980159|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888889|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26120.75, "std": 1114.446471347996, "quantiles": [21775.0, 25904.0, 26428.0, 26802.0, 26802.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25430": 1, "25904": 3, "26197": 2, "26328": 1, "26356": 2, "26500": 1, "26802": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[337, 0, 0] heldout=[[915, 0, 0]]

预处理fit=0.000795s；两分支train/heldout变换合计=0.004526s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26146.098591549297, "std": 1058.6452764101966, "quantiles": [21775.0, 25900.0, 26428.0, 26798.0, 26802.0], "value_counts": {"21775": 5, "24200": 6, "25025": 5, "25421": 1, "25426": 6, "25430": 1, "25895": 3, "25900": 11, "25904": 3, "26188": 2, "26193": 6, "26197": 2, "26319": 1, "26324": 8, "26328": 1, "26347": 2, "26352": 6, "26356": 2, "26500": 5, "26793": 11, "26798": 44, "26802": 11}}

候选数分布：{24: 3, 32: 1, 38: 1}；缺失单元格=2432。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.619718|False|False|False|
|scenario_changed_rows|0|0.570423|False|False|False|
|scenario_is_nominal_rhs|0|0.964789|False|True|False|
|risk_B_RECEIPT_present|0|0.866197|False|False|False|
|risk_B_RECEIPT_severity_loss|123|0.866197|False|False|False|
|risk_B_RECEIPT_start_offset|123|0.866197|False|False|False|
|risk_B_RECEIPT_duration|123|0.866197|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.866197|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|123|0.866197|False|False|False|
|risk_B_PROD_present|0|0.950704|False|True|False|
|risk_B_PROD_severity_loss|135|0.950704|False|True|False|
|risk_B_PROD_start_offset|135|0.950704|False|True|False|
|risk_B_PROD_duration|135|0.950704|False|True|False|
|risk_B_PROD_changed_rows|0|0.950704|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|135|0.950704|False|True|False|
|risk_B_SHIP_present|0|0.985915|False|True|False|
|risk_B_SHIP_severity_loss|140|0.985915|False|True|False|
|risk_B_SHIP_start_offset|140|0.985915|False|True|False|
|risk_B_SHIP_duration|140|0.985915|False|True|False|
|risk_B_SHIP_changed_rows|0|0.985915|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|140|0.985915|False|True|False|
|risk_ENGINE_present|0|0.591549|False|False|False|
|risk_ENGINE_severity_loss|84|0.591549|False|False|False|
|risk_ENGINE_start_offset|84|0.591549|False|False|False|
|risk_ENGINE_duration|84|0.591549|False|False|False|
|risk_ENGINE_changed_rows|0|0.591549|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|84|0.591549|False|False|False|
|risk_GEAR_present|0|0.598592|False|False|False|
|risk_GEAR_severity_loss|85|0.598592|False|False|False|
|risk_GEAR_start_offset|85|0.598592|False|False|False|
|risk_GEAR_duration|85|0.598592|False|False|False|
|risk_GEAR_changed_rows|0|0.598592|False|False|False|
|risk_GEAR_mean_effective_loss_rate|85|0.598592|False|False|False|
|risk_SEAT_present|0|0.746479|False|False|False|
|risk_SEAT_severity_loss|36|0.711268|False|False|False|
|risk_SEAT_start_offset|36|0.253521|False|False|False|
|risk_SEAT_duration|36|0.669014|False|False|False|
|risk_SEAT_changed_rows|0|0.669014|False|False|False|
|risk_SEAT_mean_effective_loss_rate|36|0.711268|False|False|False|
|risk_reachable_skus|0|0.302817|False|False|False|
|risk_reachable_orders|0|0.211268|False|False|False|
|risk_reachable_configs|0|0.760563|False|False|False|
|risk_first_delivery_period|5|0.211268|False|False|False|
|risk_due_61|0|0.788732|False|False|False|
|risk_due_62|0|0.718310|False|False|False|
|risk_due_63|0|0.535211|False|False|False|
|risk_due_64|0|0.577465|False|False|False|
|risk_due_65|0|0.661972|False|False|False|
|risk_due_66|0|0.788732|False|False|False|
|risk_due_67|0|0.859155|False|False|False|
|risk_due_68|0|0.964789|False|True|False|
|risk_due_69|0|0.964789|False|True|False|
|risk_due_70|0|0.964789|False|True|False|
|risk_due_71|0|0.964789|False|True|False|
|risk_due_72|0|0.964789|False|True|False|
|risk_due_73|0|0.964789|False|True|False|
|risk_due_74|0|0.964789|False|True|False|
|buffer_C|0|0.830986|False|False|False|
|buffer_T|0|0.661972|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.661972|False|False|False|
|buffer_C_timed_exposed_orders|0|0.464789|False|False|False|
|buffer_C_units_per_exposed_order|5|0.802817|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.866197|False|False|False|
|buffer_T_timed_exposed_orders|0|0.281690|False|False|False|
|buffer_T_units_per_exposed_order|5|0.183099|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.816901|False|False|False|
|buffer_O_timed_exposed_orders|0|0.211268|False|False|False|
|buffer_O_units_per_exposed_order|5|0.964789|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.802817|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26733.62694300518, "std": 801.1375175139253, "quantiles": [21775.0, 26758.0, 27050.0, 27050.0, 27363.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25991": 9, "26465": 60, "26500": 7, "26758": 32, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 4, 32: 1, 38: 1}；缺失单元格=6360。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.839378|False|False|False|
|scenario_changed_rows|0|0.821244|False|False|False|
|scenario_is_nominal_rhs|0|0.984456|False|True|False|
|risk_B_RECEIPT_present|0|0.945596|False|False|False|
|risk_B_RECEIPT_severity_loss|365|0.945596|False|False|False|
|risk_B_RECEIPT_start_offset|365|0.945596|False|False|False|
|risk_B_RECEIPT_duration|365|0.945596|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.945596|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|365|0.945596|False|False|False|
|risk_B_PROD_present|0|0.979275|False|True|False|
|risk_B_PROD_severity_loss|378|0.979275|False|True|False|
|risk_B_PROD_start_offset|378|0.979275|False|True|False|
|risk_B_PROD_duration|378|0.979275|False|True|False|
|risk_B_PROD_changed_rows|0|0.979275|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|378|0.979275|False|True|False|
|risk_B_SHIP_present|0|0.994819|False|True|False|
|risk_B_SHIP_severity_loss|384|0.994819|False|True|False|
|risk_B_SHIP_start_offset|384|0.994819|False|True|False|
|risk_B_SHIP_duration|384|0.994819|False|True|False|
|risk_B_SHIP_changed_rows|0|0.994819|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|384|0.994819|False|True|False|
|risk_ENGINE_present|0|0.538860|False|False|False|
|risk_ENGINE_severity_loss|208|0.538860|False|False|False|
|risk_ENGINE_start_offset|208|0.538860|False|False|False|
|risk_ENGINE_duration|208|0.538860|False|False|False|
|risk_ENGINE_changed_rows|0|0.538860|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|208|0.538860|False|False|False|
|risk_GEAR_present|0|0.541451|False|False|False|
|risk_GEAR_severity_loss|209|0.541451|False|False|False|
|risk_GEAR_start_offset|209|0.541451|False|False|False|
|risk_GEAR_duration|209|0.541451|False|False|False|
|risk_GEAR_changed_rows|0|0.541451|False|False|False|
|risk_GEAR_mean_effective_loss_rate|209|0.541451|False|False|False|
|risk_SEAT_present|0|0.896373|False|False|False|
|risk_SEAT_severity_loss|40|0.880829|False|False|False|
|risk_SEAT_start_offset|40|0.194301|False|False|False|
|risk_SEAT_duration|40|0.862694|False|False|False|
|risk_SEAT_changed_rows|0|0.862694|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.880829|False|False|False|
|risk_reachable_skus|0|0.417098|False|False|False|
|risk_reachable_orders|0|0.194301|False|False|False|
|risk_reachable_configs|0|0.740933|False|False|False|
|risk_first_delivery_period|6|0.194301|False|False|False|
|risk_due_61|0|0.805699|False|False|False|
|risk_due_62|0|0.722798|False|False|False|
|risk_due_63|0|0.595855|False|False|False|
|risk_due_64|0|0.531088|False|False|False|
|risk_due_65|0|0.619171|False|False|False|
|risk_due_66|0|0.751295|False|False|False|
|risk_due_67|0|0.834197|False|False|False|
|risk_due_68|0|0.984456|False|True|False|
|risk_due_69|0|0.984456|False|True|False|
|risk_due_70|0|0.984456|False|True|False|
|risk_due_71|0|0.984456|False|True|False|
|risk_due_72|0|0.984456|False|True|False|
|risk_due_73|0|0.984456|False|True|False|
|risk_due_74|0|0.984456|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.404145|False|False|False|
|buffer_C_units_per_exposed_order|6|0.404145|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.945596|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277202|False|False|False|
|buffer_T_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.924870|False|False|False|
|buffer_O_timed_exposed_orders|0|0.194301|False|False|False|
|buffer_O_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.919689|False|False|False|

## inner outer=[354, 0, 0] heldout=[[0, 345, 0]]

预处理fit=0.002341s；两分支train/heldout变换合计=0.004404s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26574.670454545456, "std": 915.8083309162191, "quantiles": [21775.0, 26465.0, 26798.0, 27050.0, 27363.0], "value_counts": {"21775": 11, "24200": 13, "25025": 11, "25413": 2, "25426": 6, "25887": 6, "25900": 11, "25991": 9, "26180": 4, "26193": 6, "26311": 2, "26324": 8, "26339": 4, "26352": 6, "26465": 60, "26500": 12, "26758": 32, "26785": 22, "26798": 44, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 2, 38: 2}；缺失单元格=8792。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.780303|False|False|False|
|scenario_changed_rows|0|0.753788|False|False|False|
|scenario_is_nominal_rhs|0|0.979167|False|True|False|
|risk_B_RECEIPT_present|0|0.924242|False|False|False|
|risk_B_RECEIPT_severity_loss|488|0.924242|False|False|False|
|risk_B_RECEIPT_start_offset|488|0.924242|False|False|False|
|risk_B_RECEIPT_duration|488|0.924242|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924242|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|488|0.924242|False|False|False|
|risk_B_PROD_present|0|0.971591|False|True|False|
|risk_B_PROD_severity_loss|513|0.971591|False|True|False|
|risk_B_PROD_start_offset|513|0.971591|False|True|False|
|risk_B_PROD_duration|513|0.971591|False|True|False|
|risk_B_PROD_changed_rows|0|0.971591|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|513|0.971591|False|True|False|
|risk_B_SHIP_present|0|0.992424|False|True|False|
|risk_B_SHIP_severity_loss|524|0.992424|False|True|False|
|risk_B_SHIP_start_offset|524|0.992424|False|True|False|
|risk_B_SHIP_duration|524|0.992424|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992424|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|524|0.992424|False|True|False|
|risk_ENGINE_present|0|0.553030|False|False|False|
|risk_ENGINE_severity_loss|292|0.553030|False|False|False|
|risk_ENGINE_start_offset|292|0.553030|False|False|False|
|risk_ENGINE_duration|292|0.553030|False|False|False|
|risk_ENGINE_changed_rows|0|0.553030|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|292|0.553030|False|False|False|
|risk_GEAR_present|0|0.556818|False|False|False|
|risk_GEAR_severity_loss|294|0.556818|False|False|False|
|risk_GEAR_start_offset|294|0.556818|False|False|False|
|risk_GEAR_duration|294|0.556818|False|False|False|
|risk_GEAR_changed_rows|0|0.556818|False|False|False|
|risk_GEAR_mean_effective_loss_rate|294|0.556818|False|False|False|
|risk_SEAT_present|0|0.856061|False|False|False|
|risk_SEAT_severity_loss|76|0.835227|False|False|False|
|risk_SEAT_start_offset|76|0.198864|False|False|False|
|risk_SEAT_duration|76|0.810606|False|False|False|
|risk_SEAT_changed_rows|0|0.810606|False|False|False|
|risk_SEAT_mean_effective_loss_rate|76|0.835227|False|False|False|
|risk_reachable_skus|0|0.386364|False|False|False|
|risk_reachable_orders|0|0.198864|False|False|False|
|risk_reachable_configs|0|0.746212|False|False|False|
|risk_first_delivery_period|11|0.198864|False|False|False|
|risk_due_61|0|0.801136|False|False|False|
|risk_due_62|0|0.721591|False|False|False|
|risk_due_63|0|0.579545|False|False|False|
|risk_due_64|0|0.543561|False|False|False|
|risk_due_65|0|0.630682|False|False|False|
|risk_due_66|0|0.761364|False|False|False|
|risk_due_67|0|0.840909|False|False|False|
|risk_due_68|0|0.979167|False|True|False|
|risk_due_69|0|0.979167|False|True|False|
|risk_due_70|0|0.979167|False|True|False|
|risk_due_71|0|0.979167|False|True|False|
|risk_due_72|0|0.979167|False|True|False|
|risk_due_73|0|0.979167|False|True|False|
|risk_due_74|0|0.979167|False|True|False|
|buffer_C|0|0.731061|False|False|False|
|buffer_T|0|0.821970|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.731061|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420455|False|False|False|
|buffer_C_units_per_exposed_order|11|0.295455|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924242|False|False|False|
|buffer_T_timed_exposed_orders|0|0.278409|False|False|False|
|buffer_T_units_per_exposed_order|11|0.806818|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.895833|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198864|False|False|False|
|buffer_O_units_per_exposed_order|11|0.979167|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888258|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26793.0, "mean": 26113.25, "std": 1112.0993379640147, "quantiles": [21775.0, 25895.0, 26423.5, 26793.0, 26793.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25421": 1, "25895": 3, "26188": 2, "26319": 1, "26347": 2, "26500": 1, "26793": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.291667|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[354, 0, 0] heldout=[[0, 350, 0]]

预处理fit=0.002309s；两分支train/heldout变换合计=0.004493s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26635.401746724892, "std": 886.899811298205, "quantiles": [21775.0, 26465.0, 26917.0, 27050.0, 27363.0], "value_counts": {"21775": 9, "24200": 10, "25025": 9, "25413": 2, "25421": 1, "25887": 6, "25895": 3, "25991": 9, "26180": 4, "26188": 2, "26311": 2, "26319": 1, "26339": 4, "26347": 2, "26465": 60, "26500": 10, "26758": 32, "26785": 22, "26793": 11, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 7, 32: 1, 38: 1}；缺失单元格=7584。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.812227|False|False|False|
|scenario_changed_rows|0|0.796943|False|False|False|
|scenario_is_nominal_rhs|0|0.980349|False|True|False|
|risk_B_RECEIPT_present|0|0.941048|False|False|False|
|risk_B_RECEIPT_severity_loss|431|0.941048|False|False|False|
|risk_B_RECEIPT_start_offset|431|0.941048|False|False|False|
|risk_B_RECEIPT_duration|431|0.941048|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.941048|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|431|0.941048|False|False|False|
|risk_B_PROD_present|0|0.975983|False|True|False|
|risk_B_PROD_severity_loss|447|0.975983|False|True|False|
|risk_B_PROD_start_offset|447|0.975983|False|True|False|
|risk_B_PROD_duration|447|0.975983|False|True|False|
|risk_B_PROD_changed_rows|0|0.975983|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|447|0.975983|False|True|False|
|risk_B_SHIP_present|0|0.995633|False|True|False|
|risk_B_SHIP_severity_loss|456|0.995633|False|True|False|
|risk_B_SHIP_start_offset|456|0.995633|False|True|False|
|risk_B_SHIP_duration|456|0.995633|False|True|False|
|risk_B_SHIP_changed_rows|0|0.995633|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|456|0.995633|False|True|False|
|risk_ENGINE_present|0|0.545852|False|False|False|
|risk_ENGINE_severity_loss|250|0.545852|False|False|False|
|risk_ENGINE_start_offset|250|0.545852|False|False|False|
|risk_ENGINE_duration|250|0.545852|False|False|False|
|risk_ENGINE_changed_rows|0|0.545852|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|250|0.545852|False|False|False|
|risk_GEAR_present|0|0.548035|False|False|False|
|risk_GEAR_severity_loss|251|0.548035|False|False|False|
|risk_GEAR_start_offset|251|0.548035|False|False|False|
|risk_GEAR_duration|251|0.548035|False|False|False|
|risk_GEAR_changed_rows|0|0.548035|False|False|False|
|risk_GEAR_mean_effective_loss_rate|251|0.548035|False|False|False|
|risk_SEAT_present|0|0.886463|False|False|False|
|risk_SEAT_severity_loss|52|0.866812|False|False|False|
|risk_SEAT_start_offset|52|0.196507|False|False|False|
|risk_SEAT_duration|52|0.844978|False|False|False|
|risk_SEAT_changed_rows|0|0.844978|False|False|False|
|risk_SEAT_mean_effective_loss_rate|52|0.866812|False|False|False|
|risk_reachable_skus|0|0.403930|False|False|False|
|risk_reachable_orders|0|0.196507|False|False|False|
|risk_reachable_configs|0|0.742358|False|False|False|
|risk_first_delivery_period|9|0.196507|False|False|False|
|risk_due_61|0|0.803493|False|False|False|
|risk_due_62|0|0.720524|False|False|False|
|risk_due_63|0|0.593886|False|False|False|
|risk_due_64|0|0.532751|False|False|False|
|risk_due_65|0|0.620087|False|False|False|
|risk_due_66|0|0.751092|False|False|False|
|risk_due_67|0|0.834061|False|False|False|
|risk_due_68|0|0.980349|False|True|False|
|risk_due_69|0|0.980349|False|True|False|
|risk_due_70|0|0.980349|False|True|False|
|risk_due_71|0|0.980349|False|True|False|
|risk_due_72|0|0.980349|False|True|False|
|risk_due_73|0|0.980349|False|True|False|
|risk_due_74|0|0.980349|False|True|False|
|buffer_C|0|0.842795|False|False|False|
|buffer_T|0|0.947598|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.842795|False|False|False|
|buffer_C_timed_exposed_orders|0|0.406114|False|False|False|
|buffer_C_units_per_exposed_order|9|0.340611|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.941048|False|False|False|
|buffer_T_timed_exposed_orders|0|0.279476|False|False|False|
|buffer_T_units_per_exposed_order|9|0.930131|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.917031|False|False|False|
|buffer_O_timed_exposed_orders|0|0.196507|False|False|False|
|buffer_O_units_per_exposed_order|9|0.980349|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.912664|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26160.957446808512, "std": 1029.3120085548323, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 3, "24200": 4, "25025": 3, "25426": 6, "25900": 11, "26193": 6, "26324": 8, "26352": 6, "26500": 3, "26798": 44}}

候选数分布：{24: 1, 32: 1, 38: 1}；缺失单元格=1616。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.595745|False|False|False|
|scenario_changed_rows|0|0.521277|False|False|False|
|scenario_is_nominal_rhs|0|0.968085|False|True|False|
|risk_B_RECEIPT_present|0|0.840426|False|False|False|
|risk_B_RECEIPT_severity_loss|79|0.840426|False|False|False|
|risk_B_RECEIPT_start_offset|79|0.840426|False|False|False|
|risk_B_RECEIPT_duration|79|0.840426|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.840426|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|79|0.840426|False|False|False|
|risk_B_PROD_present|0|0.946809|False|False|False|
|risk_B_PROD_severity_loss|89|0.946809|False|False|False|
|risk_B_PROD_start_offset|89|0.946809|False|False|False|
|risk_B_PROD_duration|89|0.946809|False|False|False|
|risk_B_PROD_changed_rows|0|0.946809|False|False|False|
|risk_B_PROD_mean_effective_loss_rate|89|0.946809|False|False|False|
|risk_B_SHIP_present|0|0.978723|False|True|False|
|risk_B_SHIP_severity_loss|92|0.978723|False|True|False|
|risk_B_SHIP_start_offset|92|0.978723|False|True|False|
|risk_B_SHIP_duration|92|0.978723|False|True|False|
|risk_B_SHIP_changed_rows|0|0.978723|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|92|0.978723|False|True|False|
|risk_ENGINE_present|0|0.595745|False|False|False|
|risk_ENGINE_severity_loss|56|0.595745|False|False|False|
|risk_ENGINE_start_offset|56|0.595745|False|False|False|
|risk_ENGINE_duration|56|0.595745|False|False|False|
|risk_ENGINE_changed_rows|0|0.595745|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.595745|False|False|False|
|risk_GEAR_present|0|0.606383|False|False|False|
|risk_GEAR_severity_loss|57|0.606383|False|False|False|
|risk_GEAR_start_offset|57|0.606383|False|False|False|
|risk_GEAR_duration|57|0.606383|False|False|False|
|risk_GEAR_changed_rows|0|0.606383|False|False|False|
|risk_GEAR_mean_effective_loss_rate|57|0.606383|False|False|False|
|risk_SEAT_present|0|0.702128|False|False|False|
|risk_SEAT_severity_loss|28|0.670213|False|False|False|
|risk_SEAT_start_offset|28|0.297872|False|False|False|
|risk_SEAT_duration|28|0.627660|False|False|False|
|risk_SEAT_changed_rows|0|0.627660|False|False|False|
|risk_SEAT_mean_effective_loss_rate|28|0.670213|False|False|False|
|risk_reachable_skus|0|0.287234|False|False|False|
|risk_reachable_orders|0|0.212766|False|False|False|
|risk_reachable_configs|0|0.765957|False|False|False|
|risk_first_delivery_period|3|0.212766|False|False|False|
|risk_due_61|0|0.787234|False|False|False|
|risk_due_62|0|0.723404|False|False|False|
|risk_due_63|0|0.510638|False|False|False|
|risk_due_64|0|0.595745|False|False|False|
|risk_due_65|0|0.680851|False|False|False|
|risk_due_66|0|0.808511|False|False|False|
|risk_due_67|0|0.872340|False|False|False|
|risk_due_68|0|0.968085|False|True|False|
|risk_due_69|0|0.968085|False|True|False|
|risk_due_70|0|0.968085|False|True|False|
|risk_due_71|0|0.968085|False|True|False|
|risk_due_72|0|0.968085|False|True|False|
|risk_due_73|0|0.968085|False|True|False|
|risk_due_74|0|0.968085|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.489362|False|False|False|
|buffer_C_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.840426|False|False|False|
|buffer_T_timed_exposed_orders|0|0.276596|False|False|False|
|buffer_T_units_per_exposed_order|3|0.276596|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.787234|False|False|False|
|buffer_O_timed_exposed_orders|0|0.212766|False|False|False|
|buffer_O_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.765957|False|False|False|

## inner outer=[354, 0, 0] heldout=[[337, 0, 0]]

预处理fit=0.005609s；两分支train/heldout变换合计=0.008323s。

### train

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26597.277777777777, "std": 899.4167566843445, "quantiles": [21775.0, 26465.0, 26889.0, 27050.0, 27363.0], "value_counts": {"21775": 10, "24200": 12, "25025": 10, "25421": 1, "25426": 6, "25895": 3, "25900": 11, "25991": 9, "26188": 2, "26193": 6, "26319": 1, "26324": 8, "26347": 2, "26352": 6, "26465": 60, "26500": 11, "26758": 32, "26793": 11, "26798": 44, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 6, 32: 2, 38: 2}；缺失单元格=8384。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.785714|False|False|False|
|scenario_changed_rows|0|0.757937|False|False|False|
|scenario_is_nominal_rhs|0|0.980159|False|True|False|
|risk_B_RECEIPT_present|0|0.924603|False|False|False|
|risk_B_RECEIPT_severity_loss|466|0.924603|False|False|False|
|risk_B_RECEIPT_start_offset|466|0.924603|False|False|False|
|risk_B_RECEIPT_duration|466|0.924603|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.924603|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|466|0.924603|False|False|False|
|risk_B_PROD_present|0|0.972222|False|True|False|
|risk_B_PROD_severity_loss|490|0.972222|False|True|False|
|risk_B_PROD_start_offset|490|0.972222|False|True|False|
|risk_B_PROD_duration|490|0.972222|False|True|False|
|risk_B_PROD_changed_rows|0|0.972222|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|490|0.972222|False|True|False|
|risk_B_SHIP_present|0|0.992063|False|True|False|
|risk_B_SHIP_severity_loss|500|0.992063|False|True|False|
|risk_B_SHIP_start_offset|500|0.992063|False|True|False|
|risk_B_SHIP_duration|500|0.992063|False|True|False|
|risk_B_SHIP_changed_rows|0|0.992063|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|500|0.992063|False|True|False|
|risk_ENGINE_present|0|0.551587|False|False|False|
|risk_ENGINE_severity_loss|278|0.551587|False|False|False|
|risk_ENGINE_start_offset|278|0.551587|False|False|False|
|risk_ENGINE_duration|278|0.551587|False|False|False|
|risk_ENGINE_changed_rows|0|0.551587|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|278|0.551587|False|False|False|
|risk_GEAR_present|0|0.555556|False|False|False|
|risk_GEAR_severity_loss|280|0.555556|False|False|False|
|risk_GEAR_start_offset|280|0.555556|False|False|False|
|risk_GEAR_duration|280|0.555556|False|False|False|
|risk_GEAR_changed_rows|0|0.555556|False|False|False|
|risk_GEAR_mean_effective_loss_rate|280|0.555556|False|False|False|
|risk_SEAT_present|0|0.857143|False|False|False|
|risk_SEAT_severity_loss|72|0.837302|False|False|False|
|risk_SEAT_start_offset|72|0.198413|False|False|False|
|risk_SEAT_duration|72|0.813492|False|False|False|
|risk_SEAT_changed_rows|0|0.813492|False|False|False|
|risk_SEAT_mean_effective_loss_rate|72|0.837302|False|False|False|
|risk_reachable_skus|0|0.388889|False|False|False|
|risk_reachable_orders|0|0.198413|False|False|False|
|risk_reachable_configs|0|0.746032|False|False|False|
|risk_first_delivery_period|10|0.198413|False|False|False|
|risk_due_61|0|0.801587|False|False|False|
|risk_due_62|0|0.722222|False|False|False|
|risk_due_63|0|0.579365|False|False|False|
|risk_due_64|0|0.543651|False|False|False|
|risk_due_65|0|0.630952|False|False|False|
|risk_due_66|0|0.761905|False|False|False|
|risk_due_67|0|0.841270|False|False|False|
|risk_due_68|0|0.980159|False|True|False|
|risk_due_69|0|0.980159|False|True|False|
|risk_due_70|0|0.980159|False|True|False|
|risk_due_71|0|0.980159|False|True|False|
|risk_due_72|0|0.980159|False|True|False|
|risk_due_73|0|0.980159|False|True|False|
|risk_due_74|0|0.980159|False|True|False|
|buffer_C|0|0.765873|False|False|False|
|buffer_T|0|0.765873|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.765873|False|False|False|
|buffer_C_timed_exposed_orders|0|0.420635|False|False|False|
|buffer_C_units_per_exposed_order|10|0.309524|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.924603|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277778|False|False|False|
|buffer_T_units_per_exposed_order|10|0.753968|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.896825|False|False|False|
|buffer_O_timed_exposed_orders|0|0.198413|False|False|False|
|buffer_O_units_per_exposed_order|10|0.980159|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.888889|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26785.0, "mean": 26106.583333333332, "std": 1110.017339078789, "quantiles": [21775.0, 25887.0, 26419.5, 26785.0, 26785.0], "value_counts": {"21775": 2, "24200": 2, "25025": 2, "25413": 2, "25887": 6, "26180": 4, "26311": 2, "26339": 4, "26500": 2, "26785": 22}}

候选数分布：{24: 2}；缺失单元格=816。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|44|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|44|0.916667|False|False|False|
|risk_B_RECEIPT_duration|44|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|44|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|46|0.958333|False|True|False|
|risk_B_PROD_start_offset|46|0.958333|False|True|False|
|risk_B_PROD_duration|46|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|46|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|48|1.000000|True|False|True|
|risk_B_SHIP_start_offset|48|1.000000|True|False|True|
|risk_B_SHIP_duration|48|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|48|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|28|0.583333|False|False|False|
|risk_ENGINE_start_offset|28|0.583333|False|False|False|
|risk_ENGINE_duration|28|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|28|0.583333|False|False|False|
|risk_GEAR_start_offset|28|0.583333|False|False|False|
|risk_GEAR_duration|28|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|8|0.791667|False|False|False|
|risk_SEAT_start_offset|8|0.208333|False|False|False|
|risk_SEAT_duration|8|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|8|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|2|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|2|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[354, 0, 0] heldout=[[915, 0, 0]]

预处理fit=0.001180s；两分支train/heldout变换合计=0.006135s。

### train

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26138.33734939759, "std": 1065.6974330106573, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25413": 2, "25421": 1, "25426": 6, "25887": 6, "25895": 3, "25900": 11, "26180": 4, "26188": 2, "26193": 6, "26311": 2, "26319": 1, "26324": 8, "26339": 4, "26347": 2, "26352": 6, "26500": 6, "26785": 22, "26793": 11, "26798": 44}}

候选数分布：{24: 4, 32: 1, 38: 1}；缺失单元格=2840。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.626506|False|False|False|
|scenario_changed_rows|0|0.584337|False|False|False|
|scenario_is_nominal_rhs|0|0.963855|False|True|False|
|risk_B_RECEIPT_present|0|0.873494|False|False|False|
|risk_B_RECEIPT_severity_loss|145|0.873494|False|False|False|
|risk_B_RECEIPT_start_offset|145|0.873494|False|False|False|
|risk_B_RECEIPT_duration|145|0.873494|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.873494|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|145|0.873494|False|False|False|
|risk_B_PROD_present|0|0.951807|False|True|False|
|risk_B_PROD_severity_loss|158|0.951807|False|True|False|
|risk_B_PROD_start_offset|158|0.951807|False|True|False|
|risk_B_PROD_duration|158|0.951807|False|True|False|
|risk_B_PROD_changed_rows|0|0.951807|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|158|0.951807|False|True|False|
|risk_B_SHIP_present|0|0.987952|False|True|False|
|risk_B_SHIP_severity_loss|164|0.987952|False|True|False|
|risk_B_SHIP_start_offset|164|0.987952|False|True|False|
|risk_B_SHIP_duration|164|0.987952|False|True|False|
|risk_B_SHIP_changed_rows|0|0.987952|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|164|0.987952|False|True|False|
|risk_ENGINE_present|0|0.590361|False|False|False|
|risk_ENGINE_severity_loss|98|0.590361|False|False|False|
|risk_ENGINE_start_offset|98|0.590361|False|False|False|
|risk_ENGINE_duration|98|0.590361|False|False|False|
|risk_ENGINE_changed_rows|0|0.590361|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|98|0.590361|False|False|False|
|risk_GEAR_present|0|0.596386|False|False|False|
|risk_GEAR_severity_loss|99|0.596386|False|False|False|
|risk_GEAR_start_offset|99|0.596386|False|False|False|
|risk_GEAR_duration|99|0.596386|False|False|False|
|risk_GEAR_changed_rows|0|0.596386|False|False|False|
|risk_GEAR_mean_effective_loss_rate|99|0.596386|False|False|False|
|risk_SEAT_present|0|0.759036|False|False|False|
|risk_SEAT_severity_loss|40|0.722892|False|False|False|
|risk_SEAT_start_offset|40|0.240964|False|False|False|
|risk_SEAT_duration|40|0.680723|False|False|False|
|risk_SEAT_changed_rows|0|0.680723|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.722892|False|False|False|
|risk_reachable_skus|0|0.307229|False|False|False|
|risk_reachable_orders|0|0.210843|False|False|False|
|risk_reachable_configs|0|0.759036|False|False|False|
|risk_first_delivery_period|6|0.210843|False|False|False|
|risk_due_61|0|0.789157|False|False|False|
|risk_due_62|0|0.716867|False|False|False|
|risk_due_63|0|0.542169|False|False|False|
|risk_due_64|0|0.572289|False|False|False|
|risk_due_65|0|0.656627|False|False|False|
|risk_due_66|0|0.783133|False|False|False|
|risk_due_67|0|0.855422|False|False|False|
|risk_due_68|0|0.963855|False|True|False|
|risk_due_69|0|0.963855|False|True|False|
|risk_due_70|0|0.963855|False|True|False|
|risk_due_71|0|0.963855|False|True|False|
|risk_due_72|0|0.963855|False|True|False|
|risk_due_73|0|0.963855|False|True|False|
|risk_due_74|0|0.963855|False|True|False|
|buffer_C|0|0.710843|False|False|False|
|buffer_T|0|0.566265|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.566265|False|False|False|
|buffer_C_timed_exposed_orders|0|0.457831|False|False|False|
|buffer_C_units_per_exposed_order|6|0.686747|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.873494|False|False|False|
|buffer_T_timed_exposed_orders|0|0.283133|False|False|False|
|buffer_T_units_per_exposed_order|6|0.277108|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.825301|False|False|False|
|buffer_O_timed_exposed_orders|0|0.210843|False|False|False|
|buffer_O_units_per_exposed_order|6|0.963855|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.813253|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 27363.0, "mean": 26733.62694300518, "std": 801.1375175139253, "quantiles": [21775.0, 26758.0, 27050.0, 27050.0, 27363.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25991": 9, "26465": 60, "26500": 7, "26758": 32, "26889": 10, "26917": 32, "27050": 200, "27363": 17}}

候选数分布：{4: 5, 8: 5, 16: 10, 24: 4, 32: 1, 38: 1}；缺失单元格=6360。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.839378|False|False|False|
|scenario_changed_rows|0|0.821244|False|False|False|
|scenario_is_nominal_rhs|0|0.984456|False|True|False|
|risk_B_RECEIPT_present|0|0.945596|False|False|False|
|risk_B_RECEIPT_severity_loss|365|0.945596|False|False|False|
|risk_B_RECEIPT_start_offset|365|0.945596|False|False|False|
|risk_B_RECEIPT_duration|365|0.945596|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.945596|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|365|0.945596|False|False|False|
|risk_B_PROD_present|0|0.979275|False|True|False|
|risk_B_PROD_severity_loss|378|0.979275|False|True|False|
|risk_B_PROD_start_offset|378|0.979275|False|True|False|
|risk_B_PROD_duration|378|0.979275|False|True|False|
|risk_B_PROD_changed_rows|0|0.979275|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|378|0.979275|False|True|False|
|risk_B_SHIP_present|0|0.994819|False|True|False|
|risk_B_SHIP_severity_loss|384|0.994819|False|True|False|
|risk_B_SHIP_start_offset|384|0.994819|False|True|False|
|risk_B_SHIP_duration|384|0.994819|False|True|False|
|risk_B_SHIP_changed_rows|0|0.994819|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|384|0.994819|False|True|False|
|risk_ENGINE_present|0|0.538860|False|False|False|
|risk_ENGINE_severity_loss|208|0.538860|False|False|False|
|risk_ENGINE_start_offset|208|0.538860|False|False|False|
|risk_ENGINE_duration|208|0.538860|False|False|False|
|risk_ENGINE_changed_rows|0|0.538860|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|208|0.538860|False|False|False|
|risk_GEAR_present|0|0.541451|False|False|False|
|risk_GEAR_severity_loss|209|0.541451|False|False|False|
|risk_GEAR_start_offset|209|0.541451|False|False|False|
|risk_GEAR_duration|209|0.541451|False|False|False|
|risk_GEAR_changed_rows|0|0.541451|False|False|False|
|risk_GEAR_mean_effective_loss_rate|209|0.541451|False|False|False|
|risk_SEAT_present|0|0.896373|False|False|False|
|risk_SEAT_severity_loss|40|0.880829|False|False|False|
|risk_SEAT_start_offset|40|0.194301|False|False|False|
|risk_SEAT_duration|40|0.862694|False|False|False|
|risk_SEAT_changed_rows|0|0.862694|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.880829|False|False|False|
|risk_reachable_skus|0|0.417098|False|False|False|
|risk_reachable_orders|0|0.194301|False|False|False|
|risk_reachable_configs|0|0.740933|False|False|False|
|risk_first_delivery_period|6|0.194301|False|False|False|
|risk_due_61|0|0.805699|False|False|False|
|risk_due_62|0|0.722798|False|False|False|
|risk_due_63|0|0.595855|False|False|False|
|risk_due_64|0|0.531088|False|False|False|
|risk_due_65|0|0.619171|False|False|False|
|risk_due_66|0|0.751295|False|False|False|
|risk_due_67|0|0.834197|False|False|False|
|risk_due_68|0|0.984456|False|True|False|
|risk_due_69|0|0.984456|False|True|False|
|risk_due_70|0|0.984456|False|True|False|
|risk_due_71|0|0.984456|False|True|False|
|risk_due_72|0|0.984456|False|True|False|
|risk_due_73|0|0.984456|False|True|False|
|risk_due_74|0|0.984456|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.404145|False|False|False|
|buffer_C_units_per_exposed_order|6|0.404145|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.945596|False|False|False|
|buffer_T_timed_exposed_orders|0|0.277202|False|False|False|
|buffer_T_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.924870|False|False|False|
|buffer_O_timed_exposed_orders|0|0.194301|False|False|False|
|buffer_O_units_per_exposed_order|6|0.984456|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.919689|False|False|False|

## inner outer=[915, 0, 0] heldout=[[0, 345, 0]]

预处理fit=0.001084s；两分支train/heldout变换合计=0.002008s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26139.421686746988, "std": 1066.0296128313225, "quantiles": [21775.0, 25900.0, 26428.0, 26798.0, 26802.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25413": 2, "25426": 6, "25430": 1, "25887": 6, "25900": 11, "25904": 3, "26180": 4, "26193": 6, "26197": 2, "26311": 2, "26324": 8, "26328": 1, "26339": 4, "26352": 6, "26356": 2, "26500": 6, "26785": 22, "26798": 44, "26802": 11}}

候选数分布：{24: 4, 32: 1, 38: 1}；缺失单元格=2840。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.626506|False|False|False|
|scenario_changed_rows|0|0.584337|False|False|False|
|scenario_is_nominal_rhs|0|0.963855|False|True|False|
|risk_B_RECEIPT_present|0|0.873494|False|False|False|
|risk_B_RECEIPT_severity_loss|145|0.873494|False|False|False|
|risk_B_RECEIPT_start_offset|145|0.873494|False|False|False|
|risk_B_RECEIPT_duration|145|0.873494|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.873494|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|145|0.873494|False|False|False|
|risk_B_PROD_present|0|0.951807|False|True|False|
|risk_B_PROD_severity_loss|158|0.951807|False|True|False|
|risk_B_PROD_start_offset|158|0.951807|False|True|False|
|risk_B_PROD_duration|158|0.951807|False|True|False|
|risk_B_PROD_changed_rows|0|0.951807|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|158|0.951807|False|True|False|
|risk_B_SHIP_present|0|0.987952|False|True|False|
|risk_B_SHIP_severity_loss|164|0.987952|False|True|False|
|risk_B_SHIP_start_offset|164|0.987952|False|True|False|
|risk_B_SHIP_duration|164|0.987952|False|True|False|
|risk_B_SHIP_changed_rows|0|0.987952|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|164|0.987952|False|True|False|
|risk_ENGINE_present|0|0.590361|False|False|False|
|risk_ENGINE_severity_loss|98|0.590361|False|False|False|
|risk_ENGINE_start_offset|98|0.590361|False|False|False|
|risk_ENGINE_duration|98|0.590361|False|False|False|
|risk_ENGINE_changed_rows|0|0.590361|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|98|0.590361|False|False|False|
|risk_GEAR_present|0|0.596386|False|False|False|
|risk_GEAR_severity_loss|99|0.596386|False|False|False|
|risk_GEAR_start_offset|99|0.596386|False|False|False|
|risk_GEAR_duration|99|0.596386|False|False|False|
|risk_GEAR_changed_rows|0|0.596386|False|False|False|
|risk_GEAR_mean_effective_loss_rate|99|0.596386|False|False|False|
|risk_SEAT_present|0|0.759036|False|False|False|
|risk_SEAT_severity_loss|40|0.722892|False|False|False|
|risk_SEAT_start_offset|40|0.240964|False|False|False|
|risk_SEAT_duration|40|0.680723|False|False|False|
|risk_SEAT_changed_rows|0|0.680723|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.722892|False|False|False|
|risk_reachable_skus|0|0.307229|False|False|False|
|risk_reachable_orders|0|0.210843|False|False|False|
|risk_reachable_configs|0|0.759036|False|False|False|
|risk_first_delivery_period|6|0.210843|False|False|False|
|risk_due_61|0|0.789157|False|False|False|
|risk_due_62|0|0.716867|False|False|False|
|risk_due_63|0|0.542169|False|False|False|
|risk_due_64|0|0.572289|False|False|False|
|risk_due_65|0|0.656627|False|False|False|
|risk_due_66|0|0.783133|False|False|False|
|risk_due_67|0|0.855422|False|False|False|
|risk_due_68|0|0.963855|False|True|False|
|risk_due_69|0|0.963855|False|True|False|
|risk_due_70|0|0.963855|False|True|False|
|risk_due_71|0|0.963855|False|True|False|
|risk_due_72|0|0.963855|False|True|False|
|risk_due_73|0|0.963855|False|True|False|
|risk_due_74|0|0.963855|False|True|False|
|buffer_C|0|0.566265|False|False|False|
|buffer_T|0|0.566265|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.566265|False|False|False|
|buffer_C_timed_exposed_orders|0|0.457831|False|False|False|
|buffer_C_units_per_exposed_order|6|0.548193|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.873494|False|False|False|
|buffer_T_timed_exposed_orders|0|0.283133|False|False|False|
|buffer_T_units_per_exposed_order|6|0.415663|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.825301|False|False|False|
|buffer_O_timed_exposed_orders|0|0.210843|False|False|False|
|buffer_O_units_per_exposed_order|6|0.963855|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.813253|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26793.0, "mean": 26113.25, "std": 1112.0993379640147, "quantiles": [21775.0, 25895.0, 26423.5, 26793.0, 26793.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25421": 1, "25895": 3, "26188": 2, "26319": 1, "26347": 2, "26500": 1, "26793": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.291667|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[915, 0, 0] heldout=[[0, 350, 0]]

预处理fit=0.000578s；两分支train/heldout变换合计=0.001737s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26111.791666666668, "std": 1111.6619869654126, "quantiles": [21775.0, 25895.0, 26428.0, 26785.0, 26802.0], "value_counts": {"21775": 4, "24200": 4, "25025": 4, "25413": 2, "25421": 1, "25430": 1, "25887": 6, "25895": 3, "25904": 3, "26180": 4, "26188": 2, "26197": 2, "26311": 2, "26319": 1, "26328": 1, "26339": 4, "26347": 2, "26356": 2, "26500": 4, "26785": 22, "26793": 11, "26802": 11}}

候选数分布：{24: 4}；缺失单元格=1632。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|88|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|88|0.916667|False|False|False|
|risk_B_RECEIPT_duration|88|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|88|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|92|0.958333|False|True|False|
|risk_B_PROD_start_offset|92|0.958333|False|True|False|
|risk_B_PROD_duration|92|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|92|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|96|1.000000|True|False|True|
|risk_B_SHIP_start_offset|96|1.000000|True|False|True|
|risk_B_SHIP_duration|96|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|96|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|56|0.583333|False|False|False|
|risk_ENGINE_start_offset|56|0.583333|False|False|False|
|risk_ENGINE_duration|56|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|56|0.583333|False|False|False|
|risk_GEAR_start_offset|56|0.583333|False|False|False|
|risk_GEAR_duration|56|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|56|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|16|0.791667|False|False|False|
|risk_SEAT_start_offset|16|0.208333|False|False|False|
|risk_SEAT_duration|16|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|16|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|4|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|0.500000|False|False|False|
|buffer_T|0|0.750000|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.500000|False|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|4|0.239583|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|4|0.718750|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|4|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26160.957446808512, "std": 1029.3120085548323, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 3, "24200": 4, "25025": 3, "25426": 6, "25900": 11, "26193": 6, "26324": 8, "26352": 6, "26500": 3, "26798": 44}}

候选数分布：{24: 1, 32: 1, 38: 1}；缺失单元格=1616。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_C_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.595745|False|False|False|
|scenario_changed_rows|0|0.521277|False|False|False|
|scenario_is_nominal_rhs|0|0.968085|False|True|False|
|risk_B_RECEIPT_present|0|0.840426|False|False|False|
|risk_B_RECEIPT_severity_loss|79|0.840426|False|False|False|
|risk_B_RECEIPT_start_offset|79|0.840426|False|False|False|
|risk_B_RECEIPT_duration|79|0.840426|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.840426|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|79|0.840426|False|False|False|
|risk_B_PROD_present|0|0.946809|False|False|False|
|risk_B_PROD_severity_loss|89|0.946809|False|False|False|
|risk_B_PROD_start_offset|89|0.946809|False|False|False|
|risk_B_PROD_duration|89|0.946809|False|False|False|
|risk_B_PROD_changed_rows|0|0.946809|False|False|False|
|risk_B_PROD_mean_effective_loss_rate|89|0.946809|False|False|False|
|risk_B_SHIP_present|0|0.978723|False|True|False|
|risk_B_SHIP_severity_loss|92|0.978723|False|True|False|
|risk_B_SHIP_start_offset|92|0.978723|False|True|False|
|risk_B_SHIP_duration|92|0.978723|False|True|False|
|risk_B_SHIP_changed_rows|0|0.978723|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|92|0.978723|False|True|False|
|risk_ENGINE_present|0|0.595745|False|False|False|
|risk_ENGINE_severity_loss|56|0.595745|False|False|False|
|risk_ENGINE_start_offset|56|0.595745|False|False|False|
|risk_ENGINE_duration|56|0.595745|False|False|False|
|risk_ENGINE_changed_rows|0|0.595745|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|56|0.595745|False|False|False|
|risk_GEAR_present|0|0.606383|False|False|False|
|risk_GEAR_severity_loss|57|0.606383|False|False|False|
|risk_GEAR_start_offset|57|0.606383|False|False|False|
|risk_GEAR_duration|57|0.606383|False|False|False|
|risk_GEAR_changed_rows|0|0.606383|False|False|False|
|risk_GEAR_mean_effective_loss_rate|57|0.606383|False|False|False|
|risk_SEAT_present|0|0.702128|False|False|False|
|risk_SEAT_severity_loss|28|0.670213|False|False|False|
|risk_SEAT_start_offset|28|0.297872|False|False|False|
|risk_SEAT_duration|28|0.627660|False|False|False|
|risk_SEAT_changed_rows|0|0.627660|False|False|False|
|risk_SEAT_mean_effective_loss_rate|28|0.670213|False|False|False|
|risk_reachable_skus|0|0.287234|False|False|False|
|risk_reachable_orders|0|0.212766|False|False|False|
|risk_reachable_configs|0|0.765957|False|False|False|
|risk_first_delivery_period|3|0.212766|False|False|False|
|risk_due_61|0|0.787234|False|False|False|
|risk_due_62|0|0.723404|False|False|False|
|risk_due_63|0|0.510638|False|False|False|
|risk_due_64|0|0.595745|False|False|False|
|risk_due_65|0|0.680851|False|False|False|
|risk_due_66|0|0.808511|False|False|False|
|risk_due_67|0|0.872340|False|False|False|
|risk_due_68|0|0.968085|False|True|False|
|risk_due_69|0|0.968085|False|True|False|
|risk_due_70|0|0.968085|False|True|False|
|risk_due_71|0|0.968085|False|True|False|
|risk_due_72|0|0.968085|False|True|False|
|risk_due_73|0|0.968085|False|True|False|
|risk_due_74|0|0.968085|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.489362|False|False|False|
|buffer_C_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_C_bypassed_battery_resources|0|0.840426|False|False|False|
|buffer_T_timed_exposed_orders|0|0.276596|False|False|False|
|buffer_T_units_per_exposed_order|3|0.276596|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.787234|False|False|False|
|buffer_O_timed_exposed_orders|0|0.212766|False|False|False|
|buffer_O_units_per_exposed_order|3|0.968085|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.765957|False|False|False|

## inner outer=[915, 0, 0] heldout=[[337, 0, 0]]

预处理fit=0.000720s；两分支train/heldout变换合计=0.001735s。

### train

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26146.098591549297, "std": 1058.6452764101966, "quantiles": [21775.0, 25900.0, 26428.0, 26798.0, 26802.0], "value_counts": {"21775": 5, "24200": 6, "25025": 5, "25421": 1, "25426": 6, "25430": 1, "25895": 3, "25900": 11, "25904": 3, "26188": 2, "26193": 6, "26197": 2, "26319": 1, "26324": 8, "26328": 1, "26347": 2, "26352": 6, "26356": 2, "26500": 5, "26793": 11, "26798": 44, "26802": 11}}

候选数分布：{24: 3, 32: 1, 38: 1}；缺失单元格=2432。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.619718|False|False|False|
|scenario_changed_rows|0|0.570423|False|False|False|
|scenario_is_nominal_rhs|0|0.964789|False|True|False|
|risk_B_RECEIPT_present|0|0.866197|False|False|False|
|risk_B_RECEIPT_severity_loss|123|0.866197|False|False|False|
|risk_B_RECEIPT_start_offset|123|0.866197|False|False|False|
|risk_B_RECEIPT_duration|123|0.866197|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.866197|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|123|0.866197|False|False|False|
|risk_B_PROD_present|0|0.950704|False|True|False|
|risk_B_PROD_severity_loss|135|0.950704|False|True|False|
|risk_B_PROD_start_offset|135|0.950704|False|True|False|
|risk_B_PROD_duration|135|0.950704|False|True|False|
|risk_B_PROD_changed_rows|0|0.950704|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|135|0.950704|False|True|False|
|risk_B_SHIP_present|0|0.985915|False|True|False|
|risk_B_SHIP_severity_loss|140|0.985915|False|True|False|
|risk_B_SHIP_start_offset|140|0.985915|False|True|False|
|risk_B_SHIP_duration|140|0.985915|False|True|False|
|risk_B_SHIP_changed_rows|0|0.985915|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|140|0.985915|False|True|False|
|risk_ENGINE_present|0|0.591549|False|False|False|
|risk_ENGINE_severity_loss|84|0.591549|False|False|False|
|risk_ENGINE_start_offset|84|0.591549|False|False|False|
|risk_ENGINE_duration|84|0.591549|False|False|False|
|risk_ENGINE_changed_rows|0|0.591549|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|84|0.591549|False|False|False|
|risk_GEAR_present|0|0.598592|False|False|False|
|risk_GEAR_severity_loss|85|0.598592|False|False|False|
|risk_GEAR_start_offset|85|0.598592|False|False|False|
|risk_GEAR_duration|85|0.598592|False|False|False|
|risk_GEAR_changed_rows|0|0.598592|False|False|False|
|risk_GEAR_mean_effective_loss_rate|85|0.598592|False|False|False|
|risk_SEAT_present|0|0.746479|False|False|False|
|risk_SEAT_severity_loss|36|0.711268|False|False|False|
|risk_SEAT_start_offset|36|0.253521|False|False|False|
|risk_SEAT_duration|36|0.669014|False|False|False|
|risk_SEAT_changed_rows|0|0.669014|False|False|False|
|risk_SEAT_mean_effective_loss_rate|36|0.711268|False|False|False|
|risk_reachable_skus|0|0.302817|False|False|False|
|risk_reachable_orders|0|0.211268|False|False|False|
|risk_reachable_configs|0|0.760563|False|False|False|
|risk_first_delivery_period|5|0.211268|False|False|False|
|risk_due_61|0|0.788732|False|False|False|
|risk_due_62|0|0.718310|False|False|False|
|risk_due_63|0|0.535211|False|False|False|
|risk_due_64|0|0.577465|False|False|False|
|risk_due_65|0|0.661972|False|False|False|
|risk_due_66|0|0.788732|False|False|False|
|risk_due_67|0|0.859155|False|False|False|
|risk_due_68|0|0.964789|False|True|False|
|risk_due_69|0|0.964789|False|True|False|
|risk_due_70|0|0.964789|False|True|False|
|risk_due_71|0|0.964789|False|True|False|
|risk_due_72|0|0.964789|False|True|False|
|risk_due_73|0|0.964789|False|True|False|
|risk_due_74|0|0.964789|False|True|False|
|buffer_C|0|0.830986|False|False|False|
|buffer_T|0|0.661972|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.661972|False|False|False|
|buffer_C_timed_exposed_orders|0|0.464789|False|False|False|
|buffer_C_units_per_exposed_order|5|0.802817|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.866197|False|False|False|
|buffer_T_timed_exposed_orders|0|0.281690|False|False|False|
|buffer_T_units_per_exposed_order|5|0.183099|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.816901|False|False|False|
|buffer_O_timed_exposed_orders|0|0.211268|False|False|False|
|buffer_O_units_per_exposed_order|5|0.964789|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.802817|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26785.0, "mean": 26106.583333333332, "std": 1110.017339078789, "quantiles": [21775.0, 25887.0, 26419.5, 26785.0, 26785.0], "value_counts": {"21775": 2, "24200": 2, "25025": 2, "25413": 2, "25887": 6, "26180": 4, "26311": 2, "26339": 4, "26500": 2, "26785": 22}}

候选数分布：{24: 2}；缺失单元格=816。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|44|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|44|0.916667|False|False|False|
|risk_B_RECEIPT_duration|44|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|44|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|46|0.958333|False|True|False|
|risk_B_PROD_start_offset|46|0.958333|False|True|False|
|risk_B_PROD_duration|46|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|46|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|48|1.000000|True|False|True|
|risk_B_SHIP_start_offset|48|1.000000|True|False|True|
|risk_B_SHIP_duration|48|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|48|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|28|0.583333|False|False|False|
|risk_ENGINE_start_offset|28|0.583333|False|False|False|
|risk_ENGINE_duration|28|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|28|0.583333|False|False|False|
|risk_GEAR_start_offset|28|0.583333|False|False|False|
|risk_GEAR_duration|28|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|28|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|8|0.791667|False|False|False|
|risk_SEAT_start_offset|8|0.208333|False|False|False|
|risk_SEAT_duration|8|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|8|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|2|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|2|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|2|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|

## inner outer=[915, 0, 0] heldout=[[354, 0, 0]]

预处理fit=0.002880s；两分支train/heldout变换合计=0.003926s。

### train

Q分布：{"min": 21775.0, "max": 26798.0, "mean": 26138.33734939759, "std": 1065.6974330106573, "quantiles": [21775.0, 25900.0, 26426.0, 26798.0, 26798.0], "value_counts": {"21775": 6, "24200": 7, "25025": 6, "25413": 2, "25421": 1, "25426": 6, "25887": 6, "25895": 3, "25900": 11, "26180": 4, "26188": 2, "26193": 6, "26311": 2, "26319": 1, "26324": 8, "26339": 4, "26347": 2, "26352": 6, "26500": 6, "26785": 22, "26793": 11, "26798": 44}}

候选数分布：{24: 4, 32: 1, 38: 1}；缺失单元格=2840。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, buffer_O, master_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.626506|False|False|False|
|scenario_changed_rows|0|0.584337|False|False|False|
|scenario_is_nominal_rhs|0|0.963855|False|True|False|
|risk_B_RECEIPT_present|0|0.873494|False|False|False|
|risk_B_RECEIPT_severity_loss|145|0.873494|False|False|False|
|risk_B_RECEIPT_start_offset|145|0.873494|False|False|False|
|risk_B_RECEIPT_duration|145|0.873494|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.873494|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|145|0.873494|False|False|False|
|risk_B_PROD_present|0|0.951807|False|True|False|
|risk_B_PROD_severity_loss|158|0.951807|False|True|False|
|risk_B_PROD_start_offset|158|0.951807|False|True|False|
|risk_B_PROD_duration|158|0.951807|False|True|False|
|risk_B_PROD_changed_rows|0|0.951807|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|158|0.951807|False|True|False|
|risk_B_SHIP_present|0|0.987952|False|True|False|
|risk_B_SHIP_severity_loss|164|0.987952|False|True|False|
|risk_B_SHIP_start_offset|164|0.987952|False|True|False|
|risk_B_SHIP_duration|164|0.987952|False|True|False|
|risk_B_SHIP_changed_rows|0|0.987952|False|True|False|
|risk_B_SHIP_mean_effective_loss_rate|164|0.987952|False|True|False|
|risk_ENGINE_present|0|0.590361|False|False|False|
|risk_ENGINE_severity_loss|98|0.590361|False|False|False|
|risk_ENGINE_start_offset|98|0.590361|False|False|False|
|risk_ENGINE_duration|98|0.590361|False|False|False|
|risk_ENGINE_changed_rows|0|0.590361|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|98|0.590361|False|False|False|
|risk_GEAR_present|0|0.596386|False|False|False|
|risk_GEAR_severity_loss|99|0.596386|False|False|False|
|risk_GEAR_start_offset|99|0.596386|False|False|False|
|risk_GEAR_duration|99|0.596386|False|False|False|
|risk_GEAR_changed_rows|0|0.596386|False|False|False|
|risk_GEAR_mean_effective_loss_rate|99|0.596386|False|False|False|
|risk_SEAT_present|0|0.759036|False|False|False|
|risk_SEAT_severity_loss|40|0.722892|False|False|False|
|risk_SEAT_start_offset|40|0.240964|False|False|False|
|risk_SEAT_duration|40|0.680723|False|False|False|
|risk_SEAT_changed_rows|0|0.680723|False|False|False|
|risk_SEAT_mean_effective_loss_rate|40|0.722892|False|False|False|
|risk_reachable_skus|0|0.307229|False|False|False|
|risk_reachable_orders|0|0.210843|False|False|False|
|risk_reachable_configs|0|0.759036|False|False|False|
|risk_first_delivery_period|6|0.210843|False|False|False|
|risk_due_61|0|0.789157|False|False|False|
|risk_due_62|0|0.716867|False|False|False|
|risk_due_63|0|0.542169|False|False|False|
|risk_due_64|0|0.572289|False|False|False|
|risk_due_65|0|0.656627|False|False|False|
|risk_due_66|0|0.783133|False|False|False|
|risk_due_67|0|0.855422|False|False|False|
|risk_due_68|0|0.963855|False|True|False|
|risk_due_69|0|0.963855|False|True|False|
|risk_due_70|0|0.963855|False|True|False|
|risk_due_71|0|0.963855|False|True|False|
|risk_due_72|0|0.963855|False|True|False|
|risk_due_73|0|0.963855|False|True|False|
|risk_due_74|0|0.963855|False|True|False|
|buffer_C|0|0.710843|False|False|False|
|buffer_T|0|0.566265|False|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|0.566265|False|False|False|
|buffer_C_timed_exposed_orders|0|0.457831|False|False|False|
|buffer_C_units_per_exposed_order|6|0.686747|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.873494|False|False|False|
|buffer_T_timed_exposed_orders|0|0.283133|False|False|False|
|buffer_T_units_per_exposed_order|6|0.277108|False|False|False|
|buffer_T_bypassed_battery_resources|0|0.825301|False|False|False|
|buffer_O_timed_exposed_orders|0|0.210843|False|False|False|
|buffer_O_units_per_exposed_order|6|0.963855|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.813253|False|False|False|

### heldout

Q分布：{"min": 21775.0, "max": 26802.0, "mean": 26120.75, "std": 1114.446471347996, "quantiles": [21775.0, 25904.0, 26428.0, 26802.0, 26802.0], "value_counts": {"21775": 1, "24200": 1, "25025": 1, "25430": 1, "25904": 3, "26197": 2, "26328": 1, "26356": 2, "26500": 1, "26802": 11}}

候选数分布：{24: 1}；缺失单元格=408。

常量：network_nodes, network_arcs, network_recipes, network_recipe_inputs, network_order_count, network_configuration_count, network_horizon, risk_B_SHIP_present, risk_B_SHIP_severity_loss, risk_B_SHIP_start_offset, risk_B_SHIP_duration, risk_B_SHIP_changed_rows, risk_B_SHIP_mean_effective_loss_rate, buffer_C, buffer_T, buffer_O, master_budget, master_remaining_budget

近常量：scenario_is_nominal_rhs, risk_B_PROD_present, risk_B_PROD_severity_loss, risk_B_PROD_start_offset, risk_B_PROD_duration, risk_B_PROD_changed_rows, risk_B_PROD_mean_effective_loss_rate, risk_due_68, risk_due_69, risk_due_70, risk_due_71, risk_due_72, risk_due_73, risk_due_74, buffer_T_units_per_exposed_order, buffer_O_units_per_exposed_order

|feature|missing|modal fraction|constant|near constant|all missing|
|---|---:|---:|---|---|---|
|network_nodes|0|1.000000|True|False|False|
|network_arcs|0|1.000000|True|False|False|
|network_recipes|0|1.000000|True|False|False|
|network_recipe_inputs|0|1.000000|True|False|False|
|network_order_count|0|1.000000|True|False|False|
|network_configuration_count|0|1.000000|True|False|False|
|network_horizon|0|1.000000|True|False|False|
|scenario_event_count|0|0.666667|False|False|False|
|scenario_changed_rows|0|0.666667|False|False|False|
|scenario_is_nominal_rhs|0|0.958333|False|True|False|
|risk_B_RECEIPT_present|0|0.916667|False|False|False|
|risk_B_RECEIPT_severity_loss|22|0.916667|False|False|False|
|risk_B_RECEIPT_start_offset|22|0.916667|False|False|False|
|risk_B_RECEIPT_duration|22|0.916667|False|False|False|
|risk_B_RECEIPT_changed_rows|0|0.916667|False|False|False|
|risk_B_RECEIPT_mean_effective_loss_rate|22|0.916667|False|False|False|
|risk_B_PROD_present|0|0.958333|False|True|False|
|risk_B_PROD_severity_loss|23|0.958333|False|True|False|
|risk_B_PROD_start_offset|23|0.958333|False|True|False|
|risk_B_PROD_duration|23|0.958333|False|True|False|
|risk_B_PROD_changed_rows|0|0.958333|False|True|False|
|risk_B_PROD_mean_effective_loss_rate|23|0.958333|False|True|False|
|risk_B_SHIP_present|0|1.000000|True|False|False|
|risk_B_SHIP_severity_loss|24|1.000000|True|False|True|
|risk_B_SHIP_start_offset|24|1.000000|True|False|True|
|risk_B_SHIP_duration|24|1.000000|True|False|True|
|risk_B_SHIP_changed_rows|0|1.000000|True|False|False|
|risk_B_SHIP_mean_effective_loss_rate|24|1.000000|True|False|True|
|risk_ENGINE_present|0|0.583333|False|False|False|
|risk_ENGINE_severity_loss|14|0.583333|False|False|False|
|risk_ENGINE_start_offset|14|0.583333|False|False|False|
|risk_ENGINE_duration|14|0.583333|False|False|False|
|risk_ENGINE_changed_rows|0|0.583333|False|False|False|
|risk_ENGINE_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_GEAR_present|0|0.583333|False|False|False|
|risk_GEAR_severity_loss|14|0.583333|False|False|False|
|risk_GEAR_start_offset|14|0.583333|False|False|False|
|risk_GEAR_duration|14|0.583333|False|False|False|
|risk_GEAR_changed_rows|0|0.583333|False|False|False|
|risk_GEAR_mean_effective_loss_rate|14|0.583333|False|False|False|
|risk_SEAT_present|0|0.833333|False|False|False|
|risk_SEAT_severity_loss|4|0.791667|False|False|False|
|risk_SEAT_start_offset|4|0.208333|False|False|False|
|risk_SEAT_duration|4|0.750000|False|False|False|
|risk_SEAT_changed_rows|0|0.750000|False|False|False|
|risk_SEAT_mean_effective_loss_rate|4|0.791667|False|False|False|
|risk_reachable_skus|0|0.333333|False|False|False|
|risk_reachable_orders|0|0.208333|False|False|False|
|risk_reachable_configs|0|0.750000|False|False|False|
|risk_first_delivery_period|1|0.208333|False|False|False|
|risk_due_61|0|0.791667|False|False|False|
|risk_due_62|0|0.708333|False|False|False|
|risk_due_63|0|0.583333|False|False|False|
|risk_due_64|0|0.541667|False|False|False|
|risk_due_65|0|0.625000|False|False|False|
|risk_due_66|0|0.750000|False|False|False|
|risk_due_67|0|0.833333|False|False|False|
|risk_due_68|0|0.958333|False|True|False|
|risk_due_69|0|0.958333|False|True|False|
|risk_due_70|0|0.958333|False|True|False|
|risk_due_71|0|0.958333|False|True|False|
|risk_due_72|0|0.958333|False|True|False|
|risk_due_73|0|0.958333|False|True|False|
|risk_due_74|0|0.958333|False|True|False|
|buffer_C|0|1.000000|True|False|False|
|buffer_T|0|1.000000|True|False|False|
|buffer_O|0|1.000000|True|False|False|
|master_budget|0|1.000000|True|False|False|
|master_remaining_budget|0|1.000000|True|False|False|
|buffer_C_timed_exposed_orders|0|0.416667|False|False|False|
|buffer_C_units_per_exposed_order|1|0.416667|False|False|False|
|buffer_C_bypassed_battery_resources|0|0.916667|False|False|False|
|buffer_T_timed_exposed_orders|0|0.291667|False|False|False|
|buffer_T_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_T_bypassed_battery_resources|0|0.875000|False|False|False|
|buffer_O_timed_exposed_orders|0|0.208333|False|False|False|
|buffer_O_units_per_exposed_order|1|0.958333|False|True|False|
|buffer_O_bypassed_battery_resources|0|0.875000|False|False|False|
