"""Matched comparison on the frozen D-3 Gamma=2 N=32 subset."""

import argparse
from time import perf_counter

import gurobipy as gp
from gurobipy import GRB

from prefab_v3 import e4_ccg, plain_ccg

from run import (HERE, SOURCE, COSTS, BUDGET, Coordinates, Recourse, case, frozen_catalog,
                 master, optimize_model, read, run, spend)
from direct_de import add_direct
from prepare import explicit_classes
from reference import peak_bytes


def benchmark(method):
    SOURCE.init()
    coords = Coordinates()
    c = case(2, "G2_N32")
    ids, mult, ranks = explicit_classes(coords)
    codes = list(map(int, ids[(mult[:3].sum(axis=0)>0) & (ranks<=c["threshold"])]))
    names = tuple(map(str,codes))
    assert len(names)==32 and names[0]=="0"
    profiles = {str(code):coords.profiles(coords.code_profile(code),SOURCE.OPENING) for code in codes}
    out = HERE / "finite" / method
    out.mkdir(parents=True,exist_ok=True)
    started = perf_counter()
    if method == "Implicit":
        run(2, "G2_N32")
        r = read(HERE / "outer/G2_N32/result.json")
        runs = [i["oracle"] for i in r["iterations"]]+[r["final_oracle"]]
        row = dict(method=method, objective=r["objective"], policy=r["policy"],
                   iterations=len(r["iterations"]), master_blocks=len(r["selected"]),
                   direct_blocks=0, separation_milps=sum(i["total_full_milp"] for i in runs[:-1]),
                   final_verification_milps=runs[-1]["total_full_milp"])
    else:
        calls, solver = [], None
        with SOURCE.env() as env:
            def fixed(x, tag):
                nonlocal solver
                if solver is not None:
                    calls.extend(solver.calls)
                    solver.close()
                solver = Recourse(env,SOURCE.BASE,SOURCE.OPENING,coords,x,out / tag)
                return solver

            def pointwise(name,x,tag):
                if solver is None or solver.policy != x or solver.directory.name != tag:
                    fixed(x,tag)
                return solver.solve(coords.code_profile(int(name)),f"rhs_{name}").q

            def solve_master(active,k):
                return master(env, profiles, active, out / f"master_{k:02d}.log")

            try:
                if method == "Direct":
                    with gp.Model(env=env) as model:
                        add_direct(model,coords,codes)
                        q,vector,metrics=optimize_model(model,out / "direct.log",seconds=420)
                        x=tuple(map(int,vector[:3]))
                        spend(x)
                    results = {n:pointwise(n,x,"verify") for n in names}
                    assert q==min(results.values())
                    row=dict(method=method,objective=q,policy=x,iterations=0,master_blocks=0,direct_blocks=len(codes),
                             separation_milps=0,final_verification_milps=len(codes),direct=metrics)
                else:
                    if method=="Plain":
                        result=plain_ccg.generate(names,("0",),solve_master,pointwise)
                        n=sum(len(names) for _ in result.iterations)
                    else:
                        prefix=e4_ccg.Prefix(SOURCE.BASE)
                        oracle_calls=[]
                        def oracle(x,k):
                            current=fixed(x,f"oracle_{k:02d}")
                            def evaluate(name,profile,policy):
                                assert current.policy == policy and profile==profiles[name]
                                return current.solve(coords.code_profile(int(name)),f"rhs_{name}").q, {}
                            ans=e4_ccg.separate(profiles,prefix,x,evaluate)
                            oracle_calls.append(ans.individual_solves+ans.common_solves)
                            return ans
                        result=e4_ccg.generate(names,("0",),solve_master,oracle,pointwise)
                        n=sum(oracle_calls)
                    row=dict(method=method,objective=result.objective,policy=result.policy,
                             iterations=len(result.iterations),master_blocks=len(result.selected),direct_blocks=0,
                             separation_milps=n,final_verification_milps=len(result.verified_services))
            finally:
                if solver is not None:
                    calls.extend(solver.calls)
                    solver.close()
            frozen_catalog.dump(out / "fixed_calls.json",calls)
    row.update(domain="D3_G2_N32",rhs_count=len(codes),rhs_ids=codes,initial_rhs=0,budget=str(BUDGET),
               seconds=perf_counter()-started,peak_bytes=peak_bytes())
    frozen_catalog.dump(out / "result.json",row)
    print(method,row["objective"],row["policy"],row["seconds"],flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("method",choices=("Direct","Plain","BTB","Implicit"))
    benchmark(p.parse_args().method)
