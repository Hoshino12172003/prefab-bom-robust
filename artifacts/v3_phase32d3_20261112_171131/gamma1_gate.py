"""Check the first-stage value and complete worst-RHS sets before larger runs."""

from prepare import HERE, frozen_catalog, policies, read


def main():
    rows = []
    for p in policies():
        ref = read(HERE / f"reference/gamma1_{p}/G1_N355.json")
        ans = read(HERE / f"search/{p}_G1_N355_L2/result.json")
        assert ref["exact"] and ans["exact"] and ref["rhs_count"] == ans["rhs_count"] == 355
        assert ref["full_milp"] == 355
        assert ref["worst_rhs_complete"] and ans["worst_rhs_complete"]
        assert ref["worst"] == ans["worst"] and ref["worst_rhs"] == ans["worst_rhs"]
        rows.append(dict(policy=p, W=ref["worst"], worst_rhs=ref["worst_rhs"]))
    frozen_catalog.dump(HERE / "gamma1_gate.json", rows)
    print("Gamma=1 exact value and complete worst RHS sets matched for all four policies.")


if __name__ == "__main__":
    main()
