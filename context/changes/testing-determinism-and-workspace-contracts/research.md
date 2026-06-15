---
date: 2026-06-15T18:18:22+02:00
researcher: Codex
git_commit: d9bfc199165e44d8840007c78c2ef2b8b45ea226
branch: sketch
repository: quantitative-sentiment-analysis
topic: "Ground rollout Phase 1 of context/foundation/test-plan.md"
tags: [research, codebase, determinism, workspace-isolation, jsonl-export, backtest-dataset]
status: complete
last_updated: 2026-06-15
last_updated_by: Codex
---

# Research: Ground rollout Phase 1 of context/foundation/test-plan.md

**Date**: 2026-06-15T18:18:22+02:00
**Researcher**: Codex
**Git Commit**: d9bfc199165e44d8840007c78c2ef2b8b45ea226
**Branch**: sketch
**Repository**: quantitative-sentiment-analysis

## Research Question

Ground rollout Phase 1 of `context/foundation/test-plan.md`: "Determinism and workspace contracts".

Risks to verify:

- Risk #1: identical input and deterministic run metadata must produce identical records and identical JSONL bytes.
- Risk #2: every storage/API/export boundary must require matching `workspace_id`; `run_id` alone is not sufficient.

## Summary

The current implementation has a strong backend foundation for both risks. Dataset generation starts from a workspace-scoped draft shell, normalizes and sorts provider records, fingerprints deterministic material, writes canonical `DatasetRecord` rows, stores completed runs by `(workspace_id, run_id)`, and exports sorted UTF-8 JSONL bytes through the completed-run repository.

Existing tests already cover repeated deterministic previews, reordered provider input, stable JSONL line serialization, export byte stability from stored records, repository isolation, dataset-start cross-workspace misses, and export cross-workspace misses. A focused backend verification run passed: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-research-main-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset tests/contracts/test_serialization.py tests/contracts/test_schemas.py -p no:cacheprovider` -> `84 passed`.

The main gaps are precise and TDD-able: full stored records are not validated beyond the bounded preview slice, `GET /dataset` lacks a cross-workspace route test, `list_records` lacks an explicit same-run-id cross-workspace test, exported JSONL assertions omit per-record `workspace_id`, and no API-level test proves two independent generation/export flows produce identical JSONL bytes for the same deterministic run identity. Planning should not add e2e for Phase 1; backend pytest contract tests plus FastAPI `TestClient` integration are the cheapest useful layers.

Important scope correction: the product has PRD/stack intent for auth, but current implementation deliberately has no real auth/session/JWT enforcement. Phase 1 should test route/storage workspace isolation, not invent login enforcement.

## Detailed Findings

### Deterministic Dataset Generation

- Dataset generation enters through `POST /api/workspaces/{workspace_id}/backtests/{run_id}/dataset/run` and delegates to `DatasetOrchestrator.run_dataset` ([src/quantitative_sentiment_analysis/backtest_dataset/router.py:68](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:68)).
- The orchestrator first loads the S-01 draft shell with both `workspace_id` and `run_id`, then builds the provider request from the draft identity, instrument, mode, and timeframe ([src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:52](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:52), [src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:58](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:58)).
- Provider records are normalized, sorted, and exact-provider-id deduped before fingerprinting or scoring ([src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:55](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:55), [src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:68](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:68)).
- The normalization sort key is timestamp, provider record ID, source ID, source name, casefolded headline, and original index ([src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:113](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:113)). Gap: `body` is not in this key. Equal timestamp/id/source/headline records with different body can preserve provider input order, so a reordered provider response could still diverge in edge cases.
- `input_fingerprint` material includes workspace, instrument, mode, timeframe, seed, model version, config version, and normalized records; it intentionally excludes `run_id` ([src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:241](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:241), [src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:249](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:249)).
- Dataset records stamp `workspace_id`, `run_id`, record ID, timestamp, source identity/name, sentiment score, `directional_bias`, confidence, relevance, model version, and config version ([src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:148](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:148)).
- Generated record IDs use provider IDs when present; otherwise they hash deterministic material including `input_fingerprint`, provider name, timestamp, headline, source identity, and deterministic index ([src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:290](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:290)).
- Stable serialization normalizes Pydantic models, enums, mappings, sequences, and datetimes; JSON dumps use `allow_nan=False`, compact separators, and sorted keys ([src/quantitative_sentiment_analysis/contracts/serialization.py:18](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/contracts/serialization.py:18), [src/quantitative_sentiment_analysis/contracts/serialization.py:35](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/contracts/serialization.py:35)).
- Datetimes serialize to UTC `Z`, and naive datetimes are rejected ([src/quantitative_sentiment_analysis/contracts/serialization.py:60](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/contracts/serialization.py:60)).

### JSONL Export Determinism

- `export_dataset_jsonl_bytes` first loads the run summary, requires `DatasetRunStatus.COMPLETED`, then lists full records and serializes sorted JSONL lines to UTF-8 bytes ([src/quantitative_sentiment_analysis/backtest_dataset/export.py:18](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/export.py:18), [src/quantitative_sentiment_analysis/backtest_dataset/export.py:30](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/export.py:30)).
- Export ordering is timestamp, `record_id`, source identity, and headline; source identity combines `source_id` and `source_name` so records with only one field remain sortable ([src/quantitative_sentiment_analysis/backtest_dataset/export.py:38](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/export.py:38)).
- The export route is read-only over `CompletedDatasetRepository`; it does not inject a provider or orchestrator, so export cannot implicitly generate data ([src/quantitative_sentiment_analysis/backtest_dataset/router.py:89](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:89), [src/quantitative_sentiment_analysis/backtest_dataset/router.py:93](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:93)).
- The route returns JSONL bytes with download headers and run/config/model metadata in HTTP headers, not as a manifest line ([src/quantitative_sentiment_analysis/backtest_dataset/router.py:106](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:106)).
- Existing export tests cover repeated bytes, newline rules, stable ordering, full-record export beyond preview, and provider-limited rejection ([tests/backtest_dataset/test_export.py:66](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_export.py:66), [tests/backtest_dataset/test_export.py:122](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_export.py:122), [tests/backtest_dataset/test_export.py:167](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_export.py:167)).
- Existing API tests cover successful export, full 105-record body, headers, provider not called for missing export, cross-workspace export `404`, and provider-limited export `409` ([tests/backtest_dataset/test_router.py:203](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:203), [tests/backtest_dataset/test_router.py:240](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:240), [tests/backtest_dataset/test_router.py:261](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:261), [tests/backtest_dataset/test_router.py:277](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:277)).
- Gap: export tests assert `run_id` and `config_version`, but not per-record `workspace_id`; Phase 1 should add that assertion to the export contract/API layer ([tests/backtest_dataset/test_export.py:111](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_export.py:111), [tests/backtest_dataset/test_router.py:235](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:235)).
- Gap: no API-level test creates two independent deterministic runs and compares exported JSONL bytes. Existing tests compare repeated preview serialization and repeated export from one stored run, but not the full HTTP generation -> export flow twice.
- Nuance: exported JSONL contains `run_id` per record, so byte equality across different `run_id`s is not expected. Phase 1 should prove byte equality for identical deterministic input and the same deterministic run identity, or explicitly normalize the assertion if comparing different generated run IDs.
- Nuance: `seed` changes fingerprint/metadata but does not currently affect scoring directly. For records with provider IDs, seed changes may not change every JSONL record byte, though it changes run-level fingerprint material.

### Workspace And Run Boundaries

- Draft shell storage is keyed by `(workspace_id, run_id)` and routes create/fetch draft shells under `/api/workspaces/{workspace_id}/backtests` ([src/quantitative_sentiment_analysis/backtest_shell/repository.py:56](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_shell/repository.py:56), [src/quantitative_sentiment_analysis/backtest_shell/repository.py:86](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_shell/repository.py:86)).
- Completed dataset storage is also keyed by `(workspace_id, run_id)` for run previews and full record tuples ([src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56), [src/quantitative_sentiment_analysis/backtest_dataset/repository.py:72](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/repository.py:72), [src/quantitative_sentiment_analysis/backtest_dataset/repository.py:78](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/repository.py:78), [src/quantitative_sentiment_analysis/backtest_dataset/repository.py:88](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/repository.py:88)).
- Dataset run, dataset preview, and JSONL export routes all take both `workspace_id` and `run_id` from the path and hand both into orchestrator/repository boundaries ([src/quantitative_sentiment_analysis/backtest_dataset/router.py:68](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:68), [src/quantitative_sentiment_analysis/backtest_dataset/router.py:89](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:89), [src/quantitative_sentiment_analysis/backtest_dataset/router.py:123](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:123)).
- Repository misses map to `404` in shell and dataset routes ([src/quantitative_sentiment_analysis/backtest_shell/router.py:49](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_shell/router.py:49), [src/quantitative_sentiment_analysis/backtest_dataset/router.py:101](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:101), [src/quantitative_sentiment_analysis/backtest_dataset/router.py:133](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/router.py:133)).
- Existing negative tests cover draft shell cross-workspace reads, completed repository `get_run` isolation, dataset run workspace mismatch, and export workspace mismatch ([tests/backtest_shell/test_router.py:96](/mnt/e/quantitative-sentiment-analysis/tests/backtest_shell/test_router.py:96), [tests/backtest_dataset/test_repository.py:78](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_repository.py:78), [tests/backtest_dataset/test_router.py:130](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:130), [tests/backtest_dataset/test_router.py:261](/mnt/e/quantitative-sentiment-analysis/tests/backtest_dataset/test_router.py:261)).
- Gap: `GET /dataset` lacks a route-level negative test where `workspace-alpha` has a completed dataset and `workspace-beta` requests the same `run_id`. This is a direct Phase 1 test gap.
- Gap: `list_records` lacks an explicit repository test for same `run_id` across different workspaces. Export uses `list_records`, so `get_run` isolation alone is not the full contract ([src/quantitative_sentiment_analysis/backtest_dataset/export.py:30](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/export.py:30)).
- Important gap: `InMemoryCompletedDatasetRepository.save_run` validates `DatasetRunPreview` using only the first `MAX_DATASET_PREVIEW_RECORDS`; all records beyond the bounded preview are stored without summary-identity validation ([src/quantitative_sentiment_analysis/backtest_dataset/repository.py:67](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/repository.py:67), [src/quantitative_sentiment_analysis/backtest_dataset/schemas.py:107](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_dataset/schemas.py:107)). A mismatched `workspace_id` or `run_id` outside the preview window could later be exported through `list_records`. Phase 1 should plan a failing repository test with more than 100 records and then fix storage validation for the full tuple.

### Quality Boundary Related To Workspace Scope

- The quality adapter reads completed datasets by `(workspace_id, run_id)` and maps canonical records to quality input rows ([src/quantitative_sentiment_analysis/backtest_quality/repository.py:76](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_quality/repository.py:76), [src/quantitative_sentiment_analysis/backtest_quality/repository.py:87](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_quality/repository.py:87)).
- The quality route defensively rejects reports whose returned `workspace_id` or `run_id` differs from the path ([src/quantitative_sentiment_analysis/backtest_quality/router.py:47](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/backtest_quality/router.py:47)).
- Existing adapter tests cover workspace/run isolation and missing movement behavior ([tests/backtest_quality/test_dataset_adapter.py:112](/mnt/e/quantitative-sentiment-analysis/tests/backtest_quality/test_dataset_adapter.py:112), [tests/backtest_quality/test_dataset_adapter.py:136](/mnt/e/quantitative-sentiment-analysis/tests/backtest_quality/test_dataset_adapter.py:136)).
- Gap: the route-level defensive `409` for a provider returning different workspace/run has no direct API test ([tests/backtest_quality/test_router.py:100](/mnt/e/quantitative-sentiment-analysis/tests/backtest_quality/test_router.py:100)). This can be Phase 3 if keeping Phase 1 strictly dataset/export, but it is part of the same workspace-boundary pattern.

### Auth Scope Correction

- The app currently wires CORS and routers only; no auth middleware, current-user context, session, JWT, or workspace ownership enforcement is present ([src/quantitative_sentiment_analysis/main.py:40](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/main.py:40), [src/quantitative_sentiment_analysis/main.py:51](/mnt/e/quantitative-sentiment-analysis/src/quantitative_sentiment_analysis/main.py:51)).
- Frontend API helpers pass workspace IDs from route/UI and do not send authorization headers ([frontend/src/features/backtestShell/api.ts:77](/mnt/e/quantitative-sentiment-analysis/frontend/src/features/backtestShell/api.ts:77), [frontend/src/features/backtestQuality/api.ts:37](/mnt/e/quantitative-sentiment-analysis/frontend/src/features/backtestQuality/api.ts:37)).
- Therefore Phase 1 should not attempt to prove real login ownership. It should prove local/dev path and repository isolation, and leave real authenticated workspace binding as a future auth slice.

## Code References

- `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:52` - Dataset generation service entrypoint.
- `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:241` - Deterministic input fingerprint material.
- `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:55` - Provider normalization, deterministic ordering, exact-ID dedupe.
- `src/quantitative_sentiment_analysis/contracts/serialization.py:18` - Stable JSON data conversion.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:18` - Completed dataset JSONL export boundary.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:38` - Export sort key.
- `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56` - Completed dataset repository tuple-key storage.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:89` - HTTP JSONL export route.
- `tests/backtest_dataset/test_determinism.py:77` - Existing stable serialized preview rerun test.
- `tests/backtest_dataset/test_export.py:66` - Existing stable JSONL bytes test.
- `tests/backtest_dataset/test_router.py:261` - Existing cross-workspace export route test.
- `tests/backtest_dataset/test_repository.py:78` - Existing completed repository `get_run` workspace isolation test.

## Architecture Insights

- Determinism has two different oracles. `input_fingerprint` intentionally ignores `run_id`, while JSONL records intentionally include `run_id`. Tests must not expect byte-identical JSONL across different run IDs unless they normalize that field outside the product contract.
- Workspace isolation is currently structural, not authenticated. The route and repository boundaries consistently carry `workspace_id`, but the system trusts the path parameter because auth is not implemented.
- The completed repository separates bounded preview from full stored records. That is correct for UI payload size, but it creates a validation gap: the full record tuple must be checked before storage/export, not only the preview slice.
- E2E would add cost without unique signal for this phase. The failure modes are in backend contracts, repository behavior, route semantics, and byte serialization.

## Historical Context

- F-01 contracts require `workspace_id` at API/storage/dataset/export boundaries, state that `run_id` alone is insufficient, and define stable JSONL rules ([context/foundation/quality-contracts.md:57](/mnt/e/quantitative-sentiment-analysis/context/foundation/quality-contracts.md:57), [context/foundation/quality-contracts.md:128](/mnt/e/quantitative-sentiment-analysis/context/foundation/quality-contracts.md:128)).
- S-01 deliberately avoided real auth and durable storage while requiring repository reads to use both `workspace_id` and `run_id` ([context/changes/workspace-backtest-shell/plan.md:29](/mnt/e/quantitative-sentiment-analysis/context/changes/workspace-backtest-shell/plan.md:29), [context/changes/workspace-backtest-shell/plan.md:89](/mnt/e/quantitative-sentiment-analysis/context/changes/workspace-backtest-shell/plan.md:89)).
- S-02 specified completed-run storage keyed by `(workspace_id, run_id)` and deterministic input fingerprinting over normalized provider records, run metadata, seed, model version, and config version ([context/changes/deterministic-news-dataset/plan.md:51](/mnt/e/quantitative-sentiment-analysis/context/changes/deterministic-news-dataset/plan.md:51), [context/changes/deterministic-news-dataset/plan.md:105](/mnt/e/quantitative-sentiment-analysis/context/changes/deterministic-news-dataset/plan.md:105)).
- S-03 specified JSONL export as read-only over completed S-02 records, with no implicit generation, deterministic ordering, full records rather than bounded preview, and `404`/`409` semantics ([context/changes/jsonl-export/plan.md:15](/mnt/e/quantitative-sentiment-analysis/context/changes/jsonl-export/plan.md:15), [context/changes/jsonl-export/plan.md:138](/mnt/e/quantitative-sentiment-analysis/context/changes/jsonl-export/plan.md:138)).
- Prior JSONL research found the same architecture: export is completed-run-only, body has one canonical `DatasetRecord` per line, and durable export storage/CSV remain intentionally deferred ([context/changes/jsonl-export/research.md:28](/mnt/e/quantitative-sentiment-analysis/context/changes/jsonl-export/research.md:28), [context/changes/jsonl-export/research.md:139](/mnt/e/quantitative-sentiment-analysis/context/changes/jsonl-export/research.md:139)).

## Related Research

- [context/changes/jsonl-export/research.md](/mnt/e/quantitative-sentiment-analysis/context/changes/jsonl-export/research.md) - Prior research for JSONL export architecture and frontend download flow.

## Open Questions

- Should future product requirements demand byte-identical JSONL across different `run_id`s? Current contracts include `run_id` per record, so Phase 1 should treat same-run-id bytes as the product oracle.
- Should seed affect scoring directly in a future model-backed scorer? Today it affects fingerprint/metadata but not deterministic rule/lexicon scoring output.
- Should normalization include `body` in its sort key now, or should Phase 2 own that as provider-pipeline hardening? It is a real determinism edge case when metadata/headline fields tie.
- When real auth lands, what is the source of truth for binding an authenticated trader to a workspace? Current local/dev routes cannot prove that.
