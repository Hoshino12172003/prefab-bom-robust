"""Read the frozen workbook without executing macros or changing the source."""
from collections import defaultdict
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from .data import (Arc, Network, Order, aggregate, receipts, NOMINAL, CELL, PACK, PROD,
                   OEM, COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC)

SOURCE_NAME = "2020_dataset_OfAutomotiveProductionNetwork.xlsb"
SOURCE_SHA256 = "1ea0bcdea3225d308be913c9ca0f377585e1863847c78d6e8eec10b6de82889e"
HEADERS = {
    "products": "product_p group_g transportation_size_s",
    "nodes": "node_n",
    "nodes_inflow": "node_n product_p",
    "arcs": "starting_node_i ending_node_j process_lead_time_l_ij group_g",
    "capacity_at_arc": "starting_node_i ending_node_j period_t capacity_c_ijt",
    "max_flow_product_per_arc": "starting_node_i ending_node_j product_p period_t planned_flow",
    "max_flow_group_per_arc": "starting_node_i ending_node_j group_g period_t planned_flow",
    "operations": "node_n input_product_group_x output_product_group_y input_quantity_in_nxy output_quantity_out_nxy alpha_nxy beta_nxy",
    "BOM": "mother child individual_input_quantity_q_mc",
    "demands": "node_n product_p demand_d_npt period_t",
    "initial_inventories": "node_n product_p initial_inventory_I_np0 safety_stock max_inventory period_t",
    "initial_flows": "starting_node_i ending_node_j product_p period_t initial_flow",
}


def verified_bytes(path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.rsplit("/", 1)[-1] == SOURCE_NAME]
            if len(members) != 1:
                raise ValueError("expected exactly one original XLSB in the archive")
            payload = archive.read(members[0])
    else:
        payload = path.read_bytes()
    digest = sha256(payload).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"XLSB SHA-256 mismatch: {digest}")
    return payload


def load_tables(path):
    payload = verified_bytes(path)
    from pyxlsb import open_workbook
    tables = {}
    with open_workbook(BytesIO(payload)) as workbook:
        if set(workbook.sheets) != set(HEADERS) or len(workbook.sheets) != 12:
            raise ValueError("source sheet set mismatch")
        for name in workbook.sheets:
            with workbook.get_sheet(name) as sheet:
                rows = (tuple(cell.v for cell in row) for row in sheet.rows(sparse=True))
                if next(rows) != tuple(HEADERS[name].split()):
                    raise ValueError(f"{name}: source header mismatch")
                tables[name] = tuple(rows)
    return tables


def integer(value):
    if not isinstance(value, (int, float)) or value < 0 or value != int(value):
        raise ValueError(f"expected nonnegative integer quantity, got {value!r}")
    return int(value)


def compile_network(tables):
    periods = tuple(range(61, 75))
    product_types = {item: group for item, group, _ in tables["products"]}
    bom = defaultdict(list)
    for parent, child, quantity in tables["BOM"]:
        if parent != child:
            bom[parent].append((child, integer(quantity)))
        elif integer(quantity) != 1:
            raise ValueError(f"unexpected non-unit identity BOM row for {parent}")
    orders = []
    for node, vin, quantity, due in tables["demands"]:
        if quantity != 1 or product_types[vin] != "car" or not bom[vin]:
            raise ValueError("source VIN is not an individual configured order")
        orders.append(Order(vin, node, integer(due), tuple(sorted(bom[vin]))))
    vins = {order.vin for order in orders}
    if len(vins) != len(orders):
        raise ValueError("duplicate VIN order")
    # The frozen sheets have no other VIN-specific coefficients.
    if (any(row[2] in vins for row in tables["max_flow_product_per_arc"] + tables["initial_flows"])
            or any(row[1] in vins for row in tables["initial_inventories"] + tables["nodes_inflow"])
            or any(child in vins for _, child, _ in tables["BOM"])
            or any(size != 0 for item, _, size in tables["products"] if item in vins)):
        raise ValueError("VIN-specific terms require an expanded aggregation signature")
    groups = aggregate(orders)
    bev_orders = [order for order in orders if any(child == PACK for child, _ in order.bom)]
    counts = len(orders), len(groups), len(bev_orders), len(aggregate(bev_orders))
    if counts != (28000, 1286, 3003, 28):
        raise ValueError(f"source order count gate: {counts}")
    arcs = []
    for origin, destination, lead, output_type in tables["arcs"]:
        operations = {input_type: integer(out) for node, input_type, output, _, out, _, beta
                      in tables["operations"] if (node, output) == (origin, output_type) and beta == 1}
        identity = [(integer(inc), integer(out)) for node, input_type, output, inc, out, _, beta
                    in tables["operations"] if (node, input_type, output, beta) == (origin, output_type, output_type, 1)]
        if identity and (identity != [(1, 1)] or set(operations) != {output_type} or output_type == "car"):
            raise ValueError(f"unsupported same-item operation on {(origin, destination)}")
        if not operations:
            raise ValueError(f"missing source operation on {(origin, destination)}")
        products = ((g.id, g.representative.bom) for g in groups) if output_type == "car" else (
            (product, bom[product]) for product, kind in product_types.items() if kind == output_type)
        recipes = {}
        for product, inputs in products:
            if identity:
                # Withdraw the same item that will arrive. The 1:1 coefficient
                # comes from operations, not a self-parent BOM row.
                if any(product_types[child] == output_type for child, _ in inputs):
                    raise ValueError(f"same-item operation has a distinct same-group input for {product}")
                recipes[product] = ((product, 1),)
                continue
            recipe = []
            for child, quantity in inputs:
                output_quantity = operations.get(product_types[child])
                if output_quantity:
                    if quantity % output_quantity:
                        raise ValueError("noninteger recipe for integer inventory")
                    recipe.append((child, quantity // output_quantity))
            if not recipe:
                raise ValueError(f"empty source recipe for {product}")
            recipes[product] = tuple(sorted(recipe))
        caps = {integer(t): integer(cap) for i, j, t, cap in tables["capacity_at_arc"]
                if (i, j) == (origin, destination)}
        if set(caps) != set(periods):
            raise ValueError(f"missing source capacity on {(origin, destination)}")
        arcs.append(Arc(origin, destination, integer(lead), caps, recipes))
    arc_by_key = {arc.key: arc for arc in arcs}
    if (arc_by_key[PRODUCTION_ARC].recipes[PACK] != tuple(zip(CELL, (10, 6, 4)))
            or arc_by_key[TRANSPORT_ARC].recipes[PACK] != ((PACK, 1),)
            or tuple(arc_by_key[key].lead for key in (COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC))
            != (20, 1, 1)):
        raise ValueError("source battery BOM/lead gate")
    initial = {}
    inventory_bounds = {}
    for node, item, quantity, minimum, maximum, t in tables["initial_inventories"]:
        if t != 60 or (node, item) in initial:
            raise ValueError("invalid initial stock index")
        initial[node, item] = integer(quantity)
        inventory_bounds[node, item] = (integer(minimum), integer(maximum))
    network = Network(
        periods, tuple(arcs), groups, initial,
        tuple((i, j, item, integer(t), integer(q)) for i, j, item, t, q in tables["initial_flows"]),
        tables["nodes_inflow"],
        {(i, j, p, integer(t)): integer(q) for i, j, p, t, q in tables["max_flow_product_per_arc"]},
        {(i, j, integer(t)): integer(q) for i, j, group, t, q in tables["max_flow_group_per_arc"]
         if any((i, j, group) == (a[0], a[1], a[3]) for a in tables["arcs"])},
        inventory_bounds,
        source_sha256=SOURCE_SHA256,
    )
    if len(network.group_caps) != len(tables["max_flow_group_per_arc"]):
        raise ValueError("unsupported group cap")
    network = replace(network, initial={key: initial.get(key, 0) for key in network.state_keys()})
    arrival = receipts(network, NOMINAL)
    dispatch_source = tables["initial_flows"]
    if network.historical != dispatch_source or any(
        network.initial[node,item] != qty for node,item,qty,*_ in tables["initial_inventories"]
    ):
        raise ValueError("physical quantities changed during source compilation")
    audit = {
        "source_sha256": SOURCE_SHA256, "sheet_rows": {name: len(rows) for name, rows in tables.items()},
        "vin_count": counts[0], "groups": counts[1], "bev_vin_count": counts[2], "bev_groups": counts[3],
        "demand_raw_total": sum(row[2] for row in tables["demands"]),
        "demand_model_total": sum(len(g.orders) for g in groups),
        "initial_stock_raw_total": sum(row[2] for row in tables["initial_inventories"]),
        "initial_stock_model_total": sum(network.initial.values()),
        "historical_dispatch_total": sum(row[-1] for row in network.historical),
        "historical_dispatch_raw_total": sum(row[-1] for row in dispatch_source),
        "historical_arrivals_in_window_total": sum(arrival.values()),
        "cell_arrivals_in_window": {f"{item}@{t}": q for (node,item,t),q in arrival.items()
                                    if node == PROD and item in CELL},
        "historical_rows": [list(row) for row in network.historical],
        "capacity_basis": "RAW_XLSB",
    }
    return network, audit
