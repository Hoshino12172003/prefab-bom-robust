import gzip
import json
from hashlib import sha256
from pathlib import Path

import pytest

from examples.run_v25_formal import BEST_KNOWN_FORMAL_DELIVERIES, check_exact_budget, check_witness_bound
from prefab_v25.formal import frozen_runs, manifest_bytes


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/v25_formal_feasible_witnesses.json.gz'
ARCHIVE = ROOT / 'artifacts/v25_formal_20261110/audit.json'
PHASE15_WITNESSES = {'nominal_B20': 26468, 'nominal_B50': 26498, 'DE_B50': 26024}


def test_full_formal_witness_vectors_are_preserved():
    assert sha256(FIXTURE.read_bytes()).hexdigest() == '706e4c5393cf3932370d7690bd8305512c0015bd6d4bc76b02dfb5286107c693'
    with gzip.open(FIXTURE, 'rt', encoding='utf-8') as stream:
        vectors = json.load(stream)
    assert set(vectors) == set(PHASE15_WITNESSES)
    assert set(vectors['DE_B50']) == {'NOM', 'L1_CERT', 'L2_CERT', 'L3_CERT'}
    for run, scenarios in vectors.items():
        assert len(scenarios) == (4 if run == 'DE_B50' else 1)
        for block in scenarios.values():
            assert set(block) == {'inventory', 'supply', 'dispatch', 'deliveries'}
            assert all(block.values())


@pytest.mark.parametrize('run,known_delivery', PHASE15_WITNESSES.items())
def test_formal_certification_rejects_historical_optimum_below_witness(run, known_delivery):
    archived = json.loads(ARCHIVE.read_text(encoding='utf-8'))['results'][run]
    assert archived['objective'] < known_delivery / 28000
    assert BEST_KNOWN_FORMAL_DELIVERIES[run] >= known_delivery
    result = {key: archived[key] for key in ('status', 'certified', 'objective', 'bound')}
    check_witness_bound(run, result, 28000)
    assert result['solver_reported_certified'] and not result['certified']
    assert result['status'] == 'OPTIMAL'
    assert result['objective'] == archived['objective'] and result['bound'] == archived['bound']
    assert result['known_feasible_witness']['objective'] >= known_delivery / 28000
    assert not result['known_feasible_witness']['passed']


@pytest.mark.parametrize('run', BEST_KNOWN_FORMAL_DELIVERIES)
def test_gate_checks_unrounded_maximum_and_upper_bound_independently(run):
    floor = BEST_KNOWN_FORMAL_DELIVERIES[run] / 28000
    for objective, bound, passed in ((floor, floor, True), (floor - 1/28000, floor, False),
                                     (floor, floor - 1/28000, False), (floor, None, False)):
        result = dict(objective=objective, bound=bound, certified=True)
        check_witness_bound(run, result, 28000)
        assert result['certified'] == passed
    result = dict(objective=floor, bound=floor, certified=False)
    check_witness_bound(run, result, 28000)
    assert not result['certified']


@pytest.mark.parametrize('name,tolerant_kits', [('nominal_B50', 61), ('nominal_B100', 122), ('DE_B50', 61)])
def test_exact_budget_gate_rejects_tolerance_only_incumbent(name, tolerant_kits):
    run = next(r for r in frozen_runs(manifest_bytes(ARCHIVE.with_name('manifest.json'))) if r.id == name)
    buffers = dict(x_cell_kit=tolerant_kits, x_t1_pack=0, x_oem_pack=0)
    result = dict(certified=True, buffers=buffers)
    check_exact_budget(run, result)
    assert 0 < result['exact_budget_residual_usd'] < 1e-9
    assert not result['certified']
    buffers['x_cell_kit'] -= 1
    result['certified'] = True
    check_exact_budget(run, result)
    assert result['exact_budget_residual_usd'] == 0
    assert result['certified']
