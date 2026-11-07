"""Equation 42, with automatic strict-positivity certificates."""


def certificates(d):
    for h in sorted(set(d.family.values())):
        products=[p for p in d.M if d.family[p]==h]
        prepaid=sum(d.stock("F",p)+sum(d.stock("PF",p,t) for t in d.periods) for p in products)
        target=d.val("alpha",h)*sum(d.val("D",p) for p in products)
        for j in d.J:
            a=min(d.val("A2",j,p) for p in products)
            suppliers=[s for s,jj in d.E if jj==j]
            if a<=0 or not suppliers:
                continue
            for k in d.K:
                b=min(d.val("b",k,s,j) for s in suppliers)
                if b>0:
                    yield {"h":h,"j":j,"k":k,"a":a,"b":b,"lhs":a*max(0,target-prepaid)}


def expression(d,z,w,certificate):
    j,k=certificate["j"],certificate["k"]
    component=sum(d.stock("I",j,l)+z["x"][j,l] for l in d.L)
    component+=sum(d.stock("S",s,jj) for s,jj in d.E if jj==j)
    component+=sum(d.stock("P2",j,l,t) for l in d.L for t in d.periods)
    resource=sum(d.stock("R",kk,s)+sum(d.stock("P3",kk,s,t) for t in d.periods)
                 for kk,s in d.N|d.NB if kk==k)
    resource+=sum(d.val("C",k,t)*(1-d.val("delta",k)*w["xi"][d.node[k]]) for t in d.periods)
    resource+=z["r"][k,]
    return component+resource/certificate["b"]


def reachable_expression(d,z,w,certificate):
    """Necessary prefix bound. Keep all pre-window stocks, discard only unreachable new T3 dispatches."""
    j,k,h=certificate["j"],certificate["k"],certificate["h"]
    deadline=max(d.val("due",p)-d.leads["e"][p,] for p in d.M if d.family[p]==h)
    # Shortest component transport from any location to the internal stage-2 site.
    distance={l:float("inf") for l in d.L}
    distance["a"]=0
    for _ in d.L:
        for jj,origin,dest in d.LL:
            if jj==j:
                distance[origin]=min(distance[origin],d.leads["move"][jj,origin,dest]+distance[dest])
    downstream={s:min((d.leads["z"][ss,jj,l]+distance[l] for ss,jj,l in d.SL
                      if (ss,jj)==(s,j)),default=float("inf"))
                for s,jj in d.E if jj==j}
    eligible={group:[(kk,s) for kk,s in arcs if kk==k and s in downstream]
              for group,arcs in (("t",d.N),("g",d.NB))}
    normal=sum(d.val("C",k,t)*(1-d.val("delta",k)*w["xi"][d.node[k]])
               for t in d.periods if any(t+d.leads["t"][arc]+downstream[arc[1]]<=deadline
                                         for arc in eligible["t"]))
    backup=z["r"][k,] if any(1+d.leads["g"][arc]+downstream[arc[1]]<=deadline
                             for arc in eligible["g"]) else 0
    total_normal=sum(d.val("C",k,t)*(1-d.val("delta",k)*w["xi"][d.node[k]]) for t in d.periods)
    return expression(d,z,w,certificate)+(normal+backup-total_normal-z["r"][k,])/certificate["b"]


def add_cuts(model,d,z,risks):
    count=0
    for cert in certificates(d):
        for w in risks:
            model.addConstr(expression(d,z,w,cert)>=cert["lhs"],name=f"cover_{count}")
            count+=1
            model.addConstr(reachable_expression(d,z,w,cert)>=cert["lhs"],name=f"reachable_{count}")
            count+=1
    return count
