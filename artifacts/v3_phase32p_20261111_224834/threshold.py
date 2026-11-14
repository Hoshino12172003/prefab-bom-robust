"""Evaluate only the preregistered contingent cost brackets."""
import json
from fractions import Fraction as F

from grid import BASELINE, COST_LEVELS, FROZEN, HERE, load
from run_grid import RESULTS, run_jobs


def activity(result, position):
    projection = result["projections"]
    if projection[f"{position}_max"]["value"] == 0:
        return "IMPOSSIBLE"
    if projection[f"{position}_min"]["value"] > 0:
        return "REQUIRED"
    return "OPTIONAL"


def contingent_jobs(protocol, cost_rows):
    jobs, edges = [], []
    for axis in ("T", "O"):
        def key(vary, other):
            return (vary, other) if axis == "T" else (other, vary)
        bracket = next(
            ((other, left, right, p)
             for other in COST_LEVELS for left, right in zip(COST_LEVELS, COST_LEVELS[1:])
             for p in ("T", "O")
             if {activity(cost_rows[key(left, other)], p), activity(cost_rows[key(right, other)], p)}
             == {"IMPOSSIBLE", "REQUIRED"}), None)
        if bracket is None:
            continue
        other, left, right, position = bracket
        edges.append(dict(axis=axis, other=other, left=left, right=right, position=position))
        points = [(f"Q{i}", F(left)+(right-left)*F(i, 4), F(0)) for i in (1, 2, 3)]
        points += [(f"{name}_{side}", F(level), offset) for name, level in (("L", left), ("R", right))
                   for side, offset in (("LOW_B", F(-1, 2)), ("HIGH_B", F(1, 2)))]
        for tag, value, offset in points:
            t, o = key(value, other)
            c_t = F(27, 19)*t/100
            c_o = c_t*F(11, 10)*o/100
            job = dict(protocol["cases"][BASELINE], case=f"THRESH_{axis}_{tag}", tags=["THRESHOLD"],
                       alpha_T_multiplier=str(t), alpha_O_multiplier=str(o),
                       budget_offset=str(offset), budget=str(F(protocol["budget_base"])+offset),
                       costs=["1", str(c_t), str(c_o)], threshold_axis=axis, threshold_position=position)
            jobs.append(job)
    return edges, jobs


def main():
    protocol = load()
    costs = {}
    for n, case in protocol["cases"].items():
        if "COST" in case["tags"]:
            r = json.loads((RESULTS/f"{n}.json").read_text(encoding="utf-8"))
            assert r["status"] == "EXACT_FINITE"
            costs[case["alpha_T_multiplier"], case["alpha_O_multiplier"]] = r
    assert len(costs) == 25
    edges, jobs = contingent_jobs(protocol, costs)
    path = HERE/"contingent_threshold_jobs.json"
    planned = dict(parent_grid_sha256=FROZEN.digest(HERE/"frozen_policy_grid.json"), edges=edges, jobs=jobs,
                   decision="CERTIFIED_ADJACENT_ACTIVITY_SWITCH" if edges else "NO_PREREGISTERED_TRIGGER")
    if path.is_file():
        assert json.loads(path.read_text(encoding="utf-8")) == planned
    else:
        with path.open("x", encoding="utf-8") as f:
            json.dump(planned, f, indent=2)
            f.write("\n")
    print(planned["decision"], len(jobs), "additional exact cells", flush=True)
    if jobs:
        run_jobs([(c, None) for c in jobs], workers=4)


if __name__ == "__main__":
    main()
