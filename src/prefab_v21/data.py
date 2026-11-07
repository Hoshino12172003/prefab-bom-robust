"""Explicit, sparse V2.1 input schema. All examples are synthetic."""
from dataclasses import dataclass
from itertools import product
from math import isfinite


@dataclass
class Data:
    M: tuple
    J: tuple
    S: tuple
    V: tuple
    O: tuple
    K: tuple
    T: int
    family: dict
    node: dict
    E: set
    N: set
    NB: set
    SL: set
    LL: set
    EO: set
    p: dict
    leads: dict
    costs: dict
    lots: list
    units: dict
    enable_storage_capacity: bool = False

    @property
    def L(self):
        return ("a", *self.O)

    @property
    def periods(self):
        return range(1, self.T + 1)

    def domains(self):
        return {
            "R": self.N | self.NB, "S": self.E, "I": set(product(self.J, self.L)),
            "Wa": {(m,) for m in self.M}, "Wo": self.EO, "F": {(m,) for m in self.M},
            "t": self.N, "g": self.NB, "q": self.E, "z": self.SL, "move": self.LL,
            "a": {(m, "a") for m in self.M} | self.EO,
            "b": {(m,) for m in self.M}, "h": self.EO,
            "e": {(m,) for m in self.M}, "ell": {(m,) for m in self.M},
        }

    def stock(self, kind, *index):
        return sum(lot["amount"] for lot in self.lots
                   if lot["kind"] == kind and tuple(lot["index"]) == index)

    def val(self, group, *index):
        return self.p[group].get(index, 0.0)

    def zero(self):
        return {layer: dict.fromkeys(nodes, 0.0) for layer, nodes in (
            ("eta", self.S), ("xi", self.V), ("theta", self.O))}

    def validate(self):
        def require(condition, message):
            if not condition:
                raise ValueError(message)

        require(not self.enable_storage_capacity, "storage-capacity extension has no base certificate")
        require(type(self.T) is int and self.T >= 1, "positive integer horizon required")
        for label in ("M", "J", "S", "V", "K", "O"):
            values = getattr(self, label)
            require(len(set(values)) == len(values), f"duplicate {label}")
            require(label == "O" or bool(values), f"empty {label}")
        require("a" not in self.O, "internal and external locations must differ")
        require(set(self.family) == set(self.M) and set(self.family.values()) <= {"HV", "MV", "LV"},
                "product family mapping")
        require(set(self.node) == set(self.K) and set(self.node.values()) <= set(self.V), "T3 pool mapping")
        require(not (set(self.O) & set(self.S)), "T2/external shared entity needs a shared-risk extension")
        for arcs, allowed in (
            (self.E, set(product(self.S, self.J))), (self.N | self.NB, set(product(self.K, self.S))),
            (self.SL, {(s,j,l) for s,j in self.E for l in self.L}),
            (self.LL, {(j,l,ll) for j in self.J for l in self.L for ll in self.L if l != ll}),
            (self.EO, set(product(self.M, self.O))),
        ):
            require(arcs <= allowed, "illegal qualified arc")
        require(self.units == {"component": "component-unit", "product": "product-unit",
                               "resource": "pool-specific-unit", "time": "period",
                               "capacity": "work-unit", "money": "currency"}, "unit declaration")
        P = set(product(self.periods))
        expected = {
            "D": {(m,) for m in self.M}, "due": {(m,) for m in self.M},
            "A": set(product(self.J,self.M)), "A1": set(product(self.J,self.M)),
            "A2": set(product(self.J,self.M)), "a": self.E,
            "b": {(k,s,j) for k,s in self.N | self.NB for ss,j in self.E if ss == s},
            "K": {(s,t) for s in self.S for t in self.periods},
            "C": {(k,t) for k in self.K for t in self.periods},
            "G": {(k,t) for k in self.K for t in self.periods},
            "P1": P, "P2": P, "PO": {(o,t) for o in self.O for t in self.periods},
            "tau1": {(m,) for m in self.M}, "tau2": {(m,) for m in self.M}, "tauO": self.EO,
            "eps": {(s,) for s in self.S}, "delta": {(k,) for k in self.K},
            "chi": {(o,) for o in self.O}, "alpha": {(h,) for h in set(self.family.values())},
            "X": set(product(self.J,self.L)), "Rmax": {(k,) for k in self.K},
            "cI": set(product(self.J,self.L)), "f": {(k,) for k in self.K}, "cR": {(k,) for k in self.K},
            "Bpre": {()}, "Eop": {()}, "Gamma2": {()}, "Gamma3": {()}, "GammaO": {()},
        }
        require(set(self.p) == set(expected), "missing or unknown parameter group")
        for group, keys in expected.items():
            require(set(self.p[group]) == keys, f"{group} dimensions")
            require(all(isfinite(v) and v >= 0 for v in self.p[group].values()), f"{group} finite nonnegative")
        for group in ("eps", "delta", "chi", "alpha"):
            require(all(v <= 1 for v in self.p[group].values()), f"{group} range")
        for m in self.M:
            due = self.val("due", m)
            require(type(due) is int and 1 <= due <= self.T, "deadline outside horizon")
        for j,m in product(self.J,self.M):
            require(abs(self.val("A1",j,m)+self.val("A2",j,m)-self.val("A",j,m)) <= 1e-10, "BOM split")
        expected_leads = {"t": self.N, "g": self.NB, "z": self.SL, "move": self.LL, "h": self.EO,
                          "e": {(m,) for m in self.M}}
        require(set(self.leads) == set(expected_leads), "lead groups")
        for group, keys in expected_leads.items():
            require(set(self.leads[group]) == keys, "lead indices")
            require(all(type(v) is int and v >= (0 if group == "e" else 1)
                        for v in self.leads[group].values()), "positive cross-node lead required")
        domains = self.domains()
        cost_groups = {"q", "g", "z", "move", "a", "b", "h", "e", "R", "S", "I", "Wa", "Wo", "F"}
        require(set(self.costs) == cost_groups, "cost groups")
        for group in cost_groups:
            require(set(self.costs[group]) == domains[group], f"{group} cost indices")
            require(all(isfinite(c) and c >= 0 for c in self.costs[group].values()), "cost values")
        ids = set()
        for lot in self.lots:
            require(lot["id"] not in ids, "duplicate physical lot")
            ids.add(lot["id"])
            kind, idx = lot["kind"], tuple(lot["index"])
            require(kind in {"R","S","I","Wa","Wo","F","P3","P2","PW","PF"}, "stock kind")
            base = kind[1:] if kind.startswith("P") else kind
            target = {"3": "R", "2": "I", "W": "Wa"}.get(base, base)
            require(target in {"R","S","I","Wa","Wo","F"}, "stock category")
            require(isfinite(lot["amount"]) and lot["amount"] >= 0, "lot quantity")
            if kind.startswith("P"):
                require(len(idx) >= 2 and type(idx[-1]) is int and idx[-1] in self.periods, "pipeline period")
                require(idx[:-1] in domains[target], "pipeline indices")
                if kind == "PF":
                    require(idx[-1] <= self.val("due", idx[0]), "late irrevocable customer delivery")
            else:
                require(idx in domains[target], "initial inventory indices")
        for m in self.M:
            require(sum(self.stock("PF",m,t) for t in self.periods) <= self.val("D",m),
                    "irrevocable customer deliveries exceed order")


def zero_plan(d):
    return {"x": dict.fromkeys(d.domains()["I"], 0.0),
            "y": {(k,): 0 for k in d.K}, "r": {(k,): 0.0 for k in d.K}}
