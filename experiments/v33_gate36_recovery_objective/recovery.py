"""Extended clearance recourse with the original on-time delivery decisions."""

from collections import Counter, defaultdict, deque
from functools import lru_cache
from itertools import accumulate

import gurobipy as gp
from gurobipy import GRB

from network import ASSEMBLY, CELL, COST, TOL, Operation


def clearance_paths(operation):
    arcs = defaultdict(list)
    for arc in operation.arcs.values():
        for p, recipe in arc.recipes.items():
            for child, _ in recipe:
                arcs[arc.origin, child].append(((arc.destination, p), arc.lead))

    @lru_cache(None)
    def longest(key):
        if key[0] == ASSEMBLY[1]:
            return 0, (key,)
        choices = [(l+length,(key,*path)) for dest,l in arcs[key]
                   for length,path in [longest(dest)] if length >= 0]
        return max(choices, default=(-1, ()))

    rows = []
    for n,p in sorted(set(operation.base.network.external) | operation.states.keys()):
        lead, path = longest((n,p))
        assert lead >= 0, (n,p)
        rows.append(dict(node=n,item=p,group=operation.base.products[p],lead=lead,
                         path=" -> ".join(f"{i}:{j}" for i,j in path)))
    return rows


def backlog_series(demand, due, deliveries, end):
    """Backlog measured after each period, including the due and terminal periods."""
    before = sum(q for t,q in deliveries.items() if t < due)
    return [demand-before-c for c in accumulate(deliveries.get(t,0) for t in range(due,end+1))]


class Recovery(Operation):
    def __init__(self, base, states):
        super().__init__(base, states)
        self.demand_periods = self.periods
        self.path_rows = clearance_paths(self)
        end = self.periods[-1] + max(23,max(row["lead"] for row in self.path_rows))
        self.periods = tuple(range(self.periods[0], end+1))
        self.history = Counter()
        for i,j,p,t,q in base.network.historical:
            arrival = t + self.arcs[i,j].lead
            if arrival in self.periods:
                self.history[j,p,arrival] += q
        self.nominal = {(*a.key,t):a.capacity[self.demand_periods[0]+(t-self.periods[0])%len(self.demand_periods)]
                        for a in self.arcs.values() for t in self.periods}
        self.ott = [(*ASSEMBLY,g,t) for g in self.groups for t in self.demand_periods if t<=self.due[g]]
        self.material = [(*a.key,p,t) for a in self.arcs.values() if a.key!=ASSEMBLY for p in a.recipes for t in self.periods
                         if t+a.lead<=end]
        signatures = defaultdict(list)
        for g, group in self.groups.items():
            signatures[group.representative.bom,self.weight[g]].append(g)
        self.families = {f"L{i:03}": (bom, weight, sorted(groups,key=lambda g:(self.due[g],g)))
                         for i,((bom,weight),groups) in enumerate(sorted(signatures.items()))}
        self.late_keys = [(s,t) for s, (_,_,gs) in self.families.items() for t in self.periods if t>self.due[gs[0]]]
        self.recipe = {(*a.key,p):recipe for a in self.arcs.values() for p,recipe in a.recipes.items()}
        self.recipe.update({(*ASSEMBLY,s):bom for s,(bom,_,_) in self.families.items()})
        self.maximum_backlog = sum(self.weight[g]*len(group.orders)*(end-self.due[g]+1) for g,group in self.groups.items())

    def bounds(self, preparation_limits):
        # Keep the original nominal-prefix technical bounds; extend the same
        # flow-based bound only for the new recovery periods.
        augmented = dict(self.base.network.inventory_bounds)
        for n,p in self.states.keys() - augmented.keys():
            last = self.demand_periods[-1]
            incoming = Counter()
            for a in self.arcs.values():
                if a.destination==n and p in a.recipes:
                    for t in self.periods:
                        arrival = t+a.lead
                        if arrival in self.periods:
                            incoming[arrival] += self.nominal[(*a.key,t)]
            terminal = preparation_limits[n,p][1]
            for t in self.periods:
                upper = terminal + sum(incoming[u]+self.history.get((n,p,u),0) for u in self.periods if u<=max(t,last))
                augmented[n,p,t] = (0,upper)
        return {(n,p,t): augmented[n,p] if (n,p) in augmented else augmented[n,p,t]
                for n,p in self.states for t in self.periods}

    def add_recovery(self, model, tag, profile, opening, bounds, seat, pool):
        on = model.addVars(self.ott,vtype=GRB.INTEGER,name=f"{tag}_OT")
        late = model.addVars(self.late_keys,vtype=GRB.INTEGER,name=f"{tag}_Late")
        material = model.addVars(self.material,vtype=GRB.INTEGER,name=f"{tag}_Flow")
        inventory = model.addVars(bounds.keys(),vtype=GRB.INTEGER,name=f"{tag}_I")
        incoming, consumed, used = defaultdict(gp.LinExpr),defaultdict(gp.LinExpr),defaultdict(gp.LinExpr)
        for (i,j,p,t), var in (*material.items(),*on.items(),*((( *ASSEMBLY,s,t),v) for (s,t),v in late.items())):
            if (i,j)!=ASSEMBLY:
                incoming[j,p,t+self.arcs[i,j].lead] += var
            for child,q in self.recipe[i,j,p]:
                if (i,child) in self.states:
                    consumed[i,child,t] += float(q)*var
            used[i,j,t] += var
        net = self.base.network
        for (i,j,t), cap in self.nominal.items():
            model.addConstr(used[i,j,t]<=int(cap*profile.get((i,j,t),1)),name=f"{tag}_Cap[{i},{j},{t}]")
            if (i,j,t) in net.group_caps:
                model.addConstr(used[i,j,t]<=net.group_caps[i,j,t])
        for k, cap in net.product_caps.items():
            if k in material:
                model.addConstr(material[k]<=cap)
        balances = {}
        for n,p in self.states:
            previous = opening[n,p]
            for t in self.periods:
                k = n,p,t
                v = inventory[k]
                v.LB,v.UB = bounds[k]
                balances[k] = model.addConstr(v==previous+self.history[k]+incoming[k]-consumed[k],
                                               name=f"{tag}_Bal[{n},{p},{t}]")
                previous = v
        for t in self.periods:
            model.addConstr(gp.quicksum(inventory[n,p,t] for n,p in seat)<=pool)
        ost = {g:on.sum(*ASSEMBLY,g,"*") for g in self.groups}
        for g, group in self.groups.items():
            model.addConstr(ost[g]<=len(group.orders))
        # A late unit at t may only serve a cohort already due by t-1 and
        # still unserved after its on-time assignments. Same-BOM cohorts share this queue.
        for s,(_,_,groups) in self.families.items():
            count, cumulative = 0,gp.LinExpr()
            for t in self.periods:
                for g in groups:
                    if self.due[g]==t-1:
                        count += len(self.groups[g].orders)
                        cumulative += ost[g]
                if (s,t) in late:
                    cumulative += late[s,t]
                    model.addConstr(cumulative<=count,name=f"{tag}_Queue[{s},{t}]")
        end = self.periods[-1]
        ot = gp.quicksum(self.weight[g]*v for g,v in ost.items())
        area = self.maximum_backlog - gp.quicksum(self.weight[g]*(end-self.due[g]+1)*v for g,v in ost.items())
        area -= gp.quicksum(self.families[s][1]*(end-t+1)*v for (s,t),v in late.items())
        holding = gp.quicksum(COST[self.states[n,p][0]]*v for (n,p,_),v in inventory.items() if p not in CELL)
        return material,on,late,inventory,balances,ot,area,holding

    def replay(self, model, block, opening, bounds, seat, pool, profile, run, scenario, evidence):
        mats,on,late,inventory,_,ot,area,holding = block
        f, y, late_values, stocks = (model.getAttr("X",x) for x in (mats,on,late,inventory))
        deliveries, incoming, used, withdrawn = defaultdict(Counter), Counter(), Counter(),Counter()
        for (_,_,g,t),q in y.items():
            assert t<=self.due[g]<=self.demand_periods[-1]
            if q:
                deliveries[g][t] = round(q)
        for s,(_,_,groups) in self.families.items():
            remaining = {g:len(self.groups[g].orders)-sum(deliveries[g].values()) for g in groups}
            queue = deque()
            for t in self.periods:
                queue.extend(g for g in groups if self.due[g]==t-1 and remaining[g])
                unassigned = round(late_values.get((s,t),0))
                while unassigned:
                    g = queue[0]
                    q = min(remaining[g],unassigned)
                    deliveries[g][t] += q
                    remaining[g] -= q
                    unassigned -= q
                    if not remaining[g]:
                        queue.popleft()
        int_error = max(abs(q-round(q)) for values in (f,y,late_values,stocks) for q in values.values())
        for (i,j,p,t),q in (*f.items(),*y.items(),*((( *ASSEMBLY,s,t),v) for (s,t),v in late_values.items())):
            if (i,j)!=ASSEMBLY:
                incoming[j,p,t+self.arcs[i,j].lead] += q
                assert q<=self.base.network.product_caps.get((i,j,p,t),q)+TOL
            for child,coef in self.recipe[i,j,p]:
                withdrawn[i,child,t] += float(coef)*q
            used[i,j,t] += q
        max_cap = 0
        for (i,j,t), cap in self.nominal.items():
            multiplier = profile.get((i,j,t),1)
            limit = int(cap*multiplier)
            excess = max(0,used[i,j,t]-limit,used[i,j,t]-self.base.network.group_caps.get((i,j,t),used[i,j,t]))
            max_cap = max(max_cap,excess)
            evidence["capacity_audit"].append(dict(run=run,scenario=scenario,asset=f"{i}->{j}",period=t,
                nominal=cap,multiplier=str(multiplier),effective_integer=limit,used=used[i,j,t],violation=excess))
        max_bal,max_inventory = 0,0
        for (n,p,t),(lower,upper) in bounds.items():
            k=n,p,t
            prev=stocks[n,p,t-1] if t!=self.periods[0] else opening[n,p]
            residual=stocks[k]-(prev+self.history[k]+incoming[k]-withdrawn[k])
            max_bal=max(max_bal,abs(residual))
            max_inventory=max(max_inventory,lower-stocks[k],stocks[k]-upper)
            evidence["balance_audit"].append(dict(run=run,scenario=scenario,node=n,item=p,period=t,opening=prev,
                pipeline=self.history[k],decision_arrival=incoming[k],consumption=withdrawn[k],closing=stocks[k],residual=residual))
        max_inventory=max(max_inventory,*(sum(stocks[n,p,t] for n,p in seat)-pool for t in self.periods))
        assert max(max_cap,max_bal,max_inventory,int_error) <= TOL
        segments, trajectories = defaultdict(Counter),defaultdict(Counter)
        for g, group in self.groups.items():
            due = self.due[g]
            segment = "BEV" if ("BEV",1) in group.representative.bom else "nonBEV"
            w, demand = self.weight[g],len(group.orders)
            dates = deliveries[g]
            daily = backlog_series(demand,due,dates,self.periods[-1])
            assert all(a>=0 for a in daily)
            late_dates = [(t-due,q) for t,q in dates.items() if t>due and q]
            stat = segments[segment]
            stat.update(demand=w*demand,on_time=w*sum(q for t,q in dates.items() if t<=due),terminal=w*daily[-1],area=w*sum(daily),
                        late_deliveries=sum(q for _,q in late_dates),late_periods=sum(days*q for days,q in late_dates))
            stat["max_tardiness"]=max(stat["max_tardiness"],*(days for days,_ in late_dates),0)
            for t,a in enumerate(daily,due):
                trajectories[segment,t]["backlog"] += w*a
            for t,q in dates.items():
                trajectories[segment,t]["deliveries"] += w*q
        total_ot = sum(s["on_time"] for s in segments.values())
        total_area = sum(s["area"] for s in segments.values())
        assert abs(ot.getValue()-total_ot)<=TOL and abs(area.getValue()-total_area)<=TOL
        for segment, r in segments.items():
            evidence["segment_exposure"].append(dict(run=run,scenario=scenario,segment=segment,
                on_time_service=r["on_time"]/r["demand"],**r))
            for t in self.periods:
                p=trajectories[segment,t]
                evidence["recovery_trajectories"].append(dict(run=run,scenario=scenario,segment=segment,period=t,
                    deliveries=p["deliveries"],backlog=p["backlog"]))
        late_units=sum(r["late_deliveries"] for r in segments.values())
        return dict(on_time=total_ot,rho=total_ot/self.demand,backlog_area=total_area,
                    terminal_backlog=sum(r["terminal"] for r in segments.values()),
                    avg_tardiness=sum(r["late_periods"] for r in segments.values())/late_units if late_units else None,
                    max_tardiness=max(r["max_tardiness"] for r in segments.values()),
                    recourse_operating_cost=None,holding_usd=holding.getValue()/365000,
                    max_balance_residual=max_bal,max_capacity_violation=max_cap,max_inventory_violation=max_inventory,
                    backlog_identity_error=abs(area.getValue()-total_area),max_integrality_error=int_error)
