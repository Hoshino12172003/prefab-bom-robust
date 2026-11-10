"""The six authorized formal-scale Phase 1 runs."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
from zipfile import ZipFile

from .data import BUFFER_NAMES, Scenario
from .source import SOURCE_SHA256

MANIFEST_SHA256 = "dc252572092ccd7003b33fb84c6d075658862c5f58c988530fca7f96db1b6044"
MEMBER = "paper_scale_v2/manifest.json"


def manifest_bytes(path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            if archive.namelist().count(MEMBER) != 1:
                raise ValueError("expected one exact paper_scale_v2/manifest.json")
            payload = archive.read(MEMBER)
    else:
        payload = path.read_bytes()
    if sha256(payload).hexdigest() != MANIFEST_SHA256:
        raise ValueError("frozen Phase 1 manifest SHA-256 mismatch")
    return payload


@dataclass(frozen=True)
class Run:
    budget_id: str
    de: bool
    budget: float
    costs: tuple
    scenarios: tuple

    @property
    def id(self):
        return f"{'DE' if self.de else 'nominal'}_{self.budget_id}"


def frozen_runs(payload):
    if sha256(payload).hexdigest() != MANIFEST_SHA256:
        raise ValueError("frozen Phase 1 manifest SHA-256 mismatch")
    data = json.loads(payload)
    buffers = data["first_stage_buffers"]
    matrix = data["formal_scale_run_matrix"]
    if (data["status"] != "FROZEN_FOR_PHASE1_FORMAL_SCALE_CERTIFICATION"
            or data["source"]["source_xlsb_sha256"] != SOURCE_SHA256
            or tuple(buffers["variables"]) != BUFFER_NAMES
            or not buffers["integer"] or not matrix["integer_recourse"]
            or not data["hard_stop"]["after_phase1"]):
        raise ValueError("manifest does not authorize this formal integer model")
    scenarios = {}
    for row in data["risk_scenarios"]:
        start, end = row["start_t"], row["end_t"]
        fields = ("arrival_multiplier", "pack_prod_capacity_multiplier", "pack_transport_capacity_multiplier")
        if start is None and end is None:
            if any(row[field] != 1 for field in fields):
                raise ValueError("undated scenario must be nominal")
            periods = ()
        else:
            if not 61 <= start <= end <= 74:
                raise ValueError("scenario outside frozen horizon")
            periods = range(start, end + 1)
        scenarios[row["scenario_id"]] = Scenario(row["scenario_id"], *(
            dict.fromkeys(periods, row[field]) for field in fields))
    budgets = {row["id"]: row["usd"] for row in buffers["budget_grid"]}
    costs = tuple(buffers["costs_usd"][name] for name in BUFFER_NAMES)
    return tuple(
        Run(label, de, budgets[label], costs, tuple(scenarios[s] for s in ids))
        for de, labels, ids in (
            (False, matrix["deterministic_nominal_budget_ids"], ("NOM",)),
            (True, matrix["full_scenario_DE_budget_ids"], matrix["full_scenario_set"]),
        )
        for label in labels
    )


def solve_frozen(network, payload, run_id, **solver_settings):
    from .model import _solve
    run, = (run for run in frozen_runs(payload) if run.id == run_id)
    if network.source_sha256 != SOURCE_SHA256 or network.periods != tuple(range(61, 75)):
        raise ValueError("formal run requires the verified paper-scale network")
    return _solve(network, run.scenarios, run.budget, run.costs, de=run.de,
                  formal=(payload, run_id), **solver_settings)
