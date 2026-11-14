"""Independent full-matrix checks for the mapping and an artificial envelope."""

import json
from itertools import combinations

from prepare import HERE, SOURCE, Coordinates, frozen_catalog, policies
from recourse import Recourse


def main():
    SOURCE.init()
    coords = Coordinates()
    profiles = [next(e.profile for e in coords.ordered if e.resource == i and e.code)
                for i in range(len(coords.resources))]
    envelope = tuple(map(min, zip(*(e.profile for e in coords.atoms))))
    collision = None
    for a, b in combinations((e for e in coords.atoms if e.resource == 0 and e.code), 2):
        if a.code != b.code or a.mask == b.mask:
            continue
        for c in (e for e in coords.atoms if e.resource == 3):
            for d in (e for e in coords.atoms if e.resource == 4):
                if bool(a.mask & c.mask & d.mask) != bool(b.mask & c.mask & d.mask):
                    collision = dict(equivalent_single_atoms=[a.id, b.id], other_atoms=[c.id, d.id],
                                     shared_rhs=a.code, first_legal=not bool(a.mask & c.mask & d.mask),
                                     second_legal=not bool(b.mask & c.mask & d.mask))
                    break
            if collision:
                break
        if collision:
            break
    assert collision is not None
    audit = []
    for p, x in policies().items():
        out = HERE / "mapping_audit" / p
        with SOURCE.env() as env:
            solver = Recourse(env, SOURCE.BASE, SOURCE.OPENING, coords, x, out / "logs")
            try:
                solver.verify_against_builder([*profiles, envelope])
                witness = solver.solve(envelope, "root_envelope", capture_vector=True)
                assert all(solver.feasible(witness, e.profile) for e in coords.atoms)
                for q in profiles:
                    solver.replay_matrix(witness, q)
                frozen_catalog.dump(out / "solver_calls.json", solver.calls)
                audit.append(dict(policy=p, inventory_headroom=solver.proof, row_checks=7,
                                  all_atomic_profiles_pass_envelope_witness=True,
                                  full_matrix_replays=len(profiles), envelope_service=witness.q))
                print(p, "envelope service", witness.q, flush=True)
            finally:
                solver.close()
    (HERE / "mapping_audit.json").write_text(json.dumps(dict(atomic_collision=collision, policies=audit),
                                                       indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
