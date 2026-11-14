"""Exact BOM-time bounds and finite E4 separation on the historical V3 base."""
from collections import Counter
from dataclasses import dataclass
from time import perf_counter

from prefab_v25.data import BUFFER_EFFECTS, OEM, PACK, PRODUCTION_ARC, T1, TRANSPORT_ARC
from .base import ASSEMBLY
from .plain_ccg import BoundError, Result, TOLERANCE


SEAT = ("seat-supplier_inv", OEM)
ENGINE = ("engine-supplier_prod", "engine-supplier_inv")
GEAR = ("gear-supplier_inv", OEM)


class InvalidBound(BoundError):
    pass


class Prefix:
    """Optimistic dated supply for necessary one-seat / one-Pack BOM inputs."""

    def __init__(self, base):
        net = base.network
        self.periods = net.periods
        self.demand = net.demand_weight
        self.arcs = {a.key: a for a in net.arcs}
        self.seats = set(self.arcs[SEAT].recipes)
        assert self.seats == {p for p, g in base.products.items() if g == "seat"}
        assert self.arcs[ASSEMBLY].lead == self.arcs[SEAT].lead == 0
        self.finished = {g.id for g in net.groups}
        self.total_due, self.bev_due = Counter(), Counter()
        for g in net.groups:
            o = g.representative
            assert o.node == ASSEMBLY[1] and o.weight == 1 and o.due in self.periods
            assert sum(q for p, q in o.bom if p in self.seats) == 1
            pack = sum(q for p, q in o.bom if p == PACK)
            assert pack in (0, 1)
            self.total_due[o.due] += len(g.orders)
            self.bev_due[o.due] += pack*len(g.orders)
        assert not any(net.initial.get((n,p), 0) for n,p in
                       [(OEM,p) for p in self.seats]+[(ASSEMBLY[1],p) for p in self.finished])
        keys = {(OEM,p) for p in self.seats | {PACK}} | {(T1,PACK)} | {(ASSEMBLY[1],p) for p in self.finished}
        assert not (keys & set(net.external))
        assert not any(key in keys-{(OEM,PACK), (T1,PACK)} for row in BUFFER_EFFECTS for key, _ in row)
        assert {a.key for a in net.arcs if a.destination == OEM and self.seats & a.recipes.keys()} == {SEAT}
        assert {a.key for a in net.arcs if a.destination == OEM and PACK in a.recipes} == {TRANSPORT_ARC}
        assert {a.key for a in net.arcs if a.destination == T1 and PACK in a.recipes} == {PRODUCTION_ARC}
        assert {a.key for a in net.arcs if a.destination == ASSEMBLY[1] and self.finished & a.recipes.keys()} == {ASSEMBLY}
        assert BUFFER_EFFECTS[1] == (((T1, PACK), 1),) and BUFFER_EFFECTS[2] == (((OEM, PACK), 1),)
        self.t1 = net.initial.get((T1, PACK), 0)
        self.oem = net.initial.get((OEM, PACK), 0)

    def upper(self, profile, x):
        receipts, factors = profile
        assert not any(q and n == ASSEMBLY[1] and p in self.finished for (n,p,_),q in receipts.items())
        def cap(key, t):
            a = self.arcs[key]
            return int(a.capacity.get(t,0)*factors.get((*key,t),1))
        production_lead = self.arcs[PRODUCTION_ARC].lead
        shipping_lead = self.arcs[TRANSPORT_ARC].lead
        t1_prefix, shipping_prefix, oem_receipts = self.t1+x[1], 0, self.oem+x[2]
        seat_prefix = due = bev = 0
        pack_ub = seat_ub = self.demand
        for t in self.periods:
            departure = t-shipping_lead
            if departure in self.periods:
                t1_prefix += receipts.get((T1,PACK,departure),0)+cap(PRODUCTION_ARC,departure-production_lead)
                shipping_prefix += cap(TRANSPORT_ARC,departure)
            oem_receipts += receipts.get((OEM,PACK,t),0)
            seat_in = cap(SEAT,t)+sum(receipts.get((OEM,p,t),0) for p in self.seats)
            seat_prefix += min(cap(ASSEMBLY,t),seat_in)
            due += self.total_due[t]
            bev += self.bev_due[t]
            seat_ub = min(seat_ub, self.demand-due+seat_prefix)
            pack_ub = min(pack_ub, self.demand-bev+oem_receipts+min(t1_prefix,shipping_prefix))
        return pack_ub, seat_ub, min(pack_ub,seat_ub)


def seat_pairs(profiles):
    """Pair the two approved dual-branch patterns on their identical seat-JIT row."""
    buckets = {}
    for name, (arrivals, factors) in profiles.items():
        if len(factors) != 2:
            continue
        seat = next(((k,v) for k,v in factors.items() if k[:2]==SEAT), None)
        other = next((k for k in factors if k[:2] in (ENGINE,GEAR)), None)
        if seat is not None and other is not None and seat[0][2]==other[2]:
            key = seat, tuple(sorted(arrivals.items()))
            buckets.setdefault(key, []).append((name, other[:2]))
    return {name: (a,b) for pairs in buckets.values() if len(pairs)==2
            for (a,arc_a),(b,arc_b) in (pairs,) if arc_a!=arc_b for name in (a,b)}


def intersection(a, b):
    receipts, left = a
    other, right = b
    assert receipts == other
    return receipts, {k:min(left.get(k,1),right.get(k,1)) for k in left.keys() | right.keys()}


@dataclass(frozen=True)
class Separation:
    worst: int
    ties: tuple
    rows: tuple
    bound_seconds: float
    individual_solves: int
    common_solves: int


def separate(profiles, prefix, policy, solve):
    """Solve a fixed ordered finite set. Never drop a potential exact tie."""
    started = perf_counter()
    upper = {n: prefix.upper(p, policy) for n,p in profiles.items()}
    pairs = seat_pairs(profiles)
    bound_seconds = perf_counter()-started
    rows, exact, solved_pairs = [], {}, set()
    direct = common = 0
    incumbent = float("inf")
    pending = set(profiles)
    for name in profiles:
        if name not in pending:
            continue
        pair = pairs.get(name)
        if incumbent != float("inf") and pair and pair not in solved_pairs and all(n in pending for n in pair):
            solved_pairs.add(pair)
            lower, evidence = solve(f"meet__{'__'.join(pair)}",intersection(*(profiles[n] for n in pair)),policy)
            common += 1
            for n in pair:
                up = upper[n][2]
                if lower>up:
                    raise InvalidBound(f"{n}: common feasible witness {lower} exceeds {up}")
                cutoff = incumbent
                if lower>cutoff:
                    disposition, value = "PRUNED_STRICT", None
                elif lower==up:
                    disposition, value = "BOUND_EXACT", lower
                    exact[n] = value
                    incumbent = min(incumbent,value)
                else:
                    continue
                rows.append(dict(scenario=n, lower=lower, upper=up, pack_upper=upper[n][0],
                    seat_upper=upper[n][1], incumbent=cutoff, decision=disposition, value=value,
                    proof="COMMON_INTEGER_WITNESS_AND_DATED_BOM_PREFIX", pair=pair, evidence=evidence))
                pending.remove(n)
        if name in pending:
            q, evidence = solve(name, profiles[name], policy)
            direct += 1
            if q>upper[name][2]:
                raise InvalidBound(f"{name}: integer optimum {q} exceeds {upper[name][2]}")
            rows.append(dict(scenario=name, lower=q, upper=upper[name][2], pack_upper=upper[name][0],
                seat_upper=upper[name][1], incumbent=None if incumbent==float("inf") else incumbent,
                decision="INDIVIDUAL_MILP", value=q, proof="FULL_INTEGER_OPTIMAL", pair=(), evidence=evidence))
            exact[name] = q
            incumbent = min(incumbent,q)
            pending.remove(name)
    assert not pending and len(rows)==len(profiles)
    return Separation(incumbent, tuple(sorted(n for n,q in exact.items() if q==incumbent)),
                      tuple(rows),bound_seconds,direct,common)


def generate(names, initial, master, oracle, verify):
    """Plain single-block C&CG semantics with certified partial separation."""
    names, selected = tuple(names), tuple(initial)
    if not selected or len(set(selected))!=len(selected) or not set(selected)<=set(names):
        raise ValueError("Invalid initial blocks")
    lower, upper, best = -1,float("inf"),None
    records = []
    for k in range(1,len(names)-len(selected)+2):
        start = perf_counter()
        mp = master(selected,k)
        after_master = perf_counter()
        result = oracle(mp.policy,k)
        after_oracle = perf_counter()
        by_name = {r["scenario"]:r for r in result.rows}
        if set(by_name)!=set(names):
            raise BoundError("E4 certificate does not cover the full scenario set")
        if mp.objective>upper or any(by_name[n]["value"] is not None and by_name[n]["value"]<mp.objective
                                    for n in selected):
            raise BoundError("Master bound contradicts E4 separation")
        upper = mp.objective
        if result.worst>lower:
            lower,best = result.worst,mp.policy
        if lower>upper:
            raise BoundError("E4 incumbent exceeds master upper bound")
        gap = upper-lower
        added = result.ties[0] if gap>TOLERANCE else ""
        if added and (added in selected or result.worst>=upper):
            raise BoundError("Invalid violating scenario")
        records.append(dict(iteration=k,master_scenarios=selected,added_scenario=added,policy=mp.policy,
            lower=lower,upper=upper,oracle_worst=result.worst,worst_ties=result.ties,
            master_seconds=after_master-start,oracle_seconds=after_oracle-after_master,**mp.metrics))
        if gap<=TOLERANCE:
            start_verify = perf_counter()
            values = {n:verify(n,best,"verify") for n in names}
            if min(values.values())!=lower:
                raise BoundError("Fresh exhaustive final verification differs")
            return Result(lower,best,selected,values,tuple(records),perf_counter()-start_verify)
        selected += (added,)
    raise BoundError("Full finite scenario set exhausted")
