"""Structural exposure only; reachability never certifies feasible production."""
from collections import defaultdict
from functools import lru_cache
import heapq

from .schema import FeatureSpec

SPECS = tuple(FeatureSpec(name, "int64", unit, formula, "XLSB + pinned source_base") for name, unit, formula in (
    ("network_nodes", "location_count", "len(nodes)"),
    ("network_arcs", "arc_count", "len(arcs)"),
    ("network_recipes", "recipe_count", "sum(len(arc.recipes))"),
    ("network_recipe_inputs", "input_term_count", "sum(len(recipe))"),
    ("network_order_count", "vehicle", "sum(cohort sizes)"),
    ("network_configuration_count", "configuration_count", "distinct direct BOM signatures excluding due"),
    ("network_horizon", "period", "len(periods)"),
))


def extract(network):
    net = network.base.network
    return dict(zip((s.name for s in SPECS), (
        len(network.tables["nodes"]), len(net.arcs), sum(len(a.recipes) for a in net.arcs),
        sum(len(r) for a in net.arcs for r in a.recipes.values()), net.demand_weight,
        len({g.representative.bom for g in net.groups}), len(net.periods))))


@lru_cache(maxsize=4)
def state_graph(model_id, recipe_rows):
    # OR-propagation is potential impact from any consumed child, NOT an AND-feasibility test.
    edges = defaultdict(list)
    for origin, dest, output, child, lead in recipe_rows:
        edges[origin, child].append(((dest, output), lead))
    return edges


def reach(network, seeds):
    rows = tuple((a.origin, a.destination, p, child, a.lead)
                 for a in network.base.network.arcs for p, recipe in a.recipes.items() for child, _ in recipe)
    edges = state_graph(network.model_instance_id, rows)
    queue = [(t, k) for k, t in seeds.items()]
    heapq.heapify(queue)
    earliest = {}
    while queue:
        t, state = heapq.heappop(queue)
        if state in earliest:
            continue
        earliest[state] = t
        for dest, lead in edges.get(state, ()):
            if dest not in earliest:
                heapq.heappush(queue, (t+lead, dest))
    return earliest


def risk_reach(network, scenario):
    arcs = {a.key: a for a in network.base.network.arcs}
    seeds = {}
    for key, _ in scenario.changes:
        kind, i, j, t = key
        if kind == "receipt":
            seeds[i, j] = min(t, seeds.get((i, j), t))
        else:
            arc = arcs[i, j]
            for output in arc.recipes:
                k, arrival = (j, output), t+arc.lead
                seeds[k] = min(arrival, seeds.get(k, arrival))
    return reach(network, seeds)


def due_groups(network, earliest):
    return {g.id: g for g in network.base.network.groups
            if earliest.get((g.representative.node, g.id), float("inf")) <= g.representative.due}
