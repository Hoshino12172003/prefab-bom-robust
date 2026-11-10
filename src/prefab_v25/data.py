from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction

CELL = ("componment_battery1", "componment_battery2", "componment_battery3")
PACK = "BEV"
PROD = "battery-supplier_prod"
T1 = "battery-supplier_inv"
OEM = "zp7"
COMPONENT_ARC = ("battery-supplier_trans", PROD)
PRODUCTION_ARC = (PROD, T1)
TRANSPORT_ARC = (T1, OEM)
BATTERY_ARCS = frozenset((COMPONENT_ARC, PRODUCTION_ARC, TRANSPORT_ARC))
BUFFER_EFFECTS = (
    tuple(((PROD, item), amount) for item, amount in zip(CELL, (10, 6, 4))),
    (((T1, PACK), 1),),
    (((OEM, PACK), 1),),
)
BUFFER_NAMES = ("x_cell_kit", "x_t1_pack", "x_oem_pack")
KAPPA = Fraction(5, 21)


@dataclass(frozen=True)
class Order:
    vin: str
    node: str
    due: int
    bom: tuple
    weight: int = 1


@dataclass(frozen=True)
class Group:
    id: str
    orders: tuple[Order, ...]

    @property
    def representative(self):
        return self.orders[0]


def aggregate(orders, enabled=True):
    buckets = defaultdict(list)
    for order in orders:
        key = (order.node, order.due, order.weight, tuple(sorted(order.bom)))
        if not enabled:
            key += (order.vin,)
        buckets[key].append(order)
    return tuple(Group(f"G{i:04d}", tuple(members)) for i, members in enumerate(buckets.values()))


def expand(group, period_quantities):
    """Disaggregate integer group deliveries into distinct equivalent VINs."""
    if any(type(q) is not int or q < 0 for q in period_quantities.values()):
        raise ValueError("group delivery must be a nonnegative integer")
    if sum(period_quantities.values()) > len(group.orders):
        raise ValueError("group delivery exceeds its demand")
    members = iter(group.orders)
    return {next(members).vin: t for t, q in sorted(period_quantities.items()) for _ in range(q)}


@dataclass(frozen=True)
class Arc:
    origin: str
    destination: str
    lead: int
    capacity: dict[int, int]
    recipes: dict[str, tuple]

    @property
    def key(self):
        return self.origin, self.destination

    def capacity_units(self, period):
        factor = KAPPA if self.key in BATTERY_ARCS and 61 <= period <= 74 else Fraction(1)
        return factor, factor * self.capacity[period]


@dataclass(frozen=True)
class Network:
    periods: tuple[int, ...]
    arcs: tuple[Arc, ...]
    groups: tuple[Group, ...]
    initial: dict
    historical: tuple  # (origin, destination, item, dispatch period, quantity)
    external: tuple  # original nodes_inflow eligibility only
    product_caps: dict
    group_caps: dict
    inventory_bounds: dict
    source_sha256: str | None = None

    @property
    def demand_weight(self):
        return sum(len(g.orders) * g.representative.weight for g in self.groups)

    def state_keys(self):
        keys = set(self.initial) | set(self.external) | set(self.inventory_bounds)
        keys.update((dst, item) for _, dst, item, _, _ in self.historical)
        keys.update(key for effects in BUFFER_EFFECTS for key, _ in effects)
        keys.update((g.representative.node, g.id) for g in self.groups)
        for arc in self.arcs:
            for product, inputs in arc.recipes.items():
                keys.add((arc.destination, product))
                keys.update((arc.origin, child) for child, _ in inputs)
        return tuple(sorted(keys))


@dataclass(frozen=True)
class Scenario:
    name: str
    arrival: dict
    production: dict
    transport: dict

    def validate(self, periods):
        for mapping in (self.arrival, self.production, self.transport):
            if set(mapping) - set(periods) or any(not 0 <= Fraction(str(v)) <= 1 for v in mapping.values()):
                raise ValueError(f"invalid scenario profile {self.name}")

    def factor(self, arc_key, period):
        if arc_key == PRODUCTION_ARC:
            return Fraction(str(self.production.get(period, 1)))
        if arc_key == TRANSPORT_ARC:
            return Fraction(str(self.transport.get(period, 1)))
        return Fraction(1)


NOMINAL = Scenario("nominal", {}, {}, {})


def receipts(network, scenario):
    leads = {arc.key: arc.lead for arc in network.arcs}
    result = defaultdict(int)
    for origin, dest, item, dispatch, quantity in network.historical:
        if dispatch >= network.periods[0]:
            raise ValueError("historical flow is not a pre-window dispatch")
        period = dispatch + leads[origin, dest]
        if period not in network.periods:
            continue
        result[dest, item, period] += quantity
    for (dest, item, period), quantity in tuple(result.items()):
        if dest == PROD and item in CELL:
            usable = Fraction(str(scenario.arrival.get(period, 1))) * quantity
            if usable.denominator != 1:
                raise ValueError(f"fractional usable arrival for integer inventory: {item}, t={period}")
            result[dest, item, period] = int(usable)
    return dict(result)
