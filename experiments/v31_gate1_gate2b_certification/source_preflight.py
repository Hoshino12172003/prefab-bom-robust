"""Audit source data and the existing V3 loader before any V3.1 solve."""

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter

import gurobipy as gp

from prefab_v25.data import NOMINAL, receipts
from prefab_v25.source import SOURCE_SHA256, load_tables
from prefab_v3.base import ASSEMBLY, source_base


def structural_leads(network, internal):
    """Propagate full recipe readiness from source entry at elapsed time zero."""
    ready = dict.fromkeys(network.external, 0)
    while True:
        updated = ready.copy()
        for arc in network.arcs:
            for product, recipe in arc.recipes.items():
                destination = (arc.destination, product)
                if destination not in internal:
                    continue
                inputs = [(arc.origin, child) for child, _ in recipe]
                if all(key in ready for key in inputs):
                    arrival = max(ready[key] for key in inputs) + arc.lead
                    updated[destination] = min(arrival, updated.get(destination, arrival))
        if updated == ready:
            return {key: ready.get(key) for key in internal}
        ready = updated


def audit_source(tables):
    base, _ = source_base(tables)
    network = base.network
    products = {p: g for p, g, _ in tables["products"]}
    nodes = {n for n, in tables["nodes"]}
    assert len(products) == len(tables["products"]) == 28049
    assert sum(group != "car" for group in products.values()) == 49
    leads = {(i, j): int(lead) for i, j, lead, _ in tables["arcs"]}
    assert len(leads) == len(tables["arcs"]) == 11

    children = defaultdict(dict)
    for mother, child, quantity in tables["BOM"]:
        assert mother in products and child in products
        assert child not in children[mother] and quantity > 0 and quantity == int(quantity)
        children[mother][child] = int(quantity)

    demands = {p: (n, int(t)) for n, p, q, t in tables["demands"] if q == 1}
    assert len(demands) == len(tables["demands"]) == 28000
    source_groups = defaultdict(set)
    for vin, (node, due) in demands.items():
        source_groups[node, due, tuple(sorted(children[vin].items()))].add(vin)
    loader_groups = {
        (g.representative.node, g.representative.due, g.representative.bom):
        {o.vin for o in g.orders}
        for g in network.groups
    }
    assert source_groups == loader_groups
    assert len(network.groups) == len(source_groups)
    assert sum(len(g.orders) for g in network.groups) == 28000
    assert all((o.node, o.due, o.bom) == (g.representative.node, g.representative.due, g.representative.bom)
               for g in network.groups for o in g.orders)

    # Recover origin/destination states directly from source operations and BOM.
    inputs = defaultdict(set)
    for node, consumed, produced, *_ in tables["operations"]:
        inputs[node, produced].add(consumed)
    items_by_group = defaultdict(set)
    for p, group in products.items():
        items_by_group[group].add(p)
    states = set()
    for i, j, _, group in tables["arcs"]:
        for p in items_by_group[group]:
            states.add((j, p))
            if group in inputs[i, group]:
                states.add((i, p))
            states.update((i, child) for child in children[p] if products[child] in inputs[i, group])
    source_opening = {(n, p) for n, p, *_ in tables["initial_inventories"]}
    source_inflow = set(tables["nodes_inflow"])
    internal = {(n, p) for n, p in states - source_inflow if products[p] != "car"}
    assert all(n in nodes and p in products for n, p in internal)
    assert source_opening <= internal
    assert len(internal) == 91 and len(source_opening) == 82
    assert internal == {k for k in network.state_keys() if base.products[k[1]] != "car"} - source_inflow
    assert all(network.initial[n, p] == q and network.inventory_bounds[n, p] == (lo, hi)
               for n, p, q, lo, hi, _ in tables["initial_inventories"])

    # Independently assign historical dispatches to their arrival periods.
    arrivals = Counter()
    for i, j, p, dispatch, quantity in tables["initial_flows"]:
        assert dispatch < min(network.periods)
        arrival = dispatch + leads[i, j]
        if arrival in network.periods:
            arrivals[j, p, arrival] += int(quantity)
    assert dict(arrivals) == receipts(network, NOMINAL)

    arcs = {a.key: a for a in network.arcs}
    for i, j, lead, _ in tables["arcs"]:
        assert arcs[i, j].lead == lead
    for i, j, period, capacity in tables["capacity_at_arc"]:
        assert arcs[i, j].capacity[period] == capacity
    assert network.product_caps == {(i, j, p, t): q for i, j, p, t, q in tables["max_flow_product_per_arc"]}
    assert network.group_caps == {(i, j, t): q for i, j, _, t, q in tables["max_flow_group_per_arc"]}
    assert all(arcs[ASSEMBLY].recipes[g.id] == g.representative.bom for g in network.groups)
    pack, = items_by_group["battery"]
    assert sorted(q for c, q in children[pack].items() if c != pack) == [4, 6, 10]
    assert dict(arcs["battery-supplier_prod", "battery-supplier_inv"].recipes[pack]) == {
        c: q for c, q in children[pack].items() if c != pack
    }
    assert len(items_by_group["seat"]) == 4
    seat = arcs["seat-supplier_prod", "seat-supplier_inv"].recipes
    for p in items_by_group["seat"]:
        child, = (c for c in children[p] if c != p)
        assert child in items_by_group["seat_componment"] and children[p][child] == 1
        assert seat[p] == ((child, 1),)
    for group in ("engine", "gear"):
        identity = arcs[f"{group}-supplier_prod", f"{group}-supplier_inv"].recipes
        assert all(set(children[p]) == {p} and identity[p] == ((p, 1),) for p in items_by_group[group])

    leads_by_state = structural_leads(network, internal)
    expected = {1: 29, 2: 66, 4: 74, 20: 77, 21: 78, 22: 79, 23: 91}
    cumulative = {h: sum(lead is not None and lead <= h for lead in leads_by_state.values()) for h in expected}
    return {
        "sheet_rows": {sheet: len(rows) for sheet, rows in tables.items()},
        "orders": {"before": len(demands), "after": sum(map(len, loader_groups.values())),
                   "exact_groups": len(source_groups)},
        "non_car_items": 49,
        "internal_states": len(internal),
        "flow_through_states_requiring_zero_inventory_in_gate1": sorted(internal - source_opening),
        "legacy_builder_has_no_explicit_ceiling": sorted(
            (n, p) for n, p in internal - source_opening if not (n == "zp7" and products[p] == "seat")),
        "historical_arrival_quantity_by_period": {
            t: sum(q for (_, _, period), q in arrivals.items() if period == t) for t in network.periods
        },
        "historical_arrival_quantity_in_horizon": sum(arrivals.values()),
        "operating_capacity_periods": sorted({int(t) for _, _, t, _ in tables["capacity_at_arc"]}),
        "operating_horizon": list(network.periods),
        "structural_time_check": {
            "scope": "source-entry-to-state lead time; capacity, initial stock and initial flows excluded",
            "status": "PASS" if cumulative == expected else "FAIL",
            "expected_cumulative_counts": expected,
            "actual_cumulative_counts": cumulative,
            "states": [{"node_id": n, "item_id": p, "group": products[p], "lead": leads_by_state[n, p]}
                       for n, p in sorted(internal)],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsb", help="Original, unmodified author workbook")
    parser.add_argument("--out", type=Path, help="Write the preflight JSON and time-only crosscheck CSV here")
    args = parser.parse_args()
    started = perf_counter()
    result = audit_source(load_tables(args.xlsb))
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
    result.update({
        "status": "PASS",
        "scope": "source and legacy loader preflight only",
        "commit_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "preflight_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": {"2020_dataset_OfAutomotiveProductionNetwork.xlsb": SOURCE_SHA256},
        "python_version": platform.python_version(),
        "gurobi_version": ".".join(map(str, gp.gurobi.version())),
        "gurobi_license_environment_started": True,
        "optimization_calls": 0,
        "random_seed": None,
        "config": {"mode": "source_preflight"},
        "runtime_seconds": perf_counter() - started,
    })
    report = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out is None:
        print(report)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "source_preflight.json").write_text(report + "\n", encoding="utf-8")
    fields = ("node_id", "item_id", "group", "lead", "H", "temporal_reachable", "quantity_status")
    with (args.out / "gate2b_reachability_crosscheck.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for h in (1, 2, 4, 20, 21, 22, 23):
            for state in result["structural_time_check"]["states"]:
                lead = state["lead"]
                writer.writerow(dict(state, H=h, temporal_reachable=lead is not None and lead <= h,
                                     quantity_status="NOT_TESTED"))


if __name__ == "__main__":
    main()
