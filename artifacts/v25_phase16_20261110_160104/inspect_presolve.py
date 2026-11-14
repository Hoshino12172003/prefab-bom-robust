"""Inspect presolve output without executing an additional optimization."""
from run_audit import (
    BUFFER_NAMES, FORMAL, HERE, SOURCE, build, compile_network, csv_file, frozen_runs,
    gp, info, load_tables, manifest_bytes,
)


def main():
    network, _ = compile_network(load_tables(SOURCE))
    runs = {r.id: r for r in frozen_runs(manifest_bytes(FORMAL/'manifest.json'))}
    rows = []
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag', 0)
        env.start()
        for name in ('nominal_B0', 'nominal_B20', 'nominal_B50', 'nominal_B100', 'DE_B0', 'DE_B50'):
            for aggregate in ((1, 0) if name == 'nominal_B20' else (1,)):
                model, _, _ = build(env, network, runs[name])
                with model:
                    model.Params.Threads = 4
                    model.Params.Seed = 20261110
                    model.Params.MIPGap = model.Params.MIPGapAbs = 0
                    model.Params.FeasibilityTol = model.Params.IntFeasTol = 1e-9
                    model.Params.Aggregate = aggregate
                    with model.presolve() as presolved:
                        row = dict(run=name, aggregate=aggregate, **info(presolved))
                        for key in BUFFER_NAMES:
                            var = presolved.getVarByName(key)
                            row[key] = 'eliminated' if var is None else f'[{var.LB:g}, {var.UB:g}]'
                        rows.append(row)
                        print(row, flush=True)
    csv_file(HERE/'presolve_reduction_probe.csv', rows)


if __name__ == '__main__':
    main()
