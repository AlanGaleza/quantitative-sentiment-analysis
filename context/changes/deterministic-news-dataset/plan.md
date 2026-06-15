# Deterministic News Dataset Implementation Plan

## Overview

Implement S-02: a deterministic BTCUSD BACKTEST news dataset run that starts from the S-01 draft workspace/run/timeframe shell, retrieves or accepts provider news records, normalizes them, labels relevance, scores sentiment, maps directional bias, computes classification confidence, stores completed dataset records, and exposes a bounded status/preview response. This unlocks real S-04 quality consumption while keeping JSONL export, durable storage, price enrichment, and all live/broker scope out of this slice.

## Current State Analysis

F-01 is already implemented as shared Python contracts. `BacktestRunMetadata` captures workspace/run identity, `BTCUSD`, `BACKTEST`, timezone-aware timeframe, seed, model/config versions, and input fingerprint in `src/quantitative_sentiment_analysis/contracts/schemas.py`. `DatasetRecord` is the canonical per-news record with `timestamp`, `headline`, source identity, `sentiment_score`, `directional_bias`, `confidence`, `relevance`, and model/config metadata. Stable serialization helpers already exist in `src/quantitative_sentiment_analysis/contracts/serialization.py`.

F-02 is already implemented as executable local policy under `src/quantitative_sentiment_analysis/sentiment_policy/`: `DEFAULT_POLICY_CONFIG`, `relevance_for_text`, `score_text`, `directional_bias_for_score`, and `classification_confidence`. The policy locks CryptoPanic as the MVP provider, 30 days as the baseline range, deterministic rule/lexicon scoring, `>= 0.20 LONG`, `<= -0.20 SHORT`, otherwise `FLAT`, and classification confidence semantics.

S-01 is implemented under `src/quantitative_sentiment_analysis/backtest_shell/`. It can create and fetch local/dev draft BACKTEST run shells with `workspace_id`, `run_id`, `BTCUSD`, `BACKTEST`, and timezone-aware timeframe. That repository is explicitly process-local and non-production, so S-02 should use the shell as an input contract but own its own completed-run dataset storage boundary.

S-04 is implemented under `src/quantitative_sentiment_analysis/backtest_quality/`. Its route and metrics are ready, but the default provider returns not-ready until S-02 completed-run storage exists. `QualityInputRecord` uses `event_timestamp`, `later_return`, and `realized_direction`; these are quality-view inputs, not canonical export fields. Until price enrichment exists, the S-02 adapter should map canonical records into quality inputs with missing movement fields so S-04 can surface warnings rather than fabricate price data.

The frontend already has a single operational shell route `/workspaces/:workspaceId/backtests/new`, a typed shell API client, and a shell page. The S-02 UI should extend that page with an explicit second action after draft creation instead of changing routing or making draft creation start analysis.

## Desired End State

After this plan is implemented, a user can create a draft run in the existing workspace BACKTEST shell, then explicitly start deterministic dataset generation for that run. The backend uses the draft shell's workspace/run/timeframe, the F-02 provider/scoring policy, and a deterministic normalization/orchestration pipeline to produce completed `DatasetRecord` rows stored in a local/dev completed-run repository.

The dataset API returns a bounded response containing status, run metadata, provider name, record counts, relevance counts, model/config versions, input fingerprint, and a deterministic preview of records. Provider limitations, including missing CryptoPanic configuration or failed smoke access, are surfaced as typed failed states and HTTP 409 responses rather than silent fallback or fabricated data.

The S-04 quality route can read completed S-02 records through a real adapter. Because price enrichment is out of scope, the adapter initially leaves `later_return` and `realized_direction` missing; existing S-04 metrics then produce explicit warnings while preserving BACKTEST-only analytical wording.

### Key Discoveries:

- `src/quantitative_sentiment_analysis/contracts/schemas.py` already owns canonical `BacktestRunMetadata` and `DatasetRecord`; S-02 should not invent a second dataset schema.
- `src/quantitative_sentiment_analysis/contracts/serialization.py` already owns stable JSON serialization, JSONL line serialization, and run fingerprint helpers.
- `src/quantitative_sentiment_analysis/sentiment_policy/` already owns F-02 scoring, relevance, confidence, model version, config version, provider name, and thresholds.
- `src/quantitative_sentiment_analysis/backtest_shell/` provides draft workspace/run/timeframe shells but is intentionally in-memory and non-production.
- `src/quantitative_sentiment_analysis/backtest_quality/repository.py` currently returns not-ready unless a local fixture provider is selected; S-02 should add a completed-run adapter rather than duplicating quality metrics.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx` already supports injected async actions and deterministic time defaults for tests.

## What We're NOT Doing

- No JSONL/CSV export endpoint or file download; S-03 owns export.
- No durable database, migrations, object storage, or production persistence.
- No real auth/session/JWT integration beyond the existing local/dev workspace identity.
- No price provider integration, price candles, `later_return` calculation, or real `realized_direction`.
- No multi-provider fallback, provider switching, or fabricated production news records.
- No ML/LLM sentiment calls; F-02 local deterministic rule/lexicon scoring remains canonical.
- No LIVE streaming, broker integration, order execution, investment recommendations, or executable trading signal wording.
- No replacement of S-04 metrics or frontend quality page.

## Implementation Approach

Create a new backend package, `src/quantitative_sentiment_analysis/backtest_dataset/`, parallel to `backtest_shell` and `backtest_quality`. It should own completed dataset run schemas, a local/dev completed-run repository, provider protocols, CryptoPanic configuration/smoke-test boundaries, provider fixture support for tests, normalization, deterministic orchestration, and API routes.

The orchestration should start from an existing S-01 draft run fetched by workspace/run ID, then call a provider boundary for records within the draft timeframe, normalize records into a stable provider-neutral shape, dedupe only exact repeated provider IDs, compute relevance/scoring/bias/confidence through existing `sentiment_policy` helpers, build canonical `DatasetRecord` objects, compute `input_fingerprint`, build `BacktestRunMetadata`, and persist the completed run summary plus records in S-02 storage.

Frontend work should extend the existing shell page and shell API client. The UI should show a second explicit BACKTEST-only action after draft creation, then status/result panels with bounded preview and quality-route readiness. It should not present dataset generation as live analysis, advice, or an executable signal.

## Critical Implementation Details

### Deterministic Ordering and Fingerprint

Provider APIs may return records in unstable order. S-02 must impose a stable sort after normalization and before fingerprinting or record creation. Use a documented key such as provider timestamp, provider ID, source identity, normalized headline, and original deterministic index when needed. `input_fingerprint` must be based on normalized input content and deterministic run metadata, not wall-clock time, process-local counters, local paths, environment names, or raw response ordering.

### Quality Adapter Must Not Invent Price Data

S-04 quality inputs require `later_return` and `realized_direction`, but S-02 has no approved price provider. The adapter should map canonical `DatasetRecord.timestamp` to `QualityInputRecord.event_timestamp` and leave movement fields missing. Existing quality metrics will count missing movement and warn; that is preferable to synthetic movement data.

### Real Provider Is a Manual Smoke Dependency

Automated tests should not require CryptoPanic network access or secrets. The real CryptoPanic client should be behind a provider protocol and configured by an environment variable such as `CRYPTOPANIC_API_KEY`. Missing configuration or failed provider capability should produce a typed provider limitation state and HTTP 409, while tests use fixture providers.

## Phase 1: Dataset Contracts and Store

### Overview

Define the S-02 completed dataset run contract and local/dev completed-run repository boundary.

### Changes Required:

#### 1. Backtest dataset package exports

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/__init__.py`

**Intent**: Provide stable package exports for S-02 schemas, repository helpers, provider errors, and orchestration entrypoints.

**Contract**: Re-export completed-run schemas, repository protocol/implementation/provider helper, typed errors, and orchestration service types. Do not import frontend code, S-04 metrics, or provider-specific HTTP modules from the package root unless needed for stable public exports.

#### 2. Completed dataset schemas

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/schemas.py`

**Intent**: Define the API and storage contract for completed deterministic dataset runs without changing canonical F-01 `DatasetRecord`.

**Contract**: Include:

- `DatasetRunStatus` with at least `DRAFT`, `RUNNING`, `COMPLETED`, and `FAILED_PROVIDER_LIMITATION`.
- `DatasetProviderLimitation` with provider name, reason/message, and optional detail safe for product-facing BACKTEST UI.
- `DatasetRunSummary` with `workspace_id`, `run_id`, `instrument`, `mode`, `timeframe_start`, `timeframe_end`, `status`, `provider_name`, `record_count`, relevance counts, `model_version`, `config_version`, `input_fingerprint`, and optional provider limitation.
- `DatasetRunPreview` or response model combining summary plus a bounded list of canonical `DatasetRecord` preview records.
- Validators preserving `BTCUSD`, `BACKTEST`, timezone-aware timeframe, non-negative counts, `0..1` confidence and `-1..1` score through reused contracts.

#### 3. Completed dataset repository

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py`

**Intent**: Store completed dataset run summaries and records in local/dev memory for this MVP slice.

**Contract**: Provide a `CompletedDatasetRepository` protocol, `InMemoryCompletedDatasetRepository`, `get_completed_dataset_repository()`, and typed errors such as not found and unsupported state. Storage must be keyed by `(workspace_id, run_id)`, never by `run_id` alone. The implementation must make clear in names/messages/docstrings that it is local/dev in-memory storage, not durable production storage.

### Success Criteria:

#### Automated Verification:

- Dataset package imports cleanly: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run python -c "import quantitative_sentiment_analysis.backtest_dataset"`
- Dataset schema tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_schemas.py`
- Completed repository tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_repository.py`

#### Manual Verification:

- Schemas reuse F-01 `DatasetRecord` and do not duplicate canonical dataset fields.
- Repository wording clearly states local/dev in-memory non-production storage.
- No JSONL export, auth, live, broker, order, or recommendation scope is introduced.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Provider and Normalization Pipeline

### Overview

Add the provider boundary, CryptoPanic configuration/smoke-test contract, fixture provider, deterministic normalization, and exact provider-ID dedupe.

### Changes Required:

#### 1. Provider protocol and errors

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/provider.py`

**Intent**: Define how S-02 obtains historical provider records without coupling orchestration or tests to real network calls.

**Contract**: Provide a provider protocol that can fetch historical news for `workspace_id`, `run_id`, instrument/mode, and timeframe. Include typed errors for missing configuration, provider limitation, provider unavailable, and unsupported scope. The real provider path must fail explicitly when no CryptoPanic token environment variable is configured.

#### 2. CryptoPanic client boundary

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/cryptopanic.py`

**Intent**: Encapsulate CryptoPanic-specific request construction, environment configuration, and smoke-test behavior.

**Contract**: Use an environment variable such as `CRYPTOPANIC_API_KEY` for `auth_token` configuration. The client should expose a controlled smoke-test method or fetch method that proves configured access can support BTCUSD/BACKTEST historical retrieval. The plan should not require automated tests to call the live network; tests must use injected fixture providers or HTTP client stubs.

#### 3. Provider record normalization

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py`

**Intent**: Convert provider-specific records into stable provider-neutral normalized records used for fingerprinting and scoring.

**Contract**: Normalized records must carry provider name, provider record ID when present, timezone-aware timestamp, headline, optional body/text, source identity/name, and original deterministic index. Deduplication must remove only exact repeated provider IDs; non-identical records and semantically similar headlines are preserved and labeled later. The output order must be deterministic.

#### 4. Provider tests

**File**: `tests/backtest_dataset/test_provider.py`

**Intent**: Verify provider configuration, missing-token behavior, explicit provider limitation, and no live network requirement in tests.

**Contract**: Tests should use monkeypatch/stubs for environment and HTTP behavior. They must assert that missing `CRYPTOPANIC_API_KEY` or equivalent configuration produces a typed provider limitation and does not silently switch provider.

#### 5. Normalization tests

**File**: `tests/backtest_dataset/test_normalization.py`

**Intent**: Verify stable ordering, timezone-aware timestamp handling, exact-ID dedupe, preservation of non-duplicate records, and source identity preservation.

**Contract**: Tests must cover duplicate provider IDs, repeated but non-identical headlines, missing source identity as preserved input for later `NOISE` labeling, and stable normalized output for reordered provider fixture input.

### Success Criteria:

#### Automated Verification:

- Provider tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_provider.py`
- Normalization tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_normalization.py`
- Sentiment policy tests still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/sentiment_policy`

#### Manual Verification:

- Real provider configuration is documented as an env-var smoke dependency, not committed as a secret.
- Provider limitation wording is BACKTEST-only analytical and does not imply fallback or fabricated data.
- Normalization preserves records for audit except exact repeated provider IDs.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Deterministic Dataset Orchestration

### Overview

Build the service that turns a draft run and provider records into completed deterministic `DatasetRecord` rows, run metadata, counts, and fingerprint.

### Changes Required:

#### 1. Dataset orchestration service

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py`

**Intent**: Coordinate S-01 draft run lookup, provider fetch, normalization, relevance, sentiment scoring, directional-bias mapping, classification confidence, metadata creation, fingerprinting, and completed-run storage.

**Contract**: The service must:

- Accept `workspace_id` and `run_id`.
- Fetch the draft run through the S-01 `BacktestShellRepository`.
- Use the draft shell's timeframe, instrument, and mode as authoritative.
- Use an injected provider and injected completed-run repository.
- Use `DEFAULT_POLICY_CONFIG`, `relevance_for_text`, `score_text`, `directional_bias_for_score`, and `classification_confidence`.
- Build canonical `DatasetRecord` objects with stable record IDs where provider IDs are available and deterministic generated IDs where they are not.
- Build `BacktestRunMetadata` with a stable `input_fingerprint`.
- Persist `RUNNING`, `COMPLETED`, or `FAILED_PROVIDER_LIMITATION` state.
- Return a `DatasetRunPreview` with bounded preview records.

#### 2. Deterministic fingerprint and preview helpers

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py`

**Intent**: Keep ordering, fingerprint, and preview rules explicit and testable.

**Contract**: The preview must be deterministic and bounded. Counts must include total records plus `RELEVANT`, `NOISE`, and `IRRELEVANT` counts. The fingerprint must change when normalized input, timeframe, seed, model version, or config version changes and stay stable for reordered equivalent provider input.

#### 3. Orchestration tests

**File**: `tests/backtest_dataset/test_orchestrator.py`

**Intent**: Verify the complete deterministic transformation from fixture provider records and draft shell into completed dataset output.

**Contract**: Tests must cover successful generation, repeated identical output, reordered provider fixture stability, relevance preservation, source identity validation, status transitions, provider limitation status, and no scoring network calls.

#### 4. Serialization compatibility tests

**File**: `tests/backtest_dataset/test_determinism.py`

**Intent**: Verify stable serialized preview and metadata/fingerprint behavior across repeated runs.

**Contract**: Tests must assert that the same fixture input and run metadata produce identical records, counts, fingerprint, and stable serialized preview; changed input or config changes the fingerprint.

### Success Criteria:

#### Automated Verification:

- Orchestration tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_orchestrator.py`
- Determinism tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_determinism.py`
- Contract serialization tests still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/contracts/test_serialization.py`

#### Manual Verification:

- Completed output uses the S-01 draft workspace/run/timeframe without re-deciding those fields.
- Relevance labels preserve noise and irrelevant records rather than hiding them.
- No wall-clock timestamp, random ID, provider ordering, or environment-specific value enters deterministic dataset content.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Backend API and Quality Adapter

### Overview

Expose S-02 API routes and connect completed dataset storage to S-04 quality reports through a real adapter.

### Changes Required:

#### 1. Dataset API router

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/router.py`

**Intent**: Provide the backend API boundary for starting and fetching deterministic dataset runs.

**Contract**: Add routes under `/api/workspaces/{workspace_id}/backtests/{run_id}/dataset`:

- `POST /run` starts deterministic dataset generation synchronously for MVP and returns a `DatasetRunPreview`.
- `GET /` returns the current dataset summary/preview for the workspace/run.

The start route must not create a new run ID. It must use the existing draft run as input, map provider limitations to HTTP 409 with a typed failed status, map missing runs to 404, and preserve BACKTEST-only analytical wording.

#### 2. App router wiring

**File**: `src/quantitative_sentiment_analysis/main.py`

**Intent**: Include the S-02 router without regressing root, health, CORS, shell, or quality routes.

**Contract**: `create_app()` includes the dataset router. Existing CORS methods should remain sufficient for `GET` and `POST`; do not open wildcard origins.

#### 3. Quality provider adapter

**File**: `src/quantitative_sentiment_analysis/backtest_quality/repository.py`

**Intent**: Let the existing S-04 route consume completed S-02 records instead of only fixture/not-ready providers.

**Contract**: Add or wire a `QualityInputProvider` implementation backed by the completed dataset repository. It must map canonical `DatasetRecord.timestamp` to `QualityInputRecord.event_timestamp`, preserve shared enums and metadata, and set `later_return=None` plus `realized_direction=None` until a price-enrichment slice exists. It must return not-ready or not-found errors for missing/incomplete dataset runs.

#### 4. API router tests

**File**: `tests/backtest_dataset/test_router.py`

**Intent**: Verify route contracts, status lifecycle, provider limitation errors, workspace boundaries, and bounded previews.

**Contract**: Tests must cover successful `POST /run`, `GET` completed dataset, missing draft run, cross-workspace miss, provider limitation as 409, preview bounds, CORS behavior, and no export endpoint.

#### 5. Quality adapter tests

**File**: `tests/backtest_quality/test_dataset_adapter.py`

**Intent**: Verify S-04 can consume S-02 completed records through the adapter without fixture mode.

**Contract**: Tests must cover canonical-to-quality field mapping, missing movement warnings through existing metrics, workspace/run isolation, not-ready behavior for incomplete runs, and preservation of existing S-04 response shape.

### Success Criteria:

#### Automated Verification:

- Dataset router tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_router.py`
- Quality adapter tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_quality/test_dataset_adapter.py`
- Backend regression tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/test_main.py tests/contracts tests/backtest_shell tests/backtest_dataset tests/backtest_quality tests/sentiment_policy`

#### Manual Verification:

- API can start a dataset for an existing draft run and fetch its summary/preview.
- Provider limitation returns a clear failed BACKTEST dataset state, not fabricated data.
- Existing `/api/workspaces/{workspace_id}/backtests/{run_id}/quality` route reads completed S-02 data when available.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 5: Frontend Shell Flow

### Overview

Extend the existing shell UI with an explicit deterministic dataset generation step and result display.

### Changes Required:

#### 1. Frontend dataset types

**File**: `frontend/src/features/backtestShell/types.ts`

**Intent**: Mirror the S-02 dataset summary, status, provider limitation, and preview contracts.

**Contract**: Add TypeScript types for dataset statuses, provider limitation, dataset run summary, canonical preview record shape, and dataset preview response. Keep `BTCUSD`, `BACKTEST`, `LONG`, `SHORT`, `FLAT`, `RELEVANT`, `NOISE`, and `IRRELEVANT` literal types aligned with backend contracts.

#### 2. Shell API client additions

**File**: `frontend/src/features/backtestShell/api.ts`

**Intent**: Allow the shell UI to start and fetch deterministic dataset runs.

**Contract**: Add URL builders and functions for `POST /api/workspaces/:workspaceId/backtests/:runId/dataset/run` and `GET /api/workspaces/:workspaceId/backtests/:runId/dataset`. Follow existing base URL, encoding, JSON, and typed error patterns. Do not call quality endpoints from dataset start functions.

#### 3. Shell page dataset workflow

**File**: `frontend/src/features/backtestShell/BacktestShellPage.tsx`

**Intent**: Add a second explicit BACKTEST-only action after draft creation and display dataset generation status/results.

**Contract**: The page must:

- Keep draft creation as a separate first step.
- Show a second action such as `Run deterministic BACKTEST dataset` only after a draft run exists.
- Show loading, completed, and provider limitation/error states.
- Display record count, relevance/noise/irrelevant counts, provider name, model/config versions, input fingerprint, and bounded preview records.
- Mark the quality route as unavailable before completion and available after completion, while noting missing movement if relevant.
- Avoid product-facing wording that implies live trading, broker integration, order execution, investment recommendations, or executable trading signals.

#### 4. Frontend tests

**File**: `frontend/src/features/backtestShell/api.test.ts`

**Intent**: Verify dataset API URL construction, POST/GET behavior, typed errors, and no quality endpoint misuse.

**Contract**: Tests must cover base URL, encoded workspace/run IDs, provider limitation errors, JSON request behavior, and no `/quality` call for dataset generation.

**File**: `frontend/src/features/backtestShell/BacktestShellPage.test.tsx`

**Intent**: Verify the full shell user workflow and semantic safety.

**Contract**: Tests must cover draft creation, explicit dataset run action, completed metadata/preview display, provider limitation display, quality link readiness, bounded preview rendering, and absence of forbidden product-facing wording.

### Success Criteria:

#### Automated Verification:

- Shell API tests pass: `cd frontend && npm test -- --run src/features/backtestShell/api.test.ts`
- Shell page tests pass: `cd frontend && npm test -- --run src/features/backtestShell/BacktestShellPage.test.tsx`
- Frontend build passes: `cd frontend && npm run build`
- Full frontend test suite passes: `cd frontend && npm test -- --run`

#### Manual Verification:

- User can create a draft run, then explicitly start deterministic BACKTEST dataset generation.
- Completed UI shows counts, provider, model/config versions, fingerprint, preview records, and quality route readiness.
- Provider limitation is visible and does not imply fallback or fabricated data.
- UI copy remains BACKTEST-only analytical workflow copy.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 6: Verification and Handoff

### Overview

Run full verification and update planning/foundation artifacts so S-03 export and later price enrichment can start from the completed dataset contract.

### Changes Required:

#### 1. Roadmap handoff

**File**: `context/foundation/roadmap.md`

**Intent**: Reflect that S-02 has an implementation-ready plan and, after implementation, can unblock S-03 and improve S-04 readiness.

**Contract**: Update only S-02/S-03/S-04 handoff language needed by this change. Do not mark S-03 complete, do not claim price enrichment exists, and do not remove the distinction between canonical dataset records and quality movement fields.

#### 2. Quality contract handoff

**File**: `context/foundation/quality-contracts.md`

**Intent**: Add a concise note that S-02 supplies completed canonical dataset records and a quality adapter with missing movement until price enrichment exists.

**Contract**: Keep F-01 contracts canonical. Do not duplicate the full S-02 API schema.

#### 3. News policy handoff

**File**: `context/foundation/news-sentiment-policy.md`

**Intent**: Record how S-02 implements the F-02 policy decisions and what remains deferred.

**Contract**: Note provider smoke-test behavior, local deterministic scoring, fixture-based automated tests, and deferred price enrichment/export without changing F-02 policy choices.

#### 4. Plan brief and change metadata

**File**: `context/changes/deterministic-news-dataset/plan-brief.md`

**Intent**: Keep the brief aligned with implementation reality if scope changes during implementation.

**Contract**: Update phase summary, decisions, and risks if implementation adapts.

**File**: `context/changes/deterministic-news-dataset/change.md`

**Intent**: Keep change metadata aligned with implementation status.

**Contract**: At implementation closeout, update status and date consistently with repository convention.

### Success Criteria:

#### Automated Verification:

- Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/test_main.py tests/contracts tests/backtest_shell tests/backtest_dataset tests/backtest_quality tests/sentiment_policy`
- Full frontend test suite passes: `cd frontend && npm test -- --run`
- Frontend build passes: `cd frontend && npm run build`
- Foundation docs reference S-02 handoff: `rg -n "deterministic-news-dataset|S-02|completed dataset|provider limitation" context/foundation/roadmap.md context/foundation/quality-contracts.md context/foundation/news-sentiment-policy.md`

#### Manual Verification:

- S-03 can use the completed canonical dataset records without re-deciding record fields or determinism semantics.
- S-04 can read completed S-02 records and surfaces missing movement as warnings until price enrichment exists.
- Manual CryptoPanic smoke-test instructions are clear and do not require committing secrets.
- No generated real workspace data, provider payloads, secrets, JSONL exports, or unsanitized news exports are committed.
- Working tree is clean after commits and epilogue.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- Dataset schemas: status values, provider limitation, counts, preview bounds, F-01 enum compatibility, timezone-aware metadata.
- Repository: workspace/run isolation, completed/incomplete/not-found behavior, local/dev non-production messaging, deterministic preview retrieval.
- Provider: env var configuration, missing token failure, typed provider limitation, fixture provider behavior, no automated live-network dependency.
- Normalization: stable ordering, exact provider-ID dedupe, preservation of non-duplicate records, source identity preservation, timezone handling.
- Orchestration: scoring/relevance/confidence integration, stable record IDs, stable fingerprint, repeated identical fixture output.

### Integration Tests:

- API: start dataset from draft run, fetch completed summary/preview, provider limitation 409, missing/cross-workspace run handling, CORS, no export endpoint.
- Quality adapter: completed S-02 records feed S-04 response shape, missing movement warnings, workspace/run isolation, bounded quality payloads.
- Frontend: shell create draft -> explicit dataset run -> completed metadata/preview; provider limitation and quality readiness states.

### Manual Testing Steps:

1. Start backend locally and verify `/health`.
2. Start frontend locally.
3. Open `/workspaces/workspace-alpha/backtests/new`.
4. Create a draft BTCUSD BACKTEST run.
5. Start deterministic BACKTEST dataset generation.
6. Verify status, counts, provider, model/config versions, input fingerprint, and preview records.
7. Open the quality route for the completed run and verify it reads S-02 records with missing movement warnings.
8. Run or document a controlled CryptoPanic smoke test with a local environment variable, without printing or committing the token.
9. Check visible UI/API wording for BACKTEST-only analytical framing and absence of live/execution/advice wording.

## Performance Considerations

The S-02 runtime target is the PRD 30-day historical crypto-news window completing within 5 minutes on a standard developer machine. This plan keeps execution synchronous for MVP, so the implementer should keep provider fetch, normalization, scoring, and preview construction bounded and deterministic. The API response must return a bounded preview rather than every record; full export belongs to S-03.

Metrics may be computed by S-04 over completed records, but S-04 already caps chart and representative payloads. S-02 should avoid introducing unbounded frontend payloads or duplicate quality computation.

## Migration Notes

No database migration is planned. The completed-run repository is local/dev in-memory storage and must be replaced or adapted by a later durable storage slice before production completed runs are required. S-02 should not write generated provider data or real workspace data into the repository tree.

If a real HTTP client dependency is needed for CryptoPanic, add it through `uv add` and commit both `pyproject.toml` and `uv.lock`. Keep automated tests on injected fixtures/stubs rather than live network calls.

## References

- S-02 roadmap item: `context/foundation/roadmap.md`
- PRD dataset requirements: `context/foundation/prd.md`
- F-01 quality contracts: `context/foundation/quality-contracts.md`
- F-02 news and sentiment policy: `context/foundation/news-sentiment-policy.md`
- S-01 shell plan: `context/changes/workspace-backtest-shell/plan.md`
- Shared contracts: `src/quantitative_sentiment_analysis/contracts/schemas.py`
- Stable serialization: `src/quantitative_sentiment_analysis/contracts/serialization.py`
- Sentiment policy helpers: `src/quantitative_sentiment_analysis/sentiment_policy/`
- Draft shell router/repository: `src/quantitative_sentiment_analysis/backtest_shell/`
- Quality route/provider/metrics: `src/quantitative_sentiment_analysis/backtest_quality/`
- Shell frontend API/page: `frontend/src/features/backtestShell/`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Dataset Contracts and Store

#### Automated

- [x] 1.1 Dataset package imports cleanly: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run python -c "import quantitative_sentiment_analysis.backtest_dataset"` — 2a32f72
- [x] 1.2 Dataset schema tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_schemas.py` — 2a32f72
- [x] 1.3 Completed repository tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_repository.py` — 2a32f72

#### Manual

- [x] 1.4 Schemas reuse F-01 `DatasetRecord` and do not duplicate canonical dataset fields. — 2a32f72
- [x] 1.5 Repository wording clearly states local/dev in-memory non-production storage. — 2a32f72
- [x] 1.6 No JSONL export, auth, live, broker, order, or recommendation scope is introduced. — 2a32f72

### Phase 2: Provider and Normalization Pipeline

#### Automated

- [x] 2.1 Provider tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_provider.py` — 121633e
- [x] 2.2 Normalization tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_normalization.py` — 121633e
- [x] 2.3 Sentiment policy tests still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/sentiment_policy` — 121633e

#### Manual

- [x] 2.4 Real provider configuration is documented as an env-var smoke dependency, not committed as a secret. — 121633e
- [x] 2.5 Provider limitation wording is BACKTEST-only analytical and does not imply fallback or fabricated data. — 121633e
- [x] 2.6 Normalization preserves records for audit except exact repeated provider IDs. — 121633e

### Phase 3: Deterministic Dataset Orchestration

#### Automated

- [x] 3.1 Orchestration tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_orchestrator.py` — bfb0d1c
- [x] 3.2 Determinism tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_determinism.py` — bfb0d1c
- [x] 3.3 Contract serialization tests still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/contracts/test_serialization.py` — bfb0d1c

#### Manual

- [x] 3.4 Completed output uses the S-01 draft workspace/run/timeframe without re-deciding those fields. — bfb0d1c
- [x] 3.5 Relevance labels preserve noise and irrelevant records rather than hiding them. — bfb0d1c
- [x] 3.6 No wall-clock timestamp, random ID, provider ordering, or environment-specific value enters deterministic dataset content. — bfb0d1c

### Phase 4: Backend API and Quality Adapter

#### Automated

- [x] 4.1 Dataset router tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_dataset/test_router.py` — b32d3b3
- [x] 4.2 Quality adapter tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/backtest_quality/test_dataset_adapter.py` — b32d3b3
- [x] 4.3 Backend regression tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/test_main.py tests/contracts tests/backtest_shell tests/backtest_dataset tests/backtest_quality tests/sentiment_policy` — b32d3b3

#### Manual

- [x] 4.4 API can start a dataset for an existing draft run and fetch its summary/preview. — b32d3b3
- [x] 4.5 Provider limitation returns a clear failed BACKTEST dataset state, not fabricated data. — b32d3b3
- [x] 4.6 Existing `/api/workspaces/{workspace_id}/backtests/{run_id}/quality` route reads completed S-02 data when available. — b32d3b3

### Phase 5: Frontend Shell Flow

#### Automated

- [x] 5.1 Shell API tests pass: `cd frontend && npm test -- --run src/features/backtestShell/api.test.ts` — 0805ba3
- [x] 5.2 Shell page tests pass: `cd frontend && npm test -- --run src/features/backtestShell/BacktestShellPage.test.tsx` — 0805ba3
- [x] 5.3 Frontend build passes: `cd frontend && npm run build` — 0805ba3
- [x] 5.4 Full frontend test suite passes: `cd frontend && npm test -- --run` — 0805ba3

#### Manual

- [x] 5.5 User can create a draft run, then explicitly start deterministic BACKTEST dataset generation. — 0805ba3
- [x] 5.6 Completed UI shows counts, provider, model/config versions, fingerprint, preview records, and quality route readiness. — 0805ba3
- [x] 5.7 Provider limitation is visible and does not imply fallback or fabricated data. — 0805ba3
- [x] 5.8 UI copy remains BACKTEST-only analytical workflow copy. — 0805ba3

### Phase 6: Verification and Handoff

#### Automated

- [x] 6.1 Full backend test suite passes: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-policy-venv UV_LINK_MODE=copy uv run pytest tests/test_main.py tests/contracts tests/backtest_shell tests/backtest_dataset tests/backtest_quality tests/sentiment_policy` — 1467b87
- [x] 6.2 Full frontend test suite passes: `cd frontend && npm test -- --run` — 1467b87
- [x] 6.3 Frontend build passes: `cd frontend && npm run build` — 1467b87
- [x] 6.4 Foundation docs reference S-02 handoff: `rg -n "deterministic-news-dataset|S-02|completed dataset|provider limitation" context/foundation/roadmap.md context/foundation/quality-contracts.md context/foundation/news-sentiment-policy.md` — 1467b87

#### Manual

- [x] 6.5 S-03 can use the completed canonical dataset records without re-deciding record fields or determinism semantics. — 1467b87
- [x] 6.6 S-04 can read completed S-02 records and surfaces missing movement as warnings until price enrichment exists. — 1467b87
- [x] 6.7 Manual CryptoPanic smoke-test instructions are clear and do not require committing secrets. — 1467b87
- [x] 6.8 No generated real workspace data, provider payloads, secrets, JSONL exports, or unsanitized news exports are committed. — 1467b87
- [x] 6.9 Working tree is clean after commits and epilogue. — 1467b87
