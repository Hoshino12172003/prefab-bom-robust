"""Record exact exits of individual optimal portfolios, including within a support type."""
import csv
import gzip
import io
from collections import defaultdict
from fractions import Fraction

import numpy as np

from frontier import HERE, LABEL, Frontier


def expirations(frontier, z, left, inclusive):
    """Yield each finite exact threshold and the number of portfolios that expire there."""
    p = frontier.ratio.numerator
    high = (frontier.remaining*left.denominator - int(not inclusive)) // (
        p*(left.denominator+left.numerator))
    low = np.maximum(1, z-frontier.base)
    counts = high-low+1
    pairs = np.flatnonzero(counts > 0)
    if not pairs.size:
        return
    repetitions = counts[pairs]
    i = np.repeat(pairs, repetitions)
    offsets = np.arange(repetitions.sum())-np.repeat(np.cumsum(repetitions)-repetitions, repetitions)
    d = p*(low[i]+offsets)
    n = frontier.remaining[i]-d
    divisor = np.gcd(n, d)
    radix = frontier.budget_scaled+1
    keys, multiplicities = np.unique((n//divisor)*radix+d//divisor, return_counts=True)
    for key, count in zip(keys, multiplicities):
        yield Fraction(int(key//radix), int(key % radix)), int(count)


def main():
    groups = defaultdict(list)
    with (HERE/'position_premium_breakpoints.csv').open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            groups[row['risk'], row['days'], row['k'], row['ratio']].append(row)
    summary = []
    with gzip.GzipFile(filename=str(HERE/'optimal_portfolio_expiration_events.csv.gz'), mode='wb', mtime=0) as raw:
        with io.TextIOWrapper(raw, encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(('label', 'risk', 'days', 'k', 'ratio', 'z_at', 'premium_exact',
                             'expired_immediately_after', 'service_change'))
            for (risk, days, k, ratio), events in groups.items():
                frontier = Frontier(risk, int(k), Fraction(ratio))
                intervals = [(Fraction(e['premium_exact']), int(e['z_at']))
                             for e in events if e['z_at'] != e['z_right']]
                intervals.append((None, int(events[-1]['z_right'])))
                left, inclusive = Fraction(0), True
                first, distinct, total = None, 0, 0
                for right, z in intervals:
                    for premium, count in expirations(frontier, z, left, inclusive):
                        assert (premium >= left if inclusive else premium > left) and (right is None or premium <= right)
                        writer.writerow((LABEL, risk, days, k, ratio, z, str(premium), count, premium == right))
                        first = premium if first is None else min(first, premium)
                        distinct += 1
                        total += count
                    left, inclusive = right, False
                summary.append((LABEL, risk, days, k, ratio, str(first) if first is not None else '',
                                distinct, total))
    with (HERE/'optimal_portfolio_expiration_summary.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(('label', 'risk', 'days', 'k', 'ratio', 'first_portfolio_exit_premium',
                         'distinct_exit_events', 'expiring_portfolios'))
        writer.writerows(summary)


if __name__ == '__main__':
    main()
