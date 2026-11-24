# Scenario Agent V1

Scope: fixed historical V3 network, known risk catalog, unseen complete Master policy. This package does not integrate an agent into C&CG. Unseen-RHS and cross-network generalization remain blocked.

## Reproduce

Use Python 3.12 and the versions in `training/v1/training_config_v1.json` (NumPy, SciPy, scikit-learn, pyxlsb); install joblib and threadpoolctl as recorded in the formal result manifest. Set `PYTHONPATH=src`.

- Offline checks: `python -m pytest tests/test_scenario_training_pipeline_v1.py tests/test_scenario_policy_cv_v1.py tests/test_scenario_training_audit_v1.py tests/test_scenario_formal_v1.py`.
- Formal training: `python -m scenario_agent.training.formal --allow-training`. Existing results are deliberately not overwritten. Run in a fresh checkout with result output paths absent to reproduce; retain the published results separately.
- Replay original feature generation with `scenario_agent.portable.portable_replay_root`: the context yields an isolated root for `load_standardized_v3` / `replay_and_isolation`. It preserves original source bytes without overwriting historical optimizer code in the checkout.

The original hash-pinned `design.py` had a machine-local external ZIP locator. The remote historical version uses a relative locator. Only that string differs; its exact original bytes are preserved in `provenance/design_v3_original.py`, for hash verification inside the isolated replay root. Training from the standardized cache does not need the external XLSB ZIP or this locator. No Gurobi execution is needed.

The data layer preserves 576 queries, 33 whole ranking groups, 148 policy/RHS pairs, 40 names and 38 RHS identities. Repeated calls are retained and weighted within training folds, not treated as independent networks. The two small original dataset audit documents are required by the frozen data manifest and retained as provenance. Temporary tests, broad Excel audits, diagnostic tables, failed run artifacts and unrelated local work are intentionally excluded from PRs.

Three dependent changes are separated into data/extractor, policy-CV/training interfaces, and formal ablation/results PRs. Do not merge the third without its predecessors. Formal optimizer source is reused from the default branch without algorithm changes.
