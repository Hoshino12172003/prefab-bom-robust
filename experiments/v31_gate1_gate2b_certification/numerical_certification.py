"""V3.1 Gate 1 and Gate 2B only. Input files remain outside the release."""

import argparse
import csv
import gzip
import hashlib
import json
import os
import platform
import subprocess
from collections import Counter, defaultdict
from fractions import Fraction
from io import BytesIO
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile

import gurobipy as gp
from gurobipy import GRB
from openpyxl import load_workbook

from prefab_v25.data import CELL, NOMINAL, receipts
from prefab_v25.source import load_tables
from prefab_v3.base import ASSEMBLY, source_base
from source_preflight import audit_source


GATE1_CASES = ("zero_storage", "technical_bound")
WINDOWS = (2, 20, 21, 22, 23)
TOL = 1e-6
PARAMS = {"Threads": 1, "Seed": 0, "MIPGap": 0.0, "MIPGapAbs": 0.0,
          "FeasibilityTol": 1e-8, "IntFeasTol": 1e-9, "TimeLimit": 3600}


def csv_file(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def json_file(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def workbook_map(bundle, source_states):
    with ZipFile(bundle) as archive:
        files = {Path(n).name: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
    checksums = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
    assert checksums["V31_Final_Math_Spec.docx"] == "29c89699de58d58b46de5ded9278183f21b57b55a6052c8607154bd9349c0ebf"
    workbook = load_workbook(BytesIO(files["V31_Gate0_Gate2_Audit.xlsx"]), read_only=True, data_only=True)
    try:
        mapping = list(workbook["Gate0_91_State_Mapping"].values)[1:]
        trace = list(workbook["Gate2_Reachability"].values)[1:]
    finally:
        workbook.close()
    assert len(mapping) == len(trace) == len(source_states) == 91
    assert all(row[3:6] == ("YES", "YES", "PASS") for row in mapping)
    expected = {(row["node_id"], row["item_id"]): (row["group"], row["lead"]) for row in source_states}
    assert {(n, p): g for n, p, g, *_ in mapping} == {k: g for k, (g, _) in expected.items()}
    assert {(n, p): (g, int(h)) for n, p, g, h, *_ in trace} == expected
    return expected, checksums


def kind(arc):
    return "production_capacity" if arc.origin.endswith("_prod") or arc.key == ASSEMBLY else "transportation_capacity"


def build_flows(model, arcs, schedule, states):
    """Each scheduled arc consumes its complete recipe at dispatch and credits its output at arrival."""
    keys = [(*a.key, p, t) for a in arcs for t in schedule[a.key] for p in a.recipes]
    flow = model.addVars(keys, vtype=GRB.INTEGER, name="flow")
    arrivals, consumption = defaultdict(gp.LinExpr), defaultdict(gp.LinExpr)
    for a in arcs:
        for t in schedule[a.key]:
            for p, recipe in a.recipes.items():
                var = flow[(*a.key, p, t)]
                if (a.destination, p) in states:
                    arrivals[a.destination, p, t + a.lead] += var
                for child, coef in recipe:
                    if (a.origin, child) in states:
                        consumption[a.origin, child, t] += float(coef) * var
    return flow, arrivals, consumption


def solve_info(model):
    status = {GRB.OPTIMAL: "OPTIMAL", GRB.TIME_LIMIT: "TIME_LIMIT", GRB.INFEASIBLE: "INFEASIBLE",
              GRB.INF_OR_UNBD: "INF_OR_UNBD", GRB.UNBOUNDED: "UNBOUNDED", GRB.NUMERIC: "NUMERIC"}
    bound = model.ObjBound
    data = dict(solver_status=status.get(model.Status, str(model.Status)), solution_count=model.SolCount,
                best_bound=bound if abs(bound) < GRB.INFINITY else None, runtime_seconds=model.Runtime,
                node_count=model.NodeCount, objective=None, mip_gap=None)
    if model.SolCount:
        data.update(objective=model.ObjVal, mip_gap=model.MIPGap, integrality_error=model.IntVio,
                    model_row_violation=model.ConstrVio, model_bound_violation=model.BoundVio)
    return data


def capacity_rows(network, arcs, values):
    rows = []

    def add(category, arc, period, item, used, limit):
        rows.append(dict(category=category, arc="->".join(arc), period=period, item_id=item,
                         activity=used, limit=limit, violation=max(0, used - limit)))

    for a in arcs:
        for t in network.periods:
            activity = sum(values.get((*a.key, p, t), 0) for p in a.recipes)
            add(kind(a), a.key, t, "", activity, a.capacity[t])
            if (*a.key, t) in network.group_caps:
                add("max_flow_group", a.key, t, "", activity, network.group_caps[(*a.key, t)])
    for (i, j, p, t), limit in network.product_caps.items():
        add("max_flow_product", (i, j), t, p, values.get((i, j, p, t), 0), limit)
    return rows


def gate1(env, base, states, case, out):
    network = base.network
    periods = network.periods
    historical = receipts(network, NOMINAL)
    arcs = network.arcs
    due = {g.id: g.representative.due for g in network.groups}
    bounds = dict(network.inventory_bounds)
    bounds.update({(n, p): (0, 0 if case == "zero_storage" or n == "zp7" else
                   sum(a.capacity[t] for a in arcs if a.destination == n and p in a.recipes
                       for t in periods if t + a.lead in periods)
                   + sum(historical.get((n, p, t), 0) for t in periods))
                   for n, p in states.keys() - bounds.keys()})
    schedule = {a.key: [t for t in periods if t + a.lead in periods] for a in arcs}
    out.mkdir(parents=True, exist_ok=True)
    with gp.Model(f"V31Gate1_{case}", env=env) as model:
        for key, value in PARAMS.items():
            model.setParam(key, value)
        model.Params.LogFile = str(out / "gate1_gurobi.raw.log")
        flow, incoming, used = build_flows(model, arcs, schedule, states)
        inventory = model.addVars([(n, p, t) for n, p in states for t in periods], vtype=GRB.INTEGER, name="I")
        for g in network.groups:
            for t in periods:
                if t > due[g.id]:
                    flow[(*ASSEMBLY, g.id, t)].UB = 0
            model.addConstr(flow.sum(*ASSEMBLY, g.id, "*") <= len(g.orders), name=f"Demand[{g.id}]")
        for a in arcs:
            for t in periods:
                total = flow.sum(*a.key, "*", t)
                model.addConstr(total <= a.capacity[t], name=f"{kind(a)}[{a.origin},{a.destination},{t}]")
                group_limit = network.group_caps.get((*a.key, t))
                if group_limit is not None:
                    model.addConstr(total <= group_limit, name=f"Group[{a.origin},{a.destination},{t}]")
        for key, cap in network.product_caps.items():
            if key in flow:
                model.addConstr(flow[key] <= cap, name="Product[" + ",".join(map(str, key)) + "]")
        for (n, p), (lo, hi) in bounds.items():
            previous = network.initial.get((n, p), 0)
            for t in periods:
                key = (n, p, t)
                var = inventory[key]
                var.LB, var.UB = lo, hi
                model.addConstr(var == previous + historical.get(key, 0) + incoming[key] - used[key],
                                name=f"Balance[{n},{p},{t}]")
                previous = var
        model.setObjective(flow.sum(*ASSEMBLY, "*", "*"), GRB.MAXIMIZE)
        model.update()
        model.write(str(out / "gate1_model.lp"))
        model.write(str(out / "gate1_model.mps.gz"))
        model.optimize()
        info = dict(case=case, variables=model.NumVars, constraints=model.NumConstrs, nonzeros=model.NumNZs,
                    exact_groups=len(due), historical_dispatch_rows=len(network.historical), **solve_info(model))
        info["status"] = "FAIL" if model.Status == GRB.INFEASIBLE else "BLOCKED"
        if model.SolCount:
            flows = model.getAttr("X", flow)
            inv = model.getAttr("X", inventory)
            info.update(replay_gate1(base, bounds, historical, flows, inv, out))
            info["objective_recompute_error"] = abs(info["replayed_objective"] - model.ObjVal)
            errors = (info["max_balance_residual"], info["max_order_violation"], info["objective_recompute_error"],
                      info["integrality_error"], info["model_row_violation"], info["model_bound_violation"],
                      *info["capacity_max_violation"].values())
            if max(errors) > TOL:
                info["status"] = "FAIL"
            elif model.Status == GRB.OPTIMAL and info["mip_gap"] == 0:
                info["status"] = "PASS"
            with gzip.open(out / "gate1_solution.csv.gz", "wt", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(("kind", "node", "destination", "item", "period", "value"))
                writer.writerows(("flow", *key, value) for key, value in flows.items() if value)
                writer.writerows(("inventory", n, "", p, t, value) for (n, p, t), value in inv.items() if value)
        return info


def replay_gate1(base, bounds, historical, flows, inv, out):
    unscaled_in, used, delivered, groups = Counter(), Counter(), Counter(), Counter()
    by_arc = {a.key: a for a in base.network.arcs}
    for (i, j, p, t), quantity in flows.items():
        arc = by_arc[i, j]
        if (i, j) == ASSEMBLY:
            delivered[t] += quantity
            groups[p, t] += quantity
        elif (j, p) in bounds:
            unscaled_in[j, p, t + arc.lead] += quantity
        for child, coefficient in arc.recipes[p]:
            if (i, child) in bounds:
                used[i, child, t] += quantity * float(coefficient)
    rows, peaks = [], []
    capacity = capacity_rows(base.network, by_arc.values(), flows)
    for (n, p), (lo, hi) in sorted(bounds.items()):
        opening = base.network.initial.get((n, p), 0)
        for t in base.network.periods:
            key = (n, p, t)
            residual = opening + historical.get(key, 0) + unscaled_in[key] - used[key] - inv[key]
            rows.append(dict(node_id=n, item_id=p, period=t, opening=opening, historical=historical.get(key, 0),
                             decision_arrivals=unscaled_in[key], consumption_or_dispatch=used[key],
                             closing=inv[key], residual=residual))
            capacity.append(dict(category="inventory_capacity", arc=n, period=t, item_id=p,
                                 activity=inv[key], limit=hi, violation=max(0, inv[key] - hi, lo - inv[key])))
            opening = inv[key]
        peaks.append(dict(node_id=n, item_id=p, maximum=max(inv[n, p, t] for t in base.network.periods),
                          upper_bound=hi, upper_bound_basis="DIRECT_MODEL" if (n, p) in base.network.inventory_bounds else
                          "JIT_SCENARIO" if n == "zp7" else "TECHNICAL" if hi else "ZERO_SCENARIO"))
    period_rows = [dict(period=t, on_time_deliveries=delivered[t], assembly_capacity=by_arc[ASSEMBLY].capacity[t])
                   for t in base.network.periods]
    for name, data in (("balance_residuals", rows), ("inventory_peak", peaks), ("capacity_audit", capacity),
                       ("delivery_by_period", period_rows)):
        csv_file(out / f"gate1_{name}.csv", data)
    maxima = defaultdict(float)
    for row in capacity:
        maxima[row["category"]] = max(maxima[row["category"]], row["violation"])
    demand_vio = max(max(0, sum(groups[g.id, t] for t in base.network.periods) - len(g.orders),
                         sum(groups[g.id, t] for t in base.network.periods if t > g.representative.due))
                     for g in base.network.groups)
    return dict(max_balance_residual=max(abs(r["residual"]) for r in rows), max_order_violation=demand_vio,
                capacity_max_violation=dict(maxima), replayed_objective=sum(delivered.values()),
                balance_rows=len(rows))


def stationary_capacities(tables, eta):
    raw = defaultdict(dict)
    for origin, destination, period, capacity in tables["capacity_at_arc"]:
        raw[origin, destination][int(period)] = int(capacity)
    rows, limits = [], {}
    for (i, j), period_cap in sorted(raw.items()):
        values = list(period_cap.values())
        assert set(period_cap) == set(range(61, 75))
        mean = Fraction(sum(values), len(values))
        limits[i, j] = int(eta * mean)
        rows.append(dict(origin=i, destination=j, **{f"t{t}": period_cap[t] for t in range(61, 75)},
                         minimum=min(values), maximum=max(values),
                         nonzero_periods=";".join(str(t) for t in sorted(period_cap) if period_cap[t] > 0),
                         mean=float(mean), stationary_nominal_exact=str(mean), stationary_nominal=float(mean),
                         eta=float(eta), preparation_capacity=float(eta * mean), integer_rhs=limits[i, j],
                         evidence="TRANSFORM_MEAN_INCLUDING_ZERO"))
    return limits, rows


def prep_problem(model, base, states, horizon, caps):
    network = base.network
    arcs = tuple(a for a in network.arcs if a.key != ASSEMBLY)
    times = range(horizon + 1)
    # Zero-lead operations can process an arrival at a slot's ending boundary.
    # No arc has more than H usable slots and there is no terminal source gift.
    schedule = {a.key: range(horizon - a.lead + 1) if a.lead else range(1, horizon + 1) for a in arcs}
    flow, incoming, used = build_flows(model, arcs, schedule, states)
    stock = model.addVars([(n, p, t) for n, p in states for t in times], vtype=GRB.INTEGER, name="Ipre")
    cap_rows = {}
    for a in arcs:
        for t in schedule[a.key]:
            cap_rows[a.origin, a.destination, t] = model.addConstr(
                flow.sum(*a.key, "*", t) <= caps[a.key], name=f"PrepCapacity[{a.origin},{a.destination},{t}]")
    bounds = {}
    for n, p in states:
        receipts_per_day = sum(caps[a.key] for a in arcs if a.destination == n and p in a.recipes)
        direct = network.inventory_bounds.get((n, p))
        basis = "DIRECT_MODEL_LIMIT" if direct is not None else "JIT_ZERO" if n == "zp7" else "FLOW_TECHNICAL"
        upper = direct[1] if direct is not None else 0 if basis == "JIT_ZERO" else horizon * receipts_per_day
        terminal = upper - network.initial.get((n, p), 0)
        assert terminal >= 0
        bounds[n,p] = (upper, terminal, basis)
        last = 0
        for t in times:
            k = (n, p, t)
            var = stock[k]
            var.UB = terminal if t == horizon else upper
            model.addConstr(var == last + incoming[k] - used[k], name=f"PrepBalance[{n},{p},{t}]")
            last = var
    kit = model.addVar(vtype=GRB.INTEGER, name="TerminalCellKit")
    component_node, = {n for (n, p) in states if p in CELL}
    for p, q in zip(CELL, (10, 6, 4)):
        model.addConstr(stock[component_node, p, horizon] == q * kit, name=f"Kit[{p}]")
    return arcs, flow, stock, bounds, cap_rows


def prep_replay(model, arcs, flow, stock, bounds, caps, horizon):
    quantities = model.getAttr("X", flow)
    inventory = model.getAttr("X", stock)
    arrivals, used, taken = Counter(), Counter(), Counter()
    arc_map = {a.key: a for a in arcs}
    for (i, j, p, t), q in quantities.items():
        a = arc_map[i,j]
        arrivals[j,p,t + a.lead] += q
        taken[i,j,t] += q
        for child, coefficient in a.recipes[p]:
            used[i,child,t] += q * float(coefficient)
    residual = max(abs(q - inventory.get((n, p, t - 1), 0) - arrivals[n,p,t] + used[n,p,t])
                   for (n, p, t), q in inventory.items())
    cap_error = max((q - caps[i,j] for (i,j,_), q in taken.items()), default=0)
    stock_error = max(max(-q, q - bounds[n,p][int(t == horizon)]) for (n,p,t),q in inventory.items())
    cells = [inventory[n, p, horizon] / q for p,q in zip(CELL,(10,6,4)) for n,k in bounds if p == k]
    return max(residual, cap_error, stock_error, max(cells)-min(cells)), inventory, taken


def upstream_arcs(arcs, target):
    result = set()
    queue = [target]
    visited = set()
    while queue:
        n, p = queue.pop()
        if (n, p) in visited:
            continue
        visited.add((n, p))
        for a in arcs:
            if a.destination == n and p in a.recipes:
                result.add(a.key)
                queue.extend((a.origin, child) for child, _ in a.recipes[p])
    return result


def finite_rows(model, arcs, flow, stock, bounds, cap_rows, caps, states, h, eta):
    results, binding = [], []
    for (n,p), (group, lead) in sorted(states.items()):
        target = (n,p,h)
        model.setObjective(stock[target], GRB.MAXIMIZE)
        model.optimize()
        info = solve_info(model)
        error, bmax = None, None
        label = "BLOCKED"
        tight = []
        if model.SolCount:
            error, inventory, taken = prep_replay(model, arcs, flow, stock, bounds, caps, h)
            if max(error, model.IntVio, model.ConstrVio, model.BoundVio) > TOL:
                label = "FAIL"
            elif model.Status == GRB.OPTIMAL and model.MIPGap == 0:
                label = "PASS"
                bmax = round(inventory[target])
                if (h < lead and bmax) or abs(bmax - model.ObjVal) > TOL:
                    label = "FAIL"
                if h < lead:
                    tight.append(("lead_time", f"minimum_H={lead}", None, None, None))
                if bmax == bounds[n,p][1]:
                    tight.append(("terminal_storage", bounds[n,p][2], h, float(bmax), bounds[n,p][1]))
                route = upstream_arcs(arcs, (n,p))
                for a in arcs:
                    if a.key in route:
                        for i,j,t in cap_rows:
                            q = taken[i,j,t]
                            if (i,j) == a.key and q > 0 and abs(q - caps[i,j]) <= TOL:
                                tight.append((kind(a), f"{i}->{j}", t, q, caps[i,j]))
                if not tight:
                    tight.append(("no_single_tight_integer_row", "BOM/integer lot or alternate resource mix", None, None, None))
        common = dict(node_id=n, item_id=p, group=group, H=h, eta=float(eta))
        results.append(dict(**common, temporal_reachable=h >= lead, minimum_H=lead, quantity_feasible=(bmax > 0) if bmax is not None else None,
                            Bmax=bmax, upper_bound_basis=bounds[n,p][2], terminal_headroom=bounds[n,p][1],
                            physical_storage_verified=False, scope="GROSS_CAPACITY", status=label,
                            binding_constraint=";".join(sorted({r[0] for r in tight})),
                            binding_resource=";".join(sorted({r[1] for r in tight})),
                            independent_max_violation=error, **info))
        binding.extend(dict(**common, constraint_kind=c, resource=r, slot=t, used=q, limit=k,
                            evidence="STRUCTURAL" if c in ("lead_time", "terminal_storage") else "TIGHT_IN_WITNESS")
                       for c,r,t,q,k in tight)
    return results, binding


def identities(tables, bundle, xlsb):
    preflight = audit_source(tables)
    states, checksums = workbook_map(bundle, preflight["structural_time_check"]["states"])
    assert preflight["structural_time_check"]["status"] == "PASS"
    base, _ = source_base(tables)
    for a in base.network.arcs:
        for p, recipe in a.recipes.items():
            assert (a.destination, p) in states or a.key == ASSEMBLY
            assert all((a.origin, child) in states or (a.origin, child) in base.network.external
                       for child, _ in recipe)
    checksums.update({f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (xlsb,bundle)})
    metadata = dict(commit_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), input_sha256=checksums,
                    python=platform.python_version(), gurobi=".".join(map(str,gp.gurobi.version())),
                    config=PARAMS, residual_tolerance=TOL, random_seed=PARAMS["Seed"])
    return base, states, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsb", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gate", choices=("1", "2b", "both"), default="both")
    parser.add_argument("--eta", default="1")
    args = parser.parse_args()
    eta = Fraction(args.eta)
    if not 0 < eta <= 1:
        parser.error("eta must be in (0, 1]")
    tables = load_tables(args.xlsb)
    base, states, metadata = identities(tables, args.bundle, args.xlsb)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with gp.Env(empty=True) as env:
        env.setParam("LogToConsole", 0)
        env.start()
        if args.gate in ("1", "both"):
            started = perf_counter()
            history = [dict(origin=i, destination=j, item_id=p, dispatch=t, quantity=q,
                            arrival=t + a.lead, enters_operation_horizon=t + a.lead in base.network.periods)
                       for i,j,p,t,q in base.network.historical for a in base.network.arcs if (i,j)==a.key]
            csv_file(out / "gate1_historical_flows.csv", history)
            cases = [gate1(env, base, states, case, out / case) for case in GATE1_CASES]
            for case in cases:
                print(case, flush=True)
            both_optimal = all(r["status"] == "PASS" for r in cases)
            same = both_optimal and abs(cases[0]["objective"] - cases[1]["objective"]) <= TOL
            aggregate = "PASS" if same else "FAIL" if any(r["status"] == "FAIL" for r in cases) else "BLOCKED"
            json_file(out / "gate1_summary.json", dict(**metadata, status=aggregate, cases=cases,
                      historical_rows=len(history), equal_objectives=same if both_optimal else None,
                      runtime_seconds=perf_counter()-started))
        if args.gate in ("2b", "both"):
            started = perf_counter()
            caps, cap_data = stationary_capacities(tables, eta)
            csv_file(out / "gate2b_arc_capacity_mapping.csv", cap_data)
            all_results, all_binding = [], []
            for h in WINDOWS:
                with gp.Model(f"V31Gate2B_H{h}", env=env) as model:
                    for key, value in PARAMS.items():
                        model.setParam(key, value)
                    model.Params.LogFile = os.fspath(out / f"gate2b_H{h}.raw.log")
                    arcs, flow, stock, bounds, cap_rows = prep_problem(model, base, states, h, caps)
                    results, binding = finite_rows(model, arcs, flow, stock, bounds, cap_rows, caps, states, h, eta)
                    all_results.extend(results)
                    all_binding.extend(binding)
                    print(f"H={h} {Counter(r['status'] for r in results)}", flush=True)
            csv_file(out / "gate2b_buffer_formation_limits.csv", all_results)
            csv_file(out / "gate2b_binding_constraints.csv", all_binding)
            csv_file(out / "gate2b_reachability_crosscheck.csv",
                     [{k: r[k] for k in ("node_id", "item_id", "group", "H", "eta", "minimum_H",
                                          "temporal_reachable", "quantity_feasible", "Bmax", "status")}
                      for r in all_results])
            gross = "PASS" if all(r["status"] == "PASS" for r in all_results) else (
                "FAIL" if any(r["status"] == "FAIL" for r in all_results) else "BLOCKED")
            json_file(out / "gate2b_summary.json", dict(**metadata, status="BLOCKED" if gross == "PASS" else gross,
                      gross_status=gross, residual_status="BLOCKED", residual_evidence="RESIDUAL_CAPACITY_NOT_CERTIFIED",
                      windows=WINDOWS, eta=str(eta), optimization_count=len(all_results),
                      by_window={h: dict(temporal=sum(r["temporal_reachable"] for r in all_results if r["H"]==h),
                                         positive=sum(bool(r["quantity_feasible"]) for r in all_results if r["H"]==h))
                                 for h in WINDOWS}, runtime_seconds=perf_counter()-started))


if __name__ == "__main__":
    main()
