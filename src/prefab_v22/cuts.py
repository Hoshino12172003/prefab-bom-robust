"""Reproved stage-2 resource covers, using post-preassembly component stocks."""
from prefab_v21.cuts import certificates, expression, reachable_expression
from .model import StateView


def add_cuts(model, d, z, risks):
    view = StateView(d, z["p"])
    count = 0
    for certificate in certificates(view):
        for risk in risks:
            model.addConstr(expression(view,z,risk,certificate) >= certificate["lhs"],
                            name=f"v22_cover_{count}")
            model.addConstr(reachable_expression(view,z,risk,certificate) >= certificate["lhs"],
                            name=f"v22_time_{count}")
            count += 2
    return count
