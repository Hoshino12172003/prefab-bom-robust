import csv
import json
from collections import Counter
from pathlib import Path


OUT = Path(__file__).resolve().parents[1]/"artifacts/v3_phase32d1_20261112_111159"


def rows(name):
    with (OUT/f"{name}.csv").open(encoding="utf-8-sig",newline="") as f:
        yield from csv.DictReader(f)


def test_exact_rhs_catalog_and_full_trajectory_multiplicity():
    catalog = list(rows("full_effective_rhs_catalog"))
    assert len(catalog)==38527
    assert len({r["canonical_signature"] for r in catalog})==38527
    assert len({r["integral_effective_signature"] for r in catalog})==38527
    assert any("441/2" in r["canonical_signature"] for r in catalog)
    observed = Counter()
    for i,r in enumerate(rows("trajectory_to_rhs_mapping"),1):
        assert int(r["trajectory_id"])==i
        assert 0<=int(r["exposure"])<=6
        observed[r["rhs_class_id"]] += 1
    assert sum(observed.values())==287443
    assert observed=={r["rhs_class_id"]:int(r["multiplicity"]) for r in catalog}


def test_entire_battery_catalog_ineligible_for_seat_pairing():
    r = list(rows("full_rhs_policy_summary"))
    assert [x["policy"] for x in r]==["P1","P2","P3","P4"]
    assert [json.loads(x["vector"]) for x in r]==[[915,0,0],[1338,24,0],[713,135,6],[1338,0,162]]
    assert all((int(x["exact"]),int(x["pruned"]),int(x["MILP_required"]))==(0,0,38527) for x in r)
    assert all(int(x["remaining_BTB_MILPs"])==38495 and x["BTB_full_set_certificate"]=="False" for x in r)
    counted = Counter()
    for a in rows("full_rhs_bound_classification"):
        counted[a["policy"]] += 1
        assert a["classification"]=="MILP_REQUIRED" and a["common_witness_eligible"]=="False"
        assert int(a["lower_before_individual"])==0<int(a["independent_reference_Q"])<=int(a["safe_upper"])
        assert a["reference_bound_violation"]=="False"
    assert counted==dict.fromkeys(("P1","P2","P3","P4"),38527)


def test_every_staged_step_rescreens_without_using_reference_scores():
    per = {p:[] for p in ("P1","P2","P3","P4")}
    for row in rows("full_rhs_incumbent_updates"):
        per[row["policy"]].append(row)
    for p, batch in per.items():
        assert [int(r["rank"]) for r in batch]==list(range(1,33))
        candidate = None
        for r in batch:
            assert int(r["solved_Q"])<=int(r["safe_upper"])
            candidate = min(candidate,int(r["solved_Q"])) if candidate is not None else int(r["solved_Q"])
            assert candidate==int(r["new_incumbent"])
            assert r["new_pruned"]=="0" and (OUT/r["log"]).is_file()


def test_independent_worst_values_ties_and_all_integer_matrices():
    answers = {"P1":(26652,4942),"P2":(27063,101),"P3":(26591,4942),"P4":(27201,101)}
    observed = Counter()
    sentinels = Counter()
    for row in rows("full_rhs_worst_case_certificate"):
        p = row["policy"]
        observed[p] += 1
        assert (int(row["W"]),int(row["tie_count"]))==answers[p]
        assert row["constructive_matrix_replay"]=="True" and row["integer_matrix_residual"]=="0"
        if row["direct_status"]=="OPTIMAL_MATRIX_REPLAY":
            sentinels[p] += 1
            assert int(row["direct_Q"])==answers[p][0] and (OUT/row["witness"]).is_file()
    assert observed=={p:count for p,(_,count) in answers.items()}
    assert sentinels==dict.fromkeys(answers,1)


def test_only_measured_calls_and_explicit_extrapolation():
    assert len(list(rows("full_rhs_solver_calls")))==132
    for row in rows("full_rhs_runtime_breakdown"):
        assert row["full_BTB_wall_time"]=="NOT_RUN"
        calls = int(row["measured_BTB_prefix_milps"])
        measured = float(row["measured_BTB_prefix_milp_wall_s"])
        reported = float(row["extrapolated_plain_serial_full_MILP_hours"])
        assert calls==32 and abs(reported-measured/calls*38527/3600)<1e-10
