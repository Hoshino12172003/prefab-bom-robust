from copy import deepcopy
from .data import Data
from prefab_v21.examples import micro


def extend(base, capacity=None, cost=0.2):
    n = sum(base.p["D"].values())
    return Data(base=deepcopy(base), tau_pre={(m,):1 for m in base.M},
                P_pre=n if capacity is None else capacity, Wcap_pre=n+sum(base.stock("Wa",m) for m in base.M),
                v_WIP={(m,):1 for m in base.M}, c_preasm={(m,):cost for m in base.M},
                h_preWIP={(m,):0.05 for m in base.M})


def no_value():
    return extend(micro(), cost=10)


def time_bottleneck():
    base = micro()
    base.p["P1"] = {key:0 for key in base.p["P1"]}
    base.p["PO"] = {key:0 for key in base.p["PO"]}
    return extend(base)


def flexibility():
    """Two product configurations share a single pre-risk A, with pipeline A arriving at t=1."""
    base = micro(three=True)
    # LV has no remaining order in this synthetic two-active-configuration example.
    base.p["D"]["LV",] = 0
    base.lots = [{"id":"common_A","kind":"I","index":("A","a"),"amount":1},
                 {"id":"post_risk_A","kind":"P2","index":("A","a",1),"amount":1}]
    base.p["P1"] = {key:0 for key in base.p["P1"]}
    base.p["P1"][1,] = 1
    base.p["PO"] = {key:0 for key in base.p["PO"]}
    # HV has no post-risk stage-1 route, whereas MV does. Both require the same A.
    base.p["tau1"]["HV",] = 2
    base.p["tau1"]["MV",] = 1
    base.p["tau1"]["LV",] = 1
    base.p["X"] = {key:0 for key in base.p["X"]}
    base.p["X"]["B","a"] = 2
    return extend(base, capacity=1, cost=0.2)
