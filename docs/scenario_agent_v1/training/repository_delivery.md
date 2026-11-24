# Scenario Agent V1 repository delivery

## Three dependent draft PRs

1. [PR #14 — frozen V3 data and shared extractor](https://github.com/Hoshino12172003/prefab-bom-robust/pull/14), commit `6118551d19a7208b935bd9b4a4d5cc114b97a72b`: 44 explicit package files plus hash-preserving attributes.
2. [PR #15 — policy-isolated training pipeline](https://github.com/Hoshino12172003/prefab-bom-robust/pull/15), commit `a46f4db0c8316adb154327c631612cfa6f2fa99d`: 30 explicit package files, based on #14.
3. [PR #16 — formal training and ablations](https://github.com/Hoshino12172003/prefab-bom-robust/pull/16), trained-result commit `1c07466a363c96d61399dd7fb61ed9ad5cbc3ca9`: 51 explicit package files, based on #15. A following documentation-only commit adds this index and clean-export test evidence.

Merge in dependency order; none has been merged by this task. The default branch and the existing V3.3 PR series are left unchanged. The original local branch, index and unrelated uncommitted edits are preserved.

## Inclusion boundary

Included: full standardized BOM/network data, source provenance, all original training queries, frozen grouping and feature contracts, shared extractor, offline training code, tests, model objects, predictions, selection traces and final reports. The two original dataset audits and core preflight evidence are retained because the frozen manifests reference them.

Excluded: general Excel inspection reports, dual-agent feasibility prose, temporary tests and exports, failed serialization artifacts, unrelated local changes, new Gurobi runs, and online C&CG integration. Existing optimizer paths are unchanged in all three diffs.

One remote historical source differs from its pinned original only in the external ZIP locator. Its original bytes are kept in `experiments/scenario_agent_v1/provenance/design_v3_original.py`. `portable_replay_root` reconstructs an isolated replay root rather than modifying the historical checkout. A post-training portability change to training_manifest is recorded separately; its training-time bytes are preserved as `provenance/training_manifest_before_portable.py`. Trained implementation hashes remain in the formal result manifest.

## Validation and interpretation

The clean export of `1c07466a363c96d61399dd7fb61ed9ad5cbc3ca9` passed 50 offline tests in 39.80 s. `results/clean_checkout_tests.xml` is the corresponding JUnit evidence. Published package bytes match their local originals; raw 84-column data, source labels, strict split BLOCK, and both policy-CV manifests retain their hashes.

Formal outputs contain 510 completed estimator fits, 5184 test-prediction rows, 45 fold-metric rows, 480 inner-parameter records and 35 fitted model/catalog artifacts. The prior failed serialization attempt was before outer-test predictions and is not pooled with the successful run.

ML_RANKING_VALUE=NO and BOM_INCREMENTAL_VALUE=NO mean insufficient incremental ranking evidence in this five-policy experiment. All methods reach the Recall@1 tie ceiling, while Catalog-history has the strongest non-hindsight tau-b. Ridge's lower MAE is not a claim of better worst-case ranking. Catalog-history remains the predeclared provisional default, not an outer-test-selected winner. Unseen-RHS, cross-network and C&CG-speedup claims remain blocked.
