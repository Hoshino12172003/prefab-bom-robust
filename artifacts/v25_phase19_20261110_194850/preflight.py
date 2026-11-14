"""Phase 1.9 source-capacity gate and exact cyclic index checks. No solver entry point."""
import csv
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'src'))

from prefab_v25.data import CELL, COMPONENT_ARC, OEM, PACK, PROD, PRODUCTION_ARC, T1, TRANSPORT_ARC
from prefab_v25.source import HEADERS, SOURCE_NAME, compile_network, load_tables, verified_bytes

SOURCE = Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
PAPER = Path('external_inputs/Optimisation model for multi-item multi-echelon supply chain.pdf')
REQUEST = Path('private_inputs/attachment/已粘贴的文本.txt')
PHASE16 = ROOT/'artifacts/v25_phase16_20261110_160104'
PHASE17 = ROOT/'artifacts/v25_phase17_20261110_163116'
PHASE18 = ROOT/'artifacts/v25_phase18_20261110_181931'
FORMAL = ROOT/'artifacts/v25_formal_20261110'
STATUS = 'HOLD_SOURCE_NETWORK_LONG_RUN_CAPACITY_MISMATCH'
BASELINE = 'Source-Calibrated Periodic Nominal Baseline'
NOT_RUN = 'NOT_RUN_CAPACITY_GATE'
SHA = '02143f46cab6e6a173a0f495e21b20d21311096f'
DOI = '10.1016/j.ejor.2020.08.005'
H = 14
START = 61
ASSEMBLY = (OEM,'zp8')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def write_csv(name,rows,fields=None):
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def slot(absolute_period,h=H):
    cycle,index=divmod(absolute_period-1,h)
    return cycle,index+1


def cyclic_at(profile,absolute_period):
    return profile[slot(absolute_period,len(profile))[1]-1]


def initial_pipeline(profile,lead,boundary=0):
    return tuple(cyclic_at(profile,boundary+r-lead) for r in range(1,lead+1))


def step_pipeline(pipeline,departure):
    return (pipeline[0],(*pipeline[1:],departure)) if pipeline else (departure,())


def validate_cyclic_index(profile,lead,cycles):
    """Two implementations and a dated-event ledger on the same abstract token profile."""
    h=len(profile)
    start=initial_pipeline(profile,lead)
    pipeline=start
    # Include past departures whose delivery is after the opening boundary.
    event={d+lead:cyclic_at(profile,d) for d in range(1-lead,1)}
    for t in range(1,cycles*h+1):
        q=cyclic_at(profile,t)
        event[t+lead]=q
        arrived,pipeline=step_pipeline(pipeline,q)
        assert arrived==event.pop(t)==cyclic_at(profile,t-lead)
        assert pipeline==tuple(event.get(t+r,0) for r in range(1,lead+1))
        if t%h==0:
            assert pipeline==start


def capacity_certificate(network,tables):
    arcs={a.key:a for a in network.arcs}
    components=set(CELL)
    assert len(tables['nodes'])==12 and len(arcs)==11
    assert network.periods==tuple(range(START,START+H)) and all(tuple(a.capacity)==network.periods for a in arcs.values())
    assert network.demand_weight==28000
    assert {a.key for a in arcs.values() if set(a.recipes)&components}=={COMPONENT_ARC}
    assert {a.key for a in arcs.values() if PACK in a.recipes}=={PRODUCTION_ARC,TRANSPORT_ARC}
    assert {key for key in network.external if key[1] in (*CELL,PACK)}=={(COMPONENT_ARC[0],c) for c in CELL}
    assert set(arcs[COMPONENT_ARC].recipes)==components
    assert all(arcs[COMPONENT_ARC].recipes[c]==((c,1),) for c in CELL)
    recipe=arcs[PRODUCTION_ARC].recipes[PACK]
    assert recipe==tuple(zip(CELL,(10,6,4))) and arcs[TRANSPORT_ARC].recipes[PACK]==((PACK,1),)
    assert tuple(arcs[k].lead for k in (COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC))==(20,1,1)
    assert [r[3:5] for r in tables['operations'] if r[:3]==(PROD,'battery_componment','battery')]==[(20,1)]
    cars=arcs[ASSEMBLY]
    car_ids={g.id for g in network.groups}
    assert set(cars.recipes)==car_ids
    assert all(not (car_ids & a.recipes.keys()) for a in arcs.values() if a.key!=ASSEMBLY)
    assert all(item not in car_ids for _,item in network.external)
    bev=0
    for g in network.groups:
        coefficient=dict(cars.recipes[g.id]).get(PACK,0)
        assert coefficient==dict(g.representative.bom).get(PACK,0) and coefficient in (0,1)
        assert g.representative.weight==1
        bev+=coefficient*len(g.orders)
    assert bev==3003
    amount=sum(q for _,q in recipe)
    totals={k:sum(a.capacity.values()) for k,a in arcs.items()}
    cell=totals[COMPONENT_ARC]
    non_bev=network.demand_weight-bev
    bev_upper=min(bev,cell//amount,totals[PRODUCTION_ARC],totals[TRANSPORT_ARC])
    global_upper=min(totals[ASSEMBLY],non_bev+bev_upper)
    return dict(total_vin=network.demand_weight,bev_vin=bev,non_bev_vin=non_bev,units_per_pack=amount,
                upstream_cell_units=cell,pack_production_capacity=totals[PRODUCTION_ARC],
                pack_transport_capacity=totals[TRANSPORT_ARC],oem_assembly_capacity=totals[ASSEMBLY],
                cell_units_required=amount*bev,cell_units_gap=amount*bev-cell,
                fractional_pack_upper=str(Fraction(cell,amount)),bev_integer_upper=bev_upper,
                bev_minimum_unserved=bev-bev_upper,total_integer_upper=global_upper,
                bev_service_upper=float(Fraction(bev_upper,bev)),total_service_upper=float(Fraction(global_upper,network.demand_weight)),
                capacity_mismatch=bev_upper<bev or global_upper<network.demand_weight)


def provenance(tables,certificate):
    included=('nodes','arcs','products','nodes_inflow','capacity_at_arc','operations','BOM','demands',
              'max_flow_product_per_arc','max_flow_group_per_arc','initial_inventories','initial_flows')
    for sheet in included:
        for i,r in enumerate(tables[sheet],2):
            fields=dict(zip(HEADERS[sheet].split(),r))
            raw=json.dumps(fields,ensure_ascii=False,separators=(',',':'))
            value=raw
            role='source specification'
            transform='identity'
            if sheet=='initial_inventories':
                value=json.dumps({k:v for k,v in fields.items() if k not in ('initial_inventory_I_np0','period_t')},ensure_ascii=False)
                role='inventory bounds only; historical level excluded'
                transform='retain node/item stock bounds; do not fix opening level'
            elif sheet=='initial_flows':
                value='EXCLUDED'
                role='not a model input'
                transform='historical flow not admitted to periodic pipeline'
            elif sheet in ('capacity_at_arc','demands','max_flow_product_per_arc','max_flow_group_per_arc'):
                relative=int(fields['period_t'])-START+1
                value=json.dumps(dict(fields,period_t=relative),ensure_ascii=False,separators=(',',':'))
                transform='relative t = raw t − 60; quantities and joint calendar unchanged'
            yield dict(parameter_id=f'XLSB_{sheet}_{i}',parameter_name=sheet,value=value,unit='source column units',
                       source=SOURCE_NAME,location=f'{sheet}:{i}',raw_value=raw,transformation=transform,
                       evidence_class='DIRECT_DATA',role=role)
    extra=[('PAPER_CELL_490',490,'illustrative capacity units/period','§4.4, Table 7','DIRECT_PAPER','cross-check only'),
           ('PAPER_PROD_70',70,'illustrative packs/period','Table 7','DIRECT_PAPER','cross-check only'),
           ('PAPER_TRANS_70',70,'illustrative packs/period','Table 7','DIRECT_PAPER','cross-check only'),
           ('PAPER_ASSEMBLY_2000',2000,'vehicles/period','Table 7','DIRECT_PAPER','cross-check only'),
           ('PERIOD',H,'periods','demands and capacity_at_arc: 74−61+1','EXACT_DERIVED','fixed main period'),
           ('START',START,'source day index','source calendars, Phase 1.9 §1','EXPERIMENTAL_PROTOCOL','fixed main alignment'),
           ('REPLAY_COUNT',4,'cycles','Phase 1.9 §14','EXPERIMENTAL_PROTOCOL','replay after admissibility only'),
           ('KAPPA','5/21','dimensionless','70/294=490/2058','EXACT_DERIVED','cross-check only, raw capacities retained'),
           ('RISK_ARR',1,'multiplier','Phase 1.9 §5','EXPERIMENTAL_PROTOCOL','nominal policy'),
           ('RISK_PROD',1,'multiplier','Phase 1.9 §5','EXPERIMENTAL_PROTOCOL','nominal policy'),
           ('RISK_TRANS',1,'multiplier','Phase 1.9 §5','EXPERIMENTAL_PROTOCOL','nominal policy'),
           ('BUDGET',0,'USD','Phase 1.6 B0 / Phase 1.9','EXPERIMENTAL_PROTOCOL','no new purchased buffer'),
           ('ORDER_ID','(cycle,source VIN)','identifier','Phase 1.9 §3','EXPERIMENTAL_PROTOCOL','no identity reuse'),
           ('OBJECTIVES','max on-time, min stock, min total flow if needed','lexicographic priority','Phase 1.9 §§10–11','EXPERIMENTAL_PROTOCOL','proposed gated hierarchy, not solved'),
           ('OPTIMALITY_TOL',1e-9,'solver parameter','Phase 1.6 / Phase 1.9 §19','EXPERIMENTAL_PROTOCOL','required for admitted solve'),
           ('MIP_GAP',0,'relative gap','Phase 1.6 / Phase 1.9 §19','EXPERIMENTAL_PROTOCOL','required for admitted solve')]
    extra.extend((name,value,'count/cycle','XLSB calendars, demand, BOM and exact capacity certificate','EXACT_DERIVED','preflight only')
                 for name,value in certificate.items() if name in ('bev_vin','cell_units_required','upstream_cell_units','units_per_pack',
                                                                  'bev_integer_upper','total_integer_upper'))
    for key,value,unit,location,cls,role in extra:
        yield dict(parameter_id=key,parameter_name=key,value=value,unit=unit,
                   source=DOI if cls=='DIRECT_PAPER' else 'XLSB / Phase 1.9 specification',location=location,
                   raw_value=value,transformation='see source or formula in location',evidence_class=cls,role=role)


def capacity_rows(cert):
    rows=[]
    for name,unit,available,required,vehicle_upper,source in (
        ('shared upstream cell transport','cell components',cert['upstream_cell_units'],cert['cell_units_required'],
         cert['upstream_cell_units']//cert['units_per_pack'],'capacity_at_arc, BOM, operations'),
        ('pack production','packs',cert['pack_production_capacity'],cert['bev_vin'],cert['pack_production_capacity'],'capacity_at_arc'),
        ('T1 to OEM pack transport','packs',cert['pack_transport_capacity'],cert['bev_vin'],cert['pack_transport_capacity'],'capacity_at_arc'),
        ('OEM assembly','vehicles',cert['oem_assembly_capacity'],cert['total_vin'],cert['oem_assembly_capacity'],'capacity_at_arc'),
        ('combined BEV material upper','BEV VIN',cert['bev_integer_upper'],cert['bev_vin'],cert['bev_integer_upper'],'cyclic material conservation'),
        ('optimistic total on-time upper','all VIN',cert['total_integer_upper'],cert['total_vin'],cert['total_integer_upper'],'non-BEV demand + BEV upper, capped by assembly')):
        rows.append(dict(resource=name,unit=unit,available_or_upper_per_cycle=available,full_demand_requirement=required,
                         headroom=available-required,vehicle_upper=vehicle_upper,source=source,
                         full_demand_screen='FAIL' if available<required else 'AGGREGATE_SCREEN_ONLY'))
    return rows


def prior_evidence():
    audit_files=[d/'audit.json' for d in (PHASE16,PHASE17,PHASE18)]
    states=('PASS_ROOT_CAUSE_FIXED_AND_ALL_FORMAL_RUNS_RECERTIFIED','HOLD_SHORTAGE_UNIT_UNIDENTIFIED',
            'PASS_BASELINE_CERTIFIED_WITH_PHASE_SENSITIVITY')
    protected={}
    prior=[]
    for audit_file,expected in zip(audit_files,states):
        data=json.loads(audit_file.read_text(encoding='utf8'))
        assert data['status']==expected
        prior.append(data)
        protected[audit_file]=digest(audit_file)
        protected.update({audit_file.parent/n:h for n,h in data['output_sha256'].items()})
        protected.update({Path(n):h for n,h in data.get('documentation_sha256',{}).items()})
    protected.update({PHASE16/r['path']:r['sha256'] for r in prior[0]['model_files']})
    assert (PHASE18/'audit.sha256').read_text(encoding='ascii').split()[0]==protected[audit_files[2]]
    protected.update({p:digest(p) for p in FORMAL.iterdir() if p.is_file()})
    assert all(digest(p)==h for p,h in protected.items())
    return states,prior,protected


def main():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SHA
    states,prior,protected=prior_evidence()
    inputs={str(p):digest(p) for p in (SOURCE,PAPER,REQUEST,ROOT/'src/prefab_v25/data.py',ROOT/'src/prefab_v25/source.py',
                 ROOT/'src/prefab_v25/model.py',ROOT/'src/prefab_v25/formal.py',ROOT/'examples/run_v25_formal.py')}
    assert all(inputs[k]==h for k,h in prior[0]['input_sha256'].items() if k in inputs)
    pdf=subprocess.check_output(['pdftotext','-f','8','-l','10','-layout',str(PAPER),'-']).decode('utf8',errors='replace')
    assert all(x in pdf for x in ('490','always requires 20','2000'))
    workbook=verified_bytes(SOURCE)
    with ZipFile(SOURCE) as z:
        member,=[n for n in z.namelist() if n.rsplit('/',1)[-1]==SOURCE_NAME]
    inputs[f'{SOURCE}::{member}']=hashlib.sha256(workbook).hexdigest()
    tables=load_tables(SOURCE)
    network,_=compile_network(tables)
    certificate=capacity_certificate(network,tables)
    assert certificate['capacity_mismatch'], 'this audit is scoped to the documented capacity gate'
    arcs={a.key:a for a in network.arcs}
    assert Fraction(70,294)==Fraction(490,2058)==Fraction(5,21)
    write_csv('periodic_capacity_sufficiency.csv',capacity_rows(certificate))
    from itertools import chain
    iterator=provenance(tables,certificate)
    first=next(iterator)
    write_csv('periodic_network_parameter_provenance.csv',chain([first],iterator),list(first))

    for arc in arcs.values():
        validate_cyclic_index(tuple(arc.capacity.values()),arc.lead,4)
    upstream=arcs[COMPONENT_ARC]
    long_rows=[]
    for raw,q in upstream.capacity.items():
        d=raw-START+1
        arrival=d+upstream.lead
        c,t=slot(arrival)
        for b in range((d+H-1)//H*H,arrival,H):
            long_rows.append(dict(departure_cycle=0,departure_period=d,source_departure_period=raw,
                                  absolute_lead_time=upstream.lead,absolute_arrival=arrival,
                                  arrival_cycle=c,arrival_period=t,source_arrival_period=START+t-1,
                                  boundary_at=b,residual_lead_time=arrival-b,quantity=q,
                                  quantity_role='shared capacity token for index test; no shipment decision'))
    write_csv('long_lead_cyclic_pipeline_audit.csv',long_rows)

    demand_calendar={t:sum(len(g.orders) for g in network.groups if g.representative.due==t) for t in network.periods}
    rows=[]
    for s in range(H):
        order=[START+(t+s)%H for t in range(H)]
        assert sorted(order)==list(network.periods)
        assert sum(demand_calendar[t] for t in order)==certificate['total_vin']
        assert sum(upstream.capacity[t] for t in order)==certificate['upstream_cell_units']
        rows.append(dict(offset=s,first_source_period=order[0],source_order=' '.join(map(str,order)),
                         joint_demand_capacity_mapping='EXACT_INDEX_CHECK',bev_integer_upper=certificate['bev_integer_upper'],
                         total_integer_upper=certificate['total_integer_upper'],optimal_service='NA',status=NOT_RUN))
    write_csv('joint_phase_rotation_results.csv',rows)

    write_csv('periodic_baseline_state.csv',[],('node','item','period','quantity','source_var'))
    write_csv('periodic_pipeline_state.csv',[],('arc_origin','arc_destination','item','period','residual_lead_time','quantity','source_var'))
    write_csv('periodic_replay_results.csv',[dict(check='independent 14-day restart',periods=H,service='NA',state_closed='NA',status=NOT_RUN),
        *(dict(check=f'four-cycle replay, cycle {c}',periods=c*H,service='NA',state_closed='NA',status=NOT_RUN) for c in range(1,5))])
    nb00=prior[2]['cases'][0]
    assert nb00['offset']=='NB00'
    write_csv('phase18_vs_phase19_comparison.csv',[
        dict(case='Phase 1.8 NB00 finite warmup',on_time=nb00['formal']['on_time'],bev_on_time=nb00['formal']['bev'],
             rate=nb00['formal']['service_rate'],interpretation='certified finite-horizon outcome; not a periodic state',status=prior[2]['status']),
        dict(case='Phase 1.9 joint calendar, periodic',on_time='NA',bev_on_time='NA',rate='NA',
             interpretation=f'independent upper only: all VIN <= {certificate["total_integer_upper"]}; BEV <= {certificate["bev_integer_upper"]}',status=STATUS)])

    save(HERE/'baseline_manifest.json',dict(title=BASELINE,status=STATUS,git_sha=SHA,period=H,start_source_period=START,
        workbook_sha256=hashlib.sha256(workbook).hexdigest(),joint_calendar=True,risk_factors=dict(arrival=1,production=1,transport=1),
        opening_state='endogenous only if admitted',objective_order=['max on-time count','min total inventory','min total flow if needed'],
        admitted=False,optimizer_calls_allowed=0,prohibited_input_roles=['historical opening stocks','historical pipeline','Phase 1.8 terminal state'],
        required_if_admitted=dict(optimality_tol=1e-9,mip_gap=0,strict_budget=True,independent_upper=True)))
    assert all(digest(p)==h for p,h in protected.items())
    assert all(digest(p)==h for p,h in inputs.items() if '::' not in p)
    save(HERE/'audit.json',dict(status=STATUS,git_sha=SHA,baseline_constructed=False,capacity_certificate=certificate,
        formal_optimizer_calls=0,solver_logs=[],model_files=[],preflight_cross_cycle_index_check='PASS_TOKEN_LEDGER_ONLY',
        solver_dependent_outputs=dict(periodic_state=NOT_RUN,periodic_optimum=NOT_RUN,one_cycle_replay=NOT_RUN,
                                      four_cycle_replay=NOT_RUN,joint_rotation_optima=NOT_RUN),
        prior_statuses=dict(zip(('1.6','1.7','1.8'),states)),inputs_sha256=inputs,
        protected_archive_sha256={str(p):h for p,h in protected.items()}))
    print(STATUS,certificate,'protected files',len(protected),'formal optimizer calls 0')


if __name__=='__main__':
    main()
