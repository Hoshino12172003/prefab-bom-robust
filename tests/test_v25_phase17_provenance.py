import csv
import importlib.util
import json
from pathlib import Path

import pytest

from examples.run_v25_formal import check_exact_budget
from prefab_v25.formal import frozen_runs, manifest_bytes


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/v25_phase17_20261110_163116'
spec = importlib.util.spec_from_file_location('phase17_evidence', OUT/'collect_evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(name):
    with (OUT/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


@pytest.fixture
def blocked_manifest():
    return read_json(OUT/'clean_baseline_manifest.json')


@pytest.fixture
def hypothetical():
    row = dict(candidate_id='SYNTHETIC', batch_id='TEST_LOT', field='initial_inventory',
               node=evidence.PROD, item=evidence.CELL[0], period=60, original_value=10,
               restored_value=20, clean_value=30, unit='units', evidence_class='DIRECT_DATA',
               source='test fixture', derivation='10+20', parameter_id='TEST')
    provenance = {key:'test fixture' for key in evidence.PROVENANCE_FIELDS}
    provenance.update(parameter_id='TEST',status='PATCH_AUTHORIZED',evidence_class='DIRECT_DATA')
    manifest = dict(authorized_candidates=['SYNTHETIC'],authorized_batch_ids=['TEST_LOT'],
                    authorized_patch_keys=[['initial_inventory', evidence.PROD, evidence.CELL[0], 60]],
                    required_parameter_ids=['TEST'])
    return row, [provenance], manifest


def test_source_workbook_identity_read_only(blocked_manifest):
    source = Path(blocked_manifest['source_archive'])
    if not source.is_file():
        pytest.skip('original external Mendeley ZIP is unavailable')
    before = evidence.digest(source)
    workbook = evidence.verified_bytes(source)
    assert evidence.hashlib.sha256(workbook).hexdigest() == blocked_manifest['source_workbook_sha256']
    assert evidence.digest(source) == before == read_json(OUT/'audit.json')['input_sha256'][str(source)]


def test_held_manifest_authorizes_no_patch(blocked_manifest, hypothetical):
    provenance = read_csv('parameter_provenance.csv')
    assert blocked_manifest['optimizer_calls_allowed'] == 0
    assert not read_csv('clean_baseline_patch.csv')
    evidence.check_patch([], blocked_manifest, provenance)
    with pytest.raises(ValueError,match='authorization'):
        evidence.check_patch([hypothetical[0]], blocked_manifest, provenance)


def test_only_explicit_patch_keys_allowed(hypothetical):
    row, provenance, manifest = hypothetical
    evidence.check_patch([row], manifest, provenance)
    with pytest.raises(ValueError,match='authorization'):
        evidence.check_patch([dict(row, field='demand')], manifest, provenance)


def test_10_6_4_conservation_and_pack_destination():
    evidence.check_conversion((40,24,16), (20,12,8), 2, (10,6,4), 2)
    with pytest.raises(ValueError,match='conservation'):
        evidence.check_conversion((40,24,16), (20,13,8), 2, (10,6,4), 2)
    with pytest.raises(ValueError,match='transfer'):
        evidence.check_conversion((40,24,16), (20,12,8), 2, (10,6,4), 0)


def test_duplicate_lot_sku_across_keys_rejected(hypothetical):
    row, provenance, manifest = hypothetical
    duplicate = dict(row, period=61)
    manifest['authorized_patch_keys'].append(['initial_inventory', row['node'], row['item'], 61])
    with pytest.raises(ValueError,match='duplicate'):
        evidence.check_patch([row, duplicate], manifest, provenance)


def test_flow_change_requires_direct_evidence(hypothetical, blocked_manifest):
    row, provenance, manifest = hypothetical
    assert blocked_manifest['preserved_historical_flows'] == 117
    row.update(field='historical_initial_flow',evidence_class='SUPPORTED_INFERENCE')
    provenance[0]['evidence_class'] = 'SUPPORTED_INFERENCE'
    manifest['authorized_patch_keys'] = [[row[k] for k in ('field','node','item','period')]]
    with pytest.raises(ValueError,match='direct evidence'):
        evidence.check_patch([row],manifest,provenance)


def test_clean_b0_monotonicity_gate():
    evidence.check_clean_b0(26448,26448)
    evidence.check_clean_b0(26449,26448)
    with pytest.raises(ValueError,match='HOLD_CLEAN_BASELINE_MAPPING_ERROR'):
        evidence.check_clean_b0(26447,26448)


def test_frozen_exact_budget_gate_still_active():
    run = next(r for r in frozen_runs(manifest_bytes(evidence.FORMAL/'manifest.json')) if r.id=='nominal_B50')
    report = dict(certified=True,buffers=dict(x_cell_kit=61,x_t1_pack=0,x_oem_pack=0))
    check_exact_budget(run,report)
    assert not report['certified'] and 0 < report['exact_budget_residual_usd'] < 1e-9


def test_all_six_phase16_certificates_immutable():
    audit = read_json(OUT/'audit.json')
    certificates = audit['historical_case_certificates']
    assert certificates == dict(nominal_B0=26448,nominal_B20=26472,nominal_B50=26508,nominal_B100=26569,DE_B0=25974,DE_B50=26034)
    prior = read_json(evidence.PHASE16/'audit.json')
    for row in prior['all_formal_recertification']:
        assert evidence.digest(evidence.PHASE16/row['exact_certificate_file']) == row['exact_certificate_sha256']
    path = evidence.PHASE16/'all_formal_recertification.csv'
    assert evidence.digest(path) == audit['immutable_inputs_before_after_sha256'][str(path)]


def test_missing_or_blank_provenance_fails_closed(blocked_manifest):
    rows = read_csv('parameter_provenance.csv')
    evidence.check_provenance(rows,blocked_manifest['required_parameter_ids'])
    with pytest.raises(ValueError,match='missing provenance'):
        evidence.check_provenance(rows[1:],blocked_manifest['required_parameter_ids'])
    rows[0]['primary_source'] = ''
    with pytest.raises(ValueError,match='invalid provenance'):
        evidence.check_provenance(rows,blocked_manifest['required_parameter_ids'])
