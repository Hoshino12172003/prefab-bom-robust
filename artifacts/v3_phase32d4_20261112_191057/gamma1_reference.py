"""Exhaustively certify the returned Gamma=1 policy and retain all DE starts."""

from concurrent.futures import ProcessPoolExecutor
from time import perf_counter

import numpy as np

from run import HERE, SOURCE, Coordinates, Recourse, frozen_catalog, read
from prepare import explicit_classes


OUT = HERE / "gamma1_enum"


def shard(item):
    i, x, codes = item
    SOURCE.init()
    coords = Coordinates()
    out = OUT / f"part_{i}"
    with SOURCE.env() as env:
        solver = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, out / "logs")
        try:
            vectors = np.empty((len(codes), 75810), dtype=np.int32)
            services = []
            for j, code in enumerate(codes):
                w = solver.solve(coords.code_profile(code), f"rhs_{code}", capture_vector=True)
                vectors[j] = w.vector
                assert np.array_equal(vectors[j], w.vector)
                services.append(dict(rhs=code, service=w.q, **solver.calls[-1]))
                if (j+1) % 15 == 0:
                    print(i, j+1, "/", len(codes), flush=True)
            np.savez_compressed(out / "vectors.npz", rhs=codes, vectors=vectors)
            frozen_catalog.dump(out / "results.json", services)
        finally:
            solver.close()
    return [(r["rhs"], r["service"]) for r in services]


def main():
    started = perf_counter()
    solved = read(HERE / "outer/G1/result.json")
    x = tuple(solved["policy"])
    coords = Coordinates()
    codes = sorted({0, *(a.code for a in coords.atoms)})
    all_ids, m, _ = explicit_classes(coords)
    assert len(codes) == 355 and list(all_ids[m[:2].sum(axis=0) > 0]) == codes
    n_workers = 4
    jobs = [(i, x, codes[i::n_workers]) for i in range(n_workers)]
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        records = dict(r for part in pool.map(shard, jobs) for r in part)
    w = min(records.values())
    ties = sorted(k for k, q in records.items() if q == w)
    assert len(records) == 355 and w == solved["objective"]
    assert ties == solved["final_oracle"]["worst_rhs"]
    frozen_catalog.dump(OUT / "summary.json", dict(policy=x, exact=True, rhs_count=len(records), worst=w,
        worst_rhs=ties, seconds=perf_counter()-started, workers=n_workers, services=records))
    print("Gamma=1 fixed policy verified on all", len(records), "RHS; W", w, flush=True)


if __name__ == "__main__":
    main()
