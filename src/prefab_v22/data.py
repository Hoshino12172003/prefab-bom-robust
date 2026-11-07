from dataclasses import dataclass
from math import isfinite


@dataclass
class Data:
    base: object
    tau_pre: dict
    P_pre: float
    Wcap_pre: float
    v_WIP: dict
    c_preasm: dict
    h_preWIP: dict
    available_before_risk: bool = True

    def __getattr__(self, name):
        # Preserve the exact V2.1 parameter and uncertainty interfaces.
        base = self.__dict__.get("base")
        if base is None:
            raise AttributeError(name)
        return getattr(base, name)

    def validate(self):
        self.base.validate()
        if not self.available_before_risk:
            raise ValueError("preassembly requires physically available pre-risk inventory")
        expected = {(m,) for m in self.M}
        for name in ("tau_pre", "v_WIP", "c_preasm", "h_preWIP"):
            mapping = getattr(self, name)
            if set(mapping) != expected:
                raise ValueError(f"{name} index mismatch")
            if any(not isfinite(v) or v < 0 for v in mapping.values()):
                raise ValueError(f"{name} must be finite and nonnegative")
        if any(v <= 0 for mapping in (self.tau_pre, self.v_WIP) for v in mapping.values()):
            raise ValueError("preassembly capacity and WIP space consumption must be positive")
        if any(not isfinite(v) or v < 0 for v in (self.P_pre, self.Wcap_pre)):
            raise ValueError("preassembly limits must be finite and nonnegative")
        initial_space = sum(self.v_WIP[m,] * self.stock("Wa", m) for m in self.M)
        if initial_space > self.Wcap_pre:
            raise ValueError("Wcap_pre must accommodate existing internal WIP so p=0 remains available")


def zero_plan(d):
    from prefab_v21.data import zero_plan as original
    return {**original(d.base), "p": {(m,): 0.0 for m in d.M}}
