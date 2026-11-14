import csv
import json
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "artifacts/v3_phase32d4_20261112_191057"


def read(name):
    return json.loads((OUT/name).read_text(encoding="utf-8"))


def test_closed_outer_runs_and_full_domain_replay():
    certs = {r["label"]:r for r in read("final_policy_independent_certificate.json")}
    for g,raw,rhs in ((1,415,355),(2,71830,51070),(3,2657350,1564150)):
        r=read(f"outer/G{g}/result.json")
        first,last=r["iterations"]
        assert first["added_scenario"] not in first["master_scenarios"]
        assert first["upper"]>=last["upper"] and first["lower"]<=last["lower"]
        assert last["upper"]==last["lower"]==r["objective"]==11775
        o=r["final_oracle"]
        assert o["exact"] and o["frontier_size"]==0
        assert (o["raw_count"],o["rhs_count"])==(raw,rhs)
        if g>1:
            c=certs[f"G{g}"]
            assert c["exact"] and c["raw_count"]==raw and c["full_matrix_branch_replays"]==414


def test_direct_matrix_and_independent_objective():
    de=read("gamma1_de/model_identity.json")
    reference=read("gamma1_enum/summary.json")
    bounds=read("gamma1_de/bound_certificate.json")
    assert (de["blocks"],de["cols"],de["rows"])==(355,26912554,8172101)
    assert de["matrix_pilot"]["coefficient_differences"]==0
    assert len(reference["services"])==355
    assert len(reference["worst_rhs"])==4
    assert bounds["lower"]==bounds["upper"]==min(reference["services"].values())==11775


def test_joint_policy_set_has_budget_tradeoff_and_zero_witness():
    r=read("policy_flatness_certificate.json")
    assert r["axis_min"]==[0,0,0] and r["axis_max"]==[915,644,585]
    assert r["budget_integer_form"]=={"c":[190,270,297],"rhs":173880}
    assert sum(x*c for x,c in zip(r["axis_max"],r["budget_integer_form"]["c"]))>173880
    assert r["feasible_integer_policies"]==57884083 and r["zero_policy_certified"]
    with (OUT/"gamma_policy_set_audit.csv").open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==6 and all(row["robust_service"]=="11775" for row in rows)


def test_matched_methods_share_exact_domain_and_value():
    rows=[read(f"finite/{m}/result.json") for m in ("Direct","Plain","BTB","Implicit")]
    assert all(r["rhs_ids"]==rows[0]["rhs_ids"] and r["budget"]==rows[0]["budget"] for r in rows)
    assert all(r["objective"]==12300 and r["rhs_count"]==32 for r in rows)
