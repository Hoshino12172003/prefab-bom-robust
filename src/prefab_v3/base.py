"""Source-case network, BOM compilation, and integer automotive recourse."""
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction

import gurobipy as gp
from gurobipy import GRB

from prefab_v25.data import Group, NOMINAL, OEM, receipts
from prefab_v25.source import compile_network

ASSEMBLY = (OEM, "zp8")


def operation_recipes(operations, arcs, items, individual):
    """Compile Eq. (4), including the source transport identity convention."""
    incoming = defaultdict(list)
    simultaneous = defaultdict(set)
    for node, input_group, output_group, units_in, units_out, alpha, beta in operations:
        if units_out <= 0 or beta not in (0, 1):
            raise ValueError("invalid source operation")
        incoming[node, output_group].append((input_group, units_in, units_out, alpha, beta))
        if alpha:
            simultaneous[node, input_group, alpha].add(output_group)
    by_group = defaultdict(list)
    for item, group in items.items():
        by_group[group].append(item)
    recipes = {}
    alpha_flows = defaultdict(list)
    for origin, destination, _, output_group in arcs:
        operations_here = incoming[origin, output_group]
        if not operations_here:
            raise ValueError("arc without an output operation")
        alphas = {r[3] for r in operations_here}
        if len(alphas) != 1:
            raise ValueError("alpha must be consistent for each node and output group")
        alpha, = alphas
        result = {}
        for output in by_group[output_group]:
            recipe = Counter()
            for input_group, units_in, units_out, alpha, beta in operations_here:
                bom_rows = individual.get(output, ())
                if input_group == output_group and beta == 1 and not any(
                        items[child] == input_group for child, _ in bom_rows):
                    if (units_in, units_out) != (1, 1):
                        raise ValueError("unidentified same-group identity operation")
                    inputs = ((output, 1),)
                elif beta == 1:
                    inputs = ((child, qty) for child, qty in bom_rows
                              if items[child] == input_group)
                else:
                    inputs = ((child, units_in) for child in by_group[input_group])
                sharing = len(simultaneous[origin, input_group, alpha]) if alpha else 1
                for child, qty in inputs:
                    recipe[child] += Fraction(qty) / (Fraction(units_out) * sharing)
            result[output] = tuple(sorted(recipe.items()))
            if alpha:
                normalization = sum(Fraction(r[2]) for r in operations_here)
                alpha_flows[origin, alpha].append(((origin, destination, output), normalization))
        recipes[origin, destination] = result
    return recipes, tuple(tuple(g) for g in alpha_flows.values() if len(g)>1)


@dataclass(frozen=True)
class Base:
    network: object
    products: dict
    sizes: dict
    alpha_flows: tuple


def source_base(tables, compress_vins=True):
    legacy, audit = compile_network(tables)
    groups = legacy.groups if compress_vins else tuple(
        Group(str(o.vin), (o,)) for g in legacy.groups for o in g.orders)
    products = {p: g for p,g,_ in tables["products"] if g!="car"}
    products.update((g.id,"car") for g in groups)
    sizes = {p: s for p,g,s in tables["products"] if g!="car"}
    sizes.update((g.id,0) for g in groups)
    individual = defaultdict(list)
    for mother, child, qty in tables["BOM"]:
        if mother != child and mother in products and products[mother] != "car":
            individual[mother].append((child,qty))
    individual.update((g.id,g.representative.bom) for g in groups)
    recipes, alpha = operation_recipes(tables["operations"], tables["arcs"], products, individual)
    arcs = tuple(replace(a, recipes=recipes[a.key]) for a in legacy.arcs)
    if compress_vins and arcs != legacy.arcs:
        raise ValueError("V3 BOM differs from verified source recipes")
    raw_initial = {(n,p):int(q) for n,p,q,*_ in tables["initial_inventories"]}
    network = replace(legacy, groups=groups, arcs=arcs, initial=raw_initial)
    network = replace(network,initial={k:raw_initial.get(k,0) for k in network.state_keys()})
    if not all(g.representative.node == ASSEMBLY[1] for g in groups):
        raise ValueError("vehicle-order node differs from the automotive formulation")
    return Base(network,products,sizes,alpha),audit


@dataclass(frozen=True)
class Weights:
    flow: int = 1
    inventory: int = 1
    shortfall: int = 3000
    deviation: int = 100
    unassigned: int = 200


@dataclass(frozen=True)
class Block:
    flow: object
    inventory: object
    external: object
    shortfall: object
    outflow: object
    unassigned: object
    components: dict
    regular_opening: dict
    protection_opening: dict
    receipts: dict

    @property
    def loss(self):
        return gp.quicksum(self.components.values())


def add_block(model, base, prefix, weights=Weights(), reschedule=True, *,
              regular=None, fixed_receipts=None, protection=None, arc_factors=None,
              external_limits=None, scheduled_equalities=None):
    """Build the full integer recourse block for one source or prospective scenario."""
    network = base.network
    periods = network.periods
    regular = network.initial if regular is None else regular
    fixed_receipts = receipts(network,NOMINAL) if fixed_receipts is None else fixed_receipts
    protection = {} if protection is None else protection
    arc_factors = {} if arc_factors is None else arc_factors
    external_limits = {} if external_limits is None else external_limits
    scheduled_equalities = {} if scheduled_equalities is None else scheduled_equalities
    groups = {g.id:g for g in network.groups}
    flow = model.addVars([(*a.key,p,t) for a in network.arcs for p in a.recipes for t in periods],
                         vtype=GRB.INTEGER,name=f"{prefix}_f")
    keys = sorted(set(network.state_keys())|regular.keys()|protection.keys()|
                  {(n,p) for n,p,_ in fixed_receipts})
    inventory = model.addVars([(n,p,t) for n,p in keys for t in periods],
                              vtype=GRB.INTEGER,name=f"{prefix}_inv")
    external = model.addVars([(*key,t) for key in network.external for t in periods],
                             vtype=GRB.INTEGER,name=f"{prefix}_in")
    order_keys = [(p,t) for p in groups for t in periods]
    shortfall = model.addVars(order_keys,vtype=GRB.INTEGER,name=f"{prefix}_os")
    outflow = model.addVars(order_keys,vtype=GRB.INTEGER,name=f"{prefix}_of")
    unassigned = model.addVars(periods,vtype=GRB.INTEGER,name=f"{prefix}_uc")
    changes = defaultdict(gp.LinExpr)
    for key,value in external_limits.items():
        external[key].UB=value
    for arc in network.arcs:
        for t in periods:
            raw_cap = arc.capacity[t]*arc_factors.get((*arc.key,t),1)
            total = gp.quicksum(flow[(*arc.key,p,t)] for p in arc.recipes)
            model.addConstr(total<=float(raw_cap))
            if arc.key==ASSEMBLY:
                model.addConstr(unassigned[t]+total==int(raw_cap))
            group_cap = network.group_caps.get((*arc.key,t))
            if group_cap is not None:
                model.addConstr(total<=group_cap)
            freight = [(p,base.sizes[p]) for p in arc.recipes if base.sizes[p]]
            if freight:
                model.addConstr(gp.quicksum((1 if base.products[p]=="transport" else -1)*s*
                                           flow[(*arc.key,p,t)] for p,s in freight)>=0)
            for p,recipe in arc.recipes.items():
                key=(*arc.key,p,t)
                q=flow[key]
                if key in network.product_caps:
                    model.addConstr(q<=network.product_caps[key])
                if key in scheduled_equalities:
                    model.addConstr(q==scheduled_equalities[key])
                for child,qty in recipe:
                    changes[arc.origin,child,t]-=float(qty)*q
                if t+arc.lead in periods:
                    changes[arc.destination,p,t+arc.lead]+=q
    for family in base.alpha_flows:
        first, divisor = family[0]
        for other, normalizer in family[1:]:
            for t in periods:
                model.addConstr(float(normalizer)*flow[(*first,t)]==float(divisor)*flow[(*other,t)])
    for p,g in groups.items():
        due=g.representative.due
        model.addConstr(shortfall[p,due]+gp.quicksum(flow[(*ASSEMBLY,p,t)] for t in periods)==len(g.orders))
        model.addConstr(gp.quicksum(outflow[p,t] for t in periods)+shortfall[p,due]==len(g.orders))
        for t in periods:
            if t!=due:
                shortfall[p,t].UB=0
                if not reschedule:
                    outflow[p,t].UB=flow[(*ASSEMBLY,p,t)].UB=0
            changes[g.representative.node,p,t]-=outflow[p,t]
    for node,item in keys:
        last=regular.get((node,item),0)+protection.get((node,item),0)
        for t in periods:
            key=(node,item,t)
            value=inventory[key]
            model.addConstr(value==last+fixed_receipts.get(key,0)+external.get(key,0)+changes[key])
            last=value
            if (node,item) in network.inventory_bounds:
                value.LB,value.UB=network.inventory_bounds[node,item]
            if node==OEM and base.products[item]=="seat":
                value.UB=0
    components={
        "flow":weights.flow*flow.sum(),
        "inventory":weights.inventory*inventory.sum(),
        "shortfall":weights.shortfall*shortfall.sum(),
        "deviation":weights.deviation*gp.quicksum(abs(t-groups[p].representative.due)*v for (p,t),v in outflow.items()),
        "unassigned":weights.unassigned*gp.quicksum((periods[-1]-t+1)*unassigned[t] for t in periods),
    }
    return Block(flow,inventory,external,shortfall,outflow,unassigned,components,regular,protection,fixed_receipts)
