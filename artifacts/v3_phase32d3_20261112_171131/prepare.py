"""Frozen atomic identities, exact coordinates, and independently sized benchmarks."""

import json
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np

from prefab_v3.event_search import Atom


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D2R = ROOT / "artifacts/v3_phase32d2r_20261112_134524"
sys.path.insert(1, str(D2R))
import catalog as frozen_catalog

SOURCE = frozen_catalog.frozen
D2R_AUDIT = D2R / "audit.json"
POLICIES = {"P1": "BASE_B100", "P2": "BASE_B150", "P3": "R3_S75_D7_ABRUPT_B100", "P4": "BASE_B200"}
SIZES = {1: (355,), 2: (32, 64, 128, 256, 512), 3: (64, 128, 256, 512, 1024)}
TOTALS = {1: (415, 355), 2: (71830, 51070), 3: (2657350, 1564150)}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def policies():
    phase = ROOT / "artifacts/v3_phase32p_20261111_224834/runs"
    records = {p: read(phase / f"{k}.json") for p, k in POLICIES.items()}
    assert all(r["status"] == "EXACT_FINITE" for r in records.values())
    result = {p: tuple(r["policy"]) for p, r in records.items()}
    assert list(result.values()) == [(915, 0, 0), (1338, 24, 0), (713, 135, 6), (1338, 0, 162)]
    return result


def priority(event):
    return (-Fraction(event["severity"]), -event["duration"], event["start"])


class Coordinates:
    def __init__(self):
        metadata = read(D2R / "multibom_effective_rhs_catalog/rhs_coordinates.json")
        self.resources = metadata["resources"]
        assert tuple(self.resources) == frozen_catalog.RESOURCES and metadata["daily_concurrency"] == 2
        assert metadata["gammas"] == [1, 2, 3] and metadata["recovery"] == "ABRUPT_RECOVERY"
        self.groups = metadata["groups"]
        self.keys = tuple(tuple(k) for r in self.resources for k in self.groups[r]["keys"])
        self.nominal = tuple(int(v) for r in self.resources for v in self.groups[r]["values"][0])
        self.n_receipts = len(self.groups[self.resources[0]]["keys"])
        self.rank_luts, self.atoms, self.records = [], [], []
        offset = 0
        for i, r in enumerate(self.resources):
            group = self.groups[r]
            values = group["values"]
            # Use staggered seven-day anchors from the previous nonseparability
            # design, so even a small Gamma=3 benchmark contains legal triples.
            anchor_start = 68 if r == "SEAT" else 61
            def ladder_order(option):
                anchor = (option["start"], option["duration"], option["severity"]) == (anchor_start, 7, "3/4")
                return (not anchor, *priority(option))
            ranked = dict.fromkeys([0, *(o["local_id"] for o in sorted(group["options"], key=ladder_order))])
            codes = {v: self.spread(k) << i for k, v in enumerate(ranked)}
            self.rank_luts.append(np.array([codes[j] for j in range(len(values))], dtype=np.uint64))
            for o in group["options"]:
                j, start, duration = o["local_id"], o["start"], o["duration"]
                profile = self.nominal[:offset] + tuple(values[j]) + self.nominal[offset+len(values[j]):]
                mask = ((1 << duration)-1) << (start-61)
                atom = Atom(len(self.atoms)+1, i, mask, profile, j << (7*i), codes[j])
                self.atoms.append(atom)
                self.records.append(dict(event_id=atom.id, resource=r, branch=frozen_catalog.BRANCH[r],
                                         start=start, duration=duration, severity=o["severity"],
                                         recovery=metadata["recovery"], active_mask=mask, single_rhs=atom.code,
                                         ladder_rank=atom.rank))
            offset += len(values[0])
        self.by_id = {e.id: e for e in self.atoms}
        heuristic = {"SEAT": 0, "GEAR": 1, "ENGINE": 2, "B_SHIP": 3, "B_PROD": 4, "B_RECEIPT": 5}
        self.ordered = tuple(sorted(self.atoms, key=lambda e: (
            heuristic[self.resources[e.resource]], *priority(self.records[e.id-1]), e.id)))

    def spread(self, rank):
        return sum(((rank >> b) & 1) << (b*len(self.resources)) for b in range(7))

    def code_profile(self, code):
        return tuple(v for i, r in enumerate(self.resources)
                     for v in self.groups[r]["values"][code >> (7*i) & 127])

    def ranks(self, codes):
        return sum(lut[(codes >> (7*i)) & 127] for i, lut in enumerate(self.rank_luts))

    def profiles(self, vector, opening):
        arrivals = dict(opening)
        factors = {}
        for i, (key, value, nominal) in enumerate(zip(self.keys, vector, self.nominal, strict=True)):
            if value == nominal:
                continue
            if i < self.n_receipts:
                arrivals[key] = value
            else:
                factors[key] = Fraction(value, nominal)
        return arrivals, factors


def explicit_classes(coords):
    with np.load(D2R / "multibom_effective_rhs_catalog/classes.npz") as archive:
        ids = archive["ids"]
        mult = archive["exact_event_count_multiplicity"]
    ranks = coords.ranks(ids)
    assert len(np.unique(ranks)) == len(ids)
    return ids, mult, ranks


def make_cases(coords):
    ids, mult, ranks = explicit_classes(coords)
    cases = {}
    for gamma, sizes in SIZES.items():
        n = mult[:gamma+1].sum(axis=0)
        active = n > 0
        assert (int(n.sum()), int(active.sum())) == TOTALS[gamma]
        order = np.flatnonzero(active)[np.argsort(ranks[active])]
        for size in sizes:
            selection = order[:size]
            if gamma == 3:
                assert np.any((mult[:3, selection].sum(axis=0) == 0) & (mult[3, selection] > 0))
            families = Counter(frozen_catalog.family(r for i, r in enumerate(coords.resources)
                               if int(code) >> (7*i) & 127) for code in ids[selection])
            cases[f"G{gamma}_N{size}"] = dict(gamma=gamma, rhs_count=size, raw_count=int(n[selection].sum()),
                                            threshold=int(ranks[selection[-1]]) if gamma != 1 else None,
                                            effective_family_counts=dict(families))
    return cases


def main():
    prior = read(D2R_AUDIT)
    assert prior["status"] == "PASS_EVENT_BUDGET_MULTIBOM_UNCERTAINTY"
    identity = frozen_catalog.verify_manifest(D2R)
    assert frozen_catalog.digest(SOURCE.SOURCE) == prior["source_zip_sha256"]
    SOURCE.init()
    coords = Coordinates()
    actual, _ = frozen_catalog.choices()
    assert json.loads(json.dumps(actual)) == coords.groups
    rows = []
    for a in coords.atoms:
        for b in coords.atoms:
            if a.id == b.id or a.resource != b.resource:
                continue
            worse = all(u <= v for u, v in zip(a.profile, b.profile, strict=True))
            support_compatible = not (a.mask & ~b.mask)
            rows.append(dict(replacement=a.id, original=b.id, same_resource=True,
                             componentwise_at_least_as_adverse=worse, active_support_subset=support_compatible,
                             globally_valid_replacement=worse and support_compatible,
                             strictly_more_adverse=a.profile != b.profile and worse and support_compatible,
                             applied_for_pruning=False))
    frozen_catalog.write(HERE / "atomic_event_catalog.csv", coords.records)
    frozen_catalog.write(HERE / "event_dominance_audit.csv", rows)
    cases = make_cases(coords)
    frozen_catalog.dump(HERE / "benchmark_design.json", cases)
    frozen_catalog.dump(HERE / "preflight.json", dict(
        d2r_manifest=identity, atomic_identities=len(coords.atoms),
        single_event_rhs=len({a.code for a in coords.atoms}), nominal_rhs=0,
        dominance_pairs_checked=len(rows), dominance_valid=sum(r["globally_valid_replacement"] for r in rows),
        dominance_strict_rhs=sum(r["strictly_more_adverse"] for r in rows), policies=policies()))
    print("Frozen identity verified. Atomic events:", len(coords.atoms), "cases:", len(cases), flush=True)


if __name__ == "__main__":
    main()
