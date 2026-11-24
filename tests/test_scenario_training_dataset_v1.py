"""Training-data preparation tests; no optimizer, estimator, or preprocessing fit."""
import copy
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scenario_agent import training_dataset_v1 as dataset
from scenario_agent.v3_feature_extractor import ScenarioFeatureExtractorV3
from scenario_agent.v3_feature_extractor.extractor import SPECS
from scenario_agent.v3_feature_extractor.manifest import digest
from scenario_agent.v3_feature_extractor.preprocessing import FeaturePreprocessorV3
from scenario_agent.portable import portable_replay_root

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "experiments/scenario_agent_v1/data/v3"


def read(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="session")
def prepared(tmp_path_factory):
    temp = tmp_path_factory.mktemp("training-data-v1")
    data, reports = temp / "data", temp / "reports"
    data.mkdir()
    original_manifest = json.loads((ORIGINAL / "feature_manifest_v3.json").read_text(encoding="utf-8"))
    for name in [*original_manifest["outputs"], "feature_manifest_v3.json"]:
        shutil.copy2(ORIGINAL / name, data / name)
    before = {name: digest(data / name) for name in original_manifest["outputs"]}
    original_extract = ScenarioFeatureExtractorV3.extract
    counter = []

    def counted(self, network, scenario, master):
        counter.append((scenario.name, master.state_id))
        return original_extract(self, network, scenario, master)

    def forbidden_fit(*args, **kwargs):
        raise AssertionError("Preprocessor fit is forbidden in dataset preparation")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ScenarioFeatureExtractorV3, "extract", counted)
        mp.setattr(FeaturePreprocessorV3, "fit", forbidden_fit)
        with portable_replay_root(ROOT) as replay:
            load = dataset.load_standardized_v3
            mp.setattr(dataset, "load_standardized_v3", lambda root, directory: load(replay, directory))
            manifest = dataset.build_training_dataset(ROOT, data, reports)
    assert len(counter) == 576
    assert before == {name: digest(data / name) for name in before}
    return data, reports, manifest


def test_X_84_columns_and_576_rows_no_ID(prepared):
    data, _, manifest = prepared
    X = read(data / "X_features_v1.csv")
    assert len(X) == 576 and list(X[0]) == [s.name for s in SPECS]
    assert len(X[0]) == 84 and not {"sample_id", "oracle_call_id", "effective_rhs_id", "group_key"} & X[0].keys()
    assert manifest["audit"]["feature_information_leakage_detected"] is False
    for spec in SPECS:
        for row in X:
            if row[spec.name] == "":
                assert spec.nullable
            elif spec.dtype == "int64":
                assert str(int(row[spec.name])) == row[spec.name]
            else:
                assert float(row[spec.name]) == float(row[spec.name])


def test_NULL_and_previous_LB(prepared):
    X = read(prepared[0] / "X_features_v1.csv")
    assert sum(row["master_lb_before"] == "" for row in X) == 322
    assert sum(row["master_lb_before"] != "" for row in X) == 254
    assert all(row["master_lb_initialized"] == str(int(row["master_lb_before"] != "")) for row in X)


def test_group_trace_and_exact_labels(prepared):
    data = prepared[0]
    y, groups = read(data / "y_labels_v1.csv"), read(data / "group_manifest_v1.csv")
    assert len(y) == len({r["sample_id"] for r in y}) == 576
    assert len(groups) == len({r["group_key"] for r in groups}) == 33
    assert len({r["policy_rhs_id"] for r in y}) == 148
    assert [int(r["X_data_row"]) for r in y] == list(range(1, 577))
    for group in groups:
        members = [r for r in y if r["group_key"] == group["group_key"]]
        assert len(members) == int(group["candidate_count"])
        assert set(r["sample_id"] for r in members) == set(json.loads(group["sample_ids_json"]))
        assert set(r["scenario_id"] for r in members) == set(json.loads(group["candidates_json"]))
        q_values = sorted({int(r["Q_exact"]) for r in members})
        for row in members:
            assert int(row["dense_rank"]) == q_values.index(int(row["Q_exact"]))+1
            assert int(row["is_worst"]) == int(int(row["Q_exact"]) == min(q_values))
            assert int(row["is_violating"]) == int(int(row["Q_exact"]) < int(row["U_k"])-1e-6)
            assert int(row["demand_shortfall"]) == 28000-int(row["Q_exact"])
    for row in y:
        original = json.loads((ROOT / row["source_file"]).read_text(encoding="utf-8"))
        _, field, index = row["json_pointer"].split("/")
        call = original[field][int(index)]
        assert digest(ROOT / row["source_file"]) == row["source_file_sha256"]
        assert int(row["Q_exact"]) == call.get("service", call.get("value"))


def test_nominal_loss_availability_and_formula(prepared):
    y = read(prepared[0] / "y_labels_v1.csv")
    assert sum(r["actual_disruption_loss"] != "" for r in y) == 356
    assert sum(r["actual_disruption_loss"] == "" for r in y) == 220
    for row in y:
        nominal = next((r for r in y if r["group_key"] == row["group_key"] and r["scenario_id"] == "NR"), None)
        if nominal:
            assert int(row["actual_disruption_loss"]) == int(nominal["Q_exact"])-int(row["Q_exact"])
        else:
            assert row["actual_disruption_loss"] == ""


def test_dense_ties_and_threshold_boundary():
    records = [dict(scenario_id="Z", Q_exact=5), dict(scenario_id="A", Q_exact=5), dict(scenario_id="B", Q_exact=7)]
    labels = dataset.label_group(records, 7)
    assert labels["Z"]["dense_rank"] == labels["A"]["dense_rank"] == 1
    assert labels["Z"]["is_worst"] == labels["A"]["is_worst"] == 1
    assert labels["B"]["dense_rank"] == 2 and labels["B"]["is_violating"] == 0
    assert labels["A"]["is_violating"] == 1
    assert labels["A"]["actual_disruption_loss"] is None
    with pytest.raises(ValueError, match="Repeated query"):
        dataset.label_group(records + [records[0]], 7)


def test_connection_graph_blocks_forced_split(prepared):
    split = json.loads((prepared[0] / "split_manifest_v1.json").read_text(encoding="utf-8"))
    assert split["status"] == "BLOCK" and split["connected_component_count"] == 1
    assert split["edge_count"] == 528 and len(split["common_rhs_to_all_groups"]) == 4
    assert split["same_rhs_only_component_count"] == 1
    assert split["partitions"] == dict(train=[], validation=[], test=[])
    assert set(split["group_assignments"].values()) == {None}
    assert split["leakage_free_split_certified"] is False
    assert split["baseline_training_ready"] is False


def test_aliases_link_groups_even_across_policies():
    a = dict(group_key="a", effective_rhs_ids_json=["same-rhs"], policy_json=[1,0,0], run_id="run-a", policy_family="C")
    b = dict(group_key="b", effective_rhs_ids_json=["same-rhs"], policy_json=[0,1,0], run_id="run-b", policy_family="T")
    split = dataset.split_preflight([a,b])
    assert split["connected_component_count"] == 1
    assert "shared_effective_rhs_including_aliases" in split["edges"][0]["reasons"]


def test_preprocessing_unfitted_and_order_frozen(prepared):
    spec = json.loads((prepared[0] / "preprocessing_spec_v1.json").read_text(encoding="utf-8"))
    assert spec["fitted"] is False and set(spec["parameters"].values()) == {None}
    assert spec["feature_order"] == [s.name for s in SPECS]
    assert len(spec["transformed_feature_order"]) == 168
    assert spec["id_columns_in_X"] == [] and spec["fit_status"].startswith("BLOCK")


def test_84_field_leakage_report_and_manifest_hashes(prepared):
    data, reports, manifest = prepared
    assert len(manifest["feature_leakage_audit"]) == 84
    assert all(r["audit_result"] == "PASS" for r in manifest["feature_leakage_audit"])
    assert all(r["source"] and r["formula"] and r["information_timestamp"] for r in manifest["feature_leakage_audit"])
    assert manifest["status"] == "BLOCK" and not manifest["baseline_training_ready"]
    assert manifest["optimization_calls"] == manifest["model_training_calls"] == 0
    for path, expected in manifest["outputs"].items():
        assert digest(ROOT / path) == expected
    assert "**BLOCK" in (reports / "training_dataset_audit.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="Refuse overwrite"):
        dataset.build_training_dataset(ROOT, data, reports)


def test_feature_schema_drift_stops_acceptance():
    feature_manifest = json.loads((ORIGINAL / "feature_manifest_v3.json").read_text(encoding="utf-8"))
    feature_manifest = copy.deepcopy(feature_manifest)
    feature_manifest["feature_fields"][0]["information_time"] = "after_oracle"
    with pytest.raises(ValueError, match="specification drift"):
        dataset.audit_feature_sources(ROOT, feature_manifest)


def test_no_optimizer_or_model_import():
    program = '''
import importlib.abc,sys,json
sys.path.insert(0,'src')
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith(('gurobipy','sklearn')): raise RuntimeError('Forbidden optimizer/ML import')
sys.meta_path.insert(0,Block())
from scenario_agent.training_dataset_v1 import audit_feature_sources
from pathlib import Path
m=json.loads(Path('experiments/scenario_agent_v1/data/v3/feature_manifest_v3.json').read_text(encoding='utf-8'))
assert len(audit_feature_sources(Path('.').resolve(),m))==84
'''
    result = subprocess.run([sys.executable, "-B", "-c", program], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
