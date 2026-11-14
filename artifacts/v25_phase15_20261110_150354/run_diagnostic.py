"""Phase 1.5 only. Build the frozen DE blocks at the requested diagnostic budgets."""
import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

import gurobipy as gp
from gurobipy import GRB
from examples.run_v25_phase1 import serial
from prefab_v25.data import BUFFER_NAMES, receipts
from prefab_v25.formal import frozen_runs, manifest_bytes
from prefab_v25.model import TOL, _audit, _block, initial_state
from prefab_v25.source import compile_network, load_tables


def solve(network, run, budget, path):
    with gp.Model('V25_DE') as model:
        model.Params.LogToConsole = 0
        model.Params.Threads = 4
        model.Params.Seed = 20261110
        model.Params.TimeLimit = 180
        model.Params.MIPGap = model.Params.MIPGapAbs = 0
        model.Params.FeasibilityTol = model.Params.IntFeasTol = 1e-9
        buffers = [model.addVar(vtype=GRB.INTEGER, name=name) for name in BUFFER_NAMES]
        cost = gp.quicksum(c*x for c, x in zip(run.costs, buffers))
        model.addConstr(cost <= budget)
        state = initial_state(network, buffers)
        blocks = [_block(model, network, scenario, state, receipts(network, scenario), f's{i}')
                  for i, scenario in enumerate(run.scenarios)]
        rho = model.addVar(lb=0, ub=1, name='rho')
        for block in blocks:
            model.addConstr(block[-1] >= network.demand_weight*rho)
        model.setObjective(rho, GRB.MAXIMIZE)

        with path.with_suffix('.log').open('x', encoding='utf-8') as log:
            def log_message(m, where):
                if where == GRB.Callback.MESSAGE:
                    log.write(m.cbGet(GRB.Callback.MSG_STRING))

            model.optimize(log_message)

        result = dict(label='DIAGNOSTIC_ONLY', gurobi_version=gp.gurobi.version(),
                      status={2: 'OPTIMAL', 3: 'INFEASIBLE', 9: 'TIME_LIMIT'}.get(model.Status, str(model.Status)),
                      seconds=model.Runtime, solution_count=model.SolCount, nodes=model.NodeCount,
                      budget=budget, variables=model.NumVars, integer_variables=model.NumIntVars,
                      constraints=model.NumConstrs, certified=False)
        if model.SolCount:
            raw = [x.X for x in buffers]
            used = sum(c*x for c, x in zip(run.costs, raw))
            state = initial_state(network, raw)
            result.update(objective=model.ObjVal, bound=model.ObjBound, gap=model.MIPGap,
                          buffers=dict(zip(BUFFER_NAMES, map(round, raw))), budget_used=used,
                          budget_slack=budget-used, solver_constraint_residual=model.ConstrVio,
                          solver_bound_residual=model.BoundVio, solver_integrality_residual=model.IntVio,
                          scenarios={})
            residuals = [model.ConstrVio, model.BoundVio, model.IntVio, max(0, used-budget)]
            for scenario, block in zip(run.scenarios, blocks):
                arrays = [{k: v.X for k, v in variables.items()} for variables in block[:4]]
                audit = _audit(network, scenario, state, *arrays)
                audit['service_ratio'] = audit['weighted_on_time']/network.demand_weight
                audit['rho_residual'] = max(0, model.ObjVal-audit['service_ratio'])
                residuals.extend(v for k, v in audit.items() if k.endswith('_residual'))
                result['scenarios'][scenario.name] = dict(
                    audit, **dict(zip(('inventory', 'supply', 'dispatch', 'deliveries'), arrays)))
            result['quality_residual'] = max(residuals)
            result['worst_on_time'] = min(row['weighted_on_time'] for row in result['scenarios'].values())
            result['certified'] = (model.Status == GRB.OPTIMAL and abs(model.ObjVal-model.ObjBound) <= TOL
                                   and result['quality_residual'] <= TOL)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--formal-audit', type=Path, required=True)
    args = parser.parse_args()
    network, _ = compile_network(load_tables(args.source))
    runs = {run.id: run for run in frozen_runs(manifest_bytes(args.manifest))}
    formal = json.loads(args.formal_audit.read_text(encoding='utf-8'))
    b0 = formal['results']['DE_B0']
    baseline = round(b0['objective']*network.demand_weight)
    assert b0['certified'] and baseline == 25974
    b100 = runs['nominal_B100'].budget
    for packs in (100, 150, 200):
        budget = b100*packs//100
        path = Path(__file__).with_name(f'DIAGNOSTIC_ONLY_DE_B{packs}')
        result = solve(network, runs['DE_B0'], budget, path)
        with gzip.open(path.with_suffix('.json.gz'), 'xt', encoding='utf-8') as out:
            json.dump(serial(result), out, ensure_ascii=False, allow_nan=False)
        summary = {k: v for k, v in result.items() if k != 'scenarios'}
        path.with_suffix('.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        print(path.name, summary, flush=True)
        if not result['certified']:
            return 1
        if result['worst_on_time'] > baseline:
            break
    return 0


if __name__ == '__main__':
    sys.exit(main())
