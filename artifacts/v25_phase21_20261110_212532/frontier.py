"""Independent exact policy certificates for the frozen Phase 2.1 diagnostics."""
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHASE20 = ROOT / 'artifacts/v25_phase20_20261110_203851'
SPEC = json.loads((PHASE20 / 'prospective_manifest.json').read_text(encoding='utf-8'))
PERIODS = tuple(range(1, 15))
DEMAND = tuple(SPEC['due_counts'][str(t)] for t in PERIODS)
TOTAL = sum(DEMAND)
SCALES = {days: -(-days * TOTAL // len(PERIODS)) for days in (1, 3, 5)}
RATIO = Fraction(108, 76)
RATIO_BOUNDS = (Fraction(13, 10), Fraction(157, 100))
LABEL = 'STRUCTURAL_DIAGNOSTIC_ONLY'
# The source contributes the calendar and capacities. All non-identity factors are stress assumptions.
RISKS = {
    'NOM': (Fraction(1), Fraction(1), Fraction(1)),
    'L1': (Fraction(1, 2), Fraction(1), Fraction(1)),
    'L2': (Fraction(1), Fraction(1, 4), Fraction(1)),
    'L3': (Fraction(1), Fraction(1), Fraction(1, 4)),
}
SUPPORT = ('ZERO', 'C', 'T', 'CT', 'O', 'CO', 'TO', 'CTO')


def capacity(risk, stage, t):
    return int(SPEC['battery_chain'][stage]['capacity'][str(t)] * RISKS[risk][stage])


def no_oem_service(risk, c, t1):
    """Maximal on-time count for fixed C/T with no OEM stock, elementwise."""
    produced = sent = received = due = missed = 0
    release = RISKS[risk][0]
    usable = (release.numerator * c) // release.denominator
    for t, demand in enumerate(DEMAND, 1):
        due += demand
        missed = np.maximum(missed, due - received)
        sent = np.minimum(sent + capacity(risk, 2, t), t1 + produced)
        produced = np.minimum(produced + capacity(risk, 1, t), usable)
        received = sent
    return TOTAL - missed


class Frontier:
    """Exact finite first-stage projection, with integer costs scaled by the ratio denominator."""

    def __init__(self, risk, k, ratio):
        self.ratio = ratio
        p, q = ratio.numerator, ratio.denominator
        self.budget_scaled = k * p
        # All physical storage limits are slack at the largest tested nonnegative portfolio.
        assert self.budget_scaled // q * 10 < 99999
        c, t1 = np.meshgrid(np.arange(self.budget_scaled // q + 1), np.arange(k + 1), indexing='ij')
        remaining = self.budget_scaled - q * c - p * t1
        allowed = remaining >= 0
        self.c, self.t1, self.remaining = c[allowed], t1[allowed], remaining[allowed]
        self.base = no_oem_service(risk, self.c, self.t1)
        self.kind = (self.c > 0).astype(int) + 2 * (self.t1 > 0)
        self.by_kind = [(self.base[m], self.remaining[m]) for i in range(4) for m in [self.kind == i]]

    def selection(self, premium, allowed=7, target=None):
        p = self.ratio.numerator
        # Work in scaled integers, including at exact breakpoints.
        max_o = self.remaining * premium.denominator // (p * (premium.denominator + premium.numerator))
        if not allowed & 4:
            max_o = np.zeros_like(max_o)
        eligible = self.kind & ~allowed == 0
        service = np.minimum(TOTAL, self.base + max_o)
        if target is None:
            target = int(service[eligible].max())
        selected = eligible & (service >= target)
        if not selected.any():
            raise ValueError(f'no policy attains {target}')
        c, t1 = self.c[selected], self.t1[selected]
        min_o, max_o = np.maximum(0, target - self.base[selected]), max_o[selected]
        extrema = [(int(v.min()), int(v.max())) for v in (c, t1)]
        extrema.append((int(min_o.min()), int(max_o.max())))
        witnesses = []
        for j, v in enumerate((c, t1, min_o)):
            for high in (False, True):
                use = max_o if high and j == 2 else v
                i = int(use.argmax() if high else use.argmin())
                witnesses.append((int(c[i]), int(t1[i]), int(max_o[i] if high and j == 2 else min_o[i])))
        return target, extrema, witnesses

    def thresholds(self, z):
        """Largest feasible nonnegative premium for each support at service target z."""
        values = {}
        p = self.ratio.numerator
        for i, (base, remaining) in enumerate(self.by_kind):
            if base.size == 0:
                continue
            if base.max() >= z:
                values[SUPPORT[i]] = float('inf')
            o = np.maximum(1, z - base)
            d = p * o
            n = remaining - d
            j = int(np.argmax(n / d))
            assert np.all(n * d[j] <= n[j] * d)
            if n[j] >= 0:
                values[SUPPORT[i + 4]] = Fraction(int(n[j]), int(d[j]))
        return values

    def events(self):
        """Exact changes in integer optimum or the set of optimal positive-support types."""
        initial = self.selection(Fraction(0))[0]
        baseline = int(self.base.max())
        levels = []
        # Descend service counts, skipping levels whose threshold is covered by a higher level.
        left = Fraction(-1)
        points = {Fraction(0)}
        for z in range(initial, baseline - 1, -1):
            supports = self.thresholds(z)
            upper = max(supports.values())
            if upper <= left:
                continue
            levels.append((z, supports))
            points.update(v for v in supports.values() if left < v < float('inf'))
            left = upper
            if left == float('inf'):
                break
        result = []
        previous = None
        for point in sorted(points):
            at = next((z, tuple(s for s in SUPPORT if s in vals and vals[s] >= point))
                      for z, vals in levels if max(vals.values()) >= point)
            right = next((z, tuple(s for s in SUPPORT if s in vals and vals[s] > point))
                         for z, vals in levels if max(vals.values()) > point)
            if point == 0 or at != previous or right != at:
                result.append(dict(premium_exact=str(point), premium=float(point), z_at=at[0],
                                   supports_at='|'.join(at[1]), z_right=right[0],
                                   supports_right='|'.join(right[1]), z_left=previous[0] if previous else None,
                                   supports_left='|'.join(previous[1]) if previous else ''))
            previous = right
        return result
