"""Independent, streamed 355-block deterministic equivalent for Gamma=1."""

import argparse
import gzip
import os
import re
import shutil
import subprocess
from time import perf_counter

import gurobipy as gp
import numpy as np
import psutil
from gurobipy import GRB

from prefab_v3.base import Weights
from prefab_v3.interface import add_stage_one
from prefab_v3.robust import protection_inventory

from run import HERE, ROOT, SOURCE, COSTS, BUDGET, Coordinates, Recourse, frozen_catalog, read, spend


OUT = HERE / "gamma1_de"
SHARED = ("x_C", "x_T", "x_O", "eta")
BLOCK = 75810
SENSE = {"=":"E", "<":"L", ">":"G"}


def add_direct(model, coords, codes):
    base = SOURCE.BASE
    x = add_stage_one(model, COSTS, BUDGET)
    eta = model.addVar(ub=base.network.demand_weight, vtype=GRB.INTEGER, name="eta")
    due = {g.id:g.representative.due for g in base.network.groups}
    for i, code in enumerate(codes):
        arrivals, factors = coords.profiles(coords.code_profile(code), SOURCE.OPENING)
        b = SOURCE.add_block(model, base, f"omega{i}", Weights(0,0,0,0,0), reschedule=True,
                             fixed_receipts=arrivals, arc_factors=factors, protection=protection_inventory(x))
        model.addConstr(eta <= gp.quicksum(var for (group, t), var in b.outflow.items() if t <= due[group]))
    model.setObjective(eta, GRB.MAXIMIZE)
    model.update()


class Template:
    def __init__(self, env, coords):
        with gp.Model(env=env) as model:
            add_direct(model, coords, [0])
            self.a, self.h, self.sense = SOURCE.matrix_rows(model)
            self.lb, self.ub = (np.array(model.getAttr(k)) for k in ("LB","UB"))
            assert model.NumVars == model.NumIntVars == BLOCK+4
            assert model.ModelSense == GRB.MAXIMIZE and model.getAttr("Obj")[:4] == [0,0,0,1]
        check = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, (0,0,0), OUT / "matrix")
        try:
            assert (check.matrix != self.a[1:-1,4:]).nnz == 0
            assert np.array_equal(self.h[1:-1], check.nominal_rhs)
            self.risk_rows = 1+check.rows
            self.score_idx = check.objective_idx
        finally:
            check.close()
        self.coords = coords

    def rhs(self, code):
        h = self.h.copy()
        h[self.risk_rows] += np.array(self.coords.code_profile(code)) - self.coords.nominal
        return h

    def check(self, x, eta, code, vector):
        block = np.concatenate((x, [eta], vector))
        assert np.all(block >= self.lb) and np.all(block <= self.ub)
        lhs, h, sense = self.a @ block, self.rhs(code), self.sense
        assert np.all(lhs[sense=="="] == h[sense=="="])
        assert np.all(lhs[sense=="<"] <= h[sense=="<"])
        assert np.all(lhs[sense==">"] >= h[sense==">"])
        return int(vector[self.score_idx].sum())


def write_mps(path, t, codes):
    def row(j):
        return "budget" if j == 0 else f"r@_{j}"

    def bound(name, lo, hi):
        if lo == hi:
            return f" FX bd {name} {lo:.17g}\n"
        return (f" LO bd {name} {lo:.17g}\n" if lo else "") + (
            f" PL bd {name}\n" if hi >= GRB.INFINITY else f" UP bd {name} {hi:.17g}\n")

    csc = t.a.tocsc()
    rec_columns = []
    shared_columns = []
    for j in range(csc.shape[1]):
        name = SHARED[j] if j < 4 else f"v@_{j-4}"
        left, right = csc.indptr[j:j+2]
        pairs = [(row(i), f"{v:.17g}") for i,v in zip(csc.indices[left:right],csc.data[left:right],strict=True)]
        if j < 4:
            shared_columns.append(pairs)
        else:
            # Off-due shortfall columns are fixed to zero and have no nonzeros.
            if not pairs:
                assert t.lb[j] == t.ub[j] == 0
                rec_columns.append(f" {name} obj 0\n")
                continue
            rec_columns.append("".join(
                f" {name} {pairs[i][0]} {pairs[i][1]}" +
                (f" {pairs[i+1][0]} {pairs[i+1][1]}" if i+1 < len(pairs) else "") + "\n"
                for i in range(0,len(pairs),2)))
    column_block = "".join(rec_columns)
    row_block = "".join(f" {SENSE[t.sense[j]]} {row(j)}\n" for j in range(1,len(t.h)))
    bound_block = "".join(bound(f"v@_{j-4}", t.lb[j], t.ub[j]) for j in range(4,BLOCK+4))
    with gzip.open(path, "wt", encoding="ascii", newline="\n", compresslevel=1) as out:
        out.write("NAME FULL_GAMMA1_DE\nOBJSENSE\n MAX\nROWS\n N obj\n L budget\n")
        for i in range(len(codes)):
            out.write(row_block.replace("@",str(i)))
        out.write("COLUMNS\n M0 'MARKER' 'INTORG'\n")
        for j,name in enumerate(SHARED):
            if name == "eta":
                out.write(" eta obj 1\n")
            for row_name, v in shared_columns[j]:
                if row_name == "budget":
                    out.write(f" {name} budget {v}\n")
            for i in range(len(codes)):
                for row_name, v in shared_columns[j]:
                    if row_name != "budget":
                        out.write(f" {name} {row_name.replace('@',str(i))} {v}\n")
        for i in range(len(codes)):
            out.write(column_block.replace("@",str(i)))
            if (i+1) % 50 == 0:
                print("Direct DE columns serialized", i+1, "/",len(codes),flush=True)
        out.write(" M1 'MARKER' 'INTEND'\nRHS\n")
        out.write(f" rhs budget {t.h[0]:.17g}\n")
        for i,code in enumerate(codes):
            rhs = t.rhs(code)
            out.write("".join(f" rhs r{i}_{j} {rhs[j]:.17g}\n" for j in np.flatnonzero(rhs) if j))
        out.write("BOUNDS\n")
        for j,name in enumerate(SHARED):
            out.write(bound(name,t.lb[j],t.ub[j]))
        for i in range(len(codes)):
            out.write(bound_block.replace("@",str(i)))
        out.write("ENDATA\n")


def pilot(env, coords, template, codes):
    path = OUT / "pilot.mps.gz"
    write_mps(path, template, codes)
    with gp.read(os.path.relpath(path, ROOT), env=env) as parsed, gp.Model(env=env) as reference:
        add_direct(reference, coords, codes)
        a,h,s = SOURCE.matrix_rows(parsed)
        b,j,t = SOURCE.matrix_rows(reference)
        assert (a != b).nnz == 0 and np.array_equal(h,j) and np.array_equal(s,t)
        for key in ("LB","UB","Obj","VType"):
            assert parsed.getAttr(key) == reference.getAttr(key)
        assert parsed.ModelSense == reference.ModelSense == GRB.MAXIMIZE
        return dict(rows=parsed.NumConstrs, cols=parsed.NumVars, nnz=parsed.NumNZs, coefficient_differences=0)


def build(coords, template, codes):
    started = perf_counter()
    mps = OUT / "full.mps.gz"
    with SOURCE.env() as env:
        check = pilot(env,coords,template,[0,16106127360])
    write_mps(mps,template,codes)
    result = dict(path=mps.name, sha256=frozen_catalog.digest(mps), matrix_pilot=check, blocks=len(codes),
                  rows=23020*len(codes)+1, cols=BLOCK*len(codes)+4,
                  nnz=(template.a.nnz-3)*len(codes)+3, build_seconds=perf_counter()-started, ordered_rhs=codes)
    frozen_catalog.dump(OUT / "model_identity.json", result)
    print("Full Direct DE built", result["rows"], result["cols"], result["nnz"], flush=True)


def write_start(t, codes):
    summary = read(HERE / "gamma1_enum/summary.json")
    x, eta = tuple(summary["policy"]), summary["worst"]
    vectors = {}
    for i in range(summary["workers"]):
        with np.load(HERE / f"gamma1_enum/part_{i}/vectors.npz") as a:
            vectors.update(zip(map(int,a["rhs"]),a["vectors"],strict=True))
    assert set(vectors) == set(codes)
    path = OUT / "full_start.mst.gz"
    with gzip.open(path,"wt",encoding="ascii",newline="\n",compresslevel=1) as out:
        out.write("".join(f"{n} {v}\n" for n,v in zip(SHARED,(*x,eta),strict=True)))
        service = []
        for i,code in enumerate(codes):
            vector = vectors[code]
            service.append(t.check(x,eta,code,vector))
            out.write("".join(f"v{i}_{j} {v}\n" for j,v in enumerate(vector)))
    assert min(service) == eta
    frozen_catalog.dump(OUT / "feasible_start.json", dict(policy=x, objective=eta,
        full_blocks_matrix_verified=len(codes), matrix_residual=0, sha256=frozen_catalog.digest(path)))
    return path


def check_solution(path, t, codes):
    raw = np.zeros((len(codes),BLOCK),dtype=np.int32)
    xeta = dict.fromkeys(SHARED,0)
    with gzip.open(path,"rt",encoding="ascii") as solution:
        for line in solution:
            if not line.strip() or line.startswith("#"):
                continue
            name,value = line.split()
            value = float(value)
            integer = round(value)
            assert abs(integer-value) <= 1e-7
            if name in xeta:
                xeta[name] = integer
            elif integer:
                i,j = map(int,name[1:].split("_"))
                raw[i,j] = integer
    x, eta = tuple(xeta[n] for n in SHARED[:3]), xeta["eta"]
    spend(x)
    services = [t.check(x,eta,code,v) for code,v in zip(codes,raw,strict=True)]
    assert min(services) == eta
    return dict(policy=x, objective=eta, matrix_residual=0, verified_blocks=len(services))


def solve(t, codes, attempt="initial"):
    identity = read(OUT / "model_identity.json")
    assert identity["ordered_rhs"] == codes
    mps = OUT / identity["path"]
    assert frozen_catalog.digest(mps) == identity["sha256"]
    if attempt == "initial":
        start = write_start(t,codes)
        target = OUT
    else:
        target = OUT / attempt
        target.mkdir(exist_ok=True)
        start = OUT / "full_start.mst.gz"
        assert frozen_catalog.digest(start) == read(OUT / "feasible_start.json")["sha256"]
    solution = target / "full.sol.gz"
    cli = shutil.which("gurobi_cl")
    assert cli
    params = ["Threads=1","Seed=20261110","MIPGap=0","MIPGapAbs=0","FeasibilityTol=1e-9",
              "IntFeasTol=1e-9","OptimalityTol=1e-9","TimeLimit=900","MemLimit=11","SoftMemLimit=9.5"]
    if attempt == "memory_retry":
        params[-2:] = ["MemLimit=15.5","SoftMemLimit=14","Symmetry=0","Aggregate=0","PrePasses=2"]
    if attempt == "conservative_retry":
        params[-2:] = ["MemLimit=17","SoftMemLimit=15","Symmetry=0","Aggregate=0",
                       "Presolve=1","PrePasses=1","PreSparsify=0","Method=1"]
    command = [cli,*params,"LogFile=optimizer.log",f"InputFile={os.path.relpath(start,target)}",
               f"ResultFile={solution.name}",os.path.relpath(mps,target)]
    frozen_catalog.dump(target / "command.json",command)
    peak, killed = 0, None
    started = perf_counter()
    with (target / "console.log").open("w",encoding="utf-8") as log:
        process = subprocess.Popen(command,cwd=target,stdout=log,stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        monitor = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                memory = monitor.memory_info()
                peak = max(peak,getattr(memory,"peak_wset",memory.rss))
                if psutil.virtual_memory().available < 1_500_000_000:
                    killed = "HOST_MEMORY_RESERVE"
                    process.terminate()
                    break
                process.wait(timeout=2)
            except (subprocess.TimeoutExpired,psutil.NoSuchProcess):
                pass
        rc = process.wait()
    log = (target / "console.log").read_text(encoding="utf-8",errors="replace")
    dims = re.search(r"Optimize a model with ([\d,]+) rows, ([\d,]+) columns and ([\d,]+) nonzeros",log)
    if dims:
        assert tuple(int(v.replace(",","")) for v in dims.groups()) == (
            identity["rows"],identity["cols"],identity["nnz"])
    best = re.search(r"Best objective\s+([\d.e+-]+), best bound\s+([\d.e+-]+), gap\s+([\d.]+)%",log,re.I)
    optimal = bool(dims and best and rc == 0 and "Optimal solution found" in log)
    error = re.search(r"Error (\d+): ([^\r\n]+)",log)
    record = dict(monolithic_gurobi_optimal=optimal, cli_exit=rc, aborted=killed,
        start_accepted="Loaded user MIP start with objective" in log, solver_seconds_wall=perf_counter()-started,
        peak_bytes=peak, model_dimensions_confirmed=bool(dims),
        solver_error=error.group(0) if error else None,
        solve_log=(target / "console.log").relative_to(HERE).as_posix())
    if best:
        record.update(objval=float(best[1]),objbound=float(best[2]),mip_gap_percent=float(best[3]))
    if optimal:
        assert record["objval"] == record["objbound"] and record["mip_gap_percent"] == 0
        assert solution.exists()
        record.update(check_solution(solution,t,codes))
        assert record["objective"] == record["objval"]
    frozen_catalog.dump(target / "solver_result.json",record)
    print("Direct DE result:",record,flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode",choices=("build","solve","memory_retry","conservative_retry"))
    args = parser.parse_args()
    SOURCE.init()
    coords = Coordinates()
    codes = sorted({0,*(a.code for a in coords.atoms)})
    assert len(codes) == 355
    with SOURCE.env() as env:
        template = Template(env,coords)
    if args.mode == "build":
        build(coords,template,codes)
    else:
        solve(template,codes,"initial" if args.mode == "solve" else args.mode)
