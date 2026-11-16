import importlib
from collections import defaultdict
from pathlib import Path


def test_threshold_witness_and_cache_require_the_same_physical_state(monkeypatch):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root/"experiments/v33_gate4_enhanced"))
    solver=importlib.import_module("solver")
    candidate=dict(opening={("n","p"):1},bounds={("n","p",61):(0,2)},seat=[],pool=1,
                   ot=9,tau=12,cost_ticks=20,prep_cost_ticks=8)
    assert solver.meets((9,11,12),(9,12,12))
    assert not solver.meets((8,11,12),(9,12,12))
    assert not solver.meets((9,13,12),(9,12,12))
    assert not solver.meets((9,11,13),(9,12,12))
    cache=defaultdict(list)
    cache[solver.physical_state(candidate),"cached"].append((9,11,12))
    checks=[]

    def check(*args):
        checks.append(args[3])
        return None

    monkeypatch.setattr(solver,"feasibility",check)
    allowed={"active":{},"cached":{},"violation":{}}
    priority=defaultdict(int)
    evidence=defaultdict(list)
    args=(allowed,{"active":{}},cache,priority,"case",evidence)
    assert solver.bound_separation(None,None,candidate,*args)=="violation"
    assert checks==["violation"] and len(evidence["bound_skips"])==2
    candidate["pool"]=2
    priority.clear()
    assert solver.bound_separation(None,None,candidate,*args)=="cached"
    assert checks==["violation","cached"]
