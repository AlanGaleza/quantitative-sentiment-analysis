# Test Determinism and Workspace Contracts Implementation Plan

## Overview

This plan executes rollout Phase 1 from `context/foundation/test-plan.md`: protect deterministic BACKTEST dataset generation/export and enforce workspace/run boundaries at storage, API, and JSONL export surfaces.

The change is intentionally backend-focused. It strengthens existing pytest contract and FastAPI `TestClient` coverage, then fixes the one real storage-boundary gap found during research: full records beyond the bounded preview are stored without full-run validation.

## Current State Analysis

The backend already has strong foundations for this rollout. Dataset generation starts from a workspace-scoped draft shell, normalizes provider records, creates canonical `DatasetRecord` rows, stores completed runs by `(workspace_id, run_id)`, and exports sorted UTF-8 JSONL bytes from stored records.

The main gap is that `InMemoryCompletedDatasetRepository.save_run` constructs `DatasetRunPreview` from only the first `MAX_DATASET_PREVIEW_RECORDS` records, then stores the full tuple without validating every stored record against the run summary. Because JSONL export uses `list_records`, a mismatched record after the preview window could be exported later.

## Desired End State

After this plan is complete:

- Identical provider input and deterministic run metadata produce identical API preview records and identical JSONL bytes when generated through two independent local/dev repository instances using the same deterministic `run_id`.
- Completed-run storage rejects mixed-workspace, mixed-run, mixed-config, or miscounted full record sets before they can be stored or exported.
- `GET /dataset`, `list_records`, and JSONL export all prove that `workspace_id` is required; `run_id` alone is not a sufficient access boundary.
- JSONL contract tests assert `workspace_id` per exported record, not only response headers and `run_id`.

### Key Discoveries:

- `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:61` stores completed runs and currently validates through `DatasetRunPreview` before writing the full record tuple.
- `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:88` exposes full records through `list_records`; `src/quantitative_sentiment_analysis/backtest_dataset/export.py:30` uses that full tuple for JSONL export.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:123` already routes `GET /dataset` by both `workspace_id` and `run_id`, but route-level cross-workspace coverage is missing.
- `tests/backtest_dataset/test_repository.py:78` covers `get_run` isolation but not explicit `list_records` isolation.
- `tests/backtest_dataset/test_router.py:261` covers cross-workspace export, but `tests/backtest_dataset/test_router.py:92` covers successful `GET /dataset` without the matching negative workspace case.
- `tests/backtest_dataset/test_export.py:66` proves stable repeated JSONL bytes from one stored run, but the API layer does not yet prove generation then export is byte-identical across independent deterministic flows.

## What We're NOT Doing

- No real auth, session, JWT, user ownership, or workspace membership enforcement. Current app routes trust the path `workspace_id`; this phase tests route/storage isolation only.
- No frontend, browser, or E2E tests. The risks are backend contracts, repository behavior, route semantics, and byte serialization.
- No provider normalization `body` tie-breaker change. That edge belongs to Phase 2 provider relevance pipeline.
- No quality route/provider defensive `409` test. That belongs to Phase 3 quality view truthfulness.
- No persistent storage migration or production database repository.
- No change to the canonical JSONL record schema.

## Implementation Approach

Use the existing backend testing style: pytest for repository/export contracts and FastAPI `TestClient` for route integration. Add failing tests first around the known gaps, then implement the smallest repository validation needed to make storage/export boundaries trustworthy. Keep all data deterministic through fixed provider fixtures, fixed `run_id`, fixed timestamps, and isolated in-memory repositories.

## Critical Implementation Details

### Full Stored Records Must Be Validated Before Storage

`DatasetRunPreview` is a bounded API payload and only sees the first 100 records. The repository must validate the full copied tuple before assigning `_runs[key]` and `_records[key]`; otherwise a bad record outside the preview can still be exported.

### JSONL Byte Equality Uses The Same Run Identity

JSONL record bodies include `run_id`, so byte equality across different `run_id`s is not the product contract. The API determinism test should compare independent flows that use the same deterministic `run_id` and equivalent deterministic inputs.

## Phase 1: Full-Record Storage Contract

### Overview

Close the full-record validation gap in completed-run storage, especially records beyond the preview window.

### Changes Required:

#### 1. Repository Contract Tests

**File**: `tests/backtest_dataset/test_repository.py`

**Intent**: Add failing tests showing that full stored records, including records after index 99, must match the run summary before storage succeeds.

**Contract**: Add tests that build more than `MAX_DATASET_PREVIEW_RECORDS` records and assert `InMemoryCompletedDatasetRepository.save_run` rejects:

- a record outside the preview window whose `workspace_id` or `run_id` differs from `DatasetRunSummary`;
- summary relevance counts or `record_count` that do not match the full stored tuple.

The test should assert a validation failure before data is retrievable through `get_run` or `list_records`.

#### 2. Completed Dataset Repository Validation

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py`

**Intent**: Validate the full record tuple as the storage boundary, not just the API preview subset.

**Contract**: `InMemoryCompletedDatasetRepository.save_run` must reject invalid full record sets before writing to `_runs` or `_records`.

For every stored `DatasetRecord`, validate:

- `workspace_id`, `run_id`, `instrument`, `mode`, `model_version`, and `config_version` match the summary;
- full tuple length equals `summary.record_count`;
- full relevance counts equal `summary.relevant_count`, `summary.noise_count`, and `summary.irrelevant_count`;
- provider-limited terminal summaries do not store canonical dataset records.

No public API route shape changes are expected. A plain `ValueError` from repository validation is acceptable unless the implementer finds an existing exception pattern that fits better.

### Success Criteria:

#### Automated Verification:

- Repository tests fail before the repository validation fix and pass after it: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset/test_repository.py -p no:cacheprovider`
- Existing provider-limited repository behavior still passes with zero records.

#### Manual Verification:

None required; this phase is fully covered by backend contract tests.

---

## Phase 2: Workspace Boundary Coverage

### Overview

Prove the same `run_id` cannot cross workspace boundaries through repository reads or the `GET /dataset` route.

### Changes Required:

#### 1. Full Record Repository Isolation Test

**File**: `tests/backtest_dataset/test_repository.py`

**Intent**: Cover `list_records` directly, because JSONL export depends on it and `get_run` isolation alone does not prove full-record isolation.

**Contract**: Extend or add a repository test where `workspace-alpha` and `workspace-beta` both store `draft-run-000001`, then assert:

- `list_records("workspace-alpha", "draft-run-000001")` returns only alpha records;
- `list_records("workspace-beta", "draft-run-000001")` returns only beta records;
- `list_records("workspace-gamma", "draft-run-000001")` raises `CompletedDatasetRunNotFoundError`.

#### 2. Dataset Preview Route Workspace Mismatch Test

**File**: `tests/backtest_dataset/test_router.py`

**Intent**: Add the route-level negative case missing from `GET /dataset`.

**Contract**: Generate or store a completed dataset for `workspace-alpha`, then request `/api/workspaces/workspace-beta/backtests/draft-run-fixed/dataset` for the same `run_id` and assert `404`. The provider should not be relied on for the negative read after the completed run already exists under alpha.

### Success Criteria:

#### Automated Verification:

- Repository workspace isolation test passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset/test_repository.py -p no:cacheprovider`
- Dataset route workspace mismatch test passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset/test_router.py -p no:cacheprovider`

#### Manual Verification:

None required; this phase is fully covered by backend integration tests.

---

## Phase 3: API Determinism and JSONL Bytes

### Overview

Prove the user-facing API path, not only lower-level helpers, produces identical records and identical JSONL bytes for identical deterministic input and run metadata.

### Changes Required:

#### 1. JSONL Workspace Field Assertions

**File**: `tests/backtest_dataset/test_export.py`

**Intent**: Strengthen the export contract so each exported record proves its workspace boundary in the JSONL body.

**Contract**: Extend the existing JSONL payload assertions to require `workspace_id == "workspace-alpha"` for every decoded line.

#### 2. API Export Workspace Field Assertions

**File**: `tests/backtest_dataset/test_router.py`

**Intent**: Match the lower-level export contract at the HTTP route layer.

**Contract**: Extend the full completed dataset export route test to assert every decoded JSONL payload has `workspace_id == "workspace-alpha"`, in addition to existing header, `run_id`, and `config_version` assertions.

#### 3. Independent API Rerun Byte Equality Test

**File**: `tests/backtest_dataset/test_router.py`

**Intent**: Prove two independent local/dev flows generate identical preview records and identical export bytes through the API.

**Contract**: Add a test that runs:

- fresh shell repository + fresh completed repository + fixed fixture provider;
- create the same draft run identity with deterministic `run_id`;
- `POST /dataset/run`;
- `GET /dataset/export.jsonl`;
- repeat with a new isolated repository pair and the same deterministic inputs;
- assert the two preview JSON payloads are identical and the two response byte bodies are identical.

The test must compare real response bytes without normalizing `run_id` out of the JSONL.

### Success Criteria:

#### Automated Verification:

- Export contract tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset/test_export.py -p no:cacheprovider`
- API route determinism and export tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset/test_router.py -p no:cacheprovider`

#### Manual Verification:

None required; this phase is fully covered by backend integration tests.

---

## Phase 4: Verification and Rollout Notes

### Overview

Run the focused backend gate for risks #1/#2 and update the rollout cookbook so future tests follow the same deterministic patterns.

### Changes Required:

#### 1. Rollout Cookbook Notes

**File**: `context/foundation/test-plan.md`

**Intent**: Replace the Phase 1 TBD cookbook entries with concise patterns discovered while implementing the tests.

**Contract**: Update `§6.1 Adding a determinism or JSONL stability test` and `§6.2 Adding a workspace/access-boundary API test` with short notes covering:

- same deterministic `run_id` when asserting byte-identical JSONL;
- isolated in-memory repositories for independent reruns;
- workspace mismatch tests must use the same `run_id` under different `workspace_id`s;
- assert both response headers and per-record `workspace_id` for JSONL exports.

#### 2. Focused Backend Gate

**File**: no source file; command verification only.

**Intent**: Confirm the strengthened backend contract suite passes without pulling in frontend or E2E.

**Contract**: Run the focused backend command:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset tests/contracts/test_serialization.py tests/contracts/test_schemas.py -p no:cacheprovider
```

If cheap in the current environment, also run the full backend pytest suite:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider
```

Document both outcomes in the implementation summary.

### Success Criteria:

#### Automated Verification:

- Focused backend gate passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-phase1-venv UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/backtest_dataset tests/contracts/test_serialization.py tests/contracts/test_schemas.py -p no:cacheprovider`
- Full backend pytest is either passed or explicitly reported as skipped/blocked with reason.

#### Manual Verification:

- Human confirms the rollout stayed within Phase 1 scope and did not pull in auth, frontend, quality dashboard, or provider pipeline behavior.

---

## Testing Strategy

### Unit Tests:

- Repository tests validate full record tuple consistency, including records beyond the bounded preview.
- Repository tests prove `list_records` cannot cross workspace boundaries when `run_id` matches.
- Export tests assert stable JSONL bytes, deterministic ordering, and per-record `workspace_id`.

### Integration Tests:

- FastAPI route tests prove `POST /dataset/run`, `GET /dataset`, and `GET /dataset/export.jsonl` preserve deterministic output and workspace isolation.
- API rerun tests use independent in-memory repositories to avoid accidental reuse of stored state.

### Manual Testing Steps:

1. Review pytest output for the focused backend gate.
2. Confirm the implementation summary explicitly notes that auth, quality route, frontend, and provider normalization `body` tie-breaker are out of scope.

## Performance Considerations

Full-record validation is linear in the number of stored dataset records and runs only when saving a completed local/dev run. This is acceptable for the current in-memory BACKTEST storage boundary and is cheaper than allowing bad records to reach export.

## Migration Notes

No migration is required. The completed dataset repository is process-local in-memory storage, and this plan does not introduce durable persistence or schema changes.

## References

- Related research: `context/changes/testing-determinism-and-workspace-contracts/research.md`
- Test rollout: `context/foundation/test-plan.md`
- Workspace and JSONL contracts: `context/foundation/quality-contracts.md`
- Completed dataset repository: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:61`
- JSONL export boundary: `src/quantitative_sentiment_analysis/backtest_dataset/export.py:18`
- Dataset routes: `src/quantitative_sentiment_analysis/backtest_dataset/router.py:68`
- Existing repository tests: `tests/backtest_dataset/test_repository.py:65`
- Existing route tests: `tests/backtest_dataset/test_router.py:92`
- Existing export tests: `tests/backtest_dataset/test_export.py:66`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Full-Record Storage Contract

#### Automated

- [x] 1.1 Repository tests fail before the repository validation fix and pass after it — 942f352
- [x] 1.2 Existing provider-limited repository behavior still passes with zero records — 942f352

### Phase 2: Workspace Boundary Coverage

#### Automated

- [x] 2.1 Repository workspace isolation test passes — 2f4069d
- [x] 2.2 Dataset route workspace mismatch test passes — 2f4069d

### Phase 3: API Determinism and JSONL Bytes

#### Automated

- [x] 3.1 Export contract tests pass — 30c4c68
- [x] 3.2 API route determinism and export tests pass — 30c4c68

### Phase 4: Verification and Rollout Notes

#### Automated

- [x] 4.1 Focused backend gate passes — 3ef220a
- [x] 4.2 Full backend pytest is either passed or explicitly reported as skipped/blocked with reason — 3ef220a

#### Manual

- [x] 4.3 Human confirms the rollout stayed within Phase 1 scope and did not pull in auth, frontend, quality dashboard, or provider pipeline behavior — 3ef220a
