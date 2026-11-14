"""Check every eta=1 optimum against path throughput identities for this case."""

import argparse
import csv
from collections import Counter
from pathlib import Path


def verify(folder):
    with (folder / "gate2b_arc_capacity_mapping.csv").open(encoding="utf-8") as f:
        arcs = {(r["origin"], r["destination"]): int(r["integer_rhs"]) for r in csv.DictReader(f)}
    with (folder / "gate2b_buffer_formation_limits.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len({(r["node_id"], r["item_id"], r["H"]) for r in rows}) == 455
    evidence = []
    for r in rows:
        n, p, g, h = r["node_id"], r["item_id"], r["group"], int(r["H"])
        lead, headroom = int(r["minimum_H"]), int(r["terminal_headroom"])
        slots = max(0, h - lead + 1)
        resources = []
        if g in ("engine", "gear"):
            prod = (f"{g}-supplier_prod", f"{g}-supplier_inv")
            resources = [prod] if n == prod[1] else [prod, (prod[1], "zp7")]
            throughput = slots * min(arcs[a] for a in resources)
        elif g in ("battery", "battery_componment"):
            supply = ("battery-supplier_trans", "battery-supplier_prod")
            kit = (10, 6, 4)
            component = g == "battery_componment"
            throughput = slots * arcs[supply] // sum(kit)
            if component:
                throughput = min(throughput, *(int(sibling["terminal_headroom"]) // unit
                                 for suffix, unit in enumerate(kit, 1) for sibling in rows
                                 if sibling["item_id"] == f"componment_battery{suffix}" and int(sibling["H"]) == h))
                throughput *= kit[int(p[-1])-1]
            else:
                path = [("battery-supplier_prod", "battery-supplier_inv")]
                if n == "zp7":
                    path.append(("battery-supplier_inv", "zp7"))
                assert all(arcs[a] >= -(-arcs[supply] // sum(kit)) for a in path)
            resources = [supply]
        else:
            assert g in ("seat", "seat_componment")
            supply = ("seat-supplier_trans", "seat-supplier_prod")
            path = [supply, ("seat-supplier_prod", "seat-supplier_inv"), ("seat-supplier_inv", "zp7")]
            resources = path[:1 if n == supply[1] else 3 if n == "zp7" else 2]
            throughput = slots * min(arcs[a] for a in resources)
        exact = min(throughput, headroom)
        assert r["status"] == "PASS" and r["solver_status"] == "OPTIMAL" and float(r["mip_gap"]) == 0
        assert exact == int(r["Bmax"]) == float(r["best_bound"]), (n, p, h, exact, r["Bmax"])
        if not slots:
            reason = "LEAD_TIME"
        elif exact == headroom:
            reason = "TERMINAL_HEADROOM"
        elif g in ("battery", "battery_componment"):
            reason = "UPSTREAM_TRANSPORT_AND_COMPLETE_KIT"
        else:
            limiting = {a for a in resources if arcs[a] == min(arcs[k] for k in resources)}
            reason = "+".join(sorted({"PRODUCTION" if i.endswith("_prod") else "TRANSPORT" for i, _ in limiting}))
            resources = sorted(limiting)
        evidence.append(dict(node_id=n, item_id=p, H=h, Bmax=exact, proof=reason,
                             route_resources=";".join(f"{i}->{j}" for i,j in resources)))
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    proof = verify(args.folder)
    with (args.folder / "gate2b_path_bound_verification.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(proof[0]))
        writer.writeheader()
        writer.writerows(proof)
    print(f"{len(proof)} independently checked bounds: {dict(Counter(r['proof'] for r in proof))}")
