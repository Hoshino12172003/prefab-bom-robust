"""Execute the exact six-run frozen Phase 1 matrix."""
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import gurobipy as gp
from examples.run_v25_phase1 import serial
from prefab_v25.formal import manifest_bytes, frozen_runs, solve_frozen
from prefab_v25.source import load_tables, compile_network
from prefab_v25.data import receipts, PROD, CELL


def save(path, record):
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(serial(record), indent=2, ensure_ascii=False, allow_nan=False),
                       encoding="utf-8")
    pending.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--time-limit", type=float, default=180)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    payload = manifest_bytes(args.manifest)
    manifest = json.loads(payload)
    runs = frozen_runs(payload)
    network, audit = compile_network(load_tables(args.source))
    values = manifest["aggregation"]
    assert (audit["vin_count"],audit["groups"],audit["bev_vin_count"],audit["bev_groups"]) == tuple(
        values[key] for key in ("expected_raw_vins","expected_exact_groups","expected_bev_vins","expected_bev_groups"))
    assert network.periods == tuple(range(manifest["time"]["operational_horizon"][0],
                                          manifest["time"]["operational_horizon"][1]+1))
    arrivals = {
        s.name:{f"{item}@{t}":q for (node,item,t),q in receipts(network,s).items()
                if node == PROD and item in CELL} for s in runs[-1].scenarios
    }
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/"manifest.json").write_bytes(payload)
    record = {
        "status":"RUNNING", "manifest_sha256":sha256(payload).hexdigest(), "source":audit,
        "environment":{"python":platform.python_version(),"gurobi":gp.gurobi.version(),
                       "platform":platform.platform(),"seed":20261110},
        "risk_profiles":[vars(s) for s in runs[-1].scenarios], "battery_component_arrivals":arrivals,
        "matrix":[{"id":r.id,"budget_usd":r.budget,"costs":r.costs,
                   "scenarios":[s.name for s in r.scenarios]} for r in runs],
        "results":{},
    }
    save(args.out/"audit.json",record)
    for run in runs:
        print(f"START {run.id}",flush=True)
        try:
            result = solve_frozen(network,payload,run.id,time_limit=args.time_limit,
                                  threads=args.threads,log=args.out/f"{run.id}.log")
            solutions = result.pop("scenarios",{})
            result["common_t60"] = bool(solutions) and all(
                s["initial"] == next(iter(solutions.values()))["initial"] for s in solutions.values())
            result["scenarios"] = {name:{key:value for key,value in solution.items()
                                         if not isinstance(value,dict)}
                                   for name,solution in solutions.items()}
            if solutions:
                path = args.out/f"{run.id}_solution.json.gz"
                with gzip.open(path,"wt",encoding="utf-8") as stream:
                    json.dump(serial(solutions),stream,ensure_ascii=False,separators=(",",":"),allow_nan=False)
                result["solution_artifact"] = path.name
                result["solution_sha256"] = sha256(path.read_bytes()).hexdigest()
            if run.budget == 0 and result["certified"] and any(result["buffers"].values()):
                raise RuntimeError("zero-budget buffer gate failed")
            if result["certified"] and not result["common_t60"]:
                raise RuntimeError("common t=60 state gate failed")
            if result.get("gap") == float("inf"):
                result["gap"] = None
        except (gp.GurobiError, RuntimeError, ValueError) as exc:
            result = {"status":"ERROR","certified":False,"error":str(exc)}
        record["results"][run.id] = result
        save(args.out/"audit.json",record)
        print(run.id,result["status"],result.get("objective"),result.get("bound"),flush=True)
    record["status"] = ("FORMAL_MATRIX_CERTIFIED" if all(r["certified"] for r in record["results"].values())
                        else "FORMAL_MATRIX_NOT_CERTIFIED")
    save(args.out/"audit.json",record)
    return 0 if record["status"] == "FORMAL_MATRIX_CERTIFIED" else 2


if __name__ == "__main__":
    sys.exit(main())
