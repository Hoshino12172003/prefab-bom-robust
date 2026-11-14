"""Exact raw/effective RHS catalog for the frozen Phase 3.1 candidate."""
import csv
import json
import sys
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
from pathlib import Path
from time import perf_counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C = ROOT/"artifacts/v3_phase32c_20261112_093602"
H = ROOT/"artifacts/v3_phase31_20261111_193210"
sys.path[:0] = [str(C),str(H)]
import run_e4 as previous
import run_diagnostics as phase31
from audit_historical_reduction import nonbattery_certificate, service_bound
from prefab_v3.robust import RESOURCE_IDS
from structure import reach

FROZEN = previous.FROZEN
LABEL = "STRESS_TEST_ONLY"
ATTACHMENT = Path.home()/"private_inputs/attachment/已粘贴的文本.txt"
U = phase31.candidate()
ARC = (phase31.PRODUCTION_ARC, phase31.TRANSPORT_ARC)
POLICIES = {"P1":"BASE_B100","P2":"BASE_B150","P3":"R3_S75_D7_ABRUPT_B100","P4":"BASE_B200"}
FIRST_BATCH = 32


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(name, rows):
    rows = iter(rows)
    first = next(rows,None)
    if first is None:
        raise ValueError(f"No rows for {name}")
    with (HERE/name).open("w",encoding="utf-8-sig",newline="") as f:
        writer = csv.DictWriter(f,list(first))
        writer.writeheader()
        writer.writerow(first)
        writer.writerows(rows)


def dump(name, value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def compact(value):
    return json.dumps(value,separators=(",",":"),ensure_ascii=False)


def verify_frozen():
    evidence = previous.verify_frozen()
    manifest = C/"sha256_manifest.csv"
    rows = FROZEN.read(manifest)
    assert all(FROZEN.digest(ROOT/r["path"])==r["sha256"] for r in rows)
    evidence[C.name] = dict(entries=len(rows),manifest_sha256=FROZEN.digest(manifest))
    witness = ROOT/"artifacts/v25_phase20_20261110_203851/FULL28000_witness.json.gz"
    assert FROZEN.digest(witness)==read(H/"audit.json")["phase20_JIT_witness_sha256"]
    return evidence


def episode_json(e):
    return None if e is None else (e.start,e.duration,str(e.severity))


def episodes(item):
    return tuple(phase31.Episode(t,d,F(s)) if record else None
                 for record in item for t,d,s in [record or (0,0,"0")])


def policy_map():
    policies = {}
    for p,n in POLICIES.items():
        r = read(previous.P/"runs"/f"{n}.json")
        assert r["status"]=="EXACT_FINITE"
        if p=="P2":
            assert r["projections"]["T_min"]["value"]>0
        policies[p] = dict(policy=r["policy"],source=n)
    assert [p["policy"] for p in policies.values()]==[[915,0,0],[1338,24,0],[713,135,6],[1338,0,162]]
    return policies


def model_signature(base, opening):
    caps = {a.key:a.capacity for a in base.network.arcs}
    keys = tuple(("receipt",*k) for k in sorted(opening) if k[0]==phase31.PROD and k[1] in phase31.CELL)
    keys += tuple(("capacity",*a,t) for a in ARC for t in U.periods)
    nominal = tuple(F(opening[k[1:]]) if k[0]=="receipt" else F(caps[k[1:3]][k[3]]) for k in keys)
    return caps,keys,nominal


def regenerate():
    frozen = verify_frozen()
    t0 = perf_counter()
    FROZEN.init()
    base, opening = FROZEN.BASE,FROZEN.OPENING
    caps, keys, nominal = model_signature(base,opening)
    receipt_keys = [k for k in keys if k[0]=="receipt"]
    choices = {0:(None,)}
    dates = {0:frozenset()}
    for t,d in U.intervals():
        mask = ((1<<d)-1)<<(t-U.periods[0])
        choices[mask] = tuple(phase31.Episode(t,d,s) for s in U.severities)
        dates[mask] = frozenset(range(t,t+d))
    legal = tuple(U.feasible_masks())
    independent = {m for m in product(dates,repeat=3) if sum(len(dates[k]) for k in m)<=U.gamma and
                   not (dates[m[0]] & dates[m[1]] & dates[m[2]])}
    frozen_support_count = int(read(H/"audit.json")["candidate_size"]["z_patterns"])
    assert len(legal)==len(independent)==frozen_support_count and set(legal)==independent
    fragments = {}
    for options in choices.values():
        for e in options:
            f = dict(zip(U.periods,U.factors(e)))
            fragments[0,e] = tuple(F(int(opening[k[1:]]*f[k[-1]])) for k in receipt_keys)
            for i,a in enumerate(ARC,1):
                fragments[i,e] = tuple(caps[a][t]*f[t] for t in U.periods)
    grouped = {}
    def map_rows():
        index = 0
        for support in legal:
            for triplet in product(*(choices[m] for m in support)):
                signature = sum((fragments[i,e] for i,e in enumerate(triplet)),())
                if signature not in grouped:
                    grouped[signature] = [f"R{len(grouped)+1:05}",0,triplet]
                record = grouped[signature]
                record[1] += 1
                index += 1
                yield dict(label=LABEL,trajectory_id=index,rhs_class_id=record[0],
                           L1=compact(episode_json(triplet[0])),L2=compact(episode_json(triplet[1])),
                           L3=compact(episode_json(triplet[2])),exposure=sum(len(dates[m]) for m in support))
        assert index==287443
    write("trajectory_to_rhs_mapping.csv",map_rows())
    assert len(grouped)==38527 and sum(r[1] for r in grouped.values())==287443
    assert len({tuple(map(int,s)) for s in grouped})==38527
    key_reach = {k:reach(base,{k:0})["reachable_cohort_ids"].split("|") for k in keys}
    cohort = {g.id:g for g in base.network.groups}
    rows = []
    for sig,(id_,multiplicity,triplet) in grouped.items():
        arrivals, factors = U.attenuation(triplet,opening)
        actual = tuple(F(arrivals[k[1:]]) if k[0]=="receipt" else caps[k[1:3]][k[3]]*factors.get(k[1:],1) for k in keys)
        assert actual==sig
        changes = {k:v for k,v,old in zip(keys,sig,nominal) if v!=old}
        layers = {0 if k[0]=="receipt" else ARC.index(k[1:3])+1 for k in changes}
        direct = {g for k in changes for g in key_reach[k] if g}
        coactive = sum(len({0 if k[0]=="receipt" else ARC.index(k[1:3])+1 for k in changes if k[-1]==t})>1
                       for t in {k[-1] for k in changes})
        row = dict(label=LABEL,rhs_class_id=id_,canonical_signature=compact([str(v) for v in sig]),
            integral_effective_signature=compact([int(v) for v in sig]),multiplicity=multiplicity,
            representative_trajectory=compact([episode_json(e) for e in triplet]),
            disrupted_resources="|".join(RESOURCE_IDS[i] for i in sorted(layers)),
            disrupted_periods="|".join(map(str,sorted({k[-1] for k in changes}))),
            severity="|".join(str(e.severity) if e else "-" for e in triplet),
            duration="|".join(str(e.duration) if e else "-" for e in triplet),
            start="|".join(str(e.start) if e else "-" for e in triplet),
            recovery="ABRUPT",affected_model_parameters=compact([(k,str(v)) for k,v in changes.items()]),
            disrupted_BOM_branches=int(bool(layers)),disrupted_battery_layers=len(layers),
            reachable_VINs=sum(len(cohort[g].orders) for g in direct),
            affected_VIN_configurations=len({cohort[g].representative.bom for g in direct}),
            reachable_due_date_windows="|".join(map(str,sorted({cohort[g].representative.due for g in direct}))),
            max_structural_BOM_depth=max((2 if i==0 else 1 for i in layers),default=0),
            shared_capacity_changed_rows=sum(k[0]=="capacity" for k in changes),
            coactive_effective_layer_periods=coactive)
        rows.append(row)
    write("full_effective_rhs_catalog.csv",rows)
    runtime = perf_counter()-t0
    metadata = dict(label=LABEL,phase_inputs=frozen,raw_trajectories=287443,unique_raw_RHS=38527,
        unique_integer_effective_RHS=38527,checked_representative_profiles=len(rows),legal_supports=len(legal),
        schema=keys,nominal_signature=[str(v) for v in nominal],policies=policy_map(),
        stage_order="Safe upper bound, then canonical ID. First 32 unresolved in order per policy.",
        first_contiguous_batch=FIRST_BATCH,independent_reference="Frozen Phase 3.1 historical exact reduction",
        catalog_seconds=runtime,attachment_sha256=FROZEN.digest(ATTACHMENT),
        catalog_sha256=FROZEN.digest(HERE/"full_effective_rhs_catalog.csv"),
        mapping_sha256=FROZEN.digest(HERE/"trajectory_to_rhs_mapping.csv"))
    dump("catalog_metadata.json",metadata)
    print("Exact catalog",len(rows),sum(r[1] for r in grouped.values()),"seconds",round(runtime,2),flush=True)


if __name__=="__main__":
    regenerate()
