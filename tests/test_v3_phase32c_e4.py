import csv
import json
from pathlib import Path

import pytest

from prefab_v3 import e4_ccg as e4
from prefab_v3.plain_ccg import MasterSolution


OUT = Path(__file__).resolve().parents[1]/"artifacts/v3_phase32c_20261112_093602"


def rows(name):
    with (OUT/f"{name}.csv").open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def profiles():
    return {"pilot": ({},{}),
            "engine": ({},{(*e4.SEAT,64):0.5,(*e4.ENGINE,64):0.5}),
            "gear": ({},{(*e4.SEAT,64):0.5,(*e4.GEAR,64):0.5})}


class Bound:
    def __init__(self, upper):
        self.q = upper

    def upper(self, profile, x):
        return self.q,self.q,self.q


def exercise(upper, meet, exact=(6,7)):
    called = []
    def solve(name, profile, x):
        called.append(name)
        return (meet if name.startswith("meet__") else dict(pilot=6,engine=exact[0],gear=exact[1])[name]),{}
    return e4.separate(profiles(),Bound(upper),(1,0,0),solve),called


def test_strict_witness_pruning_counts_common_milp():
    r,called = exercise(9,7)
    assert (r.worst,r.ties,r.individual_solves,r.common_solves)==(6,("pilot",),1,1)
    assert called==["pilot","meet__engine__gear"]
    assert [x["decision"] for x in r.rows]==["INDIVIDUAL_MILP","PRUNED_STRICT","PRUNED_STRICT"]


def test_equal_incumbent_without_tight_upper_keeps_potential_tie():
    r,called = exercise(9,6)
    assert r.ties==("engine","pilot")
    assert called[-2:]==["engine","gear"]
    assert r.individual_solves==3 and r.common_solves==1


def test_tight_bounds_may_lower_incumbent_and_preserve_all_ties():
    p = profiles()
    class Prefix:
        def upper(self, profile, x):
            q = 5 if profile[1] else 6
            return q,q,q
    r = e4.separate(p,Prefix(),(1,0,0),lambda n,*_: (5 if n.startswith("meet__") else 6,{}))
    assert (r.worst,r.ties)==(5,("engine","gear"))
    assert [x["decision"] for x in r.rows][-2:]==["BOUND_EXACT","BOUND_EXACT"]
    assert [x["incumbent"] for x in r.rows][-2:]==[6,5]


def test_rejects_invalid_bound_and_requires_equal_receipts():
    with pytest.raises(e4.InvalidBound):
        exercise(7,8)
    p = profiles()
    p["gear"][0]["unexpected"] = 1
    assert not e4.seat_pairs(p)
    with pytest.raises(AssertionError):
        e4.intersection(p["engine"],p["gear"])


def test_full_verification_after_bound_closure():
    p = profiles()
    calls = []
    def verify(n,x,tag):
        calls.append((n,x,tag))
        return {"pilot":6,"engine":7,"gear":7}[n]
    def oracle(*_):
        return exercise(9,7)[0]
    x = (1,0,0)
    result = e4.generate(p,("pilot",),lambda *_:MasterSolution(6,x,{}),oracle,verify)
    assert result.objective==6
    assert calls==[(n,x,"verify") for n in p]


def test_source_bounds_and_independent_pruning_replay():
    probes = rows("e4_bound_validation")
    assert len(probes)==74 and all(int(r["lower"])<=int(r["exact"])<=int(r["upper"]) for r in probes)
    certificate = rows("e4_pruning_certificate")
    assert certificate and all(r["independent_matrix_replay"]=="True" for r in certificate)
    for r in certificate:
        lo, q, up = (int(r[k]) for k in ("lower","independent_full_value","upper"))
        assert lo<=q<=up
        if r["condition"]=="L>INCUMBENT":
            assert lo>int(r["incumbent"])
        else:
            assert lo==up


def test_matched_rounds_and_repeatability():
    checks = rows("e4_iteration_crosscheck")
    assert all(r["match"]=="True" for r in checks)
    assert {r["case"] for r in checks} >= {"4","8","16","24","32","38","region_CT","region_CTO"}
    for r in rows("e4_repeatability"):
        assert int(r["completed"])==3
        if r["method"] in ("E4","PLAIN"):
            assert r["objective_consistent"]=="True" and int(r["exact"])==3
        if r["method"]=="E4":
            assert r["pruning_consistent"]=="True"
    audit = json.loads((OUT/"e4_exactness_certificate.json").read_text())
    assert audit["bound_violation_count"]==audit["false_pruning_count"]==audit["oracle_mismatches"]==0


def test_policy_regions_and_final_exhaustive_scope():
    region = rows("e4_policy_region_validation")
    assert {r["region"] for r in region}=={"C_ONLY","C_T","C_T_O"}
    assert all(r["e4"]==r["plain"] for r in region)
    cto = next(r for r in region if r["region"]=="C_T_O" and r["style"]=="single")
    assert json.loads(cto["frozen_policy"])==[713,135,6] and cto["e4"]=="27286"
    summary = rows("e4_vs_plain_vs_direct")
    assert len(summary)==58
    for r in summary:
        if r["status"]=="EXACT_FINITE":
            assert int(r["final_exhaustive_solves"])==int(r["scenario_count"])
