"""Run each Phase 3.2A method in a fresh process on the frozen benchmark."""
import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import gurobipy as gp
import psutil
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / "artifacts/v3_phase31r_20261111_202237"
sys.path[:0] = [str(ROOT / "src"), str(FROZEN)]
import run_matrix as frozen
from design import COSTS, LABEL, de_scenarios
from prefab_v3 import plain_ccg as ccg


COUNTS = (4, 8, 16)
METHODS = ("DIRECT_DE", "CCG_MINIMAL", "CCG_INFORMED")
BASELINE = "DE_ENGINE_68"
SEVERE = "DE_GEAR_61"
BUDGET = 644 * COSTS[1]
BLOCK_INTEGERS = 75810
BLOCK_ROWS_WITH_GUARANTEE = 23020
BLOCK_NONZEROS_WITH_GUARANTEE = 218092


def verify_inputs():
    prior = frozen.verify_frozen()
    manifest = FROZEN / "sha256_manifest.csv"
    rows = frozen.read(manifest)
    assert all(frozen.digest(ROOT / r["path"]) == r["sha256"] for r in rows)
    prior[FROZEN.name] = dict(entries=len(rows), manifest_sha256=frozen.digest(manifest))
    assert gp.gurobi.version() == (13, 0, 1)
    return prior


def peak_bytes():
    return psutil.Process().memory_info().peak_wset


def log_path(n, method, tag):
    return HERE / "logs" / f"n{n:02d}_{method}_{tag}.log"


def setup(model, path):
    frozen.configure(model, seconds=90)
    model.Params.SoftMemLimit = 3
    path.write_text("", encoding="utf-8")
    model.Params.LogFile = os.path.relpath(path, ROOT)


def optimize(model, log):
    model.update()
    if model.NumIntVars != model.NumVars or model.NumBinVars:
        raise RuntimeError("HOLD_INTEGER_RECOURSE_IMPLEMENTATION: expected all-general-integer model")
    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(f"{log.name}: Gurobi status {model.Status}; exact solve required")
    if model.ObjVal != model.ObjBound or model.MIPGap != 0:
        raise RuntimeError(f"{log.name}: global integer bound failed to close")
    vector, residual = frozen.exact_vector(model, frozen.matrix_rows(model))
    objective = int(model.ObjVal)
    assert objective == model.ObjVal
    metrics = dict(status="OPTIMAL", solver_objective=objective, solver_bound=objective, solver_gap=0,
                   integers=model.NumIntVars, constraints=model.NumConstrs, nonzeros=model.NumNZs,
                   solver_seconds=model.Runtime, nodes=int(model.NodeCount), solver_residual=residual,
                   exact_matrix_residual=0, peak_process_bytes=peak_bytes(), gurobi_peak_gb=model.MaxMemUsed,
                   log=log.relative_to(HERE).as_posix())
    return objective, vector, metrics


def direct_score(block, base):
    # Construct DE's objective links separately from the master/oracle score helper.
    order_due = {g.id: g.representative.due for g in base.network.groups}
    return gp.quicksum(v for (group, t), v in block.outflow.items() if t <= order_due[group])


def selected_quantity(block, base, vector):
    order_due = {g.id: g.representative.due for g in base.network.groups}
    return sum(int(vector[v.index]) for (group, t), v in block.outflow.items() if t <= order_due[group])


def budget_use(x):
    value = sum(c*v for c, v in zip(COSTS, x, strict=True))
    assert min(x) >= 0 and value <= BUDGET
    return str(value)


def solve(n, method):
    verify_inputs()
    frozen.init()
    base, opening = frozen.BASE, frozen.OPENING
    selected = de_scenarios()[:n]
    profiles = {s.name: frozen.data_for(s, opening, base) for s in selected}
    names = tuple(profiles)
    supports = {frozenset(factors) for _, factors in profiles.values()}
    assert len(supports) == len(names) == n
    assert all(arrivals == opening for arrivals, _ in profiles.values())
    assert all(len(keys) == 2 for keys in supports)
    frozen_rows = {int(r["scenario_count"]): r for r in frozen.read(FROZEN/"direct_de_multi_bom_scaling.csv")}
    assert names == tuple(frozen_rows[n]["scenarios"].split("|"))
    (HERE / "logs").mkdir(exist_ok=True)
    oracle_rows = []
    start = perf_counter()
    with frozen.env() as env:
        def recourse(name, x, tag):
            log = log_path(n, method, f"{tag}_{name}")
            before = perf_counter()
            with gp.Model(name, env=env) as model:
                setup(model, log)
                b = ccg.add_recourse_block(model, base, name, profiles[name], x)
                model.setObjective(ccg.on_time(b, base), GRB.MAXIMIZE)
                objective, vector, metrics = optimize(model, log)
                assert objective == selected_quantity(b, base, vector)
                assert metrics["integers"] == BLOCK_INTEGERS
                assert metrics["constraints"] == BLOCK_ROWS_WITH_GUARANTEE - 1
                oracle_rows.append(dict(evaluation=tag, scenario=name, policy=x, service=objective,
                                        elapsed_seconds=perf_counter()-before, **metrics))
                return objective

        def master(active, k):
            log = log_path(n, method, f"master_{k:02d}")
            with gp.Model(f"master_{k}", env=env) as model:
                setup(model, log)
                x, eta, blocks = ccg.build_master(model, base, profiles, active, COSTS, BUDGET)
                value, vector, metrics = optimize(model, log)
                assert value == vector[eta.index]
                assert value == min(selected_quantity(b, base, vector) for b in blocks.values())
                check_size(metrics, len(active))
                policy = tuple(int(vector[v.index]) for v in x)
                budget_use(policy)
                return ccg.MasterSolution(value, policy, metrics)

        if method == "DIRECT_DE":
            with gp.Model(f"direct_{n}", env=env) as model:
                setup(model, log_path(n, method, "model"))
                x = frozen.add_stage_one(model, COSTS, BUDGET)
                eta = model.addVar(ub=base.network.demand_weight, vtype=GRB.INTEGER, name="worst")
                blocks = {}
                for name, (arrivals, factors) in profiles.items():
                    b = frozen.add_block(model, base, name, frozen.Weights(0, 0, 0, 0, 0),
                                         reschedule=True, fixed_receipts=arrivals, arc_factors=factors,
                                         protection=frozen.protection_inventory(x))
                    blocks[name] = b
                    model.addConstr(eta <= direct_score(b, base))
                model.setObjective(eta, GRB.MAXIMIZE)
                objective, vector, largest = optimize(model, log_path(n, method, "model"))
                assert objective == vector[eta.index]
                assert objective == min(selected_quantity(b, base, vector) for b in blocks.values())
                check_size(largest, n)
                assert objective == int(frozen_rows[n]["Q"])
                policy = tuple(int(vector[v.index]) for v in x)
                del vector, blocks
            final, iterations, initial = names, (), ()
            model_seconds = perf_counter() - start
            before = perf_counter()
            verified = {name: recourse(name, policy, "verify") for name in names}
            verify_seconds = perf_counter() - before
            if min(verified.values()) != objective:
                raise ccg.BoundError("Direct DE policy differs from its fresh full-set evaluation")
        else:
            initial = (BASELINE,) if method == "CCG_MINIMAL" else (BASELINE, SEVERE)
            result = ccg.generate(names, initial, master, recourse)
            objective, policy, final = result.objective, result.policy, result.selected
            verified, iterations = result.verified_services, result.iterations
            largest = iterations[-1]
            verify_seconds = result.verification_seconds
            model_seconds = perf_counter() - start - verify_seconds
    output = dict(label=LABEL, method=method, n=n, benchmark=names, initial=initial, final=final,
                  objective=objective, policy=policy, cost=budget_use(policy), verified=verified,
                  worst=sorted(name for name, q in verified.items() if q == objective),
                  iterations=iterations, oracle=oracle_rows, largest=largest,
                  model_seconds=model_seconds, verification_seconds=verify_seconds,
                  total_seconds=perf_counter()-start, peak_process_bytes=peak_bytes(),
                  certification="EXACT_FINITE")
    (HERE / f"n{n:02d}_{method}.json").write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    print(n, method, "objective", objective, "policy", policy, "blocks", len(final),
          "seconds", round(output["total_seconds"], 2), flush=True)


def check_size(metrics, n):
    if (metrics["integers"], metrics["constraints"], metrics["nonzeros"]) != (
            BLOCK_INTEGERS*n+4, BLOCK_ROWS_WITH_GUARANTEE*n+1, BLOCK_NONZEROS_WITH_GUARANTEE*n+3):
        raise RuntimeError("HOLD_INTEGER_RECOURSE_IMPLEMENTATION: unexpected full-block dimensions")


def main():
    if len(sys.argv) == 3:
        n, method = int(sys.argv[1]), sys.argv[2]
        assert n in COUNTS and method in METHODS
        solve(n, method)
    else:
        verify_inputs()
        for n in COUNTS:
            for method in METHODS:
                subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), str(n), method],
                               cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
