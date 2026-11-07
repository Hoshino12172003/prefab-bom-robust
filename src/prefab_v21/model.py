from itertools import product
import gurobipy as gp
from gurobipy import GRB

from .data import zero_plan

TOL = 1e-7
CASH = ("q", "g", "z", "move", "a", "b", "h", "e")
HOLD = ("R", "S", "I", "Wa", "Wo", "F")


def first_stage(m, d, fixed=None):
    z = zero_plan(d)
    for group in z:
        for key in z[group]:
            z[group][key] = m.addVar(vtype=GRB.BINARY if group == "y" else GRB.CONTINUOUS,
                                      name=f"{group}{key}")
            if fixed is not None:
                m.addConstr(z[group][key] == fixed[group][key])
    for key in z["x"]:
        m.addConstr(z["x"][key] <= d.p["X"][key])
    for key in z["r"]:
        m.addConstr(z["r"][key] <= d.p["Rmax"][key]*z["y"][key])
    cost = sum(d.p["cI"][key]*v for key,v in z["x"].items()) + sum(
        d.p["f"][key]*z["y"][key]+d.p["cR"][key]*z["r"][key] for key in z["y"])
    m.addConstr(cost <= d.val("Bpre"))
    return z, cost


def block(m, d, z, risk, mode, name):
    """Equations 8--29. Different risks use different variable containers."""
    v = {group: {(*idx,t): m.addVar(name=f"{name}_{group}{(*idx,t)}")
                 for idx in sorted(keys) for t in d.periods}
         for group,keys in d.domains().items()}
    u = {p: m.addVar(ub=0 if mode == "nominal" else d.val("D",p)) for p in d.M}
    sigma = {h: m.addVar() for h in set(d.family.values())} if mode == "phase" else {}

    def f(group, *key):
        return v[group].get(key, 0.0)

    def arrive(group, idx, t):
        return f(group, *idx, t-d.leads[group][idx]) if idx in d.leads[group] else 0

    def prev(group, idx, t):
        if t > 1:
            return f(group, *idx, t-1)
        base = d.stock(group, *idx)
        return base + z["x"][idx] if group == "I" else base

    for k in d.K:
        m.addConstr(sum(f("g",kk,s,t) for kk,s in d.NB if kk==k for t in d.periods)
                    <= z["r"][k,], name=f"{name}_total_reserve_{k}")
        for t in d.periods:
            normal = sum(f("t",kk,s,t) for kk,s in d.N if kk==k)
            backup = sum(f("g",kk,s,t) for kk,s in d.NB if kk==k)
            loss = d.val("C",k,t)*d.val("delta",k)*risk["xi"][d.node[k]]
            m.addConstr(normal <= d.val("C",k,t)-loss,name=f"{name}_T3_{k}_{t}")
            m.addConstr(backup <= d.val("G",k,t)*z["y"][k,])
            m.addConstr(backup <= loss)
    for t in d.periods:
        for k,s in d.N | d.NB:
            used = sum(d.val("b",k,s,j)*f("q",s,j,t) for ss,j in d.E if ss==s)
            m.addConstr(f("R",k,s,t) == prev("R",(k,s),t) + d.stock("P3",k,s,t)
                        + arrive("t",(k,s),t)+arrive("g",(k,s),t)-used)
        for s in d.S:
            m.addConstr(sum(d.val("a",ss,j)*f("q",ss,j,t) for ss,j in d.E if ss==s)
                        <= d.val("K",s,t)*(1-d.val("eps",s)*risk["eta"][s]),name=f"{name}_T2_{s}_{t}")
        for s,j in d.E:
            m.addConstr(f("S",s,j,t) == prev("S",(s,j),t)+f("q",s,j,t)
                        - sum(f("z",ss,jj,l,t) for ss,jj,l in d.SL if (ss,jj)==(s,j)))
        for j,l in product(d.J,d.L):
            incoming = d.stock("P2",j,l,t) + sum(arrive("z",(s,jj,ll),t)
                       for s,jj,ll in d.SL if (jj,ll)==(j,l)) + sum(
                       arrive("move",(jj,ll,l2),t) for jj,ll,l2 in d.LL if (jj,l2)==(j,l))
            outgoing = sum(f("move",jj,ll,l2,t) for jj,ll,l2 in d.LL if (jj,ll)==(j,l))
            consumed = sum(d.val("A1",j,p)*f("a",p,l,t) for p in d.M)
            if l == "a":
                consumed += sum(d.val("A2",j,p)*f("b",p,t) for p in d.M)
            m.addConstr(f("I",j,l,t) == prev("I",(j,l),t)+incoming-outgoing-consumed)
        m.addConstr(sum(d.val("tau1",p)*f("a",p,"a",t) for p in d.M) <= d.val("P1",t))
        m.addConstr(sum(d.val("tau2",p)*f("b",p,t) for p in d.M) <= d.val("P2",t))
        for o in d.O:
            m.addConstr(sum(d.val("tauO",p,oo)*f("a",p,oo,t) for p,oo in d.EO if oo==o)
                        <= d.val("PO",o,t)*(1-d.val("chi",o)*risk["theta"][o]),name=f"{name}_O_{o}_{t}")
        for p,o in d.EO:
            m.addConstr(f("Wo",p,o,t) == prev("Wo",(p,o),t)+f("a",p,o,t)-f("h",p,o,t))
        for p in d.M:
            m.addConstr(f("Wa",p,t) == prev("Wa",(p,),t)+f("a",p,"a",t)+d.stock("PW",p,t)
                        +sum(arrive("h",(pp,o),t) for pp,o in d.EO if pp==p)-f("b",p,t))
            m.addConstr(f("F",p,t) == prev("F",(p,),t)+f("b",p,t)-f("e",p,t))
            m.addConstr(f("ell",p,t) == d.stock("PF",p,t)+arrive("e",(p,),t))
            if t+d.leads["e"][p,] > d.val("due",p):
                m.addConstr(f("e",p,t)==0)
    for p in d.M:
        m.addConstr(sum(f("ell",p,t) for t in d.periods if t<=d.val("due",p)) + u[p] == d.val("D",p))
    for h in set(d.family.values()):
        received = sum(f("ell",p,t) for p in d.M if d.family[p]==h
                       for t in d.periods if t<=d.val("due",p))
        required = d.val("alpha",h)*sum(d.val("D",p) for p in d.M if d.family[p]==h)
        m.addConstr(received+sigma.get(h,0) >= required)
    cash = gp.quicksum(d.costs[group][key[:-1]]*var
                       for group in CASH for key,var in v[group].items())
    holding = gp.quicksum(d.costs[group][key[:-1]]*var
                          for group in HOLD for key,var in v[group].items())
    m.addConstr(cash <= d.val("Eop"))
    return v, u, sigma, cash, cash+holding


def values(z):
    return {group: {key: var.X for key,var in entries.items()} for group,entries in z.items()}
