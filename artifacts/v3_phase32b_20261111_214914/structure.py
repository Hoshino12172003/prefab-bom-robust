"""Read-only RHS, BOM time reachability, and safe-bound audit."""
import heapq
import json
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import product, permutations

from profile_runs import FROZEN, HERE, LABEL, catalog, prior, verify_frozen, write_csv
from design import ARCS, PERIODS
from prefab_v25.data import BUFFER_EFFECTS, OEM, PACK, PRODUCTION_ARC, TRANSPORT_ARC
from prefab_v3.robust import Episode, UncertaintySet


def all_reachable(base, seeds):
    edges = defaultdict(list)
    for arc in base.network.arcs:
        for mother, children in arc.recipes.items():
            for child, _ in children:
                edges[arc.origin, child].append((arc.lead, (arc.destination, mother)))
    earliest = {}
    queue = [(date, state) for state, date in seeds.items()]
    heapq.heapify(queue)
    while queue:
        date, state = heapq.heappop(queue)
        if state in earliest:
            continue
        earliest[state] = date
        for lead, following in edges[state]:
            if following not in earliest:
                heapq.heappush(queue, (date+lead, following))
    return earliest


def reach(base, changes):
    arcs = {a.key: a for a in base.network.arcs}
    seeds = {}
    for kind, i, j, t in changes:
        if kind == "receipt":
            seeds[i, j] = min(t, seeds.get((i, j), t))
        else:
            arc = arcs[i, j]
            for p in arc.recipes:
                date = t+arc.lead
                seeds[j, p] = min(date, seeds.get((j, p), date))
    state_dates = all_reachable(base, seeds)
    ancestor = [g for g in base.network.groups if (g.representative.node, g.id) in state_dates]
    reached = [g for g in ancestor if state_dates[g.representative.node, g.id] <= g.representative.due]
    parts = {sku for (_, sku), t in state_dates.items() if t <= PERIODS[-1] and base.products[sku] != "car"}
    cars = sum(len(g.orders) for g in ancestor if state_dates[g.representative.node, g.id] <= PERIODS[-1])
    return dict(reachable_items=len(parts)+cars, reachable_non_vin_items="|".join(sorted(parts)),
                ancestor_vins=sum(len(g.orders) for g in ancestor),
                reachable_vins=sum(len(g.orders) for g in reached),
                reachable_configs=len({g.representative.bom for g in reached}),
                due_groups="|".join(map(str, sorted({g.representative.due for g in reached}))),
                first_delivery_reachable=min((state_dates[g.representative.node, g.id] for g in reached), default=""),
                reachable_cohort_ids="|".join(g.id for g in reached))


def receipt_headroom(base, opening, receipt_keys):
    net = base.network
    margins = {}
    for node, sku in sorted(receipt_keys):
        key = node, sku
        if key in net.external:
            continue
        buffer_upper = sum(int(prior.BUDGET / price)*v for price, effects in zip(prior.COSTS, BUFFER_EFFECTS)
                           for effect, v in effects if effect == key)
        fixed_upper = sum(q for (n, p, _), q in opening.items() if (n, p) == key)
        optional_upper = sum(sum(a.capacity.values()) for a in net.arcs
                             if a.destination == node and sku in a.recipes)
        ceiling = net.inventory_bounds.get(key, (0, float("inf")))[1]
        margin = ceiling - net.initial.get(key, 0) - buffer_upper - fixed_upper - optional_upper
        if margin >= 0:
            margins[key] = margin
    return margins


def monotone_order(a, b, nominal, safe_receipts):
    """Return whether every operation under worse b can be mapped into better a."""
    cap_diffs = receipt_diffs = 0
    for key in a.keys() | b.keys():
        left, right = a.get(key, nominal[key]), b.get(key, nominal[key])
        if left < right:
            return False, 0, 0
        if left > right:
            if key[0] == "receipt" and key[1:3] not in safe_receipts:
                return False, 0, 0
            if key[0] == "capacity":
                cap_diffs += 1
            else:
                receipt_diffs += 1
    return True, cap_diffs, receipt_diffs


def prefix_bounds(base, profile, x):
    """Safe service UBs from one-unit BOM incidence and dated arrivals."""
    net = base.network
    arrivals, factors = profile
    assembly = next(a for a in net.arcs if a.key == FROZEN.ASSEMBLY)
    seat_arc = next(a for a in net.arcs if a.key == ARCS["SEAT"])
    pack_arc = next(a for a in net.arcs if a.key == TRANSPORT_ARC)
    seat_skus = set(seat_arc.recipes)
    assert assembly.lead == seat_arc.lead == 0
    assert {p for p, group in base.products.items() if group == "seat"} == seat_skus
    assert all((OEM, sku) not in net.external and net.initial.get((OEM, sku), 0) == 0
               for sku in seat_skus)
    assert not any(key == (OEM, p) for p in seat_skus for row in BUFFER_EFFECTS for key, _ in row)
    assert {a.key for a in net.arcs if a.destination == OEM and seat_skus & a.recipes.keys()} == {seat_arc.key}
    assert {a.key for a in net.arcs if a.destination == OEM and PACK in a.recipes} == {pack_arc.key}
    assert (OEM, PACK) not in net.external
    n_due, bev_due = Counter(), Counter()
    for g in net.groups:
        item = g.id
        due = g.representative.due
        assert g.representative.node == assembly.destination and net.initial.get((assembly.destination, item), 0) == 0
        assert (assembly.destination, item) not in net.external
        assert sum(q for p, q in g.representative.bom if p in seat_skus) == 1
        assert all(p != PACK or q == 1 for p, q in g.representative.bom)
        n_due[due] += len(g.orders)
        if any(p == PACK for p, _ in g.representative.bom):
            bev_due[due] += len(g.orders)
    cars = {g.id for g in net.groups}
    assert not any(q and n == assembly.destination and p in cars for (n, p, _), q in arrivals.items())
    assert all(a.key == assembly.key or not cars & a.recipes.keys() for a in net.arcs)
    assert not any(p in cars for row in BUFFER_EFFECTS for (_, p), _ in row)
    pack_total = net.initial.get((OEM, PACK), 0) + FROZEN.protection_inventory(x)[OEM, PACK]
    seat_total, due_total, due_bev_total = 0, 0, 0
    seat_ub = pack_ub = net.demand_weight
    for t in PERIODS:
        def capacity(a, depart):
            return int(a.capacity[depart]*factors.get((*a.key, depart), 1)) if depart in PERIODS else 0
        seat_total += min(capacity(assembly, t), capacity(seat_arc, t) +
                          sum(arrivals.get((OEM, p, t), 0) for p in seat_skus))
        pack_total += capacity(pack_arc, t-pack_arc.lead) + arrivals.get((OEM, PACK, t), 0)
        due_total += n_due[t]
        due_bev_total += bev_due[t]
        seat_ub = min(seat_ub, seat_total + net.demand_weight - due_total)
        pack_ub = min(pack_ub, pack_total + net.demand_weight - due_bev_total)
    return seat_ub, pack_ub, min(seat_ub, pack_ub)


def combinatorial_rhs(base, opening):
    from design import F
    u = UncertaintySet(PERIODS, (1, 3, 5), (F(1, 4), F(1, 2), F(3, 4)), 6, 2)
    options = {0: (None,)}
    for t, duration in u.intervals():
        mask = ((1<<duration)-1) << (t-PERIODS[0])
        options[mask] = tuple(Episode(t, duration, severity) for severity in u.severities)
    caps = {a.key: a.capacity for a in base.network.arcs}
    cache = {}
    for e in (e for choices in options.values() for e in choices):
        remaining = dict(zip(PERIODS, u.factors(e)))
        cache[0, e] = tuple((k, int(q*remaining[k[2]])) for k, q in sorted(opening.items())
                            if k[0] == FROZEN.PROD and k[1] in FROZEN.CELL and int(q*remaining[k[2]]) != q)
        for i, arc in enumerate((PRODUCTION_ARC, TRANSPORT_ARC), 1):
            cache[i, e] = tuple((t, int(caps[arc][t]*remaining[t])) for t in PERIODS
                                if int(caps[arc][t]*remaining[t]) != caps[arc][t])
    count = 0
    signatures = Counter()
    for masks in u.feasible_masks():
        for signature in product(*(tuple(cache[i, e] for e in options[mask]) for i, mask in enumerate(masks))):
            count += 1
            signatures[signature] += 1
    assert (count, len(signatures)) == (287443, 38527)
    inactive = [(i, e) for (i, e), signature in cache.items() if e is not None and not signature]
    return dict(label=LABEL, legal_trajectories=count, unique_rhs=len(signatures),
                duplicates=count-len(signatures), largest_class=max(signatures.values()),
                nominal_equivalence_class=signatures[((), (), ())],
                individually_ineffective_episodes=dict(Counter(f"L{i+1}" for i, _ in inactive)),
                ineffective_episode_examples=[(f"L{i+1}", e.start, e.duration, str(e.severity)) for i, e in inactive[:5]],
                mip_solves=0)


def audit():
    verify_frozen()
    FROZEN.init()
    base, opening = FROZEN.BASE, FROZEN.OPENING
    source, profiles, diffs, reps, unique = catalog(base, opening)
    nominal = {("capacity", *a.key, t): v for a in base.network.arcs for t, v in a.capacity.items()}
    nominal.update({("receipt", *k): v for k, v in opening.items()})
    safe_receipts = receipt_headroom(base, opening, {k[1:3] for d in diffs.values() for k in d if k[0] == "receipt"})
    dominance, equivalence, resources, pattern, time = [], [], [], [], []
    for a, b in permutations(profiles, 2):
        valid, caps, receipts = monotone_order(diffs[a], diffs[b], nominal, safe_receipts)
        equal = diffs[a] == diffs[b]
        result = "EXACT_EQUIVALENCE_SCREENING" if equal else "PROVEN_GLOBAL_DOMINANCE" if valid else "NOT_PROVEN"
        dominance.append(dict(label=LABEL, weaker=a, stronger=b, verdict=result,
                              relaxed_capacity_rows=caps, increased_receipt_rows=receipts,
                              both_in_16=a in unique[:16] and b in unique[:16],
                              both_in_24=a in unique[:24] and b in unique[:24],
                              both_in_32=a in unique[:32] and b in unique[:32]))
    for name, d in diffs.items():
        events = source[name].events
        signature = tuple(sorted(d.items()))
        fingerprint = sha256(json.dumps(signature, separators=(",", ":")).encode()).hexdigest()
        equivalence.append(dict(label=LABEL, catalog="MULTI_BOM_FROZEN", scenario=name, representative=reps[name],
                                equivalent_to_earlier=name != reps[name], effective_rhs_sha256=fingerprint,
                                changed_rows=len(signature), raw_events=json.dumps([
                                    (e.resource, e.start, e.duration, str(e.severity)) for e in events])))
        union = reach(base, d)
        pattern.append(dict(label=LABEL, scenario=name, branches="|".join(sorted({
            "BATTERY" if e.resource.startswith("B_") else e.resource for e in events})),
            resources="|".join(e.resource for e in events), start="|".join(str(e.start) for e in events),
            duration="|".join(str(e.duration) for e in events), severity="|".join(str(e.severity) for e in events),
            recovery="ABRUPT", effective_capacity_availability=json.dumps(signature), **union))
        affected = int(union["reachable_vins"])
        time.append(dict(label=LABEL, scenario=name, changed_rhs=len(d), reachable_by_due_vins=affected,
                         disposition="NOMINAL_CONTROL" if not events else
                         "EXACT_EQUIVALENCE_SCREENING" if not d else
                         "KEEP_DIRECT_PATH" if affected else "NO_DIRECT_PATH_BUT_SCREEN_NOT_PROVEN",
                         actual_screened_from_plain=False))
        for e in events:
            days = range(e.start, e.start+e.duration)
            resource_d = {k: v for k, v in d.items() if k[-1] in days and
                          ((e.resource == "B_RECEIPT" and k[0] == "receipt") or
                           (k[0] == "capacity" and k[1:3] == ARCS.get(e.resource)))}
            resources.append(dict(label=LABEL, scenario=name, resource=e.resource, start=e.start,
                                  duration=e.duration, changed_rhs=len(resource_d), **reach(base, resource_d)))
    write_csv("scenario_dominance_audit.csv", dominance)
    write_csv("rhs_equivalence_audit.csv", equivalence)
    write_csv("bom_risk_reachability.csv", resources)
    write_csv("risk_pattern_signature.csv", pattern)
    write_csv("bom_time_screening_audit.csv", time)
    data = dict(label=LABEL, frozen_catalog=len(profiles), unique_rhs=len(unique),
                aliases={n: r for n, r in reps.items() if n != r}, benchmark_order=unique,
                receipt_storage_headroom={"|".join(k): v for k, v in safe_receipts.items()},
                proven_pairs={str(n): sum(r[f"both_in_{n}"] and r["verdict"] == "PROVEN_GLOBAL_DOMINANCE"
                                         for r in dominance) for n in (16, 24, 32)},
                total_proven_pairs=sum(r["verdict"] == "PROVEN_GLOBAL_DOMINANCE" for r in dominance),
                old_battery_combinatorial=combinatorial_rhs(base, opening))
    (HERE/"structure_summary.json").write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    print(data)


if __name__ == "__main__":
    audit()
