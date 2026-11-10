from .data import (Arc, Network, Order, aggregate, CELL, PACK, PROD, T1, OEM,
                   COMPONENT_ARC, Scenario)

TOY_COSTS = (2, 3, 4)


def micro(aggregated=True):
    periods = tuple(range(61,65))
    destination = "zp8"
    orders = tuple(Order(f"micro-{i}",destination,due,((PACK,1),))
                   for i,due in enumerate((62,62,63,64)))
    groups = aggregate(orders, enabled=aggregated)
    arcs = (
        Arc(*COMPONENT_ARC,20,dict.fromkeys(periods,20),{item:((item,1),) for item in CELL}),
        Arc(PROD,T1,1,dict.fromkeys(periods,1),{PACK:tuple(zip(CELL,(10,6,4)))}),
        Arc(T1,OEM,1,dict.fromkeys(periods,1),{PACK:((PACK,1),)}),
        Arc(OEM,destination,0,dict.fromkeys(periods,2),{g.id:((PACK,1),) for g in groups}),
    )
    historical = tuple((*COMPONENT_ARC,item,41,q) for item,q in zip(CELL,(10,6,4)))
    return Network(periods,arcs,groups,{},historical,(),{},{},{})


def micro_risks():
    return (
        Scenario("L1_unusable_arrival",{61:0},{},{}),
        Scenario("L2_no_pack_production",{},dict.fromkeys(range(61,65),0),{}),
        Scenario("L3_no_pack_transport",{},{},dict.fromkeys(range(61,65),0)),
    )
