"""Full integer witnesses and frozen BTB re-audit on catalogued profiles."""

import json
import os
from collections import Counter
from fractions import Fraction as F
from time import perf_counter

import gurobipy as gp
import numpy as np
from gurobipy import GRB

import catalog as cat
from audit_historical_reduction import nonbattery_certificate, service_bound
from design import overlap_scenarios
from prefab_v3 import e4_ccg as e4, plain_ccg as plain
from prefab_v3.robust import RESOURCE_IDS, UncertaintySet


HERE, ROOT, SOURCE = cat.HERE, cat.ROOT, cat.frozen
PHASE32P = cat.ARTIFACTS / "v3_phase32p_20261111_224834"


def archived_policy(name):
    evidence = json.loads((PHASE32P / "runs" / f"{name}.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "EXACT_FINITE"
    return tuple(evidence["policy"])


def representative_events():
    def event(r, t, d, s=F(1, 2)):
        return cat.Event(r, next(e for e in cat.EPISODES if (e.start, e.duration, e.severity) == (t, d, s)))

    anchors = next(s.events for s in overlap_scenarios() if s.name == "BGS_OVERLAP")
    b, g, s = tuple(event(e.resource, e.start, min(cat.DURATIONS), e.severity) for e in anchors)
    # Use a production event here because the 7-day receipt choice at 61
    # has the same RHS as the 4-day receipt anchor at 66.
    b7 = event("B_PROD", 61, 7)
    g7 = event("GEAR", 61, 7)
    s7 = event("SEAT", 68, 7)
    s11 = event("SEAT", 64, 11, F(1, 4))
    s_late = event("SEAT", 68, 4, F(1, 4))
    return dict(NR=(), B=(b,), G=(g,), S=(s,), BG=(b, g), BS=(b, s), GS=(g, s),
                BGS=(b, g, s), E=(event("ENGINE", 61, 4),), B7=(b7,), G7=(g7,), S7=(s7,),
                S11=(s11,), BGS7=(b7, g7, s7), S_LATE=(s_late,), BS_LATE=(b, s_late),
                BS11=(b, s11))


def catalog_inputs(scenarios):
    metadata = json.loads((cat.CATALOG / "rhs_coordinates.json").read_text(encoding="utf-8"))
    groups = metadata["groups"]
    with np.load(cat.CATALOG / "classes.npz") as payload:
        ids = payload["ids"]
        multiplicities = payload["exact_event_count_multiplicity"]
    rows = {}
    for name, events in scenarios.items():
        exposure = cat.BUDGET.validate(events, max(1, len(events)))
        code, expected = 0, Counter()
        for e in events:
            r, episode = e.resource, e.episode
            group = groups[r]
            value = next(o["local_id"] for o in group["options"]
                         if (o["start"], o["duration"], o["severity"]) ==
                         (episode.start, episode.duration, str(episode.severity)))
            code |= value << (cat.BITS*cat.RESOURCES.index(r))
            expected.update((a, b) for a, b in zip(group["values"][0], group["values"][value], strict=True) if a != b)
        i = np.searchsorted(ids, np.uint64(code))
        assert int(ids[i]) == code and multiplicities[len(events), i] > 0
        rows[name] = dict(scenario=name, rhs_id=code, event_count=len(events), exposure=exposure,
                          family=cat.family(e.resource for e in events), rhs_changed_rows=sum(expected.values()),
                          events=[(e.resource, e.episode.start, e.episode.duration, str(e.episode.severity), e.recovery)
                                  for e in events])
    return rows


def rhs_delta(name, scenarios, rows):
    metadata = json.loads((cat.CATALOG / "rhs_coordinates.json").read_text(encoding="utf-8"))
    expected = Counter()
    for r in (e.resource for e in scenarios[name]):
        group = metadata["groups"][r]
        code = rows[name]["rhs_id"] >> (cat.BITS*cat.RESOURCES.index(r)) & ((1 << cat.BITS)-1)
        expected.update((a, b) for a, b in zip(group["values"][0], group["values"][code], strict=True) if a != b)
    return expected


def optimize(model, expr, tag):
    path = HERE / "logs" / f"{tag}.log"
    path.parent.mkdir(exist_ok=True)
    path.write_text("", encoding="utf-8")
    model.Params.LogFile = os.path.relpath(path, ROOT)
    model.setObjective(expr, GRB.MAXIMIZE)
    model.optimize()
    if model.Status != GRB.OPTIMAL or model.MIPGap != 0 or model.ObjVal != model.ObjBound:
        raise RuntimeError(f"{tag}: missing exact optimum, status={model.Status}, log={path}")
    vector, residual = SOURCE.exact_vector(model, SOURCE.matrix_rows(model))
    q = int(model.ObjVal)
    assert q == model.ObjVal
    record = dict(tag=tag, status="OPTIMAL", Q=q, bound=model.ObjBound, gap=model.MIPGap,
                  integer_variables=model.NumIntVars, constraints=model.NumConstrs, matrix_residual=0,
                  solver_residual=residual, solver_seconds=model.Runtime,
                  log=path.relative_to(HERE).as_posix())
    return q, vector, record


def prefix_dp(env, base, x, components, values, profiles):
    """Evaluate the existing isolated due-prefix DP for the chosen joint witness."""
    groups = base.network.groups
    periods = base.network.periods
    daily = Counter()
    for g in groups:
        daily[g.representative.due] += len(g.orders)
    per_branch, records = {}, []
    for name in components:
        per_branch[name] = {}
        with gp.Model(env=env) as model:
            SOURCE.configure(model, seconds=180)
            block = plain.add_recourse_block(model, base, "recourse", profiles[name], x)
            expr = gp.LinExpr()
            for d in periods:
                expr += gp.quicksum(block.outflow[g.id, t] for g in groups if g.representative.due == d
                                    for t in periods if t <= d)
                q, _, record = optimize(model, expr, f"prefix_{name}_{d}")
                per_branch[name][d] = q
                records.append(record)
            assert per_branch[name][periods[-1]] == values[name]
    value, rows = 0, []
    for d in periods:
        isolated = {n: per_branch[n][d] for n in components}
        value = min(min(isolated.values()), value+daily[d])
        rows.append(dict(due_period=d, due_demand=daily[d], isolated_prefix_json=json.dumps(isolated), scalar_DP=value))
    cat.write(HERE / "scalar_due_prefix_dp.csv", rows)
    return value, records


def main():
    started = perf_counter()
    SOURCE.init()
    base, opening = SOURCE.BASE, SOURCE.OPENING
    scenarios = representative_events()
    rows = catalog_inputs(scenarios)
    profiles = {n: cat.profile(n, es) for n, es in scenarios.items()}
    assert len({r["rhs_id"] for r in rows.values()}) == len(rows)
    cat.dump(HERE / "representative_scenarios.json", rows)
    policies = {"C": archived_policy("BASE_B100"), "CT": archived_policy("BASE_B150"),
                "CTO": archived_policy("R3_S75_D7_ABRUPT_B100")}
    assert list(policies.values()) == [(915, 0, 0), (1338, 24, 0), (713, 135, 6)]
    joint = dict(BG=("B", "G"), BS=("B", "S"), GS=("G", "S"), BGS=("B", "G", "S"),
                 BGS7=("B7", "G7", "S7"), BS_LATE=("B", "S_LATE"), BS11=("B", "S11"))
    reference_resources = dict(zip(cat.RESOURCES[:3], RESOURCE_IDS, strict=True))
    reduction = nonbattery_certificate(base)
    # Use only the battery projection for the old recursion diagnostic.
    battery_u = UncertaintySet(cat.BUDGET.periods, cat.DURATIONS, cat.SEVERITIES,
                              max(cat.DURATIONS), cat.CONCURRENCY)
    prefix = e4.Prefix(base)
    pairs = e4.seat_pairs(profiles)
    assert not pairs
    calls, btb, decisions, comparisons, outcomes = [], [], [], [], {}
    witnesses = HERE / "witnesses"
    witnesses.mkdir(exist_ok=True)
    with SOURCE.env() as env:
        for policy, x in policies.items():
            with gp.Model(env=env) as nominal:
                plain.add_recourse_block(nominal, base, "recourse", profiles["NR"], x)
                nominal.update()
                matrix, rhs, senses = SOURCE.matrix_rows(nominal)
                lb, ub = nominal.getAttr("LB"), nominal.getAttr("UB")
                variable_names = nominal.getAttr("VarName")
            policy_calls = {}

            def solve(name, profile, fixed_x):
                assert fixed_x == x and name in scenarios
                with gp.Model(env=env) as model:
                    SOURCE.configure(model, seconds=180)
                    block = plain.add_recourse_block(model, base, "recourse", profile, x)
                    model.update()
                    a, h, s = SOURCE.matrix_rows(model)
                    assert (matrix != a).nnz == 0 and np.array_equal(senses, s)
                    assert model.getAttr("LB") == lb and model.getAttr("UB") == ub
                    assert model.getAttr("VarName") == variable_names
                    assert model.NumVars == model.NumIntVars == 75810
                    delta = Counter(zip(rhs[rhs != h], h[rhs != h]))
                    assert delta == rhs_delta(name, scenarios, rows)
                    q, vector, record = optimize(model, plain.on_time(block, base), f"{policy}_{name}")
                    reconstructed = sum(int(vector[block.outflow[g.id, t].index]) for g in base.network.groups
                                        for t in base.network.periods if t <= g.representative.due)
                    assert q == reconstructed
                    witness = witnesses / f"{policy}_{name}.npz"
                    np.savez_compressed(witness, solution=vector.astype(np.int64))
                    record.update(policy=policy, scenario=name, x_C=x[0], x_T=x[1], x_O=x[2],
                                  rhs_id=rows[name]["rhs_id"], changed_rhs_rows=sum(delta.values()),
                                  witness=witness.relative_to(HERE).as_posix(), witness_sha256=cat.digest(witness))
                    policy_calls[name] = record
                    print(policy, name, q, flush=True)
                    return q, record

            t0 = perf_counter()
            result = e4.separate(profiles, prefix, x, solve)
            answers = {name: r["Q"] for name, r in policy_calls.items()}
            assert set(answers) == set(profiles)
            assert result.worst == min(answers.values()) and result.ties == tuple(sorted(
                name for name, q in answers.items() if q == result.worst))
            calls.extend(policy_calls.values())
            outcomes[policy] = answers
            counts = Counter(r["decision"] for r in result.rows)
            btb.append(dict(policy=policy, x_C=x[0], x_T=x[1], x_O=x[2], candidates=len(profiles),
                            eligible_seat_pairs=0, pruned=counts["PRUNED_STRICT"], bound_exact=counts["BOUND_EXACT"],
                            individual_MILP=result.individual_solves, common_MILP=result.common_solves,
                            worst_subset_Q=result.worst, worst_subset_ties="|".join(result.ties),
                            bound_seconds=result.bound_seconds, wall_seconds=perf_counter()-t0))
            decisions.extend(dict(policy=policy, **{k: v for k, v in row.items() if k != "evidence"})
                             for row in result.rows)
            for name, parts in joint.items():
                isolated = {p: answers[p] for p in parts}
                eb = {reference_resources[e.resource]: e.episode for e in scenarios[name] if e.resource in reference_resources}
                battery = service_bound(base, battery_u, opening, tuple(eb.get(r) for r in RESOURCE_IDS), x)
                battery_component = next((p for p in parts if p.startswith("B")), "NR")
                assert battery == answers[battery_component]
                comparisons.append(dict(policy=policy, scenario=name, isolated_json=json.dumps(isolated),
                                        nominal=answers["NR"], integer_Q=answers[name], branch_min=min(isolated.values()),
                                        additive=answers["NR"]-sum(answers["NR"]-q for q in isolated.values()),
                                        battery_only_recursion=battery))

        witness = next((r for r in comparisons if len({r["integer_Q"]} &
                       {r["branch_min"], r["additive"], r["battery_only_recursion"]}) == 0), None)
        prefix_records = []
        if witness:
            n, p = witness["scenario"], witness["policy"]
            scalar, prefix_records = prefix_dp(env, base, policies[p], joint[n], outcomes[p], profiles)
            witness = dict(witness, scalar_due_prefix_dp=scalar)
            assert scalar == witness["branch_min"] and scalar != witness["integer_Q"]
    cat.write(HERE / "fixed_policy_full_milp.csv", calls)
    cat.write(HERE / "multibom_btb_reaudit.csv", btb)
    cat.write(HERE / "btb_scenario_decisions.csv", decisions)
    cat.write(HERE / "nonseparability_comparisons.csv", comparisons)
    if prefix_records:
        cat.write(HERE / "prefix_solver_calls.csv", prefix_records)
    cat.dump(HERE / "validation_run.json", dict(policies=policies, policy_outcomes=outcomes, btb=btb,
             witness=witness, nominal_nonbattery_certificate=reduction, full_integer_calls=len(calls),
             prefix_integer_calls=len(prefix_records), max_solver_residual=max(r["solver_residual"] for r in calls+prefix_records),
             gurobi=gp.gurobi.version(), seconds=perf_counter()-started))
    print("witness", witness, flush=True)


if __name__ == "__main__":
    main()
