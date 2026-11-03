from .data import ModelData


def example_a() -> ModelData:
    """Two products, dedicated components, shared T3 pool; analytic investment = 4."""
    return ModelData(
        H=("HV", "LV"), M=("hv1", "lv1"), J=("jh", "jl"), S=("s1", "s2"), V=("v1",), K=("k1",),
        family={"hv1": "HV", "lv1": "LV"}, pool_node={"k1": "v1"},
        E={("s1", "jh"), ("s2", "jl")}, N={("k1", "s1"), ("k1", "s2")},
        B_arc={("k1", "s1"), ("k1", "s2")},
        A={("jh", "hv1"): 1, ("jh", "lv1"): 0, ("jl", "hv1"): 0, ("jl", "lv1"): 1},
        D={"hv1": 1, "lv1": 1}, I0={"jh": 0, "jl": 0},
        a={("s1", "jh"): 1, ("s2", "jl"): 1},
        b={("k1", "s1", "jh"): 1, ("k1", "s2", "jl"): 1},
        Kbar={"s1": 2, "s2": 2}, Cbar={"k1": 2}, epsilon={"s1": 0, "s2": 0}, delta={"k1": 1},
        Xbar={"jh": 1, "jl": 1}, Rbar={"k1": 2}, cI={"jh": 3, "jl": 3},
        f={"k1": 0}, cR={"k1": 2}, cQ={("s1", "jh"): 0, ("s2", "jl"): 0},
        cA={("k1", "s1"): 0, ("k1", "s2"): 0}, alpha={"HV": 1, "LV": 1},
        tau={"hv1": 1, "lv1": 1}, P=2, B_pre=10, E_op=10, Gamma2=0, Gamma3=1, name="example_a")


def example_b() -> ModelData:
    """One product and a fractional T3 budget; analytic investment = 0.5."""
    return ModelData(
        H=("HV",), M=("p",), J=("j",), S=("s",), V=("v",), K=("k",),
        family={"p": "HV"}, pool_node={"k": "v"}, E={("s", "j")}, N={("k", "s")}, B_arc={("k", "s")},
        A={("j", "p"): 1}, D={"p": 1}, I0={"j": 0}, a={("s", "j"): 1}, b={("k", "s", "j"): 1},
        Kbar={"s": 2}, Cbar={"k": 1}, epsilon={"s": 0}, delta={"k": 1}, Xbar={"j": 1}, Rbar={"k": 1},
        cI={"j": 2}, f={"k": 0}, cR={"k": 1}, cQ={("s", "j"): 0}, cA={("k", "s"): 0},
        alpha={"HV": 1}, tau={"p": 1}, P=1, B_pre=5, E_op=5, Gamma2=0, Gamma3=0.5, name="example_b")


def sufficient_inventory() -> ModelData:
    d = example_b()
    d.I0 = {"j": 1}; d.Gamma3 = 0; d.alpha = {"HV": 1}
    return d
