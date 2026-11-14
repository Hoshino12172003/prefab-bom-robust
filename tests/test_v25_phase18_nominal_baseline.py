import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'artifacts/v25_phase18_20261110_181931'
spec = importlib.util.spec_from_file_location('phase18_runner', OUT/'run_baseline.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
sys.path.insert(0, str(OUT))
from finalize_baseline import arrays, read_csv


@pytest.fixture(scope='module')
def source():
    tables = runner.load_tables(runner.SOURCE)
    network, _ = runner.compile_network(tables)
    return tables, network


@pytest.fixture(scope='module')
def manifest():
    return json.loads((OUT/'baseline_manifest.json').read_text(encoding='utf8'))


@pytest.fixture(scope='module')
def warm(source):
    net = source[1]
    return runner.horizon(net,56,0,'WNB00',runner.seed_stock(net))


def test_source_topology_is_preserved(source, warm):
    tables, original = source
    assert len(tables['nodes']) == 12
    assert len(warm.arcs) == len(original.arcs) == 11
    assert [a.key for a in warm.arcs] == [a.key for a in original.arcs]


def test_source_battery_bom_is_unchanged(source, warm):
    expected = tuple(zip(runner.CELL,(10,6,4)))
    assert sum(q for _,q in expected) == 20
    assert next(a for a in warm.arcs if a.key==runner.PRODUCTION_ARC).recipes[runner.PACK] == expected
    assert next(a for a in source[1].arcs if a.key==runner.PRODUCTION_ARC).recipes[runner.PACK] == expected


def test_raw_lead_times_are_unchanged(source, warm):
    assert [a.lead for a in warm.arcs] == [a.lead for a in source[1].arcs]
    lookup = {a.key:a.lead for a in warm.arcs}
    assert [lookup[k] for k in (runner.COMPONENT_ARC,runner.PRODUCTION_ARC,runner.TRANSPORT_ARC)] == [20,1,1]


def test_raw_capacities_cycled_without_scaling_stock_or_orders(source, warm):
    original=source[1]
    assert warm.initial == runner.seed_stock(original)
    assert sum(warm.initial.values()) == sum(original.initial.values())
    assert warm.demand_weight == 4*original.demand_weight
    for raw,new in zip(original.arcs,warm.arcs):
        assert all(new.capacity[t]==raw.capacity[runner.mapping(t,0)] for t in warm.periods)


def test_warmup_length_is_frozen(manifest, warm):
    assert manifest['warmup_periods'] == 56 == len(warm.periods)
    assert 42 <= manifest['settling_periods_paper'] == 55 < 56


def test_four_complete_original_demand_cycles_per_offset(source, manifest):
    original=source[1]
    daily=Counter()
    for group in original.groups:
        daily[group.representative.due]+=len(group.orders)
    rows=read_csv(OUT/'warmup_demand_mapping.csv')
    assert len(rows)==14*56
    for s in manifest['offsets']:
        case=[r for r in rows if r['offset']==f'NB{s:02d}']
        for cycle in range(4):
            block=case[14*cycle:14*(cycle+1)]
            assert {int(r['raw_due_t']) for r in block}==set(range(61,75))
            assert all(int(r['raw_due_t'])==runner.mapping(int(r['warmup_t']),s) and
                       int(r['vin_count'])==daily[int(r['raw_due_t'])] for r in block)
            assert sum(int(r['bev_count']) for r in block)==3003


def test_new_unique_vin_and_group_ids_preserve_orders(source, warm):
    original=source[1]
    formal=runner.horizon(original,14,0,'FNB00',{})
    ids={o.vin for g in warm.groups for o in g.orders}
    formal_ids={o.vin for g in formal.groups for o in g.orders}
    assert len(ids)==112000 and len(formal_ids)==28000 and ids.isdisjoint(formal_ids)
    assert len({g.id for g in warm.groups})==5144
    assert {g.id for g in warm.groups}.isdisjoint(g.id for g in formal.groups)
    raw={(o.vin,o.bom,o.due) for g in original.groups for o in g.orders}
    assert {(o.vin.split('_',2)[2],o.bom,o.due+60) for g in formal.groups for o in g.orders}==raw


def test_no_disruption_multipliers_all_one(manifest, warm):
    assert manifest['no_disruption_multipliers']==dict(arrival=1,production=1,transport=1)
    assert not runner.NOMINAL.arrival
    assert all(runner.NOMINAL.factor(a.key,t)==1 for a in warm.arcs for t in warm.periods)


def test_nb00_inventory_is_from_warmup_vector(source, warm):
    case=OUT/'NB00'
    seed=runner.seed_pipeline(source[1])
    stock,counts,_=runner.ledger(warm,runner.arrival_map(seed,56),arrays(case/'warmup.json.gz'))
    recorded={(r['node'],r['item']):int(r['quantity']) for r in read_csv(case/'state.csv')}
    assert recorded==stock
    assert runner.warmup_material_upper(warm,runner.arrival_map(seed,56))['integer_upper']==sum(counts[k] for k in ('bev','non_bev'))


def test_transit_reindex_handles_beyond_horizon_and_no_duplicates(source, warm):
    flow=arrays(OUT/'NB00/warmup.json.gz')[2]
    generated=runner.terminal_pipeline(warm,flow,runner.seed_pipeline(source[1]))
    assert len({row[:4] for row in generated})==len(generated)
    for i,j,item,t,lead,relative,q in generated:
        assert relative==t+lead-56>0 and q>0
    unit=('test','destination','SKU',56,20,20,1)
    assert runner.arrival_map([unit],14)=={}
    assert runner.arrival_map([unit],20)=={('destination','SKU',20):1}


def test_primary_selection_fixed_natural_order(manifest):
    assert runner.MAIN==manifest['main_baseline']=='NB00'
    assert runner.mapping(1,0)==61 and runner.mapping(14,0)==74


def test_all_fourteen_candidate_results_present_and_certified(manifest):
    assert manifest['offsets']==list(range(14))
    for s in manifest['offsets']:
        summary=json.loads((OUT/f'NB{s:02d}'/'summary.json').read_text(encoding='utf8'))
        assert summary['offset']==f'NB{s:02d}'
        assert summary['formal']['independent_exact_certificate']
        assert summary['formal']['on_time']==summary['formal']['independent_upper']['integer_upper']


def test_phase16_six_exact_certificate_bytes_unchanged():
    prior=json.loads((runner.P16/'audit.json').read_text(encoding='utf8'))
    assert len(prior['all_formal_recertification'])==6
    for item in prior['all_formal_recertification']:
        assert runner.digest(runner.P16/item['exact_certificate_file'])==item['exact_certificate_sha256']


def test_historical_shortage_number_cannot_enter_model(manifest):
    assert '860' not in json.dumps(manifest)
    code=(OUT/'run_baseline.py').read_text(encoding='utf8')
    assert '860' not in code and 'L1_CERT' not in code and 'L2_CERT' not in code and 'L3_CERT' not in code


def test_every_workbook_row_and_protocol_parameter_has_provenance(source):
    expected={f'XLSB_{sheet}_{i}' for sheet,rows in source[0].items() for i in range(2,2+len(rows))}
    seen=set()
    with (OUT/'network_parameter_provenance.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            assert r['parameter_id'] not in seen
            assert r['source_file'] and r['source_sheet_or_table'] and r['transformation_formula']
            assert r['evidence_class'] in ('DIRECT_PAPER','DIRECT_DATA','EXACT_DERIVED','EXPERIMENTAL_PROTOCOL')
            seen.add(r['parameter_id'])
    assert expected <= seen
    assert {'W_LENGTH','W_INIT','W_RISK_ARR','W_RISK_PROD','W_RISK_TRANS','W_CAP_CALENDAR',
            'W_STOP','F_MAIN','F_TRANSIT','F_B0','G_OPT_TOL','F_OBJECTIVE'} <= seen
