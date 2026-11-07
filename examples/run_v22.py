"""Gated V2.2 micro certification. Run python -m examples.run_v22 from the repository root."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import gurobipy as gp
from prefab_v21.examples import micro
from prefab_v21 import solvers as original
from prefab_v22.examples import extend, no_value, time_bottleneck, flexibility
from prefab_v22 import solvers
from prefab_v22.model import StateView
from prefab_v21.cuts import certificates
from prefab_v21.model import TOL


def serial(value):
    if isinstance(value, dict):
        return {str(key): serial(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serial(item) for item in value]
    return value


def save(path, value):
    path.write_text(json.dumps(serial(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def gate(folder, label, selections):
    command = [sys.executable, "-m", "pytest", "-vv", *selections]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")
    (folder / f"{label}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}")
    return {"command": command, "exit": result.returncode, "summary": result.stdout.strip().splitlines()[-1]}


def measure(solve, folder):
    folder.mkdir(parents=True, exist_ok=False)
    tracemalloc.start()
    start = time.perf_counter()
    try:
        result = solve(directory=folder)
        result["python_peak_bytes"] = tracemalloc.get_traced_memory()[1]
        result["measured_seconds"] = time.perf_counter() - start
    finally:
        tracemalloc.stop()
    save(folder / "result.json", result)
    return result


def summary(result):
    leaves = []
    def visit(node):
        if isinstance(node, dict):
            if "solver_seconds" in node:
                leaves.append(node)
            for key, value in node.items():
                if key not in ("flows", "plan"):
                    visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(result)
    return {
        "status": result["status"], "certified": result["certified"],
        "objective": result.get("objective"), "lb": result.get("lb"), "ub": result.get("ub"),
        "gap": result.get("gap"), "seconds": result["measured_seconds"],
        "solver_seconds": sum(model["solver_seconds"] for model in leaves),
        "python_peak_bytes": result["python_peak_bytes"],
        "gurobi_environment_peak_gb": max((model["peak_gb"] for model in leaves), default=0),
        "max_residual": max((model.get("residual", 0) for model in leaves), default=0),
        "worst_gap": result.get("worst", result.get("separation", {}).get("worst")),
        "iterations": result.get("iterations", 1), "plan": result.get("plan"),
    }


def preserved_hashes():
    tracked = subprocess.check_output(["git", "ls-tree", "-rz", "--name-only", "e46bb52"], cwd=ROOT).decode("utf-8").split("\0")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in tracked if name and (ROOT / name).is_file()}


def check_exact(a, b, expected=None):
    assert a["certified"] and b["certified"]
    assert abs(a["objective"] - b["objective"]) <= TOL
    for result in (a, b):
        assert result["status"] == "OPTIMAL"
        assert abs(result["objective"] - result["lb"]) <= TOL
        assert result["ub"] is not None and abs(result["objective"] - result["ub"]) <= TOL
        if expected is not None:
            assert abs(result["objective"] - expected) <= TOL


def strategy(d, name):
    candidate = deepcopy(d)
    if name in ("E2",):
        candidate.base.p["X"] = dict.fromkeys(candidate.base.p["X"], 0)
    if name in ("E1", "E4"):
        candidate.base.p["Rmax"] = dict.fromkeys(candidate.base.p["Rmax"], 0)
    pre = {(m,): 0 for m in candidate.M} if name in ("E1", "E2", "E3") else None
    return candidate, pre


def main():
    folder = ROOT / "artifacts" / f"v22_{datetime.now():%Y%m%d_%H%M%S}"
    folder.mkdir(parents=True, exist_ok=False)
    evidence = {
        "baseline_commit": "e46bb52c71a67ac9d33e8e1970c040fa41ff2895",
        "run": str(folder), "python": sys.version, "platform": platform.platform(),
        "cpu": platform.processor(), "gurobi": gp.gurobi.version(),
        "seed": 20261107, "tolerance": TOL, "formal_experiments_enabled": False,
        "input_spec_sha256": hashlib.sha256(
            (ROOT / "docs/specs/v22_preassembly_instruction.md").read_bytes()).hexdigest(),
    }
    before = preserved_hashes()
    save(folder / "baseline_hashes.json", before)
    save(folder / "manifest.json", evidence)
    evidence["original_69"] = gate(folder, "v21_regression", [
        "tests/test_v1.py", "tests/test_acceptance.py", "tests/test_v21.py"])
    evidence["base_tests"] = gate(folder, "v22_base_tests", [
        "tests/test_v22.py", "-k", "not reproved"])
    regression = []
    for three in (False, True):
        d = extend(micro(three))
        save(folder / f"regression_{int(three)}_input.json", asdict(d))
        pre = {(m,): 0 for m in d.M}
        records = []
        for label, old_method, new_method in (
            ("direct", original.direct, solvers.direct), ("ccg", original.ccg, solvers.ccg)):
            a = measure(lambda **kw: old_method(d.base, **kw), folder / f"regression_{int(three)}" / f"old_{label}")
            b = measure(lambda **kw: new_method(d, fixed_pre=pre, **kw), folder / f"regression_{int(three)}" / f"new_{label}")
            check_exact(a, b, 8.92 if three else 3.12)
            records.append({"method": label, "original": summary(a), "v22_p0": summary(b)})
        regression.append({"three": three, "records": records})
    evidence["zero_preassembly_regression"] = regression
    cases = []
    definitions = (("no_value", no_value, 3.12), ("bottleneck", time_bottleneck, 3.27),
                   ("flexibility", flexibility, 5.89))
    for name, factory, expected in definitions:
        d = factory()
        save(folder / f"{name}_input.json", asdict(d))
        a = measure(lambda **kw: solvers.direct(d, **kw), folder / name / "A0")
        b = measure(lambda **kw: solvers.ccg(d, **kw), folder / name / "A1")
        check_exact(a, b, expected)
        # Rebuild the full extensive model at each returned complete first-stage plan.
        for label, result in (("direct", a), ("ccg", b)):
            replay = solvers.run_model(d, solvers.vertices(d), fixed=result["plan"],
                                       logfile=folder / name / f"fixed_plan_{label}.log")
            assert replay["certified"] and abs(replay["objective"]-expected) <= TOL
            save(folder / name / f"fixed_plan_{label}.json", replay)
        cases.append({"name": name, "A0": summary(a), "A1": summary(b)})
    evidence["cases"] = cases
    evidence["base_status"] = "PASS_V22_BASE_EXACT"
    save(folder / "manifest.json", evidence)
    evidence["cut_tests"] = gate(folder, "v22_cut_tests", ["tests/test_v22.py", "-k", "reproved"])
    cut_runs = []
    for name, factory, expected in definitions:
        d = factory()
        result = measure(lambda **kw: solvers.ccg(d, cuts=True, **kw), folder / name / "cuts")
        assert result["certified"] and abs(result["objective"]-expected) <= TOL
        save(folder / name / "cut_certificates.json", [
            {"certificate": cert, "risk": risk} for cert in certificates(StateView(d, result["plan"]["p"]))
            for risk in solvers.vertices(d)])
        cut_runs.append({"name": name, **summary(result)})
    evidence["cut_runs"] = cut_runs
    evidence["cut_status"] = "PASS_V22_CUT_VALID"
    save(folder / "manifest.json", evidence)
    ablation = []
    for name, factory, _ in definitions:
        for label in ("E1", "E2", "E3", "E4", "E5"):
            d, pre = strategy(factory(), label)
            save(folder / f"{name}_{label}_input.json", asdict(d))
            a = measure(lambda **kw: solvers.direct(d, fixed_pre=pre, **kw), folder / name / label / "A0")
            b = measure(lambda **kw: solvers.ccg(d, fixed_pre=pre, **kw), folder / name / label / "A1")
            if a["status"] == "INFEASIBLE":
                assert b["status"] == "INFEASIBLE"
            else:
                check_exact(a, b)
            ablation.append({"case": name, "strategy": label, "A0": summary(a), "A1": summary(b)})
    evidence["strategy_ablation"] = ablation
    evidence["full_tests"] = gate(folder, "pytest_full", [])
    after = preserved_hashes()
    assert before == after, "V2.1 baseline contents changed"
    evidence["baseline_files_preserved"] = len(before)
    evidence["source_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [*(ROOT / "src/prefab_v22").glob("*.py"), ROOT / "tests/test_v22.py", Path(__file__)]
    }
    evidence["model_status"] = "PASS_V22_MODEL_IMPLEMENTED"
    save(folder / "manifest.json", evidence)
    print(json.dumps(serial(evidence), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
