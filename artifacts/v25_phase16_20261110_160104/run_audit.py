"""Phase 1.6 evidence runner. The production model and Phase 1 archive are read-only."""
import argparse
import csv
import gzip
import json
import math
import os
import platform
import re
import subprocess
import sys
from ast import literal_eval
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

import gurobipy as gp
from gurobipy import GRB
from prefab_v25 import model as production
from prefab_v25.data import BUFFER_NAMES, receipts
from prefab_v25.formal import frozen_runs, manifest_bytes, solve_frozen
from prefab_v25.source import compile_network, load_tables

FORMAL = ROOT / 'artifacts/v25_formal_20261110'
WITNESSES = ROOT / 'tests/fixtures/v25_formal_feasible_witnesses.json.gz'
WITNESS_SHA256 = '706e4c5393cf3932370d7690bd8305512c0015bd6d4bc76b02dfb5286107c693'
SOURCE = Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
TARGETS = {'nominal_B20': (20, 26468), 'nominal_B50': (50, 26498), 'DE_B50': (50, 26024)}
ARRAYS = ('inventory', 'supply', 'dispatch', 'deliveries')
EPS = 1e-9


def digest(path):
    with path.open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def csv_file(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def gzip_json(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)


def scalar(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def parameters(model, env):
    return {p: scalar(getattr(model.Params, p)) for p in env._paramlist('*')
            if p not in ('CSAuthToken', 'CSManagerPassword', 'ServerPassword', 'CloudAccessID',
                         'CloudSecretKey', 'WLSAccessID', 'WLSSecret', 'WLSToken', 'CSApiAccessID',
                         'CSApiSecret', 'CSRouterPassword')}


def info(model):
    model.update()
    objective = model.getObjective()
    return dict(fingerprint=f'0x{model.Fingerprint & 0xffffffff:08x}', variables=model.NumVars,
                rows=model.NumConstrs, nonzeros=int(model.DNumNZs), integer_variables=model.NumIntVars,
                objective_direction='MAXIMIZE' if model.ModelSense == GRB.MAXIMIZE else 'MINIMIZE',
                objective_nonzeros=objective.size(), objective_constant=objective.getConstant())


def build(env, network, run):
    model = gp.Model('V25_DE' if run.de else 'V25_nominal', env=env)
    buffers = [model.addVar(vtype=GRB.INTEGER, name=name) for name in BUFFER_NAMES]
    model.addConstr(gp.quicksum(c*x for c, x in zip(run.costs, buffers)) <= run.budget)
    state = production.initial_state(network, buffers)
    blocks = [production._block(model, network, scenario, state, receipts(network, scenario), f's{i}')
              for i, scenario in enumerate(run.scenarios)]
    if run.de:
        rho = model.addVar(lb=0, ub=1, name='rho')
        for block in blocks:
            model.addConstr(block[-1] >= network.demand_weight*rho)
        model.setObjective(rho, GRB.MAXIMIZE)
    else:
        model.setObjective(blocks[0][-1]/network.demand_weight, GRB.MAXIMIZE)
    model.update()
    return model, buffers, blocks


@contextmanager
def capture_original(env, network, payload, run, out):
    """Intercept the archived runner's call boundary, before optimize executes."""
    captured = {}

    class Captured(Exception):
        pass

    class Capture(gp.Model):
        def __init__(self, name):
            super().__init__(name, env=env)

        def optimize(self, *args, **kwargs):
            captured['info'] = info(self)
            captured['params'] = parameters(self, env)
            captured['model'] = self.copy()
            raise Captured

    with patch.object(production.gp, 'Model', Capture):
        try:
            solve_frozen(network, payload, run.id, time_limit=180, threads=4,
                         log=out / f'{run.id}_capture_call_boundary.txt')
        except Captured:
            pass
    with captured.pop('model') as original:
        yield original, captured


def compare(run_id, lhs, rhs, source):
    """Compare ordered names and all actual binary64 coefficients, without tolerance."""
    left_vars, right_vars = lhs.getVars(), rhs.getVars()
    left_rows, right_rows = lhs.getConstrs(), rhs.getConstrs()
    fields = dict(objective_direction=0, objective_constant=0, variable_count=0, constraint_count=0,
                  variable_name=0, lower_bound=0, upper_bound=0, variable_type=0, objective_coefficient=0,
                  constraint_name=0, constraint_direction=0, rhs=0, matrix_missing_left=0,
                  matrix_missing_right=0, matrix_coefficient=0)
    first = {}

    def pair(field, location, a, b):
        if a != b:
            fields[field] += 1
            first.setdefault(field, (location, a, b))

    pair('objective_direction', 'model', lhs.ModelSense, rhs.ModelSense)
    pair('objective_constant', 'model', lhs.ObjCon, rhs.ObjCon)
    pair('variable_count', 'model', len(left_vars), len(right_vars))
    pair('constraint_count', 'model', len(left_rows), len(right_rows))
    for i, (a, b) in enumerate(zip(left_vars, right_vars)):
        for field, attr in (('variable_name', 'VarName'), ('lower_bound', 'LB'), ('upper_bound', 'UB'),
                            ('variable_type', 'VType'), ('objective_coefficient', 'Obj')):
            pair(field, f'{i}:{a.VarName}', getattr(a, attr), getattr(b, attr))
    for i, (a, b) in enumerate(zip(left_rows, right_rows)):
        for field, attr in (('constraint_name', 'ConstrName'), ('constraint_direction', 'Sense'), ('rhs', 'RHS')):
            pair(field, f'{i}:{a.ConstrName}', getattr(a, attr), getattr(b, attr))
        x, y = lhs.getRow(a), rhs.getRow(b)
        u = {x.getVar(j).VarName: x.getCoeff(j) for j in range(x.size())}
        v = {y.getVar(j).VarName: y.getCoeff(j) for j in range(y.size())}
        for name in u:
            where = f'{i}:{a.ConstrName}/{name}'
            if name not in v:
                pair('matrix_missing_right', where, u[name], None)
            else:
                pair('matrix_coefficient', where, u[name], v[name])
        for name in v.keys()-u.keys():
            pair('matrix_missing_left', f'{i}:{a.ConstrName}/{name}', None, v[name])
    return [dict(run=run_id, comparison=source, field=field, differences=count,
                 first_location=first.get(field, ('', '', ''))[0],
                 first_left=scalar(first.get(field, ('', '', ''))[1]),
                 first_right=scalar(first.get(field, ('', '', ''))[2])) for field, count in fields.items()]


def evaluate(expr, values):
    return math.fsum([expr.getConstant(), *(expr.getCoeff(i)*values[expr.getVar(i).index]
                                           for i in range(expr.size()))])


def dense(model, buffers, blocks, run, x, snapshots):
    values = [0.0]*model.NumVars
    present = set()
    for var, value in zip(buffers, x):
        values[var.index] = value
        present.add(var.index)
    for scenario, block in zip(run.scenarios, blocks):
        for vars_, key in zip(block[:4], ARRAYS):
            data = {literal_eval(k): v for k, v in snapshots[scenario.name][key].items()}
            assert data.keys() == vars_.keys()
            for index, var in vars_.items():
                values[var.index] = data[index]
                present.add(var.index)
    rho = model.getVarByName('rho')
    if rho is not None:
        # The historical recourse archive does not store rho. Read its upper bounds
        # from actual matrix rows, using the archived recourse and no delivery summary.
        limits = []
        for constraint in model.getConstrs()[-len(run.scenarios):]:
            row = model.getRow(constraint)
            term = model.getCoeff(constraint, rho)
            assert term < 0 and constraint.Sense == '>'
            limits.append((evaluate(row, values)-constraint.RHS)/(-term))
        values[rho.index] = min(rho.UB, *limits)
        present.add(rho.index)
    assert len(present) == len(values)
    return values


def quality(model, values):
    row_max = 0.0
    for constr in model.getConstrs():
        delta = evaluate(model.getRow(constr), values)-constr.RHS
        residual = abs(delta) if constr.Sense == '=' else delta if constr.Sense == '<' else -delta
        row_max = max(row_max, residual)
    vars_ = model.getVars()
    bound = max(0, max(max(v.LB-x, x-v.UB) for v, x in zip(vars_, values)))
    integer = max(abs(x-round(x)) for v, x in zip(vars_, values) if v.VType == GRB.INTEGER)
    return dict(row_residual=row_max, bound_residual=bound, integrality_residual=integer)


def objective_record(model, run, label, values, demand, recorded=None):
    objective = evaluate(model.getObjective(), values)
    return dict(run=run.id, vector=label, objective_direction='MAXIMIZE',
                recomputed_objective=objective, objective_times_demand=objective*demand,
                objective_form='rho' if run.de else 'on_time_linear_form/divided_by_demand',
                recorded_solver_objval=recorded, **quality(model, values))


def solve(model, run, settings, start, start_value, out, env, demand):
    tag = f'{run.id}__{settings}'
    logfile = out / f'{tag}.log'
    model.Params.LogFile = os.path.relpath(logfile)
    model.Params.LogToConsole = 0
    if settings.startswith('frozen'):
        model.Params.Threads = 4
        model.Params.Seed = 20261110
        model.Params.MIPGap = model.Params.MIPGapAbs = 0
        model.Params.FeasibilityTol = model.Params.IntFeasTol = 1e-9
    else:
        model.Params.Threads = 1
    if 'presolve0' in settings:
        model.Params.Presolve = 0
    if settings.endswith('aggregate0'):
        model.Params.Aggregate = 0
    if 'opttol' in settings:
        model.Params.OptimalityTol = 1e-9
    if settings.endswith('dual'):
        model.Params.Method = 1
    assert all(model.getParamInfo(p)[2] == model.getParamInfo(p)[-1] for p in
               ('TimeLimit', 'BestObjStop', 'BestBdStop', 'Cutoff', 'SolutionLimit'))
    save_json(out / f'{tag}.parameters.json', parameters(model, env))
    if start is not None:
        model.setAttr('Start', model.getVars(), start)
        model.update()
        model.write(os.path.relpath(out / f'{tag}.mst'))
    print('START', tag, flush=True)
    model.optimize()
    log = logfile.read_text(encoding='utf-8', errors='replace')
    loaded = re.findall(r'Loaded user MIP start with objective ([^\s]+)', log)
    row = dict(run=run.id, profile=settings, start_injected=start is not None,
               start_objective=start_value, start_objective_times_demand=None if start_value is None else start_value*demand,
               accepted=bool(loaded), logged_start_objective=loaded[-1] if loaded else '',
               start_messages=' | '.join(line for line in log.splitlines() if re.search('mip start', line, re.I)),
               status=GRB.Status.OPTIMAL if model.Status == GRB.OPTIMAL else model.Status,
               status_name='OPTIMAL' if model.Status == GRB.OPTIMAL else str(model.Status),
               seconds=model.Runtime, work=model.Work, log=logfile.name, solution_count=model.SolCount,
               model_fingerprint=info(model)['fingerprint'])
    if model.SolCount:
        values = model.getAttr('X')
        obj = evaluate(model.getObjective(), values)
        row.update(objval=model.ObjVal, objbound=model.ObjBound, objboundc=model.ObjBoundC,
                   mipgap=model.MIPGap, objective_recomputed=obj, delivery_equivalent=obj*demand,
                   upper_delivery_equivalent=model.ObjBound*demand,
                   **quality(model, values))
        model.write(os.path.relpath(out / f'{tag}.sol.gz'))
    print('END', tag, row.get('objval'), row.get('objbound'), row['accepted'], flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('primary', 'isolate', 'all-formal', 'precision', 'recertify'), default='primary')
    args = parser.parse_args()
    opt_dir = HERE / 'opt_model_identity'
    opt_dir.mkdir(exist_ok=True)
    payload = manifest_bytes(FORMAL / 'manifest.json')
    archive = json.loads((FORMAL/'audit.json').read_text(encoding='utf-8'))
    assert digest(WITNESSES) == WITNESS_SHA256
    witnesses = gzip_json(WITNESSES)
    network, _ = compile_network(load_tables(SOURCE))
    runs = {r.id:r for r in frozen_runs(payload)}
    results_file = HERE / 'execution.json'
    if results_file.exists():
        evidence = json.loads(results_file.read_text(encoding='utf-8'))
        assert not evidence.get('immediate_stop')
    else:
        evidence = dict(metadata={}, comparison=[], objectives=[], solves=[])
    demand = network.demand_weight
    with gp.Env(empty=True) as env:
        env.setParam('LogToConsole', 0)
        env.start()
        if args.stage == 'primary':
            for name in runs:
                run = runs[name]
                old = archive['results'][name]
                path = FORMAL / old['solution_artifact']
                assert path.name == f'{name}_solution.json.gz' and digest(path) == old['solution_sha256']
                model, buffers, blocks = build(env, network, run)
                with model, capture_original(env, network, payload, run, opt_dir) as (captured, origin):
                    origin['archive_has_model_file'] = False
                    log = (FORMAL/f'{name}.log').read_text(encoding='utf-8')
                    fingerprint, = re.findall(r'Model fingerprint: (0x[0-9a-f]+)', log)
                    actual = info(model)
                    assert actual['fingerprint'] == origin['info']['fingerprint'] == fingerprint
                    evidence['metadata'][name] = dict(reconstruction=actual, original_entrypoint=origin,
                                                      historical_log_fingerprint=fingerprint, exports={})
                    if name in TARGETS:
                        rows = compare(name, captured, model, 'historical_entrypoint_replay_vs_new_builder')
                        evidence['comparison'].extend(rows)
                        for extension in ('lp', 'mps'):
                            export = opt_dir / f'{name}.{extension}'
                            model.write(os.path.relpath(export))
                            evidence['metadata'][name]['exports'][extension] = dict(file=export.name, sha256=digest(export))
                    x = [old['buffers'][key] for key in BUFFER_NAMES]
                    values = dense(model, buffers, blocks, run, x, gzip_json(path))
                    archive_obj = objective_record(model, run, 'archived_solution', values, demand, old['objective'])
                    archive_obj['archived_bound'] = old['bound']
                    evidence['objectives'].append(archive_obj)
                    assert abs(archive_obj['recomputed_objective']-old['objective']) <= EPS
                    if name in TARGETS:
                        retained, expected = TARGETS[name]
                        values = dense(model, buffers, blocks, run, (0, 0, retained), witnesses[name])
                        candidate = objective_record(model, run, 'known_feasible_witness', values, demand)
                        assert abs(candidate['objective_times_demand']-expected) <= EPS
                        assert max(v for k, v in candidate.items() if k.endswith('_residual')) <= EPS
                        evidence['objectives'].append(candidate)
                print('IDENTITY', name, actual['fingerprint'], flush=True)
            csv_file(HERE/'model_coefficient_diff.csv', evidence['comparison'])
            csv_file(HERE/'objective_recomputation.csv', evidence['objectives'])
            save_json(results_file, evidence)
            if any(row['differences'] for row in evidence['comparison']):
                return 3
            plan = [(name, setting, True) for name in TARGETS for setting in ('frozen_start', 'default_start')]
        elif args.stage == 'isolate':
            plan = [('nominal_B20', setting, False) for setting in
                    ('frozen_no_start', 'frozen_aggregate0', 'frozen_presolve0')]
            plan.extend((name, 'frozen_no_start', False) for name in ('nominal_B50', 'DE_B50', 'nominal_B100'))
        elif args.stage == 'all-formal':
            plan = [(name, 'frozen_presolve0', name in TARGETS) for name in runs]
        elif args.stage == 'recertify':
            plan = [(name, 'frozen_opttol', False) for name in runs]
        else:
            plan = [('nominal_B20', 'frozen_opttol', False)]
            plan.extend(('nominal_B100', setting, False) for setting in
                        ('frozen_opttol', 'frozen_presolve0_opttol', 'frozen_presolve0_dual'))

        for name, setting, inject in plan:
            if any((r['run'], r['profile']) == (name, setting) for r in evidence['solves']):
                continue
            if args.stage == 'precision' and name == 'nominal_B100' and any(
                r['run'] == name and abs(r.get('delivery_equivalent', -1)-26570) <= EPS for r in evidence['solves']
            ):
                break
            run = runs[name]
            model, buffers, blocks = build(env, network, run)
            with model:
                if not evidence['metadata'][name]['exports']:
                    with capture_original(env, network, payload, run, opt_dir) as (captured, _):
                        evidence['comparison'].extend(compare(
                            name, captured, model, 'historical_entrypoint_replay_vs_new_builder'))
                    csv_file(HERE/'model_coefficient_diff.csv', evidence['comparison'])
                    for extension in ('lp', 'mps'):
                        path = opt_dir / f'{name}.{extension}'
                        model.write(os.path.relpath(path))
                        evidence['metadata'][name]['exports'][extension] = dict(file=path.name, sha256=digest(path))
                start = None
                start_value = None
                if inject:
                    start = dense(model, buffers, blocks, run, (0, 0, TARGETS[name][0]), witnesses[name])
                    start_value = evaluate(model.getObjective(), start)
                record = solve(model, run, setting, start, start_value, HERE, env, demand)
            evidence['solves'].append(record)
            if record['accepted'] and record['status_name'] == 'OPTIMAL' and record['objval']+EPS < start_value:
                evidence['immediate_stop'] = record
                (HERE/'reproduce_stop.py').write_text(
                    f"import gurobipy as gp\nm = gp.read('opt_model_identity/{name}.mps')\n"
                    f"m.read('{name}__{setting}.mst')\n"
                    + ("m.Params.Threads=4\nm.Params.Seed=20261110\nm.Params.MIPGap=0\n"
                       "m.Params.MIPGapAbs=0\nm.Params.FeasibilityTol=1e-9\nm.Params.IntFeasTol=1e-9\n"
                       if setting.startswith('frozen') else 'm.Params.Threads=1\n')
                    + f"m.optimize()\nprint('obj/bound/known start',m.ObjVal,m.ObjBound,{start_value!r})\n",
                    encoding='utf-8')
            save_json(results_file, evidence)
            csv_file(HERE/'feasible_start_verification.csv', evidence['solves'])
            if evidence.get('immediate_stop'):
                return 4
    return 0


if __name__ == '__main__':
    sys.exit(main())
