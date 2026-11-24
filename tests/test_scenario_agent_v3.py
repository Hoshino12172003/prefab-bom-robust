"""Real frozen-input checks; no solver or ML model is imported or run."""
import csv
import json
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from scenario_agent.v3_feature_extractor import load_v3, load_standardized_v3, MasterStateV3, ScenarioFeatureExtractorV3
from scenario_agent.v3_feature_extractor.build import build, standard_tables
from scenario_agent.v3_feature_extractor.extractor import SPECS
from scenario_agent.v3_feature_extractor.historical import historical_records
from scenario_agent.v3_feature_extractor.manifest import MODEL_INSTANCE_ID, check_hash, digest
from scenario_agent.v3_feature_extractor.preprocessing import FeaturePreprocessorV3
from scenario_agent.v3_feature_extractor.scenario_features import load_scenarios
from scenario_agent.v3_feature_extractor.schema import BUDGET, COSTS, FEATURE_VERSION
from scenario_agent.v3_feature_extractor.source import check_dag

ROOT = Path(__file__).resolve().parents[1]
ZIP = Path("E:/文献阅读/论文写作/prefab/数据/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip")


@pytest.fixture(scope="session")
def network():
    return load_v3(ROOT, ZIP)


@pytest.fixture(scope="session")
def scenarios(network):
    return load_scenarios(network)


@pytest.fixture(scope="session")
def history(network, scenarios):
    return historical_records(network, scenarios)


@pytest.fixture(scope="session")
def exported(tmp_path_factory):
    out = tmp_path_factory.mktemp("scenario-v3") / "data"
    build(ROOT, ZIP, out)
    return out


def test_network_bom_layers(network, scenarios):
    tables = standard_tables(network, scenarios)
    assert [len(v) for v in tables.values()] == [12, 11, 154, 87059, 1377, 3979, 40]
    assert sum(r["is_identity_convention"] for r in tables["bom_relations_raw"]) == 49
    assert len(network.tables) == 12
    assert len(network.base.network.state_keys()) == 1421
    assert sum(1 for n, p in network.base.network.state_keys() if network.base.products[p] != "car"
               and (n, p) not in network.base.network.external) == 91


def test_manufacturing_dag_and_bad_cycle(network):
    check_dag(network.tables["BOM"])
    with pytest.raises(ValueError, match="cycle"):
        check_dag([("A", "B", 1), ("B", "A", 1)])
    check_dag([("A", "A", 1)])  # raw identity convention excluded, not a manufacturing cycle


def test_source_hash_rejects_corruption(tmp_path):
    path = tmp_path / "source"
    path.write_bytes(b"source")
    expected = digest(path)
    check_hash(path, expected)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA-256"):
        check_hash(path, expected)


def test_units_and_exact_budget(network, scenarios, history):
    arc = next(a for a in network.base.network.arcs if a.key == ("battery-supplier_prod", "battery-supplier_inv"))
    assert dict(arc.recipes["BEV"]) == {"componment_battery1": 10, "componment_battery2": 6, "componment_battery3": 4}
    state = MasterStateV3(MODEL_INSTANCE_ID, 1, (915, 0, 0), (scenarios["NR"].rhs_id,), 28000, None)
    assert state.budget-state.spent == Fraction(3, 19)
    assert state.costs == COSTS and state.budget == BUDGET
    changed = dict(scenarios["B_RECEIPT_1"].changes)
    assert changed["receipt", "battery-supplier_prod", "componment_battery1", 66] == 4735
    with pytest.raises(ValueError, match="unit"):
        replace(state, budget=Fraction(1000000))


def test_historical_join_and_sources(history):
    snapshots, calls, labels, samples, contexts, sources = history
    assert len(sources) == 25 and len(snapshots) == 33
    assert len(calls) == len(labels) == len(samples) == len(contexts) == 576
    assert len({r["oracle_call_id"] for r in calls}) == 576
    assert len({r["master_state_id"] for r in snapshots}) == 33
    assert len({r["policy_rhs_id"] for r in samples}) == 148
    assert all(r["phase"] == "separation" and r["solver_status"] == "OPTIMAL" for r in calls)
    for row in calls:
        raw = json.loads((ROOT / row["source_file"]).read_text(encoding="utf-8"))
        _, key, index = row["json_pointer"].split("/")
        original = raw[key][int(index)]
        assert original.get("evaluation", original.get("tag", "")).startswith("oracle_")
        assert digest(ROOT / row["source_file"]) == row["source_file_sha256"]


def test_previous_lb_only(history):
    snapshots, _, _, _, contexts, _ = history
    assert sum(state.lb_before_oracle is None for _, _, state in contexts) == 322
    assert sum(state.lb_before_oracle is not None for _, _, state in contexts) == 254
    assert all((s["lb_before_oracle"] is None) == (not s["lb_initialized"]) for s in snapshots)
    for s in snapshots:
        if s["iteration_id"] > 1:
            raw = json.loads((ROOT / s["source_file"]).read_text(encoding="utf-8"))
            assert s["lb_before_oracle"] == raw["iterations"][s["iteration_id"]-2]["lower"]


def test_history_online_parity_all_fields(network, scenarios, history, exported):
    extractor = ScenarioFeatureExtractorV3()
    with (exported / "master_snapshots_v3.csv").open(encoding="utf-8", newline="") as f:
        snapshots = {r["master_state_id"]: r for r in csv.DictReader(f)}
    for _, scenario, state in history[4]:
        historical = extractor.extract(network, scenario, state)
        r = snapshots[state.state_id]
        # Reconstruct through the future public input interface using only pre-query CSV fields.
        online = MasterStateV3(r["model_instance_id"], int(r["iteration_id"]),
            tuple(int(r[k]) for k in ("x_C", "x_T", "x_O")), tuple(json.loads(r["active_rhs_ids_json"])),
            int(r["ub_before_oracle"]), int(r["lb_before_oracle"]) if r["lb_before_oracle"] else None,
            budget=Fraction(r["budget"]), costs=tuple(map(Fraction, json.loads(r["costs_json"]))), run_id=r["run_id"])
        assert online.state_id == state.state_id
        predicted = extractor.extract(network, scenarios[scenario.name], online)
        assert historical.feature_version == predicted.feature_version == FEATURE_VERSION
        assert historical.as_dict() == predicted.as_dict()
        assert tuple(historical.values) == extractor.feature_names


def test_feature_spec_order_types_and_golden_semantics(network, scenarios, history):
    extractor = ScenarioFeatureExtractorV3()
    assert len(extractor.feature_names) == len(set(extractor.feature_names)) == len(SPECS)
    state = history[4][0][2]
    v = extractor.extract(network, scenarios["DE_ENGINE_61"], state).as_dict()
    assert v["scenario_event_count"] == 2
    assert v["risk_ENGINE_severity_loss"] == .5
    assert v["risk_reachable_orders"] == 28000
    assert v["buffer_O_timed_exposed_orders"] == 3003
    assert v["risk_B_PROD_severity_loss"] is None
    assert all(s.unit and s.formula and s.source and s.information_time for s in SPECS)


def test_nominal_missing_and_alias_parity(network, scenarios, history):
    extractor = ScenarioFeatureExtractorV3()
    state = history[4][0][2]
    v = extractor.extract(network, scenarios["NR"], state).as_dict()
    assert v["scenario_event_count"] == 0 and v["risk_first_delivery_period"] is None
    assert v["buffer_C_units_per_exposed_order"] is None
    for a, b in [("ES", "DE_ENGINE_61"), ("GS", "DE_GEAR_61")]:
        assert scenarios[a].rhs_id == scenarios[b].rhs_id
        assert extractor.extract(network, scenarios[a], state).as_dict() == extractor.extract(network, scenarios[b], state).as_dict()


@pytest.mark.parametrize("mode", ["ridge", "tree"])
def test_preprocessing_fit_transform_persistence(mode, network, scenarios, history, tmp_path):
    extractor = ScenarioFeatureExtractorV3()
    vectors = [extractor.extract(network, scenarios[n], history[4][0][2]) for n in ["NR", "DE_ENGINE_61"]]
    prep = FeaturePreprocessorV3(mode)
    with pytest.raises(ValueError, match="not fitted"):
        prep.transform(vectors)
    # Preprocessor-only unit test, explicitly identified test fold; no ML estimator is trained.
    prep.fit(vectors, training_split_id="unit-test-only-two-vectors")
    before = json.dumps(prep.state, sort_keys=True)
    values = prep.transform(vectors)
    assert json.dumps(prep.state, sort_keys=True) == before
    assert all(len(row) == 2*len(SPECS) for row in values)
    assert values[0][len(SPECS)+extractor.feature_names.index("risk_first_delivery_period")] == 1
    path = tmp_path / "preprocessor.json"
    prep.save(path)
    assert FeaturePreprocessorV3.load(path).transform(vectors) == values
    with pytest.raises(ValueError, match="Fit once"):
        prep.fit(vectors, training_split_id="wrong-second-fold")
    with pytest.raises(ValueError, match="version"):
        prep.transform([replace(vectors[0], feature_version="v33")])


def test_leakage_closed_input_contract(network, scenarios, history):
    extractor = ScenarioFeatureExtractorV3()
    forbidden = {"oracle_objective", "oracle_runtime", "node_count", "lower_after", "worst_ties", "added_scenario"}
    assert not forbidden & set(extractor.feature_names)
    state = history[4][0][2]
    with pytest.raises(TypeError):
        MasterStateV3(**{**state.__dict__, "oracle_objective": 999})
    with pytest.raises(ValueError):
        replace(state, lb_before_oracle=0)  # first-round after-query LB must not be supplied
    # Oracle labels/call statistics are not passed to extract and cannot affect the returned fields.
    first = extractor.extract(network, scenarios["NR"], state).as_dict()
    assert "oracle_objective" not in first


def test_v33_and_tampered_scenario_rejected(network, scenarios, history):
    extractor = ScenarioFeatureExtractorV3()
    state = history[4][0][2]
    with pytest.raises(ValueError, match="identity"):
        extractor.extract(replace(network, model_version="V3.3"), scenarios["NR"], state)
    with pytest.raises(ValueError, match="identity"):
        replace(state, model_instance_id="v33")
    with pytest.raises(ValueError, match="conflict"):
        extractor.extract(network, replace(scenarios["NR"], rhs_id="fake"), state)


def test_new_master_plan_shared_interface(network, scenarios, history):
    old = history[4][0][2]
    new = replace(old, policy=(10, 5, 2), ub=28000, run_id="future-plan-example")
    vector = ScenarioFeatureExtractorV3().extract(network, scenarios["B_PROD_4"], new).as_dict()
    assert [vector[n] for n in ("buffer_C", "buffer_T", "buffer_O")] == [10, 5, 2]
    assert vector["buffer_O_bypassed_battery_resources"] == 1
    assert vector["buffer_C_bypassed_battery_resources"] == 0


def test_artifact_manifest_integrity_and_no_overwrite(exported):
    manifest = json.loads((exported / "feature_manifest_v3.json").read_text(encoding="utf-8"))
    assert manifest["model_instance_id"] == MODEL_INSTANCE_ID
    assert not manifest["preprocessing_fitted"] and manifest["no_optimization"]
    assert all(digest(exported / name) == h for name, h in manifest["outputs"].items())
    with pytest.raises(FileExistsError):
        build(ROOT, ZIP, exported)


def test_standardized_reload_feature_parity(network, scenarios, history, exported):
    reloaded = load_standardized_v3(ROOT, exported)
    extractor = ScenarioFeatureExtractorV3()
    for _, scenario, state in history[4][::31]:
        assert extractor.extract(network, scenario, state).as_dict() == extractor.extract(reloaded, scenario, state).as_dict()


def test_deterministic_tables_and_extract(network, scenarios, history):
    tables = standard_tables(network, scenarios)
    assert tables == standard_tables(network, scenarios)
    extractor = ScenarioFeatureExtractorV3()
    for _, scenario, state in reversed(history[4][::23]):
        a = extractor.extract(network, scenario, state).as_dict()
        assert a == extractor.extract(network, scenario, state).as_dict()


def test_no_solver_import_in_isolated_loading():
    program = '''
import importlib.abc, sys
sys.path.insert(0, 'src')
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('gurobipy', 'sklearn')):
            raise RuntimeError('Forbidden solver/ML import')
sys.meta_path.insert(0, Block())
from scenario_agent.v3_feature_extractor import load_v3, ScenarioFeatureExtractorV3
from scenario_agent.v3_feature_extractor.scenario_features import load_scenarios
from scenario_agent.v3_feature_extractor.schema import MasterStateV3
from scenario_agent.v3_feature_extractor.manifest import MODEL_INSTANCE_ID
n=load_v3('.', sys.argv[1]); s=load_scenarios(n)
m=MasterStateV3(MODEL_INSTANCE_ID, 1, (10,5,2), (s['NR'].rhs_id,), 28000, None)
assert ScenarioFeatureExtractorV3().extract(n,s['NR'],m).values
'''
    result = subprocess.run([sys.executable, "-B", "-c", program, str(ZIP)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
