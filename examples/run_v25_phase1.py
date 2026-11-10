"""Audit the original workbook and run the explicitly synthetic Phase 1 checks."""
import argparse
import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import gurobipy as gp
from prefab_v25.data import NOMINAL
from prefab_v25.examples import TOY_COSTS, micro, micro_risks
from prefab_v25.model import nominal, extensive
from prefab_v25.source import load_tables, compile_network


def serial(value):
    if isinstance(value, dict):
        return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):
        return [serial(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="original XLSB or its archive")
    parser.add_argument("--out", type=Path, required=True, help="new directory for audit evidence")
    args = parser.parse_args()
    network, audit = compile_network(load_tables(args.source))
    args.out.mkdir(parents=True,exist_ok=False)
    data = micro()
    cases = {}
    for budget, expected in ((0,0.25),(2,0.5),(7,0.75),(10,1.0)):
        label = f"micro_nominal_B{budget}"
        result = nominal(data,budget,TOY_COSTS,log=args.out/f"{label}.log")
        if not result["certified"] or abs(result["objective"]-expected)>1e-7:
            raise RuntimeError(f"{label} did not certify")
        cases[label] = result
    risks = (NOMINAL,*micro_risks())
    cases["micro_DE_B7"] = extensive(data,risks,7,TOY_COSTS,log=args.out/"micro_DE_B7.log")
    if not cases["micro_DE_B7"]["certified"] or abs(cases["micro_DE_B7"]["objective"]-0.25)>1e-7:
        raise RuntimeError("micro DE did not certify")
    evidence = {
        "status": "SOURCE_AUDITED_AND_MICRO_VALIDATED",
        "paper_scale": {"status":"BLOCKED_MISSING_FROZEN_MANIFEST",
                        "required":"paper_scale_v2/manifest.json",
                        "optimizer_calls":0},
        "environment": {"python":platform.python_version(),"gurobi":gp.gurobi.version(),
                        "platform":platform.platform(),"threads":1,"seed":20261110},
        "source_path": str(args.source.resolve()), "source": audit,
        "source_network_state_keys": len(network.initial),
        "synthetic_inputs": {"budgets":[0,2,7,10],"buffer_costs":TOY_COSTS,
                             "DE_scenarios":[vars(s) for s in risks]},
        "synthetic_solves": cases,
    }
    (args.out/"audit.json").write_text(json.dumps(serial(evidence),ensure_ascii=False,indent=2,
                                                 allow_nan=False),encoding="utf-8")
    print(args.out/"audit.json")
    for label,result in cases.items():
        print(label,result["status"],result["objective"],result["bound"],result["quality_residual"])


if __name__ == "__main__":
    main()
