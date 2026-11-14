"""Build the row-level source semantics register and focused audit views."""
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from itertools import chain
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))

from prefab_v25.data import BUFFER_EFFECTS, BUFFER_NAMES, CELL, COMPONENT_ARC, NOMINAL, PACK, PROD, PRODUCTION_ARC, T1, TRANSPORT_ARC, receipts
from prefab_v25.formal import frozen_runs, manifest_bytes
from prefab_v25.source import SOURCE_NAME, HEADERS, compile_network, load_tables

SOURCE=Path('external_inputs/Data for Optimisation model for multi-item multi-echelon supply chains with nested multi-level products.zip')
PAPER=Path('external_inputs/Optimisation model for multi-item multi-echelon supply chain.pdf')
FORMAL=ROOT/'artifacts/v25_formal_20261110'
SHA='02143f46cab6e6a173a0f495e21b20d21311096f'
DOI='10.1016/j.ejor.2020.08.005'
SCOPE='operational t=61..74 only'
ADAPT='MODEL_ADAPTATION'
FIELDS=('parameter_id','raw_field','raw_value','numerical_unit','unit_semantics','applies_to','item_or_group_scope',
        'node_or_arc_scope','time_scope','mathematical_constraint','coefficient_usage','source_file','source_sheet',
        'source_paper_location','evidence_class','transformed','transformation_formula','transformation_reason',
        'extrapolated_beyond_source','allowed_in_formal_model','notes')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def save(name,data):
    (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def write(name,rows,fields=None):
    with (HERE/name).open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def semantic(id_,field,value,unit,meaning,applies,item,node,time,constraint,use,sheet,
             *,paper='N/A',cls='DIRECT_DATA',formula='identity',reason='N/A',allowed='YES',notes='N/A',source=SOURCE_NAME):
    return dict(zip(FIELDS,(id_,field,value,unit,meaning,applies,item,node,time,constraint,use,source,sheet,paper,cls,
                            'NO' if formula=='identity' else 'YES',formula,reason,'NO',allowed,notes)))


def source_rows(tables, network, runs):
    emit=semantic
    for n,(item,group,size) in enumerate(tables['products'],2):
        yield emit(f'P{n}','group_g',group,'category','product to eligibility group','route/operation',item,'source network',SCOPE,
                   'arc recipe and dispatch domain','matching group',f'products:{n}',notes=f'transportation_size_s={size}; no source Eq.6 in V2.5')
    for n,(node,) in enumerate(tables['nodes'],2):
        yield emit(f'N{n}','node_n',node,'identifier','source node index','inventory and arcs','source-compatible items',node,SCOPE,
                   'node-item balance domain','index only',f'nodes:{n}')
    for n,(node,item) in enumerate(tables['nodes_inflow'],2):
        yield emit(f'E{n}','node_n,product_p',f'{node},{item}','eligibility','allowed external inflow only','supply variables',item,node,SCOPE,
                   'inventory balance','+external supply at eligible key',f'nodes_inflow:{n}',cls=ADAPT,
                   notes='no independent external quantity cap; downstream arc/stock constraints still apply')
    for n,(i,j,l,g) in enumerate(tables['arcs'],2):
        yield emit(f'L{n}','process_lead_time_l_ij',int(l),'periods','elapsed from launch to arrival','dispatch and receipt',g,f'{i}->{j}',
                   f'{SCOPE}; historical receipt timestamp t_dep+L','inventory balance','q(t) arrives t+L; L=0 same period',f'arcs:{n}',paper='§3, §4.4')
    arc_group={(i,j):g for i,j,_,g in tables['arcs']}
    for n,(i,j,t,c) in enumerate(tables['capacity_at_arc'],2):
        yield emit(f'C{n}','capacity_c_ijt',int(c),'model flow-capacity units/period','shared sum of eligible item dispatch units',
                   'arc dispatch',arc_group[i,j],f'{i}->{j}',f't={int(t)} within 61..74','sum eligible q <= c*factor',
                   'LHS coefficient 1 per eligible item; original RHS before risk',f'capacity_at_arc:{n}',paper='Eq. (2), Table 7 (example only)',
                   notes='engineering packaging scale is not established by the XLSB field')
    for name,expr in (('max_flow_product_per_arc','q[item] <= planned_flow'),('max_flow_group_per_arc','sum eligible q <= planned_flow')):
        for n,(i,j,p,t,q) in enumerate(tables[name],2):
            yield emit(f'{name}:{n}','planned_flow',int(q),'model item units/period','row-specific production-plan ceiling in V2.5',
                       'planned-flow layer',p,f'{i}->{j}',f't={int(t)} within 61..70',expr,'RHS only on source-listed key',f'{name}:{n}',
                       paper='§4.6 Eq. (17) is an equality example, not a verified XLSB mapping',cls=ADAPT,
                       notes='absence means no extra planned-flow row; exact source enforcement is unverified')
    for n,(parent,child,q) in enumerate(tables['BOM'],2):
        use=parent!=child
        yield emit(f'B{n}','individual_input_quantity_q_mc',int(q),'item units/operation output batch',
                   'distinct child requirement' if use else 'identity encoding, excluded from transformation BOM',
                   'material recipe',f'{parent}/{child}','eligible transformation node',SCOPE,
                   'inventory balance' if use else 'N/A: excluded',
                   'child withdrawal q_mc/out when beta=1' if use else 'none; identity transfer comes from operations',f'BOM:{n}',
                   paper='§3 Eq. (4), §4.3',allowed='YES' if use else 'NO',
                   formula='q_mc/out' if use else 'excluded',reason='individual BOM override' if use else 'm=c is not a child requirement')
    for n,(node,ig,og,inc,out,alpha,beta) in enumerate(tables['operations'],2):
        identity=ig==og and beta==1
        yield emit(f'O{n}','in_nxy,out_nxy,alpha_nxy,beta_nxy',f'{inc},{out},{alpha},{beta}','units/operation; flags',
                   'same-item 1:1 movement' if identity else 'variant selector and output factor',
                   'operation',f'{ig}->{og}',node,SCOPE,'inventory balance and eligible recipes' if beta==1 else 'N/A: no compiled dispatch',
                   'withdraw one at departure, add one at arrival' if identity else 'for beta=1 use q_mc/out; generic input not additive',
                   f'operations:{n}',paper='§3 Eq. (4), §4.3, Table 6',allowed='YES' if beta==1 else 'NO',
                   notes='alpha has no simultaneous-output role in these compiled source rows')
    for n,(node,vin,qty,t) in enumerate(tables['demands'],2):
        yield emit(f'D{n}','demand_d_npt,period_t',f'{int(qty)}@{int(t)}','VIN, period','single order with promised due period',
                   'on-time service',vin,node,f'due t={int(t)}; delivery decision 61..74','group total y <= group count; objective t<=due',
                   'unit demand and due selector',f'demands:{n}',paper='§4.3 Table 4; objective is V2.5 adaptation',
                   formula='exact aggregation by node/BOM/due/weight',reason='same effective coefficients')
    for n,(node,item,q,lb,ub,t) in enumerate(tables['initial_inventories'],2):
        yield emit(f'I{n}','initial_inventory_I_np0',int(q),'item units','provided opening inventory','opening state',item,node,
                   f't={int(t)} only','opening stock in first balance','one-time constant',f'initial_inventories:{n}',paper='§4.6')
        yield emit(f'IB{n}','safety_stock,max_inventory',f'{int(lb)},{int(ub)}','item units','end-period stock bounds by node and item',
                   'inventory',item,node,SCOPE,'lower <= I_t <= upper','variable bounds',f'initial_inventories:{n}',cls=ADAPT,
                   notes='V2.5 applies the two fields as operational bounds on the frozen horizon')
    present={r[:2] for r in tables['initial_inventories']}
    for n,(node,item) in enumerate(k for k in network.initial if k not in present):
        yield emit(f'IZ{n}','missing initial_inventory row',0,'item units','loader default, source zero not verified','opening state',item,node,
                   't=60 only','opening stock in first balance','zero-fill missing index','initial_inventories: absent key',cls=ADAPT,
                   formula='dict.get(key,0)',reason='preserve certified loader policy',allowed='CERTIFICATION_ONLY',notes='MISSING_NOT_ZERO_CERTIFIED')
    leads={a.key:a.lead for a in network.arcs}
    for n,(i,j,item,t,q) in enumerate(tables['initial_flows'],2):
        arrival=int(t)+leads[i,j]
        yield emit(f'H{n}','initial_flow',int(q),'item units','fixed pre-window dispatch, not a future capacity','historical receipt',item,f'{i}->{j}',
                   f'departure t={int(t)}; arrival t={arrival}','inventory balance if arrival in 61..74','+quantity at arrival; L1 may reduce usable receipt',
                   f'initial_flows:{n}',paper='§4.6',formula='arrival=departure+lead',reason='historical pipeline',
                   allowed='YES' if arrival in network.periods else 'NO',notes='no retroactive capacity checks or dispatch changes')
    manifest='artifacts/v25_formal_20261110/manifest.json'
    for j,(name,effects,cost) in enumerate(zip(BUFFER_NAMES,BUFFER_EFFECTS,runs[0].costs)):
        for (node,item),coefficient in effects:
            yield emit(f'BUF{j}_{item}','buffer opening effect',coefficient,'item units/buffer','one balanced kit or one pack at specified location',
                       'first-stage inventory',item,node,'decision before t=61','opening balance','coefficient of '+name,manifest,cls=ADAPT,
                       allowed='CERTIFICATION_ONLY',source=manifest)
        yield emit(f'BC{j}','costs_usd',cost,'USD/buffer','certification-only cost coefficient','first-stage budget',name,'buffer node',
                   'before t=61; six frozen runs','sum c*x <= budget','positive coefficient',manifest,cls=ADAPT,
                   allowed='CERTIFICATION_ONLY',source=manifest,notes='T1/OEM equal cost and OEM premium zero are not managerial assumptions')
    for run in runs:
        yield emit(f'BUDGET_{run.id}','budget_usd',run.budget,'USD','frozen experiment budget','first-stage budget',run.id,'all buffers',
                   'before t=61; frozen case only','sum c*x <= budget','RHS',manifest,cls='EXPERIMENTAL_PROTOCOL',allowed='CERTIFICATION_ONLY',source=manifest)
    for s in runs[-1].scenarios:
        for layer,profile,constraint,scope in (('arrival',s.arrival,'fixed usable receipt into stock balance','battery component arrivals'),
            ('production',s.production,'raw production-arc capacity RHS',str(PRODUCTION_ARC)),('transport',s.transport,'raw transport-arc capacity RHS',str(TRANSPORT_ARC))):
            for t,v in profile.items():
                yield emit(f'{s.name}_{layer}_{t}',layer,v,'fraction','frozen scenario multiplier','scenario recourse',layer,scope,
                           f't={t} only; default 1 otherwise',constraint,'multiply RHS or usable receipt',manifest,
                           cls='EXPERIMENTAL_PROTOCOL',allowed='CERTIFICATION_ONLY',source=manifest)
    for id_,field,value,meaning,constraint in (('SERVICE_WEIGHT','weight',1,'uniform on-time vehicle count','maximize sum w*y/D'),
        ('SERVICE_DENOM','demand weight',network.demand_weight,'total VIN weight','nominal service ratio and rho constraints'),
        ('DEFAULT_RISK','unlisted factor',1,'no perturbation on unlisted period','capacity RHS or usable receipt'),
        ('OEM_PREMIUM','oem_positioning_premium_usd',0,'placeholder for certification only','buffer budget cost already frozen')):
        yield emit(id_,field,value,'model weight, factor or USD',meaning,'frozen V2.5','applicable variables','source network',SCOPE,
                   constraint,'as specified in V2.5',manifest,cls=ADAPT,allowed='CERTIFICATION_ONLY',source=manifest)


def main():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SHA
    pdf=subprocess.check_output(['pdftotext','-layout',str(PAPER),'-']).decode('utf8',errors='replace')
    assert all(s in pdf for s in ('scheduled production','duction of period t =65','amount of 40','settling time was set to 55'))
    tables=load_tables(SOURCE)
    network,audit=compile_network(tables)
    runs=frozen_runs(manifest_bytes(FORMAL/'manifest.json'))
    arcs={a.key:a for a in network.arcs}
    group_by_arc={(i,j):g for i,j,_,g in tables['arcs']}
    records=source_rows(tables,network,runs)
    write('source_parameter_semantics.csv',records,FIELDS)
    write('capacity_semantics_audit.csv',[dict(origin=i,destination=j,period=int(t),raw_capacity=int(q),group=group_by_arc[i,j],
            eligible_items=len(arcs[i,j].recipes),lead=int(arcs[i,j].lead),lhs='sum eligible SKU dispatch with coefficient 1',
            rhs='raw c times scenario factor',physical_unit='model flow-capacity units/period',scope='original indexed date only',
            capacity_basis='RAW_XLSB',normalization='DEPRECATED_ALGEBRAIC_NORMALIZATION' if (i,j) in (COMPONENT_ARC,PRODUCTION_ARC,TRANSPORT_ARC) else 'N/A')
            for i,j,t,q in tables['capacity_at_arc']])
    self_rows=[(n,r) for n,r in enumerate(tables['BOM'],2) if r[0]==r[1]]
    assert len(self_rows)==49 and all(r[2]==1 for _,r in self_rows)
    write('bom_semantics_audit.csv',[dict(sheet='BOM',row=n,mother=m,child=c,quantity=q,classification='IDENTITY_ROW_EXCLUDED',
            historical_route_uses=' | '.join(f'{a.origin}->{a.destination}' for a in network.arcs if a.recipes.get(m)==((m,1),)),
            enters_bom_explosion=False,enters_transform_consumption=False,detail='same-item stock transfer sourced from 1:1 operations')
            for n,(m,c,q) in self_rows]+[dict(sheet='BOM/operations',row='87051–87053 / 14',mother=PACK,child='10/6/4 by SKU',quantity=20,
                classification='INDIVIDUAL_BOM_OVERRIDE',historical_route_uses='pack production',enters_bom_explosion=True,
                enters_transform_consumption=True,detail='beta=1; generic input 20 is not added')])
    planned=[]
    for name in ('max_flow_product_per_arc','max_flow_group_per_arc'):
        for n,(i,j,item,t,q) in enumerate(tables[name],2):
            planned.append(dict(sheet=name,row=n,origin=i,destination=j,item_or_group=item,period=int(t),value=int(q),
                source_semantics='max_* table label and planned_flow field; original executable interpretation unverified',
                implemented='q <= value' if name.startswith('max_flow_product') else 'sum q <= value',classification=ADAPT))
    planned.append(dict(sheet='paper',row='Eq. (17)',origin='engine-supplier_prod',destination='engine-supplier_inv',item_or_group='D60',period=65,value=40,
                        source_semantics='explicit equality in the paper example',implemented='not imported; XLSB row 163 is 22',classification='SOURCE_PAPER_CROSSCHECK'))
    write('planned_flow_semantics_audit.csv',planned)

    direct={row[:2]:row for row in tables['initial_inventories']}
    initial=[]
    for (node,item),q in network.initial.items():
        initial.append(dict(kind='inventory',node=node,origin='',destination='',item=item,t=60,arrival='',source_quantity=q if (node,item) in direct else 'ABSENT',
                            modeled_quantity=q,L1_usable='',classification='DIRECT_DATA' if (node,item) in direct else 'MISSING_NOT_ZERO_CERTIFIED',
                            allowed_use='frozen short-window certification'))
    l1=runs[-1].scenarios[1]
    for i,j,p,t,q in network.historical:
        day=t+arcs[i,j].lead
        use=q*l1.arrival.get(day,1) if j==PROD and p in CELL else q
        initial.append(dict(kind='historical_dispatch',node='',origin=i,destination=j,item=p,t=t,arrival=day,source_quantity=q,
                            modeled_quantity=q,L1_usable=use if day in network.periods else 'OUTSIDE_WINDOW',classification='DIRECT_DATA',
                            allowed_use='fixed arrival calculation; no historical capacity backcast'))
    write('initial_state_semantics_audit.csv',initial)
    times=[('capacity_at_arc','t=61..74 indexed rows','no cyclic or long-run extrapolation'),
           ('demands','due t=61..74','one 14-period order window'),('max_flow_product_per_arc','t=61..70 listed keys','no extra rows when absent'),
           ('max_flow_group_per_arc','t=61..70 listed keys','no extra rows when absent'),('initial_inventories','opening t=60','initial quantities fixed only at opening'),
           ('safety_stock/max_inventory','V2.5 end stock bounds t=61..74','loader policy limited to certification'),
           ('initial_flows','departures t=39,46,53,59,60; arrivals derived by arc','do not extend 61–74 dispatch capacities backwards'),
           ('lead times','record-specific constant used for this case','arrival departure+lead; in-window balance'),
           ('historical L1','arrival t=66 only','usable quantity, not a dispatch-capacity shock'),
           ('55 periods','source data-generation settling time','no optimization convergence or steady-state claim')]
    write('time_scope_audit.csv',[dict(parameter=p,time_scope=t,restriction=r,extrapolated_beyond_source=False) for p,t,r in times])

    groups=[]
    vin_set={o.vin for g in network.groups for o in g.orders}
    source_constraints=(*tables['max_flow_product_per_arc'],*tables['initial_flows'])
    assert not any(r[2] in vin_set for r in source_constraints)
    assert not any(r[1] in vin_set for r in (*tables['initial_inventories'],*tables['nodes_inflow']))
    assert not any(child in vin_set for _,child,_ in tables['BOM'])
    assert all(size==0 for item,_,size in tables['products'] if item in vin_set)
    for g in network.groups:
        rep=g.representative
        assert all((o.node,o.due,o.bom,o.weight)==(rep.node,rep.due,rep.bom,rep.weight) for o in g.orders)
        groups.append(dict(group=g.id,VINs=len(g.orders),node=rep.node,due=rep.due,weight=rep.weight,bom=json.dumps(rep.bom),
            eligibility='single OEM assembly and delivery node; identical per VIN',risk='same recipe and same scenario-dependent upstream resources',
            planned_flow='no VIN-specific row; same upstream SKU/group constraints',cost_priority='no VIN-specific term',
            member_sha256=hashlib.sha256('\n'.join(o.vin for o in g.orders).encode()).hexdigest(),passed=True))
    write('aggregation_semantics_audit.csv',groups)
    due=Counter(); bev_due=Counter()
    for g in network.groups:
        due[g.representative.due]+=len(g.orders)
        if (PACK,1) in g.representative.bom:
            bev_due[g.representative.due]+=len(g.orders)
    write('demand_calendar.csv',[dict(period=t,vin=due[t],bev=bev_due[t],non_bev=due[t]-bev_due[t]) for t in network.periods])
    write('lead_time_audit.csv',[dict(origin=a.origin,destination=a.destination,lead=a.lead,group=group_by_arc[a.key],
            arrival_rule='departure + lead',same_period_arrival=a.lead==0,stock_convention='period-end after all dated receipts and uses') for a in network.arcs])

    save('phase19_disposition.json',dict(current_status='HOLD_LONG_RUN_EXTRAPOLATION_UNSUPPORTED',
        original_artifact_status_preserved='HOLD_SOURCE_NETWORK_LONG_RUN_CAPACITY_MISMATCH',
        scope='conditional proof only under indefinitely repeated joint 14-period source calendar',source_long_run_capacity_inference=False))
    save('scope_manifest.json',dict(git_base=SHA,capacity='RAW_XLSB',time_scope=SCOPE,
        normalization='DEPRECATED_ALGEBRAIC_NORMALIZATION',table7='SOURCE_PAPER_CROSSCHECK',
        scheduled_flow=ADAPT,sparse_zero='MISSING_NOT_ZERO_CERTIFIED',cost='CERTIFICATION_ONLY',
        managerial_cost_gate='HOLD_FINAL_POSITION_COST_CALIBRATION',clean='SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED',
        permitted_optimization='six frozen Phase 1.6 regression cases only',baseline_construction_allowed=False))
    hist_in=[q for i,j,p,t,q in network.historical if t+arcs[i,j].lead in network.periods]
    l1_arr=receipts(network,l1)
    nom_arr=receipts(network,NOMINAL)
    assert [(k,nom_arr[k],l1_arr[k]) for k in nom_arr if nom_arr[k]!=l1_arr[k]]==[
        ((PROD,CELL[0],66),9470,4735),((PROD,CELL[1],66),5682,2841),((PROD,CELL[2],66),3788,1894)]
    save('source_checks.json',dict(source_sha256=network.source_sha256,source_zip_sha256=digest(SOURCE),paper_sha256=digest(PAPER),
        capacity_rows=len(tables['capacity_at_arc']),bom_identity_rows=len(self_rows),
        identity_movements=sum(recipe==((item,1),) for a in network.arcs for item,recipe in a.recipes.items()),
        planned_flow_product_rows=len(tables['max_flow_product_per_arc']),planned_flow_group_rows=len(tables['max_flow_group_per_arc']),
        explicit_opening_rows=len(direct),sparse_default_rows=len(network.initial)-len(direct),historical_rows=len(network.historical),
        historical_arrivals_in_horizon_rows=len(hist_in),historical_arrivals_in_horizon_qty=sum(hist_in),
        historical_arrival_last=max(t+arcs[i,j].lead for i,j,_,t,_ in network.historical),
        demand_groups=len(groups),demand_vins=len(vin_set),bev=sum(bev_due.values()),formal_scope=SCOPE))
    print('semantics complete',len(groups),'groups',len(self_rows),'identity rows')


if __name__=='__main__':
    main()
