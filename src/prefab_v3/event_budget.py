"""Phase 3.2D-2R cardinality for contiguous, abrupt disruption events."""

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from .robust import Episode


DURATIONS = (4, 7, 11)
SEVERITIES = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
GAMMAS = (1, 2, 3)
CONCURRENCY = 2
RECOVERY = "ABRUPT_RECOVERY"


@dataclass(frozen=True)
class Event:
    resource: str
    episode: Episode
    recovery: str = RECOVERY


@dataclass(frozen=True)
class EventBudget:
    resources: tuple[str, ...]
    periods: tuple[int, ...]

    def episodes(self):
        return tuple(Episode(t, d, s) for d in DURATIONS for t in self.periods
                     if t+d-1 <= self.periods[-1] for s in SEVERITIES)

    def validate(self, events, gamma, concurrency=CONCURRENCY):
        if gamma not in GAMMAS or concurrency not in (1, 2, 3):
            raise ValueError("unsupported event budget or daily concurrency")
        if len(events) > gamma:
            raise ValueError("event count exceeds budget")
        resources = {e.resource for e in events}
        if len(resources) != len(events) or not resources.issubset(self.resources):
            raise ValueError("duplicate or unknown resource")
        eligible = set(self.episodes())
        if any(e.episode not in eligible or e.recovery != RECOVERY for e in events):
            raise ValueError("ineligible episode or recovery class")
        active = Counter(t for e in events
                         for t in range(e.episode.start, e.episode.start+e.episode.duration))
        if max(active.values(), default=0) > concurrency:
            raise ValueError("daily concurrency exceeds limit")
        return sum(active.values())
