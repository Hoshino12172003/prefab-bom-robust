"""Independently replay the two horizons and certify the exported handoff."""
import math
import shutil
import statistics
from collections import Counter
from fractions import Fraction
from zipfile import ZIP_DEFLATED, ZipFile

from run_baseline import (
    HERE, SOURCE, FORMAL, P16, W, LENGTH, MAIN, SHA, BUFFER_NAMES, GRB, NOMINAL, gp,
    arrival_map, compile_network, configure, csv, csv_file, digest, exact_lp_upper,
    frozen_runs, gzip, horizon, initial_state, json, ledger, manifest_bytes, _block,
    load_tables, reachable_bev, save, seed_pipeline, seed_stock, subprocess,
    terminal_pipeline, warmup_material_upper,
)


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def arrays(path):
    with gzip.open(path,'rt',encoding='utf8') as f:
        data=json.load(f)
    assert set(data)=={'inventory','supply','dispatch','service'}
    return [{tuple(k):v for k,v in data[n]} for n in ('inventory','supply','dispatch','service')]


def record_main_dual(network,arrivals,count):
    out=HERE/MAIN
    run=frozen_runs(manifest_bytes(FORMAL/'manifest.json'))[0]
    with gp.Model('NB00_independent_dual_evidence') as model:
        configure(model,out/'independent_dual_preparation.log')
        buffers=[model.addVar(vtype=GRB.INTEGER,name=n) for n in BUFFER_NAMES]
        model.addConstr(gp.quicksum(c*v for c,v in zip(run.costs,buffers))<=0)
        block=_block(model,network,NOMINAL,initial_state(network,buffers),arrivals,'s0')
        model.setObjective(block[-1]/network.demand_weight,GRB.MAXIMIZE)
        model.update()
        proof=exact_lp_upper(model,network,block,arrivals,out/'independent_dual.log',out/'independent_dual.json')
    assert proof['integer_upper']==count


def main():
    manifest=json.loads((HERE/'baseline_manifest.json').read_text(encoding='utf8'))
    policy=json.loads((HERE/'stability_classification_policy.json').read_text(encoding='utf8'))
    assert (manifest['offsets'],manifest['main_baseline'])==(list(range(14)),MAIN)
    source,_=compile_network(load_tables(SOURCE))
    seed=seed_pipeline(source)
    p16=json.loads((P16/'audit.json').read_text(encoding='utf8'))
    stressed=next(r['exact_deliveries'] for r in p16['all_formal_recertification'] if r['run']=='nominal_B0')
    for row in p16['all_formal_recertification']:
        assert digest(P16/row['exact_certificate_file'])==row['exact_certificate_sha256']
    summaries, case_rows, reindex_rows=[],[],[]
    for offset in manifest['offsets']:
        label=f'NB{offset:02d}'
        out=HERE/label
        summary=json.loads((out/'summary.json').read_text(encoding='utf8'))
        warm_net=horizon(source,W,offset,'W'+label,seed_stock(source))
        warm_arrays=arrays(out/'warmup.json.gz')
        warm_arrivals=arrival_map(seed,W)
        stock,w_counts,w_orders=ledger(warm_net,warm_arrivals,warm_arrays)
        upper=warmup_material_upper(warm_net,warm_arrivals)
        assert w_counts['bev']+w_counts['non_bev']==summary['warmup']['on_time']==upper['integer_upper']
        assert 'BestObjStop' in (out/'warmup.log').read_text(encoding='utf8'), 'comparison requires the common warmup completion rule'
        assert summary['warmup']['status_name'] in ('USER_OBJ_LIMIT','OPTIMAL')
        summary['warmup']['independent_upper']=upper
        summary['warmup']['independent_exact_certificate']=True
        pipeline=terminal_pipeline(warm_net,warm_arrays[2],seed)
        saved_stock={(r['node'],r['item']):int(r['quantity']) for r in read_csv(out/'state.csv')}
        assert stock==saved_stock
        transit=read_csv(out/'in_transit.csv')
        assert [(r['origin'],r['destination'],r['item'],int(r['warmup_dispatch_t']),int(r['lead_time']),
                 int(r['remaining_lead']),int(r['quantity'])) for r in transit]==pipeline
        assert sum(r['undelivered'] for r in w_orders)==sum(int(r['undelivered']) for r in read_csv(out/'retired_orders.csv'))
        formal_net=horizon(source,LENGTH,0,'F'+label,{key:q for key,q in stock.items() if q})
        assert set(g.id for g in formal_net.groups).isdisjoint(g.id for g in warm_net.groups)
        arrival=arrival_map(pipeline,LENGTH)
        final,f_counts,_=ledger(formal_net,arrival,arrays(out/'formal.json.gz'))
        f=summary['formal']
        assert f_counts['bev']==f['bev'] and f_counts['non_bev']==f['non_bev']
        assert f['on_time']==f['bev']+f['non_bev']==f['feasible_witness']
        proof=f['independent_upper']
        if 'numerator' in proof:
            assert math.floor(Fraction(proof['numerator'],proof['denominator']))==proof['integer_upper']
        assert f['status_name']=='OPTIMAL' and f['mip_gap']==0 and f['exact_budget_residual_usd']==0
        assert abs(f['objective']-f['on_time']/28000)<=1e-9 and abs(f['bound']-f['objective'])<=1e-9
        assert summary['reachable_bev_supply']==reachable_bev(formal_net,arrival)
        assert f['independent_exact_certificate'] and proof['integer_upper']==f['on_time'], (label,proof,f['on_time'])
        if label==MAIN:
            record_main_dual(formal_net,arrival,f['on_time'])
        for r in transit:
            assert int(r['formal_arrival_t'])==int(r['warmup_dispatch_t'])+int(r['lead_time'])-W>0
            reindex_rows.append(dict(offset=label,kind='pipeline',origin=r['origin'],destination=r['destination'],
                item=r['item'],warmup_departure=r['warmup_dispatch_t'],warmup_arrival=r['warmup_arrival_t'],
                relative_arrival=r['formal_arrival_t'],quantity=r['quantity'],mapping='arrival minus 56',
                status='IN_WINDOW' if int(r['formal_arrival_t'])<=LENGTH else 'RETAINED_BEYOND_14'))
        reindex_rows.append(dict(offset=label,kind='stock',origin='',destination='',item='all node-item keys',
                warmup_departure='',warmup_arrival=W,relative_arrival=0,quantity=sum(stock.values()),
                mapping=f'{len(stock)} unchanged stock rows',status='EXACT'))
        case_rows.append(dict(offset=label,selected=label==MAIN,warmup_on_time=summary['warmup']['on_time'],
                              warmup_status=summary['warmup']['status_name'],warmup_seconds=summary['warmup']['runtime'],
                              warmup_exact_upper=upper['integer_upper'],**summary['terminal'],
                              reachable_bev_supply=summary['reachable_bev_supply'],
                              formal_on_time=f['on_time'],formal_bev=f['bev'],formal_non_bev=f['non_bev'],
                              nominal_service_rate=f['service_rate'],formal_seconds=f['runtime'],
                              formal_exact_upper=proof['integer_upper'],formal_mip_gap=f['mip_gap']))
        summaries.append(summary)
        print(label,'warmup',upper['integer_upper'],'formal',f['on_time'],flush=True)
    metrics=('total_inventory','battery_component_kit_equivalent','t1_pack','oem_pack','total_in_transit',
             'reachable_bev_supply','nominal_service_rate')
    stats=[]
    for key in metrics:
        values=[r[key] for r in case_rows]
        mean=statistics.mean(values)
        deviation=statistics.pstdev(values)
        stats.append(dict(metric=key,n=14,min=min(values),max=max(values),mean=mean,median=statistics.median(values),
                          standard_deviation=deviation,coefficient_of_variation=deviation/mean if mean else 'NA'))
    service=next(r for r in stats if r['metric']=='nominal_service_rate')
    sensitive=(service['max']-service['min'])*100>=policy['service_range_percentage_points'] or any(
        r['coefficient_of_variation']!='NA' and r['coefficient_of_variation']>=policy['battery_state_cv']
        for r in stats if r['metric'] in ('battery_component_kit_equivalent','t1_pack','oem_pack','reachable_bev_supply'))
    csv_file(HERE/'phase_offset_stability.csv',stats)
    csv_file(HERE/'phase_offset_baselines.csv',case_rows)
    csv_file(HERE/'time_reindex_audit.csv',reindex_rows)
    for original,final in (('state.csv','nominal_baseline_state.csv'),('in_transit.csv','nominal_baseline_in_transit.csv'),
                           ('formal_battery_trajectory.csv','nominal_baseline_battery_trajectory.csv')):
        shutil.copyfile(HERE/MAIN/original,HERE/final)
    save(HERE/'NB00_formal_B0.json',summaries[0]['formal'])
    inputs=json.loads((HERE/'input_hashes.json').read_text(encoding='utf8'))
    for path,h in inputs.items():
        if '::' not in path: assert digest(path)==h,path
    for name in ('run_baseline.py','prepare_evidence.py','finalize_baseline.py','baseline_manifest.json',
                 'stability_classification_policy.json','warmup_execution_protocol.json'):
        inputs[str(HERE/name)]=digest(HERE/name)
    solver_logs=sorted(HERE.rglob('*.log'))
    with ZipFile(HERE/'gurobi_logs.zip','w',compression=ZIP_DEFLATED) as z:
        for p in solver_logs:
            z.write(p,p.relative_to(HERE).as_posix())
    outputs={p.relative_to(HERE).as_posix():digest(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.name not in ('audit.json','audit.sha256')}
    status='PASS_BASELINE_CERTIFIED_WITH_PHASE_SENSITIVITY' if sensitive else 'PASS_SOURCE_CALIBRATED_NOMINAL_BASELINE_CERTIFIED'
    audit=dict(status=status,git_sha=SHA,manifest_sha256=digest(HERE/'baseline_manifest.json'),main_baseline=MAIN,
               verified_offsets=14,independently_verified_warmups=14,independently_verified_formal_solves=14,
               solver_logs=[n for n in outputs if n.endswith('.log')],solver_log_archive='gurobi_logs.zip',
               strict_budget=True,exact_balance_residual=0,
               stressed_B0=stressed,main_baseline_B0=summaries[0]['formal']['on_time'],
               main_minus_stressed=summaries[0]['formal']['on_time']-stressed,
               difference_is_not_historical_causal_estimate=True,phase_sensitivity_policy=policy,
               phase_offset_stability=stats,cases=summaries,source_and_input_sha256=inputs,output_sha256=outputs)
    save(HERE/'audit.json',audit)
    (HERE/'audit.sha256').write_text(digest(HERE/'audit.json')+'  audit.json\n',encoding='ascii')
    print(status,flush=True)


if __name__=='__main__':
    main()
