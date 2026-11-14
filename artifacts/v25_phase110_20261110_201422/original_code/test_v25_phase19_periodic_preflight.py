import csv
import importlib.util
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'artifacts/v25_phase19_20261110_194850'
spec = importlib.util.spec_from_file_location('periodic_preflight', OUT/'preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def rows(name):
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope='module')
def source():
    tables=preflight.load_tables(preflight.SOURCE)
    network,_=preflight.compile_network(tables)
    return tables,network


def test_shared_raw_capacity_calendar_and_integer_deficit(source):
    tables,network=source
    arc=next(a for a in network.arcs if a.key==preflight.COMPONENT_ARC)
    raw={int(t):int(c) for i,j,t,c in tables['capacity_at_arc'] if (i,j)==arc.key}
    assert arc.capacity==raw
    assert {t:c for t,c in raw.items() if c}=={67:2058,74:2058}
    proof=preflight.capacity_certificate(network,tables)
    assert proof['upstream_cell_units']==4116
    assert proof['cell_units_required']==20*3003==60060
    assert proof['cell_units_gap']==55944
    assert proof['bev_integer_upper']==205 and proof['total_integer_upper']==25202
    assert Fraction(proof['fractional_pack_upper'])==Fraction(1029,5)


def test_stock_and_history_cannot_alter_cyclic_throughput_bound(source):
    tables,network=source
    unrelated_initial=replace(network,initial={(preflight.PROD,preflight.CELL[0]):10**6},historical=())
    assert preflight.capacity_certificate(network,tables)==preflight.capacity_certificate(unrelated_initial,tables)


def test_long_lead_has_two_distinct_cross_cycle_arrivals():
    assert preflight.slot(7+20)==(1,13)
    assert preflight.slot(14+20)==(2,6)
    results=rows('long_lead_cyclic_pipeline_audit.csv')
    positive=[r for r in results if int(r['quantity'])]
    assert [(int(r['departure_period']),int(r['boundary_at']),int(r['residual_lead_time'])) for r in positive]==[
        (7,14,13),(14,14,20),(14,28,6)]
    assert all('no shipment decision' in r['quantity_role'] for r in positive)


@pytest.mark.parametrize('lead',[0,1,14,20,23,28,42])
def test_modulo_and_residual_pipeline_match_four_unrolled_cycles(lead):
    tokens=tuple(1000+i for i in range(14))
    preflight.validate_cyclic_index(tokens,lead,4)
    current=preflight.initial_pipeline(tokens,lead)
    for t in range(1,57):
        arrived,current=preflight.step_pipeline(current,tokens[(t-1)%14])
        assert arrived==tokens[(t-lead-1)%14]
        if t%14==0:
            assert current==preflight.initial_pipeline(tokens,lead)


def test_joint_rotations_are_relabelings_with_same_capacity_bound(source):
    tables,network=source
    demands={t:tuple(sorted(p for _,p,_,due in tables['demands'] if due==t)) for t in network.periods}
    schedule={t:(demands[t],tuple(a.capacity[t] for a in network.arcs)) for t in network.periods}
    outputs=rows('joint_phase_rotation_results.csv')
    assert len(outputs)==14
    for offset,result in enumerate(outputs):
        ordered=[int(t) for t in result['source_order'].split()]
        assert ordered==list(network.periods[offset:]+network.periods[:offset])
        assert {schedule[t] for t in ordered}==set(schedule.values())
        assert int(result['bev_integer_upper'])==205 and result['optimal_service']=='NA'


def test_repeated_cycles_create_unique_order_identity(source):
    vins=[vin for _,vin,qty,_ in source[0]['demands'] if qty==1]
    assert len(set(vins))==28000
    assert len({(cycle,vin) for cycle in range(4) for vin in vins})==112000


def test_hold_disables_solver_replay_and_state_exports():
    manifest=json.loads((OUT/'baseline_manifest.json').read_text(encoding='utf8'))
    audit=json.loads((OUT/'audit.json').read_text(encoding='utf8'))
    assert manifest['status']==audit['status']==preflight.STATUS
    assert not manifest['admitted'] and not audit['baseline_constructed']
    assert manifest['optimizer_calls_allowed']==audit['formal_optimizer_calls']==0
    assert not audit['model_files'] and not audit['solver_logs']
    assert not rows('periodic_baseline_state.csv') and not rows('periodic_pipeline_state.csv')
    assert all(r['status']==preflight.NOT_RUN for r in rows('periodic_replay_results.csv'))


def test_frozen_phase16_phase17_phase18_archive_hashes():
    a=json.loads((OUT/'audit.json').read_text(encoding='utf8'))
    assert len(a['prior_statuses'])==3
    assert all(preflight.digest(p)==h for p,h in a['protected_archive_sha256'].items())
