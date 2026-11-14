"""Isolated profiling and development-only ablations of the frozen plain method."""
import csv
import json
import os
import random
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import gurobipy as gp
import psutil
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHASE_A = ROOT / "artifacts/v3_phase32a_20261111_212045"
sys.path[:0] = [str(PHASE_A), str(ROOT / "src")]
import run_benchmark as prior
from design import de_scenarios, overlap_scenarios, scenarios
from prefab_v3 import plain_ccg as ccg

FROZEN = prior.frozen
LABEL = "STRESS_TEST_ONLY"
EXPANSION_FIRST = ("NR", "B_RECEIPT_1", "E_11", "S_7", "B_PROD_E_S", "BGS_OVERLAP", "S_4", "G_4")
RANDOM_SEED = 20261111


def write_csv(name, rows):
    with (HERE/name).open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def verify_frozen():
    records = prior.verify_inputs()
    manifest = PHASE_A / "sha256_manifest.csv"
    rows = FROZEN.read(manifest)
    assert all(FROZEN.digest(ROOT/r["path"]) == r["sha256"] for r in rows)
    records[PHASE_A.name] = dict(entries=len(rows), manifest_sha256=FROZEN.digest(manifest))
    return records


def rhs_changes(base, opening, profile):
    arrivals, factors = profile
    caps = {a.key: a.capacity for a in base.network.arcs}
    return {
        **{("receipt", *k): v for k, v in arrivals.items() if v != opening.get(k, 0)},
        **{("capacity", *k): int(caps[k[:2]][k[2]]*v) for k, v in factors.items()
           if int(caps[k[:2]][k[2]]*v) != caps[k[:2]][k[2]]},
    }


def catalog(base, opening):
    ordered = [*de_scenarios(), *scenarios(), *overlap_scenarios()]
    by_name = {s.name: s for s in ordered}
    ordered = [*ordered[:16], *(by_name[n] for n in EXPANSION_FIRST),
               *(s for s in ordered[16:] if s.name not in EXPANSION_FIRST)]
    profiles = {s.name: FROZEN.data_for(s, opening, base) for s in ordered}
    diffs = {n: rhs_changes(base, opening, p) for n, p in profiles.items()}
    first = {}
    rep = {n: first.setdefault(tuple(sorted(d.items())), n) for n, d in diffs.items()}
    unique = tuple(n for n in profiles if rep[n] == n)
    assert len(unique) >= 32 and len(unique) == 38
    return by_name, profiles, diffs, rep, unique


def start_blocks(method, names, source, diffs, solve_q):
    if method in ("PLAIN", "INIT_A", "BATCH2", "BATCH4"):
        return (prior.BASELINE,)
    if method == "TWO":
        return prior.BASELINE, prior.SEVERE
    if method == "INIT_B":
        severe = max((n for n in names if len(source[n].events) >= 2),
                     key=lambda n: (sum(e.duration*e.severity for e in source[n].events), n))
        return "NR", severe
    if method == "INIT_C":
        # Jaccard distance on actual resource-period supports, then distinct branch tags and dates.
        from itertools import combinations
        choices = [n for n in names if diffs[n]]
        def distance(pair):
            a, b = pair
            A, B = set(diffs[a]), set(diffs[b])
            resources = len({e.resource for n in pair for e in source[n].events})
            calendar = abs(min(e.start for e in source[a].events) - min(e.start for e in source[b].events))
            return Fraction(len(A ^ B), len(A | B)), resources, calendar, tuple(sorted(pair))
        return max(combinations(choices, 2), key=distance)
    if method == "INIT_D":
        return tuple(random.Random(RANDOM_SEED).sample(names, 2))
    if method == "INIT_E":
        pilot = ("E_11", "S_7", "BGS_OVERLAP")
        severe = min((solve_q(n, (0, 0, 0), "pilot"), n) for n in pilot)[1]
        return "NR", severe
    raise ValueError(method)


def batch_diagnostic(names, initial, master, recourse, width):
    """Temporary top-k ablation. Use full exact oracle in every round."""
    active, rows, best, upper, policy = initial, [], -1, float("inf"), None
    for i in range(1, len(names)+1):
        mp = master(active, i)
        q = {n: recourse(n, mp.policy, f"oracle_{i:02d}") for n in names}
        worst = min(q.values())
        assert mp.objective <= upper and all(q[n] >= mp.objective for n in active)
        upper = mp.objective
        if worst > best:
            best, policy = worst, mp.policy
        assert best <= upper
        ordered = sorted((value, name) for name, value in q.items() if value < upper)
        added = tuple(n for _, n in ordered[:width]) if upper > best else ()
        assert all(n not in active for n in added)
        rows.append(dict(iteration=i, master_scenarios=active, added_scenario=added, policy=mp.policy,
                         upper=upper, lower=best, worst_ties=sorted(n for n in names if q[n] == worst)))
        if upper == best:
            verify = {n: recourse(n, policy, "verify") for n in names}
            assert min(verify.values()) == best
            return best, policy, active, verify, rows
        assert added
        active += added
    raise RuntimeError("batch diagnostic exhausted catalog without closure")


def solve(n, method):
    FROZEN.init()
    base, opening = FROZEN.BASE, FROZEN.OPENING
    source, profiles, diffs, rep, unique = catalog(base, opening)
    names = unique[:n]
    logs = HERE/"logs"
    logs.mkdir(exist_ok=True)
    start = perf_counter()
    available = psutil.virtual_memory().available
    records, iteration_rows = [], []
    final, policy, verify, objective, initial = (), None, {}, None, ()
    status = "EXACT_FINITE"

    with FROZEN.env() as env:
        def profiled(kind, tag, name, construct):
            job_start = perf_counter()
            path = logs/f"n{n:02d}_{method}_{tag}_{name}.log"
            path.write_text("", encoding="utf-8")
            with gp.Model(name, env=env) as model:
                FROZEN.configure(model, seconds=90 if n <= 16 else 240)
                if n <= 16:
                    model.Params.SoftMemLimit = 3
                model.Params.LogFile = os.path.relpath(path, ROOT)
                before = perf_counter()
                x, eta, blocks, fixed = construct(model)
                model.update()
                after_build = perf_counter()
                assert model.NumVars == model.NumIntVars and model.NumBinVars == 0
                model.optimize()
                after_solve = perf_counter()
                status_code = model.Status
                if status_code == GRB.OPTIMAL:
                    vector, residual = FROZEN.exact_vector(model, FROZEN.matrix_rows(model))
                    q = int(model.ObjVal)
                    assert q == model.ObjVal == model.ObjBound and model.MIPGap == 0
                    assert q == min(prior.selected_quantity(b, base, vector) for b in blocks.values())
                    if eta is not None:
                        assert q == int(vector[eta.index])
                    chosen = fixed if x is None else tuple(int(vector[v.index]) for v in x)
                    prior.budget_use(chosen)
                else:
                    q, chosen, residual = None, fixed, None
                record = dict(kind=kind, tag=tag, name=name, value=q, policy=chosen, status=status_code,
                    build_seconds=after_build-before, solve_wall_seconds=after_solve-after_build,
                    gurobi_seconds=model.Runtime, post_solve_seconds=perf_counter()-after_solve,
                    serialization_seconds=0, rows=model.NumConstrs, integers=model.NumIntVars,
                    nonzeros=model.NumNZs, gurobi_peak_gb=model.MaxMemUsed, peak_process_bytes=prior.peak_bytes(),
                    nodes=int(model.NodeCount), residual=residual, log=path.relative_to(HERE).as_posix())
            record["job_wall_seconds"] = perf_counter()-job_start
            records.append(record)
            if status_code != GRB.OPTIMAL:
                raise RuntimeError(f"Gurobi status {status_code} in {path.name}")
            return q, chosen

        def master(active, i):
            def construct(model):
                x, eta, blocks = ccg.build_master(model, base, profiles, active, prior.COSTS, prior.BUDGET)
                return x, eta, blocks, None
            q, x = profiled("MASTER", f"round_{i:02d}", "MP", construct)
            return ccg.MasterSolution(q, x, {})

        def recourse(name, policy, tag):
            def construct(model):
                b = ccg.add_recourse_block(model, base, name, profiles[name], policy)
                model.setObjective(ccg.on_time(b, base), GRB.MAXIMIZE)
                return None, None, {name: b}, policy
            kind = {"pilot": "PILOT", "verify": "VERIFY"}.get(tag, "ORACLE")
            return profiled(kind, tag, name, construct)[0]

        try:
            if method == "DIRECT":
                def construct(model):
                    x = FROZEN.add_stage_one(model, prior.COSTS, prior.BUDGET)
                    eta = model.addVar(ub=base.network.demand_weight, vtype=GRB.INTEGER, name="worst")
                    blocks = {}
                    for name in names:
                        arrivals, factors = profiles[name]
                        b = FROZEN.add_block(model, base, name, FROZEN.Weights(0, 0, 0, 0, 0), reschedule=True,
                            fixed_receipts=arrivals, arc_factors=factors, protection=FROZEN.protection_inventory(x))
                        blocks[name] = b
                        model.addConstr(eta <= prior.direct_score(b, base))
                    model.setObjective(eta, GRB.MAXIMIZE)
                    return x, eta, blocks, None
                objective, policy = profiled("DIRECT", "solve", "DE", construct)
                final = names
                verify = {name: recourse(name, policy, "verify") for name in names}
                assert min(verify.values()) == objective
            else:
                initial = start_blocks(method, names, source, diffs, recourse)
                if method.startswith("BATCH"):
                    objective, policy, final, verify, iteration_rows = batch_diagnostic(
                        names, initial, master, recourse, int(method[-1]))
                else:
                    result = ccg.generate(names, initial, master, recourse)
                    objective, policy, final = result.objective, result.policy, result.selected
                    verify, iteration_rows = result.verified_services, result.iterations
        except RuntimeError as error:
            if not records or records[-1]["status"] == GRB.OPTIMAL:
                raise
            status = str(error)
    payload = dict(label=LABEL, n=n, method=method, names=names, initial=initial, final=final, status=status,
                   Q=objective, policy=policy, verify=verify, iterations=iteration_rows, records=records,
                   available_bytes_at_start=available, peak_process_bytes=prior.peak_bytes(),
                   wall_seconds=perf_counter()-start, time_limit_s=90 if n<=16 else 240,
                   soft_mem_gb=3 if n<=16 else None)
    (HERE/f"n{n:02d}_{method}.json").write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(n, method, status, objective, "blocks", len(final), "seconds", round(payload["wall_seconds"], 2), flush=True)


def main():
    if len(sys.argv) == 3:
        solve(int(sys.argv[1]), sys.argv[2])
        return
    verify_frozen()
    jobs = [
        (4, "PLAIN"), (8, "PLAIN"), (16, "PLAIN"), (16, "TWO"), (16, "BATCH2"), (16, "BATCH4"),
        (24, "DIRECT"), (24, "INIT_A"), (24, "INIT_B"), (24, "INIT_C"), (24, "INIT_D"), (24, "INIT_E"),
        (32, "DIRECT"), (32, "PLAIN"), (38, "DIRECT"), (38, "PLAIN"),
    ]
    for n, m in jobs:
        subprocess.run([sys.executable, "-B", __file__, str(n), m], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
