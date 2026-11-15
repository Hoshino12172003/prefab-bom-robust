"""Build and verify the formal V3.3 protocol. No optimizer is imported or called."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
from fractions import Fraction
from itertools import combinations, combinations_with_replacement
from pathlib import Path

from experiments.v321_gate3_direct_de.event_catalog import Event


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = "2b16f8bbd33936ca754986b606c731a13e3b0758"
CONFIG = HERE / "v33_formal_risk_protocol.json"
GATE3 = ROOT / "experiments/v321_gate3_direct_de/evidence"
GATE35 = ROOT / "experiments/v321_gate35_risk_effectiveness/evidence"
GATE36 = ROOT / "experiments/v33_gate36_recovery_objective/evidence"
CAPACITY = ROOT / "experiments/v31_gate1_gate2b_certification/numerical/gate2b_arc_capacity_mapping.csv"
PRIOR_RISK = ROOT / "artifacts/v3_phase32d2_20261112_132513/parameter_evidence_classification.csv"
TOYOTA = "https://global.toyota/en/detail/11138722"
FORD = "https://www.sec.gov/Archives/edgar/data/37996/000003799618000047/exhibit99to516188k.htm"
AISIN = "https://merc.e.u-tokyo.ac.jp/mmrc/dp/pdf/MMRC433_2013.pdf"
RENESAS = "https://www.renesas.com/en/about/press-room/update-9-notice-regarding-semiconductor-manufacturing-factory-naka-factory-fire-production-capacity"
CLASSES = {"DIRECT", "LITERATURE", "TRANSFORM", "CALIBRATED", "SCENARIO", "MISSING"}


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def csv_bytes(rows):
    f = io.StringIO(newline="")
    writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return f.getvalue().encode("utf-8")


def catalog(config, originals):
    result = []
    for resource in config["core"]:
        original=originals[resource["family"]]
        assert original["asset"] == resource["asset"] and int(original["start"]) == resource["start"]
        for level, values in config["levels"].items():
            result.append(dict(event_id=f'{resource["family"]}_{level}',event_family=resource["family"],asset=resource["asset"],
                               asset_type=original["asset_type"],level=level,start=resource["start"],duration=values["duration"],
                               availability=values["availability"],recovery=values["recovery"],scope="CORE",
                               evidence_class=values["evidence_class"],sensitivity_status=values["sensitivity_status"]))
    for family in config["supplementary"]:
        r=originals[family]
        assert r["has_window_arrival"]=="False"
        result.append(dict(event_id=family,event_family=family,asset=r["asset"],asset_type=r["asset_type"],level="mapping",
                           start=int(r["start"]),duration=int(r["duration"]),availability=r["disruption_availability"],
                           recovery=int(r["recovery"]),scope="SUPPLEMENTARY",evidence_class="SCENARIO",
                           sensitivity_status="MAPPING_ONLY_TAIL_EFFECT_UNTESTED"))
    return result


def compatible(a,b):
    if a["event_id"]==b["event_id"]:
        return "DUPLICATE_ATOM"
    if a["asset"]!=b["asset"]:
        return "LEGAL"
    if a["level"]!=b["level"]:
        return "SAME_ASSET_DIFFERENT_LEVELS"
    if max(a["start"],b["start"]) < min(a["start"]+a["duration"]+a["recovery"],
                                        b["start"]+b["duration"]+b["recovery"]):
        return "SAME_ASSET_ACTIVE_INTERVAL_OVERLAP"
    return "LEGAL"


def nominal_capacities(source, protocol, conservative):
    result = {}
    for arc, values in source.items():
        mean = Fraction(sum(values),len(values))
        for period in range(61,98):
            cap = values[(period-61)%14]
            if period>=75 and protocol!="CALENDAR_REPEAT":
                cap=mean if protocol=="MEAN_EXTENSION" else conservative*mean
            result[(*arc,period)]=Fraction(cap)
    return result


def capacity_key(nominal, profile):
    return tuple(nominal[k]*profile.get(k,1) for k in sorted(nominal))


def subsets(core, budget, nominal):
    unique,mapping={},[]
    for size in range(budget+1):
        for atoms in combinations(core,size):
            label="+".join(r["event_id"] for r in atoms) or "NOM"
            reason=compatible(*atoms) if size==2 else "LEGAL"
            representative,digest="",""
            if reason=="LEGAL":
                multipliers={}
                for r in atoms:
                    e=Event(r["event_id"],tuple(r["asset"].split("->")),r["asset_type"],r["start"],r["duration"],
                            Fraction(r["availability"]),r["recovery"])
                    profile=e.profile(range(61,98))
                    assert not multipliers.keys() & profile.keys()
                    multipliers.update(profile)
                vector=capacity_key(nominal,multipliers)
                representative=unique.setdefault(vector,label)
                digest=hashlib.sha256(";".join(map(str,vector)).encode()).hexdigest()
            mapping.append(dict(gamma=budget,combination=label,atom_count=size,compatibility=reason,
                                canonical_scenario=representative,exact_capacity_sha256=digest))
    return unique,mapping


def budget_grid(ceiling_cents, config, profile):
    """Apply the frozen grid rule to an externally certified joint ceiling."""
    assert type(ceiling_cents) is int and ceiling_cents>=0
    grid={int(Fraction(q)*ceiling_cents) for q in config["grid_fractions"]}
    anchor=config["reference_anchor_cents"]
    if profile==config["reference_profile"] and anchor<=ceiling_cents:
        grid.add(anchor)
    return sorted(grid)


def evidence_rows(events, thresholds):
    rows=[]

    def add(family, asset, level, parameter, value, unit, cls, src, rationale, relation, status):
        rows.append(dict(event_family=family,asset=asset,level=level,parameter=parameter,value=value,unit=unit,
                         evidence_class=cls,source=src,rationale=rationale,gate35_threshold_relation=relation,formal_status=status))

    for r in events:
        family,asset,level=(r[k] for k in ("event_family","asset","level"))
        core=r["scope"]=="CORE"
        relation="MAPPING_ONLY" if not core else "OFF_GRID_D4; duration bracket 3 and 5" if level=="moderate" else "D7; a=1/4 bracketed by a=1/5 and a=2/5"
        if core:
            duration=int(r["duration"])
            local=[x for x in thresholds if x["resource"]==family]
            assert any(int(x["duration"])==7 and Fraction(x["availability"])==Fraction(1,5) for x in local)
            assert any(int(x["duration"])==7 and Fraction(x["availability"])==Fraction(2,5) for x in local)
            assert duration==7 or {3,5} <= {int(x["duration"]) for x in local}
        status="FROZEN_STRESS_SCENARIO" if core else "SUPPLEMENTARY_ONLY"
        add(family,asset,level,"asset",asset,"arc","DIRECT",str(CAPACITY.relative_to(ROOT).as_posix()),
            "Mapped to an observed source arc",relation,status)
        add(family,asset,level,"start",r["start"],"period","SCENARIO","experiments/v321_gate3_direct_de/evidence/event_catalog.csv",
            "Retain the Gate 3 start calendar; no onset inference",relation,status)
        for p,unit,src,why in (
            ("duration","period",PRIOR_RISK.relative_to(ROOT).as_posix()+" | "+AISIN+" | "+(TOYOTA if level=="moderate" else FORD),
             "Pre-existing days-to-week stress scale; external cases anchor magnitude only"),
            ("availability","fraction",PRIOR_RISK.relative_to(ROOT).as_posix(),"Pre-existing standardized stress loss converted to availability"),
            ("recovery","period","docs/v33_recovery_objective_spec.md | "+RENESAS,"Existing two-step curve; external case anchors gradual recovery only"),
        ):
            if not core:
                src="experiments/v321_gate3_direct_de/evidence/event_catalog.csv"
                why="Inherited mapping certification event"
            add(family,asset,level,p,r[p],unit,"SCENARIO",src,why,relation,status)
    for r in (x for x in events if x["level"]=="moderate"):
        for parameter in ("empirical_duration", "empirical_availability", "empirical_recovery", "frequency_and_dependence"):
            add(r["event_family"],r["asset"],"empirical",parameter,"","","MISSING",
                "docs/v3_phase32d2_multibom_uncertainty_calibration.md","No asset-level identification in case data",
                "Diagnostic response gives no empirical identification","UNRESOLVED")
    add("ALL","external automotive cases","context","duration_scale","days to approximately one week","qualitative","LITERATURE",
        AISIN+" | "+TOYOTA+" | "+FORD,"External plant shutdown and recommencement timelines","Design context only","CONTEXT_ONLY")
    add("ALL","external manufacturing case","context","recovery_shape","gradual","qualitative","DIRECT",RENESAS,
        "Observed recovery mechanism at an external asset","No fitting to this case","CONTEXT_ONLY")
    return rows


def audit():
    config=json.loads(CONFIG.read_bytes())
    assert config["certified_base"]==BASELINE
    gate36=json.loads((GATE36/"gate36_summary.json").read_bytes())
    assert gate36["V33_RECOVERY_OBJECTIVE_CERTIFIED"] and set(gate36["checks"].values())=={"PASS"}
    stage=(GATE36/"gate36_nonanticipativity_audit.csv")
    assert all(int(r["common_first_stage"])==config["common_first_stage_variables"]==4208 and
               int(r["common_opening_rows"])==config["candidate_states"]==91 for r in read_csv(stage))
    subprocess.run(["git","diff","--exit-code",BASELINE,"--","src/","artifacts/","audit/","experiments/v321_gate3_direct_de/",
                    "experiments/v321_gate35_risk_effectiveness/","experiments/v33_gate36_recovery_objective/",
                    "experiments/v32_gate2c_joint_preparedness/","experiments/v31_gate1_gate2b_certification/",
                    "docs/v33_recovery_objective_spec.md","docs/v33_gate36_certification.md"],cwd=ROOT,check=True,capture_output=True)
    assert config["recovery_horizon_inclusive"]==[75,97] and gate36["end"]==97 and gate36["tail_length"]==23
    assert config["demand_horizon_inclusive"]==[61,74]
    assert max(int(r["lead"]) for r in read_csv(GATE36/"gate36_clearance_paths.csv"))==config["longest_legal_lead_periods"]==23
    originals={r["event_id"]:r for r in read_csv(GATE3/"event_catalog.csv")}
    events=catalog(config,originals)
    core=[r for r in events if r["scope"]=="CORE"]
    assert len(core)==10 and {r["event_family"] for r in core}=={"BAT_PROD","BAT_OEM","SEAT_PROD","ENGINE_PROD","GEAR_OEM"}
    assert len({r["event_id"] for r in events})==12 and config["supplementary"]==["BAT_UP","SEAT_UP"]
    source={(r["origin"],r["destination"]):[int(r[f"t{t}"]) for t in range(61,75)] for r in read_csv(CAPACITY)}
    assert len(source)==11 and all(tuple(r["asset"].split("->")) in source for r in events)
    assert config["availability_field"]=="availability" and config["derived_loss"]=="1 - availability"
    assert all(0<=Fraction(r["availability"])<=1 and r["duration"]>0 and r["recovery"]>=0 and "severity" not in r for r in events)
    prior=read_csv(PRIOR_RISK)
    assert {Fraction(r["value"]) for r in prior if r["parameter"]=="severity"} >= {Fraction(1,4),Fraction(3,4)}
    assert {int(r["value"]) for r in prior if r["parameter"]=="duration"} >= {4,7}
    assert {k:(Fraction(r["availability"]),r["duration"],r["recovery"]) for k,r in config["levels"].items()}=={
        "moderate":(Fraction(3,4),4,2),"severe":(Fraction(1,4),7,2)}
    evidence=evidence_rows(events,read_csv(GATE35/"gate35_event_thresholds.csv"))
    assert all(r["evidence_class"] in CLASSES and r["source"] and r["rationale"] for r in evidence)
    for r in events:
        assert {e["parameter"] for e in evidence if (e["event_family"],e["level"])==(r["event_family"],r["level"])}=={
            "asset","start","duration","availability","recovery"}
    assert config["event_budget"]==[0,1,2]
    assert config["compatibility"]["deduplication"]=="EXACT_RATIONAL_EFFECTIVE_CAPACITY_ALL_ASSETS_AND_PERIODS_61_97"
    assert not config["compatibility"]["objective_based_filtering"] and not config["compatibility"]["supplementary_in_core"]
    pairs=[]
    for a,b in combinations_with_replacement(core,2):
        reason=compatible(a,b)
        assert reason==compatible(b,a)
        pairs.append(dict(first=a["event_id"],second=b["event_id"],legal=reason=="LEGAL",reason=reason))
    tail=config["tail"]
    conservative=Fraction(tail["conservative_fraction"])
    assert conservative==Fraction(3,4) and tail["mean_includes_zero"] and not tail["extend_source_specific_flow_caps"]
    plans=[tail["baseline"],*tail["sensitivities"]]
    assert plans==["CALENDAR_REPEAT","MEAN_EXTENSION","CONSERVATIVE_EXTENSION"]
    maps, counts=[],{}
    for plan in plans:
        nominal=nominal_capacities(source,plan,conservative)
        assert len(nominal)==11*37 and all(v==source[k[:2]][k[2]-61] for k,v in nominal.items() if k[2]<=74)
        previous=set()
        counts[plan]={}
        for gamma in config["event_budget"]:
            unique,mapping=subsets(core,gamma,nominal)
            assert previous < unique.keys()
            counts[plan][gamma]=dict(raw=len(mapping),legal=sum(m["compatibility"]=="LEGAL" for m in mapping),deduplicated=len(unique))
            assert tuple(counts[plan][gamma].values())==((1,1,1),(11,11,11),(56,51,51))[gamma]
            previous=set(unique)
            maps.extend(dict(tail_protocol=plan,**r) for r in mapping)
    expr=config["metrics"]
    assert expr["secondary"]=="cumulative backlog burden over the recovery horizon" and expr["backlog_sum_inclusive"]==["d_g",97]
    assert expr["segment_role"]=="product-segment disruption exposure" and expr["epsilon_service"]==expr["epsilon_backlog"]==0
    assert len(config["economics"]["missing_not_included"])==6 and config["economics"]["expansion"]=="DISABLED"
    assert config["economics"]["holding_rate"]["annual_fraction"]=="1/10"
    budget=config["budget"]
    gate35=json.loads((GATE35/"gate35_summary.json").read_bytes())
    assert budget["reference_kit_ceiling"]==gate35["battery_material_cut"]["prep_kit_bound"]==29
    assert budget["reference_anchor_cents"]==29*budget["kit_cost_cents"]==22931054
    assert budget["capital_ceiling_status"]=="NOT_COMPUTED_IN_PROTOCOL_FREEZE"
    assert config["selection"]["threshold_use"].startswith("context-only") and not config["selection"]["formal_optimization_results_used"]
    assert config["selection"]["authorized_operations"]=="STATIC_ONLY"
    tails=[dict(protocol_name=name,formula=form,evidence_class="SCENARIO",main_or_sensitivity=role,justification=why)
           for name,form,role,why in zip(plans,["C_source[a,61+((t-61) mod 14)]","sum(C_source[a,t=61..74])/14 (zeros included)",
                    "(3/4)*sum(C_source[a,t=61..74])/14 (zeros included)"],["MAIN","SENSITIVITY","SENSITIVITY"],
                    ["Retain certified operating calendar and zero slots","Remove calendar shape while preserving source mean",
                     "Pre-registered uniform 25% reduction from the mean sensitivity"])]
    budget_rows=[dict(rule=k,definition=v,evidence_class=cls,status=status) for k,v,cls,status in (
        ("joint_capital_ceiling",budget["ceiling"],"TRANSFORM",budget["capital_ceiling_status"]),
        ("normalised_grid",", ".join(budget["grid_fractions"])+" times joint ceiling", "SCENARIO","FROZEN_METHOD"),
        ("rounding",budget["rounding"],"TRANSFORM","FROZEN_METHOD"),
        ("reference_29_kit_anchor",f'{budget["reference_anchor_cents"]} cents. '+budget["reference_anchor_rule"],"TRANSFORM","FROZEN_METHOD"),
        ("service_response_breakpoint",budget["response_breakpoint_rule"],"SCENARIO","NOT_TESTED"),
    )]
    tables={"formal_event_catalog.csv":events,"formal_event_parameter_evidence.csv":evidence,"formal_event_compatibility.csv":pairs,
            "tail_capacity_protocol.csv":tails,"formal_budget_protocol.csv":budget_rows,"formal_scenario_dedup_map.csv":maps}
    report=dict(baseline=BASELINE,checks={f"P-{n:02}":"PASS" for n in range(1,13)},scenario_counts=counts,
                core_events=len(core),supplementary_events=len(events)-len(core),formal_optimization_calls=0,gate4_executed=False,
                FORMAL_RISK_PROTOCOL_FROZEN=True,READY_FOR_GATE4=True,
                unresolved=["asset_level_empirical_event_parameters", "risk_frequency_and_dependence", "observed_tail_capacities",
                            "missing_operating_costs", "empirical_residual_capacity", "joint_capital_ceiling_and_service_breakpoints"])
    return {**{name:csv_bytes(data) for name,data in tables.items()},
            "v33_formal_risk_static_audit.json":(json.dumps(report,indent=2)+"\n").encode()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true",help="Generate protocol tables and static verdict")
    args=parser.parse_args()
    for name,content in audit().items():
        file=HERE/name
        if args.write:
            file.write_bytes(content)
        else:
            assert content==file.read_bytes(),name
    print("P-01--P-12 PASS; STATIC_ONLY; formal optimization calls=0")


if __name__=="__main__":
    main()
