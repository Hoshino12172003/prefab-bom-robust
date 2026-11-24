"""Verify exported predictions and annotate their ceiling/claim limitations, without model inference."""
import csv
import hashlib
import json
from pathlib import Path


def read(path):
    with path.open(encoding="utf-8",newline="") as stream:return list(csv.DictReader(stream))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[2];out=root/"experiments/scenario_agent_v1/training/v1/results"
    target=out/"export_verification.json"
    assert not target.exists(),"Refuse overwrite"
    predictions=read(out/"outer_fold_predictions.csv");metrics=read(out/"outer_fold_metrics.csv")
    selections=read(out/"hyperparameter_selection.csv")
    assert len(predictions)==5184 and len(metrics)==45 and len(selections)==480
    assert len({(r['sample_id'],r['model'],r['feature_view']) for r in predictions})==5184
    assert len(list((out/'models').glob('*.joblib')))==35
    source=json.loads((root/'experiments/scenario_agent_v1/data/v3/training_dataset_manifest.json').read_text(encoding='utf-8'))
    for rel,expected in source['outputs'].items():assert sha(root/rel)==expected
    formal=json.loads((out/'formal_training_manifest.json').read_text(encoding='utf-8'))
    assert formal['estimator_fit_calls']==510 and formal['optimization_calls']==0
    assert formal['estimator_predict_calls']==510
    for rel,expected in formal['outputs_sha256'].items():assert sha(root/rel)==expected
    for rel,expected in formal['implementation_sha256'].items():
        path=root/rel
        if sha(path)!=expected:
            assert rel=='src/scenario_agent/training/training_manifest.py'
            path=root/'experiments/scenario_agent_v1/provenance/training_manifest_before_portable.py'
            assert sha(path)==expected
    extra="""

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
"""
    docs=root/'docs/scenario_agent_v1/training'
    for name in ('formal_training_results.md','feature_ablation_results.md','model_selection_decision.md'):
        with (docs/name).open('a',encoding='utf-8',newline='\n') as stream:stream.write(extra)
    evidence=dict(predictions=5184,outer_metrics=45,hyperparameter_rows=480,model_artifacts=35,
        exact_original_queries=576,unique_policy_rhs_pairs=148,formal_model_fits=510,optimization_calls=0,
        formal_manifest_sha256=sha(out/'formal_training_manifest.json'),
        postprocessing_script_sha256=sha(Path(__file__)),
        report_sha256={p.name:sha(p) for p in docs.glob('*results.md')},
        recommendation_report_sha256=sha(docs/'model_selection_decision.md'),
        portable_code_revision='Historical replay isolation only; trained implementation hashes retained in formal manifest')
    target.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
