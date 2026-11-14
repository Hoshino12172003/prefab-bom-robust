"""Check independent audit output coverage, evidence status, and solver gates."""

import csv
import json
from collections import Counter

from v3_audit_context import OUT, ROOT, digest, dump, git, verify_inputs, write


def rows(name):
    with (OUT / name).open(encoding="utf-8-sig",newline="") as stream:
        yield from csv.DictReader(stream)


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def keys(data):
    return {(r["node_id"],r["item_id"]) for r in data}


def main():
    for n in ("seat","inventory"):
        assert int((OUT / f"v3_{n}_run.exit").read_text(encoding="utf-8-sig"))==0
    initial = read("v3_input_provenance.json")
    current = verify_inputs()
    assert all(current[k]==v for k,v in initial.items() if k!="workspace_status")
    assert set(current["workspace_status"])-set(initial["workspace_status"]) <= {
        "?? docs/v3_full_bom_four_audits.md"}
    census = Counter()
    candidates, base, extended, item_nodes = set(), set(), set(), set()
    for r in rows("v3_buffer_eligibility.csv"):
        item_node=r["node_id"],r["item_id"]
        assert item_node not in item_nodes
        item_nodes.add(item_node)
        census[r["buffer_eligibility"]]+=1
        if r["extended_eligibility"] in ("ELIGIBLE","CONDITIONAL"):
            candidates.add(item_node)
        if r["E_base_certified"]=="True":
            base.add(item_node)
            assert r["storage_capacity_evidence"]=="DIRECT" and r["storage_capacity"]=="99999"
        if r["E_extended_conditional"]=="True":
            extended.add(item_node)
    assert len(item_nodes)==28049*12 and len(candidates)==91 and len(base)==82 and len(extended)==9
    assert len(keys(rows("v3_E_base.csv")))==87 and keys(rows("v3_E_extended.csv"))==candidates
    assert len({r["item_id"] for r in rows("v3_buffer_eligibility.csv")})==28049
    economics=list(rows("v3_buffer_economic_feasibility.csv"))
    prep=list(rows("v3_preparation_reachability.csv"))
    portfolio_keys={(r["node"],r["material_state"]) for r in rows("v3_buffer_portfolio.csv")}
    assert keys(economics)==keys(prep)==portfolio_keys==candidates
    for r in economics:
        for p in ("c_np","h_np","c_prod","c_trans","prep_capacity","trans_capacity","K_np_physical_verified"):
            assert r[p]=="" and r[p+"_basis" if p!="K_np_physical_verified" else "K_np_physical_basis"]=="MISSING"
    assert all(r["additional_prep"]=="NOT_CERTIFIED" and not r["physical_maximum"] for r in prep)
    types = Counter(r["operation_type"] for r in rows("v3_state_transition_graph.csv"))
    assert sum(types.values())==115096 and types["ASSEMBLY"]==87003 and types["CUSTOMER_OUTFLOW"]==28000
    solver=read("v3_seat_oem_preposition_detail.json")
    result=solver["results"]
    assert solver["full_domain_runs"]==0 and solver["policy"]==[915,0,0]
    assert [r["case"] for r in result]==["C0","C1","C2","C3","C4","C4_MIN_PLUS_ONE"]
    assert [(r["on_time"],r["required_preposition"]) for r in result]==[(11775,0)]*4+[(17250,5475),(11776,1)]
    stages=[s for r in result for s in r["stages"]]
    assert all(s["status"]=="OPTIMAL" and s["objective"]==s["bound"] and s["gap"]==s["matrix_residual"]==0 for s in stages)
    assert all("Optimal solution found" in (ROOT/r["log"]).read_text(encoding="utf-8") for r in result)
    assert len(list(rows("v3_seat_oem_preposition_counterfactual.csv")))==6
    report=ROOT/"docs/v3_full_bom_four_audits.md"
    assert report.is_file()
    assert not git("diff","--check")
    dump("v3_full_bom_audit.json",dict(status="PASS_WITH_CONDITIONS",formal_reconstruction_authorized=False,
        evidence_boundary="fixed D4 RHS only; source storage eligibility separate from physical preparation",
        input_identity="v3_input_provenance.json", audits=dict(eligibility_rows=len(item_nodes),eligibility=census,
        graph_rows=sum(types.values()),operation_types=types,economic_candidates=len(economics),
        preparation_candidates=len(prep),certified_positive_increment=0),
        fixed_scenario_optimal_stages=len(stages),max_matrix_residual=max(s["matrix_residual"] for s in stages),
        max_solver_residual=max(s["solver_residual"] for s in stages),
        missing=["physical SKU and shared storage","pre-reveal spare production and transport calendar",
                 "uncommitted source material and intermediate headroom","economic costs and delivery value"],
        checks="all CSV joins, row counts, scenario results and source hashes verified",
        workspace_status_after_audit=current["workspace_status"]))
    manifest=OUT/"v3_sha256_manifest.csv"
    files=[p for p in OUT.rglob("*") if p.is_file() and p!=manifest]
    files.append(report)
    write(manifest.name,(dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in sorted(files)))
    print("PASS_WITH_CONDITIONS",len(item_nodes),sum(types.values()),len(stages),len(files),flush=True)


if __name__=="__main__":
    main()
