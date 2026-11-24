"""Protocol checks only: no fitting, prediction, or optimizer execution."""
import copy
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from scenario_agent import policy_cv_protocol_v1 as protocol
from scenario_agent.v3_feature_extractor.manifest import digest
from scenario_agent.v3_feature_extractor.preprocessing import FeaturePreprocessorV3

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments/scenario_agent_v1/data/v3"
INPUTS = ("X_features_v1.csv", "y_labels_v1.csv", "group_manifest_v1.csv",
          "split_manifest_v1.json", "feature_manifest_v3.json", "training_dataset_manifest.json",
          "master_snapshots_v3.csv", "preprocessing_spec_v1.json")


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    temp = tmp_path_factory.mktemp("policy-cv")
    data, reports = temp / "data", temp / "reports"
    data.mkdir()
    for name in INPUTS:
        shutil.copy2(DATA / name, data / name)
    before = {name: digest(data / name) for name in INPUTS}

    def forbidden_fit(*args, **kwargs):
        raise AssertionError("Protocol generation must not fit preprocessing")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(FeaturePreprocessorV3, "fit", forbidden_fit)
        split, nested = protocol.build_policy_cv(ROOT, data, reports)
    assert before == {name: digest(data / name) for name in INPUTS}
    return data, reports, split, nested


def test_all_originals_preserved_and_no_fit(prepared):
    data, reports, split, nested = prepared
    assert {p.name for p in reports.iterdir()} == {"policy_cv_audit.md", "generalization_scope_v1.md"}
    for name in INPUTS:
        assert digest(data / name) == digest(DATA / name)
    assert digest(data / "split_manifest_v1.json") == protocol.OLD_SPLIT_SHA
    for manifest in (split, nested):
        assert manifest["fitted"] is False
        assert manifest["optimization_calls"] == manifest["model_training_calls"] == 0
        assert manifest["original_unseen_rhs_split_status"] == "BLOCKED_WITH_CURRENT_576_DATA"
    assert split["unseen_rhs_generalization"] == "UNSEEN_RHS_GENERALIZATION_BLOCKED"
    assert split["cross_network_generalization"] == "CROSS_NETWORK_GENERALIZATION_BLOCKED"


def test_five_outer_folds_cover_whole_groups_and_every_call_once(prepared):
    split = prepared[2]
    labels = protocol.read_csv(DATA / "y_labels_v1.csv")
    groups = protocol.read_csv(DATA / "group_manifest_v1.csv")
    membership = {g["group_key"]: set(json.loads(g["sample_ids_json"])) for g in groups}
    assert len(split["outer_folds"]) == 5
    all_test = Counter()
    for fold in split["outer_folds"]:
        train, test = fold["training_pool"], fold["test"]
        assert len(train["policy_ids"]) == 4 and len(test["policy_ids"]) == 1
        assert not set(train["sample_ids"]) & set(test["sample_ids"])
        assert set(train["sample_ids"]) | set(test["sample_ids"]) == {r["sample_id"] for r in labels}
        assert len(train["group_keys"])+len(test["group_keys"]) == 33
        for part in (train, test):
            assert set(part["sample_ids"]) == set().union(*(membership[k] for k in part["group_keys"]))
        all_test.update(test["sample_ids"])
    assert set(all_test.values()) == {1} and len(all_test) == 576
    assert split["query_count"] == 576 and split["policy_rhs_pairs"] == 148


def test_twenty_inner_folds_exclude_outer_test_and_fit_only_inner_train(prepared):
    split, nested = prepared[2:]
    assert len(nested["inner_folds"]) == 20
    for outer in split["outer_folds"]:
        inner = [f for f in nested["inner_folds"] if f["outer_fold_id"] == outer["fold_id"]]
        assert len(inner) == 4
        seen_validation = Counter()
        for fold in inner:
            train, val = fold["training"], fold["validation"]
            assert train["stats"]["policy_count"] == 3 and val["stats"]["policy_count"] == 1
            combined = set(train["sample_ids"]) | set(val["sample_ids"])
            assert combined == set(outer["training_pool"]["sample_ids"])
            assert not combined & set(outer["test"]["sample_ids"])
            assert set(fold["preprocessing_fit_sample_ids"]) == set(train["sample_ids"])
            seen_validation.update(val["sample_ids"])
        assert set(seen_validation.values()) == {1}


def test_no_policy_rhs_alias_or_source_identity_crosses_any_partition(prepared):
    _, _, groups, _, _ = protocol.load_inputs(ROOT, DATA)
    by_key = {g["group_key"]: g for g in groups}
    partitions = [(f["training_pool"], f["test"]) for f in prepared[2]["outer_folds"]]
    partitions += [(f["training"], f["validation"]) for f in prepared[3]["inner_folds"]]
    for a, b in partitions:
        left, right = [by_key[k] for k in a["group_keys"]], [by_key[k] for k in b["group_keys"]]
        rows_a, rows_b = [r for g in left for r in g["rows"]], [r for g in right for r in g["rows"]]
        for field in ("sample_id", "oracle_call_id", "policy_rhs_id"):
            assert not {r[field] for r in rows_a} & {r[field] for r in rows_b}
        physical_a = {(g["policy"], r["effective_rhs_id"]) for g in left for r in g["rows"]}
        physical_b = {(g["policy"], r["effective_rhs_id"]) for g in right for r in g["rows"]}
        assert not physical_a & physical_b
        assert not {(r["source_file_sha256"], r["json_pointer"]) for r in rows_a} & {
            (r["source_file_sha256"], r["json_pointer"]) for r in rows_b}
        assert protocol.separation_audit(left, right)["shared_rhs_count"] > 0


def test_fold_statistics_match_audited_source_counts(prepared):
    expected = {(0,345,0): (1,24,1,0), (0,350,0): (3,94,3,0), (337,0,0): (2,48,2,0),
                (354,0,0): (1,24,1,0), (915,0,0): (26,386,46,98)}
    for fold in prepared[2]["outer_folds"]:
        p = tuple(fold["test_policy"])
        a, b = fold["training_pool"]["stats"], fold["test"]["stats"]
        fields = ("group_count", "query_count", "is_worst_positive", "is_violating_positive")
        assert tuple(b[k] for k in fields) == expected[p]
        assert tuple(a[k]+b[k] for k in fields) == (33,576,53,98)
        assert sum(b["candidate_size_distribution"].values()) == b["group_count"]
        assert b["groups_with_tied_worst"] == (20 if p == (915,0,0) else 0)
        assert fold["trainability"]["primary_ranking"] == "GO"
        assert fold["partition_audit"]["test_rhs_with_training_labels_fraction"] == 1.0
        assert fold["partition_audit"]["catalog_known_test_rhs_without_training_labels"] == []
    partial = [f for f in prepared[3]["inner_folds"]
               if f["partition_audit"]["test_rhs_with_training_labels_fraction"] < 1]
    assert len(partial) == 2
    for fold in partial:
        assert {tuple(fold["outer_test_policy"]), tuple(fold["validation_policy"])} == {(0,350,0),(915,0,0)}
        assert fold["partition_audit"]["test_rhs_with_training_labels_fraction"] == 24/38
        assert len(fold["partition_audit"]["catalog_known_test_rhs_without_training_labels"]) == 14


def test_auxiliary_violation_is_blocked_not_masked(prepared):
    split, nested = prepared[2:]
    held915 = next(f for f in split["outer_folds"] if f["test_policy"] == [915,0,0])
    assert held915["training_pool"]["stats"]["is_violating_positive"] == 0
    assert held915["trainability"]["auxiliary_violation_fit"] == "BLOCK_NO_TWO_TRAIN_CLASSES"
    assert split["auxiliary_is_violating"] == "NO-GO_FOR_COMPLETE_NESTED_CV"
    assert all(f["trainability"]["primary_ranking"] == "GO" for f in nested["inner_folds"])
    assert any(f["trainability"]["auxiliary_violation_fit"].startswith("BLOCK") for f in nested["inner_folds"])
    assert split["policy_generalization"] == "POLICY_GENERALIZATION_GO"


def test_contextual_labels_not_mistaken_for_Q_inconsistency(prepared):
    audit = prepared[2]["label_context_audit"]
    assert audit["fields"] == {
        "Q_exact": {"varying_policy_rhs_pairs": 0, "affected_query_rows": 0},
        "dense_rank": {"varying_policy_rhs_pairs": 16, "affected_query_rows": 316},
        "is_worst": {"varying_policy_rhs_pairs": 2, "affected_query_rows": 52},
        "is_violating": {"varying_policy_rhs_pairs": 9, "affected_query_rows": 134},
    }
    assert audit["frozen_primary_training_target"].startswith("Q_exact regression")


def test_84_field_identity_review_and_78_column_firewall(prepared):
    split = prepared[2]
    audit, view = split["identifiability_audit"], split["primary_feature_view"]
    raw_order = list(protocol.read_csv(DATA / "X_features_v1.csv")[0])
    assert audit["direct_identity_columns_in_X"] == []
    assert audit["combined_identifier"]["distinct_combinations"] == 5
    assert "master_remaining_budget" in audit["individually_policy_identifying_constant_fields"]
    assert audit["cross_policy_history_queries"] == 166
    assert len(audit["cross_policy_history_groups"]) == 6
    assert view["selected_feature_order"] == [n for n in raw_order if n not in protocol.HISTORY_FIELDS]
    assert len(view["selected_feature_order"]) == 78
    assert all(n in view["selected_feature_order"] for n in ("buffer_C", "buffer_T", "buffer_O", "master_remaining_budget"))
    assert len(split["feature_policy_leakage_audit"]) == 84
    assert sum(r["policy_cv_use"] == "EXCLUDE_HISTORY" for r in split["feature_policy_leakage_audit"]) == 6
    assert "REQUIRED before any fitting" in prepared[3]["preprocessing"]["existing_preprocessor_compatibility"]


def test_cross_policy_history_trace_matches_original_json(prepared):
    for record in prepared[2]["identifiability_audit"]["cross_policy_history_groups"]:
        path = ROOT / record["source_file"]
        assert digest(path) == record["source_file_sha256"]
        source = json.loads(path.read_text(encoding="utf-8"))
        previous = source["iterations"][int(record["preceding_iteration_json_pointer"].split("/")[-1])]
        current = source["iterations"][int(record["current_iteration_json_pointer"].split("/")[-1])]
        assert previous["policy"] == record["preceding_policy"] == [915,0,0]
        assert current["policy"] == record["current_policy"] != previous["policy"]


def test_rejects_duplicate_calls_and_incomplete_groups():
    _, _, groups, _, _ = protocol.load_inputs(ROOT, DATA)
    train = [g for g in groups if g["policy"] == (915,0,0)]
    test = copy.deepcopy([g for g in groups if g["policy"] == (0,350,0)])
    test[0]["rows"][0]["sample_id"] = train[0]["rows"][0]["sample_id"]
    with pytest.raises(ValueError, match="duplicate: sample_id"):
        protocol.separation_audit(train, test)
    assert protocol.trainability([], test)["primary_ranking"] == "BLOCK"


def test_refuses_overwrite_and_hash_drift(prepared, tmp_path):
    data, reports = prepared[:2]
    with pytest.raises(ValueError, match="Refuse overwrite"):
        protocol.build_policy_cv(ROOT, data, reports)
    for name in INPUTS:
        shutil.copy2(DATA / name, tmp_path / name)
    with (tmp_path / "split_manifest_v1.json").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="Original blocked split changed"):
        protocol.load_inputs(ROOT, tmp_path)


def test_protocol_dependency_graph_does_not_import_model_or_optimizer():
    script = """
import sys
class Guard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'gurobipy', 'sklearn', 'xgboost', 'lightgbm'}:
            raise AssertionError('Forbidden import: '+fullname)
sys.meta_path.insert(0, Guard())
from pathlib import Path
from scenario_agent.policy_cv_protocol_v1 import load_inputs
load_inputs(Path.cwd(), Path('experiments/scenario_agent_v1/data/v3'))
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
