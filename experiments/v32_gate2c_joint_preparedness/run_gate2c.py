"""Exact joint preparedness diagnostics, using unchanged V3.1 preparation balances."""

import argparse
import csv
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v31_gate1_gate2b_certification"
sys.path.insert(0, str(BASE))
from numerical_certification import (PARAMS, TOL, WINDOWS, identities, kind, prep_problem,
                                     prep_replay, solve_info, stationary_capacities)

from prefab_v25.data import CELL
from prefab_v25.source import load_tables

ALPHAS = tuple(map(Fraction, ("0.10", "0.25", "0.50", "0.75", "1.00")))
DELTAS = tuple(map(Fraction, ("0", "0.5", "1", "2")))
COVER = {"restrictive": 0, "base": Fraction(1, 2), "relaxed": 2, "technical-bound-only": None}
COST = {"engine": 730577, "gear": 268300, "battery": 964686, "seat": 104841, "seat_componment": 75486}
KIT_COST = 790726
BUDGETS = (0, 1_000_000, 10_000_000)  # integer cents, diagnostic only
BMAX_FILE = BASE / "numerical/gate2b_buffer_formation_limits.csv"
PR2_SHA = "fa13b2ebd7a7aa92efae3493dd952941523a7b06"
PR3_SHA = "1acb8872bedf99de5bed1e8d94ffbae2190cd7f2"
ORIGINAL_CROSSCHECK = HERE / "evidence/gate2c_bmax_crosscheck.csv"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(out, name, rows):
    with (out / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(out, name, value):
    (out / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode())


def old_projections(states):
    with BMAX_FILE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 455 and all(r["status"] == "PASS" and float(r["eta"]) == 1 for r in rows)
    result = {(int(r["H"]), r["node_id"], r["item_id"]): int(r["Bmax"]) for r in rows}
    assert result.keys() == {(h, *k) for h in WINDOWS for k in states}
    return result


def prepare(model, base, states, h, nominal, alpha, delta, storage):
    # Fractional RHS can be floored exactly because arc quantities are integer.
    caps = {a: int(c * (alpha[a] if isinstance(alpha, dict) else alpha)) for a, c in nominal.items()}
    arcs, flow, stock, limits, cap_rows = prep_problem(model, base, states, h, caps)
    terminal = {k: stock[(*k, h)] for k in states}
    oem_seat = [k for k, (g, _) in states.items() if k[0] == "zp7" and g == "seat"]
    missing = states.keys() - base.network.inventory_bounds.keys()
    assert len(oem_seat) == 4 and len(missing - set(oem_seat)) == 5
    for n, p in missing:
        key = n, p
        feeders = [a.key for a in arcs if a.destination == n and p in a.recipes]
        assert len(feeders) == 1 and base.network.initial[key] == 0
        tech = h * caps[feeders[0]]
        cover = COVER[storage]
        scenario = int(cover * nominal[feeders[0]]) if cover is not None and key not in oem_seat else None
        effective = tech if scenario is None else min(tech, scenario)
        limits[key] = (effective, effective, "SCENARIO_PARAMETER" if scenario is not None else "FLOW_TECHNICAL")
        for t in range(h + 1):
            stock[n, p, t].UB = effective
    pool = int(delta * 2000)
    for t in range(h + 1):
        model.addConstr(gp.quicksum(stock[(*k, t)] for k in oem_seat) <= pool, name=f"SharedOemSeat[{t}]")
    model.update()
    cost = gp.quicksum(COST[g] * terminal[k] for k, (g, _) in states.items() if k[1] not in CELL)
    cost += KIT_COST * model.getVarByName("TerminalCellKit")
    return arcs, flow, stock, limits, cap_rows, caps, terminal, tuple(oem_seat), pool, cost


def optimize(model, objective):
    model.setObjective(objective, GRB.MAXIMIZE)
    model.optimize()
    info = solve_info(model)
    assert model.Status == GRB.OPTIMAL and info["mip_gap"] == 0, info
    assert max(info[key] for key in ("integrality_error", "model_row_violation", "model_bound_violation")) <= TOL, info
    assert abs(info["objective"] - info["best_bound"]) <= TOL, info
    return info


def audit(model, block, h):
    arcs, flow, stock, limits, cap_rows, caps, terminal, seat, pool, cost = block
    error, inventory, resource = prep_replay(model, arcs, flow, stock, limits, caps, h)
    pool_violation = max(sum(inventory[(*k, t)] for k in seat) - pool for t in range(h + 1))
    error = max(0, error, pool_violation)
    assert error <= TOL
    return error, inventory, resource


def joint_witness(model, block, states, run, metadata, buffers, inventories, resources, flows):
    h = metadata["H"]
    error, inventory, resource = audit(model, block, h)
    arcs, flow, _, limits, cap_rows, caps, _, seat, pool, cost = block
    values = {k: round(inventory[(*k, h)]) for k in states}
    kit_values = [values[k] for p in CELL for k in values if k[1] == p]
    kits = kit_values[0] // 10
    assert kit_values == [10 * kits, 6 * kits, 4 * kits]
    spend = KIT_COST * kits + sum(COST[g] * values[k] for k, (g, _) in states.items() if k[1] not in CELL)
    assert abs(spend - cost.getValue()) <= TOL
    for t in range(h + 1):
        quantities = [inventory[(*k, t)] for k in seat]
        resources.append(dict(run_id=run, origin="zp7", destination="OEM_SEAT_POOL", slot=t,
                              resource_type="shared_storage", used=sum(quantities), integer_rhs=pool,
                              positive_skus=sum(q > TOL for q in quantities), violation=max(0, sum(quantities) - pool)))
    by_arc = {a.key: kind(a) for a in arcs}
    arc_data = {a.key: a for a in arcs}
    receipts, usage = defaultdict(float), defaultdict(float)
    positive_skus = Counter()
    for (i, j, p, t), v in model.getAttr("X", flow).items():
        arc = arc_data[i, j]
        receipts[j, p, t + arc.lead] += v
        for child, coefficient in arc.recipes[p]:
            usage[i, child, t] += float(coefficient) * v
        if v > TOL:
            positive_skus[i,j,t] += 1
            flows.append(dict(run_id=run, origin=i, destination=j, item_id=p, slot=t, quantity=round(v)))
    for i, j, t in cap_rows:
        used = resource[i,j,t]
        resources.append(dict(run_id=run, origin=i, destination=j, slot=t, resource_type=by_arc[i,j],
                              used=round(used), integer_rhs=caps[i,j], positive_skus=positive_skus[i,j,t],
                              violation=max(0, used-caps[i,j])))
    for (n,p,t), q in sorted(inventory.items()):
        if q > TOL or t == h:
            inventories.append(dict(run_id=run, node_id=n, item_id=p, slot=t, stock=round(q),
                                    upper_bound=limits[n,p][int(t == h)], basis=limits[n,p][2]))
    for (n,p), (group, lead) in sorted(states.items()):
        value = values[n,p]
        assert not value or h >= lead
        buffers.append(dict(run_id=run, node_id=n, item_id=p, group=group, quantity=value, minimum_H=lead))
    quality = dict(
        shared_capacity_violation=max(0, max(resource[i,j,t] - caps[i,j] for i,j,t in cap_rows)),
        inventory_violation=max(0, *(max(-q, q - limits[n,p][int(t == h)]) for (n,p,t),q in inventory.items())),
        oem_seat_pool_violation=max(0, *(sum(inventory[(*k,t)] for k in seat) - pool for t in range(h+1))),
        bom_violation=max(abs(inventory[n,p,t] - inventory.get((n,p,t-1),0) - receipts[n,p,t] + usage[n,p,t])
                          for n,p,t in inventory),
        integrality_violation=model.IntVio,
    )
    assert all(value == 0 for value in quality.values()), (run, quality)
    return dict(**quality, max_replay_violation=error, positive_positions=sum(v > 0 for v in values.values()),
                kit_count=kits, oem_seat=sum(values[k] for k in seat), material_cents=spend,
                positive_oem_seat_skus=sum(values[k] > 0 for k in seat),
                buffers_by_group=dict(Counter({g: sum(v for k,v in values.items() if states[k][0]==g)
                                               for g in set(group for group,_ in states.values())})))


def scenario_identity(block, h, alpha, delta, storage):
    scenario = dict(H=h, alpha=str(alpha), delta=str(delta), storage=storage,
                    kappa=str(COVER[storage]) if COVER[storage] is not None else None,
                    capacities=[[*k, q] for k,q in sorted(block[5].items())],
                    K_eff=[[*k, *bounds[:2]] for k,bounds in sorted(block[3].items())],
                    oem_seat_pool=block[8])
    return hashlib.sha256(json.dumps(scenario, sort_keys=True).encode()).hexdigest(), scenario


def projection_certificates(model, block, scenario_id, solo=False):
    """Use the full physical domain for C2C-07, or solo units for C2C-10."""
    terminal = block[6]
    kit = model.getVarByName("TerminalCellKit")
    cells = {k: (10, 6, 4)[CELL.index(k[1])] for k in terminal if k[1] in CELL}
    assert len(cells) == 3
    original = {k: var.UB for k, var in terminal.items()}
    units = [({k: 1}, var, "item-position") for k,var in sorted(terminal.items()) if k not in cells]
    units.append((cells, kit, "complete battery kit"))
    for members, objective, name in units:
        if solo:
            for k,var in terminal.items():
                var.UB = original[k] if k in members else 0
        info = optimize(model, objective)
        optimum = round(info["objective"])
        assert abs(optimum - info["objective"]) <= TOL
        for (n,p), factor in sorted(members.items()):
            assert abs(terminal[n,p].X - factor * optimum) <= TOL
            yield dict(scenario_id=scenario_id, node_id=n, item_id=p, projection_unit=name,
                       unit_optimum=optimum, factor=factor, Bproj=factor * optimum,
                       unit_best_bound=info["best_bound"], solver_status=info["solver_status"], mip_gap=info["mip_gap"])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--bundle", type=Path, required=True)
    cli.add_argument("--xlsb", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True)
    started = perf_counter()
    tables = load_tables(args.xlsb)
    base, states, provenance = identities(tables, args.bundle, args.xlsb)
    prereq = {g: json.loads((BASE / "numerical" / f"gate{g}_summary.json").read_text(encoding="utf-8"))
              for g in ("1", "2b")}
    assert prereq["1"]["status"] == prereq["2b"]["gross_status"] == "PASS"
    old = old_projections(states)
    nominal_int, cap_map = stationary_capacities(tables, Fraction(1))
    nominal = {(r["origin"],r["destination"]): Fraction(r["stationary_nominal_exact"]) for r in cap_map}
    assert {k: int(n) for k,n in nominal.items()} == nominal_int
    config = dict(**provenance, protocol="V3.2.1", gate2c_runner_sha256=sha256(Path(__file__)),
                  pr2_baseline=PR2_SHA, pr3_baseline=PR3_SHA, source_nominal_evidence="TRANSFORM_MEAN_INCLUDING_ZERO",
                  nominal_by_arc={"->".join(k): str(v) for k,v in nominal.items()},
                  alpha=[str(x) for x in ALPHAS], horizons=WINDOWS, delta=[str(x) for x in DELTAS],
                  storage_coverage={k: str(v) if v is not None else None for k,v in COVER.items()},
                  capacity_scenarios_evidence="SCENARIO_PARAMETER", cost_cents=COST, kit_cost_cents=KIT_COST,
                  cost_evidence="V31_CLASS_LEVEL_CALIBRATION_AND_PROXY", budget_cents=BUDGETS,
                  budget_evidence="SCENARIO_PARAMETER", test_a="maximize material value", test_b="maximize material value under capital budget",
                  empirical_residual_capacity="NOT_IDENTIFIED", baseline_Bmax_sha256=sha256(BMAX_FILE),
                  original_failure_csv_sha256=sha256(ORIGINAL_CROSSCHECK),
                  projection_scope="Physical prepared inventory domain, before diagnostic capital budget")
    write_json(out, "gate2c_config.json", config)
    results, buffers, inventories, resources, flows, cross = [], [], [], [], [], []
    scenarios, projections, frozen_reproduction = {}, {}, []
    with gp.Env(empty=True) as env:
        env.setParam("LogToConsole", 0)
        env.start()
        grid = {(h, a, Fraction(0), "technical-bound-only", "A", None) for h in WINDOWS for a in ALPHAS}
        grid |= {(23, a, d, s, "A", None) for a in ALPHAS for d in DELTAS for s in COVER}
        grid |= {(23, Fraction(1), Fraction(2), "technical-bound-only", "B", b) for b in BUDGETS}
        grid |= {(23, Fraction(1), d, "technical-bound-only", "OEM_SEAT", None) for d in DELTAS}
        for h,a,d,s,test,budget in sorted(grid):
            run = f"{test}_H{h}_a{float(a):.2f}_d{float(d):g}_{s}" + (f"_B{budget}" if budget is not None else "")
            with gp.Model(run, env=env) as model:
                for k,v in PARAMS.items():
                    model.setParam(k,v)
                model.Params.LogFile = str(out / "gate2c_gurobi.log")
                block = prepare(model, base, states, h, nominal, a, d, s)
                sid, scenario = scenario_identity(block, h, a, d, s)
                cost = block[-1]
                if budget is not None:
                    model.addConstr(cost <= budget, name="ProtectionCapital")
                obj = gp.quicksum(block[6][k] for k in block[7]) if test == "OEM_SEAT" else cost
                if run == "A_H23_a1.00_d2_technical-bound-only":
                    model.setObjective(obj, GRB.MAXIMIZE)
                    for name in ("gate2c_model.lp.gz", "gate2c_model.mps.gz"):
                        model.write(str(out / name))
                        assert gzip.decompress((out / name).read_bytes()) == gzip.decompress((HERE / "evidence" / name).read_bytes()), name
                info = optimize(model, obj)
                meta = dict(H=h, alpha=float(a), delta=float(d), storage=s, test=test, budget_cents=budget)
                evidence = joint_witness(model, block, states, run, meta, buffers, inventories, resources, flows)
                assert budget is None or evidence["material_cents"] <= budget
                joint_buffers = buffers[-len(states):]
                if sid not in projections:
                    assert test == "A" and budget is None
                    scenarios[sid] = scenario
                    projections[sid] = {(r["node_id"],r["item_id"]): r for r in projection_certificates(model, block, sid)}
                assert scenarios[sid] == scenario and projections[sid].keys() == states.keys()
                for row in joint_buffers:
                    certificate = projections[sid][row["node_id"],row["item_id"]]
                    observed = row["quantity"]
                    cross.append(dict(check="C2C-07", run_id=run, H=h, observed=observed, reference=certificate["Bproj"],
                                      status="PASS" if observed <= certificate["Bproj"] else "FAIL", **certificate))
                results.append(dict(run_id=run, scenario_id=sid, **meta, **info, **evidence))
                if (d == 0 and s == "technical-bound-only") or test != "A":
                    print(run, "verified", flush=True)
        for h in WINDOWS:
            with gp.Model(f"Comparable_Projection_H{h}", env=env) as model:
                for k,v in PARAMS.items():
                    model.setParam(k,v)
                model.Params.LogFile = str(out / "gate2c_gurobi.log")
                frozen = prepare(model, base, states, h, nominal, Fraction(1), Fraction(0), "technical-bound-only")
                sid, scenario = scenario_identity(frozen, h, Fraction(1), Fraction(0), "technical-bound-only")
                assert scenarios[sid] == scenario
                for row in projection_certificates(model, frozen, sid, solo=True):
                    k = row["node_id"], row["item_id"]
                    expected = old[(h, *k)]
                    observed = row["Bproj"]
                    frozen_reproduction.append(row)
                    cross.append(dict(check="C2C-10", run_id=f"frozen_projection_H{h}", H=h, observed=observed,
                                      reference=expected, status="PASS" if observed == expected else "FAIL", **row))
        with gp.Model("Simultaneous_Engine_Projections", env=env) as model:
            model.Params.LogFile = str(out / "gate2c_gurobi.log")
            _, _, _, _, _, _, end, _, _, _ = prepare(
                model, base, states, 2, nominal, Fraction(1), Fraction(0), "technical-bound-only")
            pair = sorted(k for k in end if k[0] == "engine-supplier_inv")[:2]
            for k in pair:
                model.addConstr(end[k] == old[(2, *k)])
            model.optimize()
            shared = dict(status="PASS" if model.Status == GRB.INFEASIBLE else "FAIL",
                          test="simultaneous Engine T1 single-location optima", states=pair, each=old[(2, *pair[0])],
                          solver_status=model.Status)
    monotone = []
    for dimension in ("alpha", "H"):
        buckets = {}
        key_fields = [k for k in ("H", "alpha", "delta", "storage") if k != dimension]
        for r in results:
            if r["test"] == "A":
                buckets.setdefault(tuple(r[k] for k in key_fields), []).append(r)
        for series in buckets.values():
            series.sort(key=lambda r:r[dimension])
            for lo, hi in zip(series, series[1:]):
                monotone.append(dict(dimension=dimension, low_run=lo["run_id"], high_run=hi["run_id"],
                                     low=lo["objective"], high=hi["objective"],
                                     status="PASS" if lo["objective"] <= hi["objective"] + TOL else "FAIL"))
    for filename, rows in (("joint_buffers", buffers), ("inventory_usage", inventories), ("resource_usage", resources),
                           ("shared_capacity_audit", [r for r in resources if r["positive_skus"] > 1 or r["resource_type"]=="shared_storage"]),
                           ("flow_witnesses", flows), ("bmax_crosscheck", cross), ("monotonicity_audit", monotone)):
        write_csv(out, f"gate2c_{filename}.csv", rows)
    failures = Counter(r["check"] for r in cross if r["status"] == "FAIL")
    checks = {f"C2C-{i:02d}": "PASS" for i in range(1, 11)}
    for k in failures:
        checks[k] = "FAIL"
    if shared["status"] != "PASS":
        checks["C2C-03"] = "FAIL"
    for r in monotone:
        if r["status"] == "FAIL":
            checks["C2C-08" if r["dimension"] == "alpha" else "C2C-09"] = "FAIL"
    prior = {"Gate0":"PASS", "Gate1":prereq["1"]["status"], "Gate2A":"PASS", "Gate2B_gross":prereq["2b"]["gross_status"]}
    residual_status = config["empirical_residual_capacity"]
    passed = all(v == "PASS" for v in checks.values())
    ready = passed and all(v == "PASS" for v in prior.values()) and residual_status == "NOT_IDENTIFIED"
    write_json(out, "gate2c_scenarios.json", scenarios)
    write_csv(out, "gate2c_scenario_projections.csv", [r for rows in projections.values() for r in rows.values()])
    write_json(out, "gate2c_summary.json", dict(protocol=config["protocol"], status="PASS" if passed else "FAIL", checks=checks,
               READY_FOR_GATE3=ready, EMPIRICAL_RESIDUAL_CAPACITY=residual_status, prior_gate_status=prior,
               scenario_count=len(scenarios), comparison_counts=dict(Counter(r["check"] for r in cross)),
               frozen_projection_units=sum(r["factor"] == 1 or r["factor"] == 10 for r in frozen_reproduction),
               blockers=[k for k,v in checks.items() if v=="FAIL"], comparison_failures=dict(failures),
               shared_negative_control=shared, results=results, runtime_seconds=perf_counter()-started))


if __name__ == "__main__":
    main()
