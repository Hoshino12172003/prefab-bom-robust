"""Seal the completed Phase 2.2 hold decision and its evidence."""
import ast
import csv
import json
import platform
from pathlib import Path

from design import DEMAND,HERE,PASS_HOLD,RATIOS,ROOT,SCALES,TOTAL,prior,read

TESTS=('tests/test_v25_phase20_prospective_spec.py','tests/test_v25_phase21_calibration.py',
       'tests/test_v25_phase21a_joint_policy.py','tests/test_v25_phase21b_mechanism.py',
       'tests/test_v25_phase22_design_and_reducibility.py')
DOC=ROOT/'docs/v25_phase22_formal_experiment_freeze.md'


def main():
    audit_path=HERE/'audit.json'
    a=json.loads(audit_path.read_text(encoding='utf-8'))
    assert a['status']==PASS_HOLD and a['algorithm_calls']==0
    for filename,identity in a['frozen_input_manifests'].items():
        assert prior.digest(ROOT/filename)==identity['sha256']
        assert prior.verify_manifest(ROOT/filename)==identity['entries']
    assert all(prior.digest(Path(p))==h for p,h in a['unchanged_code_sha256'].items())
    assert prior.digest(prior.prior.SOURCE)==a['source_zip_sha256']
    cases=read(HERE/'direct_de_scaling_benchmark.csv')
    assert len(cases)==6
    assert all(r['status']=='OPTIMAL' and int(r['objective'])==int(r['independent_exact_bound'])==float(r['objective_bound'])
               and float(r['gap'])==0 for r in cases)
    recourse=read(HERE/'recourse_necessity_audit.csv')
    assert len(recourse)==184 and all(r['exact_Q']==r['direct_Q'] for r in recourse)
    logs=sorted((HERE/'logs').glob('*.log'))
    assert len(logs)==54 and all(p.read_text(encoding='utf-8').count('Optimal solution found')==1 for p in logs)
    phase20=prior.prior.PHASE20
    ledger=read(phase20/'BEV3003_selected_parts_ledger.csv')
    upper={r['key']:int(r['value'].split('..')[1]) for r in read(phase20/'prospective_instance_parameter_provenance.csv')
           if r['parameter']=='end_period_stock_bounds'}
    oem_max={j:max(int(row['closing']) for row in ledger if row['item']==j) for j in ('D83','G1Z','Q2J','Q4H')}
    assert all(q+TOTAL<=upper.get(f'zp7/{j}',float('inf')) for j,q in oem_max.items())
    assert max(DEMAND)<=2000
    x_max=int(SCALES[5]*max(RATIOS))
    assert 10*x_max<99999
    a['analytical_proof_storage_checks']=dict(nonbattery_oem_closing_max=oem_max,
        additional_unconsumed_nonbattery_bound=TOTAL,source_daily_peak_due=max(DEMAND),
        source_oem_daily_assembly_capacity=2000,component_bound_max=10*x_max,source_stock_cap=99999)
    a['gurobi_version']='13.0.1'
    a['python_version']=platform.python_version()
    a['solver_logs']='logs/'
    a['direct_benchmark_summary']=dict(guarantee_status='OPTIMAL',max_solver_residual=max(float(r['max_solver_residual']) for r in cases),
        max_optimize_wall_s=max(float(r['optimize_wall_s']) for r in cases),
        peak_working_set_bytes=max(int(r['process_peak_working_set_bytes']) for r in cases),
        max_gap=max(float(r['gap']) for r in cases),scenarios_checked=[1,2],
        predeclared_solver_resource_limit_observed=False)
    assert (HERE/'pytest_exit_code.txt').read_text().strip()=='0'
    test_summary=(HERE/'pytest.txt').read_text(encoding='utf-8').splitlines()[-1].strip('= ')
    assert test_summary.startswith('35 passed')
    for path in [*HERE.glob('*.py'),ROOT/TESTS[-1]]:
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    a['tests']=dict(command='python -m pytest -p no:cacheprovider -vv '+' '.join(TESTS),
        exit_code=0,summary=test_summary,log='pytest.txt')
    a['sha256_manifest']='sha256_manifest.csv'
    audit_path.write_text(json.dumps(a,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    manifest=HERE/'sha256_manifest.csv'
    files=sorted([p for p in HERE.rglob('*') if p.is_file() and p!=manifest]+[DOC,ROOT/TESTS[-1]])
    with manifest.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(('path','sha256'))
        writer.writerows((p.relative_to(ROOT).as_posix(),prior.digest(p)) for p in files)
    assert prior.verify_manifest(manifest)==len(files)
    print(json.dumps(dict(status=PASS_HOLD,verified_sha256=len(files),tests=test_summary,direct_logs=len(logs))))


if __name__=='__main__':
    main()
