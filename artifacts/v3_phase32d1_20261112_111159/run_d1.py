"""Run fixed-policy BTB prefix work and the separate frozen exact reference."""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from time import perf_counter

import gurobipy as gp
import numpy as np
from gurobipy import GRB

import catalog_d1 as cat

HERE, ROOT, FROZEN = cat.HERE,cat.ROOT,cat.FROZEN
E4, PLAIN = cat.previous.e4,cat.previous.plain


def load():
    meta = cat.read(HERE/"catalog_metadata.json")
    assert FROZEN.digest(HERE/"full_effective_rhs_catalog.csv")==meta["catalog_sha256"]
    rows = FROZEN.read(HERE/"full_effective_rhs_catalog.csv")
    assert len(rows)==38527
    FROZEN.init()
    return meta,rows,FROZEN.BASE,FROZEN.OPENING


def rhs(row, keys, nominal, opening):
    arrivals, factors = dict(opening), {}
    for key,q,original in zip(keys,map(F,json.loads(row["canonical_signature"])),nominal,strict=True):
        if q!=original:
            if key[0]=="receipt":
                arrivals[key[1:]] = int(q)
            else:
                factors[key[1:]] = q/original
    return arrivals,factors


def full_solve(env, base, profile, x, policy, id_, purpose):
    start = perf_counter()
    path = HERE/"logs"/policy/f"{purpose}_{id_}.log"
    path.parent.mkdir(parents=True,exist_ok=True)
    with gp.Model("fixed_policy",env=env) as model:
        FROZEN.configure(model,seconds=180)
        path.write_text("",encoding="utf-8")
        model.Params.LogFile = os.path.relpath(path,ROOT)
        b = PLAIN.add_recourse_block(model,base,"recourse",profile,x)
        model.setObjective(PLAIN.on_time(b,base),GRB.MAXIMIZE)
        model.update()
        assert model.NumVars==model.NumIntVars==75810
        after_build = perf_counter()
        model.optimize()
        record = dict(policy=policy,rhs_class_id=id_,purpose=purpose,status=model.Status,
                      build_seconds=after_build-start,solver_seconds=model.Runtime,log=path.relative_to(HERE).as_posix(),
                      nodes=int(model.NodeCount),integer_variables=model.NumIntVars,rows=model.NumConstrs)
        if model.Status==GRB.OPTIMAL and model.ObjVal==model.ObjBound and model.MIPGap==0:
            v,residual = FROZEN.exact_vector(model,FROZEN.matrix_rows(model))
            q = cat.previous.grid.prior.selected_quantity(b,base,v)
            assert q==model.ObjVal
            record.update(Q=q,certified_bound=q,residual=residual,exact_integer_matrix_residual=0)
            if purpose=="WORST_REFERENCE_VERIFY":
                target = HERE/"witnesses"/policy/f"{id_}.npz"
                target.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(target,solution=v.astype(np.int64))
                record.update(witness=target.relative_to(HERE).as_posix(),witness_sha256=FROZEN.digest(target))
        else:
            record.update(Q=None,certified_bound=model.ObjBound,residual=None)
    record["wall_seconds"] = perf_counter()-start
    return record


def first_pass(policy):
    meta,rows,base,opening = load()
    x = tuple(meta["policies"][policy]["policy"])
    keys,nominal = tuple(map(tuple,meta["schema"])),tuple(map(F,meta["nominal_signature"]))
    t0 = perf_counter()
    prefix = E4.Prefix(base)
    bounds = []
    for r in rows:
        profile = rhs(r,keys,nominal,opening)
        assert all(k[:2]!=E4.SEAT for k in profile[1])
        pack,seat,upper = prefix.upper(profile,x)
        bounds.append((pack,seat,upper))
    t_bound = perf_counter()-t0
    ranks = sorted(range(len(rows)),key=lambda i:(bounds[i][2],rows[i]["rhs_class_id"]))
    rank_by_index = {i:k for k,i in enumerate(ranks,1)}
    lower = np.zeros(len(rows),dtype=np.int64)
    upper = np.array([v[2] for v in bounds])
    categories = np.where(lower==upper,"BOUND_EXACT","MILP_REQUIRED").astype("U16")
    evaluated = {}
    trace = []
    incumbent = int(min(upper[lower==upper])) if np.any(lower==upper) else None
    with FROZEN.env() as env:
        for i in ranks:
            if len(evaluated)==cat.FIRST_BATCH:
                break
            if categories[i]!="MILP_REQUIRED":
                continue
            r = rows[i]
            call = full_solve(env,base,rhs(r,keys,nominal,opening),x,policy,r["rhs_class_id"],"BTB_PREFIX")
            evaluated[i] = call
            q = call["Q"]
            before = incumbent
            if q is not None:
                assert 0<=q<=upper[i]
                incumbent = q if incumbent is None else min(incumbent,q)
            assert incumbent is not None
            start_screen = perf_counter()
            pruned = (categories=="MILP_REQUIRED") & (lower>incumbent)
            assert not any(pruned[j] for j in evaluated)
            categories[pruned] = "SAFE_PRUNED"
            screen_seconds = perf_counter()-start_screen
            trace.append(dict(label=cat.LABEL,policy=policy,rank=rank_by_index[i],rhs_class_id=r["rhs_class_id"],
                safe_upper=int(upper[i]),solved_Q=q,old_incumbent=before,new_incumbent=incumbent,
                new_pruned=int(pruned.sum()),rescreen_seconds=screen_seconds,log=call["log"]))
    detail = [dict(label=cat.LABEL,policy=policy,policy_vector=x,rhs_class_id=r["rhs_class_id"],
        priority_rank=rank_by_index[i],common_witness_eligible=False,lower_before_individual=0,
        pack_upper=bounds[i][0],seat_upper=bounds[i][1],safe_upper=bounds[i][2],
        classification=str(categories[i]),prefix_exact_Q=evaluated.get(i,{}).get("Q"),
        prefix_execution="SOLVED_EXACT" if evaluated.get(i,{}).get("Q") is not None else
                         "ATTEMPTED_UNCERTIFIED" if i in evaluated else "PENDING",
        best_evaluated_incumbent=incumbent) for i,r in enumerate(rows)]
    cat.write(f"{policy}_first_pass.csv",detail)
    cat.dump(f"{policy}_btb.json",dict(policy=x,bound_seconds=t_bound,incumbent=incumbent,
        trace=trace,calls=list(evaluated.values()),categories={c:int(sum(categories==c)) for c in
            ("BOUND_EXACT","SAFE_PRUNED","MILP_REQUIRED")}))
    print(policy,"BTB",incumbent,"bounds",round(t_bound,2),"MILP",len(evaluated),flush=True)


def independent(policy):
    meta,rows,base,opening = load()
    x = tuple(meta["policies"][policy]["policy"])
    t0 = perf_counter()
    proof = cat.nonbattery_certificate(base)
    # Use the independently frozen Phase 3.1 full-network service proof for every class.
    reference = {r["rhs_class_id"]:cat.service_bound(base,cat.U,opening,
                 cat.episodes(json.loads(r["representative_trajectory"])),x) for r in rows}
    seconds = perf_counter()-t0
    q = min(reference.values())
    ties = [n for n,v in reference.items() if v==q]
    btb = cat.read(HERE/f"{policy}_btb.json")
    assert all(r["Q"] is None or r["Q"]==reference[r["rhs_class_id"]] for r in btb["calls"])
    cat.dump(f"{policy}_reference.json",dict(policy=x,worst=q,ties=ties,reference_seconds=seconds,
        nonbattery_proof=proof,service_by_class=reference))
    print(policy,"reference",q,"ties",len(ties),"seconds",round(seconds,2),flush=True)


def verify_worst(policy):
    meta,rows,base,opening = load()
    by_id = {r["rhs_class_id"]:r for r in rows}
    reference = cat.read(HERE/f"{policy}_reference.json")
    keys,nominal = tuple(map(tuple,meta["schema"])),tuple(map(F,meta["nominal_signature"]))
    x = tuple(reference["policy"])
    t0 = perf_counter()
    # Every worst class is listed by the proof. Run full MILP on each if the tie set is small.
    # If larger, confirm the first exact tied class as an integer matrix sentinel.
    planned = reference["ties"] if len(reference["ties"])<=32 else reference["ties"][:1]
    checks = []
    with FROZEN.env() as env:
        for id_ in planned:
            run = full_solve(env,base,rhs(by_id[id_],keys,nominal,opening),x,policy,id_,"WORST_REFERENCE_VERIFY")
            assert run["Q"]==reference["worst"]
            checks.append(run)
    cat.dump(f"{policy}_worst_verification.json",dict(calls=checks,verification_seconds=perf_counter()-t0,
            every_tie_replayed=len(checks)==len(reference["ties"])))
    print(policy,"worst full matrix checks",len(checks),"/",len(reference["ties"]),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage",choices=("btb","reference","verify","all"))
    args = parser.parse_args()
    stages = {"btb":first_pass,"reference":independent,"verify":verify_worst}
    todo = stages.values() if args.stage=="all" else [stages[args.stage]]
    for fn in todo:
        with ProcessPoolExecutor(max_workers=4) as pool:
            list(pool.map(fn,cat.POLICIES))


if __name__=="__main__":
    main()
