# JSONL Export Implementation Plan

## Overview

Implement S-03: a trader can export a complete deterministic BTCUSD BACKTEST dataset as JSONL after S-02 dataset generation completes. The export should reuse canonical `DatasetRecord` rows and stable serialization, expose a downloadable API response, and add a shell UI action without creating local durable export artifacts.

## Current State Analysis

S-02 has completed dataset generation and local/dev in-memory completed-run storage. The backend can save and retrieve full records through `CompletedDatasetRepository.list_records()` while the existing dataset preview API returns only a bounded subset. Stable JSON serialization helpers already exist for canonical dataset records.

The frontend shell can create a draft BACKTEST run, trigger deterministic dataset generation, and show completed dataset metadata plus preview rows. It does not currently offer any download action. Tests explicitly assert that no dataset export endpoint exists yet, so S-03 should replace that absence with a real route and regression coverage.

## Desired End State

A completed dataset run is exportable at `GET /api/workspaces/{workspace_id}/backtests/{run_id}/dataset/export.jsonl`. The response body is UTF-8 JSONL with exactly one canonical `DatasetRecord` per line, newline terminated, no blank lines, deterministic key ordering/timestamps, and stable bytes for repeated exports of identical records.

The route returns `404` when the completed dataset is missing or outside the workspace boundary, `409` when the stored run is not exportable as a completed dataset, and never triggers dataset generation implicitly. The frontend shows an explicit JSONL download action only after a completed dataset run and handles API errors without rendering the full export in the page.

### Key Discoveries:

- `src/quantitative_sentiment_analysis/contracts/serialization.py:35` already provides `stable_json_dumps()`, and `src/quantitative_sentiment_analysis/contracts/serialization.py:45` provides `dataset_record_jsonl_line(record)`.
- `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:40` exposes `list_records(workspace_id, run_id)` for complete stored records, while `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:68` bounds the preview response separately.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:85` currently exposes `GET .../dataset` for the preview but no export route.
- `tests/backtest_dataset/test_router.py:222` currently asserts the export endpoint does not exist and must be replaced by positive export coverage.
- `frontend/src/features/backtestShell/api.ts:51` already centralizes dataset URL construction, and `frontend/src/features/backtestShell/BacktestShellPage.tsx:316` is the completed-dataset branch where the download action belongs.

## What We're NOT Doing

- No CSV export, format negotiation, sidecar manifest endpoint, or metadata line inside the JSONL body.
- No durable database, object storage, local filesystem export persistence, committed `.jsonl` fixtures, or generated data files in the repo.
- No implicit dataset generation from the export route.
- No provider ingestion changes, price enrichment, live streaming, broker integration, order execution, or investment-recommendation wording.
- No auth/session model changes beyond preserving the existing workspace/run path boundary.

## Implementation Approach

Keep the feature as a vertical slice over the existing S-02 completed-run boundary. Add a focused backend export module inside `backtest_dataset`, use `list_records()` for full rows, check the stored run summary before exporting, sort records deterministically at export time, and emit existing `dataset_record_jsonl_line()` output.

Wire the export module into the current dataset router using a GET download route. On the frontend, extend the existing shell API utilities and completed-dataset panel with a testable blob download helper/action. Update tests and handoff docs so future CSV or durable export storage is clearly deferred rather than accidentally implied.

## Critical Implementation Details

### Exportability State

`InMemoryCompletedDatasetRepository.save_run()` accepts both `COMPLETED` and `FAILED_PROVIDER_LIMITATION` terminal summaries. The export route must inspect the stored summary via `get_run()` or an equivalent repository method before streaming records, because provider-limited terminal runs are stored but should return `409` rather than an empty or partial JSONL file.

### Deterministic Ordering

The export service should impose order at export time, regardless of repository insertion order. Use the quality-contract sort keys: `timestamp`, `record_id`, source identity, and `headline`; source identity should be stable when only `source_id` or only `source_name` is present.

## Phase 1: Backend Export Contract

### Overview

Create the backend export boundary that turns completed canonical records into deterministic JSONL bytes or an iterator. This phase does not expose the HTTP route yet; it establishes the behavior and tests that the route will depend on.

### Changes Required:

#### 1. Export module

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/export.py`

**Intent**: Add a small service/function boundary for JSONL exports over completed S-02 records. It should keep export-specific ordering and state validation out of the router.

**Contract**: The module exposes a JSONL export function or service that accepts a `CompletedDatasetRepository`, `workspace_id`, and `run_id`, verifies that the stored run is exportable, obtains full records via `list_records()`, sorts deterministically, and emits UTF-8 JSONL bytes or newline-terminated strings.

#### 2. Export error types

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/export.py`

**Intent**: Model not-exportable terminal runs separately from missing completed runs so the route can map errors cleanly.

**Contract**: Provider-limited or otherwise non-`COMPLETED` stored summaries raise a typed export error that maps to HTTP `409`. Missing records continue to use `CompletedDatasetRunNotFoundError` from the repository and map to HTTP `404`.

#### 3. Package exports

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/__init__.py`

**Intent**: Expose only the export types/helpers needed by tests or routers, following the package's existing public-boundary pattern.

**Contract**: Keep public exports minimal; do not expose internal sorting helpers unless tests need them through the service behavior.

#### 4. Backend export unit tests

**File**: `tests/backtest_dataset/test_export.py`

**Intent**: Lock the deterministic JSONL contract before wiring HTTP. Tests should prove full-record export behavior independent of preview size and repository insertion order.

**Contract**: Cover stable sort by timestamp, record ID, source identity, and headline; stable repeated bytes; UTF-8 body; exactly one newline per record; no blank lines; canonical field preservation including `run_id`, `config_version`, directional bias, confidence, relevance, source identity, and no metadata line.

### Success Criteria:

#### Automated Verification:

- Backend export unit tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_export.py`
- Existing serialization contract tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/contracts/test_serialization.py`
- Export output from the same stored records is byte-identical across repeated service calls.

#### Manual Verification:

- Confirm the export service does not write `.jsonl` files or temporary durable export artifacts into the repo.
- Confirm provider-limited stored summaries are treated as not exportable rather than as empty datasets.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 2: Backend Export API

### Overview

Expose the JSONL export through the existing dataset router as a downloadable GET response. This phase replaces the current "no export endpoint" expectation with positive route coverage and error semantics.

### Changes Required:

#### 1. Dataset router route

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/router.py`

**Intent**: Add `GET /api/workspaces/{workspace_id}/backtests/{run_id}/dataset/export.jsonl` under the current dataset router prefix. The route should be a read-only export of an existing completed dataset.

**Contract**: The route depends on `get_completed_dataset_repository`, calls the export boundary, returns JSONL as a download/stream response, maps missing completed datasets to `404`, and maps non-exportable terminal states to `409`.

#### 2. Response headers and filename

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/router.py`

**Intent**: Make the response usable as a browser/API download while keeping metadata outside the JSONL body.

**Contract**: Set a JSONL/NDJSON media type, `Content-Disposition` attachment filename derived from sanitized `workspace_id` and `run_id`, and stable metadata headers for run/config context where appropriate. Do not include a manifest record in the response body.

#### 3. Router tests

**File**: `tests/backtest_dataset/test_router.py`

**Intent**: Replace the negative export-endpoint test with route-level tests covering success, headers, complete-vs-preview behavior, workspace isolation, and failure semantics.

**Contract**: Cover successful `GET .../dataset/export.jsonl`; `404` for missing or cross-workspace completed datasets; `409` for provider-limited stored runs; no implicit call to provider/dataset generation; response body has deterministic JSONL bytes and includes all stored records even when preview is bounded.

#### 4. CORS/preflight coverage

**File**: `tests/backtest_dataset/test_router.py`

**Intent**: Preserve browser access expectations for the new GET route.

**Contract**: Add or extend a CORS test for the export route with `Access-Control-Request-Method: GET`, aligned with the existing dataset route preflight pattern.

### Success Criteria:

#### Automated Verification:

- Backend router tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_router.py`
- Backend export tests still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_export.py`
- Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest`

#### Manual Verification:

- `curl -i` against a completed dataset export returns an attachment-style JSONL response with expected headers.
- `curl` against a missing run returns `404` and does not generate a dataset run.
- `curl` against a provider-limited run returns `409` and no JSONL body pretending to be valid export data.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Frontend Download Flow

### Overview

Add a testable frontend download action to the existing BACKTEST shell after a dataset completes. The UI should expose the S-03 capability without rendering large JSONL text or changing the dataset generation flow.

### Changes Required:

#### 1. Export URL and download helper

**File**: `frontend/src/features/backtestShell/api.ts`

**Intent**: Centralize construction of the export URL and provide a helper for fetching the JSONL blob through the same API base-url convention as existing shell calls.

**Contract**: Add `buildBacktestDatasetExportUrl(workspaceId, runId)` for `/dataset/export.jsonl` and a download/fetch helper that sends an appropriate `Accept` header, returns a `Blob` or browser-download result, and raises `BacktestShellApiError` through existing error handling on non-OK responses.

#### 2. Browser download utility

**File**: `frontend/src/features/backtestShell/api.ts` or `frontend/src/features/backtestShell/download.ts`

**Intent**: Keep object URL creation, anchor click, and cleanup isolated so React components remain simple and tests can stub browser APIs.

**Contract**: The utility derives a deterministic filename from `workspaceId` and `runId`, creates an object URL for the JSONL blob, triggers a download, and revokes the object URL. It must not render JSONL text into the DOM.

#### 3. Shell page props and state

**File**: `frontend/src/features/backtestShell/BacktestShellPage.tsx`

**Intent**: Inject the download function for tests and add state for export download progress/error without coupling it to dataset generation state.

**Contract**: Extend `BacktestShellPageProps` with an optional export/download function, pass it into the completed dataset panel, and show a compact progress/error state around the download action.

#### 4. Completed dataset action

**File**: `frontend/src/features/backtestShell/BacktestShellPage.tsx`

**Intent**: Show a clear JSONL download button only when `datasetState.status === "completed"`.

**Contract**: The action appears in the completed branch near existing quality/preview content, is absent for idle/running/error/provider-limited states, disables while download is in progress, and uses BACKTEST/directional-bias language without implying executable trading signals.

#### 5. Frontend tests

**File**: `frontend/src/features/backtestShell/*.test.tsx` and/or existing shell tests

**Intent**: Cover URL construction, download helper behavior, and UI visibility/error states.

**Contract**: Tests assert encoded workspace/run URLs, Accept/error handling, button visibility only after completion, injection of the download function, progress disabled state, and error display. Browser object URL/click behavior should be stubbed without requiring a real download prompt.

### Success Criteria:

#### Automated Verification:

- Frontend tests pass: `cd frontend && npm test`
- Frontend build/typecheck passes: `cd frontend && npm run build`
- Existing backend full test suite still passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest`

#### Manual Verification:

- After creating and completing a BACKTEST dataset in the shell, the JSONL download action appears and triggers a file download.
- Provider-limited, running, idle, and error dataset states do not show a misleading export button.
- The page never displays the full JSONL export body as visible text.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Verification and Handoff

### Overview

Run final regression checks and update planning/context documents so S-03 is clear, reviewable, and safely handed off. This phase should not add new runtime behavior unless verification finds a defect.

### Changes Required:

#### 1. Roadmap/status handoff

**File**: `context/foundation/roadmap.md`

**Intent**: Mark or annotate S-03 JSONL export according to the roadmap's existing status style after implementation completes.

**Contract**: State that JSONL export is implemented, CSV remains deferred, and exports are generated as HTTP downloads from completed datasets without durable local export storage.

#### 2. Quality contract cross-check

**File**: `context/foundation/quality-contracts.md`

**Intent**: Update only if implementation introduces a concrete named endpoint or verification note that belongs in the canonical contract.

**Contract**: Preserve the existing JSONL determinism rules; do not weaken them or add implementation-specific details that should stay in the plan.

#### 3. Plan progress and handoff notes

**File**: `context/changes/jsonl-export/plan.md`

**Intent**: Keep progress checkboxes accurate as implementation phases land and include commit SHAs when available.

**Contract**: Do not rename progress items. Append `— <commit sha>` to completed items after commits land.

#### 4. Generated artifact audit

**File**: repository root and `context/changes/jsonl-export/`

**Intent**: Verify no real or generated workspace JSONL exports were committed as fixtures/artifacts.

**Contract**: `git status --short` should show only intended source, test, and context edits. Any manual export file used for inspection must remain outside the repo or be deleted before final handoff.

### Success Criteria:

#### Automated Verification:

- Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest`
- Frontend tests pass: `cd frontend && npm test`
- Frontend build/typecheck passes: `cd frontend && npm run build`
- Repository audit shows no generated `.jsonl` export artifacts staged or committed: `git status --short`

#### Manual Verification:

- Manual browser or curl smoke confirms the downloaded file body is valid JSONL with one dataset record per line.
- Manual review confirms no UI copy presents directional bias as an executable trading signal.
- Manual review confirms S-03 scope does not include CSV, durable export storage, or implicit generation.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for final human confirmation that S-03 is ready to commit/archive according to the normal workflow.

---

## Testing Strategy

### Unit Tests:

- Export service emits deterministic JSONL from complete stored records.
- Export sorting is stable across repository insertion order changes.
- Export body is UTF-8 compatible, newline terminated, has no blank lines, and contains no metadata/manifest line.
- Provider-limited stored summaries raise a typed not-exportable error.
- Frontend URL builder encodes workspace and run IDs correctly.
- Frontend download helper maps non-OK responses to `BacktestShellApiError`.

### Integration Tests:

- Backend `GET .../dataset/export.jsonl` returns all stored records, not the bounded preview.
- Missing and cross-workspace export requests return `404`.
- Provider-limited export requests return `409`.
- Export requests do not call the news provider or run dataset orchestration implicitly.
- Frontend completed dataset panel exposes the JSONL download action and invokes the injected download helper.

### Manual Testing Steps:

1. Start the local API and frontend using the existing development commands.
2. Create a BACKTEST draft run in the shell.
3. Run deterministic dataset generation.
4. Click the JSONL download action and inspect the downloaded file with a local JSONL parser or line-by-line check.
5. Request the same export twice and confirm the file bytes match.
6. Try a missing run and a provider-limited run path and confirm no valid JSONL file is produced.

## Performance Considerations

The current repository is in-memory and S-03 can generate bytes from stored records directly. Keep the export boundary stream-friendly so a later durable storage implementation can yield lines without changing the route contract. Do not add frontend JSONL preview rendering; large exports should remain downloads.

## Migration Notes

No database migration is required. Existing completed runs in the local/dev in-memory repository become exportable only if their stored summary status is `COMPLETED`. Provider-limited terminal summaries remain visible through preview/status APIs but are not valid JSONL exports.

## References

- Roadmap S-03: `context/foundation/roadmap.md`
- JSONL quality contract: `context/foundation/quality-contracts.md`
- Stable serialization helper: `src/quantitative_sentiment_analysis/contracts/serialization.py:35`
- Dataset JSONL line helper: `src/quantitative_sentiment_analysis/contracts/serialization.py:45`
- Completed records repository method: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:40`
- Dataset preview route: `src/quantitative_sentiment_analysis/backtest_dataset/router.py:85`
- Current negative export test: `tests/backtest_dataset/test_router.py:222`
- Frontend API URL pattern: `frontend/src/features/backtestShell/api.ts:51`
- Frontend completed dataset branch: `frontend/src/features/backtestShell/BacktestShellPage.tsx:316`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append `— <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Backend Export Contract

#### Automated

- [x] 1.1 Backend export unit tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_export.py` — b21e565
- [x] 1.2 Existing serialization contract tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/contracts/test_serialization.py` — b21e565
- [x] 1.3 Export output from the same stored records is byte-identical across repeated service calls. — b21e565

#### Manual

- [x] 1.4 Confirm the export service does not write `.jsonl` files or temporary durable export artifacts into the repo. — b21e565
- [x] 1.5 Confirm provider-limited stored summaries are treated as not exportable rather than as empty datasets. — b21e565

### Phase 2: Backend Export API

#### Automated

- [x] 2.1 Backend router tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_router.py` — ba990ff
- [x] 2.2 Backend export tests still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_export.py` — ba990ff
- [x] 2.3 Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest` — ba990ff

#### Manual

- [x] 2.4 `curl -i` against a completed dataset export returns an attachment-style JSONL response with expected headers. — ba990ff
- [x] 2.5 `curl` against a missing run returns `404` and does not generate a dataset run. — ba990ff
- [x] 2.6 `curl` against a provider-limited run returns `409` and no JSONL body pretending to be valid export data. — ba990ff

### Phase 3: Frontend Download Flow

#### Automated

- [x] 3.1 Frontend tests pass: `cd frontend && npm test`
- [x] 3.2 Frontend build/typecheck passes: `cd frontend && npm run build`
- [x] 3.3 Existing backend full test suite still passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest`

#### Manual

- [x] 3.4 After creating and completing a BACKTEST dataset in the shell, the JSONL download action appears and triggers a file download.
- [x] 3.5 Provider-limited, running, idle, and error dataset states do not show a misleading export button.
- [x] 3.6 The page never displays the full JSONL export body as visible text.

### Phase 4: Verification and Handoff

#### Automated

- [ ] 4.1 Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest`
- [ ] 4.2 Frontend tests pass: `cd frontend && npm test`
- [ ] 4.3 Frontend build/typecheck passes: `cd frontend && npm run build`
- [ ] 4.4 Repository audit shows no generated `.jsonl` export artifacts staged or committed: `git status --short`

#### Manual

- [ ] 4.5 Manual browser or curl smoke confirms the downloaded file body is valid JSONL with one dataset record per line.
- [ ] 4.6 Manual review confirms no UI copy presents directional bias as an executable trading signal.
- [ ] 4.7 Manual review confirms S-03 scope does not include CSV, durable export storage, or implicit generation.
