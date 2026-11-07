from prefab_v21.model import first_stage as original_first_stage
from prefab_v21.model import block as original_block


class StateView:
    """Read-only symbolic initial-state mapping into the unchanged recourse model."""

    def __init__(self, data, preassembly):
        self.base = data.base
        self.preassembly = preassembly

    def __getattr__(self, name):
        return getattr(self.base, name)

    def stock(self, kind, *index):
        amount = self.base.stock(kind, *index)
        if kind == "I" and index[1] == "a":
            return amount - sum(self.base.val("A1", index[0], m) * self.preassembly[m,]
                                for m in self.base.M)
        if kind == "Wa":
            return amount + self.preassembly[index[0],]
        return amount


def first_stage(model, d, fixed=None, fixed_pre=None):
    original_fixed = {k: fixed[k] for k in ("x", "y", "r")} if fixed is not None else None
    z, original_cost = original_first_stage(model, d.base, original_fixed)
    z["p"] = {}
    for m in d.M:
        limit = max(0, d.val("D", m) - d.stock("Wa", m))
        z["p"][m,] = model.addVar(ub=limit, name=f"preassembly[{m}]")
        if fixed is not None:
            model.addConstr(z["p"][m,] == fixed["p"][m,])
        if fixed_pre is not None:
            model.addConstr(z["p"][m,] == fixed_pre[m,])
    for j in d.J:
        model.addConstr(sum(d.val("A1", j, m) * z["p"][m,] for m in d.M)
                        <= d.stock("I", j, "a") + z["x"][j, "a"], name=f"pre_material[{j}]")
    model.addConstr(sum(d.tau_pre[m,] * z["p"][m,] for m in d.M) <= d.P_pre, name="pre_capacity")
    model.addConstr(sum(d.v_WIP[m,] * (d.stock("Wa", m) + z["p"][m,]) for m in d.M)
                    <= d.Wcap_pre, name="pre_WIP_space")
    pre_cost = sum((d.c_preasm[m,] + d.h_preWIP[m,]) * z["p"][m,] for m in d.M)
    return z, original_cost + pre_cost


def block(model, d, z, risk, mode, name):
    return original_block(model, StateView(d, z["p"]), z, risk, mode, name)
