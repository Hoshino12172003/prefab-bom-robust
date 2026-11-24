# 特征消融

Risk-only=39个纯风险字段；Risk+Master=44列（增加缓冲与预算）；Full-78=78列。图可达性/订单暴露/risk_due均属于图派生，仅Full-78使用。所有视图独立内层选参，网格不因外层结果扩展。

|view|model|Recall@1|Recall@3|MRR|tau-b|MAE|RMSE|
|---|---|---:|---:|---:|---:|---:|---:|
|static_catalog|rule|0.923077|0.942308|1.000000|0.490724|NULL|NULL|
|static_catalog|catalog_history|0.923077|1.000000|1.000000|0.954998|160.971318|190.153851|
|Risk-only|ridge|0.923077|1.000000|1.000000|0.821905|197.902870|234.025028|
|Risk-only|gradient_boosting|0.923077|0.961538|1.000000|0.761118|381.190517|482.017660|
|Risk+Master|ridge|0.923077|1.000000|1.000000|0.829985|127.427539|161.579441|
|Risk+Master|gradient_boosting|0.923077|0.961538|1.000000|0.761118|381.190517|482.017660|
|Full-78|ridge|0.923077|1.000000|1.000000|0.846501|87.648426|104.571777|
|Full-78|gradient_boosting|0.923077|0.961538|1.000000|0.788625|367.755635|472.913911|
|reference|oracle_hindsight|0.923077|1.000000|1.000000|1.000000|0.000000|0.000000|

|比较问题|5折配对Recall@1增量|严格改善折数|稳定改善（≥4折且次指标不降）|
|---|---|---:|---|
|Ridge vs Rule|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|Ridge vs Catalog|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|GB vs Rule|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|GB vs Catalog|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|GB vs Ridge|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|ridge: Risk+Master vs Risk-only|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|gradient_boosting: Risk+Master vs Risk-only|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|ridge: Full vs Risk+Master|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|
|gradient_boosting: Full vs Risk+Master|[0.0, 0.0, 0.0, 0.0, 0.0]|0|False|

Full未稳定改善时，不支持BOM独立增量价值。网络常量、图暴露和交互共同构成Full新增块，本消融不能分离其各自因果作用。

固定V3单网络、已知风险目录、未见完整policy。组内指标→policy宏平均→5政策等权；不是576个独立实验。并列最坏全部保留；Rule无量纲分数的Q_hat/MAE/RMSE为NULL。Oracle仅为hindsight reference。

即使离线排序改善，也不能称为C&CG加速；本次Gurobi调用0，未修改正式C&CG。unseen-RHS与cross-network继续BLOCK。


## 九项比较的解释

1. Rule已经达到本数据的Recall@1/首个最坏命中上限，但Recall@3=0.9423、tau-b=0.4907，全排序弱于Catalog。
2. Catalog-history的Recall@3=1、tau-b=0.9550，简单目录历史已非常强；两类ML未稳定超过它。
3. Full-78 Ridge的MAE=87.65低于Catalog的160.97，但tau-b=0.8465更低，不能把Q数值误差改善写成最坏排序增益。
4. GB并未稳定优于Ridge，Full视图的MAE/RMSE和全排序指标均更差。
5. Risk+Master相对Risk-only没有改善主排序指标。Ridge的MAE从197.90降至127.43，仅是数值回归的描述性改进。
6. Full相对Risk+Master没有改善主排序指标；Ridge MAE进一步降至87.65、tau-b略有提高，不能据此宣称独立BOM最坏排序价值。
7. 本轮未获得可重复的BOM/交互增量排序证据，且整个Full新增块不能单独归因于BOM。
8. 预定崩溃诊断下没有Recall@1为零或tau-b为负的fold；逐折误差仍应分别阅读。
9. 未见稳定的政策交互排序增益；结果与风险目录记忆已经足够强一致，但不能证明模型内部仅记忆了目录。

所有方法和hindsight的Recall@1均为0.923077。并列最坏未被拆分时，k=1的最大召回本来可能小于1；本数据上主指标已饱和。
因此ML_RANKING_VALUE=NO、BOM_INCREMENTAL_VALUE=NO表示“本轮增量排序证据不足”，不是证明这些信息在其他数据上无用。
五个历史政策不支持总体显著性或跨网络结论；后续应以新增独立政策检验，而不是依据当前test结果扩展网格。

运行记录：首次尝试在第一个模型序列化时失败，尚未进入outer test；失败目录本地保留但不纳入正式结果。
修复仅将可序列化预处理器移至可导入模块；网格、视图和选择规则没有变动。正式完整运行拟合510次。
完成训练后增加了历史源码的隔离重放适配，不改变拟合函数、数值特征、预测或网格；训练时版本源码快照另行保留。
