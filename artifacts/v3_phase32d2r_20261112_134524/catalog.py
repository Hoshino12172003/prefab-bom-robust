"""Count all event trajectories and archive exact recourse-RHS identities."""

import csv
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
from time import perf_counter

import numpy as np

from prefab_v3.event_budget import CONCURRENCY, DURATIONS, GAMMAS, RECOVERY, SEVERITIES, Event, EventBudget


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = ROOT / "artifacts"
PHASE31 = ARTIFACTS / "v3_phase31_20261111_193210"
PHASE31R = ARTIFACTS / "v3_phase31r_20261111_202237"
D2 = ARTIFACTS / "v3_phase32d2_20261112_132513"
sys.path[:0] = [str(PHASE31R), str(PHASE31), str(D2)]
import run_matrix as frozen
from design import ARCS, Event as SourceEvent, Scenario
from record_gate import digest, verify_manifest

BRANCH = dict(B_RECEIPT="B", B_PROD="B", B_SHIP="B", GEAR="G", SEAT="S", ENGINE="E")
RESOURCES = tuple(BRANCH)
BUDGET = EventBudget(RESOURCES, frozen.PERIODS)
EPISODES = BUDGET.episodes()
FAMILIES = ("NR", "B", "G", "S", "BG", "BS", "GS", "BGS", "E", "BE", "GE", "SE", "BGE", "BSE", "GSE")
BITS = 7
CATALOG = HERE / "multibom_effective_rhs_catalog"


def write(path, records):
    records = list(records)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def family(resources):
    branches = {BRANCH[r] for r in resources}
    return "".join(b for b in "BGSE" if b in branches) or "NR"


def profile(name, events):
    BUDGET.validate(events, max(1, len(events)))
    raw = tuple(SourceEvent(e.resource, e.episode.start, e.episode.duration, e.episode.severity)
                for e in events)
    return frozen.data_for(Scenario(name, raw), frozen.OPENING, frozen.BASE)


def choices():
    """Build ordered local coordinates and assign local IDs by exact RHS equality."""
    arcs = {arc.key: arc for arc in frozen.BASE.network.arcs}
    groups, evidence = {}, []
    selected = {r["resource_id"]: r for r in frozen.read(PHASE31R / "selected_multi_bom_risk_resources.csv")}
    assert set(selected) == set(RESOURCES) and selected["ENGINE"]["status"] == "PRIMARY"
    assert frozen.BASE.network.periods == BUDGET.periods
    for r in RESOURCES:
        if r == "B_RECEIPT":
            keys = sorted(key for key in frozen.OPENING if key[0] == frozen.PROD
                          and key[1] in frozen.CELL and key[2] in BUDGET.periods)
            baseline = tuple(frozen.OPENING[k] for k in keys)
            assert {k[1] for k in keys} == set(frozen.CELL) and any(baseline)
        else:
            arc = arcs[ARCS[r]]
            keys = [(*arc.key, t) for t in BUDGET.periods]
            baseline = tuple(arc.capacity[k[2]] for k in keys)
            assert all(baseline) and arc.lead == int(selected[r]["lead_time"])
            assert len(arc.recipes) == int(selected[r]["distinct_exposed_SKUs"])
        signatures = {baseline: 0}
        options = []
        for e in EPISODES:
            arrivals, factors = profile(r, (Event(r, e),))
            values = (tuple(arrivals[k] for k in keys) if r == "B_RECEIPT" else
                      tuple(int(raw*factors.get(key, 1)) for key, raw in zip(keys, baseline, strict=True)))
            independently = tuple(raw * (1-e.severity) if e.start <= k[2] < e.start+e.duration else raw
                                  for k, raw in zip(keys, baseline, strict=True))
            assert values == tuple(map(int, independently))
            local_id = signatures.setdefault(values, len(signatures))
            options.append(dict(start=e.start, duration=e.duration, severity=str(e.severity), local_id=local_id))
        assert len(signatures) <= (1 << BITS)
        groups[r] = dict(kind="fixed_receipt" if r == "B_RECEIPT" else "capacity", keys=keys,
                         values=list(signatures), options=options)
        evidence.append(dict(**selected[r], branch=BRANCH[r], exact_rhs_coordinates=len(keys),
                             duration_4_valid_starts=11, duration_7_valid_starts=8, duration_11_valid_starts=4,
                             raw_event_options=len(options), local_rhs_with_nominal=len(signatures),
                             no_effect_events=sum(o["local_id"] == 0 for o in options),
                             evidence_file=f"{PHASE31R.name}/selected_multi_bom_risk_resources.csv"))
    coordinates = [(group["kind"], *k) for group in groups.values() for k in group["keys"]]
    assert len(coordinates) == len(set(coordinates))
    return groups, evidence


def supports():
    """Cross-check bitmask legality against direct day-set intersections."""
    distinct = tuple(dict.fromkeys((e.start, e.duration) for e in EPISODES))
    dates = [set(range(t, t+d)) for t, d in distinct]
    masks = np.array([sum(1 << (t-BUDGET.periods[0]) for t in day) for day in dates], dtype=np.uint16)
    triple = (masks[:, None, None] & masks[None, :, None] & masks[None, None, :]) == 0
    legal = [np.ones((len(masks),)*k, dtype=bool) for k in (1, 2)] + [triple]
    reference = np.array([not (a & b & c) for a, b, c in product(dates, repeat=3)]).reshape(triple.shape)
    assert CONCURRENCY == 2 and np.array_equal(triple, reference)
    return distinct, legal


def exact_codes(locals_, legality):
    ids = tuple(v.reshape(tuple(-1 if i == j else 1 for i in range(len(locals_))))
                for j, v in enumerate(locals_))
    expanded = legality
    for axis in range(legality.ndim):
        expanded = np.repeat(expanded, len(SEVERITIES), axis=axis)
    return sum(ids)[expanded]


def count():
    started = perf_counter()
    frozen.init()
    groups, evidence = choices()
    CATALOG.mkdir(exist_ok=True)
    dump(CATALOG / "rhs_coordinates.json", dict(resources=RESOURCES, bits=BITS, groups=groups,
                                                gammas=GAMMAS, daily_concurrency=CONCURRENCY,
                                                recovery=RECOVERY, label="STRESS_TEST_ONLY"))
    write(HERE / "multibom_risk_resource_catalog.csv", evidence)
    intervals, legality = supports()
    local = {r: np.array([e["local_id"] for e in groups[r]["options"]], dtype=np.uint64) << (BITS*i)
             for i, r in enumerate(RESOURCES)}
    per_family, per_cardinality = defaultdict(list), {0: [np.array([0], dtype=np.uint64)]}
    per_family[0, "NR"].extend(per_cardinality[0])
    raw = Counter({(0, "NR"): 1})
    distributions = Counter()
    for k in GAMMAS:
        per_cardinality[k] = []
        for rs in combinations(RESOURCES, k):
            f = family(rs)
            raw[k, f] += len(EPISODES)**k
            codes = exact_codes(tuple(local[r] for r in rs), legality[k-1])
            assert codes.size == np.count_nonzero(legality[k-1])*len(SEVERITIES)**k
            per_family[k, f].append(codes)
            per_cardinality[k].append(codes)
            for slot, r in enumerate(rs):
                marginal = legality[k-1].sum(axis=tuple(i for i in range(k) if i != slot))
                for (start, duration), n in zip(intervals, marginal, strict=True):
                    distributions[k, f, r, start, duration] += int(n) * len(SEVERITIES)**(k-1)
    write(HERE / "multibom_event_distribution.csv",
          (dict(event_count=k, family=f, resource=r, start=t, duration=d, severity=str(s),
                trajectory_occurrences=n) for (k, f, r, t, d), n in sorted(distributions.items()) for s in SEVERITIES))

    layers = [np.unique(np.concatenate(per_cardinality[k]), return_counts=True) for k in range(4)]
    all_ids = np.unique(np.concatenate([ids for ids, _ in layers]))
    multiplicities = np.zeros((4, len(all_ids)), dtype=np.uint32)
    for k, (ids, counts) in enumerate(layers):
        multiplicities[k, np.searchsorted(all_ids, ids)] = counts
    choice_masks = tuple((all_ids >> (BITS*i) & ((1 << BITS)-1)) != 0 for i in range(len(RESOURCES)))
    min_gamma = sum(mask.astype(np.uint8) for mask in choice_masks)
    assert np.array_equal(min_gamma, (multiplicities > 0).argmax(axis=0))
    np.savez_compressed(CATALOG / "classes.npz", ids=all_ids, exact_event_count_multiplicity=multiplicities)
    effective_branch_mask = sum(
        np.logical_or.reduce([m for m, r in zip(choice_masks, RESOURCES, strict=True) if BRANCH[r] == branch])
        .astype(np.uint8) * (1 << i) for i, branch in enumerate("BGSE"))
    summary, effective = [], []
    for gamma in GAMMAS:
        for f in (*FAMILIES, "Total"):
            if f == "Total":
                candidates = sum(n for (k, _), n in raw.items() if k <= gamma)
                legal_count = int(multiplicities[:gamma+1].sum())
                distinct_rhs = int(np.count_nonzero(min_gamma <= gamma))
            else:
                candidates = sum(raw[k, f] for k in range(gamma+1))
                arrays = [a for k in range(gamma+1) for a in per_family[k, f]]
                legal_count = sum(a.size for a in arrays)
                distinct_rhs = np.unique(np.concatenate(arrays)).size if arrays else 0
                mask = sum(1 << i for i, b in enumerate("BGSE") if b in f)
                effective.append(dict(gamma_evt=gamma, family=f, legal_event_family_trajectories=legal_count,
                                      raw_family_distinct_rhs=distinct_rhs, globally_effective_family_rhs=
                                      int(np.count_nonzero((min_gamma <= gamma) & (effective_branch_mask == mask)))))
            summary.append(dict(gamma_evt=gamma, K=CONCURRENCY, family=f, raw_candidates=candidates,
                                legal_trajectories=legal_count, illegal_concurrency=candidates-legal_count,
                                exact_event_duplicates=0, distinct_rhs=distinct_rhs,
                                exact_rhs_duplicates=legal_count-distinct_rhs,
                                compression_ratio=legal_count/distinct_rhs if distinct_rhs else None))
    write(HERE / "multibom_scenario_count_by_gamma.csv", summary)
    write(HERE / "multibom_family_summary.csv", effective)
    result = dict(seconds=perf_counter()-started, legal_interval_supports_per_resource_subset=[
        int(a.sum()) for a in legality], total_by_gamma=[row for row in summary if row["family"] == "Total"],
        catalog_classes=len(all_ids))
    dump(HERE / "count_run.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    count()
