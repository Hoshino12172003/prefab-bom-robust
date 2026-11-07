"""Numerical replay independent of the Gurobi constraint builder."""
from itertools import product
from math import isfinite


def audit(d,z,risk,v,mode):
    rows = {}
    for group,domain in d.domains().items():
        expected={(*idx,t) for idx in domain for t in d.periods}
        if set(v[group]) != expected:
            return {"illegal_flow_domain":float("inf")}

    def record(label, violation):
        rows[label] = max(rows.get(label,0),violation)

    def get(group,*idx):
        return v[group].get(idx,0)

    def lag(group,idx,time):
        lead = d.leads[group].get(idx)
        return get(group,*idx,time-lead) if lead is not None else 0

    for group,entries in v.items():
        for value in entries.values():
            record("nonnegative", max(0,-value) if isfinite(value) else float("inf"))
    investment = 0
    for idx,x in z["x"].items():
        record("stage1",max(-x,x-d.p["X"][idx]))
        investment += d.p["cI"][idx]*x
    for idx,r in z["r"].items():
        y=z["y"][idx]
        record("stage1",max(-r,r-d.p["Rmax"][idx]*y, min(abs(y),abs(y-1))))
        investment += d.p["f"][idx]*y+d.p["cR"][idx]*r
    record("stage1",investment-d.val("Bpre"))
    # Reconstruct balances using accumulated receipts and cumulative consumption,
    # rather than the production model's one-step recursion.
    balances = {group:{idx:d.stock(group,*idx)+(z["x"][idx] if group=="I" else 0)
                       for idx in d.domains()[group]} for group in ("R","S","I","Wa","Wo","F")}
    received = dict.fromkeys(d.M,0.0)
    for time in d.periods:
        for k,s in balances["R"]:
            balances["R"][k,s] += d.stock("P3",k,s,time)+lag("t",(k,s),time)+lag("g",(k,s),time)
        for s,j in balances["S"]:
            quantity = get("q",s,j,time)
            balances["S"][s,j] += quantity
            for k,ss in balances["R"]:
                if ss == s:
                    balances["R"][k,s] -= d.val("b",k,s,j)*quantity
        for s,j,l in d.SL:
            balances["S"][s,j] -= get("z",s,j,l,time)
            balances["I"][j,l] += lag("z",(s,j,l),time)
        for j,l in balances["I"]:
            balances["I"][j,l] += d.stock("P2",j,l,time)
        for j,origin,dest in d.LL:
            balances["I"][j,origin] -= get("move",j,origin,dest,time)
            balances["I"][j,dest] += lag("move",(j,origin,dest),time)
        for p,l in d.domains()["a"]:
            first = get("a",p,l,time)
            for j in d.J:
                balances["I"][j,l] -= d.val("A1",j,p)*first
            balances["Wa" if l=="a" else "Wo"][(p,) if l=="a" else (p,l)] += first
        for p,o in d.EO:
            balances["Wo"][p,o] -= get("h",p,o,time)
            balances["Wa"][p,] += lag("h",(p,o),time)
        for p in d.M:
            second, shipped = get("b",p,time),get("e",p,time)
            for j in d.J:
                balances["I"][j,"a"] -= d.val("A2",j,p)*second
            balances["Wa"][p,] += d.stock("PW",p,time)-second
            balances["F"][p,] += second-shipped
            actual = d.stock("PF",p,time)+lag("e",(p,),time)
            record("customer_arrivals",abs(actual-get("ell",p,time)))
            if time <= d.val("due",p):
                received[p] += actual
            if time+d.leads["e"][p,] > d.val("due",p):
                record("late_dispatch",abs(shipped))
        for group,entries in balances.items():
            for idx,amount in entries.items():
                record(group+"_balance",abs(amount-get(group,*idx,time)))
                record("physical_available",-amount)
        for s in d.S:
            consumed = sum(d.val("a",ss,j)*get("q",ss,j,time) for ss,j in d.E if ss==s)
            record("T2_capacity",consumed-d.val("K",s,time)*(1-d.val("eps",s)*risk["eta"][s]))
        for k in d.K:
            t = sum(get("t",kk,s,time) for kk,s in d.N if kk==k)
            g = sum(get("g",kk,s,time) for kk,s in d.NB if kk==k)
            loss = d.val("C",k,time)*d.val("delta",k)*risk["xi"][d.node[k]]
            record("T3_capacity",t-d.val("C",k,time)+loss)
            record("backup_period",g-d.val("G",k,time)*z["y"][k,])
            record("backup_loss",g-loss)
        record("stage1_capacity",sum(d.val("tau1",p)*get("a",p,"a",time) for p in d.M)-d.val("P1",time))
        record("stage2_capacity",sum(d.val("tau2",p)*get("b",p,time) for p in d.M)-d.val("P2",time))
        for o in d.O:
            used = sum(d.val("tauO",p,oo)*get("a",p,oo,time) for p,oo in d.EO if oo==o)
            record("external_capacity",used-d.val("PO",o,time)*(1-d.val("chi",o)*risk["theta"][o]))
    for k in d.K:
        record("backup_cumulative",sum(val for (kk,s,t),val in v["g"].items() if kk==k)-z["r"][k,])
    for p in d.M:
        record("order",abs(received[p]+get("u",p)-d.val("D",p)))
        if mode=="nominal":
            record("nominal_full",abs(get("u",p)))
    for h in set(d.family.values()):
        required = d.val("alpha",h)*sum(d.val("D",p) for p in d.M if d.family[p]==h)
        record("joint_service",required-sum(received[p] for p in d.M if d.family[p]==h)-get("sigma",h))
    cash = sum(d.costs[group][idx[:-1]]*quantity for group in ("q","g","z","move","a","b","h","e")
               for idx,quantity in v[group].items())
    record("cash",cash-d.val("Eop"))
    return rows
