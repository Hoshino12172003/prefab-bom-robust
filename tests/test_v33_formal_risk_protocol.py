import hashlib
import json
from fractions import Fraction

import pytest

from experiments.configs import audit_v33_formal_risk_protocol as protocol


def config():
    return json.loads(protocol.CONFIG.read_bytes())


def test_static_protocol_agrees_with_all_machine_artifacts():
    for filename, content in protocol.audit().items():
        assert (protocol.HERE / filename).read_bytes() == content
    report = json.loads((protocol.HERE / "v33_formal_risk_static_audit.json").read_bytes())
    assert set(report["checks"]) == {f"P-{i:02}" for i in range(1, 13)}
    assert all(v == "PASS" for v in report["checks"].values())
    assert report["FORMAL_RISK_PROTOCOL_FROZEN"] and report["READY_FOR_GATE4"]
    assert report["formal_optimization_calls"] == 0 and not report["gate4_executed"]


def test_compatibility_includes_recovery_and_disjoint_level_rule():
    a = dict(event_id="a", asset="i->j", level="moderate", start=67, duration=4, recovery=2)
    b = {**a, "event_id": "b", "start": 72}
    assert protocol.compatible(a, a) == "DUPLICATE_ATOM"
    assert protocol.compatible(a, b) == "SAME_ASSET_ACTIVE_INTERVAL_OVERLAP"
    b["start"] = 73
    assert protocol.compatible(a, b) == "LEGAL"
    b["level"] = "severe"
    assert protocol.compatible(a, b) == "SAME_ASSET_DIFFERENT_LEVELS"
    b["asset"] = "j->k"
    assert protocol.compatible(a, b) == protocol.compatible(b, a) == "LEGAL"


def test_trajectory_identity_uses_exact_capacity_and_recovery_tail():
    first = ("i", "j", 74)
    second = ("i", "j", 75)
    other = ("j", "k", 75)
    nominal = {first: 0, second: 7, other: 14}
    assert protocol.capacity_key(nominal, {}) == protocol.capacity_key(nominal, {first: Fraction(1, 4)})
    assert protocol.capacity_key(nominal, {second: Fraction(1, 3)}) != protocol.capacity_key(nominal, {second: Fraction(1, 4)})
    assert protocol.capacity_key(nominal, {second: Fraction(1, 2)}) != protocol.capacity_key(nominal, {other: Fraction(1, 2)})
    e = protocol.Event("cross", ("i", "j"), "transport", 74, 1, Fraction(1, 4), 2)
    assert list(e.profile(range(61, 98)).values()) == [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]


@pytest.mark.parametrize(("plan", "expected"), [("CALENDAR_REPEAT", 0), ("MEAN_EXTENSION", Fraction(5, 7)),
                                                ("CONSERVATIVE_EXTENSION", Fraction(15, 28))])
def test_tail_protocol_changes_only_the_tail_and_includes_zeros(plan, expected):
    arc = ("i", "j")
    source = {arc: [0]*13 + [10]}
    capacities = protocol.nominal_capacities(source, plan, Fraction(3, 4))
    assert [capacities[(*arc, t)] for t in range(61, 75)] == source[arc]
    assert capacities[(*arc, 75)] == expected
    assert max(k[-1] for k in capacities) == 97


def test_budget_rule_is_exact_and_reference_is_conditional():
    rule = config()["budget"]
    profile = rule["reference_profile"]
    assert protocol.budget_grid(3, rule, profile) == [0, 1, 2, 3]
    assert protocol.budget_grid(0, rule, profile) == [0]
    assert rule["reference_anchor_cents"] in protocol.budget_grid(30_000_000, rule, profile)
    assert rule["reference_anchor_cents"] not in protocol.budget_grid(30_000_000, rule, {**profile, "H": 20})


def test_manifest_identifies_frozen_protocol_and_input_evidence():
    manifest = protocol.read_csv(protocol.HERE / "v33_formal_risk_sha256_manifest.csv")
    assert {r["kind"] for r in manifest} == {"protocol", "frozen_input"}
    assert len({r["path"] for r in manifest}) == len(manifest)
    for row in manifest:
        data = (protocol.ROOT / row["path"]).read_bytes()
        assert int(row["bytes"]) == len(data)
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
