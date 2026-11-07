from itertools import product
from .data import Data


def micro(three=False):
    """Fully declared synthetic data, positive transport leads, two complementary BOM stages."""
    products = ("HV","MV","LV") if three else ("HV",)
    d = Data(M=products,J=("A","B"),S=("s0","s1"),V=("v",),O=("o",),K=("k",),T=4,
             family={p:p for p in products},node={"k":"v"},
             E={("s0","B"),("s1","B")},N={("k","s0")},NB={("k","s1")},
             SL={("s0","B","a"),("s1","B","a")},LL={("A","a","o")},
             EO={(p,"o") for p in products},p={},leads={},costs={},lots=[],
             units={"component":"component-unit","product":"product-unit","resource":"pool-specific-unit",
                    "time":"period","capacity":"work-unit","money":"currency"})
    n=len(products)
    d.p = {
        "D":{(p,):1 for p in products}, "due":{(p,):4 for p in products},
        "A":{(j,p):1 for j,p in product(d.J,products)},
        "A1":{(j,p):int(j=="A") for j,p in product(d.J,products)},
        "A2":{(j,p):int(j=="B") for j,p in product(d.J,products)},
        "a":dict.fromkeys(d.E,1), "b":{("k",s,"B"):1 for s in d.S},
        "K":{(s,t):2*n if t==2 else 0 for s in d.S for t in d.periods},
        "C":{("k",t):n if t==1 else 0 for t in d.periods},
        "G":{("k",t):n if t==1 else 0 for t in d.periods},
        "P1":{(t,):1 if t==1 else 0 for t in d.periods},
        "P2":{(t,):n if t==3 else 0 for t in d.periods},
        "PO":{("o",t):2*n if t==2 else 0 for t in d.periods},
        "tau1":{(p,):1 for p in products},"tau2":{(p,):1 for p in products},
        "tauO":dict.fromkeys(d.EO,1),
        "eps":{(s,):1 for s in d.S},"delta":{("k",):1},"chi":{("o",):1},
        "alpha":{(p,):1 for p in products}, "X":{(j,l):n if (j,l)==("B","a") else 0 for j,l in product(d.J,d.L)},
        "Rmax":{("k",):n},"cI":dict.fromkeys(product(d.J,d.L),4),
        "f":{("k",):0.5},"cR":{("k",):1},"Bpre":{():20},"Eop":{():20},
        "Gamma2":{():0.5},"Gamma3":{():1},"GammaO":{():0.5},
    }
    domains=d.domains()
    d.leads={group:dict.fromkeys(domains[group],1) for group in ("t","g","z","move","h","e")}
    d.costs={group:dict.fromkeys(domains[group],{
        "q":1,"g":0.3,"z":0.2,"move":0.1,"a":0.1,"b":0.2,"h":0.2,"e":0.1,
    }.get(group,0.01)) for group in ("q","g","z","move","a","b","h","e","R","S","I","Wa","Wo","F")}
    d.lots=[{"id":"initial_A","kind":"I","index":("A","a"),"amount":n}]
    d.validate()
    return d
