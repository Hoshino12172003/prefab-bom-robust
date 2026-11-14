"""Freeze the Phase 3.2P parameter protocol before starting any solver."""
import hashlib
import json
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHASE_B = ROOT / "artifacts/v3_phase32b_20261111_214914"
sys.path.insert(0, str(PHASE_B))
from profile_runs import FROZEN, prior, verify_frozen
from design import ARCS, Event, Scenario, de_scenarios, overlap_scenarios, scenarios
from prefab_v3.robust import Episode, UncertaintySet

PROTOCOL = HERE / "frozen_policy_grid.json"
PIN = HERE / "frozen_policy_grid.sha256"
BASELINE = "BASE_B100"
B_MULTIPLIERS = (25, 50, 75, 100, 125, 150, 200)
SEVERITIES = (25, 50, 75)
DURATIONS = (4, 7, 11)
COST_LEVELS = (80, 90, 100, 110, 120)
LOCATIONS = {
    "R1": ("B_RECEIPT",), "R2": ("B_PROD",), "R3": ("B_SHIP",),
    "R4": ("GEAR",), "R5": ("SEAT",), "R6": ("B_RECEIPT", "GEAR", "SEAT"),
}
REFERENCE = (50, 7)
GAMMA_CATALOG = ("NR", "BE", "BS", "DE_ENGINE_61", "B_PROD_4", "B_SHIP_4",
                 "BGS", "B_PROD_E_S", "BGS_OVERLAP")
ATTACHMENT = Path.home() / "private_inputs/attachment/已粘贴的文本.txt"


def events_of(s):
    return [(e.resource, e.start, e.duration, str(e.severity)) for e in s.events]


def build_protocol():
    source = {s.name: s for s in [*de_scenarios(), *scenarios(), *overlap_scenarios()]}
    baseline = [s.name for s in de_scenarios()[:4]]
    profiles = {n: dict(events=events_of(s), recovery=0) for n, s in source.items()
                if n in {*baseline, *GAMMA_CATALOG}}
    cases = {}

    def add(name, risk, names, initial, tags, budget_multiplier=100, severity=None, duration=None,
            recovery=0, gamma=None, t_factor=100, o_factor=100):
        costs = (F(1), prior.COSTS[1]*F(t_factor)/100,
                 prior.COSTS[1]*F(t_factor)/100*F(11, 10)*F(o_factor)/100)
        cases[name] = dict(case=name, risk=risk, scenarios=names, initial=initial, tags=tags,
            budget_multiplier=budget_multiplier, budget=str(prior.BUDGET*F(budget_multiplier)/100),
            severity=severity, duration=duration, recovery=recovery, gamma=gamma,
            alpha_T_multiplier=t_factor, alpha_O_multiplier=o_factor, costs=[str(c) for c in costs])

    for b in B_MULTIPLIERS:
        add(f"BASE_B{b}", "BASE4", baseline, [prior.BASELINE, prior.SEVERE],
            ["BASE_BUDGET", *(["COST"] if b == 100 else [])], budget_multiplier=b)
    for loc, branches in LOCATIONS.items():
        for s in SEVERITIES:
            for d in DURATIONS:
                name = f"{loc}_S{s}_D{d}_ABRUPT"
                profiles[name] = dict(events=[(r, 64, d, str(F(s, 100))) for r in branches], recovery=0)
                bs = B_MULTIPLIERS if (s, d) == REFERENCE else (100,)
                for b in bs:
                    tags = (["LOCATION_BUDGET"] if (s, d) == REFERENCE else []) + (["SEVERITY_DURATION"] if b == 100 else [])
                    add(f"{name}_B{b}", loc, ["NR", name], [name], tags, b, s, d)
        if loc in ("R1", "R2", "R3"):
            name = f"{loc}_S50_D7_GRADUAL"
            profiles[name] = dict(events=[(branches[0], 64, 7, "1/2")], recovery=2)
            add(f"{name}_B100", loc, ["NR", name], [name], ["RECOVERY"], severity=50, duration=7, recovery=2)

    for t in COST_LEVELS:
        for o in COST_LEVELS:
            if (t, o) != (100, 100):
                add(f"COST_T{t}_O{o}", "BASE4", baseline, [prior.BASELINE, prior.SEVERE], ["COST"],
                    t_factor=t, o_factor=o)
    for gamma in (2, 4, 6):
        names = [n for n in GAMMA_CATALOG if source[n].exposure <= gamma]
        add(f"GAMMA_{gamma}", "GAMMA_MENU", names, ["BS"], ["GAMMA"], gamma=gamma)
    anchors = [BASELINE, *(f"{loc}_S50_D7_ABRUPT_B100" for loc in LOCATIONS)]
    return dict(label="STRESS_TEST_ONLY", cost_label="COST_SENSITIVITY_ONLY",
        model="V3 historical t=60 source; complete t=61..74 integer recourse; frozen PLAIN_EXACT_CCG",
        budget_base=str(prior.BUDGET), starting_costs=[str(c) for c in prior.COSTS],
        scenarios=profiles, cases=cases, ablation_anchors=anchors,
        initialization="BASE4 uses frozen informed start; R1-R6 start at declared shock; Gamma starts BS",
        threshold_rule=dict(
            trigger="Adjacent main COST cells switch a downstream coordinate between impossible and required in optimal set",
            scan="For each ratio axis choose first qualifying edge ordered by fixed-other ratio then ascending axis",
            design="Evaluate all three quarter subdivisions of that edge, and +/- half component-budget unit at both endpoints",
            proportions=["1/4", "1/2", "3/4"], budget_offsets=["-1/2", "1/2"],
            classification="Local discrete brackets only. Compare to +/-1/2 budget; no monotonicity or universal breakpoint assumed."),
        assembly_rule="Complete grid outputs remain visible, including failures and all optimal range witnesses")


def freeze():
    previous = verify_frozen()
    manifest = PHASE_B / "sha256_manifest.csv"
    rows = FROZEN.read(manifest)
    assert all(FROZEN.digest(ROOT / r["path"]) == r["sha256"] for r in rows)
    previous[PHASE_B.name] = dict(entries=len(rows), manifest_sha256=FROZEN.digest(manifest))
    data = build_protocol()
    data.update(previous=previous, instruction_sha256=FROZEN.digest(ATTACHMENT))
    if not PROTOCOL.exists():
        with PROTOCOL.open("x", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")
        with PIN.open("x", encoding="ascii") as file:
            file.write(FROZEN.digest(PROTOCOL)+"\n")
    else:
        assert load() == json.loads(json.dumps(data))
    print("Frozen cases", len(data["cases"]), "ablation jobs", len(data["ablation_anchors"])*3,
          "protocol SHA-256", FROZEN.digest(PROTOCOL))


def load():
    payload = PROTOCOL.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == PIN.read_text(encoding="ascii").strip()
    return json.loads(payload)


def profile(name, record, base, opening):
    s = Scenario(name, tuple(Event(r, t, d, F(f)) for r, t, d, f in record["events"]))
    s.validate()
    if not record["recovery"]:
        return FROZEN.data_for(s, opening, base)
    # Reuse the frozen two-step Phase 3.1 battery recovery curve, with Phase 3.1R integer rounding.
    event, = s.events
    periods = base.network.periods
    u = UncertaintySet(periods, (event.duration,), (event.severity,), event.duration, 1, record["recovery"])
    curve = dict(zip(periods, u.factors(Episode(event.start, event.duration, event.severity))))
    if event.resource == "B_RECEIPT":
        arrivals = {k: int(q*curve[k[2]]) if k[0] == FROZEN.PROD and k[1] in FROZEN.CELL else q
                    for k, q in opening.items()}
        return arrivals, {}
    arc = ARCS[event.resource]
    cap = next(a.capacity for a in base.network.arcs if a.key == arc)
    return dict(opening), {(*arc, t): F(int(cap[t]*f), cap[t]) for t, f in curve.items() if f != 1 and cap[t]}


if __name__ == "__main__":
    freeze()
