"""Frozen V1 ablations, nested policy CV, and auditable offline result export."""
import argparse
import csv
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path
import platform
from time import perf_counter

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from ..policy_cv_protocol_v1 import require
from ..v3_feature_extractor.manifest import digest, identity
from .baseline_models import CatalogHistoryBaseline, RuleBasedBaseline
from .dataset import FEATURE_SPECS, TrainingDataset
from .fold_loader import PolicyFoldLoader
from .nested_cv import training_weights
from .ranking_metrics import METRICS, evaluate_predictions, rank_groups
from .regression_models import GB_FIXED, GB_GRID, RIDGE_GRID, make_regressor
from .training_manifest import configs
from .feature_views import ViewPreprocessor, feature_views


def write_json(path,payload):
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write("\n")


def write_csv(path,rows):
    require(bool(rows),"Empty export")
    with path.open("x",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def freeze(dataset,output):
    require(not output.exists(),"Refuse overwrite of formal results")
    output.mkdir(parents=True)
    specs={s.name:asdict(s) for s in FEATURE_SPECS}
    manifest=dict(version="formal.views.1",source_view="v1.conservative78.1",source_hashes=dataset.input_hashes,
        views={v:dict(feature_names=list(names),feature_fields=[specs[n] for n in names],raw_dimensions=len(names),
            transformed_dimensions=2*len(names)) for v,names in feature_views().items()},
        preprocessing="frozen per-column mean/scale fitted on training only; projected before any estimator receives data; unused columns cannot affect selected statistics")
    protocol=dict(version="formal.nested.1",scope=dataset.outer["scope"],outer_folds=5,inner_folds=20,
        ridge_grid=list(RIDGE_GRID),gradient_boosting_grid=list(GB_GRID),gradient_boosting_fixed=GB_FIXED,
        learning_rate_grid=[GB_FIXED["learning_rate"]],search_expansion=False,selection="inner policy-macro Recall@1; first grid candidate breaks ties",
        target="Q_exact",weighting="inverse training policy/RHS repeat count, mean weight=1",
        outer_test_model_selection=False,primary_metric="worst_recall_at_1",secondary=["worst_recall_at_3","mean_reciprocal_rank"],
        decision_rules=dict(ML_YES="a model Full-78 strictly beats BOTH simple baselines in Recall@1 in >=4/5 folds, higher mean, and nonworse mean Recall@3/MRR",
            ML_NO="both Full-78 models have mean Recall@1 <= best simple baseline and <=2 strict paired wins against it",
            BOM_YES="Full-78 beats Risk+Master in >=4/5 primary folds for BOTH regressors, with nonworse mean Recall@3/MRR",
            BOM_NO="both regressors have nonpositive mean primary increment and <=2 strict wins",
            otherwise="INCONCLUSIVE; five historical policies do not support population significance",
            collapse="Recall@1=0 or Kendall tau-b<0, descriptive warning only"),
        recommendation="CATALOG_HISTORY_PROVISIONAL; fixed before training, not chosen from outer-test results; online deployment remains unvalidated",
        baseline_rule_unit="dimensionless ranking_score; Q_hat/MAE/RMSE NULL",prediction_ties="scenario name for presentation only; ground-truth ties intact",
        expected_estimator_fits=510,blas_threads=1,random_state=0,optimization_calls=0)
    write_json(output/"feature_view_manifest_v1.json",manifest)
    write_json(output/"formal_protocol_v1.json",protocol)
    return protocol


def score_export(dataset,fold,view,model,batch,scores,*,Q_units,params=None,prep=None,timing=None):
    Q=dataset.targets(batch.sample_ids)  # Only after this fold's parameters/models are locked.
    orders=rank_groups(batch,scores)
    evaluated=evaluate_predictions(batch,Q,scores,in_Q_units=Q_units,orders=orders)
    meta=dict(fold_id=fold.fold_id,test_policy=json.dumps(dataset.groups[fold.heldout_group_keys[0]]["policy"]),
        train_policies=json.dumps(sorted({dataset.groups[k]["policy"] for k in fold.training_group_keys})),
        feature_view=view,model=model,deployable=model!="oracle_hindsight",chosen_hyperparameters=json.dumps(params or {},sort_keys=True),
        preprocessing_fingerprint=identity("prep-",prep.state) if prep else "NOT_APPLICABLE")
    metric=dict(**meta,**evaluated["policy_macro"],**(timing or dict(preprocessing_seconds=0.0,prediction_seconds=0.0,sorting_seconds=0.0)))
    metric["tau_valid_groups"]=sum(r["kendall_tau_b"] is not None for r in evaluated["groups"])
    metric["tau_undefined_groups"]=sum(r["kendall_tau_b"] is None for r in evaluated["groups"])
    predictions=[]
    for key,indices in orders.items():
        pred_unique=sorted({float(scores[i]) for i in indices})
        for rank,i in enumerate(indices,1):
            row=dataset.labels_by_id[batch.sample_ids[i]]
            predictions.append(dict(fold_id=fold.fold_id,test_policy=meta["test_policy"],feature_view=view,model=model,
                sample_id=batch.sample_ids[i],group_key=key,effective_rhs_id=batch.rhs_ids[i],scenario_id=batch.scenario_ids[i],
                Q_exact=int(Q[i]),Q_hat=float(scores[i]) if Q_units else None,ranking_score=float(scores[i]),
                true_dense_rank=int(row["dense_rank"]),predicted_rank=rank,predicted_dense_rank=pred_unique.index(float(scores[i]))+1,
                is_worst=int(row["is_worst"]),deployable=meta["deployable"]))
    return metric,predictions


def timed_predict(batch,predict,prep=None,mode=None):
    start=perf_counter();X=prep.transform(batch,mode) if prep else batch
    preprocessing=perf_counter()-start if prep else 0.0
    start=perf_counter();scores=predict(X);prediction=perf_counter()-start
    start=perf_counter();rank_groups(batch,scores);sorting=perf_counter()-start
    return scores,dict(preprocessing_seconds=preprocessing,prediction_seconds=prediction,sorting_seconds=sorting)


def run(root):
    root=Path(root).resolve();dataset=TrainingDataset(root);loader=PolicyFoldLoader(dataset)
    output=root/"experiments/scenario_agent_v1/training/v1/results"
    expected,_=configs(dataset)
    require(json.loads((output.parent/"training_config_v1.json").read_text(encoding="utf-8"))==expected,"Frozen config conflict")
    protocol=freeze(dataset,output)
    metrics=[];predictions=[];selection=[];fit_calls=0;prediction_calls=0
    (output/"models").mkdir()
    with threadpool_limits(limits=1):
        for outer in loader.outer:
            locked={};chosen={}
            # No outer-test labels are accessed until all view/model parameters are locked.
            for view in feature_views():
                cached=[]
                for inner in loader.for_outer(outer.fold_id):
                    train,val=dataset.batch(inner.training_ids),dataset.batch(inner.heldout_ids)
                    prep=ViewPreprocessor(view).fit(train,fold=inner)
                    cached.append((inner,train,val,prep,dataset.targets(inner.training_ids)))
                for model,grid,mode in (("ridge",RIDGE_GRID,"ridge"),("gradient_boosting",GB_GRID,"tree")):
                    candidates=[]
                    for candidate,params in enumerate(grid):
                        scores=[]
                        for inner,train,val,prep,Q in cached:
                            estimator=make_regressor(model,params)
                            estimator.fit(prep.transform(train,mode),Q,sample_weight=training_weights(train));fit_calls+=1
                            p=estimator.predict(prep.transform(val,mode));prediction_calls+=1
                            value=evaluate_predictions(val,dataset.targets(val.sample_ids),p)["policy_macro"]["worst_recall_at_1"]
                            scores.append(value)
                            selection.append(dict(outer_fold_id=outer.fold_id,outer_test_policy=json.dumps(dataset.groups[outer.heldout_group_keys[0]]["policy"]),
                                feature_view=view,model=model,candidate=candidate,parameters=json.dumps(params,sort_keys=True),
                                inner_fold_id=inner.fold_id,validation_policy_id=val.policy_ids[0],validation_recall_at_1=value,chosen=False))
                        candidates.append(float(np.mean(scores)))
                    best=int(np.argmax(candidates));chosen[view,model]=dict(grid[best])
                    for row in selection:
                        if row["outer_fold_id"]==outer.fold_id and row["feature_view"]==view and row["model"]==model:
                            row["chosen"]=row["candidate"]==best
                    train=dataset.batch(outer.training_ids)
                    prep=ViewPreprocessor(view).fit(train,fold=outer)
                    estimator=make_regressor(model,grid[best])
                    estimator.fit(prep.transform(train,mode),dataset.targets(train.sample_ids),sample_weight=training_weights(train));fit_calls+=1
                    locked[view,model]=(prep,estimator,mode)
                    joblib.dump(dict(preprocessor=prep,model=estimator,mode=mode,training_sample_ids=train.sample_ids,
                                     feature_view=view,parameters=grid[best]),output/"models"/(outer.fold_id+"_"+view.replace("+","_")+"_"+model+".joblib"))
            print(f"Locked all models for {outer.fold_id}; final test predictions",flush=True)
            train,test=dataset.batch(outer.training_ids),dataset.batch(outer.heldout_ids)
            catalog=CatalogHistoryBaseline().fit(train,dataset.targets(train.sample_ids),fold=outer)
            joblib.dump(catalog,output/"models"/(outer.fold_id+"_catalog.joblib"))
            for name,baseline,units in (("rule",RuleBasedBaseline(),False),("catalog_history",catalog,True)):
                scores,timing=timed_predict(test,baseline.predict)
                m,p=score_export(dataset,outer,"static_catalog",name,test,scores,Q_units=units,timing=timing)
                metrics.append(m);predictions.extend(p)
            for (view,model),(prep,estimator,mode) in locked.items():
                scores,timing=timed_predict(test,estimator.predict,prep,mode);prediction_calls+=1
                m,p=score_export(dataset,outer,view,model,test,scores,Q_units=True,params=chosen[view,model],prep=prep,timing=timing)
                metrics.append(m);predictions.extend(p)
            m,p=score_export(dataset,outer,"reference","oracle_hindsight",test,dataset.targets(test.sample_ids),Q_units=True)
            metrics.append(m);predictions.extend(p)
    require(fit_calls==protocol["expected_estimator_fits"],"Unexpected fit count")
    comparison=[]
    for view,model in dict.fromkeys((m["feature_view"],m["model"]) for m in metrics):
        rows=[m for m in metrics if (m["feature_view"],m["model"])==(view,model)]
        summary=dict(feature_view=view,model=model,policy_count=len(rows))
        for name in METRICS:
            values=[r[name] for r in rows if r[name] is not None]
            summary[name]=float(np.mean(values)) if values else None
        summary["prediction_seconds"]=float(np.mean([r["prediction_seconds"] for r in rows]))
        comparison.append(summary)
    write_csv(output/"outer_fold_predictions.csv",predictions)
    write_csv(output/"outer_fold_metrics.csv",metrics)
    write_csv(output/"hyperparameter_selection.csv",selection)
    write_csv(output/"feature_ablation_metrics.csv",[m for m in metrics if m["model"] in ("ridge","gradient_boosting")])
    write_csv(output/"model_comparison.csv",comparison)
    decisions=write_reports(root,metrics,comparison,protocol)
    provenance=dict(scope=protocol["scope"],estimator_fit_calls=fit_calls,estimator_predict_calls=prediction_calls,
        outer_test_predictions_per_estimator=1,optimization_calls=0,source_input_sha256=dataset.input_hashes,
        implementation_sha256={p.relative_to(root).as_posix():digest(p) for p in Path(__file__).parent.glob("*.py")},
        dependencies={p:importlib.metadata.version(p) for p in ("numpy","scipy","scikit-learn","joblib","threadpoolctl")},
        hardware=dict(platform=platform.platform(),processor=platform.processor(),python=platform.python_version()),
        decisions=decisions,outputs_sha256={p.relative_to(root).as_posix():digest(p) for p in output.rglob("*") if p.is_file()})
    write_json(output/"formal_training_manifest.json",provenance)
    return decisions


def write_reports(root,metrics,comparison,protocol):
    lookup={(m["fold_id"],m["feature_view"],m["model"]):m for m in metrics}
    folds=list(dict.fromkeys(m["fold_id"] for m in metrics))
    def paired(view,model,other_view,other_model):
        return [lookup[f,view,model]["worst_recall_at_1"]-lookup[f,other_view,other_model]["worst_recall_at_1"] for f in folds]
    def stable(view,model,ov,om):
        delta=paired(view,model,ov,om)
        return sum(d>1e-12 for d in delta)>=4 and np.mean(delta)>1e-12 and all(np.mean([
            lookup[f,view,model][k]-lookup[f,ov,om][k] for f in folds])>=-1e-12 for k in ("worst_recall_at_3","mean_reciprocal_rank"))
    models=("ridge","gradient_boosting")
    ml_yes=any(all(stable("Full-78",m,"static_catalog",b) for b in ("rule","catalog_history")) for m in models)
    means={(r["feature_view"],r["model"]):r["worst_recall_at_1"] for r in comparison}
    best=max(("rule","catalog_history"),key=lambda b:means["static_catalog",b])
    ml_no=all(means["Full-78",m]<=means["static_catalog",best]+1e-12 and sum(d>1e-12 for d in paired("Full-78",m,"static_catalog",best))<=2 for m in models)
    bom_yes=all(stable("Full-78",m,"Risk+Master",m) for m in models)
    bom_no=all(np.mean(paired("Full-78",m,"Risk+Master",m))<=1e-12 and sum(d>1e-12 for d in paired("Full-78",m,"Risk+Master",m))<=2 for m in models)
    decisions=dict(ML_RANKING_VALUE="YES" if ml_yes else "NO" if ml_no else "INCONCLUSIVE",
        BOM_INCREMENTAL_VALUE="YES" if bom_yes else "NO" if bom_no else "INCONCLUSIVE",
        RIDGE_STATUS="OFFLINE_EVALUATED_NO_TEST_BASED_SELECTION",GRADIENT_BOOSTING_STATUS="OFFLINE_EVALUATED_NO_TEST_BASED_SELECTION",
        RECOMMENDED_V1_MODEL="CATALOG_HISTORY_PROVISIONAL_NO_ONLINE_DEPLOYMENT")
    docs=root/"docs/scenario_agent_v1/training"
    files=("formal_training_results.md","feature_ablation_results.md","model_selection_decision.md")
    require(not any((docs/f).exists() for f in files),"Refuse overwrite of formal reports")
    table="|view|model|Recall@1|Recall@3|MRR|tau-b|MAE|RMSE|\n|---|---|---:|---:|---:|---:|---:|---:|\n"
    for r in comparison:
        table+=f"|{r['feature_view']}|{r['model']}|"+"|".join("NULL" if r[k] is None else f"{r[k]:.6f}" for k in METRICS)+"|\n"
    detail="|test policy|view|model|Recall@1|Recall@3|MRR|tau-b|\n|---|---|---|---:|---:|---:|---:|\n"
    for r in metrics:
        detail+=f"|{r['test_policy']}|{r['feature_view']}|{r['model']}|"+"|".join("NULL" if r[k] is None else f"{r[k]:.6f}" for k in METRICS[:4])+"|\n"
    common="\n固定V3单网络、已知风险目录、未见完整policy。组内指标→policy宏平均→5政策等权；不是576个独立实验。并列最坏全部保留；Rule无量纲分数的Q_hat/MAE/RMSE为NULL。Oracle仅为hindsight reference。\n\n即使离线排序改善，也不能称为C&CG加速；本次Gurobi调用0，未修改正式C&CG。unseen-RHS与cross-network继续BLOCK。\n"
    texts=["# 正式离线训练结果\n\n"+table+"\n## 每折结果\n\n"+detail+common,
        "# 特征消融\n\nRisk-only=39个纯风险字段；Risk+Master=44列（增加缓冲与预算）；Full-78=78列。图可达性/订单暴露/risk_due均属于图派生，仅Full-78使用。所有视图独立内层选参，网格不因外层结果扩展。\n\n"+table,
        "# 模型选择与证据边界\n\n"+"\n".join(f"- {k}: {v}" for k,v in decisions.items())+"\n\n推荐Catalog-history是训练前固定的保守默认，不是根据外层测试挑选的赢家。Ridge/GB不直接上线；是否换模型需新的独立政策验证。\n"]
    evidence="\n|比较问题|5折配对Recall@1增量|严格改善折数|稳定改善（≥4折且次指标不降）|\n|---|---|---:|---|\n"
    comparisons=[("Ridge vs Rule","Full-78","ridge","static_catalog","rule"),
        ("Ridge vs Catalog","Full-78","ridge","static_catalog","catalog_history"),
        ("GB vs Rule","Full-78","gradient_boosting","static_catalog","rule"),
        ("GB vs Catalog","Full-78","gradient_boosting","static_catalog","catalog_history"),
        ("GB vs Ridge","Full-78","gradient_boosting","Full-78","ridge")]
    comparisons += [(f"{m}: Risk+Master vs Risk-only","Risk+Master",m,"Risk-only",m) for m in models]
    comparisons += [(f"{m}: Full vs Risk+Master","Full-78",m,"Risk+Master",m) for m in models]
    for label,v,m,ov,om in comparisons:
        delta=paired(v,m,ov,om)
        evidence+=f"|{label}|{[round(x,6) for x in delta]}|{sum(d>1e-12 for d in delta)}|{stable(v,m,ov,om)}|\n"
    collapse=[dict(test_policy=r["test_policy"],view=r["feature_view"],model=r["model"]) for r in metrics
              if r["model"]!="oracle_hindsight" and (r["worst_recall_at_1"]==0 or (r["kendall_tau_b"] is not None and r["kendall_tau_b"]<0))]
    texts[1]+=evidence+"\nFull未稳定改善时，不支持BOM独立增量价值。网络常量、图暴露和交互共同构成Full新增块，本消融不能分离其各自因果作用。\n"+common
    texts[2]+=evidence+f"\n预先定义的崩溃诊断（Recall@1=0或tau-b<0）：{json.dumps(collapse,ensure_ascii=False)}。\n\n"
    texts[2]+="|主张|所需证据|本轮证据与缺口|\n|---|---|---|\n|ML优于简单目录记忆|跨政策稳定超过两个简单基准|以上逐折配对；仅5政策，无总体显著性结论|\n|BOM有独立价值|Full稳定超过Risk+Master|上述块消融；不能单独归因网络/BOM/交互|\n|学习了政策交互|Master/交互视图稳定超过纯风险|结合Catalog比较，仅条件性证据，不能排除样本选择偏差|\n|C&CG提速|在线端到端相同认证标准对比|未验证，禁止宣称|\n"+common
    for file,text in zip(files,texts):
        with (docs/file).open("x",encoding="utf-8",newline="\n") as stream:stream.write(text)
    return decisions


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument("--allow-training",action="store_true")
    args=parser.parse_args()
    require(args.allow_training,"Explicit --allow-training required")
    print(json.dumps(run(args.root),indent=2))
