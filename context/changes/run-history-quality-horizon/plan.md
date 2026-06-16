# Run History and Quality Horizon Implementation Plan

## Overview

Add a durable workspace run-history discovery surface and make the backtest-quality
horizon an explicit, configurable report parameter. This closes the post-login
recovery gap for completed BACKTEST work while keeping quality metrics honest
when later BTCUSD movement values are still missing.

## Current State Analysis

The application now persists users, workspaces, saved configs, draft runs,
dataset summaries, and dataset records in Postgres. `backtest_runs` and
`dataset_runs` already contain the data needed for a run-history read model, but
the API only exposes exact-run routes and the frontend has no route or nav item
for run history.

Quality reports already carry a `QualityHorizon` response field and
`build_quality_report()` can accept an explicit horizon, but the route always
uses the hidden default and the frontend client cannot pass a chosen horizon.
Completed real datasets still map `later_return` and `realized_direction` to
`None`, so configurable horizon must not imply that price movement enrichment
exists.

## Desired End State

A logged-in user can land on `/workspaces/:workspaceId/backtests`, see historical
BACKTEST runs from the workspace after logout/login, distinguish draft,
completed, and provider-limited dataset states, and use run-specific actions to
run a dataset, open quality, or download JSONL when available.

A user can open a quality report with a default 4 hour horizon or choose a
supported horizon such as 1 minute. The chosen horizon is visible in the URL,
sent to the backend, echoed by the report, and tested. Missing movement remains
explicitly warned and is not fabricated.

### Key Discoveries:

- `BacktestRunModel` already stores workspace-owned run metadata and relates to
  a single dataset run (`src/quantitative_sentiment_analysis/persistence/models.py:186`,
  `src/quantitative_sentiment_analysis/persistence/models.py:241`).
- `DatasetRunModel` already stores terminal dataset status, provider metadata,
  relevance counts, model/config versions, and input fingerprint
  (`src/quantitative_sentiment_analysis/persistence/models.py:248`).
- The shell router has create/exact-read routes but no list route
  (`src/quantitative_sentiment_analysis/backtest_shell/router.py:26`,
  `src/quantitative_sentiment_analysis/backtest_shell/router.py:42`).
- Authenticated frontend navigation exposes only saved configs and new BACKTEST
  (`frontend/src/App.tsx:283`, `frontend/src/App.tsx:286`).
- `BacktestConfigPage` and `BacktestShellPage` store run/dataset results in
  transient component state (`frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:71`,
  `frontend/src/features/backtestShell/BacktestShellPage.tsx:34`).
- `QualityHorizon` defaults to 4 hours and `build_quality_report()` already
  accepts a horizon argument (`src/quantitative_sentiment_analysis/backtest_quality/schemas.py:34`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:28`).
- The completed-dataset quality adapter still sets movement fields to missing
  (`src/quantitative_sentiment_analysis/backtest_quality/repository.py:124`,
  `src/quantitative_sentiment_analysis/backtest_quality/repository.py:125`).

## What We're NOT Doing

- No price/candle provider integration in this change.
- No fabricated `later_return` or `realized_direction` values.
- No schema migration unless implementation discovers an unavoidable missing
  index; current tables already contain the required read-model inputs.
- No live streaming, broker integration, order execution, or investment
  recommendation wording.
- No broad redesign of saved configuration CRUD.
- No advanced quality dashboard beyond the existing report with an explicit
  horizon selector.

## Implementation Approach

Build run history as a workspace-scoped read model over existing Postgres tables:
`backtest_runs` left joined to `backtest_configs` and `dataset_runs`. Expose that
read model through a new `GET /api/workspaces/{workspace_id}/backtests` route
with action paths rather than making the frontend infer availability from raw
database fields.

Add a frontend run-history feature package and route at
`/workspaces/:workspaceId/backtests`. Make it the default authenticated landing
path so a returning user immediately sees previously created runs, while keeping
"Saved configs" and "New BACKTEST" in navigation.

Keep quality horizon in the quality boundary. Add explicit query parameters
`horizon_value` and `horizon_unit`, validate them against a small supported
preset set, pass a `QualityHorizon` into `build_quality_report()`, and mirror the
same options in the frontend selector.

## Critical Implementation Details

### History Is a Workspace Read Model

The run-history query must resolve the workspace slug to the owned workspace and
filter every row by that workspace UUID. The list must never accept or expose a
run based on `run_id` alone, because workspace/run isolation is a top test-plan
risk.

### Horizon Does Not Enrich Prices

Changing the horizon changes the requested quality evaluation window metadata.
Until price enrichment exists, real completed datasets still produce missing
movement warnings and empty or flat-looking return plots. UI copy must keep this
boundary visible and must not present horizon selection as a fix for missing
movement data.

### Supported Horizon Presets

Use a controlled V1 preset list: `1 minute`, `15 minutes`, `1 hour`, `4 hours`,
and `24 hours`. Keep `4 hours` as the default for backwards compatibility with
the foundation policy.

## Phase 1: Backend Run History Contract

### Overview

Add the workspace-scoped backend read model and API route that can recover
historical BACKTEST runs from durable Postgres state.

### Changes Required:

#### 1. Run history schemas

**File**: `src/quantitative_sentiment_analysis/backtest_shell/schemas.py`

**Intent**: Define the response contract for a workspace run-history list without
weakening the existing exact-run shell contract.

**Contract**: Add immutable Pydantic schemas for a history item and response.
Each item should include run metadata (`workspace_id`, `run_id`, `config_id`,
`config_name`, instrument, mode, timeframe, run status, created time), nullable
dataset summary metadata (`dataset_status`, provider, record/relevance counts,
model/config versions, fingerprint, provider limitation), and nullable action
paths (`dataset_preview_path`, `dataset_export_path`, `quality_report_path`).

#### 2. Repository list method

**File**: `src/quantitative_sentiment_analysis/backtest_shell/repository.py`

**Intent**: Let shell storage return workspace run history using the same
workspace boundary as exact-run reads.

**Contract**: Extend `BacktestShellRepository` with `list_runs(workspace_id:
str)`. The Postgres implementation must resolve `WorkspaceModel.slug`, filter
`BacktestRunModel.workspace_id`, left join `BacktestConfigModel` and
`DatasetRunModel`, order newest first by `BacktestRunModel.created_at` then
`run_id`, and return schema objects with URL-safe action paths. The in-memory
implementation can return draft-only items for tests/local compatibility.

#### 3. API route

**File**: `src/quantitative_sentiment_analysis/backtest_shell/router.py`

**Intent**: Expose the history list as a first-class workspace API.

**Contract**: Add `GET /api/workspaces/{workspace_id}/backtests` with
`response_model=BacktestRunHistoryResponse`. It must use
`require_owned_workspace`, map missing workspace behavior consistently with
existing shell reads, and not call dataset generation, quality, or export logic.

#### 4. Backend tests

**File**: `tests/backtest_shell/test_postgres_repository.py`

**Intent**: Verify the Postgres read model across draft, completed, and
provider-limited runs.

**Contract**: Cover newest-first ordering, config name inclusion, completed
dataset summary fields, provider limitation fields, action paths, and
cross-workspace non-leakage.

**File**: `tests/backtest_shell/test_router.py`

**Intent**: Verify the authenticated API route contract.

**Contract**: Cover successful authenticated list, empty list, 401/404 behavior
consistent with existing workspace ownership tests, and prove no exact-run access
is possible with `run_id` alone.

### Success Criteria:

#### Automated Verification:

- Backend run-history repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pytest tests/backtest_shell/test_postgres_repository.py -p no:cacheprovider`
- Backend run-history router tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pytest tests/backtest_shell/test_router.py -p no:cacheprovider`
- Backend lint/type checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pyright`

#### Manual Verification:

- With two runs in `demo-workspace`, `GET /api/workspaces/demo-workspace/backtests` returns both after logout/login and never includes another workspace's runs.

**Implementation Note**: After completing this phase and automated verification,
pause for manual confirmation that the backend list contract returns the expected
production-like data before building the frontend around it.

---

## Phase 2: Frontend Run History and Re-Entry

### Overview

Add the user-visible run-history route, make it discoverable after login, and
allow users to re-enter historical run actions without relying on transient
component state.

### Changes Required:

#### 1. Run history API client and types

**File**: `frontend/src/features/backtestRuns/types.ts`

**Intent**: Mirror the backend history response in TypeScript.

**Contract**: Define `BacktestRunHistoryItem` and
`BacktestRunHistoryResponse` with the same nullable dataset/action fields as the
backend schema.

**File**: `frontend/src/features/backtestRuns/api.ts`

**Intent**: Fetch workspace run history through the same cookie-authenticated API
client style as the rest of the app.

**Contract**: Add URL builder and `fetchBacktestRunHistory(workspaceId)`.
Respect `VITE_API_BASE_URL`, encode workspace IDs, send `credentials:
"include"`, parse typed errors, and read empty 200 responses as errors.

#### 2. Run history page

**File**: `frontend/src/features/backtestRuns/BacktestRunHistoryPage.tsx`

**Intent**: Render a durable operational list of historical BACKTEST runs.

**Contract**: Load history on mount; show loading, empty, error, draft,
completed, and provider-limited states. For each run, display config name when
available, run ID, timeframe, created time, provider/status/counts, and actions:
run deterministic dataset when no terminal dataset exists, open quality only
when completed, and download JSONL only when completed. After running a dataset
from history, refresh the list from the API instead of relying only on local
mutation.

#### 3. App routing, nav, and default landing

**File**: `frontend/src/App.tsx`

**Intent**: Make run history discoverable after login and navigable from the
authenticated frame.

**Contract**: Add route parsing for `/workspaces/:workspaceId/backtests`, render
`BacktestRunHistoryPage`, add a "Run history" nav link, and change
`defaultWorkspacePath()` to return `/workspaces/:workspaceId/backtests`. Keep
existing saved config, new BACKTEST, and direct quality routes working.

#### 4. Frontend tests

**File**: `frontend/src/features/backtestRuns/api.test.ts`

**Intent**: Verify the new API client contract.

**Contract**: Cover base URL, relative URL, encoding, credentials, successful
history parsing, and typed errors.

**File**: `frontend/src/features/backtestRuns/BacktestRunHistoryPage.test.tsx`

**Intent**: Verify user-visible run recovery and actions.

**Contract**: Cover empty history, completed run quality/export actions,
draft-run dataset action with refresh, provider limitation display, and absence
of forbidden investment-signal wording.

**File**: `frontend/src/App.test.ts`

**Intent**: Keep top-level routing and auth bootstrap correct.

**Contract**: Cover parsing `/workspaces/:workspaceId/backtests`, default login
landing to run history, nav links, and existing config/shell/quality routes.

### Success Criteria:

#### Automated Verification:

- Run-history frontend tests pass: `npm --prefix frontend run test -- src/features/backtestRuns src/App.test.ts`
- Existing shell/config frontend regressions pass: `npm --prefix frontend run test -- src/features/backtestShell src/features/backtestConfigs`
- Frontend build passes: `npm --prefix frontend run build`

#### Manual Verification:

- Log in, create a saved config draft, run a deterministic BACKTEST dataset, log
  out, log back in, and see the run on `/workspaces/demo-workspace/backtests`.
- From run history, open the completed run's quality route and download JSONL.
- A provider-limited run is visible as historical work but does not offer quality
  or JSONL as if it completed.

**Implementation Note**: After completing this phase, pause for manual browser
confirmation that post-login run recovery works on the local app before adding
the horizon selector.

---

## Phase 3: Configurable Quality Horizon

### Overview

Make the quality horizon an explicit, shareable API/UI parameter while retaining
the 4 hour default and preserving missing-movement truthfulness.

### Changes Required:

#### 1. Backend horizon query contract

**File**: `src/quantitative_sentiment_analysis/backtest_quality/schemas.py`

**Intent**: Define the supported V1 horizon presets in the quality domain.

**Contract**: Add a constant or helper that validates only these query pairs:
`(1, minutes)`, `(15, minutes)`, `(1, hours)`, `(4, hours)`, and
`(24, hours)`. Keep `QualityHorizon()` as the default 4 hour value.

**File**: `src/quantitative_sentiment_analysis/backtest_quality/router.py`

**Intent**: Accept the requested horizon and pass it into report generation.

**Contract**: Add query parameters `horizon_value` and `horizon_unit`, defaulting
to `4` and `hours`. Build a `QualityHorizon`, validate it against supported
presets, pass it to `build_quality_report(records, horizon=horizon)`, and map
unsupported presets to a clear 422 validation response.

#### 2. Backend quality tests

**File**: `tests/backtest_quality/test_router.py`

**Intent**: Verify the route contract for default, selected, and invalid
horizons.

**Contract**: Cover default 4 hour response, `?horizon_value=1&horizon_unit=minutes`
response, unsupported horizon rejection, and preserved missing-movement warning
for real completed dataset adapter output.

**File**: `tests/backtest_quality/test_metrics.py`

**Intent**: Keep metric generation deterministic with explicit horizons.

**Contract**: Cover that `build_quality_report(records, horizon=...)` echoes the
provided horizon without changing sorting, sampling, relevance denominator rules,
or missing-movement warnings.

#### 3. Frontend quality API and URL state

**File**: `frontend/src/features/backtestQuality/types.ts`

**Intent**: Add a client-side supported horizon option type aligned to the
backend contract.

**Contract**: Keep `QualityHorizon` and add `SupportedQualityHorizon` or a
constant option list with `1 minute`, `15 minutes`, `1 hour`, `4 hours`, and
`24 hours`.

**File**: `frontend/src/features/backtestQuality/api.ts`

**Intent**: Send the requested horizon to the backend.

**Contract**: Extend `buildBacktestQualityReportUrl()` and
`fetchBacktestQualityReport()` to accept an optional horizon. When provided, add
`horizon_value` and `horizon_unit` query parameters; when omitted, preserve the
current default `/quality` URL.

**File**: `frontend/src/features/backtestQuality/BacktestQualityPage.tsx`

**Intent**: Let the user change the horizon from the report page and keep the URL
shareable.

**Contract**: Initialize selected horizon from query params when valid, otherwise
default to 4 hours. Render a labelled select/segmented control for supported
presets. On change, update the browser URL query and reload the report by waiting
on the loader promise, not on timeouts. Continue displaying warnings and missing
movement states.

#### 4. Frontend quality tests and docs

**File**: `frontend/src/features/backtestQuality/api.test.ts`

**Intent**: Verify URL/query behavior and cookie-authenticated fetches.

**Contract**: Cover default URL compatibility, selected horizon URL, base URL
handling with query params, and fetch called with credentials.

**File**: `frontend/src/features/backtestQuality/BacktestQualityPage.test.tsx`

**Intent**: Verify the selector behavior from the user's perspective.

**Contract**: Cover default 4 hours, changing to 1 minute calls the loader with
the selected horizon, metadata updates after the new report loads, and missing
movement warnings remain visible.

**File**: `context/foundation/news-sentiment-policy.md`

**Intent**: Clarify that 4 hours is the default, not the only allowed report
horizon.

**Contract**: Update the Quality Horizon section to name the supported V1 UI/API
presets and state that price movement enrichment remains a separate prerequisite
for non-missing real movement metrics.

### Success Criteria:

#### Automated Verification:

- Backend quality horizon tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pytest tests/backtest_quality/test_router.py tests/backtest_quality/test_metrics.py -p no:cacheprovider`
- Frontend quality horizon tests pass: `npm --prefix frontend run test -- src/features/backtestQuality`
- Backend and frontend full quality gates pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pyright && npm --prefix frontend run build`

#### Manual Verification:

- Opening `/workspaces/demo-workspace/backtests/<run_id>/quality` shows 4 hours
  by default.
- Changing the selector to 1 minute updates the URL and report metadata to
  `1 minute` without inventing later movement values.
- Missing movement warnings remain visible for real completed runs until price
  enrichment exists.

**Implementation Note**: After this phase, confirm manually that a historical run
can be reopened from run history and evaluated with both the default 4 hour
horizon and the 1 minute horizon.

---

## Testing Strategy

### Unit Tests:

- Pydantic schema tests for run-history item validation and supported horizon
  validation.
- Metrics tests proving explicit horizons are echoed without altering existing
  denominator and warning behavior.

### Integration Tests:

- Postgres repository and FastAPI route tests for run-history list ordering,
  workspace isolation, completed/provider-limited metadata, and auth behavior.
- FastAPI quality route tests for default, selected, and invalid horizons.

### Frontend Component/API Tests:

- API client tests for run-history and horizon query construction.
- Component tests for post-login run history recovery states and quality horizon
  selection.
- App routing tests for `/workspaces/:workspaceId/backtests` and default login
  landing.

### Manual Testing Steps:

1. Log in locally as the seeded user.
2. Create a saved BACKTEST config and create a draft from it.
3. Run the deterministic BACKTEST dataset.
4. Log out and log in again.
5. Confirm `/workspaces/demo-workspace/backtests` lists the historical run.
6. Open quality from history and switch between 4 hours and 1 minute.
7. Confirm missing movement warnings remain visible and no copy frames
   directional bias as an executable signal.

## Performance Considerations

Run history should be bounded. If the implementation adds pagination, default to
a small page such as 50 newest runs. If it ships without pagination, the query
should still order by indexed workspace/run fields and avoid loading dataset
records; list items need only `backtest_runs`, optional config metadata, and one
dataset summary row.

Quality horizon selection re-runs the current quality report calculation over
the same bounded response behavior. It must not fetch full JSONL exports or
dataset record payloads through the frontend.

## Migration Notes

No schema migration is expected. The feature reads existing Postgres tables.
If implementation discovers a missing index for the list query, add a focused
Alembic migration and keep it separate from any data backfill.

Existing historical runs remain valid. Runs without a dataset summary appear as
draft/no-terminal-dataset items; completed and provider-limited summaries are
derived from existing `dataset_runs` rows.

## References

- Frame brief: `context/changes/run-history-quality-horizon/frame.md`
- Related research: `context/changes/run-history-quality-horizon/research.md`
- Postgres/auth persistence plan: `context/changes/postgres-auth-crud-persistence/plan.md`
- Deterministic dataset plan: `context/changes/deterministic-news-dataset/plan.md`
- Quality contracts: `context/foundation/quality-contracts.md`
- Test-plan risks: `context/foundation/test-plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Backend Run History Contract

#### Automated

- [x] 1.1 Backend run-history repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pytest tests/backtest_shell/test_postgres_repository.py -p no:cacheprovider` — adfea41
- [x] 1.2 Backend run-history router tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pytest tests/backtest_shell/test_router.py -p no:cacheprovider` — adfea41
- [x] 1.3 Backend lint/type checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pyright` — adfea41

#### Manual

- [x] 1.4 With two runs in `demo-workspace`, `GET /api/workspaces/demo-workspace/backtests` returns both after logout/login and never includes another workspace's runs. — adfea41

### Phase 2: Frontend Run History and Re-Entry

#### Automated

- [x] 2.1 Run-history frontend tests pass: `npm --prefix frontend run test -- src/features/backtestRuns src/App.test.ts` — ba3e528
- [x] 2.2 Existing shell/config frontend regressions pass: `npm --prefix frontend run test -- src/features/backtestShell src/features/backtestConfigs` — ba3e528
- [x] 2.3 Frontend build passes: `npm --prefix frontend run build` — ba3e528

#### Manual

- [x] 2.4 Log in, create a saved config draft, run a deterministic BACKTEST dataset, log out, log back in, and see the run on `/workspaces/demo-workspace/backtests`. — ba3e528
- [x] 2.5 From run history, open the completed run's quality route and download JSONL. — ba3e528
- [x] 2.6 A provider-limited run is visible as historical work but does not offer quality or JSONL as if it completed. — ba3e528

### Phase 3: Configurable Quality Horizon

#### Automated

- [x] 3.1 Backend quality horizon tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pytest tests/backtest_quality/test_router.py tests/backtest_quality/test_metrics.py -p no:cacheprovider` — b4c1b8e
- [x] 3.2 Frontend quality horizon tests pass: `npm --prefix frontend run test -- src/features/backtestQuality` — b4c1b8e
- [x] 3.3 Backend and frontend full quality gates pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-run-history-venv uv run pyright && npm --prefix frontend run build` — b4c1b8e

#### Manual

- [x] 3.4 Opening `/workspaces/demo-workspace/backtests/<run_id>/quality` shows 4 hours by default. — b4c1b8e
- [x] 3.5 Changing the selector to 1 minute updates the URL and report metadata to `1 minute` without inventing later movement values. — b4c1b8e
- [x] 3.6 Missing movement warnings remain visible for real completed runs until price enrichment exists. — b4c1b8e
