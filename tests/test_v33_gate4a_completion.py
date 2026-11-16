import importlib.util
from pathlib import Path


def test_independent_strict_improvement_probe():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("completion_run", root/"experiments/v33_gate4a_completion/run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with module.gp.Env(empty=True) as env:
        env.setParam("OutputFlag",0)
        env.start()
        with module.gp.Model(env=env) as model:
            x=model.addVar(vtype=module.GRB.INTEGER, lb=7)
            assert module.probe(model,3*x,"improve",21,"test")["solver_status"]=="INFEASIBLE"
            row=module.probe(model,3*x,"target",21,"test")
            assert row["solver_status"]=="OPTIMAL" and module.quality(row) and x.X==7
