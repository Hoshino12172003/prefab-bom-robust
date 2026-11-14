"""Full outer C&CG on the three frozen event-budget domains."""

import argparse
import json
import os
import sys
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from prefab_v3 import implicit_ccg, plain_ccg


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D3 = ROOT / "artifacts/v3_phase32d3_20261112_171131"
A = ROOT / "artifacts/v3_phase32a_20261111_212045"
sys.path.insert(1, str(D3))
from prepare import SOURCE, TOTALS, Coordinates, frozen_catalog, read
from reference import peak_bytes
from implicit import run_case
from recourse import Recourse
import recourse as d3_recourse

# Redirect only the relative path used to record solver logs.
d3_recourse.HERE = HERE
COSTS = tuple(SOURCE.COSTS)
BUDGET = 644*COSTS[1]


def verify_frozen():
    d3 = read(D3 / "audit.json")
    assert d3["status"] == "PASS_IMPLICIT_EVENT_SEPARATION_EXACT_PROTOTYPE"
    assert all(r["full_certificate"] for r in d3["certificate"]["full_independent_certificate"].values())
    verified = {path.name: frozen_catalog.verify_manifest(path) for path in (D3, A)}
    assert (COSTS, BUDGET) == ((Fraction(1), Fraction(27, 19), Fraction(297, 190)), Fraction(17388, 19))
    assert frozen_catalog.digest(SOURCE.SOURCE) == d3["source_zip_sha256"]
    frozen_catalog.dump(HERE / "preflight.json", dict(frozen_manifests=verified, costs=list(map(str, COSTS)),
                        budget=str(BUDGET), source_zip_sha256=d3["source_zip_sha256"], gurobi=gp.gurobi.version()))


def spend(policy):
    value = sum(c*x for c, x in zip(COSTS, policy, strict=True))
    assert all(type(x) is int and x >= 0 for x in policy) and value <= BUDGET
    return value


def case(gamma, subset=None):
    if subset is not None:
        return read(D3 / "benchmark_design.json")[subset]
    raw, rhs = TOTALS[gamma]
    return dict(gamma=gamma, raw_count=raw, rhs_count=rhs, threshold=None)


def certified_event(coords, result):
    records = result["worst_event_details"]
    from prefab_v3.event_budget import Event
    from prefab_v3.robust import Episode
    events = tuple(Event(r["resource"], Episode(r["start"], r["duration"], Fraction(r["severity"])), r["recovery"])
                   for r in records)
    exposure = frozen_catalog.BUDGET.validate(events, result["gamma"])
    assert [r["event_id"] for r in records] == result["worst_events"]
    code = sum(coords.by_id[i].code for i in result["worst_events"])
    actual = frozen_catalog.profile("outer_worst", events)
    assert coords.profiles(coords.code_profile(code), SOURCE.OPENING) == actual
    return str(code), actual, exposure


def fixed_oracle(env, coords, x, definition, out, full=True):
    spend(x)
    with_solver = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, out / "logs")
    try:
        run_case(with_solver, "outer", out.name, definition, 2, out, full)
    finally:
        with_solver.close()
    return read(out / "result.json")


def optimize_model(model, log, seconds=180):
    log.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.configure(model, seconds=seconds)
    log.write_text("", encoding="utf-8")
    model.Params.LogFile = os.path.relpath(log, ROOT)
    model.update()
    assert model.NumVars == model.NumIntVars and not model.NumBinVars
    model.optimize()
    if model.Status != GRB.OPTIMAL or model.MIPGap != 0 or model.ObjVal != model.ObjBound:
        raise RuntimeError(f"uncertified MIP {model.Status}: {log}")
    vector, residual = SOURCE.exact_vector(model, SOURCE.matrix_rows(model))
    objective = int(model.ObjVal)
    assert objective == model.ObjVal
    return objective, vector, dict(solver_status="OPTIMAL", solver_gap=0, objective_bound=objective,
        integer_vars=model.NumVars, constraints=model.NumConstrs, nonzeros=model.NumNZs,
        solver_seconds=model.Runtime, solver_residual=residual, matrix_residual=0,
        peak_bytes=peak_bytes(), log=log.relative_to(HERE).as_posix())


def master(env, profiles, active, log):
    with gp.Model(env=env) as model:
        x, eta, blocks = plain_ccg.build_master(model, SOURCE.BASE, profiles, active, COSTS, BUDGET)
        q, vector, metrics = optimize_model(model, log)
        assert q == vector[eta.index]
        assert model.NumVars == 75810*len(active)+4 and model.NumConstrs == 23020*len(active)+1
        quantities = {n: sum(int(vector[b.outflow[g.id, t].index]) for g in SOURCE.BASE.network.groups
                      for t in SOURCE.BASE.network.periods if t <= g.representative.due) for n, b in blocks.items()}
        assert q == min(quantities.values())
        policy = tuple(int(vector[v.index]) for v in x)
        spend(policy)
    return plain_ccg.MasterSolution(q, policy, dict(mp=metrics, master_service=quantities))


def run(gamma, subset=None):
    assert (HERE / "preflight.json").is_file()
    SOURCE.init()
    coords, definition = Coordinates(), case(gamma, subset)
    out = HERE / "outer" / (subset or f"G{gamma}")
    out.mkdir(parents=True, exist_ok=True)
    profiles = {"0": coords.profiles(coords.nominal, SOURCE.OPENING)}
    with SOURCE.env() as env:
        def separation(x, k):
            answer = fixed_oracle(env, coords, x, definition, out / f"oracle_{k:02d}", subset is None)
            if not answer["exact"] or answer["frontier_size"]:
                raise implicit_ccg.OracleError("unclosed frozen D-3 oracle")
            assert answer["lower_bound"] == answer["worst"]
            code, actual, exposure = certified_event(coords, answer)
            profiles.setdefault(code, actual)
            return implicit_ccg.WorstScenario(answer["worst"], code, True, 0,
                dict(oracle=answer, exposure=exposure))

        started = perf_counter()
        result = implicit_ccg.generate(("0",), definition["rhs_count"],
            lambda active, k: master(env, profiles, active, out / f"master_{k:02d}.log"), separation)
        final = fixed_oracle(env, coords, tuple(result["policy"]), definition, out / "final_oracle", subset is None)
        if not final["exact"] or final["frontier_size"] or final["worst"] != result["objective"]:
            raise implicit_ccg.OracleError("fresh final oracle failed to certify the incumbent")
        code, _, exposure = certified_event(coords, final)
        result.update(gamma=gamma, subset=subset, budget=str(BUDGET), final_oracle=final,
            final_worst_rhs=int(code), final_exposure=exposure, total_seconds=perf_counter()-started)
    frozen_catalog.dump(out / "result.json", result)
    print(out.name, "Z", result["objective"], "x", result["policy"], "iterations", len(result["iterations"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "outer", "finite"))
    parser.add_argument("gamma", nargs="?", type=int, choices=(1, 2, 3))
    args = parser.parse_args()
    if args.mode == "preflight":
        verify_frozen()
    elif args.mode == "finite":
        run(2, "G2_N32")
    else:
        run(args.gamma)
