"""Audit fixed-policy bounds for paired seat-JIT scenarios without pruning plain runs."""
import json
import os
from time import perf_counter

import gurobipy as gp

from profile_runs import FROZEN, HERE, LABEL, PHASE_A, ROOT, catalog, ccg, prior, verify_frozen, write_csv
from structure import prefix_bounds
from design import ARCS


def main():
    verify_frozen()
    FROZEN.init()
    base, opening = FROZEN.BASE, FROZEN.OPENING
    source, profiles, _, _, unique = catalog(base, opening)
    names = unique[:16]
    reference = json.loads((PHASE_A/"n16_DIRECT_DE.json").read_text(encoding="utf-8"))
    dates = [source[n].events[0].start for n in names if n.startswith("DE_ENGINE")]
    rows, metrics = [], []
    (HERE/"logs").mkdir(exist_ok=True)

    with FROZEN.env() as env:
        def solve(name, profile, policy, policy_id):
            start = perf_counter()
            path = HERE/"logs"/f"probe_{policy_id}_{name}.log"
            path.write_text("", encoding="utf-8")
            with gp.Model(name, env=env) as model:
                FROZEN.configure(model, seconds=90)
                model.Params.SoftMemLimit = 3
                model.Params.LogFile = os.path.relpath(path, ROOT)
                block = ccg.add_recourse_block(model, base, name, profile, policy)
                model.setObjective(ccg.on_time(block, base), gp.GRB.MAXIMIZE)
                model.update()
                assert model.NumVars == model.NumIntVars
                model.optimize()
                assert model.Status == gp.GRB.OPTIMAL and model.ObjVal == model.ObjBound and model.MIPGap == 0
                vector, residual = FROZEN.exact_vector(model, FROZEN.matrix_rows(model))
                q = int(model.ObjVal)
                assert q == model.ObjVal
                assert q == prior.selected_quantity(block, base, vector)
                ev = dict(status="OPTIMAL", solver_seconds=model.Runtime, solver_residual=residual,
                          log=path.relative_to(HERE).as_posix())
            seconds = perf_counter()-start
            metrics.append(dict(label=LABEL, policy_id=policy_id, experiment=name, Q=q,
                                wall_seconds=seconds, **ev))
            return q, seconds

        for policy_id, x in (("C", tuple(reference["policy"])), ("T", (0, 644, 0))):
            values = reference["verified"] if policy_id == "C" else {
                n: solve(n, profiles[n], x, policy_id)[0] for n in names}
            # Emulate evaluating the first fixed catalog ID; the incumbent is a valid worst upper bound.
            incumbent = values[names[0]]
            for day in dates:
                pair = f"DE_ENGINE_{day}", f"DE_GEAR_{day}"
                p, q = (profiles[n] for n in pair)
                assert p[0] == q[0] == opening
                assert p[1][(*ARCS["SEAT"], day)] == q[1][(*ARCS["SEAT"], day)]
                factors = {k: min(p[1].get(k, 1), q[1].get(k, 1)) for k in p[1].keys() | q[1].keys()}
                lower, wall = solve(f"intersection_{day}", (opening, factors), x, policy_id)
                for n in pair:
                    seat, pack, upper = prefix_bounds(base, profiles[n], x)
                    actual = values[n]
                    assert lower <= actual <= upper
                    rows.append(dict(label=LABEL, policy_id=policy_id, policy=x, day=day, scenario=n,
                        exact_service=actual, common_feasible_lower=lower, seat_jit_prefix_upper=seat,
                        pack_prefix_upper=pack, safe_upper=upper, pilot_scenario=names[0], pilot_service=incumbent,
                        certified_nonworst_at_pilot=lower>incumbent, certified_exact_without_individual_solve=lower==upper,
                        intersection_wall_seconds=wall, used_to_skip_any_plain_solve=False))
    write_csv("reachability_safe_bounds.csv", rows)
    write_csv("reachability_probe_solve_log.csv", metrics)
    print("Bounds", len(rows), "strict pilot exclusions", sum(r["certified_nonworst_at_pilot"] for r in rows),
          "tight sandwiches", sum(r["certified_exact_without_individual_solve"] for r in rows))


if __name__ == "__main__":
    main()
