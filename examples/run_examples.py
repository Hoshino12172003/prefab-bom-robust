from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prefab_bom_robust.examples import example_a, example_b
from prefab_bom_robust.solvers import solve_ccg, solve_direct
from prefab_bom_robust.uncertainty import budget_extreme_points


for data in (example_a(), example_b()):
    direct = solve_direct(data)
    ccg = solve_ccg(data)
    print({
        "instance": data.name,
        "vertices_T3": budget_extreme_points(data.V, data.Gamma3),
        "direct": {"status": direct.status, "objective": direct.objective, "worst_gap": direct.worst_gap,
                   "runtime": direct.runtime, "plan": direct.plan},
        "ccg": {"status": ccg.status, "objective": ccg.objective, "worst_gap": ccg.worst_gap,
                "runtime": ccg.runtime, "iterations": len(ccg.iterations), "plan": ccg.plan},
    })
