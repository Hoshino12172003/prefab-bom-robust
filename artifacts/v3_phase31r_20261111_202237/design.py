"""Multi-BOM stress design for the frozen historical V3 model."""
from dataclasses import dataclass
from fractions import Fraction as F
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIOR=ROOT/"artifacts/v3_phase31_20261111_193210"
PHASE30=ROOT/"artifacts/v3_phase30_20261111_104032"
PERIODS=tuple(range(61,75))
COSTS=(F(1),F(27,19),F(297,190))
KS=(215,429,644,858,1073)
SOURCE=Path("external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip")
LABEL="STRESS_TEST_ONLY"
E_ARC=("engine-supplier_prod","engine-supplier_inv")
G_ARC=("gear-supplier_inv","zp7")
S_ARC=("seat-supplier_inv","zp7")
B_PROD=("battery-supplier_prod","battery-supplier_inv")
B_SHIP=("battery-supplier_inv","zp7")
ARCS={"B_PROD":B_PROD,"B_SHIP":B_SHIP,"ENGINE":E_ARC,"GEAR":G_ARC,"SEAT":S_ARC}


@dataclass(frozen=True)
class Event:
    resource: str
    start: int
    duration: int
    severity: F = F(1,2)


@dataclass(frozen=True)
class Scenario:
    name: str
    events: tuple
    isolated: tuple = ()

    @property
    def exposure(self):
        return sum(e.duration for e in self.events)

    def validate(self):
        names={e.resource for e in self.events}
        assert len(names)==len(self.events)
        for e in self.events:
            assert e.resource in (*ARCS,"B_RECEIPT")
            assert 0<e.severity<=1 and e.duration>0 and e.start in PERIODS
            assert e.start+e.duration-1<=PERIODS[-1]


def scenarios():
    singles={
        "B_RECEIPT_1":Event("B_RECEIPT",66,1),
        "B_PROD_4":Event("B_PROD",61,4),
        "B_SHIP_4":Event("B_SHIP",64,4),
        "E_1":Event("ENGINE",61,1),
        "G_1":Event("GEAR",61,1),
        "S_1":Event("SEAT",61,1),
        "E_4":Event("ENGINE",64,4),
        "G_4":Event("GEAR",64,4),
        "S_4":Event("SEAT",64,4),
        "S_7":Event("SEAT",61,7,F(1,4)),
        "E_11":Event("ENGINE",61,11,F(3,4)),
    }
    joint={
        "BE":("B_RECEIPT_1","E_1"),"BG":("B_RECEIPT_1","G_1"),"BS":("B_RECEIPT_1","S_1"),
        "EG":("E_1","G_1"),"ES":("E_1","S_1"),"GS":("G_1","S_1"),
        "BES":("B_RECEIPT_1","E_1","S_1"),"BGS":("B_RECEIPT_1","G_1","S_1"),
        "B_PROD_E_S":("B_PROD_4","E_1","S_1"),
    }
    result=[Scenario("NR",()),*(Scenario(key,(e,),(key,)) for key,e in singles.items()),
            *(Scenario(key,tuple(singles[p] for p in parts),parts) for key,parts in joint.items())]
    for s in result:
        s.validate()
    assert len(result)==21
    return result


def policies():
    for k in KS:
        budget=k*COSTS[1]
        yield k,f"K{k}_C",(int(budget),0,0)
        yield k,f"K{k}_T",(0,k,0)
        yield k,f"K{k}_O",(0,0,int(budget/COSTS[2]))
        yield k,f"K{k}_M",(int(budget/3),int(budget/(3*COSTS[1])),int(budget/(3*COSTS[2])))


def de_scenarios():
    # Equal two-resource exposure. Spread across release dates and two powertrain branches.
    return [Scenario(f"DE_{r}_{t}",(Event(r,t,1),Event("SEAT",t,1)))
            for t in (61,68,64,66,62,67,63,65) for r in ("ENGINE","GEAR")]


def overlap_scenarios():
    single={s.name:s.events[0] for s in scenarios() if len(s.events)==1}
    designs={
        "BS_OVERLAP":("B_RECEIPT_1","S_4"),
        "BG_OVERLAP":("B_RECEIPT_1","G_4"),
        "BGS_OVERLAP":("B_RECEIPT_1","G_4","S_1"),
    }
    result=[Scenario(name,tuple(single[p] for p in parts),parts) for name,parts in designs.items()]
    for s in result:
        s.validate()
    return result
