"""Phase 3.2C finite certification and matched solver runs."""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
from pathlib import Path
from time import perf_counter

import gurobipy as gp
import numpy as np
import psutil
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = ROOT/"artifacts/v3_phase32p_20261111_224834"
sys.path.insert(0,str(P))
import grid
from profile_runs import catalog
from prefab_v3 import e4_ccg as e4, plain_ccg as plain

FROZEN = grid.FROZEN
BASE = PROFILES = CASES = PREFIX = None
VALIDATION = ("probe_C", "probe_T", "probe_CT", "probe_CTO", "region_CTO")
SIZES = (4,8,16,24,32,38)
INPUT = Path.home()/"private_inputs/attachment/已粘贴的文本.txt"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_frozen():
    grid.freeze()
    previous = grid.load()["previous"]
    path = P/"sha256_manifest.csv"
    records = FROZEN.read(path)
    assert all(FROZEN.digest(ROOT/r["path"])==r["sha256"] for r in records)
    return {**previous,P.name:dict(entries=len(records),manifest_sha256=FROZEN.digest(path))}


def init():
    global BASE, PROFILES, CASES, PREFIX
    FROZEN.init()
    BASE = FROZEN.BASE
    opening = FROZEN.OPENING
    _, PROFILES, _, _, names = catalog(BASE,opening)
    protocol = grid.load()
    for name, record in protocol["scenarios"].items():
        profile = grid.profile(name,record,BASE,opening)
        if name in PROFILES:
            assert PROFILES[name]==profile
        PROFILES[name] = profile
    PREFIX = e4.Prefix(BASE)
    CASES = {str(n):dict(names=names[:n],costs=grid.prior.COSTS,budget=grid.prior.BUDGET,
                       source_policy=None) for n in SIZES}
    for n,key in (("region_C","BASE_B100"),("region_CT","BASE_B150"),("region_CTO","R3_S75_D7_ABRUPT_B100")):
        r = read(P/"runs"/f"{key}.json")
        assert r["status"]=="EXACT_FINITE"
        c = r["case"]
        CASES[n] = dict(names=tuple(c["scenarios"]),costs=tuple(map(F,c["costs"])),budget=F(c["budget"]),
                        source_policy=r["policy"],source_objective=r["objective"],source=key)
    for name, x in (("probe_C",(915,0,0)),("probe_T",(0,644,0)),
                    ("probe_CT",tuple(CASES["region_CT"]["source_policy"])),
                    ("probe_CTO",tuple(CASES["region_CTO"]["source_policy"]))):
        CASES[name] = dict(names=names[:16]+("BGS_OVERLAP","R3_S75_D7_ABRUPT"),source_policy=x)


class Solver:
    def __init__(self, key, env, limit):
        self.env,self.limit = env,limit
        self.directory = HERE/"logs"/key
        self.directory.mkdir(parents=True,exist_ok=True)
        self.records = []

    def run(self, tag, build, witness=False):
        t = perf_counter()
        with gp.Model(env=self.env) as model:
            FROZEN.configure(model,seconds=self.limit)
            path = self.directory/f"{tag}.log"
            path.write_text("",encoding="utf-8")
            model.Params.LogFile = os.path.relpath(path,ROOT)
            score, variables, blocks = build(model)
            model.update()
            assert model.NumVars==model.NumIntVars and not model.NumBinVars
            after_build = perf_counter()
            model.optimize()
            r = dict(tag=tag,log=path.relative_to(HERE).as_posix(),status=model.Status,integers=model.NumIntVars,
                constraints=model.NumConstrs,nodes=int(model.NodeCount),solver_seconds=model.Runtime,
                build_seconds=after_build-t,peak_bytes=grid.prior.peak_bytes())
            self.records.append(r)
            if model.Status!=GRB.OPTIMAL or model.MIPGap!=0 or model.ObjVal!=model.ObjBound:
                r.update(incumbent=model.ObjVal if model.SolCount else None,bound=model.ObjBound)
                raise RuntimeError(f"{path.name} Gurobi status={model.Status}")
            v,residual = FROZEN.exact_vector(model,FROZEN.matrix_rows(model))
            q = int(model.ObjVal)
            assert q==model.ObjVal==min(grid.prior.selected_quantity(b,BASE,v) for b in blocks.values())
            if score is not None:
                assert q==v[score.index]
            x = tuple(int(v[p.index]) for p in variables)
            r.update(q=q,bound=q,residual=residual)
            if witness:
                target = HERE/"witnesses"/self.directory.name/f"{tag}.npz"
                target.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(target,solution=v.astype(np.int64))
                r.update(witness=target.relative_to(HERE).as_posix(),witness_sha256=FROZEN.digest(target))
        r["wall_seconds"] = perf_counter()-t
        return q,x,r

    def fixed(self, name, profile, policy, tag):
        def build(model):
            b = plain.add_recourse_block(model,BASE,"recourse",profile,policy)
            model.setObjective(plain.on_time(b,BASE),GRB.MAXIMIZE)
            return None,(),{name:b}
        q,_,r = self.run(f"{tag}__{name}",build,witness=name.startswith("meet__"))
        return q,r

    def master(self, profiles, names, costs, budget, tag, direct=False):
        def build(model):
            if not direct:
                x,z,b = plain.build_master(model,BASE,profiles,names,costs,budget)
            else:
                x = FROZEN.add_stage_one(model,costs,budget)
                z = model.addVar(ub=BASE.network.demand_weight,vtype=GRB.INTEGER,name="worst")
                b = {}
                for n in names:
                    arrivals,factors = profiles[n]
                    b[n] = FROZEN.add_block(model,BASE,n,FROZEN.Weights(0,0,0,0,0),reschedule=True,
                        fixed_receipts=arrivals,arc_factors=factors,protection=FROZEN.protection_inventory(x))
                    model.addConstr(z<=grid.prior.direct_score(b[n],BASE))
                model.setObjective(z,GRB.MAXIMIZE)
            return z,x,b
        q,x,r = self.run(tag,build)
        assert sum(c*p for c,p in zip(costs,x,strict=True))<=budget
        return plain.MasterSolution(q,x,dict(log=r["log"]))


def save(key, value):
    dest = HERE/"runs"/f"{key}.json"
    temp = dest.with_suffix(".tmp")
    temp.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
    temp.replace(dest)


def validate_policy(name):
    c = CASES[name]
    profiles = {n:PROFILES[n] for n in c["names"]}
    x = c["source_policy"]
    with FROZEN.env() as env:
        solver = Solver(name,env,180)
        actual = {n:solver.fixed(n,p,x,"validate")[0] for n,p in profiles.items()}
        # Check every available common witness, including the first calendar pair.
        bounds = {}
        for a,b in dict.fromkeys(e4.seat_pairs(profiles).values()):
            low, r = solver.fixed(f"meet__{a}__{b}",e4.intersection(profiles[a],profiles[b]),x,"validate")
            for n in (a,b):
                bounds[n] = low,r
        rows = []
        for n,p in profiles.items():
            lower,evidence = bounds.get(n,(0,{}))
            pack,seat,upper = PREFIX.upper(p,x)
            rows.append(dict(policy_id=name,policy=x,scenario=n,lower=lower,upper=upper,pack_upper=pack,
                seat_upper=seat,exact=actual[n],violation=not lower<=actual[n]<=upper,
                witness=evidence.get("witness"),exact_log=next(r["log"] for r in solver.records if r["tag"]==f"validate__{n}")))
        if "source_objective" in c:
            assert min(actual.values())==c["source_objective"]
        save(name,dict(rows=rows,records=solver.records))
    print(name,len(rows),"violations",sum(r["violation"] for r in rows),flush=True)


def initial_blocks(name, names, style):
    if name=="region_CTO":
        return (names[-1],) if style=="single" else names
    return (grid.prior.BASELINE,) if style=="single" else (grid.prior.BASELINE,grid.prior.SEVERE)


def benchmark(name, style, repeat, method):
    key = f"{name}_{style}_{repeat}_{method}"
    c = CASES[name]
    names = c["names"]
    profiles = {n:PROFILES[n] for n in names}
    payload = dict(name=name,style=style,repeat=repeat,method=method,scenarios=names,
                   status="UNCERTIFIED",objective=None,iterations=[],oracles=[],verified={})
    start = perf_counter()
    with FROZEN.env() as env:
        solver = Solver(key,env,240 if len(names)>16 else 90)
        def master(active,k):
            return solver.master(profiles,active,c["costs"],c["budget"],f"MP_{k:02d}")
        def fixed(n,x,tag):
            return solver.fixed(n,profiles[n],x,tag)[0]
        def oracle(x,k):
            t = perf_counter()
            ans = e4.separate(profiles,PREFIX,x,lambda n,p,y:solver.fixed(n,p,y,f"E4_{k:02d}"))
            payload["oracles"].append(dict(policy=x,iteration=k,worst=ans.worst,ties=ans.ties,rows=ans.rows,
                bound_seconds=ans.bound_seconds,individual=ans.individual_solves,common=ans.common_solves,
                wall_seconds=perf_counter()-t))
            return ans
        try:
            if method=="DE":
                mp = solver.master(profiles,names,c["costs"],c["budget"],"DE",direct=True)
                t = perf_counter()
                v = {n:fixed(n,mp.policy,"verify") for n in names}
                assert mp.objective==min(v.values())
                sol = plain.Result(mp.objective,mp.policy,names,v,(),perf_counter()-t)
            else:
                initial = initial_blocks(name,names,style)
                payload["initial"] = initial
                sol = (plain.generate(names,initial,master,fixed) if method=="PLAIN"
                       else e4.generate(names,initial,master,oracle,fixed))
            payload.update(status="EXACT_FINITE",objective=sol.objective,policy=sol.policy,iterations=sol.iterations,
                           selected=sol.selected,verified=sol.verified_services,verification_seconds=sol.verification_seconds)
        except (RuntimeError,gp.GurobiError) as error:
            payload.update(error=str(error),error_type=type(error).__name__)
        payload["records"] = solver.records
    payload.update(wall_seconds=perf_counter()-start,peak_bytes=grid.prior.peak_bytes(),
                   affinity=psutil.Process().cpu_affinity())
    save(key,payload)
    print(key,payload["status"],payload["objective"],round(payload["wall_seconds"],2),flush=True)


def run_lane(jobs, core, direct_slots):
    for job in jobs:
        cmd = [sys.executable,"-B",__file__,"job",str(core),*map(str,job)]
        if job[-1]=="DE":
            with direct_slots:
                subprocess.run(cmd,cwd=ROOT,check=True)
        else:
            subprocess.run(cmd,cwd=ROOT,check=True)


def main():
    if len(sys.argv)>1 and sys.argv[1]=="job":
        _,_,core,name,style,repeat,method = sys.argv
        psutil.Process().cpu_affinity([int(core)])
        init()
        benchmark(name,style,int(repeat),method)
        return
    from multiprocessing import Manager
    parser = argparse.ArgumentParser()
    parser.add_argument("stage",choices=("validate","bench","repeat","all"))
    args = parser.parse_args()
    verify_frozen()
    (HERE/"runs").mkdir(exist_ok=True)
    if args.stage=="validate":
        with ProcessPoolExecutor(max_workers=5,initializer=init) as pool:
            list(pool.map(validate_policy,VALIDATION))
        assert not any(r["violation"] for n in VALIDATION for r in read(HERE/"runs"/f"{n}.json")["rows"])
        return
    assert not any(r["violation"] for n in VALIDATION for r in read(HERE/"runs"/f"{n}.json")["rows"])
    lanes = [[(n,"single",1,"PLAIN"),(n,"single",1,"E4"),(n,"direct",1,"DE"),
              (n,"two",1,"E4"),(n,"two",1,"PLAIN")] for n in (*map(str,SIZES),"region_CT","region_CTO")]
    repeats = [[(str(n),"single",r,m) for m in (("E4","PLAIN","DE") if r==2 else ("PLAIN","E4","DE"))]
               for r,n in ((2,38),(3,38),(2,16),(3,16),(2,32),(3,32))]
    if args.stage=="all":
        for index,extra in zip((0,1,2,7,6,7),repeats,strict=True):
            lanes[index].extend(extra)
    if args.stage=="repeat":
        lanes = repeats
    with Manager() as manager:
        direct_slots = manager.BoundedSemaphore(2)
        cores = psutil.Process().cpu_affinity()[:len(lanes)]
        with ProcessPoolExecutor(max_workers=len(lanes)) as pool:
            futures = [pool.submit(run_lane,lane,core,direct_slots) for lane,core in zip(lanes,cores,strict=True)]
            for future in as_completed(futures):
                future.result()


if __name__=="__main__":
    main()
