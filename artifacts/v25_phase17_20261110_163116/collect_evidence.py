"""Read-only Phase 1.7 evidence collection. No solver entry point."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'src'))

from prefab_v25.data import CELL, COMPONENT_ARC, OEM, PACK, PROD, PRODUCTION_ARC, T1, TRANSPORT_ARC, receipts
from prefab_v25.formal import frozen_runs, manifest_bytes
from prefab_v25.source import HEADERS, compile_network, load_tables, verified_bytes

PAPER = Path('external_inputs/Optimisation model for multi-item multi-echelon supply chain.pdf')
SOURCE = Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
SPEC = Path('E:/浏览器文件/V2.5_Phase1_spec_bundle_v2_with_manifest.zip')
REQUEST = Path('private_inputs/attachment/已粘贴的文本.txt')
PHASE16 = ROOT/'artifacts/v25_phase16_20261110_160104'
FORMAL = ROOT/'artifacts/v25_formal_20261110'
GIT_SHA = '02143f46cab6e6a173a0f495e21b20d21311096f'
STATUS = 'HOLD_SHORTAGE_UNIT_UNIDENTIFIED'
DOI = '10.1016/j.ejor.2020.08.005'
DATA_DOI = '10.17632/pr3sdy5vp3.1'
PROVENANCE_FIELDS = ('parameter_id', 'symbol', 'value', 'unit', 'physical_meaning', 'evidence_class',
                     'primary_source', 'source_location', 'source_quote_or_field', 'derivation_formula',
                     'assumption_reason', 'uncertainty_or_limit', 'allowed_use', 'status')
CLASSES = {'DIRECT_PAPER', 'DIRECT_DATA', 'EXACT_DERIVED', 'SUPPORTED_INFERENCE', 'SCENARIO_ASSUMPTION'}
PATCH_FIELDS = ('candidate_id', 'batch_id', 'field', 'node', 'item', 'period', 'original_value', 'restored_value',
                'clean_value', 'unit', 'evidence_class', 'source', 'derivation', 'parameter_id')
PATTERN = re.compile(r'shortage|battery|initial[ _-]?inventor|initial[ _-]?flow|t\s*=\s*59|\b860\b|quality|scenario|data[ _-]?generation', re.I)


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def check_provenance(rows, required):
    ids = [r['parameter_id'] for r in rows]
    if len(ids) != len(set(ids)) or not set(required) <= set(ids):
        raise ValueError('duplicate or missing provenance')
    if any(set(row) != set(PROVENANCE_FIELDS) or any(v is None or not str(v).strip() for v in row.values())
           or row['evidence_class'] not in CLASSES for row in rows):
        raise ValueError('invalid provenance row')


def check_patch(rows, manifest, provenance):
    check_provenance(provenance, manifest['required_parameter_ids'])
    by_id = {r['parameter_id']: r for r in provenance}
    seen = set()
    seen_batch_items = set()
    for row in rows:
        key = tuple(row[k] for k in ('field', 'node', 'item', 'period'))
        if list(key) not in manifest['authorized_patch_keys'] or row['candidate_id'] not in manifest['authorized_candidates']:
            raise ValueError('patch is outside manifest authorization')
        source = by_id.get(row['parameter_id'])
        if source is None or source['status'] != 'PATCH_AUTHORIZED' or source['evidence_class'] != row['evidence_class']:
            raise ValueError('missing authorized patch provenance')
        if row['field'] == 'historical_initial_flow' and source['evidence_class'] not in ('DIRECT_DATA', 'DIRECT_PAPER'):
            raise ValueError('historical flow requires direct evidence')
        event = row['candidate_id'], key
        batch_item = row['candidate_id'], row['batch_id'], row['item']
        if event in seen or batch_item in seen_batch_items or row['batch_id'] not in manifest['authorized_batch_ids']:
            raise ValueError('duplicate restoration or unauthorized batch')
        seen.add(event)
        seen_batch_items.add(batch_item)
        if row['original_value']+row['restored_value'] != row['clean_value']:
            raise ValueError('patch does not balance')


def check_conversion(restored, remaining, r, recipe, packs_at_t1):
    if type(r) is not int or r < 0 or packs_at_t1 != r or len(restored) != len(recipe) or len(remaining) != len(recipe):
        raise ValueError('invalid counterfactual transfer')
    if any(y < 0 or y+q*r != x for x, y, q in zip(restored, remaining, recipe)):
        raise ValueError('BOM conservation violation')


def check_clean_b0(clean, stressed):
    if clean < stressed:
        raise ValueError('HOLD_CLEAN_BASELINE_MAPPING_ERROR')


def write_csv(name, rows, fields=None):
    if fields is None:
        fields = list(rows[0])
    with (HERE/name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def parameters():
    rows = []

    def row(id_, symbol, value, unit, meaning, cls, location, field, formula='N/A', reason='N/A',
            limit='Limited to the cited case/model context', use='Paper with source attribution', status='EVIDENCE_ONLY',
            source=None):
        source = source or (DOI if cls == 'DIRECT_PAPER' else DATA_DOI if cls == 'DIRECT_DATA' else f'{DOI}; {DATA_DOI}')
        rows.append(dict(zip(PROVENANCE_FIELDS, (id_, symbol, value, unit, meaning, cls, source, location, field,
                                                 formula, reason, limit, use, status))))

    row('SHORT_T', 't_short', 59, 'day index', 'Reported quality incident', 'DIRECT_PAPER', 'p.151 Table 3', 'Supply shortage period')
    row('SHORT_AMOUNT', 's', 860, 'UNSPECIFIED', 'Reported shortage magnitude', 'DIRECT_PAPER', 'p.151 Table 3', 'Supply shortage amount', limit='No physical unit or SKU vector printed')
    row('SHORT_CAUSE', 'cause', 'quality deficiencies', 'category', 'Weekly delivered battery-cell shipment unusable for production', 'DIRECT_PAPER', 'p.151 §4.2 and Table 3', 'Quality incident')
    row('SHORT_GROUP', 'g', 'battery_component', 'group label', 'Group affected by the incident', 'DIRECT_PAPER', 'p.151 Table 3', 'Supply shortage group')
    row('SHORT_NODE', 'n', PROD, 'node label', 'First affected node', 'DIRECT_PAPER', 'p.151 Table 3 and p.153 battery supply chain', 'Table prints battery-supplier_prodt; normalized to the network node')
    row('SHORT_UNIT', 'unit(s)', 'UNIDENTIFIED', 'physical unit', 'Mapping from 860 to physical stock', 'SUPPORTED_INFERENCE', 'Table 3; §3; §§4.6–4.7; XLSB schema', 'No unit binding in the published equation set or source workbook', limit='No SKU vector, paired shipment or generator mapping', use='Limitation only', status='BLOCKED')
    row('RECEIPT_STAGE', 'stage59', 'Delivered shipment unusable', 'stage', 'Likely receipt/quality-release loss at pack producer', 'SUPPORTED_INFERENCE', 'p.151 §4.2/Table 3; p.155 §4.9', 'Delivered cells and next new receipt at t66', limit='No lot ledger or exact write-off posting', use='Mechanism interpretation only')
    for i, q in enumerate((10, 6, 4)):
        row(f'BOM_{i+1}', f'a_{i+1}', q, f'{CELL[i]} units/pack', 'Individual BEV battery recipe', 'DIRECT_DATA', f'BOM row {87051+i}', 'individual_input_quantity_q_mc')
    row('BOM_TOTAL', 'sum(a)', 20, 'component units/pack', 'Total units in one complete recipe', 'EXACT_DERIVED', 'BOM rows 87051–87053; §4.4/Table 6', 'Three SKU quantities', '10+6+4')
    for id_, val, pos, meaning in (('LEAD_CELL',20,12,'Upstream cell transit'), ('LEAD_PROD',1,9,'Pack production to T1 inventory'), ('LEAD_OEM',1,7,'T1 to OEM transport')):
        row(id_, 'l_ij', val, 'days', meaning, 'DIRECT_DATA', f'arcs row {pos}; Table 7 corroborates', 'process_lead_time_l_ij')
    row('DAY', 'period length', 1, 'day/period', 'Case time unit', 'DIRECT_PAPER', 'p.152 §4.4', 'Length of one period')
    row('STOCK_T', 't0', 60, 'day index', 'Initial inventory cutoff', 'DIRECT_DATA', 'initial_inventories (all 82 rows); §4.6 corroborates', 'period_t')
    row('HORIZON', 'T', '61–74', 'day indices', 'Optimization window', 'DIRECT_DATA', 'demands; capacity_at_arc; Table 3 corroborates', 'period_t')
    for i, q in enumerate((930, 558, 372)):
        row(f'INIT_CELL_{i+1}', f'I_prod,{i+1},60', q, f'{CELL[i]} units', 'Post-incident source state at pack producer', 'DIRECT_DATA', f'initial_inventories row {77+i}', 'initial_inventory_I_np0')
    row('INIT_T1', 'I_T1,pack,60', 0, 'pack', 'Model baseline state at T1', 'EXACT_DERIVED', 'initial_inventories; source.compile_network', 'No explicit T1 BEV inventory row', 'zero fill of omitted state key', limit='Source omission interpreted by current model, no historical count measurement')
    row('INIT_OEM', 'I_OEM,pack,60', 52, 'packs', 'Observed case input at OEM cutoff', 'DIRECT_DATA', 'initial_inventories row 2', 'initial_inventory_I_np0')
    for start, quantities in ((46,(9470,5682,3788)),(53,(4220,2532,1688)),(60,(4240,2544,1696))):
        offset = (46,53,60).index(start)
        for i, q in enumerate(quantities):
            row(f'FLOW_CELL_{start}_{i+1}', f'f_cell,{i+1},{start}', q, f'{CELL[i]} units', 'Existing historical cell dispatch', 'DIRECT_DATA', f'initial_flows row {48+3*i+offset}', 'initial_flow', limit='Keep original dispatch and quantity')
        kits = min(q//a for q, a in zip(quantities,(10,6,4)))
        row(f'BATCH_{start}', f'kit_equivalent({start})', kits, 'BOM-compatible kit equivalents', 'Quantity in this observed batch', 'EXACT_DERIVED', 'initial_flows rows 48–56; BOM', 'Matched three SKU dispatch rows', 'min(q1//10,q2//6,q3//4)', limit='No mapping to 860')
        row(f'RECEIPT_{start}', 't_arr', start+20, 'day index', 'Cell receipt at pack producer', 'EXACT_DERIVED', 'initial_flows; arcs row 12', 'Dispatch period and lead', f'{start}+20')
    for id_, q, pos, meaning in (('FLOW_PACK_PROD',159,73,'t60 production dispatch arrives at T1 at t61'), ('FLOW_PACK_OEM',200,2,'t60 transport dispatch arrives at OEM at t61')):
        row(id_, 'f_pack,60', q, 'packs', meaning, 'DIRECT_DATA', f'initial_flows row {pos}', 'initial_flow')
    row('PACK_PROD_CAP', 'C_prod(t)', 294, 'packs/day', 'Raw pack arc capacity t61–74', 'DIRECT_DATA', 'capacity_at_arc rows 100–113', 'capacity_c_ijt', limit='No t59 row')
    row('PACK_OEM_CAP', 'C_trans(t)', 294, 'packs/day', 'Raw T1→OEM capacity t61–74', 'DIRECT_DATA', 'capacity_at_arc rows 30–43', 'capacity_c_ijt', limit='No t59 row')
    row('CELL_CAP', 'C_cell(t)', '2058 at 67 and 74, else 0', 'component-flow units/day', 'Raw upstream departure capacity t61–74', 'DIRECT_DATA', 'capacity_at_arc rows 128–141', 'capacity_c_ijt', limit='Not a historical batch size or receipt')
    row('PAPER_PROD_CAP', 'C_prod example', 70, 'battery items/period', 'Paper illustrative production arc capacity', 'DIRECT_PAPER', 'p.153 Table 7', 'capacity at edge', limit='Caption prints p=6; no t59 or invariant history')
    row('PAPER_OEM_CAP', 'C_trans example', 70, 'battery items/period', 'Paper illustrative transport arc capacity', 'DIRECT_PAPER', 'p.153 Table 7', 'capacity at edge', limit='No t59 value')
    row('PAPER_CELL_CAP', 'C_cell example', 490, 'battery_component arc capacity units', 'Paper example, §4.4 names t67', 'DIRECT_PAPER', 'pp.152–153 §4.4/Table 7', 'capacity at edge', limit='Not 860 conversion or lost shipment size')
    row('CAP_NORMALIZATION', 'kappa', '5/21', 'dimensionless', 'Both sides of frozen in-window capacity row rescaled', 'EXACT_DERIVED', 'Table 7; capacity_at_arc; frozen manifest/data.py', 'Representative capacity ratios', '70/294=490/2058; kappa*q<=kappa*C iff q<=C', limit='Model equivalence only; no historical quantity or 860 conversion', use='Paper as capacity-row convention')
    row('FIGURE_SCALE', 'figure factor', '1/50', 'plot multiplier', 'Battery-component inventory display in Fig.11(a)', 'DIRECT_PAPER', 'p.154 Fig.11(a) legend', 'Inventory plotting factor', limit='No scale for Table 3 and no pre-window observation')
    row('WEEKLY_BACKSTEP', 't_dep?', 39, 'day index', 'Possible departure corresponding to missed receipt', 'SUPPORTED_INFERENCE', '§4.2; initial_flows rows 48–56; arcs row 12', '7-day observed recurrence plus lead time', '46-7=39 and 39+20=59', limit='No battery row at t39; earlier arrival may simply be outside the in-transit snapshot', use='Hypothesis only')
    row('CBA_UNIT', 'unit_A(s)', 'total component units', 'conditional unit', 'Candidate A interpretation', 'SUPPORTED_INFERENCE', 'Table 3 and §3; XLSB item-indexed flows', 'Affected group; item units', limit='A group label does not bind the unit of s', use='Hypothesis only', status='BLOCKED')
    row('CBA_KIT_UPPER', 'K_A', 43, 'complete kits, upper bound', 'Conditional ceiling if A held', 'EXACT_DERIVED', 'Table 3; BOM; candidate A hypothesis', '860 total units under A', 'floor(860/(10+6+4))', limit='Equality needs 430/258/172; unknown actual composition', use='Conditional algebra only')
    row('CBB_UNIT', 'unit_B(s)', 'complete battery kits', 'conditional unit', 'Candidate B interpretation', 'SUPPORTED_INFERENCE', 'Table 3; XLSB observed batches', 'Observed batches are balanced', limit='No actual lot or scale bridge', use='Hypothesis only', status='BLOCKED')
    row('CBB_VECTOR', 'Delta_B', '8600/5160/3440', 'component units by SKU', 'Conditional physical quantities if B held', 'EXACT_DERIVED', 'Table 3; BOM; candidate B hypothesis', '860 complete kits under B', '860*(10,6,4)', limit='No identified lost batch', use='Conditional algebra only')
    row('CBC_UNIT', 'unit_C(s)', 'specific SKU or other shipment/accounting unit', 'conditional unit', 'Candidate C interpretation', 'SUPPORTED_INFERENCE', 'Table 3; §4.2; products', 'Affected group and shipment wording', limit='No SKU, container, lot or unit conversion field', use='Hypothesis only', status='BLOCKED')
    row('RESTORE', 'Delta', 'UNIDENTIFIED', 'component vector', 'No-incident component amount and location', 'SUPPORTED_INFERENCE', 'Table 3; §4.7; XLSB archive', 'No matched pre/post shipment', limit='Amount, allocation and t60 disposition missing', use='Limitation only', status='BLOCKED')
    row('R59', 'r', 'UNIDENTIFIED', 'packs', 'No-incident t59 additional pack production', 'SUPPORTED_INFERENCE', 'Table 7; capacity_at_arc; initial_flows', 'No t59 production capacity or fixed plan', limit='No numeric value or source-supported finite t59 interval', use='Limitation only', status='COUNTERFACTUAL_STATE_ASSUMPTION_REQUIRED')
    row('R70_HYPOTHESIS', 'r_bar?', 70, 'packs/day if assumed', 'Possible future sensitivity input', 'SCENARIO_ASSUMPTION', 'Table 7 exemplar', 'Capacity example', reason='Would extrapolate a model-window example', limit='Unapproved and unsupported for t59', use='Hypothesis only; no solve', status='NOT_ADOPTED')
    row('R_MAPPING', '(Delta-r*a,r)', 'Delta- (10,6,4)*r ; r', 'component units and packs', 'Conditional BOM and lead-time mapping to t60 producer/T1', 'EXACT_DERIVED', 'BOM; arcs; inventory equation (4)', 'Recipe and lag', 't59 prod reaches T1 at t60; t60 shipment would reach OEM t61', limit='Conditional on identified Delta, r, and no extra t60 dispatch; no inferred OEM stock', use='Symbolic rule only')
    row('DEMAND', 'D', '28000 total; 3003 BEV; 24997 other', 'VIN', 'Public case window demand', 'EXACT_DERIVED', 'demands; BOM; products', 'One order per VIN, count by battery requirement', '28000-3003=24997')
    row('CLEAN_B0', 'B', 0, 'USD', 'First clean verification budget if admitted', 'SCENARIO_ASSUMPTION', 'Phase 1.7 §J1; frozen manifest', 'B0 budget', reason='Isolate historical incident from new purchased buffers', limit='Solve gated by provenance', use='Design only', status='NOT_RUN')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloaded-xlsb', type=Path, required=True)
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(('git', *a), cwd=ROOT).decode('utf-8').strip()
    assert git('rev-parse', 'HEAD') == GIT_SHA
    prior = json.loads((PHASE16/'audit.json').read_text(encoding='utf-8'))
    assert prior['status'] == 'PASS_ROOT_CAUSE_FIXED_AND_ALL_FORMAL_RUNS_RECERTIFIED'
    protected = {PHASE16/'audit.json': digest(PHASE16/'audit.json'),
                 **{PHASE16/k:v for k,v in prior['output_sha256'].items()},
                 **{PHASE16/m['path']:m['sha256'] for m in prior['model_files']},
                 **{p:digest(p) for p in FORMAL.iterdir() if p.is_file()}}
    paths = [PAPER, SOURCE, SPEC, REQUEST, args.downloaded_xlsb, HERE/'mendeley_file_index.json',
             SOURCE.with_name('paper_scale_instance_v1.zip'), ROOT/'V2.1完整模型.zip']
    inputs = {str(p):digest(p) for p in paths}
    assert all(digest(p) == h for p,h in protected.items())
    payload = verified_bytes(SOURCE)
    index = json.loads((HERE/'mendeley_file_index.json').read_text(encoding='utf-8'))
    book_hash = hashlib.sha256(payload).hexdigest()
    assert len(index) == 1 and index[0]['content_details']['sha256_hash'] == book_hash
    assert inputs[str(args.downloaded_xlsb)] == book_hash
    tables = load_tables(SOURCE)
    network, _ = compile_network(tables)
    assert set(tables) == set(HEADERS)
    capacity_times = sorted({int(r[2]) for r in tables['capacity_at_arc']})
    assert capacity_times == list(range(61,75))
    assert {int(r[-1]) for r in tables['initial_inventories']} == {60}
    assert not any(860 in r for rows in tables.values() for r in rows)
    assert not any(r[:2] in (PRODUCTION_ARC,TRANSPORT_ARC) and r[-2] == 59 for r in tables['initial_flows'])
    assert not any(r[:2] in (COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC) for name in
                   ('max_flow_product_per_arc','max_flow_group_per_arc') for r in tables[name])
    battery = lambda r: any(isinstance(v,str) and (v == PACK or 'battery' in v) for v in r)
    history = [(i,r) for i,r in enumerate(tables['initial_flows'],2) if battery(r)]
    assert len(history) == 11
    source_rows = []
    for name in ('products','arcs','operations','BOM','capacity_at_arc','initial_inventories','initial_flows','nodes_inflow'):
        for n,r in enumerate(tables[name],2):
            if battery(r) and (name != 'BOM' or r[0] == PACK):
                source_rows.append(dict(sheet=name,row=n,values=json.dumps(r,ensure_ascii=False)))
    write_csv('raw_battery_evidence.csv',source_rows)
    with ZipFile(io.BytesIO(payload)) as z:
        workbook_members = z.namelist()
        metadata_parts = {n:hashlib.sha256(z.read(n)).hexdigest() for n in workbook_members if n.startswith('customXml/')}
        assert not any(re.search(rb'\b860\b|shortage', z.read(n), re.I) for n in metadata_parts)
        assert not any(re.search('vba|macro|externalLinks|queryTables|connections',n,re.I) for n in workbook_members)
    with ZipFile(SPEC) as z:
        spec_members = z.namelist()
        spec_notes = {n:hashlib.sha256(z.read(n)).hexdigest() for n in spec_members if n.startswith('paper_scale_v2/')}
    with ZipFile(SOURCE) as z:
        member, = [n for n in z.namelist() if n.endswith('.xlsb')]
    inputs[f'{SOURCE}::{member}'] = book_hash
    inputs[f'{SPEC}::paper_scale_v2/manifest.json'] = hashlib.sha256(manifest_bytes(SPEC)).hexdigest()

    scan = []
    found = git('ls-files','-co','--exclude-standard','-z').split('\0')
    for relative in sorted(set(found)):
        p = ROOT/relative
        if not p.is_file() or p.suffix not in ('.md','.py','.json','.csv','.txt','.toml','.yaml','.yml','.log') or HERE in p.parents:
            continue
        hits = PATTERN.findall(p.read_text(encoding='utf-8-sig',errors='replace'))
        if hits:
            scan.append(dict(path=relative, sha256=digest(p), matches=len(hits), examples=' | '.join(sorted(set(h.lower() for h in hits))[:12])))
    write_csv('repository_keyword_scan.csv',scan)
    sources = parameters()
    manifest = dict(phase='V2.5 Phase 1.7',status=STATUS,git_sha=GIT_SHA,
                    source_workbook_sha256=book_hash, source_archive=str(SOURCE),
                    authorized_patch_keys=[],authorized_batch_ids=[],authorized_candidates=[],
                    optimizer_calls_allowed=0,required_parameter_ids=[p['parameter_id'] for p in sources],
                    preserved_historical_flows=len(tables['initial_flows']),
                    rejected_calibration_target='1552', pending=['physical unit of s=860','SKU/lot and disposition','t59 production/capacity'],
                    future_verification=dict(scenario='NOM',budget=0,optimality_tol=1e-9,strict_budget=True,
                                             feasible_witness_floor=True,independent_upper_bound=True,exact_replay_if_needed=True))
    check_patch([],manifest,sources)
    write_json('clean_baseline_manifest.json',manifest)
    write_csv('parameter_provenance.csv',sources,PROVENANCE_FIELDS)
    write_csv('clean_baseline_patch.csv',[],PATCH_FIELDS)

    semantics = [
        dict(candidate='CB_A', interpretation='860 total component units', evidence_class='SUPPORTED_INFERENCE',
             basis='Paper §4.2/Table 3 group, §3 item-indexed flows, §4.4 uses physical item count',
             implication='0–43 complete kits from the vector alone; 43 requires exact 430/258/172 allocation',
             limitation='No lost SKU quantities. Observed raw weekly totals 8440–18940, no same-basis confirmation.',
             status='BLOCKED_NO_IDENTIFIED_ALLOCATION'),
        dict(candidate='CB_B', interpretation='860 complete battery kits', evidence_class='SUPPORTED_INFERENCE',
             basis='Observed intact weekly batches are balanced and yield 422, 424, 947 kits',
             implication='Conditional vector 8600/5160/3440, total 17200 units',
             limitation='Magnitude plausible only. No label, lost lot or generator bridge binds s to kits.',
             status='BLOCKED_NO_KIT_UNIT_EVIDENCE'),
        dict(candidate='CB_C', interpretation='860 units of one SKU, other shipment unit or group accounting unit', evidence_class='SUPPORTED_INFERENCE',
             basis='Table 3 reports a group; XLSB distinguishes three SKUs; shipment loss is described',
             implication='No unique SKU/quantity vector, no stand-alone complete kit if only one SKU',
             limitation='No SKU, shipment document, conversion field or accounting definition for s',
             status='BLOCKED_NO_SKU_OR_SHIPMENT_UNIT')]
    write_csv('shortage_semantics_audit.csv',semantics)
    write_csv('clean_baseline_candidates.csv',[dict(candidate_id=s['candidate'],status=s['status'],classification=s['evidence_class'],
                    usable_patch='NO', t60_mapping='UNIDENTIFIED', optimizer_status='NOT_RUN', detail=s['limitation']) for s in semantics])

    cert = next(r for r in prior['all_formal_recertification'] if r['run']=='nominal_B0')
    with gzip.open(PHASE16/cert['exact_certificate_file'],'rt',encoding='utf-8') as f:
        solution=json.load(f)
    get = lambda field,*key: solution.get(f's0_{field}['+','.join(map(str,key))+']',0)
    bev, other, late = 0, 0, 0
    for g in network.groups:
        car = g.representative
        ontime=sum(get('y',g.id,t) for t in network.periods if t<=car.due)
        if (PACK,1) in car.bom:
            bev += ontime
            late += sum(get('y',g.id,t) for t in network.periods if t>car.due)
        else:
            other += ontime
    assert (bev,other,late)==(1451,24997,0) and bev+other==cert['exact_deliveries']
    nominal, = frozen_runs(manifest_bytes(SPEC))[0].scenarios
    arrives = receipts(network,nominal)
    trajectory = []
    for t in network.periods:
        trajectory.append(dict(period=t, **{f'cell{i+1}_end':get('I',PROD,c,t) for i,c in enumerate(CELL)},
            T1_pack_end=get('I',T1,PACK,t), OEM_pack_end=get('I',OEM,PACK,t),
            pack_production_dispatch=get('q',*PRODUCTION_ARC,PACK,t), T1_OEM_dispatch=get('q',*TRANSPORT_ARC,PACK,t),
            T1_pack_receipt=arrives.get((T1,PACK,t),0)+get('q',*PRODUCTION_ARC,PACK,t-1),
            OEM_pack_receipt=arrives.get((OEM,PACK,t),0)+get('q',*TRANSPORT_ARC,PACK,t-1)))
    write_csv('stressed_B0_battery_trajectory.csv',trajectory)
    metrics = [('restored_battery_components',0,'component units'),
               ('pack_production',sum(r['pack_production_dispatch'] for r in trajectory),'packs'),
               ('T1_pack_availability',sum(r['T1_pack_receipt'] for r in trajectory),'packs received plus zero opening stock'),
               ('OEM_pack_arrival',sum(r['OEM_pack_receipt'] for r in trajectory),'packs received'),
               ('BEV_on_time',bev,'VIN'),('BEV_not_on_time',3003-bev,'VIN'),('BEV_delivered_late_in_window',late,'VIN'),
               ('nonBEV_on_time',other,'VIN'),('total_on_time',bev+other,'VIN'),('service_rate','26448/28000','fraction')]
    write_csv('clean_vs_stressed_decomposition.csv',[dict(metric=m,stressed_B0=v,clean_B0='NA',delta='NA',unit=u,
                        status='NOT_EVALUATED_NO_ADMITTED_CLEAN_BASELINE') for m,v,u in metrics])
    assert all(digest(p)==h for p,h in protected.items())
    assert all(digest(p)==inputs[str(p)] for p in paths)
    assert all(digest(ROOT/r['path'])==r['sha256'] for r in scan)
    assert git('rev-parse','HEAD')==GIT_SHA
    write_json('audit.json',dict(status=STATUS,git_sha=GIT_SHA,formal_optimizer_calls=0,admitted_candidates=[],
        clean_values_available=False,flow_changes=0,inventory_changes=0,patch_rows=0, provenance_rows=len(sources),
        document=dict(doi=DOI,sha256=inputs[str(PAPER)],inspected='Published PDF, pp. 144–158; §§3,4.2–4.9 and visual Table 7/Fig.11'),
        source=dict(doi=DATA_DOI,workbook_sha256=book_hash,download_verified=True,tables={s:len(r) for s,r in tables.items()},
                    workbook_members=workbook_members,custom_xml_sha256=metadata_parts,capacity_times=capacity_times,
                    historical_flow_period_counts=dict(Counter(int(r[-2]) for r in tables['initial_flows'])),
                    historical_battery_t39_rows=0,workbook_numeric_860_hits=0),
        source_spec_members=spec_members,source_spec_members_sha256=spec_notes, repository_scan_count=len(scan),
        historical_case_certificates={r['run']:r['exact_deliveries'] for r in prior['all_formal_recertification']},
        existing_stressed_B0=dict(total=bev+other,bev=bev,nonbev=other,late_bev=late,buffer=[0,0,0]),
        immutable_inputs_before_after_sha256={str(p):h for p,h in protected.items()}, input_sha256=inputs,
        output_sha256={p.name:digest(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='audit.json'}))
    print(STATUS,len(sources),'provenance rows',len(scan),'keyword files; formal optimizer calls=0')


if __name__ == '__main__':
    main()
