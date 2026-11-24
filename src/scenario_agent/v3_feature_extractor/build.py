"""Build the audited data layers; no feature matrix, fit, or optimization."""
import argparse
import csv
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from .extractor import ScenarioFeatureExtractorV3, SPECS
from .historical import historical_records
from .manifest import (MODEL_INSTANCE_ID, MODEL_SPEC, SOURCE_HASHES, XLSB_SHA256, ZIP_SHA256,
                       canonical, digest, identity)
from .schema import FEATURE_VERSION
from .source import load_v3, check_dag
from .scenario_features import load_scenarios


def arc_id(arc):
    return "->".join(arc.key)


def standard_tables(network, scenarios):
    t, base = network.tables, network.base
    net = base.network
    nodes, arcs, periods, relations, recipes, inputs, catalog = [], [], [], [], [], [], []
    product_groups = {p: g for p, g, _ in t["products"]}
    cap_rows = {(i, j, int(period)): index+2 for index, (i, j, period, _) in enumerate(t["capacity_at_arc"])}
    bom_rows = {}
    for index, (parent, child, q) in enumerate(t["BOM"]):
        bom_rows.setdefault(parent, []).append(index+2)
        if parent == child and q != 1:
            raise ValueError("Nonunit BOM identity convention")
        relations.append(dict(mother=parent, child=child, quantity=int(q),
            is_identity_convention=parent == child,
            treatment="exclude_manufacturing_self_loop" if parent == child else "retain_dependency",
            quantity_unit="child_unit/parent_unit", source_sheet="BOM", source_row=index+2))
    for index, (node,) in enumerate(t["nodes"]):
        role = ("assembly" if node == "zp7" else "delivery" if node == "zp8" else
                "production" if node.endswith("_prod") else "inventory" if node.endswith("_inv") else "source_transport")
        nodes.append(dict(node_id=node, role=role,
            in_degree=sum(a.destination == node for a in net.arcs), out_degree=sum(a.origin == node for a in net.arcs),
            external_skus_json=[p for n, p in net.external if n == node], source_sheet="nodes", source_row=index+2))
    cohorts = {g.id: g for g in net.groups}
    operation_refs = {}
    for index, (node, _, output_group, *_) in enumerate(t["operations"]):
        operation_refs.setdefault((node, output_group), []).append(index+2)
    for index, a in enumerate(net.arcs):
        output_group = t["arcs"][index][3]
        kind = "assembly" if a.key == ("zp7", "zp8") else "production" if a.origin.endswith("_prod") else "transport"
        arcs.append(dict(arc_id=arc_id(a), origin=a.origin, destination=a.destination,
            lead_periods=a.lead, output_group=output_group, resource_type=kind,
            quantity_unit=f"{output_group}_unit", source_sheet="arcs", source_row=index+2))
        for period in net.periods:
            periods.append(dict(arc_id=arc_id(a), period=period, capacity=a.capacity[period],
                capacity_unit=f"{output_group}_unit/period", group_flow_cap=net.group_caps.get((*a.key, period)),
                has_group_flow_cap=(*a.key, period) in net.group_caps,
                product_flow_caps_json=[[p, q] for (i, j, p, day), q in net.product_caps.items()
                                        if (i, j, day) == (*a.key, period)],
                source_sheet="capacity_at_arc", source_row=cap_rows[*a.key, period]))
        for output, recipe in a.recipes.items():
            rid = identity("recipe-", [MODEL_INSTANCE_ID, a.key, output])
            mothers = [o.vin for o in cohorts[output].orders] if output in cohorts else [output]
            same = recipe == ((output, 1),)
            recipes.append(dict(recipe_id=rid, arc_id=arc_id(a), output_sku_id=output,
                output_group=base.products[output], output_quantity=1, kind="same_sku_transfer" if same else kind,
                original_mother_ids_json=mothers,
                source_bom_rows_json=[row for m in mothers for row in bom_rows.get(m, [])],
                source_operation_rows_json=operation_refs[a.origin, output_group],
                normalization="pinned_operation_recipes; per_one_output; no_extra_generic_consumption"))
            for child, coefficient in recipe:
                inputs.append(dict(recipe_id=rid, input_sku_id=child, consume_node=a.origin,
                    produce_node=a.destination, coefficient_num=coefficient.numerator,
                    coefficient_den=coefficient.denominator, unit="input_sku_unit/output_sku_unit"))
    for index, s in enumerate(scenarios.values()):
        catalog.append(dict(scenario_id=s.name, representative_id=s.representative, effective_rhs_id=s.rhs_id,
            raw_events_json=s.events, effective_changes_json=s.changes, event_count=len(s.events),
            changed_rows=len(s.changes), recovery="ABRUPT", source_row=index+2,
            source_file="artifacts/v3_phase32b_20261111_214914/rhs_equivalence_audit.csv"))
    result = dict(network_nodes_v3=nodes, network_arcs_v3=arcs, arc_periods_v3=periods,
        bom_relations_raw=relations, bom_recipes_v3=recipes, bom_recipe_inputs_v3=inputs, scenario_catalog_v3=catalog)
    expected = (12, 11, 154, 87059, 1377, 3979, 40)
    if tuple(map(len, result.values())) != expected or sum(r["is_identity_convention"] for r in relations) != 49:
        raise ValueError("Standardized data count conflict")
    check_dag(t["BOM"])
    for rows in result.values():
        for row in rows:
            row.update(model_instance_id=MODEL_INSTANCE_ID, source_xlsb_sha256=XLSB_SHA256)
    return result


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if v is None else str(v).lower() if isinstance(v, bool)
                else canonical(v) if isinstance(v, (list, tuple, dict)) else v for k, v in row.items()})


def build(root, source_zip, out):
    root, out = Path(root), Path(out)
    if out.exists():
        raise FileExistsError(f"Preserve existing artifacts: choose a new output directory: {out}")
    network = load_v3(root, source_zip)
    scenarios = load_scenarios(network)
    tables = standard_tables(network, scenarios)
    snapshots, calls, labels, samples, contexts, sources = historical_records(network, scenarios)
    tables.update(master_snapshots_v3=snapshots, oracle_calls_v3=calls, oracle_labels_v3=labels, sample_manifest_v3=samples)
    extractor = ScenarioFeatureExtractorV3()
    # Exercise the same public method; deliberately do NOT save a training feature matrix.
    for _, scenario, state in contexts:
        extractor.extract(network, scenario, state)
    out.mkdir(parents=True)
    for name, rows in tables.items():
        write_csv(out / f"{name}.csv", rows)
    # Lossless workbook layer retains ALL twelve sheets, including sparse constraints and units' source fields.
    (out / "source_workbook_v3.json").write_text(canonical(dict(
        model_instance_id=MODEL_INSTANCE_ID, xlsb_sha256=XLSB_SHA256,
        columns=network.columns, tables=network.tables))+"\n", encoding="utf-8")
    contract = dict(feature_version=FEATURE_VERSION, modes=["ridge", "tree"], fitted=False,
        fit_scope="explicit_training_fold_only", predict="transform_only", raw_null="empty CSV cell / JSON null",
        processed_null="training_fold_mean + appended missing flag; all-missing training column baseline 0 with flag",
        persistence="FeaturePreprocessorV3.save/load; no parameters fitted during data conversion")
    (out / "preprocessing_contract_v3.json").write_text(canonical(contract)+"\n", encoding="utf-8")
    code = {p.relative_to(root).as_posix(): digest(p) for p in sorted((root / "src/scenario_agent").rglob("*.py"))}
    manifest = dict(model_instance_id=MODEL_INSTANCE_ID, model_spec=MODEL_SPEC, feature_version=FEATURE_VERSION,
        source_zip_sha256=ZIP_SHA256, source_xlsb_sha256=XLSB_SHA256, pinned_sources=SOURCE_HASHES,
        historical_sources=sources, extractor_code_sha256=code,
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        counts={k: len(v) for k, v in tables.items()}, effective_rhs_count=38,
        ranking_groups=33, policy_rhs_pairs=148, first_round_null_lb=322, certified_previous_lb=254,
        no_optimization=True, no_model_training=True, preprocessing_fitted=False,
        feature_fields=[asdict(s) for s in SPECS],
        source_sheet_columns=network.columns,
        csv_contract=dict(null="empty cell", boolean="true/false", nested="JSON", rational="exact numerator/denominator string"),
        units=dict(time="period", policy=["complete_cell_kit", "Pack", "Pack"],
                   budget="normalized_investment", service="vehicle", bom="child_sku_unit/parent_sku_unit"),
        formulas=dict(receipt_period="dispatch + arc.lead", budget_remaining="17388/19 - x_C - 27*x_T/19 - 297*x_O/190",
            cells_to_kits="min(q1//10,q2//6,q3//4); material ceiling, NOT feasible production",
            effective_rhs="floor(nominal*(1-loss_fraction))", first_lb="NULL, never current iteration lower"),
        unimplemented=["inventory_exposure", "feasible_buffer_mitigation", "recovery_backlog", "economic_features", "GNN"],
        outputs={p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    (out / "feature_manifest_v3.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.root, args.source_zip, args.out)
    print(json.dumps(dict(model_instance_id=manifest["model_instance_id"], counts=manifest["counts"]), indent=2))


if __name__ == "__main__":
    main()
