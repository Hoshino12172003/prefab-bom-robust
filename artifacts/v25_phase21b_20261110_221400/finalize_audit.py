"""Validate the Phase 2.1B decision and seal the frozen evidence."""
import ast
import csv
import json
import platform
from pathlib import Path

from audit_mechanism import HERE, LABEL, PASS, ROOT, cert, export, physical_trace, policy

TESTS = (
    'tests/test_v25_phase20_prospective_spec.py',
    'tests/test_v25_phase21_calibration.py',
    'tests/test_v25_phase21a_joint_policy.py',
    'tests/test_v25_phase21b_mechanism.py',
)
DOC = ROOT/'docs/v25_phase21b_mechanism_nontriviality.md'


def nominal_single_position_timeline():
    rows = []
    controls = cert.records(cert.PRIOR/'single_buffer_capability.csv')
    for control in controls:
        if control['mode']=='all_open':
            continue
        previous_due = previous_q = 0
        for t,due,available,missed,_,_ in physical_trace('NOM',*policy(control)):
            cumulative = int(due-missed)
            rows.append(dict(label=LABEL,archived_run=control['run'],mode=control['mode'],K=control['k'],
                x_C=control['x_C'],x_T=control['x_T'],x_O=control['x_O'],relative_period=t,
                due_today=due-previous_due,cumulative_due=due,earliest_OEM_pack_availability=int(available),
                earliest_Q_t=cumulative-previous_q,earliest_Q_cumulative=cumulative))
            previous_due,previous_q = due,cumulative
        assert previous_q==int(control['z'])
    assert len(rows)==126
    export('time_value_nominal_single_position.csv',rows)
    return len(rows)


def main():
    path = HERE/'audit.json'
    audit = json.loads(path.read_text(encoding='utf-8'))
    assert audit['status']==PASS
    assert all(cert.digest(ROOT/name)==digest for name,digest in audit['frozen_input_manifest_sha256'].items())
    assert all(cert.verify_manifest(ROOT/name)>0 for name in audit['frozen_input_manifest_sha256'])
    assert all(cert.digest(Path(name))==digest for name,digest in audit['frozen_code_sha256'].items())
    assert cert.digest(cert.prior.SOURCE)==audit['source_zip_sha256']
    audit['scope_counts']['time_value_nominal_single_position'] = nominal_single_position_timeline()
    rows = {name:cert.records(HERE/f'{name}.csv') for name in (
        'buffer_delivery_efficiency_audit','risk_relaxation_audit','risk_policy_matching_effect',
        'buffer_form_ablation','optimal_set_cross_policy_overlap','zero_buffer_baseline','direct_solver_certificates')}
    for risk in ('L1','L2','L3'):
        match, = [r for r in rows['risk_policy_matching_effect'] if (r['days'],r['regime'],r['risk'])==('5','COST_PROBE',risk)]
        assert int(match['M_vehicles'])>0
        other = [r for r in rows['optimal_set_cross_policy_overlap'] if r['days']=='5'
                 and r['regime']=='COST_PROBE' and r['risk']==risk and r['policy_origin']!=risk]
        assert len(other)==3 and max(int(r['maximum_fixed_Q']) for r in other)<int(match['matched_Q'])
        assert any(int(r['delta_Q_relax'])>0 for r in rows['risk_relaxation_audit']
                   if r['policy_role']=='NR_MIN_COST_TRANSFER' and r['risk']==risk)
    assert {r['excluded_position'] for r in rows['buffer_form_ablation'] if int(r['service_loss'])>0}=={'x_C','x_T','x_O'}
    assert all(r['Q']=='0' for r in rows['zero_buffer_baseline'])
    assert (HERE/'pytest_exit_code.txt').read_text().strip()=='0'
    tests = (HERE/'pytest.txt').read_text(encoding='utf-8').splitlines()[-1].strip('= ')
    assert tests.startswith('30 passed')
    for f in (*HERE.glob('*.py'),ROOT/TESTS[-1]):
        ast.parse(f.read_text(encoding='utf-8'),filename=str(f))
    eff = rows['buffer_delivery_efficiency_audit']
    audit['all_efficiency_contexts'] = dict(count=len(eff),all_optima_equal=sum(r['all_optima_Q_equals_X']=='True' for r in eff),
        representative_equal=sum(r['Q_equals_X']=='True' for r in eff),
        eta_below_one_policy_count=sum(int(r['eta_below_one_policy_count']) for r in eff))
    audit['python_version'] = platform.python_version()
    audit['solver_logs'] = 'logs/'
    audit['academic_license_observed'] = True
    audit['main_thresholds_changed'] = False
    audit['final_risk_calibration_performed'] = False
    audit['tests'] = dict(command='python -m pytest -p no:cacheprovider -vv '+' '.join(TESTS),
                          exit_code=0,summary=tests,log='pytest.txt')
    audit['sha256_manifest'] = 'sha256_manifest.csv'
    path.write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    manifest = HERE/'sha256_manifest.csv'
    all_files = sorted([f for f in HERE.rglob('*') if f.is_file() and f!=manifest]+[DOC,ROOT/TESTS[-1]])
    with manifest.open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(('path','sha256'))
        writer.writerows((p.relative_to(ROOT).as_posix(),cert.digest(p)) for p in all_files)
    assert cert.verify_manifest(manifest)==len(all_files)
    print(json.dumps({'status':PASS,'tested':tests,'verified_hashes':len(all_files),'direct_logs':audit['direct_diagnostic_calls']}))


if __name__=='__main__':
    main()
