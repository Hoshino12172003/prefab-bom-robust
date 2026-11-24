"""Verified XLSB and exact, solver-free reuse of pinned historical pure functions."""
import ast
import csv
import hashlib
import json
import sys
import types
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from pyxlsb import open_workbook

from .manifest import SOURCE_HASHES, XLSB_SHA256, ZIP_SHA256, MODEL_INSTANCE_ID, check_hash

SHEET_COUNTS = dict(products=28049, nodes=12, nodes_inflow=44, arcs=11,
    capacity_at_arc=154, max_flow_product_per_arc=365, max_flow_group_per_arc=20,
    operations=15, BOM=87059, demands=28000, initial_inventories=82, initial_flows=117)


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def historical_compiler(root):
    """Only the hash-pinned data classes and pure compilation functions execute."""
    module = types.ModuleType("_scenario_agent_pinned_v3")
    sys.modules[module.__name__] = module
    selections = (
        ("src/prefab_v25/data.py", None),
        ("src/prefab_v25/source.py", {"integer", "compile_network"}),
        ("src/prefab_v3/base.py", {"Base", "operation_recipes", "source_base"}),
    )
    for rel, names in selections:
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        body = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                if (not isinstance(node, ast.ImportFrom) or not node.level) and mod in (
                        "collections", "dataclasses", "fractions", "hashlib", "io", "pathlib", "zipfile"):
                    body.append(node)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and (names is None or node.name in names):
                body.append(node)
            elif isinstance(node, ast.Assign) and (names is None or any(
                    isinstance(t, ast.Name) and t.id in ("HEADERS", "SOURCE_SHA256", "ASSEMBLY") for t in node.targets)):
                body.append(node)
        exec(compile(ast.Module(body=body, type_ignores=[]), rel, "exec"), module.__dict__)
    return module


def check_dag(relations):
    children = {}
    for parent, child, _ in relations:
        if parent != child:
            children.setdefault(parent, []).append(child)
    done, visiting = set(), set()

    def visit(item):
        if item in visiting:
            raise ValueError("Manufacturing BOM cycle")
        if item not in done:
            visiting.add(item)
            for child in children.get(item, ()):
                visit(child)
            visiting.remove(item)
            done.add(item)
    for item in children:
        visit(item)


@dataclass
class NetworkV3:
    root: Path
    tables: dict
    base: object
    opening: dict
    columns: dict
    model_instance_id: str = MODEL_INSTANCE_ID
    model_version: str = "V3_HISTORICAL_SERVICE"


def load_v3(root, source_zip):
    root, source_zip = Path(root), Path(source_zip)
    for rel, expected in SOURCE_HASHES.items():
        check_hash(root / rel, expected)
    check_hash(source_zip, ZIP_SHA256)
    with ZipFile(source_zip) as archive:
        names = [n for n in archive.namelist() if n.rsplit("/", 1)[-1] == "2020_dataset_OfAutomotiveProductionNetwork.xlsb"]
        if len(names) != 1:
            raise ValueError("Expected exactly one audited XLSB")
        payload = archive.read(names[0])
    if hashlib.sha256(payload).hexdigest() != XLSB_SHA256:
        raise ValueError("XLSB SHA-256 conflict")
    compiler = historical_compiler(root)
    tables = {}
    with open_workbook(BytesIO(payload)) as book:
        if set(book.sheets) != set(SHEET_COUNTS):
            raise ValueError("Workbook sheet identity conflict")
        for name in book.sheets:
            with book.get_sheet(name) as sheet:
                rows = [tuple(c.v for c in row) for row in sheet.rows(sparse=True)]
                if rows[0] != tuple(compiler.HEADERS[name].split()):
                    raise ValueError(f"Header conflict: {name}")
                tables[name] = tuple(rows[1:])
                if len(tables[name]) != SHEET_COUNTS[name] or len(set(tables[name])) != len(tables[name]):
                    raise ValueError(f"Sheet row/duplicate conflict: {name}")
                if any(v is None for row in tables[name] for v in row):
                    raise ValueError(f"Missing raw workbook value: {name}")
    check_dag(tables["BOM"])
    base, _ = compiler.source_base(tables)
    net = base.network
    counts = (len(tables["nodes"]), len(net.arcs), sum(len(a.recipes) for a in net.arcs),
              sum(len(q) for a in net.arcs for q in a.recipes.values()), len(net.state_keys()))
    if counts != (12, 11, 1377, 3979, 1421) or net.periods != tuple(range(61, 75)):
        raise ValueError(f"V3 structure conflict: {counts}")
    return NetworkV3(root, tables, base, compiler.receipts(net, compiler.NOMINAL),
                     {n: compiler.HEADERS[n].split() for n in tables})


def load_standardized_v3(root, directory):
    """Reload the verified static layer without needing the external ZIP at inference time."""
    root, directory = Path(root), Path(directory)
    manifest = json.loads((directory / "feature_manifest_v3.json").read_text(encoding="utf-8"))
    if manifest["model_instance_id"] != MODEL_INSTANCE_ID or manifest["source_xlsb_sha256"] != XLSB_SHA256:
        raise ValueError("Standardized V3 model identity conflict")
    for rel, expected in SOURCE_HASHES.items():
        check_hash(root / rel, expected)
    for name, expected in manifest["outputs"].items():
        check_hash(directory / name, expected)
    raw = json.loads((directory / "source_workbook_v3.json").read_text(encoding="utf-8"))
    if raw["model_instance_id"] != MODEL_INSTANCE_ID or raw["xlsb_sha256"] != XLSB_SHA256:
        raise ValueError("Standardized workbook identity conflict")
    tables = {k: tuple(tuple(row) for row in rows) for k, rows in raw["tables"].items()}
    if {k: len(rows) for k, rows in tables.items()} != SHEET_COUNTS:
        raise ValueError("Standardized workbook row conflict")
    compiler = historical_compiler(root)
    if raw["columns"] != {n: compiler.HEADERS[n].split() for n in tables}:
        raise ValueError("Standardized workbook column conflict")
    check_dag(tables["BOM"])
    base, _ = compiler.source_base(tables)
    return NetworkV3(root, tables, base, compiler.receipts(base.network, compiler.NOMINAL), raw["columns"])
