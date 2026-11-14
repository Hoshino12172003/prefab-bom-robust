from itertools import combinations

from prefab_v3.event_search import Atom, Space, search


NOMINAL = (9, 9, 9)
ATOMS = (
    Atom(1, 0, 0b0011, (4, 9, 9), 1, 1),
    Atom(2, 0, 0b1100, (4, 9, 9), 1, 1),
    Atom(3, 1, 0b0011, (9, 4, 9), 128, 2),
    Atom(4, 2, 0b0011, (9, 9, 4), 16384, 4),
    Atom(5, 2, 0b1100, (9, 9, 4), 16384, 4),
    Atom(6, 1, 0b1100, (9, 1, 9), 256, 8),
)


def exact_service(rhs):
    return min(rhs[0], rhs[1]) + rhs[2]


def exhaustive(gamma, threshold):
    outcomes = {}
    for k in range(gamma+1):
        for chosen in combinations(ATOMS, k):
            if len({e.resource for e in chosen}) != k:
                continue
            if any(sum(bool(e.mask & (1 << t)) for e in chosen) > 2 for t in range(4)):
                continue
            if threshold is not None and sum(e.rank for e in chosen) > threshold:
                continue
            outcomes[tuple(e.id for e in chosen)] = (
                sum(e.code for e in chosen), exact_service(tuple(map(min, zip(NOMINAL, *(e.profile for e in chosen)))))
            )
    return outcomes


def test_bounds_and_tree_match_independent_enumeration():
    for gamma in (1, 2, 3):
        for threshold in (None, 7, 13):
            outcomes = exhaustive(gamma, threshold)
            visited = set()

            def record(action, node, bound, incumbent):
                if action != "visit":
                    return
                ids = tuple(e.id for e in node.selected)
                assert ids in outcomes
                visited.add(ids)

            space = Space(ATOMS, NOMINAL, gamma, threshold)
            plain = search(space, lambda p, _: exact_service(p), lambda *_: 0, record, keep_ties=True)
            assert set(outcomes) == visited
            q = min(v for _, v in outcomes.values())
            assert plain["worst"] == q
            bounded = search(space, lambda p, _: exact_service(p),
                             lambda node, _: exact_service(node.envelope()), record, keep_ties=True)
            assert bounded["exact"] and bounded["worst_rhs_complete"]
            assert bounded["worst"] == q
            assert bounded["worst_rhs"] == sorted({c for c, v in outcomes.values() if v == q})


def test_equal_single_rhs_retains_different_triple_legality():
    outcomes = exhaustive(3, None)
    assert ATOMS[0].profile == ATOMS[1].profile
    assert (1, 3, 4) not in outcomes and (2, 3, 4) in outcomes


def test_capped_search_preserves_unresolved_frontier():
    result = search(Space(ATOMS, NOMINAL, 3), lambda p, _: exact_service(p),
                    lambda *_: 0, lambda *_: None, node_limit=1)
    assert not result["exact"] and not result["worst_rhs_complete"]
    assert result["stop"] == "node limit" and result["frontier"]
    assert result["lower_bound"] <= min(v for _, v in exhaustive(3, None).values()) <= result["worst"]
