# Workspace BACKTEST Shell Implementation Plan

## Overview

Implement S-01: a workspace-scoped BTCUSD BACKTEST shell where a trader can enter a workspace, keep instrument and mode explicit, choose a valid timeframe, and create a draft BACKTEST run shell. This gives S-02 a stable run/timeframe contract while deliberately avoiding real auth, persistent storage, news ingestion, sentiment scoring execution, and export.

## Current State Analysis

The backend currently exposes `/`, `/health`, and the S-04 quality route under `/api/workspaces/{workspace_id}/backtests/{run_id}/quality`. Shared F-01 contracts already define workspace/run identity, `BTCUSD`, `BACKTEST`, timezone-aware run metadata, stable serialization, and semantic-safety wording. F-02 now defines the 30-day default range, scoring policy, and S-02 handoff.

The frontend is a Vite/React app with one route parser in `frontend/src/App.tsx`, currently limited to the S-04 quality path. It has tested API-client and page patterns under `frontend/src/features/backtestQuality/`, but no shell route, draft run API client, or operational form.

## Desired End State

After this plan is implemented, the app has a local/dev workspace identity shell and a draft BACKTEST run contract. A user can open `/workspaces/:workspaceId/backtests/new`, see BTCUSD and BACKTEST locked, use a default last-30-days timeframe, submit a draft run, and see the resulting run metadata/status. The API can create and fetch draft runs from an explicitly non-production in-memory repository.

Existing S-04 quality report routing continues to work. The UI can show a quality-route link for the created run, but it must clearly frame it as unavailable until S-02 produces a completed deterministic dataset. No product-facing copy may imply LIVE mode, broker integration, order execution, investment recommendations, or executable trading signals.

### Key Discoveries:

- The existing FastAPI app includes routers through `create_app()` in `src/quantitative_sentiment_analysis/main.py`.
- The existing S-04 route already uses the target workspace-scoped URL shape in `src/quantitative_sentiment_analysis/backtest_quality/router.py`.
- F-01 run metadata requires `workspace_id`, `run_id`, `BTCUSD`, `BACKTEST`, `timeframe_start`, `timeframe_end`, `seed`, `model_version`, `config_version`, and `input_fingerprint` in `src/quantitative_sentiment_analysis/contracts/schemas.py`.
- The frontend route parser currently only recognizes `/workspaces/:workspaceId/backtests/:runId/quality` in `frontend/src/App.tsx`.
- F-02 policy sets the default historical range to 30 days and keeps S-02 responsible for real ingestion in `context/foundation/news-sentiment-policy.md`.

## What We're NOT Doing

- No real auth provider, sessions, roles, JWT verification, or auth middleware.
- No database, migrations, or production run storage.
- No S-02 news ingestion or CryptoPanic API calls.
- No sentiment scoring execution as part of submit.
- No JSONL/CSV export.
- No price enrichment or quality metric computation in the shell.
- No LIVE mode, broker integration, order execution, or investment-recommendation wording.
- No removal or regression of the existing S-04 quality route.

## Implementation Approach

Add a focused backend package, `src/quantitative_sentiment_analysis/backtest_shell/`, parallel to `backtest_quality`. It should own draft run schemas, validation, and the in-memory repository boundary. Then add a workspace-scoped router and wire it into `create_app()`.

On the frontend, extend routing rather than replacing the existing quality view. Add a `backtestShell` feature folder with types, API client, and a single-screen shell page. Tests should mirror the existing S-04 frontend testing style.

## Critical Implementation Details

### In-Memory Repository Is Non-Production

The repository exists only to make S-01 testable and to hand S-02 a contract. It must be named and messaged as local/dev or in-memory storage, and it must not be described as durable completed-run storage.

### Default Dates Must Be Testable

The UI may default to the last 30 days, but tests should inject or derive a fixed reference timestamp so snapshots and assertions do not depend on the current wall clock.

## Phase 1: Backend Run-Shell Contract

### Overview

Define the draft BACKTEST run schema, status model, timeframe validation, and local in-memory repository contract.

### Changes Required:

#### 1. Backtest shell package

**File**: `src/quantitative_sentiment_analysis/backtest_shell/__init__.py`

**Intent**: Provide stable exports for draft run contracts and repository helpers without coupling shell work to S-04 quality modules.

**Contract**: Re-export schemas, repository provider helpers, and typed errors. The package must not import frontend code, `backtest_quality`, or provider-specific ingestion modules.

#### 2. Draft run schemas

**File**: `src/quantitative_sentiment_analysis/backtest_shell/schemas.py`

**Intent**: Define the request/response contract for S-01 draft BACKTEST runs.

**Contract**: Models must include:

- `BacktestRunStatus` enum with at least `DRAFT` and `READY_FOR_DATASET`.
- `CreateBacktestRunRequest` with timezone-aware `timeframe_start` and `timeframe_end`.
- `BacktestRunShell` response with `workspace_id`, `run_id`, `instrument`, `mode`, `timeframe_start`, `timeframe_end`, `status`, `created_at`, and optional `quality_report_path`.
- Validation that mode is `BACKTEST`, instrument is `BTCUSD`, timestamps are aware, `timeframe_end >= timeframe_start`, and the range is no more than 30 days.

#### 3. Repository and run-id contract

**File**: `src/quantitative_sentiment_analysis/backtest_shell/repository.py`

**Intent**: Store draft run shells in process memory for local/test use and make the non-production boundary explicit.

**Contract**: Provide a provider dependency equivalent to `get_backtest_shell_repository()`, an in-memory repository implementation, and typed not-found/unsupported errors. Run IDs must be stable enough for tests and safe in URLs. Repository reads must always use both `workspace_id` and `run_id`.

### Success Criteria:

#### Automated Verification:

- Shell package imports cleanly: `uv run python -c "import quantitative_sentiment_analysis.backtest_shell"`
- Schema tests pass: `uv run pytest tests/backtest_shell/test_schemas.py`
- Repository tests pass: `uv run pytest tests/backtest_shell/test_repository.py`

#### Manual Verification:

- Schemas use `BTCUSD`, `BACKTEST`, and workspace/run identity consistently with F-01.
- Repository naming and errors make clear that this is not production storage.
- No auth, ingestion, scoring, export, broker, order, or LIVE scope is introduced.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Backend API Routes

### Overview

Expose workspace-scoped API routes to create and fetch draft BACKTEST run shells.

### Changes Required:

#### 1. Backtest shell router

**File**: `src/quantitative_sentiment_analysis/backtest_shell/router.py`

**Intent**: Provide the backend API boundary for S-01 without starting S-02 processing.

**Contract**: Add routes under `/api/workspaces/{workspace_id}/backtests`:

- `POST /drafts` accepts `CreateBacktestRunRequest` and returns `BacktestRunShell`.
- `GET /{run_id}` returns an existing draft run shell for that workspace.

The create route must use the path `workspace_id` as the authoritative workspace boundary. It must reject invalid timeframes with FastAPI/Pydantic validation errors and return explicit 404/409-style errors for missing or unsupported runs. It must not start ingestion or scoring.

#### 2. App router wiring

**File**: `src/quantitative_sentiment_analysis/main.py`

**Intent**: Include the shell router while preserving `/`, `/health`, CORS behavior, and the existing quality router.

**Contract**: `create_app()` includes the new router. CORS currently allows only `GET`; update allowed methods so the local frontend can `POST` draft runs without opening wildcard origins.

#### 3. Router tests

**File**: `tests/backtest_shell/test_router.py`

**Intent**: Verify route contracts, workspace boundaries, validation errors, and CORS behavior.

**Contract**: Tests must cover successful draft creation, `GET` by workspace/run, missing run, cross-workspace miss, invalid timeframe, range over 30 days, timezone-naive input, no S-02 side effects, and CORS preflight for `POST`.

### Success Criteria:

#### Automated Verification:

- Router tests pass: `uv run pytest tests/backtest_shell/test_router.py`
- Existing backend tests still pass: `uv run pytest tests/test_main.py tests/contracts tests/backtest_quality tests/sentiment_policy tests/backtest_shell`
- FastAPI app imports with the new router: `uv run python -c "from quantitative_sentiment_analysis.main import app; print(app.title)"`

#### Manual Verification:

- API responses use BACKTEST-only analytical wording.
- Existing quality route `/api/workspaces/{workspace_id}/backtests/{run_id}/quality` still works with its fixture provider path.
- CORS still rejects wildcard origins and unconfigured origins.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Frontend Route and API Client

### Overview

Extend the Vite app so the new shell route and existing S-04 quality route coexist.

### Changes Required:

#### 1. App routing

**File**: `frontend/src/App.tsx`

**Intent**: Parse the new shell route without regressing the quality route.

**Contract**: Support `/workspaces/:workspaceId/backtests/new` for the shell and keep `/workspaces/:workspaceId/backtests/:runId/quality` for S-04. Malformed encoded route segments must still return an error/unknown route state instead of throwing.

#### 2. Route tests

**File**: `frontend/src/App.test.ts`

**Intent**: Verify both route shapes and malformed encoding behavior.

**Contract**: Tests must cover parsing shell route, parsing quality route, route priority so `new` does not get treated as a run ID, and malformed encoded segments.

#### 3. Shell frontend types

**File**: `frontend/src/features/backtestShell/types.ts`

**Intent**: Mirror the backend draft run request/response contract in TypeScript.

**Contract**: Types include `BacktestRunStatus`, create request, run shell response, `BTCUSD`, `BACKTEST`, ISO datetime strings, and quality path.

#### 4. Shell API client

**File**: `frontend/src/features/backtestShell/api.ts`

**Intent**: Create and fetch draft run shells through the backend API.

**Contract**: Follow the existing S-04 API client pattern: use `VITE_API_BASE_URL` when set, fall back to relative `/api`, encode workspace/run IDs, send JSON for `POST`, parse typed errors, and avoid metric/scoring logic.

#### 5. Shell API tests

**File**: `frontend/src/features/backtestShell/api.test.ts`

**Intent**: Verify URL construction, POST behavior, error handling, and base URL behavior.

**Contract**: Tests must cover `VITE_API_BASE_URL`, relative fallback, encoded workspace IDs, JSON body, non-2xx typed errors, and no use of quality-report endpoints for draft creation.

### Success Criteria:

#### Automated Verification:

- Frontend route/API tests pass: `cd frontend && npm test -- --run App.test.ts src/features/backtestShell/api.test.ts`
- Frontend typecheck/build passes: `cd frontend && npm run build`
- Existing quality frontend tests still pass: `cd frontend && npm test -- --run src/features/backtestQuality`

#### Manual Verification:

- Existing quality route still renders for a run-scoped quality path.
- Unknown routes still show a clear route guidance state.
- No frontend copy implies that creating a draft run starts analysis.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Operational Shell UI

### Overview

Build the single-screen shell UI for creating draft BTCUSD BACKTEST runs.

### Changes Required:

#### 1. Shell page

**File**: `frontend/src/features/backtestShell/BacktestShellPage.tsx`

**Intent**: Render the operational shell where the trader selects/enters workspace context, confirms BTCUSD BACKTEST mode, chooses timeframe, and creates a draft run.

**Contract**: The page must:

- show workspace identity from the route;
- show locked `BTCUSD` instrument and `BACKTEST` mode;
- default to a last-30-days timeframe;
- allow editing timezone-aware ISO datetime inputs;
- submit to the shell API client;
- show loading, success, validation/API error, and created run metadata states;
- show a quality-route link for the draft run, clearly marked as not ready until S-02 produces a completed dataset;
- avoid banned trading/advice wording.

#### 2. Shell page tests

**File**: `frontend/src/features/backtestShell/BacktestShellPage.test.tsx`

**Intent**: Verify the user workflow and semantic-safety boundaries.

**Contract**: Tests must cover default 30-day values with an injected fixed reference timestamp, successful submit, displayed draft run metadata, API error state, validation/range feedback where implemented client-side, and absence of forbidden product-facing wording.

#### 3. App integration

**File**: `frontend/src/App.tsx`

**Intent**: Render the shell page for the new route.

**Contract**: The shell route renders `BacktestShellPage` with the decoded workspace ID. The quality route still renders `BacktestQualityPage` with workspace/run IDs.

#### 4. Shared styles

**File**: `frontend/src/styles.css`

**Intent**: Add operational shell styling consistent with the existing quiet dashboard aesthetic.

**Contract**: Keep UI dense, readable, and tool-like. Do not add marketing hero sections, decorative cards inside cards, or copy explaining implementation details. Preserve mobile layout and avoid text overflow.

### Success Criteria:

#### Automated Verification:

- Shell page tests pass: `cd frontend && npm test -- --run src/features/backtestShell/BacktestShellPage.test.tsx`
- Full frontend test suite passes: `cd frontend && npm test -- --run`
- Frontend build passes: `cd frontend && npm run build`

#### Manual Verification:

- Opening `/workspaces/workspace-alpha/backtests/new` shows the operational shell.
- Creating a draft run shows run ID, workspace, BTCUSD, BACKTEST, timeframe, and draft/ready status.
- UI text is BACKTEST-only analytical workflow copy and does not imply live trading, broker integration, order execution, or investment advice.
- Existing `/workspaces/workspace-alpha/backtests/run-001/quality` route still works.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 5: Verification and Handoff

### Overview

Complete cross-layer verification and update planning artifacts so S-02 can start from the new shell contract.

### Changes Required:

#### 1. Roadmap handoff

**File**: `context/foundation/roadmap.md`

**Intent**: Reflect that S-01 has an implementation-ready plan and, after implementation, can unblock S-02 together with F-02.

**Contract**: Update only S-01/S-02 handoff language needed by this change. Do not mark S-02 complete or remove its provider smoke-test risk.

#### 2. Quality contract handoff

**File**: `context/foundation/quality-contracts.md`

**Intent**: Add a concise note that S-01 supplies the draft workspace/run/timeframe shell for S-02.

**Contract**: Keep F-01 contracts canonical; do not duplicate the entire shell API schema.

#### 3. Plan brief and change metadata

**File**: `context/changes/workspace-backtest-shell/plan-brief.md`

**Intent**: Keep the brief aligned with implementation reality if scope changes during implementation.

**Contract**: Update phase summary, decisions, and risks if needed.

**File**: `context/changes/workspace-backtest-shell/change.md`

**Intent**: Keep change metadata aligned with implementation status.

**Contract**: At implementation closeout, update status and date consistently with repository convention.

### Success Criteria:

#### Automated Verification:

- Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/test_main.py tests/contracts tests/backtest_quality tests/sentiment_policy tests/backtest_shell`
- Full frontend test suite passes: `cd frontend && npm test -- --run`
- Frontend build passes: `cd frontend && npm run build`
- Foundation docs reference S-01 handoff: `rg -n "workspace-backtest-shell|S-01|draft" context/foundation/roadmap.md context/foundation/quality-contracts.md`

#### Manual Verification:

- S-02 can use the new draft run shell contract without re-deciding workspace, mode, instrument, or timeframe semantics.
- The final handoff names the next sensible command as `/10x-plan deterministic-news-dataset`.
- No generated real workspace data or unsanitized news exports are committed.
- Working tree is clean after commits and epilogue.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- Pydantic schema validation for aware timestamps, max 30-day range, ordered timeframe, `BTCUSD`, `BACKTEST`, and status values.
- Repository tests for workspace/run isolation, not found behavior, deterministic testable run IDs, and non-production messaging.
- Frontend route parser and API client tests for both shell and quality routes.

### Integration Tests:

- FastAPI router tests for create/get draft run, CORS `POST`, invalid payloads, and cross-workspace misses.
- Frontend page tests for default 30-day timeframe, submit flow, success/error states, and semantic-safety copy.
- Existing S-04 backend and frontend tests must remain green.

### Manual Testing Steps:

1. Start backend locally and verify `/health`.
2. Start the frontend locally.
3. Open `/workspaces/workspace-alpha/backtests/new`.
4. Create a draft run and verify workspace, `BTCUSD`, `BACKTEST`, status, and timeframe.
5. Confirm the quality route link is present but framed as unavailable until S-02 data exists.
6. Open the existing quality route and confirm it still renders.
7. Check visible copy for banned live/execution/advice wording.

## Performance Considerations

S-01 stores only small draft run shells and does not process news. Its main performance constraint is preventing accidental large BACKTEST ranges that would later break S-02 runtime expectations. The max 30-day validation is therefore part of the shell contract.

## Migration Notes

No database migration is planned. The in-memory repository is a deliberate MVP/test boundary and must be replaced or adapted by a later storage slice before durable production runs are required.

## References

- S-01 roadmap item: `context/foundation/roadmap.md`
- PRD access/setup requirements: `context/foundation/prd.md`
- F-01 quality contracts: `context/foundation/quality-contracts.md`
- F-02 policy default range: `context/foundation/news-sentiment-policy.md`
- Current FastAPI app: `src/quantitative_sentiment_analysis/main.py`
- Shared run contracts: `src/quantitative_sentiment_analysis/contracts/schemas.py`
- Existing S-04 router pattern: `src/quantitative_sentiment_analysis/backtest_quality/router.py`
- Existing frontend route parser: `frontend/src/App.tsx`
- Existing frontend API client pattern: `frontend/src/features/backtestQuality/api.ts`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Backend Run-Shell Contract

#### Automated

- [x] 1.1 Shell package imports cleanly: `uv run python -c "import quantitative_sentiment_analysis.backtest_shell"` — 1651f72
- [x] 1.2 Schema tests pass: `uv run pytest tests/backtest_shell/test_schemas.py` — 1651f72
- [x] 1.3 Repository tests pass: `uv run pytest tests/backtest_shell/test_repository.py` — 1651f72

#### Manual

- [x] 1.4 Schemas use `BTCUSD`, `BACKTEST`, and workspace/run identity consistently with F-01. — 1651f72
- [x] 1.5 Repository naming and errors make clear that this is not production storage. — 1651f72
- [x] 1.6 No auth, ingestion, scoring, export, broker, order, or LIVE scope is introduced. — 1651f72

### Phase 2: Backend API Routes

#### Automated

- [x] 2.1 Router tests pass: `uv run pytest tests/backtest_shell/test_router.py` — a67bf62
- [x] 2.2 Existing backend tests still pass: `uv run pytest tests/test_main.py tests/contracts tests/backtest_quality tests/sentiment_policy tests/backtest_shell` — a67bf62
- [x] 2.3 FastAPI app imports with the new router: `uv run python -c "from quantitative_sentiment_analysis.main import app; print(app.title)"` — a67bf62

#### Manual

- [x] 2.4 API responses use BACKTEST-only analytical wording. — a67bf62
- [x] 2.5 Existing quality route `/api/workspaces/{workspace_id}/backtests/{run_id}/quality` still works with its fixture provider path. — a67bf62
- [x] 2.6 CORS still rejects wildcard origins and unconfigured origins. — a67bf62

### Phase 3: Frontend Route and API Client

#### Automated

- [x] 3.1 Frontend route/API tests pass: `cd frontend && npm test -- --run App.test.ts src/features/backtestShell/api.test.ts`
- [x] 3.2 Frontend typecheck/build passes: `cd frontend && npm run build`
- [x] 3.3 Existing quality frontend tests still pass: `cd frontend && npm test -- --run src/features/backtestQuality`

#### Manual

- [x] 3.4 Existing quality route still renders for a run-scoped quality path.
- [x] 3.5 Unknown routes still show a clear route guidance state.
- [x] 3.6 No frontend copy implies that creating a draft run starts analysis.

### Phase 4: Operational Shell UI

#### Automated

- [ ] 4.1 Shell page tests pass: `cd frontend && npm test -- --run src/features/backtestShell/BacktestShellPage.test.tsx`
- [ ] 4.2 Full frontend test suite passes: `cd frontend && npm test -- --run`
- [ ] 4.3 Frontend build passes: `cd frontend && npm run build`

#### Manual

- [ ] 4.4 Opening `/workspaces/workspace-alpha/backtests/new` shows the operational shell.
- [ ] 4.5 Creating a draft run shows run ID, workspace, BTCUSD, BACKTEST, timeframe, and draft/ready status.
- [ ] 4.6 UI text is BACKTEST-only analytical workflow copy and does not imply live trading, broker integration, order execution, or investment advice.
- [ ] 4.7 Existing `/workspaces/workspace-alpha/backtests/run-001/quality` route still works.

### Phase 5: Verification and Handoff

#### Automated

- [ ] 5.1 Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/test_main.py tests/contracts tests/backtest_quality tests/sentiment_policy tests/backtest_shell`
- [ ] 5.2 Full frontend test suite passes: `cd frontend && npm test -- --run`
- [ ] 5.3 Frontend build passes: `cd frontend && npm run build`
- [ ] 5.4 Foundation docs reference S-01 handoff: `rg -n "workspace-backtest-shell|S-01|draft" context/foundation/roadmap.md context/foundation/quality-contracts.md`

#### Manual

- [ ] 5.5 S-02 can use the new draft run shell contract without re-deciding workspace, mode, instrument, or timeframe semantics.
- [ ] 5.6 The final handoff names the next sensible command as `/10x-plan deterministic-news-dataset`.
- [ ] 5.7 No generated real workspace data or unsanitized news exports are committed.
- [ ] 5.8 Working tree is clean after commits and epilogue.
