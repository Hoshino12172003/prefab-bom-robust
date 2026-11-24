# V3 统一特征提取器设计

目录命名为 `src/scenario_agent/v3_feature_extractor/`，便于直接识别。没有另建历史专用或在线专用的第二套特征计算。

## 1. 模块与入口

| 文件 | 单一职责 |
|---|---|
| schema.py | 版本、单位、风险资源、封闭的MasterStateV3和有序FeatureSpec |
| source.py | 哈希核验、读取12表、复用固定源代码的纯数据编译、DAG、标准层重载 |
| network_features.py | 7个静态特征和结构可达传播；不认证生产可行性 |
| scenario_features.py | 40签名/38RHS核验及57个风险特征 |
| master_features.py | 10个Oracle前Master特征 |
| interaction_features.py | 10个场景/缓冲/图交互特征 |
| extractor.py | 唯一入口extract及有版本的只读FeatureVectorV3 |
| preprocessing.py | 独立fit/transform/save/load，ridge/tree模式共用原始规范 |
| manifest.py | 固定源身份与确定性ID |
| historical.py | 25份JSON的33快照/576查询关联，标签留在接口之外 |
| build.py | 标准化产物生成和统一提取器冒烟执行；不保存训练矩阵 |

入口固定为`ScenarioFeatureExtractorV3.extract(network, scenario, master_state)`。返回model_instance_id、feature_version和固定顺序values。84个字段的类型/单位/公式/来源/缺失规则见v3_feature_dictionary.md，机器可读规范在data/v3/feature_manifest_v3.json的feature_fields。

## 2. 历史与未来用法

历史构造由historical_records恢复prediction-time MasterStateV3，再调用同一个extract。未来调用示例：

```python
from pathlib import Path
from scenario_agent.v3_feature_extractor import (
    load_standardized_v3, MasterStateV3, ScenarioFeatureExtractorV3,
)
from scenario_agent.v3_feature_extractor.scenario_features import load_scenarios

repo = Path('.')
network = load_standardized_v3(repo, repo/'experiments/scenario_agent_v1/data/v3')
scenarios = load_scenarios(network)  # only audited static risk files
master = MasterStateV3(
    model_instance_id=network.model_instance_id,
    iteration_id=1, policy=(10, 5, 2),
    active_rhs_ids=(scenarios['NR'].rhs_id,), ub=28000,
    lb_before_oracle=None, run_id='future-example',
)
raw = ScenarioFeatureExtractorV3().extract(network, scenarios['B_PROD_4'], master)
```

该例不会求解Master、分离风险或预测排序，只说明新政策可用同接口。调用者以后须保证UB/前轮LB确实在Oracle前已知；输入类型拒绝未知目标字段、预算单位不一致、非法缓冲和V3.3身份。

标准层重载不需外部ZIP，但核对所有输出摘要、源代码身份、原列名和计数，随后用同一纯编译函数恢复内存结构。load_v3可从原ZIP重建，二者特征一致性有测试。

## 3. 版本与关联

model_instance_id覆盖XLSB、V3规格和固定构造/配置/风险文件摘要。feature_version为v3.features.1.0.0；实现代码摘要另存，原工作树修改不会被旧Git HEAD隐藏。

run_id区分原文件与运行；master_state_id覆盖run、轮次、政策、active RHS、UB、前轮LB及预算；oracle_call_id覆盖源文件SHA+路径+JSON指针；policy_rhs_id只用于标记重复监督信号，不删除原始调用。有效RHS哈希必须与重新计算的整数变化签名一致。aliases共享特征，但保留不同来源名。

## 4. 防泄漏与物理边界

封闭MasterStateV3只允许政策、active、当前Master UB、前轮LB等输入，不接收Oracle目标/时间/节点。labels/calls与snapshots分表。首轮LB无法初始化时留NULL，不用事后lower填充。ID、样本重复次数、标签和时间都不在84个数值特征里。

风险/缓冲的结构可达性是OR潜在暴露，不是AND可行生产。交互只报告按期结构交集、单位需求比例和电池注入位置绕过关系，不提供可行缓解量。inventory_exposure保持未实现。无GNN、强化学习或正式C&CG集成。

## 5. 预处理生命周期

原始提取器不做fit；始终保留NULL和固定列顺序。FeaturePreprocessorV3在未来训练折显式fit一次，保存参数后，预测仅load+transform。ridge执行均值插补及标准化；tree执行同一均值插补；都附加缺失flag，共168列。all-missing训练列使用0计算基准+flag，原始数据不变。

当前仅交付preprocessing_contract_v3.json（fitted=false），没有在576条上拟合参数。测试为两向量的预处理生命周期单元测试，不训练任何ML估计器。之后模型训练必须保存split ID、fit来源及独立模型摘要。

## 6. 下一阶段准入

可以用sample_manifest逐查询调用本入口构建正式X，关联oracle_labels构建y。仍须先冻结按(policy,RHS)分组的切分，不能随机把重复调用拆到两侧。单网络数据仅支持有限目录验证，不能据本任务宣称跨网络泛化或C&CG加速。
