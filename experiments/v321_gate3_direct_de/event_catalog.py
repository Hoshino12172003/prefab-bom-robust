"""Frozen finite Gate 3 event catalogue and its explicit enumeration."""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations


@dataclass(frozen=True)
class Event:
    id: str
    asset: tuple
    asset_type: str
    start: int
    duration: int
    availability: Fraction
    recovery: int

    def profile(self, periods):
        last_disrupted = self.start + self.duration - 1
        loss = 1 - self.availability
        return {(*self.asset, t): 1 - loss * (1 if t <= last_disrupted else
                Fraction(self.recovery + 1 - (t - last_disrupted), self.recovery + 1))
                for t in periods if self.start <= t <= last_disrupted + self.recovery}


F = Fraction
EVENTS = (
    Event("BAT_UP", ("battery-supplier_trans", "battery-supplier_prod"), "transport", 67, 2, F("0.4"), 2),
    Event("BAT_PROD", ("battery-supplier_prod", "battery-supplier_inv"), "production", 64, 3, F("0.4"), 2),
    Event("BAT_PROD_ALT", ("battery-supplier_prod", "battery-supplier_inv"), "production", 66, 2, F("0.65"), 1),
    Event("BAT_OEM", ("battery-supplier_inv", "zp7"), "transport", 69, 2, F("0.5"), 2),
    Event("SEAT_UP", ("seat-supplier_trans", "seat-supplier_prod"), "transport", 67, 2, F("0.5"), 1),
    Event("SEAT_PROD", ("seat-supplier_prod", "seat-supplier_inv"), "production", 67, 2, F("0.8"), 2),
    Event("ENGINE_PROD", ("engine-supplier_prod", "engine-supplier_inv"), "production", 65, 2, F("0.8"), 2),
    Event("GEAR_OEM", ("gear-supplier_inv", "zp7"), "transport", 65, 2, F("0.8"), 2),
)


def compatibility(events, periods):
    seen, occupied = set(), set()
    for event in events:
        if event.id in seen:
            return "DUPLICATE_EVENT"
        affected = set(event.profile(periods))
        if occupied & affected:
            return "OVERLAPPING_SAME_ASSET"
        occupied.update(affected)
        seen.add(event.id)
    return "LEGAL"


def enumerate_scenarios(events, gamma, nominal, periods):
    """Deduplicate exact effective capacity vectors and retain raw memberships."""
    ids = [e.id for e in events]
    assert len(set(ids)) == len(ids)
    keys = sorted(nominal)
    unique, mapping, by_capacity = {}, [], {}
    for count in range(gamma + 1):
        for chosen in combinations(events, count):
            event_ids = "+".join(e.id for e in chosen) or "NOM"
            reason = compatibility(chosen, periods)
            scenario = ""
            dedup = False
            if reason == "LEGAL":
                multipliers = {k: m for e in chosen for k,m in e.profile(periods).items()}
                effective = tuple(nominal[k] * multipliers.get(k, 1) for k in keys)
                dedup = effective in by_capacity
                if not dedup:
                    by_capacity[effective] = event_ids
                    unique[event_ids] = multipliers
                scenario = by_capacity[effective]
            mapping.append(dict(gamma=gamma, combination=event_ids, event_count=count, compatibility=reason,
                                scenario=scenario, deduplicated=dedup))
    return unique, mapping
