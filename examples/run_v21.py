"""Actual gated certification. python -m examples.run_v21"""
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import gurobipy as gp
from prefab_v21.examples import micro
from prefab_v21.solvers import direct, ccg, vertices, phase1
from prefab_v21.model import TOL


def serial(value):
    if isinstance(value,dict):
        return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list,set)):
        return [serial(v) for v in value]
    return value


def save(path,value):
    path.write_text(json.dumps(serial(value),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")


def test_gate(folder,label,selection):
    command=[sys.executable,"-m","pytest","-vv",*selection]
    process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace")
    (folder/f"{label}.txt").write_text(process.stdout+process.stderr,encoding="utf-8")
    if process.returncode:
        raise RuntimeError(f"{label} exited {process.returncode}")
    return {"command":command,"exit":process.returncode,"summary":process.stdout.strip().splitlines()[-1]}


def measure(function,folder):
    folder.mkdir(parents=True,exist_ok=True)
    tracemalloc.start()
    try:
        result=function(directory=folder)
        peak=tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    result["python_peak_bytes"]=peak
    save(folder/"result.json",result)
    return result


def stats(result):
    models=[]
    def collect(node):
        if isinstance(node,dict):
            if "solver_seconds" in node:
                models.append(node)
            for key,value in node.items():
                if key not in {"flows","plan"}:
                    collect(value)
        elif isinstance(node,list):
            for value in node: collect(value)
    collect(result)
    return {"status":result["status"],"certified":result["certified"],
            "objective":result.get("objective"),"lb":result.get("lb"),"ub":result.get("ub"),
            "gap":result.get("gap"),"seconds":result.get("total_seconds",result.get("wall_seconds")),
            "solver_seconds":sum(v["solver_seconds"] for v in models),
            "separation_seconds":sum(v["solver_seconds"] for v in models if v.get("capacity_duals") is not None),
            "gurobi_peak_gb":max((v["peak_gb"] for v in models),default=0),
            "python_peak_bytes":result["python_peak_bytes"],
            "max_residual":max((v.get("residual",0) for v in models),default=0),
            "iterations":result.get("iterations",1),
            "scenarios":len(result["flows"])-1 if "flows" in result else len(result.get("history",[])),
            "LP_models":sum("capacity_duals" in v for v in models)}


def main():
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    folder=ROOT/"artifacts"/f"v21_{stamp}"
    folder.mkdir(parents=True,exist_ok=False)
    evidence={"run":str(folder),"python":sys.version,"platform":platform.platform(),
              "gurobi":gp.gurobi.version(),"seed":20261107,"tolerance":TOL,"formal_experiments_enabled":False}
    evidence["input_zip_sha256"]=hashlib.sha256((ROOT/"V2.1完整模型.zip").read_bytes()).hexdigest()
    save(folder/"manifest.json",evidence)
    evidence["base_tests"]=test_gate(folder,"G0_G5_tests",["-k","not G6"])
    records=[]
    for name,three,expected in (("single",False,3.12),("three_families",True,8.92)):
        d=micro(three)
        save(folder/f"{name}_input.json",asdict(d))
        a=measure(lambda **kw:direct(d,**kw),folder/name/"G4")
        b=measure(lambda **kw:ccg(d,**kw),folder/name/"G5")
        assert a["certified"] and b["certified"]
        assert max(abs(a["objective"]-expected),abs(b["objective"]-expected))<=TOL
        # Back-substitute both distinct first-stage plans through every risk vertex.
        for result in (a,b):
            for i,w in enumerate(vertices(d)):
                replay=phase1(d,result["plan"],w,logfile=folder/name/f"replay_{len(records)}_{i}.log")
                assert replay["certified"] and replay["objective"]<=TOL
                records.append({"case":name,"risk":w,"result":replay})
        evidence[name]={"A0":stats(a),"A1":stats(b)}
    save(folder/"independent_numeric_replays.json",records)
    evidence["base_status"]="PASS_V2_BASE_EXACT"
    save(folder/"manifest.json",evidence)
    # Only this successfully completed gate authorizes the following micro ablation.
    evidence["cut_tests"]=test_gate(folder,"G6_tests",["tests/test_v21.py","-k","G6"])
    evidence["cut_status"]="PASS_V2_CUT_VALID"
    paired=[]
    for three in (False,True):
        for repeat in range(3):
            d=micro(three)
            methods={
                "A0":lambda **kw:direct(d,**kw),
                "A1":lambda **kw:ccg(d,**kw),
                "A2":lambda **kw:ccg(d,cuts=True,**kw),
                "A3":lambda **kw:ccg(d,rank=True,**kw),
            }
            for method in list(methods)[repeat:]+list(methods)[:repeat]:
                result=measure(methods[method],folder/f"paired_{int(three)}_{repeat}"/method)
                assert result["certified"]
                assert abs(result["objective"]-(8.92 if three else 3.12))<=TOL
                paired.append({"three":three,"repeat":repeat,"method":method,**stats(result)})
    evidence["paired"]=paired
    evidence["full_tests"]=test_gate(folder,"pytest_full",[])
    evidence["algorithm_status"]="PARTIAL_V2"
    evidence["algorithm_reason"]="Only two synthetic micro instances. No stable incremental acceleration demonstrated."
    evidence["source_sha256"]={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                               for base in ("src/prefab_v21","tests") for p in (ROOT/base).glob("*.py")}
    save(folder/"manifest.json",evidence)
    print(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
