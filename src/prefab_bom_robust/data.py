from dataclasses import dataclass, field
from math import isfinite


Pair = tuple[str, str]
Triple = tuple[str, str, str]


@dataclass(frozen=True)
class FirstStagePlan:
    x: dict[str, float]
    y: dict[str, int]
    r: dict[str, float]


@dataclass
class ModelData:
    H: tuple[str, ...]
    M: tuple[str, ...]
    J: tuple[str, ...]
    S: tuple[str, ...]
    V: tuple[str, ...]
    K: tuple[str, ...]
    family: dict[str, str]
    pool_node: dict[str, str]
    E: set[Pair]
    N: set[Pair]
    B_arc: set[Pair]
    A: dict[Pair, float]
    D: dict[str, float]
    I0: dict[str, float]
    a: dict[Pair, float]
    b: dict[Triple, float]
    Kbar: dict[str, float]
    Cbar: dict[str, float]
    epsilon: dict[str, float]
    delta: dict[str, float]
    Xbar: dict[str, float]
    Rbar: dict[str, float]
    cI: dict[str, float]
    f: dict[str, float]
    cR: dict[str, float]
    cQ: dict[Pair, float]
    cA: dict[Pair, float]
    alpha: dict[str, float]
    tau: dict[str, float]
    P: float
    B_pre: float
    E_op: float
    Gamma2: float
    Gamma3: float
    name: str = "instance"

    def validate(self) -> None:
        errors: list[str] = []
        sets = {"H": self.H, "M": self.M, "J": self.J, "S": self.S, "V": self.V, "K": self.K}
        for label, values in sets.items():
            if not values or len(values) != len(set(values)):
                errors.append(f"{label} must be nonempty and unique")
        if set(self.family) != set(self.M) or any(h not in self.H for h in self.family.values()):
            errors.append("family must map every product to H")
        if set(self.pool_node) != set(self.K) or any(v not in self.V for v in self.pool_node.values()):
            errors.append("pool_node must map every pool to V")
        if not self.B_arc <= self.N:
            errors.append("B_arc must be a subset of N")
        if any(s not in self.S or j not in self.J for s, j in self.E):
            errors.append("E contains an unknown supplier/component")
        if any(k not in self.K or s not in self.S for k, s in self.N | self.B_arc):
            errors.append("N/B_arc contains an unknown pool/supplier")
        for (k, s, j), value in self.b.items():
            if value > 0 and ((s, j) not in self.E or (k, s) not in self.N):
                errors.append(f"positive b[{k},{s},{j}] lacks E and/or N qualification")
        required = [
            ("D", self.D, self.M), ("I0", self.I0, self.J), ("Kbar", self.Kbar, self.S),
            ("Cbar", self.Cbar, self.K), ("epsilon", self.epsilon, self.S),
            ("delta", self.delta, self.K), ("Xbar", self.Xbar, self.J),
            ("Rbar", self.Rbar, self.K), ("cI", self.cI, self.J), ("f", self.f, self.K),
            ("cR", self.cR, self.K), ("alpha", self.alpha, self.H), ("tau", self.tau, self.M),
        ]
        for label, mapping, keys in required:
            if set(mapping) != set(keys):
                errors.append(f"{label} keys do not match its index set")
            if any(not isfinite(v) for v in mapping.values()):
                errors.append(f"{label} contains a non-finite value")
        if any(v < 0 for label, mapping, _ in required for v in mapping.values() if label not in {"epsilon", "delta", "alpha"}):
            errors.append("capacities, demands, quantities, and costs must be nonnegative")
        if any(not 0 <= v <= 1 for mapping in (self.epsilon, self.delta, self.alpha) for v in mapping.values()):
            errors.append("epsilon, delta, and alpha must lie in [0,1]")
        for key in ((j, m) for j in self.J for m in self.M):
            if key not in self.A or self.A[key] < 0:
                errors.append(f"A missing or negative at {key}")
        for key in self.E:
            if key not in self.a or key not in self.cQ or self.a[key] < 0 or self.cQ[key] < 0:
                errors.append(f"a/cQ missing or negative at {key}")
        for key in self.B_arc:
            if key not in self.cA or self.cA[key] < 0:
                errors.append(f"cA missing or negative at {key}")
        if any(v < 0 or not isfinite(v) for v in (self.P, self.B_pre, self.E_op, self.Gamma2, self.Gamma3)):
            errors.append("scalar capacities and budgets must be finite and nonnegative")
        if self.Gamma2 > len(self.S) or self.Gamma3 > len(self.V):
            errors.append("risk budget cannot exceed the number of risk nodes")
        if errors:
            raise ValueError("; ".join(errors))

    def family_demand(self, h: str) -> float:
        return sum(self.D[m] for m in self.M if self.family[m] == h)

    def zero_scenario(self) -> tuple[dict[str, float], dict[str, float]]:
        return ({s: 0.0 for s in self.S}, {v: 0.0 for v in self.V})
