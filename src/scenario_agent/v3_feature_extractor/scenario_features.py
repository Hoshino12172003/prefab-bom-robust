"""Raw event encoding and independently verified integer-RHS identities."""
from fractions import Fraction
import hashlib
import json

from .manifest import PHASE_B, MODEL_INSTANCE_ID
from .schema import RESOURCES, RESOURCE_ARCS, PERIODS, CELL, ScenarioV3, FeatureSpec
from .source import read_csv
from .network_features import risk_reach, due_groups


def signature(network, events):
    arcs = {a.key: a for a in network.base.network.arcs}
    changes = {}
    resources = set()
    for resource, start, duration, severity in events:
        if resource not in RESOURCES or resource in resources or not 0 < Fraction(severity) <= 1:
            raise ValueError("Unknown, duplicated or invalid V3 risk resource")
        resources.add(resource)
        if type(start) is not int or type(duration) is not int or duration < 1 or not set(range(start, start+duration)) <= set(PERIODS):
            raise ValueError("V3 risk window conflict")
        for t in range(start, start+duration):
            if resource == "B_RECEIPT":
                values = [(('receipt', *k), v) for k, v in network.opening.items()
                          if k[0] == "battery-supplier_prod" and k[1] in CELL and k[2] == t]
            else:
                i, j = RESOURCE_ARCS[resource]
                values = [(('capacity', i, j, t), arcs[i, j].capacity[t])]
            for key, nominal in values:
                effective = int(nominal*(1-Fraction(severity)))
                if effective != nominal:
                    changes[key] = effective
    return tuple(sorted(changes.items()))


def rhs_hash(changes):
    return hashlib.sha256(json.dumps(changes, separators=(",", ":")).encode()).hexdigest()


def load_scenarios(network):
    directory = network.root / PHASE_B
    patterns = {r["scenario"]: r for r in read_csv(directory / "risk_pattern_signature.csv")}
    result = {}
    rows = read_csv(directory / "rhs_equivalence_audit.csv")
    for r in rows:
        events = tuple(tuple(v) for v in json.loads(r["raw_events"]))
        changes = signature(network, events)
        if rhs_hash(changes) != r["effective_rhs_sha256"] or json.loads(json.dumps(changes)) != json.loads(
                patterns[r["scenario"]]["effective_capacity_availability"]):
            raise ValueError("Risk signature conflict")
        result[r["scenario"]] = ScenarioV3(MODEL_INSTANCE_ID, r["scenario"], r["representative"],
                                            r["effective_rhs_sha256"], events, changes)
    if len(rows) != len(result) or len(result) != 40 or len({s.rhs_id for s in result.values()}) != 38:
        raise ValueError("Risk catalog count conflict")
    for name, s in result.items():
        if result[s.representative].rhs_id != s.rhs_id:
            raise ValueError(f"Alias conflict: {name}")
    return result


SPECS = [FeatureSpec("scenario_event_count", "int64", "event_count", "len(raw_events)", "raw_events"),
    FeatureSpec("scenario_changed_rows", "int64", "RHS_row_count", "len(integer changes)", "verified signature"),
    FeatureSpec("scenario_is_nominal_rhs", "int64", "boolean", "integer signature is empty", "verified signature")]
for resource in RESOURCES:
    for name, dtype, unit, formula, nullable in (
        ("present", "int64", "boolean", "resource in events", False),
        ("severity_loss", "float64", "fraction", "event severity loss", True),
        ("start_offset", "int64", "period", "start-61", True),
        ("duration", "int64", "period", "duration", True),
        ("changed_rows", "int64", "RHS_row_count", "effective changed rows of resource", False),
        ("mean_effective_loss_rate", "float64", "fraction", "mean((nominal-effective)/nominal) over changed positive-nominal rows", True),
    ):
        SPECS.append(FeatureSpec(f"risk_{resource}_{name}", dtype, unit, formula, "raw_events + original capacity/receipts", nullable))
SPECS += [FeatureSpec("risk_reachable_skus", "int64", "SKU_count", "distinct non-car SKU reachable by 74", "V3 recipe graph"),
    FeatureSpec("risk_reachable_orders", "int64", "vehicle", "sum(cohort sizes reachable before due)", "V3 recipe graph + due"),
    FeatureSpec("risk_reachable_configs", "int64", "configuration_count", "distinct BOM of exposed cohorts", "V3 BOM"),
    FeatureSpec("risk_first_delivery_period", "int64", "period_index", "min potential arrival among exposed cohorts", "V3 recipe graph + due", True)]
SPECS += [FeatureSpec(f"risk_due_{t}", "int64", "boolean", f"any exposed cohort due={t}", "V3 demand + graph") for t in PERIODS]
SPECS = tuple(SPECS)


def extract(network, scenario):
    arcs = {a.key: a for a in network.base.network.arcs}
    out = dict(scenario_event_count=len(scenario.events), scenario_changed_rows=len(scenario.changes),
               scenario_is_nominal_rhs=int(not scenario.changes))
    events = {e[0]: e for e in scenario.events}
    for resource in RESOURCES:
        e = events.get(resource)
        rows = [(k, v) for k, v in scenario.changes if (k[0] == "receipt" if resource == "B_RECEIPT"
                else k[0] == "capacity" and k[1:3] == RESOURCE_ARCS[resource])]
        rates = []
        for k, effective in rows:
            nominal = network.opening[k[1:]] if k[0] == "receipt" else arcs[k[1:3]].capacity[k[3]]
            rates.append(Fraction(nominal-effective, nominal))
        prefix = f"risk_{resource}_"
        out.update({prefix+"present": int(e is not None), prefix+"severity_loss": float(Fraction(e[3])) if e else None,
            prefix+"start_offset": e[1]-61 if e else None, prefix+"duration": e[2] if e else None,
            prefix+"changed_rows": len(rows), prefix+"mean_effective_loss_rate": float(sum(rates)/len(rates)) if rates else None})
    earliest = risk_reach(network, scenario)
    groups = due_groups(network, earliest)
    out.update(risk_reachable_skus=len({p for (_, p), t in earliest.items() if t <= 74 and network.base.products[p] != "car"}),
        risk_reachable_orders=sum(len(g.orders) for g in groups.values()),
        risk_reachable_configs=len({g.representative.bom for g in groups.values()}),
        risk_first_delivery_period=min((earliest[g.representative.node, g.id] for g in groups.values()), default=None))
    out.update({f"risk_due_{t}": int(any(g.representative.due == t for g in groups.values())) for t in PERIODS})
    return out
