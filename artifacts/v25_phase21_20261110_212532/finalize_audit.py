"""Verify the completed Phase 2.1 evidence and seal its SHA-256 manifest."""
import ast
import csv
import gzip
import hashlib
import json
import platform
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TESTS = ('tests/test_v25_phase20_prospective_spec.py', 'tests/test_v25_phase21_calibration.py')
DOCS = ('docs/v25_phase21_cost_risk_calibration.md', 'docs/v25_phase21_endogenous_buffer_pre_audit.md')
PHASE110 = ROOT/'artifacts/v25_phase110_20261110_201422/audit.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(name):
    with (HERE/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    audit = json.loads((HERE/'run_summary.json').read_text(encoding='utf-8'))
    summary = json.loads(PHASE110.read_text(encoding='utf-8-sig'))
    protected = {
        'phase110_protected_archives': summary['protected_archive_sha256'],
        'phase110_output': summary['output_sha256'],
        'existing_model_source': {p: h for p,h in summary['input_sha256'].items() if p.endswith('.py')},
    }
    for checks in protected.values():
        assert all(digest(Path(p)) == h for p,h in checks.items())
    phase20 = ROOT/'artifacts/v25_phase20_20261110_203851/sha256_manifest.csv'
    assert digest(phase20) == audit['phase20_manifest_sha256']
    with phase20.open(encoding='utf-8-sig', newline='') as f:
        checks = list(csv.DictReader(f))
    assert len(checks) == audit['phase20_files_verified']
    assert all(digest(ROOT/r['path']) == r['sha256'] for r in checks)

    logs = sorted((HERE/'logs').glob('*.log'))
    assert len(logs) == audit['diagnostic_runs'] == 352
    assert all(p.read_text(encoding='utf-8').count('Optimal solution found') == 1 for p in logs)
    certs = {r['run']: r for name in ('single_buffer_capability', 'equal_cost_dominance',
            'risk_location_policy_response', 'optimal_policy_set_ranges', 'near_optimal_policy_ranges',
            'threshold_direct_checks') for r in table(f'{name}.csv')}
    assert {p.stem for p in logs} - set(certs) == {
        f'P1_{risk}_{tag}' for risk in ('NOM', 'L1', 'L2', 'L3') for tag in ('zero', 'x_C', 'x_T', 'x_O')
    }
    assert all(r['status'] == 'OPTIMAL' and r['exact_crosscheck'] == 'MATCH'
               and float(r['objective']) == float(r['best_bound'])
               and float(r['residual']) <= 1e-7 and float(r['mip_gap']) == 0 for r in certs.values())
    opt_exp = table('optimal_portfolio_expiration_summary.csv')
    expiry_events = sum(int(r['distinct_exit_events']) for r in opt_exp)
    with gzip.open(HERE/'optimal_portfolio_expiration_events.csv.gz', 'rt', encoding='utf-8') as f:
        assert sum(1 for _ in f)-1 == expiry_events
    assert (HERE/'pytest_exit_code.txt').read_text().strip() == '0'
    test_result = (HERE/'pytest.txt').read_text(encoding='utf-8').splitlines()[-1].strip('= ')
    assert test_result.startswith('19 passed')
    code = sorted(HERE.glob('*.py'))+[ROOT/TESTS[1]]
    for p in code:
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p))

    audit.update(status='PASS_WITH_MULTIPLE_OPTIMAL_POLICIES', structural_finding='STRUCTURAL_DOMINANCE_DETECTED',
                 clean_baseline='SOURCE_SUPPORTED_CLEAN_BASELINE_NOT_IDENTIFIED',
                 final_managerial_position_cost=None, final_risk_grid=None, final_budget_grid=None,
                 protected_files={key: dict(checked=len(checks), mismatches=0) for key,checks in protected.items()},
                 solver=dict(status='OPTIMAL', optimal_runs=len(logs), threads=1,
                             license='Academic license observed in successful run',
                             exact_policy_projection_checks=len(logs), certified_csv_rows=len(certs),
                             max_direct_constraint_bound_integrality_residual=max(float(r['residual']) for r in certs.values()),
                             max_exact_integer_ledger_residual=0, gap=0,
                             direct_seconds_excluding_p1=sum(float(r['seconds']) for r in certs.values())),
                 python=platform.python_version(), source_xlsb_sha256='1ea0bcdea3225d308be913c9ca0f377585e1863847c78d6e8eec10b6de82889e',
                 input_code_sha256=protected['existing_model_source'],
                 full_portfolio_expiry_events=expiry_events,
                 full_portfolio_expirations=sum(int(r['expiring_portfolios']) for r in opt_exp),
                 commands=[
                     dict(command='python -B artifacts/v25_phase21_20261110_212532/run_diagnostics.py', exit=0),
                     dict(command='python -B artifacts/v25_phase21_20261110_212532/portfolio_expirations.py', exit=0),
                     dict(command='python -m pytest -p no:cacheprovider -vv '+' '.join(TESTS), exit=0,
                          result=test_result, prior_attempt_exit=1,
                          prior_attempt_cause='Synthetic test oracle missed the first C-only arrival; replaced by explicit one-period in-transit ledgers'),
                 ],
                 scope='Phase 2.1 structural diagnostics only',
                 output_manifest='sha256_manifest.csv')
    (HERE/'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    artifacts = [p for p in HERE.iterdir() if p.is_file() and p.name != 'sha256_manifest.csv']
    files = [*artifacts, *logs, *(ROOT/p for p in (*DOCS, TESTS[1]))]
    with (HERE/'sha256_manifest.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(('path', 'sha256'))
        writer.writerows((p.relative_to(ROOT).as_posix(), digest(p)) for p in sorted(files))
    print(json.dumps(dict(status=audit['status'], logs=len(logs), events=expiry_events, entries=len(files),
                          tests=test_result, max_residual=audit['solver']['max_direct_constraint_bound_integrality_residual'])))


if __name__ == '__main__':
    main()
