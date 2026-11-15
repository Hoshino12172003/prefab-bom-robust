"""Plain finite C&CG. One block per iteration and serial exact enumeration."""

import ctypes as ct
import sys
from collections import defaultdict
from time import perf_counter

from common import ALPHA, CELL, COST, DELTA, GRB, H, STORAGE, TOL, audit_prep, capital, dimensions, exact, gp, prepare


def memory():
    """Process high-water RSS on Windows. Samples are cumulative across runs."""
    if sys.platform != "win32":
        return None
    class ProcessMemory(ct.Structure):
        _fields_ = [("cb",ct.c_ulong),("faults",ct.c_ulong)] + [(k,ct.c_size_t) for k in (
            "peak_working","working","quota_peak_paged","quota_paged","quota_peak_nonpaged","quota_nonpaged","page","peak_page")]
    info=ProcessMemory()
    info.cb=ct.sizeof(info)
    get_process=ct.windll.kernel32.GetCurrentProcess
    get_process.restype=ct.c_void_p
    get_memory=ct.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes=(ct.c_void_p,ct.POINTER(ProcessMemory),ct.c_ulong)
    return info.peak_working if get_memory(get_process(),ct.byref(info),info.cb) else None


class Incomplete(Exception):
    """An unclosed solve cannot provide evidence for a certificate."""

    def __init__(self, row):
        self.row=row
        super().__init__(f'{row["run"]}/{row["level"]}: {row["solver_status"]}')


def solve_stage(model, objective, sense, run, level, rows, **fields):
    info=exact(model,objective,sense)
    row=dict(run=run,level=level,**fields,**info)
    rows.append(row)
    if not info["exact"]:
        raise Incomplete(row)
    return round(info["objective"])


def master(env, op, nominal, active, budget, label, out, evidence, export=False):
    started=perf_counter()
    with gp.Model(label,env=env) as model:
        prep=prepare(model,op.base,op.states,H,nominal,ALPHA,DELTA,STORAGE)
        end,seat,pool,material=prep[6:]
        model.addConstr(material<=budget,name="PreparationCapital")
        common=model.addVars(op.states,vtype=GRB.INTEGER,name="CommonOpening60")
        for k in op.states:
            model.addConstr(common[k]==op.initial[k]+end[k])
        model.update()
        pre={v.index for v in model.getVars()}
        assert len(pre)==4208
        ot=model.addVar(vtype=GRB.INTEGER,ub=op.demand,name="WorstOnTimeCount")
        area=model.addVar(vtype=GRB.INTEGER,ub=op.maximum_backlog,name="WorstOrderPeriodBacklog")
        holding=model.addVar(name="WorstHoldingCentsPeriods")
        bounds=op.bounds(prep[3])
        blocks={}
        for i,(scenario,profile) in enumerate(active.items()):
            block=op.add_recovery(model,f"W{i}",profile,common,bounds,seat,pool)
            blocks[scenario]=block
            model.addConstr(block[-3]>=ot)
            model.addConstr(block[-2]<=area)
            model.addConstr(block[-1]<=holding)
        pre_holding=gp.quicksum(COST[op.states[n,p][0]]*v for (n,p,_),v in prep[2].items() if p not in CELL)
        total=3650*material+pre_holding+holding
        model.update()
        build=perf_counter()-started
        size=dimensions(model)
        growth=dict(run=label,scenarios=len(active),build_seconds=build,**size)
        evidence["master_growth"].append(growth)
        stats=evidence["lexicographic_profile"]
        first=len(stats)
        try:
            rho=solve_stage(model,ot,GRB.MAXIMIZE,label,"service",stats)
            ot.LB=ot.UB=rho
            tau=solve_stage(model,area,GRB.MINIMIZE,label,"backlog",stats)
            area.LB=area.UB=tau
            cost=solve_stage(model,total,GRB.MINIMIZE,label,"economics",stats)
        finally:
            growth.update(solve_seconds=sum(r["runtime_seconds"] for r in stats[first:]),peak_rss_bytes=memory())
        if export:
            for extension in ("lp.gz","mps.gz"):
                model.write(str(out/f"{label}.{extension}"))
        b={k:round(v.X) for k,v in end.items()}
        start={k:round(v.X) for k,v in common.items()}
        residual,_,_=audit_prep(model,prep,H)
        assert capital(op,b)<=budget and all(op.initial[k]+b[k]==v for k,v in start.items())
        base_cost=round(3650*material.getValue()+pre_holding.getValue())
        assert abs(cost-base_cost-holding.X)<=TOL
        all_indices=set()
        max_residual=residual
        binding={}
        for scenario,block in blocks.items():
            indices={v.index for family in block[:4] for v in family.values()}
            assert len(indices)==sum(map(len,block[:4])) and not indices & (all_indices | pre)
            all_indices.update(indices)
            for n,p in common:
                line=model.getRow(block[4][n,p,op.periods[0]])
                assert [(line.getVar(i).index,line.getCoeff(i)) for i in range(line.size()) if line.getVar(i).index in pre]==[(common[n,p].index,-1)]
            metrics=op.replay(model,block,start,bounds,seat,pool,active[scenario],label,scenario,defaultdict(list))
            assert metrics["on_time"]>=rho and metrics["backlog_area"]<=tau
            binding[scenario]=metrics["on_time"]==rho or metrics["backlog_area"]==tau
            max_residual=max(max_residual,*(metrics[k] for k in ("max_balance_residual","max_capacity_violation",
                                                               "max_inventory_violation","backlog_identity_error")))
        assert len(all_indices)+len(pre)+3==model.NumVars
        return dict(ot=rho,tau=tau,cost_ticks=cost,prep_cost_ticks=base_cost,capital_cents=capital(op,b),b=b,opening=start,
            bounds=bounds,seat=seat,pool=pool,max_residual=max_residual,first_stage_variables=len(pre),
            selected_ids=list(active),binding=binding,stage_rows=stats[first:],**growth)


def recourse(env, op, solution, scenario, profile, objective, ot, backlog, label, evidence, audit=False):
    start=perf_counter()
    with gp.Model(f"{label}_{scenario}_{objective}",env=env) as model:
        args=[solution[k] for k in ("opening","bounds","seat","pool")]
        model_block=op.add_recovery(model,"R",profile,*args)
        q,a,h=model_block[-3:]
        if ot is not None:
            model.addConstr(q>=ot)
        if backlog is not None:
            model.addConstr(a<=backlog)
        model.update()
        row_start=len(evidence)
        try:
            value=solve_stage(model,{"service":q,"backlog":a,"economics":h}[objective],
                GRB.MAXIMIZE if objective=="service" else GRB.MINIMIZE,label,objective,evidence,
                scenario=scenario,event_composition=scenario,service_floor=ot,backlog_ceiling=backlog,**dimensions(model))
        finally:
            if len(evidence)>row_start:
                evidence[-1]["wall_seconds"]=perf_counter()-start
        if audit:
            metrics=op.replay(model,model_block,*args,profile,label,scenario,defaultdict(list))
            evidence[-1]["residual"]=max(metrics[k] for k in ("max_balance_residual","max_capacity_violation",
                                                              "max_inventory_violation","backlog_identity_error"))
            evidence[-1]["replayed_ot"]=metrics["on_time"]
            evidence[-1]["replayed_backlog"]=metrics["backlog_area"]
            assert abs(metrics["holding_usd"]*365000-value)<1e-4
        return value


def risk_order(service, backlog):
    return sorted(service,key=lambda s:(service[s],-backlog.get(s,0),s))


def separation_choice(solution, service, backlog, economics):
    """Risk ranking is independent of economics. Complete feasibility certifies each tier."""
    ranked=risk_order(service,backlog)
    winner=ranked[0]
    if service[winner]<solution["ot"]:
        return winner,"PRIMARY_VIOLATION",winner
    assert service[winner]==solution["ot"]
    worst=min(backlog,key=lambda s:(-backlog[s],s))
    if backlog[worst]>solution["tau"]:
        return worst,"CONDITIONAL_BACKLOG_VIOLATION",winner
    assert backlog[worst]==solution["tau"]
    violated=sorted(s for s,h in economics.items() if solution["prep_cost_ticks"]+h>solution["cost_ticks"])
    if violated:
        return violated[0],"ECONOMIC_FEASIBILITY_VIOLATION",winner
    assert solution["prep_cost_ticks"]+max(economics.values())==solution["cost_ticks"]
    return None,"CERTIFIED",winner


def oracle(env, op, solution, scenarios, label, rows, audit=False):
    service,backlog,economics={},{},{}
    first=len(rows)
    for s, profile in scenarios.items():
        service[s]=recourse(env,op,solution,s,profile,"service",None,None,label,rows)
    worst=min(service.values())
    if worst<solution["ot"]:
        candidates=[s for s in scenarios if service[s]==worst]
    else:
        candidates=list(scenarios)
    for s in candidates:
        backlog[s]=recourse(env,op,solution,s,scenarios[s],"backlog",worst,None,label,rows)
    if worst==solution["ot"] and max(backlog.values())==solution["tau"]:
        for s,profile in scenarios.items():
            economics[s]=recourse(env,op,solution,s,profile,"economics",worst,solution["tau"],label,rows,audit)
    selection,reason,winner=separation_choice(solution,service,backlog,economics)
    ranked=risk_order(service,backlog)
    secondary=sorted(backlog,key=lambda s:(-backlog[s],s)) if worst==solution["ot"] else []
    rank={s:i for i,s in enumerate(ranked,1)}
    subrank={s:i for i,s in enumerate(secondary,1)}
    for row in rows[first:]:
        s=row["scenario"]
        row.update(primary_rank=rank[s],secondary_rank=subrank.get(s),selected_risk=s==winner,added=s==selection,
                   scenario_ot=service[s],scenario_backlog=backlog.get(s),scenario_min_holding_ticks=economics.get(s))
    return dict(added=selection,reason=reason,winner=winner,service=service,backlog=backlog,economics=economics,rank=rank,
                recovery_worst=secondary[0] if secondary else None,solves=rows[first:])


def ccg(env, op, nominal, scenarios, budget, gamma, label, out, evidence, checkpoint):
    started=perf_counter()
    active={"NOM":scenarios["NOM"]}
    primary_lb=0
    discovery={"NOM":0}
    repeated=set()
    iteration=0
    while True:
        iteration+=1
        t=perf_counter()
        tag=f"{label}_i{iteration}"
        current=master(env,op,nominal,active,budget,tag,out,evidence,export=iteration==1 and label=="G1_MID")
        end_master=perf_counter()
        result=oracle(env,op,current,scenarios,tag,evidence["oracle_profile"])
        primary_worst=min(result["service"].values())
        primary_lb=max(primary_lb,primary_worst)
        assert primary_lb<=current["ot"]
        if result["winner"] in active:
            repeated.add(result["winner"])
        added=result["added"]
        times=[r["runtime_seconds"] for r in result["solves"]]
        levels={r["level"]:r for r in current["stage_rows"]}
        evidence["iteration_profile"].append(dict(run=label,iteration=iteration,budget_cents=budget,gamma=gamma,
            master_count=len(active),master_scenarios=";".join(active),added=added,composition=added,
            oracle_winner=result["winner"],recovery_worst=result["recovery_worst"],primary_master=current["ot"],
            secondary_master=current["tau"],tertiary_master_ticks=current["cost_ticks"],oracle_worst_ot=primary_worst,
            oracle_worst_backlog=max(result["backlog"].values()),primary_lb=primary_lb,primary_ub=current["ot"],
            secondary_lb=current["tau"] if primary_worst==current["ot"] else None,
            secondary_ub=max(result["backlog"].values()) if primary_worst==current["ot"] else None,
            result=result["reason"],converged=added is None,master_variables=current["variables"],
            master_constraints=current["constraints"],master_nonzeros=current["nonzeros"],
            master_level1=levels["service"]["runtime_seconds"],master_level2=levels["backlog"]["runtime_seconds"],
            master_level3=levels["economics"]["runtime_seconds"],master_seconds=end_master-t,
            oracle_seconds=perf_counter()-end_master,recourse_milps=len(times),recourse_mean=sum(times)/len(times),
            recourse_max=max(times),winner_recourse=sum(r["runtime_seconds"] for r in result["solves"] if r["scenario"]==result["winner"]),
            iteration_seconds=perf_counter()-t,cumulative_seconds=perf_counter()-started,peak_rss_bytes=memory(),
            master_nodes=sum(r["node_count"] for r in levels.values()),master_solution_count=sum(r["solution_count"] for r in levels.values()),
            max_mip_gap=max(r["mip_gap"] for r in [*levels.values(),*result["solves"]]),repeat_winner=result["winner"] in active))
        checkpoint()
        print(tag,"OT",current["ot"],"tau",current["tau"],"oracle",result["winner"],"add",added,flush=True)
        if added is None:
            final=oracle(env,op,current,scenarios,f"{label}_independent_replay",evidence["final_replay"],audit=True)
            assert final["reason"]=="CERTIFIED" and final["added"] is None
            for s,i in discovery.items():
                atoms=s.split("+") if s!="NOM" else []
                evidence["scenario_discovery"].append(dict(run=label,budget_cents=budget,gamma=gamma,iteration=i,scenario=s,
                    families=";".join(a.rsplit("_",1)[0] for a in atoms),levels=";".join(a.rsplit("_",1)[1] for a in atoms),
                    primary_critical=final["service"][s]==current["ot"],secondary_critical=final["backlog"][s]==current["tau"],
                    repeated_later=s in repeated,remained_binding_in_final_master=current["binding"][s],
                    final_full_replay_rank=final["rank"][s]))
            return current, final, iteration
        assert added not in active and len(active)<len(scenarios),result["reason"]
        active[added]=scenarios[added]
        discovery[added]=iteration
