"""Compare exact effective arc-period RHS values over the frozen horizon."""

import argparse
import sys
from pathlib import Path

def capacity_vectors(op, scenarios):
    group_caps = op.base.network.group_caps
    return {s: {k: min(int(cap*profile.get(k,1)), group_caps.get(k,cap))
                for k,cap in op.nominal.items()} for s,profile in scenarios.items()}


def certify_cover(vectors):
    ids = sorted(vectors)
    keys = vectors[ids[0]].keys()
    assert all(v.keys()==keys for v in vectors.values())
    roots = {s:[] for s in ids}
    pairs = []
    for s in ids:
        for t in ids:
            if s==t:
                continue
            low, high = vectors[s], vectors[t]
            less = next((k for k in keys if low[k]<high[k]), None)
            greater = next((k for k in keys if low[k]>high[k]), None)
            covers = greater is None
            strict = covers and less is not None
            if strict or (covers and s<t):
                roots[t].append(s)
            pairs.append(dict(harder=s, other=t, covers=covers, strict=strict,
                example_lower=str(less or ""), example_higher=str(greater or "")))
    keep = [s for s in ids if not roots[s]]
    cover = {s: s if s in keep else min(set(roots[s]) & set(keep)) for s in ids}
    return keep, cover, pairs


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v33_gate4a_plain_ccg"))
    from common import frozen_inputs, write_csv, write_json

    p = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "xlsb", "out"):
        p.add_argument("--"+name, type=Path, required=True)
    args = p.parse_args()
    op, _, _, scenarios, meta = frozen_inputs(args.xlsb,args.bundle)
    args.out.mkdir(parents=True)
    summary = {}
    for gamma, catalog in scenarios.items():
        vectors = capacity_vectors(op, catalog)
        keep, cover, pairs = certify_cover(vectors)
        write_csv(args.out, f"gamma{gamma}_pairs.csv", pairs)
        write_csv(args.out, f"gamma{gamma}_cover.csv",
            [dict(scenario=s, representative=t, retained=s==t) for s,t in cover.items()])
        summary[str(gamma)] = dict(scenarios=len(catalog), retained=keep, rows=len(op.nominal),
            period_first=op.periods[0], period_last=op.periods[-1],
            strict_ordered_pairs=sum(r["strict"] for r in pairs))
    write_json(args.out,"audit.json",dict(metadata=meta, sets=summary))
    print(summary)


if __name__ == "__main__":
    main()
