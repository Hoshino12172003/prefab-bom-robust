"""Join original calls to PRE-oracle snapshots; labels never enter the extractor."""
import json
from collections import Counter

from .manifest import PHASE_A, PHASE_B, MODEL_INSTANCE_ID, digest, check_hash, identity
from .schema import MasterStateV3, BUDGET, COSTS
from .source import read_csv


def historical_records(network, scenarios):
    snapshots, calls, labels, samples, contexts, sources = [], [], [], [], [], {}
    pair_values = {}
    for phase, expected_files in ((PHASE_A, 9), (PHASE_B, 16)):
        directory = network.root / phase
        manifest = {r["path"]: r["sha256"] for r in read_csv(directory / "sha256_manifest.csv")}
        files = sorted(directory.glob("n*.json"))
        if len(files) != expected_files:
            raise ValueError("Historical source file count conflict")
        for path in files:
            rel = path.relative_to(network.root).as_posix()
            check_hash(path, manifest[rel])
            sha = digest(path)
            sources[rel] = sha
            data = json.loads(path.read_text(encoding="utf-8"))
            run_id = identity("run-", [rel, sha])
            field = "oracle" if phase == PHASE_A else "records"
            candidates = data.get("benchmark", data.get("names"))
            if len(candidates) != len(set(candidates)) or not set(candidates) <= scenarios.keys():
                raise ValueError("Candidate set conflict")
            indexed = list(enumerate(data[field]))
            previous_lb, previous_ub = None, 28000
            for offset, it in enumerate(data["iterations"]):
                k = it["iteration"]
                if k != offset+1 or it["upper"] > previous_ub:
                    raise ValueError("Iteration/upper monotonicity conflict")
                selected = it["master_scenarios"]
                if not set(selected) <= set(candidates):
                    raise ValueError("Master active scenario conflict")
                state = MasterStateV3(MODEL_INSTANCE_ID, k, tuple(it["policy"]),
                    tuple(scenarios[n].rhs_id for n in selected), it["upper"], previous_lb, run_id=run_id)
                group = [(i, v) for i, v in indexed if v.get("evaluation", v.get("tag")) == f"oracle_{k:02d}"]
                by_name = {v.get("scenario", v.get("name")): v for _, v in group}
                if len(group) != len(candidates) or set(by_name) != set(candidates):
                    raise ValueError("Incomplete or duplicate ranking group")
                q_by_name = {n: v.get("service", v.get("value")) for n, v in by_name.items()}
                if any(type(q) is not int or not 0 <= q <= 28000 for q in q_by_name.values()):
                    raise ValueError("Nonexact service label")
                worst = min(q_by_name.values())
                if it["lower"] != max(previous_lb if previous_lb is not None else -1, worst):
                    raise ValueError("Certified lower-bound history conflict")
                ranks = {q: i+1 for i, q in enumerate(sorted(set(q_by_name.values())))}
                snapshots.append(dict(master_state_id=state.state_id, run_id=run_id, iteration_id=k,
                    model_instance_id=MODEL_INSTANCE_ID, x_C=state.policy[0], x_T=state.policy[1], x_O=state.policy[2],
                    budget=str(BUDGET), costs_json=list(map(str, COSTS)), remaining_budget=str(BUDGET-state.spent),
                    ub_before_oracle=state.ub, lb_before_oracle=previous_lb, lb_initialized=previous_lb is not None,
                    active_scenarios_json=selected, active_rhs_ids_json=state.active_rhs_ids, candidate_scenarios_json=candidates,
                    source_file=rel, source_file_sha256=sha, json_pointer=f"/iterations/{offset}"))
                for sequence, (index, v) in enumerate(group):
                    name = v.get("scenario", v.get("name"))
                    scenario = scenarios[name]
                    q = q_by_name[name]
                    if tuple(v["policy"]) != state.policy or v["status"] not in (2, "OPTIMAL"):
                        raise ValueError("Call policy/status conflict")
                    if name in selected and q < state.ub:
                        raise ValueError("Active scenario violates exact Master")
                    if phase == PHASE_A and (v["solver_bound"] != q or v["solver_gap"] != 0 or v["exact_matrix_residual"] != 0):
                        raise ValueError("A exact certificate conflict")
                    if phase == PHASE_B and not 0 <= v["residual"] <= 1e-7:
                        raise ValueError("B matrix certificate conflict")
                    pointer = f"/{field}/{index}"
                    call_id = identity("oracle-", [sha, pointer, rel])
                    pair_id = identity("policy-rhs-", [MODEL_INSTANCE_ID, scenario.rhs_id, state.policy])
                    if pair_id in pair_values and pair_values[pair_id] != q:
                        raise ValueError("Conflicting repeated policy/RHS objective")
                    pair_values[pair_id] = q
                    common = dict(oracle_call_id=call_id, master_state_id=state.state_id,
                        effective_rhs_id=scenario.rhs_id, scenario_id=name, model_instance_id=MODEL_INSTANCE_ID,
                        run_id=run_id, iteration_id=k, policy_rhs_id=pair_id)
                    calls.append(dict(**common, phase="separation", query_sequence=sequence,
                        solver_status="OPTIMAL", best_bound=q, mip_gap=0, node_count=v["nodes"],
                        bound_gap_source="direct" if phase == PHASE_A else "derived_from_pinned_exact_assertion",
                        solver_runtime_s=v.get("solver_seconds", v.get("gurobi_seconds")),
                        wall_seconds=v.get("elapsed_seconds", v.get("job_wall_seconds")),
                        feasibility_status="integer_matrix_verified", log_path=phase+"/"+v["log"],
                        source_file=rel, source_file_sha256=sha, json_pointer=pointer))
                    labels.append(dict(oracle_call_id=call_id, oracle_objective=q, is_worst=q == worst,
                        dense_risk_rank=ranks[q], is_strict_violation=q < state.ub,
                        service_shortfall=28000-q,
                        disruption_loss=q_by_name["NR"]-q if "NR" in q_by_name else None,
                        label_source="exact_milp", objective_version="V3_on_time_count", label_unit="vehicle"))
                    samples.append(dict(**common, source_file_sha256=sha, json_pointer=pointer,
                        feature_information_time="after_master_before_oracle", independent_network=False))
                    contexts.append((call_id, scenario, state))
                previous_lb, previous_ub = it["lower"], it["upper"]
    counts = Counter(s["policy_rhs_id"] for s in samples)
    for sample in samples:
        sample["policy_rhs_repeat_count"] = counts[sample["policy_rhs_id"]]
    if (len(calls), len(snapshots), len(counts), sum(c[2].lb_before_oracle is None for c in contexts)) != (576, 33, 148, 322):
        raise ValueError("Historical audited cohort count conflict")
    return snapshots, calls, labels, samples, contexts, sources
