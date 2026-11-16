"""Targeted baseline checks in fresh solver models; PR #9 remains read-only."""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v33_gate4a_plain_ccg"))
import baseline
from archive_evidence import safe_copy
from common import GRB, SETTINGS, TOL, bmax, exact, frozen_inputs, gp, solve_info, write_json


def quality(row):
    return row["solution_count"] and max(row[k] for k in
        ("model_row_violation", "model_bound_violation", "integrality_error")) <= TOL


def probe(model, objective, op, target, label):
    if op == "improve":
        row = model.addConstr(objective <= target-1)
    else:
        row = model.addConstr(objective <= target)
    model.setObjective(0)
    model.optimize()
    result = dict(probe=op, target=target, run=label, **solve_info(model))
    model.remove(row)
    return result


def solve_with_evidence(targets, certificates):
    def solve(model, objective, sense, label, level, rows, **fields):
        if (label, level) in targets:
            target = targets[label, level]
            assert sense == GRB.MINIMIZE
            result = probe(model, objective, "improve", target, label)
            certificates.append(dict(level=level, **result))
            if result["solver_status"] == "INFEASIBLE":
                # Retain a physical incumbent in the original matrix at the proposed cutoff.
                model.addConstr(objective <= target, name="CertifiedTarget")
                info = exact(model, objective, sense)
                row = dict(run=label, level=level, **fields, **info)
                rows.append(row)
                if quality(info) and abs(info["objective"]-target) <= TOL:
                    row["certificate"] = "STRICT_IMPROVEMENT_INFEASIBLE"
                    return target
                raise baseline.Incomplete(row)
            raise baseline.Incomplete(dict(run=label, level=level, **fields,
                solver_status=result["solver_status"], check="strict_improvement"))

        info = exact(model, objective, sense)
        row = dict(run=label, level=level, **fields, **info)
        rows.append(row)
        if info["exact"]:
            return round(info["objective"])
        if sense != GRB.MINIMIZE or info["solver_status"] != "OPTIMAL" or not quality(info) or "scenario" not in fields:
            raise baseline.Incomplete(row)

        expr = gp.LinExpr(objective)
        terms = [(expr.getCoeff(i), expr.getVar(i)) for i in range(expr.size())]
        if not float(expr.getConstant()).is_integer() or any(not float(c).is_integer() or v.VType != GRB.INTEGER for c,v in terms):
            raise baseline.Incomplete(row)
        rounded = {v.index: round(v.X) for v in model.getVars()}
        value = int(expr.getConstant()) + sum(int(c)*rounded[v.index] for c,v in terms)
        raw_bound = info["best_bound"]
        outward = math.nextafter(raw_bound, -math.inf)
        if math.ceil(outward) != value or abs(info["objective"]-value) > TOL:
            raise baseline.Incomplete(row)

        # The independently rounded incumbent must satisfy the original rows and bounds.
        assert all(v.VType == GRB.INTEGER and v.LB-TOL <= rounded[v.index] <= v.UB+TOL for v in model.getVars())
        max_violation = 0
        for c in model.getConstrs():
            lhs = model.getRow(c)
            error = math.fsum(lhs.getCoeff(i)*rounded[lhs.getVar(i).index] for i in range(lhs.size())) - c.RHS
            violation = abs(error) if c.Sense == "=" else max(0, error if c.Sense == "<" else -error)
            max_violation = max(max_violation, violation)
        assert max_violation <= TOL
        model.update()
        with model.copy() as verification:
            variables = verification.getVars()
            copied = gp.LinExpr([c for c,_ in terms], [variables[v.index] for _,v in terms]) + expr.getConstant()
            support = probe(verification, copied, "improve", value, label)
        certificates.append(dict(level=level, scenario=fields["scenario"], raw_gap=info["mip_gap"],
            bound_outward_1ulp=outward, lattice_bound=math.ceil(outward), rounded_incumbent=value,
            rounded_max_violation=max_violation, **support))
        if support["solver_status"] != "INFEASIBLE":
            raise baseline.Incomplete(row)
        row["certificate"] = "INTEGER_WITNESS_AND_STRICT_IMPROVEMENT_INFEASIBLE"
        return value
    return solve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "xlsb", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--case", required=True, choices=("G1_MID_DE", "G2_MID_DE", "G2_MAX"))
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True)
    op, nominal, protocol, scenarios, meta = frozen_inputs(args.xlsb,args.bundle)
    evidence, certificates = defaultdict(list), []
    case = args.case
    gamma = int(case[1])
    targets = {(case,"economics"):590764793776} if gamma == 1 else {(case,"backlog"):76351}
    baseline.solve_stage = solve_with_evidence(targets, certificates)

    def checkpoint():
        for k, rows in evidence.items():
            write_json(out, k+".json", rows)
        write_json(out, "strict_improvement.json", certificates)

    write_json(out, "config.json", dict(**meta, case=case, targets={level:v for (_,level),v in targets.items()}))
    with gp.Env(empty=True) as env:
        for k,v in SETTINGS.items():
            env.setParam(k,v)
        env.setParam("LogToConsole",0)
        env.setParam("LogFile",str(out/"raw.log"))
        env.start()
        try:
            budget = 11989002887 if case.endswith("_DE") else 23978005774
            if case.endswith("_DE"):
                row = baseline.master(env,op,nominal,scenarios[gamma],budget,case,out,evidence)
                replay = baseline.oracle(env,op,row,scenarios[gamma],case+"_replay",evidence["final_replay"],audit=True)
                assert replay["reason"] == "CERTIFIED"
            else:
                row,replay,_ = baseline.ccg(env,op,nominal,scenarios[gamma],budget,gamma,case,out,evidence,checkpoint)
            result = dict(status="PASS", **{k:row[k] for k in ("ot","tau","cost_ticks","max_residual")})
        except baseline.Incomplete as e:
            result = dict(status="BLOCKED", stop=e.row)
        finally:
            checkpoint()
    safe_copy(out/"raw.log",out/"gurobi.log")
    write_json(out,"result.json",result)
    print(case, json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
