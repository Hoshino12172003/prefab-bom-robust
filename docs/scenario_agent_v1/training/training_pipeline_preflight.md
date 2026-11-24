# 训练管线补充预检

TRAINING_PIPELINE_GO；RIDGE_ELIGIBLE；GRADIENT_BOOSTING_ELIGIBLE；PAIRWISE_RANKING_DEFERRED。

78列原始规范保持冻结；六个排除字段及其缺失指示不进入模型。历史与未来均调用ScenarioFeatureExtractorV3.extract后投影。576重放与576历史扰动检查通过，25折只在各自训练样本fit预处理，heldout只transform。

Rule与Catalog-history在五个外层折均可计算；后者只聚合外层训练Q，不读取测试Q。规则分数无vehicle单位，MAE/RMSE不适用。Catalog按不同训练policy/RHS均值聚合，重复原始调用保留。Ridge正alpha四候选，GB深1/2、叶样本8/16、最多4叶、50棵树；只由内层CV选择。

Recall@1/3保留全部并列最坏，MRR取首个最坏，tau-b保留真实Q并列且未定义值为NULL；预测同分可按名称确定展示顺序，不拆分真实Q标签。指标按完整组再按policy宏平均。预处理、预测和排序时间分开记录，不能解释为C&CG提速。

本次只执行预处理与基准可计算性检查：Ridge/GB fit=0、predict=0、Gurobi=0；不报告模型性能。嵌套模型执行路径此前经非学习替身测试，真实模型CV尚未运行。is_violating不训练；actual_disruption_loss不作监督；Oracle排序仅作hindsight参考。

全部50个分区的Q分布和78列诊断见fold_statistics.md及pipeline_audit_v1.json。近常量阈值为包括NULL的众数占比≥95%，严格常量另列；这些统计仅作审计，不据测试统计删特征或调参。常量不自动BLOCK：固定网络的结构常量属预期，零方差scale=1；全缺失训练列以0及缺失标记处理。无有效组、目标常量、维度错误、拟合失败或泄漏必须BLOCK。

旧84列、旧切分BLOCK及两份Policy CV清单均保持原字节；三份既有训练规范也保持原字节。execution manifest更新前版本保存在archive_before_supplement/。unseen-RHS与cross-network保持BLOCK；只有5个历史policy，不把576查询当独立实验单位。

复现：python -m scenario_agent.training.audit。已有补充输出拒绝覆盖。源码、原始输入及文档哈希保存在补充JSON。
