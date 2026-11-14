"""Load and hash frozen V3 evidence. This module writes only audit outputs."""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
D4 = ROOT / "artifacts/v3_phase32d4_20261112_191057"
D3 = ROOT / "artifacts/v3_phase32d3_20261112_171131"
D2R = ROOT / "artifacts/v3_phase32d2r_20261112_134524"
sys.path[:0] = [str(ROOT / "src"), str(D4)]
from run import SOURCE, Coordinates, certified_event, read
from prefab_v25.source import SOURCE_SHA256, load_tables
from prefab_v3.base import source_base
from prefab_v25.data import NOMINAL, receipts


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(name, rows):
    rows = iter(rows)
    first = next(rows)
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=first)
        writer.writeheader()
        writer.writerow(first)
        writer.writerows(rows)


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, encoding="utf-8").strip("\r\n")


def verify_inputs():
    manifests = {}
    for path in (D4, D3, D2R):
        manifest = path / "sha256_manifest.csv"
        with manifest.open(encoding="utf-8-sig", newline="") as stream:
            entries = list(csv.DictReader(stream))
        for row in entries:
            if digest(ROOT / row["path"]) != row["sha256"]:
                raise ValueError(f"Frozen file mismatch: {row['path']}")
        manifests[path.name] = dict(entries=len(entries), sha256=digest(manifest))
    source_hash = digest(SOURCE.SOURCE)
    assert source_hash == read(D4 / "preflight.json")["source_zip_sha256"]
    config = [D4 / n for n in ("run.py","preflight.json","gamma_worst_event_comparison.csv",
                               "outer/G1/final_oracle/result.json")]
    config += [D2R / "multibom_effective_rhs_catalog/rhs_coordinates.json", D3 / "prepare.py",
               ROOT / "src/prefab_v3/event_budget.py", ROOT / "src/prefab_v3/base.py",
               ROOT / "src/prefab_v25/source.py", ROOT / "src/prefab_v25/data.py"]
    return dict(branch=git("branch","--show-current"), head=git("rev-parse","HEAD"),
                workspace_status=git("status","--porcelain=v1","--untracked-files=normal").splitlines(),
                xlsb_sha256=SOURCE_SHA256, source_zip_sha256=source_hash,
                frozen_manifests=manifests, config_sha256={p.relative_to(ROOT).as_posix():digest(p) for p in config})


def load():
    tables = load_tables(SOURCE.SOURCE)
    SOURCE.BASE, source_audit = source_base(tables)
    SOURCE.OPENING = receipts(SOURCE.BASE.network, NOMINAL)
    assert source_audit["source_sha256"] == SOURCE_SHA256
    return tables, SOURCE.BASE


def terminal():
    result = read(D4 / "outer/G1/result.json")
    code, profile, exposure = certified_event(Coordinates(), result["final_oracle"])
    assert (code, exposure, result["objective"]) == ("16106127360", 11, 11775)
    return tuple(result["policy"]), profile, code
