"""Materialize the pre-solve protocol and row-level source provenance."""
import re

from run_baseline import (
    HERE, ROOT, PAPER, SOURCE, REQUEST, FORMAL, P16, SHA, W, LENGTH, DATA, DOI,
    compile_network, load_tables, verified_bytes, mapping, csv_file, save, digest, hashlib,
    json, subprocess, protocol,
)
from prefab_v25.source import HEADERS


def table_provenance(tables, costs):
    sections = dict(nodes='§4.4/Fig.8',arcs='§4.4/Table 7',capacity_at_arc='§4.4/Table 7',
                    BOM='§4.3/Table 5; §4.4/Table 6',operations='§4.4/Table 6',
                    demands='§4.3/Table 4',products='§4.3',nodes_inflow='§3, §4.4',
                    initial_inventories='§4.6',initial_flows='§4.6',
                    max_flow_product_per_arc='§4.6',max_flow_group_per_arc='§4.6')
    units = dict(nodes='node ID',arcs='node IDs; days; product group',capacity_at_arc='physical units/period',
                 BOM='individual component units/output',operations='item units; operation flags',
                 demands='VIN units; day index',products='item ID; group; transport size',nodes_inflow='node; item eligibility',
                 initial_inventories='physical units; day index',initial_flows='physical units; departure day',
                 max_flow_product_per_arc='physical units/period',max_flow_group_per_arc='physical units/period')
    for sheet, rows in tables.items():
        seed=sheet.startswith('initial_')
        for i,row in enumerate(rows,2):
            value=json.dumps(dict(zip(HEADERS[sheet].split(),row)),ensure_ascii=False,separators=(',',':'))
            time_indexed=sheet in ('capacity_at_arc','max_flow_product_per_arc','max_flow_group_per_arc','demands')
            formula=('reindex time only; see mapping and manifest' if time_indexed else
                     'seed only; original quantity unchanged' if seed else 'identity')
            yield dict(parameter_id=f'XLSB_{sheet}_{i}',parameter_name=sheet,symbol=HEADERS[sheet],value=value,
                       unit=units[sheet],source_type='published workbook',source_file='2020_dataset_OfAutomotiveProductionNetwork.xlsb',
                       source_sheet_or_table=f'{sheet}:{i}',paper_section_or_table=sections[sheet],raw_value=value,
                       transformed_value=value,transformation_formula=formula,evidence_class='DIRECT_DATA',used_in_warmup=True,
                       used_in_formal_baseline=not seed,notes='source values unchanged; no historical claims')
    examples=[('P_SETTLE',55,'periods','§4.7 p.155','Reported settling time', 'DIRECT_PAPER'),
              ('P_CELL_CAP',490,'example capacity units/period','Table 7 and §4.4','Illustration only','DIRECT_PAPER'),
              ('P_PROD_CAP',70,'battery items/period','Table 7','Illustration only','DIRECT_PAPER'),
              ('P_TRANS_CAP',70,'battery items/period','Table 7','Illustration only','DIRECT_PAPER'),
              ('P_OEM_CAP',2000,'cars/period','Table 7','Illustration only','DIRECT_PAPER'),
              ('D_LENGTH',14,'periods','Table 3 and demands period_t','74−61+1','EXACT_DERIVED'),
              ('D_BOM_TOTAL',20,'cells/pack','BOM; Table 6','10+6+4','EXACT_DERIVED'),
              ('D_KAPPA','5/21','dimensionless','Table 7 and capacity_at_arc','70/294=490/2058; comparison only','EXACT_DERIVED'),
              ('D_VINS',28000,'VIN','demands','One unit per unique raw VIN','EXACT_DERIVED'),
              ('D_BEV',3003,'VIN','BOM + demands','Count VIN with BEV pack in BOM','EXACT_DERIVED'),
              ('D_GROUPS',1286,'groups','demands + BOM','Exact group by node, due, weight, BOM','EXACT_DERIVED'),
              ('W_LENGTH',56,'periods','§4.7 and demands','4×14 is the smallest complete multiple above 55','EXPERIMENTAL_PROTOCOL'),
              ('W_CYCLE',4,'repeats','Phase 1.8 F','Four full original patterns','EXPERIMENTAL_PROTOCOL'),
              ('W_OFFSET','0..13','periods','Phase 1.8 M','61+(t−1+s) mod 14','EXPERIMENTAL_PROTOCOL'),
              ('W_CAP_CALENDAR','unshifted; repeat 61..74','period indices','Phase 1.8 C/M','61+(t−1) mod 14, raw units','EXPERIMENTAL_PROTOCOL'),
              ('W_INIT','original t60 stocks and unexpired shipments','physical units','Phase 1.8 H','Opening seed; not final state','EXPERIMENTAL_PROTOCOL'),
              ('W_DUE','allow late inside 56; zero on-time credit','policy','Phase 1.6 _block / Phase 1.8 G','Total delivery ≤ size per unique order group','EXPERIMENTAL_PROTOCOL'),
              ('W_RISK_ARR',1,'multiplier','Phase 1.8 I','NOMINAL arrivals','EXPERIMENTAL_PROTOCOL'),
              ('W_RISK_PROD',1,'multiplier','Phase 1.8 I','NOMINAL production','EXPERIMENTAL_PROTOCOL'),
              ('W_RISK_TRANS',1,'multiplier','Phase 1.8 I','NOMINAL transport','EXPERIMENTAL_PROTOCOL'),
              ('F_B0',0,'USD','Phase 1.8 P and frozen manifest','Zero protective buffer spend','EXPERIMENTAL_PROTOCOL'),
              ('F_MAIN','NB00','offset ID','Phase 1.8 O','Natural order, no outcome-based selection','EXPERIMENTAL_PROTOCOL'),
              ('F_ORDERS','natural order; new unique identities','policy','Phase 1.8 F, G, Q','No retired warmup demand carries','EXPERIMENTAL_PROTOCOL'),
              ('F_INVENTORY','warmup end at t=56','physical units','Phase 1.8 K/L','Exact warmup I to formal t=0','EXPERIMENTAL_PROTOCOL'),
              ('F_TRANSIT','remaining = dispatch + lead − 56','days','Phase 1.8 K/L','Include each outstanding dispatch once','EXACT_DERIVED'),
              ('F_OBJECTIVE','maximum weighted on-time fraction','fraction','Phase 1.6 nominal','Same objective and unit weights','EXPERIMENTAL_PROTOCOL'),
              ('W_STOP','independent integer optimum, warmup only','on-time VIN','Phase 1.8 independent proof','Stop if exactly matching feasible witness is recovered; formal optimization unchanged','EXPERIMENTAL_PROTOCOL'),
              ('G_OPT_TOL','1e-9','solver tolerance','Phase 1.6 corrected run','Dual optimality tolerance','EXPERIMENTAL_PROTOCOL'),
              ('G_FEAS_TOL','1e-9','solver tolerance','Phase 1.6 corrected run','Primal tolerance plus exact ledger','EXPERIMENTAL_PROTOCOL'),
              ('G_INT_TOL','1e-9','solver tolerance','Phase 1.6 corrected run','Integrality tolerance plus exact ledger','EXPERIMENTAL_PROTOCOL'),
              ('G_MIP_GAP',0,'relative and absolute','Phase 1.6 corrected run','Gurobi gap for the 14-period solves','EXPERIMENTAL_PROTOCOL'),
              ('G_THREADS',4,'threads','Phase 1.6 corrected run','Frozen solver setting','EXPERIMENTAL_PROTOCOL'),
              ('G_SEED',20261110,'integer seed','Phase 1.6 corrected run','Frozen solver setting','EXPERIMENTAL_PROTOCOL')]
    for k,cost in zip(('cell_kit','t1_pack','oem_pack'),costs):
        examples.append((f'COST_{k}',cost,'USD/unit','Frozen manifest first_stage_buffers',
                         'Reused exactly; zero expenditure at B0','EXPERIMENTAL_PROTOCOL'))
    for row in examples:
        i,value,unit,source,formula,cls=row
        used=not i.startswith('P_') and i!='D_KAPPA'
        both=i in ('F_B0','F_OBJECTIVE')
        yield dict(parameter_id=i,parameter_name=i,symbol=i,value=value,unit=unit,
                   source_type='paper/mathematical derivation/protocol',source_file=DOI if cls=='DIRECT_PAPER' else 'XLSB and Phase 1.8',
                   source_sheet_or_table=source,paper_section_or_table=source,raw_value=value,transformed_value=value,
                   transformation_formula=formula,evidence_class=cls,used_in_warmup=(used and not i.startswith('F_')) or both or i=='P_SETTLE',
                   used_in_formal_baseline=used and not i.startswith('W_'),notes='Use within source scope or label as protocol')


def main():
    pdf=subprocess.check_output(['pdftotext','-layout',str(PAPER),'-']).decode('utf-8',errors='replace')
    assert re.search(r'settling time was set to 55',pdf) and 'Optimisation model' in pdf
    tables=load_tables(SOURCE)
    network,_=compile_network(tables)
    manifest=protocol(network,tables)
    natural={t:[g for g in network.groups if g.representative.due==t] for t in network.periods}
    rows=[]
    for offset in manifest['offsets']:
        for t in range(1,W+1):
            raw=mapping(t,offset)
            groups=natural[raw]
            rows.append(dict(offset=f'NB{offset:02d}',warmup_t=t,cycle=(t-1)//LENGTH+1,position=(t-1)%LENGTH+1,
                             raw_due_t=raw,raw_capacity_t=mapping(t,0),vin_count=sum(len(g.orders) for g in groups),
                             bev_count=sum(len(g.orders) for g in groups if ('BEV',1) in g.representative.bom),
                             identity_prefix=f'WNB{offset:02d}_{t:02d}'))
    csv_file(HERE/'warmup_demand_mapping.csv',rows)
    csv_file(HERE/'network_topology.csv',[dict(origin=i,destination=j,lead_days=int(lead),group=g,capacity_from=61,capacity_to=74)
                                        for i,j,lead,g in tables['arcs']])
    from prefab_v25.formal import frozen_runs, manifest_bytes
    costs=frozen_runs(manifest_bytes(FORMAL/'manifest.json'))[0].costs
    provenance=table_provenance(tables,costs)
    first=next(provenance)
    from itertools import chain
    csv_file(HERE/'network_parameter_provenance.csv',chain([first],provenance),list(first))
    # Descriptive thresholds frozen before inspecting any offset result.
    policy=dict(service_range_percentage_points=1, battery_state_cv=0.10,
                decision='flag if service range is at least 1 pp or nonzero-mean kit/T1/OEM/reachable CV is at least 0.10',
                standard_deviation='population across the complete set of offsets', zero_mean_cv='NA')
    if (HERE/'stability_classification_policy.json').exists():
        assert json.loads((HERE/'stability_classification_policy.json').read_text(encoding='utf8'))==policy
    else:
        save(HERE/'stability_classification_policy.json',policy)
    save(HERE/'warmup_execution_protocol.json',dict(
        scope='warmup only; formal B0 has no objective/time stop',
        initial='zero-gap Gurobi execution; preserve logs of superseded attempts',
        completion='BestObjStop at independent material integer upper; require exact replay equality',
        justification='several initial runs had incumbents equal to proven integer bound while branching continued',
        unchanged='same objective, data, constraints, variable domains and nominal model',
        primary_selection='NB00 remains the natural-order candidate'))
    p16=json.loads((P16/'audit.json').read_text(encoding='utf8'))
    assert p16['git_sha']==SHA
    exact={r['exact_certificate_file']:r['exact_certificate_sha256'] for r in p16['all_formal_recertification']}
    for name,h in exact.items(): assert digest(P16/name)==h
    inputs={str(p):digest(p) for p in (SOURCE,PAPER,REQUEST,FORMAL/'manifest.json',P16/'audit.json',
              P16/'run_audit.py',P16/'finalize_audit.py',ROOT/'examples/run_v25_formal.py',
              *(ROOT/f'src/prefab_v25/{f}.py' for f in ('source','model','data','formal')),*(P16/name for name in exact))}
    for name in ('run_audit.py','finalize_audit.py'):
        assert inputs[str(P16/name)]==p16['output_sha256'][name]
    for relative in ('src/prefab_v25/source.py','src/prefab_v25/model.py','src/prefab_v25/data.py',
                     'src/prefab_v25/formal.py','examples/run_v25_formal.py'):
        key=str(ROOT/relative)
        assert inputs[key]==p16['input_sha256'][key], key
    inputs[f'{SOURCE}::2020_dataset_OfAutomotiveProductionNetwork.xlsb']=hashlib.sha256(verified_bytes(SOURCE)).hexdigest()
    save(HERE/'input_hashes.json',inputs)
    print('source rows',sum(map(len,tables.values())),'demand map',len(rows),'frozen checks',len(exact))


if __name__=='__main__':
    main()
