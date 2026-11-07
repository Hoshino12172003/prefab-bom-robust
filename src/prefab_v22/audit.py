from copy import deepcopy
from math import isfinite
from prefab_v21.audit import audit as original_audit


def mapped_data(d, plan):
    """Numerical ledger replay, independently implemented from the symbolic StateView."""
    base = deepcopy(d.base)
    for product in d.M:
        quantity = plan["p"][product,]
        base.lots.append({"id": f"v22_WIP_{product}", "kind": "Wa", "index": (product,), "amount": quantity})
        for j in d.J:
            used = d.base.p["A1"][j, product] * quantity
            # Signed ledger adjustments are internal replay entries, never input supply.
            base.lots.append({"id": f"v22_used_{j}_{product}", "kind": "I",
                              "index": (j, "a"), "amount": -used})
    return base


def stage1_audit(d, plan):
    rows = {}
    quantities = plan["p"]
    if set(quantities) != {(m,) for m in d.M} or any(not isfinite(p) for p in quantities.values()):
        return {"pre_domain": float("inf")}
    rows["pre_nonnegative"] = max([0, *(-p for p in quantities.values())])
    rows["pre_order"] = max([0, *(quantities[m,] - max(0, d.val("D",m)-d.stock("Wa",m)) for m in d.M)])
    rows["pre_capacity"] = max(0, sum(d.tau_pre[m,]*quantities[m,] for m in d.M)-d.P_pre)
    rows["pre_space"] = max(0, sum(d.v_WIP[m,]*(d.stock("Wa",m)+quantities[m,]) for m in d.M)-d.Wcap_pre)
    rows["pre_material"] = max([0, *(sum(d.val("A1",j,m)*quantities[m,] for m in d.M)
                                               -d.stock("I",j,"a")-plan["x"][j,"a"] for j in d.J)])
    return rows


def audit(d, plan, risk, flows, mode):
    rows = original_audit(mapped_data(d, plan), plan, risk, flows, mode)
    rows.update(stage1_audit(d, plan))
    return rows


def costs(d, plan, flows):
    original = sum(d.p["cI"][idx]*q for idx,q in plan["x"].items()) + sum(
        d.val("f",k)*plan["y"][k,] + d.val("cR",k)*plan["r"][k,] for k in d.K)
    preassembly = sum((d.c_preasm[m,]+d.h_preWIP[m,])*plan["p"][m,] for m in d.M)
    cash = sum(d.costs[group][idx[:-1]]*q for group in ("q","g","z","move","a","b","h","e")
               for idx,q in flows[group].items())
    holding = sum(d.costs[group][idx[:-1]]*q for group in ("R","S","I","Wa","Wo","F")
                  for idx,q in flows[group].items())
    return {"original_pre": original, "preassembly": preassembly, "cash": cash,
            "holding": holding, "objective": original + preassembly + cash + holding}


def initial_states(d, plan):
    return {
        "Ipre": {(j,"a"): d.stock("I",j,"a") + plan["x"][j,"a"]
                 - sum(d.val("A1",j,m)*plan["p"][m,] for m in d.M) for j in d.J},
        "W0post": {(m,): d.stock("Wa",m) + plan["p"][m,] for m in d.M},
    }
