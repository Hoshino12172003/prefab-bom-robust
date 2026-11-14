"""Run the authorized Direct MILPs. All rows and logs are diagnostic only."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from fractions import Fraction
from math import lcm
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

from frontier import HERE, LABEL, PHASE20, RATIO, RATIO_BOUNDS, RISKS, ROOT, SCALES, Frontier

sys.path.insert(0, str(ROOT / 'src'))
from prefab_v25.data import (CELL, COMPONENT_ARC, NOMINAL, OEM, PACK, PROD, T1, Scenario, receipts)
from prefab_v25.model import _block
from prefab_v25.source import compile_network, load_tables

POSITIONS = ('x_C', 'x_T', 'x_O')
BATTERY = {*CELL, PACK}
SOURCE = Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
REQUEST = Path('private_inputs/attachment/已粘贴的文本.txt')


def export(name, rows):
    with (HERE / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_prospective():
    with (PHASE20 / 'sha256_manifest.csv').open(encoding='utf-8-sig', newline='') as f:
        frozen = list(csv.DictReader(f))
    for row in frozen:
        assert digest(ROOT / row['path']) == row['sha256'], row
    source, _ = compile_network(load_tables(SOURCE))
    groups = tuple(g for g in source.groups if (PACK, 1) in g.representative.bom)
    assembly = source.arcs[0]
    assert assembly.key == (OEM, 'zp8')
    ids = {g.id for g in groups}
    raw_vins = {(str(o.vin), o.due, o.node, o.bom) for g in groups for o in g.orders}
    with (PHASE20 / 'bev_orders.csv').open(encoding='utf-8-sig', newline='') as f:
        assert raw_vins == {(r['vin'], int(r['source_due']), r['due_node'], tuple(json.loads(r['bom']).items()))
                            for r in csv.DictReader(f)}
    arcs = (replace(assembly, recipes={key: v for key, v in assembly.recipes.items() if key in ids}), *source.arcs[1:])
    network = replace(source, groups=groups, arcs=arcs, initial={},
                      historical=tuple(r for r in source.historical if r[2] not in BATTERY),
                      external=tuple((node, item) for node, item in source.external if item not in BATTERY))
    network = replace(network, initial={k: source.initial[k] if k[1] not in BATTERY else 0
                                        for k in network.state_keys()})
    assert len(groups) == 28 and network.demand_weight == 3003
    return network, len(frozen)


class Direct:
    def __init__(self, network, risk, env):
        self.network = network
        self.risk = risk
        model = self.model = gp.Model(f'Phase21_{risk}', env=env)
        model.Params.Threads = 1
        model.Params.MIPGap = model.Params.MIPGapAbs = 0
        model.Params.IntFeasTol = model.Params.FeasibilityTol = model.Params.OptimalityTol = 1e-9
        model.Params.LogToConsole = 0
        self.x = tuple(model.addVar(vtype=GRB.INTEGER, name=n) for n in POSITIONS)
        self.z = model.addVar(vtype=GRB.INTEGER, ub=3003, name='Z')
        c, t1, o = self.x
        self.release = release = model.addVars(network.periods, vtype=GRB.INTEGER, name='K_released')
        factor, prod, trans = RISKS[risk]
        self.scenario = Scenario(risk, {}, dict.fromkeys(network.periods, prod), dict.fromkeys(network.periods, trans))
        self.background = receipts(network, NOMINAL)
        inflow = self.background.copy()
        previous = 0
        for t in network.periods:
            residual = factor.numerator*c - factor.denominator*release[t]
            model.addConstr(residual >= 0, name=f'release_floor_L[{t}]')
            model.addConstr(residual <= factor.denominator-1, name=f'release_floor_U[{t}]')
            for item, qty in zip(CELL, (10, 6, 4)):
                inflow[PROD, item, t] = qty * (release[t] - previous)
            previous = release[t]
        initial = network.initial | {(T1, PACK): t1, (OEM, PACK): o}
        self.block = _block(model, network, self.scenario, initial, inflow, 'prospective')
        inventory, _, dispatch, _, service = self.block
        for t in network.periods:
            for item, qty in zip(CELL, (10, 6, 4)):
                model.addConstr(inventory[PROD, item, t] + qty*(c-release[t])
                                <= network.inventory_bounds[PROD, item][1], name=f'physical_storage[{item},{t}]')
        # RSP-C admits no regular battery credits. The upstream arc and its
        # original bounds still exist; it has no qualifying stock to dispatch.
        assert all(network.initial[COMPONENT_ARC[0], item] == 0 for item in CELL)
        assert not set(dispatch.keys()).intersection({(*COMPONENT_ARC, PACK, t) for t in network.periods})
        model.addConstr(self.z <= service, name='on_time_count')
        self.budget = model.addConstr(c+t1+o <= 0, name='diagnostic_budget')
        model.setObjective(self.z, GRB.MAXIMIZE)
        model.update()

    def freedom(self):
        return [dict(label=LABEL, risk=self.risk, variable=v.VarName, vtype=v.VType,
                     lower_bound=v.LB, upper_bound='inf' if v.UB >= GRB.INFINITY else v.UB,
                     service_objective_coefficient=v.Obj, forced_positive=False)
                for v in self.x]

    def replay(self, solution, expected_budget, allowed, target):
        network = self.network
        x = tuple(solution[v.index] for v in self.x)
        assert all(q >= 0 and (allowed & (1 << j) or not q) for j, q in enumerate(x))
        scale, coeffs, budget = expected_budget
        spend = sum(a*q for a, q in zip(coeffs, x))
        assert spend <= budget
        inventory, supply, dispatch, service, _ = self.block
        states = network.initial | {(T1, PACK): x[1], (OEM, PACK): x[2]}
        delta = Counter(self.background)
        factor = RISKS[self.risk][0]
        released = 0
        for t in network.periods:
            next_release = solution[self.release[t].index]
            assert next_release == int(x[0]*factor) >= released
            for item, qty in zip(CELL, (10, 6, 4)):
                delta[PROD, item, t] += qty*(next_release-released)
            released = next_release
        for (n, item, t), var in supply.items():
            assert (n, item) in network.external and item not in BATTERY
            delta[n, item, t] += solution[var.index]
        for arc in network.arcs:
            for t in network.periods:
                total = 0
                for product, recipe in arc.recipes.items():
                    key = (*arc.key, product, t)
                    value = solution[dispatch[key].index]
                    assert value <= network.product_caps.get(key, value)
                    total += value
                    for item, qty in recipe:
                        delta[arc.origin, item, t] -= qty*value
                    delta[arc.destination, product, t+arc.lead] += value
                assert total <= arc.capacity[t]*self.scenario.factor(arc.key, t)
                assert total <= network.group_caps.get((*arc.key, t), total)
                if arc.key == COMPONENT_ARC:
                    assert total == 0
        ontime = 0
        for group in network.groups:
            order = group.representative
            delivered = 0
            for t in network.periods:
                quantity = solution[service[group.id, t].index]
                delta[order.node, group.id, t] -= quantity
                delivered += quantity
                ontime += quantity if t <= order.due else 0
            assert delivered <= len(group.orders)
        for t in network.periods:
            for (node, item) in states:
                key = node, item, t
                states[node, item] += delta[key]
                lo, hi = network.inventory_bounds.get((node, item), (0, float('inf')))
                assert lo <= states[node, item] == solution[inventory[key].index] <= hi
            for item, qty in zip(CELL, (10, 6, 4)):
                assert states[PROD, item]+qty*(x[0]-solution[self.release[t].index]) <= network.inventory_bounds[PROD, item][1]
        z = solution[self.z.index]
        assert ontime >= z >= target
        return x, z, ontime, str(Fraction(spend, scale))

    def solve(self, name, k, ratio, premium, certificate, allowed=7, floor=0, exact=False, endpoint=None):
        model = self.model
        # Rational prices are scaled into integer row coefficients.
        prices = (Fraction(1), ratio, ratio*(1+premium))
        scale = lcm(*(p.denominator for p in prices))
        coeffs = tuple(int(p*scale) for p in prices)
        rhs = int(ratio*k*scale)
        for j, (v, a) in enumerate(zip(self.x, coeffs)):
            v.UB = GRB.INFINITY if allowed & (1 << j) else 0
            model.chgCoeff(self.budget, v, a)
        self.budget.RHS = rhs
        self.z.LB, self.z.UB = floor, floor if exact else 3003
        expected_z, ranges, witnesses = certificate
        obj, sense, expected = self.z, GRB.MAXIMIZE, expected_z
        warm = witnesses[0]
        if endpoint is not None:
            j, high = endpoint
            obj, sense, expected = self.x[j], GRB.MAXIMIZE if high else GRB.MINIMIZE, ranges[j][int(high)]
            warm = witnesses[2*j+int(high)]
        model.setObjective(obj, sense)
        model.reset()
        for v, q in zip(self.x, warm):
            v.Start = q
        self.z.Start = expected_z
        log = HERE / 'logs' / f'{name}.log'
        model.Params.LogFile = os.path.relpath(log)
        model.message(f'{LABEL} {name} k={k} ratio={ratio} premium={premium} floor={floor} exact={exact}')
        model.optimize()
        assert model.Status == GRB.OPTIMAL, (name, model.Status)
        objective = round(model.ObjVal)
        assert abs(model.ObjVal-objective) <= 1e-7 and abs(model.ObjBound-objective) <= 1e-7, name
        assert objective == expected, (name, objective, expected)
        raw = model.getAttr('X')
        rounded = [round(v) for v in raw]
        residual = max(model.ConstrVio, model.BoundVio, model.IntVio)
        assert min(rounded) >= 0 and residual <= 1e-7 and max(abs(a-b) for a,b in zip(raw,rounded)) <= 1e-7
        x, z, ontime, spend = self.replay(rounded, (scale, coeffs, rhs), allowed, floor)
        return dict(label=LABEL, run=name, risk=self.risk, k=k, ratio=str(ratio), premium=str(premium),
                    budget=str(ratio*k), target=floor, objective=objective, best_bound=model.ObjBound,
                    status='OPTIMAL', mip_gap=model.MIPGap, residual=residual, integer_ledger_residual=0,
                    seconds=model.Runtime, z=z, realized_ontime=ontime, x_C=x[0], x_T=x[1], x_O=x[2],
                    spend=spend, exact_crosscheck='MATCH', log=log.relative_to(HERE).as_posix())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def endpoints(direct, frontier, name, k, ratio, premium, z, epsilon):
    floor = -(-(1-epsilon).numerator*z // (1-epsilon).denominator)
    certificate = frontier.selection(premium, target=floor)
    rows = []
    for j, position in enumerate(POSITIONS):
        for high in (False, True):
            side = 'max' if high else 'min'
            row = direct.solve(f'{name}_{position}_{side}', k, ratio, premium, certificate, floor=floor,
                               exact=epsilon == 0, endpoint=(j, high))
            rows.append(dict(**row, z_star=z, epsilon=str(epsilon), position=position, endpoint=side))
    return rows


def threshold_audit():
    result = []
    for ratio in (RATIO, *RATIO_BOUNDS):
        scales = SCALES.items() if ratio == RATIO else [(5, SCALES[5])]
        for days, k in scales:
            for risk in RISKS:
                frontier = Frontier(risk, k, ratio)
                result.extend(dict(label=LABEL, risk=risk, days=days, k=k, ratio=str(ratio), budget=str(ratio*k),
                                   **event) for event in frontier.events())
    export('position_premium_breakpoints.csv', result)
    l3 = [r for r in result if r['ratio'] == str(RATIO) and r['risk'] == 'L3' and r['days'] == 5]
    drops = [Fraction(r['premium_exact']) for r in l3 if r['z_right'] < r['z_at']]
    first = min(drops) if drops else Fraction(0)
    later = [Fraction(r['premium_exact']) for r in l3 if Fraction(r['premium_exact']) > first]
    probe = (first+min(later))/2 if later else first+1
    return result, probe


def main():
    network, protected = load_prospective()
    (HERE / 'logs').mkdir(exist_ok=True)
    events, probe = threshold_audit()
    rows = {name: [] for name in ('buffer_variable_freedom', 'single_buffer_capability', 'equal_cost_dominance',
                                 'risk_location_policy_response', 'optimal_policy_set_ranges',
                                 'near_optimal_policy_ranges', 'threshold_direct_checks')}
    zero, equal = Fraction(0), Fraction(1)
    with gp.Env() as env:
        for risk in RISKS:
            direct = Direct(network, risk, env)
            freedom = direct.freedom()
            assert all(r['vtype'] == 'I' and r['lower_bound'] == 0 and r['upper_bound'] == 'inf'
                       and r['service_objective_coefficient'] == 0 for r in freedom)
            unit = []
            for j, pos in enumerate(POSITIONS):
                # All three unit vectors and the origin are feasible at K1 with service floor zero.
                case = Frontier(risk, SCALES[1], equal)
                if j == 0:
                    unit.append(direct.solve(f'P1_{risk}_zero', SCALES[1], equal, zero,
                                             case.selection(zero, allowed=0), allowed=0))
                unit.append(direct.solve(f'P1_{risk}_{pos}', 1, equal, zero, Frontier(risk, 1, equal).selection(
                    zero, allowed=1<<j, target=0), allowed=1<<j, endpoint=(j, True)))
            rows['buffer_variable_freedom'].extend(dict(**r, zero_feasible=True, isolated_unit_feasible=True,
                                                       log=unit[j+1]['log']) for j,r in enumerate(freedom))
            for days, k in SCALES.items():
                phys = Frontier(risk, k, equal)
                for allowed in (1, 2, 4, 7):
                    if risk != 'NOM' and allowed != 7:
                        continue
                    kind = SUPPORT_NAME[allowed]
                    row = direct.solve(f'P2_{risk}_K{days}_{kind}', k, equal, zero,
                                       phys.selection(zero, allowed), allowed=allowed)
                    if risk == 'NOM':
                        rows['single_buffer_capability'].append(dict(**row, days=days, mode=kind))
                    if allowed == 7:
                        value, ranges, _ = phys.selection(zero)
                        rows['equal_cost_dominance'].append(dict(**row, days=days, optimal_OEM_only=value == k,
                                                               all_optima_OEM_only=ranges[2] == (k,k)))
                economic = Frontier(risk, k, RATIO)
                for tag, premium in (('ZERO', zero), ('PROBE', probe)):
                    name = f'P5_{risk}_K{days}_{tag}'
                    row = direct.solve(name, k, RATIO, premium, economic.selection(premium))
                    rows['risk_location_policy_response'].append(dict(**row, days=days, premium_case=tag))
                if days != 5:
                    continue
                for tag, frontier, ratio, premium in (('EQUAL', phys, equal, zero),
                        ('COST_ZERO', economic, RATIO, zero), ('COST_PROBE', economic, RATIO, probe)):
                    z = frontier.selection(premium)[0]
                    rows['optimal_policy_set_ranges'].extend(endpoints(
                        direct, frontier, f'P6_{risk}_{tag}', k, ratio, premium, z, zero))
                    for eps in (Fraction(1,1000), Fraction(1,200), Fraction(1,100)):
                        rows['near_optimal_policy_ranges'].extend(endpoints(
                            direct, frontier, f'P7_{risk}_{tag}_{eps.denominator}', k, ratio, premium, z, eps))
                if risk == 'L3':
                    points = [Fraction(r['premium_exact']) for r in events if r['ratio'] == str(RATIO)
                              and r['risk'] == risk and r['days'] == 5 and r['z_right'] < r['z_at']]
                    for tag, premium in (('FIRST_AT', min(points)), ('LAST_AT', max(points)),
                                         ('TAIL', max(points)+1)):
                        rows['threshold_direct_checks'].append(direct.solve(
                            f'P4_{tag}', k, RATIO, premium, economic.selection(premium)))
            direct.model.dispose()
            print(f'{risk} completed', flush=True)
            for key, table in rows.items():
                if table:
                    export(f'{key}_audit.csv' if key == 'buffer_variable_freedom' else f'{key}.csv', table)
    run_files = list((HERE / 'logs').glob('*.log'))
    audit = dict(git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 label=LABEL, source_sha256=digest(SOURCE), user_request_sha256=digest(REQUEST),
                 phase20_manifest_sha256=digest(PHASE20/'sha256_manifest.csv'), phase20_files_verified=protected,
                 gurobi_version=gp.gurobi.version(), ratio=str(RATIO), ratio_support=[str(x) for x in RATIO_BOUNDS],
                 diagnostic_scales=SCALES, common_premium_probe=str(probe), oem_premium_estimate=None,
                 diagnostic_runs=len(run_files), algorithm_runs=0, formal_managerial_runs=0,
                 breakpoint_events=len(events), tables={k:len(v) for k,v in rows.items()})
    (HERE/'run_summary.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')


SUPPORT_NAME = {1:'C_only', 2:'T1_only', 4:'OEM_only', 7:'all_open'}

if __name__ == '__main__':
    main()
