# Backtest Quality View Implementation Plan

## Overview

Implement the contract/UI portion of the run-scoped BTCUSD BACKTEST quality view described by `S-04`. This plan defines a full backend report contract, deterministic quality metrics, a fixture-backed provider path for verification, a React/Vite frontend, and deployment/test integration while leaving real completed-run wiring to a later `S-02` integration pass.

## Current State Analysis

The repository is still a thin FastAPI service. The application exposes only `/` and `/health`, no backtest routes, no dataset/result schema, no frontend, and no tests. `S-04` is marked blocked because it depends on `S-02` and on the visualization decision, and the roadmap explicitly warns that shipping the view before trusted data would be misleading.

The plan treats `S-04` as two distinct delivery stages. This change delivers the contract and UI now, backed by deterministic fixtures and an explicit provider boundary. A later integration pass, after `S-02` lands, wires that provider to real completed-run data. Tests may use fixtures to prove the report contract and rendering behavior before `S-02` exists.

## Desired End State

After this plan is complete, the application has a tested quality-report contract, deterministic metric engine, fixture-capable API boundary, and React/Vite quality view. In local development and tests, the view can render a run-scoped fixture-backed BTCUSD BACKTEST report showing correlation, hit rate, and a sentiment-vs-later-return plot for a configurable fixed horizon defaulting to 4 hours. It also shows report metadata, warnings, record samples, missing-data effects, and explicit BACKTEST-only analytical wording.

The backend exposes the deterministic full report object shape for `GET /api/workspaces/{workspace_id}/backtests/{run_id}/quality`. Until `S-02` exists, production/default provider behavior must return an explicit not-ready error instead of pretending real run data exists. The later `S-02` integration pass will connect the same provider contract to records that include deterministic later price movement or realized direction fields.

### Delivery Split

- **Contract/UI now:** schemas, metric rules, provider protocol, fixture-backed verification path, React/Vite report UI, local/deploy docs, and automated tests.
- **Real `S-02` integration later:** connect the provider to completed BACKTEST run storage, enforce workspace access against real run ownership, and verify the view against real deterministic later price movement fields.
- Completing this plan means the `S-04` contract and UI are implementation-ready; it does not mean production quality reports are available for real BACKTEST runs.

### Key Discoveries:

- `S-04` is the roadmap north star, but its own entry is blocked by `S-02` and the visualization decision in `context/foundation/roadmap.md:131`.
- The roadmap baseline says the frontend is absent and the backend has only smoke endpoints in `context/foundation/roadmap.md:54`.
- The PRD defines the minimal quality dashboard as sentiment versus later BTCUSD price movement with correlation or hit-rate metrics in `context/foundation/prd.md:101`.
- The PRD requires deterministic BACKTEST output and no live-ready implication in `context/foundation/prd.md:41`.
- The current FastAPI app has only `/` and `/health` in `src/quantitative_sentiment_analysis/main.py:7`.
- No test runner exists yet, so first feature work must add tests and document the runner per `AGENTS.md:32`.

## What We're NOT Doing

- No LIVE streaming, broker integration, order execution, or investment-recommendation wording.
- No implementation of `S-02` news ingestion, sentiment scoring, backtest orchestration, or price fetching.
- No direct price-source integration inside `S-04`; later price movement must be supplied by `S-02`.
- No real completed-run provider wiring in this plan; that belongs to the later `S-02` integration pass.
- No multi-instrument dashboard; BTCUSD remains the only supported instrument for this slice.
- No multi-horizon dashboard; the first report uses one configurable fixed horizon with a 4-hour default.
- No advanced analytics beyond correlation, hit rate, and sentiment-vs-return plotting.
- No full auth system; workspace identity is kept explicit in contracts and must align with `S-01` once that slice exists.

## Implementation Approach

Use a contract-first implementation. First define the report schema, metric semantics, and expected `S-02` input shape. Then implement deterministic metric generation and expose it through a FastAPI route that can be exercised with injected fixtures, while default production behavior remains not-ready until the real provider exists. Add a root-level `frontend/` React/Vite app that consumes the report object and renders the run-scoped view. Finish by integrating local/deployment commands and test runners in repo docs.

Phase 1 can run before `S-02` because it defines the consumer contract. Phase 2 can use fixture inputs for automated verification, but production route wiring must stop at the provider boundary until `S-02` exposes equivalent records. Phases 3-5 validate the frontend against deterministic fixture-backed API responses. The real completed-run path is a later pass after `S-02` lands.

## Critical Implementation Details

### Timing & lifecycle

Do not let `S-04` invent or fetch price data. The quality report input must come from either deterministic test/local fixtures or completed BACKTEST run records produced by `S-02`. In production/default mode before `S-02`, the API must return an explicit not-ready error. After `S-02`, if the run is incomplete, missing, wrong-instrument, or not BACKTEST mode, the API must return an explicit error instead of fabricating a report.

### User experience spec

The view must say that the report is a BACKTEST-only analytical dataset quality indicator, not an investment recommendation or executable trading signal. Use `directional bias`, `LONG`, `SHORT`, and `FLAT`; avoid "signal" wording in UI text.

### State sequencing

Do not include current wall-clock timestamps in the report body. Report output must be deterministic for the same run inputs, horizon, model version, and config version; any displayed load time belongs only to transient frontend state.

### Metric semantics

Hit rate denominator includes all non-noise records in the report sample set. A `LONG` bias is a hit only when realized later direction is up, `SHORT` is a hit only when realized later direction is down, and `FLAT` is a hit only when the realized later direction is flat. Missing later movement is counted as a miss and included in the denominator. Noise records are preserved and counted in `noise_count`, but excluded from hit-rate and correlation denominators because they are explicitly not evaluable as BTCUSD directional-bias quality evidence.

## Phase 1: Quality Report Contract

### Overview

Define the backend report contract and the `S-02` input contract that the quality view consumes. This phase establishes deterministic field names and validation boundaries before metrics or UI are implemented.

### Changes Required:

#### 1. Backtest quality package

**File**: `src/quantitative_sentiment_analysis/backtest_quality/__init__.py`

**Intent**: Create a package namespace for report schemas, metrics, repository/provider boundaries, and API routing.

**Contract**: The package exports no runtime side effects. It should be importable without requiring frontend assets or `S-02` storage.

#### 2. Report and input schemas

**File**: `src/quantitative_sentiment_analysis/backtest_quality/schemas.py`

**Intent**: Define Pydantic models for the full quality report object and the deterministic input records supplied by `S-02`.

**Contract**: Include these conceptual models and invariants:

- `QualityHorizon`: fixed horizon value and unit, defaulting to 4 hours.
- `QualityInputRecord`: run/workspace identity, event timestamp, headline, source identity or `source_name`, sentiment score `-1..1`, directional bias `LONG|SHORT|FLAT`, confidence `0..1`, relevance/noise status, later return value when available, realized later price direction, run/config/model metadata.
- `QualityChartPoint`: normalized chart row for timestamp, sentiment score, later return, directional bias, realized direction, confidence, and hit/miss outcome.
- `QualityMetrics`: correlation, hit rate, sample counts, hit/miss counts, missing movement count, flat count, and noise count.
- `BacktestQualityReport`: full report envelope for workspace, run, BTCUSD instrument, BACKTEST mode, horizon, metrics, warnings, chart points, and representative records.

Missing later price movement is counted as a miss for hit-rate purposes and surfaced through counts/warnings. Missing numeric return is excluded only from correlation because correlation cannot be computed without a numeric pair. Noise records are preserved in the report but excluded from hit-rate and correlation denominators.

#### 3. Backend test setup

**File**: `pyproject.toml`

**Intent**: Add pytest and any required FastAPI test dependency as dev tooling for the first feature test suite.

**Contract**: Use uv-managed dev dependencies and keep runtime dependencies limited to app needs. Configure pytest in `pyproject.toml` only if it helps consistent discovery.

#### 4. Schema tests

**File**: `tests/backtest_quality/test_schemas.py`

**Intent**: Verify validation bounds, enum values, default horizon behavior, and required audit fields.

**Contract**: Tests must cover invalid sentiment/confidence bounds, accepted `LONG|SHORT|FLAT` values, BTCUSD/BACKTEST report identity, and preservation of workspace/run/config metadata.

### Success Criteria:

#### Automated Verification:

- Dependency lock is valid: `uv lock --check`
- Backend dependencies install with dev tools: `UV_LINK_MODE=copy uv sync --locked --dev`
- Schema tests pass: `uv run pytest tests/backtest_quality/test_schemas.py`
- Source and tests compile: `uv run python -m compileall src tests`

#### Manual Verification:

- Report fields are reviewed against `AGENTS.md` data-contract requirements and PRD FR-015.
- The `S-02` handoff fields are explicit enough for a future deterministic dataset implementation.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Metric Engine and Quality API

### Overview

Implement deterministic metric calculation and expose the run-scoped report through FastAPI using a provider boundary for `S-02` data. This phase verifies the route with injected fixture data; the default provider remains explicitly not-ready until the later real `S-02` integration pass.

### Changes Required:

#### 1. Metric engine

**File**: `src/quantitative_sentiment_analysis/backtest_quality/metrics.py`

**Intent**: Convert validated `QualityInputRecord` values into a deterministic `BacktestQualityReport`.

**Contract**: Provide a pure function equivalent to `build_quality_report(input) -> BacktestQualityReport`. It must calculate hit rate, Pearson correlation where numeric pairs exist, chart points, counts, warnings, and record samples without reading global state or current time. Apply the metric semantics from Critical Implementation Details exactly: non-noise rows form the hit-rate denominator, missing movement is a miss, noise is preserved but excluded from metric denominators, and FLAT is a hit only against realized flat movement.

#### 2. S-02 provider boundary

**File**: `src/quantitative_sentiment_analysis/backtest_quality/repository.py`

**Intent**: Define the interface that `S-04` uses to retrieve completed BACKTEST run quality inputs without owning dataset generation or price retrieval.

**Contract**: Expose a provider protocol or abstract class for `get_quality_inputs(workspace_id, run_id)`. The default production implementation raises a typed not-ready error until `S-02` exists, while tests and local development may inject deterministic fixture providers. The real `S-02` storage adapter is explicitly deferred to the later integration pass.

#### 3. API router

**File**: `src/quantitative_sentiment_analysis/backtest_quality/router.py`

**Intent**: Add a run-scoped API route for quality reports.

**Contract**: Route shape: `GET /api/workspaces/{workspace_id}/backtests/{run_id}/quality`. With an injected fixture or later real provider, it returns `BacktestQualityReport`. With the default not-ready provider, it returns an explicit 409-style response naming the missing `S-02` integration. It returns explicit 404/409-style errors for missing/incomplete/wrong-mode runs and never fetches prices directly.

#### 4. Application wiring

**File**: `src/quantitative_sentiment_analysis/main.py`

**Intent**: Include the quality router while preserving existing `/` and `/health` behavior.

**Contract**: Existing smoke endpoints continue to return the same service and health metadata. API routes are mounted under `/api`.

#### 5. Metric and API tests

**File**: `tests/backtest_quality/test_metrics.py`

**Intent**: Verify deterministic metric behavior for hit rate, correlation, missing movement, FLAT rows, and warnings.

**Contract**: Tests use fixed fixtures and assert stable report dictionaries across repeated calls.

**File**: `tests/backtest_quality/test_router.py`

**Intent**: Verify FastAPI response shape and error handling using an injected fixture provider.

**Contract**: Tests cover success, missing run, incomplete run, non-BTCUSD/non-BACKTEST rejection, and unchanged `/health`.

### Success Criteria:

#### Automated Verification:

- Backend quality tests pass: `uv run pytest tests/backtest_quality`
- Full backend test suite passes: `uv run pytest`
- Source and tests compile: `uv run python -m compileall src tests`
- Local API still starts: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- Health endpoint still responds: `curl -fsS http://127.0.0.1:8000/health`

#### Manual Verification:

- A fixture-backed quality report returns correlation, hit rate, chart points, counts, warnings, and report metadata.
- Missing later price movement is visibly counted as a miss in the returned report.
- API errors do not reveal cross-workspace data or imply live trading behavior.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: React/Vite Quality View

### Overview

Add a root-level React/Vite frontend that renders the run-scoped quality report and handles loading, error, empty, and missing-data states.

### Changes Required:

#### 1. Frontend scaffold

**File**: `frontend/package.json`

**Intent**: Create a Vite React TypeScript app with scripts for development, build, and tests.

**Contract**: Keep the frontend in `frontend/` with its own `package-lock.json`. Scripts should include `dev`, `build`, and `test`.

**File**: `frontend/vite.config.ts`

**Intent**: Configure Vite for local API integration and test environment.

**Contract**: Dev server proxies `/api` to the local FastAPI server. Test config supports React component tests.

#### 2. Report types and API client

**File**: `frontend/src/features/backtestQuality/types.ts`

**Intent**: Mirror the backend quality report contract in TypeScript.

**Contract**: Types include report envelope, metrics, chart points, warnings, record samples, and `LONG|SHORT|FLAT` directional bias.

**File**: `frontend/src/features/backtestQuality/api.ts`

**Intent**: Fetch quality reports by `workspace_id` and `run_id`.

**Contract**: Client builds request URLs from `VITE_API_BASE_URL` when it is set, then calls `/api/workspaces/{workspaceId}/backtests/{runId}/quality` under that base. If `VITE_API_BASE_URL` is unset, it falls back to relative `/api` for local Vite proxy development only. It handles non-2xx responses and does not contain metric calculation logic.

#### 3. Quality page and components

**File**: `frontend/src/features/backtestQuality/BacktestQualityPage.tsx`

**Intent**: Render the run-scoped report page after a BACKTEST run completes.

**Contract**: The page displays run metadata, horizon, correlation, hit rate, counts, warnings, and safety wording. It must not call the output a trading signal or recommendation.

**File**: `frontend/src/features/backtestQuality/SentimentReturnPlot.tsx`

**Intent**: Render the sentiment-vs-later-return visualization.

**Contract**: Plot chart points from the backend report, indicate hit/miss outcomes, and handle missing numeric returns without shifting the report denominator.

**File**: `frontend/src/App.tsx`

**Intent**: Route or parse the run-scoped view path for local and production use.

**Contract**: Support a run-scoped quality view path such as `/workspaces/:workspaceId/backtests/:runId/quality`. Future `S-01`/`S-02` work can link to this path after BACKTEST completion.

#### 4. Frontend tests

**File**: `frontend/src/features/backtestQuality/BacktestQualityPage.test.tsx`

**Intent**: Verify report rendering, safety copy, missing-as-miss display, and error states.

**Contract**: Tests use fixture report objects matching backend schema and do not duplicate metric formulas.

**File**: `frontend/src/features/backtestQuality/SentimentReturnPlot.test.tsx`

**Intent**: Verify chart rendering for hit/miss/missing rows.

**Contract**: Tests assert accessible labels or visible markers rather than brittle pixel positions.

### Success Criteria:

#### Automated Verification:

- Frontend dependencies install from lockfile: `npm --prefix frontend ci`
- Frontend tests pass: `npm --prefix frontend run test`
- Frontend build succeeds: `npm --prefix frontend run build`
- Backend tests still pass: `uv run pytest`

#### Manual Verification:

- With FastAPI and Vite dev servers running, the run-scoped quality view renders a fixture-backed report.
- The UI shows correlation, hit rate, sentiment-vs-return plot, report metadata, warnings, and missing movement counted as a miss.
- The UI includes explicit BACKTEST-only analytical wording and avoids investment-recommendation language.
- Mobile and desktop widths keep metric cards, chart labels, and warning text readable without overlap.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Frontend/Backend Deployment Integration

### Overview

Document and wire the frontend/backend development and deployment story without disturbing the existing Render API health deployment.

### Changes Required:

#### 1. Render blueprint integration

**File**: `render.yaml`

**Intent**: Add the Vite frontend deployment path while keeping the existing Python API web service.

**Contract**: Preserve the current FastAPI service and `/health` check. Add or document a Render Static Site service rooted at `frontend/`, with build command `npm ci && npm run build`, publish directory `dist`, and SPA rewrite to `index.html`. Frontend configuration must point to the API base URL through an environment variable rather than hard-coding a workspace or run.

#### 2. CORS and API base configuration

**File**: `src/quantitative_sentiment_analysis/main.py`

**Intent**: Allow the deployed frontend origin to call the API when the frontend is hosted separately.

**Contract**: Add CORS only through an explicit configured origin list. Keep local development support for Vite while avoiding wildcard production origins.

**File**: `frontend/.env.example`

**Intent**: Document required frontend environment variables.

**Contract**: Include `VITE_API_BASE_URL` and safe local defaults or comments. Document that deployed frontend builds must set `VITE_API_BASE_URL` to the FastAPI service origin, while local development may leave it unset to use the Vite `/api` proxy. Do not include secrets.

#### 3. Development documentation

**File**: `README.md`

**Intent**: Document backend, frontend, and test commands for local development.

**Contract**: Include uv install/start/test commands, npm frontend install/dev/build/test commands, and the `/health` smoke check. Include the `/mnt/e` `UV_LINK_MODE=copy` caveat.

#### 4. Change handoff notes

**File**: `context/changes/s-04/plan.md`

**Intent**: Keep the plan aligned with any implementation-specific deployment decision made during Phase 4.

**Contract**: If Render field names or service shape differ during implementation, update only the relevant Phase 4 contract and keep the Progress section stable.

### Success Criteria:

#### Automated Verification:

- Backend lock remains valid: `uv lock --check`
- Backend tests pass: `uv run pytest`
- Frontend tests pass: `npm --prefix frontend run test`
- Frontend build succeeds: `npm --prefix frontend run build`
- Render blueprint parses as YAML: `uv run python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('render.yaml').read_text())"` after adding a YAML parser dependency if needed, or equivalent stdlib-safe validation chosen by the implementer.

#### Manual Verification:

- README local setup commands are sufficient to start FastAPI and Vite in separate terminals.
- Render service changes are reviewed so the existing API health service is not accidentally replaced.
- No frontend environment variable contains secrets or real workspace identifiers.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 5: Contract/UI Verification and Handoff

### Overview

Run the full contract/UI verification suite, confirm the S-02 integration gate, and leave clear handoff notes for implementing or reviewing the slice.

### Changes Required:

#### 1. Integration fixtures

**File**: `tests/backtest_quality/fixtures.py`

**Intent**: Centralize deterministic quality input fixtures used by backend tests and mirrored by frontend test fixtures.

**Contract**: Fixtures include hit, miss, FLAT, noise, and missing later movement cases. They must include stable run/config/model metadata.

#### 2. Frontend fixture alignment

**File**: `frontend/src/features/backtestQuality/testFixtures.ts`

**Intent**: Keep frontend fixtures aligned with backend report shape.

**Contract**: Fixture reports should represent backend response JSON, not raw input records, so frontend tests verify rendering rather than metric calculation.

#### 3. Handoff checklist

**File**: `context/changes/s-04/plan-brief.md`

**Intent**: Summarize decisions, gates, and verification commands for the implementer.

**Contract**: Brief must identify `S-02` as the data prerequisite and list the agreed decisions: full report object, 4-hour default horizon, missing-as-miss, React/Vite frontend, pytest plus Vitest/RTL, and explicit safety wording.

### Success Criteria:

#### Automated Verification:

- Full backend test suite passes: `uv run pytest`
- Frontend test suite passes: `npm --prefix frontend run test`
- Frontend build succeeds: `npm --prefix frontend run build`
- FastAPI app starts: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- Health endpoint responds: `curl -fsS http://127.0.0.1:8000/health`

#### Manual Verification:

- The quality view is checked in a browser against deterministic fixture-backed data.
- The view is confirmed to be contract/UI-complete but blocked from real production run data until the later `S-02` integration pass supplies deterministic later price movement fields.
- The final UI copy is reviewed for BACKTEST-only analytical wording and absence of broker/order/recommendation language.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before closing the change.

---

## Testing Strategy

### Unit Tests:

- Pydantic validation for score/confidence bounds, directional bias values, BTCUSD/BACKTEST identity, and required run metadata.
- Metric calculations for hit rate, correlation, missing movement as miss, insufficient correlation sample size, noise rows, and deterministic repeated output.
- React component tests for metric cards, chart states, warnings, safety wording, loading, empty, and error states.

### Integration Tests:

- FastAPI route tests for successful report generation with injected fixture provider.
- FastAPI route tests for missing run, incomplete run, wrong instrument, wrong mode, and provider-not-wired states.
- Frontend API client tests for non-2xx responses and full report rendering.

### Manual Testing Steps:

1. Start FastAPI locally with `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`.
2. Start Vite locally with `npm --prefix frontend run dev`.
3. Open a run-scoped quality view path backed by deterministic fixture data.
4. Verify correlation, hit rate, sentiment-vs-return plot, warning counts, horizon metadata, and record samples.
5. Confirm missing later movement is counted as a miss.
6. Confirm UI text says BACKTEST-only analytical quality indicator and does not imply trading recommendations.

## Performance Considerations

The first report should be small enough for in-memory metric calculation. Keep metric generation linear in record count and avoid frontend recomputation of correlation/hit rate. If `S-02` later supports large runs, add pagination or sampling for record samples without changing the full metric denominator.

## Migration Notes

No database migration is planned in this contract/UI pass. If `S-02` introduces persistent run storage, the later real integration pass should consume that repository/provider contract instead of adding `S-04`-owned tables.

## References

- Product requirements: `context/foundation/prd.md`
- Roadmap item: `context/foundation/roadmap.md`
- Change identity: `context/changes/s-04/change.md`
- Current FastAPI app: `src/quantitative_sentiment_analysis/main.py`
- Repository rules: `AGENTS.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Quality Report Contract

#### Automated

- [x] 1.1 Dependency lock is valid: `uv lock --check` — 5e64a85
- [x] 1.2 Backend dependencies install with dev tools: `UV_LINK_MODE=copy uv sync --locked --dev` — 5e64a85
- [x] 1.3 Schema tests pass: `uv run pytest tests/backtest_quality/test_schemas.py` — 5e64a85
- [x] 1.4 Source and tests compile: `uv run python -m compileall src tests` — 5e64a85

#### Manual

- [x] 1.5 Report fields are reviewed against `AGENTS.md` data-contract requirements and PRD FR-015 — 5e64a85
- [x] 1.6 The `S-02` handoff fields are explicit enough for a future deterministic dataset implementation — 5e64a85

### Phase 2: Metric Engine and Quality API

#### Automated

- [x] 2.1 Backend quality tests pass: `uv run pytest tests/backtest_quality`
- [x] 2.2 Full backend test suite passes: `uv run pytest`
- [x] 2.3 Source and tests compile: `uv run python -m compileall src tests`
- [x] 2.4 Local API still starts: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- [x] 2.5 Health endpoint still responds: `curl -fsS http://127.0.0.1:8000/health`

#### Manual

- [x] 2.6 A fixture-backed quality report returns correlation, hit rate, chart points, counts, warnings, and report metadata
- [x] 2.7 Missing later price movement is visibly counted as a miss in the returned report
- [x] 2.8 API errors do not reveal cross-workspace data or imply live trading behavior

### Phase 3: React/Vite Quality View

#### Automated

- [ ] 3.1 Frontend dependencies install from lockfile: `npm --prefix frontend ci`
- [ ] 3.2 Frontend tests pass: `npm --prefix frontend run test`
- [ ] 3.3 Frontend build succeeds: `npm --prefix frontend run build`
- [ ] 3.4 Backend tests still pass: `uv run pytest`

#### Manual

- [ ] 3.5 With FastAPI and Vite dev servers running, the run-scoped quality view renders a fixture-backed report
- [ ] 3.6 The UI shows correlation, hit rate, sentiment-vs-return plot, report metadata, warnings, and missing movement counted as a miss
- [ ] 3.7 The UI includes explicit BACKTEST-only analytical wording and avoids investment-recommendation language
- [ ] 3.8 Mobile and desktop widths keep metric cards, chart labels, and warning text readable without overlap

### Phase 4: Frontend/Backend Deployment Integration

#### Automated

- [ ] 4.1 Backend lock remains valid: `uv lock --check`
- [ ] 4.2 Backend tests pass: `uv run pytest`
- [ ] 4.3 Frontend tests pass: `npm --prefix frontend run test`
- [ ] 4.4 Frontend build succeeds: `npm --prefix frontend run build`
- [ ] 4.5 Render blueprint parses as YAML

#### Manual

- [ ] 4.6 README local setup commands are sufficient to start FastAPI and Vite in separate terminals
- [ ] 4.7 Render service changes are reviewed so the existing API health service is not accidentally replaced
- [ ] 4.8 No frontend environment variable contains secrets or real workspace identifiers

### Phase 5: Contract/UI Verification and Handoff

#### Automated

- [ ] 5.1 Full backend test suite passes: `uv run pytest`
- [ ] 5.2 Frontend test suite passes: `npm --prefix frontend run test`
- [ ] 5.3 Frontend build succeeds: `npm --prefix frontend run build`
- [ ] 5.4 FastAPI app starts: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- [ ] 5.5 Health endpoint responds: `curl -fsS http://127.0.0.1:8000/health`

#### Manual

- [ ] 5.6 The quality view is checked in a browser against deterministic fixture-backed data
- [ ] 5.7 The view is confirmed to be contract/UI-complete but blocked from real production run data until the later `S-02` integration pass supplies deterministic later price movement fields
- [ ] 5.8 The final UI copy is reviewed for BACKTEST-only analytical wording and absence of broker/order/recommendation language
