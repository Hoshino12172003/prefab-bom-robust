import csv
import json
from collections import defaultdict
from pathlib import Path

import pytest

from prefab_v25.data import CELL, COMPONENT_ARC, NOMINAL, PACK, PROD, PRODUCTION_ARC, T1, TRANSPORT_ARC, receipts
from prefab_v25.formal import frozen_runs, manifest_bytes
from prefab_v25.source import compile_network, load_tables


ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/v25_phase110_20261110_201422'
SOURCE=Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
FORMAL=ROOT/'artifacts/v25_formal_20261110/manifest.json'


@pytest.fixture(scope='module')
def source():
    tables=load_tables(SOURCE)
    return tables,compile_network(tables)[0]


def read_rows(name):
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def test_no_self_bom_row_can_generate_material_consumption(source):
    tables,network=source
    distinct=tuple(r for r in tables['BOM'] if r[0]!=r[1])
    assert len(tables['BOM'])-len(distinct)==49
    assert compile_network(dict(tables,BOM=distinct))[0]==network
    arcs={a.key:a for a in network.arcs}
    assert arcs[TRANSPORT_ARC].recipes[PACK]==((PACK,1),)
    assert arcs[PRODUCTION_ARC].recipes[PACK]==tuple(zip(CELL,(10,6,4)))


def test_beta_one_never_adds_generic_pack_input(source):
    tables,network=source
    altered=tuple((*r[:3],200,*r[4:]) if r[:3]==(PROD,'battery_componment','battery') else r for r in tables['operations'])
    recompiled=compile_network(dict(tables,operations=altered))[0]
    assert recompiled.arcs==network.arcs


def test_raw_dispatch_cap_and_planned_rows_have_separate_roles(source):
    tables,network=source
    arcs={a.key:a for a in network.arcs}
    for i,j,t,raw in tables['capacity_at_arc']:
        assert arcs[i,j].capacity[t]==raw
    assert set(arcs[COMPONENT_ARC].recipes)==set(CELL)
    assert arcs[COMPONENT_ARC].capacity[67]==arcs[COMPONENT_ARC].capacity[74]==2058
    assert len(network.product_caps)==365 and len(network.group_caps)==20
    key=('engine-supplier_prod','engine-supplier_inv','D60',65)
    assert network.product_caps[key]==22
    assert all(61<=k[-1]<=70 for k in (*network.product_caps,*network.group_caps))


def test_missing_opening_inventory_stays_explicitly_uncertified_zero(source):
    tables,network=source
    provided={row[:2] for row in tables['initial_inventories']}
    assert (T1,PACK) not in provided and network.initial[T1,PACK]==0
    assert (T1,PACK) not in network.inventory_bounds
    absent=set(network.initial)-provided
    assert len(absent)==1339 and all(network.initial[k]==0 for k in absent)
    row=next(r for r in read_rows('initial_state_semantics_audit.csv') if r['kind']=='inventory' and r['node']==T1 and r['item']==PACK)
    assert row['classification']=='MISSING_NOT_ZERO_CERTIFIED' and row['source_quantity']=='ABSENT'


def test_historical_receipt_dates_and_quality_do_not_change_dispatch(source):
    tables,network=source
    leads={a.key:a.lead for a in network.arcs}
    expected=defaultdict(int)
    for i,j,p,t,q in tables['initial_flows']:
        assert t<61
        day=t+leads[i,j]
        if day in network.periods:
            expected[j,p,day]+=q
    assert receipts(network,NOMINAL)==expected
    l1=frozen_runs(manifest_bytes(FORMAL))[-1].scenarios[1]
    impacted=receipts(network,l1)
    assert {k for k in expected if impacted[k]!=expected[k]}=={(PROD,c,66) for c in CELL}
    assert all(2*impacted[PROD,c,66]==expected[PROD,c,66] for c in CELL)
    assert network.historical==tables['initial_flows']


def test_semantics_required_fields_and_frozen_scope():
    with (OUT/'source_parameter_semantics.csv').open(encoding='utf-8-sig',newline='') as f:
        ids=set()
        for r in csv.DictReader(f):
            assert r['parameter_id'] not in ids
            ids.add(r['parameter_id'])
            assert all(r[k].strip() for k in ('unit_semantics','time_scope','mathematical_constraint'))
            assert r['extrapolated_beyond_source']=='NO'
    assert len(ids)>140000
    manifest=json.loads((OUT/'scope_manifest.json').read_text(encoding='utf8'))
    assert manifest['capacity']=='RAW_XLSB' and not manifest['baseline_construction_allowed']
    assert manifest['managerial_cost_gate']=='HOLD_FINAL_POSITION_COST_CALIBRATION'


def test_all_six_raw_matrix_certificates_preserve_strict_optimum():
    rows=read_rows('phase16_regression_after_semantic_cleanup.csv')
    assert [int(r['strict_witness_deliveries']) for r in rows]==[26448,26472,26508,26569,25974,26034]
    assert [int(r['raw_capacity_rows_changed']) for r in rows]==[42,42,42,42,168,168]
    assert all(r['passed']=='True' and r['other_model_differences']=='0' and r['exact_max_residual']=='0' for r in rows)
