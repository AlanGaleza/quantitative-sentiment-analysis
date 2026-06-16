# Price Enrichment for Quality Movement Implementation Plan

## Overview

Add deterministic BTCUSD price enrichment for completed BACKTEST quality reports.
For every completed dataset record, the quality adapter will resolve the BTCUSD
proxy price at the event timestamp and at the selected quality horizon, compute
`later_return` and `realized_direction`, and keep explicit missing-data warnings
when price data cannot be resolved.

## Current State Analysis

Completed BACKTEST datasets already persist workspace-scoped news/sentiment
records in Postgres and feed the S-04 quality report route. The quality report
already accepts a selected horizon and can compute hit rate, correlation, missing
movement warnings, and bounded chart payloads from enriched `QualityInputRecord`
values.

The missing piece is the enrichment boundary. The completed-dataset quality
adapter maps canonical dataset records into quality records, but deliberately
sets `later_return=None` and `realized_direction=None`. The frontend plot then
has no numeric pairs, so the user sees only axes and missing-movement copy even
after selecting a 1 minute horizon.

The canonical `DatasetRecord` and JSONL export contract do not contain movement
fields. This change should therefore enrich quality inputs at report-read time
rather than mutating the completed dataset/export schema.

## Desired End State

Opening a completed run quality report for any supported V1 horizon produces
quality inputs enriched from deterministic 1 minute BTC price candles when data
is available. The report exposes numeric `later_return` values, `UP`/`DOWN`/`FLAT`
realized directions, hit-rate and correlation metrics derived from those values,
and a sentiment-vs-return plot with real numeric points.

If price data is unavailable, provider access fails, or a specific candle cannot
be resolved, the route still returns a partial quality report. Affected records
keep `later_return=null` and `realized_direction=null`, warning copy explains the
missing price movement, and the frontend shows a clear empty state instead of a
misleading flat-looking plot.

### Key Discoveries:

- `CompletedDatasetQualityInputProvider` is the real completed-run adapter and
  currently maps movement fields to missing values
  (`src/quantitative_sentiment_analysis/backtest_quality/repository.py:79`,
  `src/quantitative_sentiment_analysis/backtest_quality/repository.py:124`).
- `QualityHorizon` already supports the V1 presets `1 minute`, `15 minutes`,
  `1 hour`, `4 hours`, and `24 hours`
  (`src/quantitative_sentiment_analysis/backtest_quality/schemas.py:34`,
  `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:45`).
- The quality route validates the horizon and passes it to
  `build_quality_report()`, but the `QualityInputProvider` contract does not yet
  receive that horizon
  (`src/quantitative_sentiment_analysis/backtest_quality/router.py:40`,
  `src/quantitative_sentiment_analysis/backtest_quality/router.py:45`).
- `build_quality_report()` is a deterministic calculator over already enriched
  records; it should not fetch external price data
  (`src/quantitative_sentiment_analysis/backtest_quality/metrics.py:26`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:60`).
- The Postgres `dataset_records` table stores canonical news/sentiment fields,
  not price movement fields
  (`src/quantitative_sentiment_analysis/persistence/models.py:342`).
- The frontend plot renders only records with numeric `later_return`; when all
  returns are missing it still renders axes with `0 numeric pairs`
  (`frontend/src/features/backtestQuality/SentimentReturnPlot.tsx:29`,
  `frontend/src/features/backtestQuality/SentimentReturnPlot.tsx:45`).

## What We're NOT Doing

- No live streaming, broker integration, order execution, or investment
  recommendation wording.
- No change to V1 scope beyond `BTCUSD` and `BACKTEST`.
- No mutation of canonical `DatasetRecord` or JSONL export schema with
  `later_return` or `realized_direction`.
- No Sharpe Terminal price integration in this change unless a documented
  historical candle endpoint is later confirmed in a separate change.
- No fallback to fixture prices in production when the live price provider fails.
- No full quality-dashboard redesign beyond the missing numeric-pairs UX.
- No background job framework; enrichment happens during quality report reads.

## Implementation Approach

Introduce a new price-enrichment boundary that mirrors the existing provider
style: typed request objects, fixture-backed tests, injectable fetch functions,
and typed provider failures. Use public Binance Spot `BTCUSDT` 1 minute klines as
the V1 BTCUSD proxy price source, with that proxy choice documented in operator
and foundation notes.

Add a Postgres candle cache keyed by provider, symbol, interval, and candle open
time. The quality adapter will receive the selected `QualityHorizon`, compute
the required 1 minute candle open times for each record's event timestamp and
event-plus-horizon timestamp, read cached candles, fetch missing candle windows,
and then build enriched `QualityInputRecord` values.

Keep price enrichment out of `build_quality_report()`. The metrics layer remains
pure and deterministic over its input records, with an optional route/report path
to include enrichment warnings produced before metric calculation.

## Critical Implementation Details

### Horizon Must Reach the Adapter

The current `QualityInputProvider.get_quality_inputs(workspace_id, run_id)`
signature is insufficient because `later_return` depends on the selected
horizon. Update the provider contract and all test fixtures so the route builds
the validated `QualityHorizon` first, then asks the provider for horizon-specific
quality inputs.

### BTCUSDT Is a Documented BTCUSD Proxy

The V1 price provider will use Binance Spot `BTCUSDT` 1 minute candles as a
practical BTCUSD proxy. This must be visible in docs and provider metadata so
users do not mistake it for a direct BTCUSD feed.

### Candle Alignment Is Close-To-Close

For a timestamp `t`, floor `t` to the UTC minute and use the close price of the
1 minute candle whose open time is that floored minute. The horizon price uses
the same rule for `t + horizon`. `later_return` is
`(horizon_close - event_close) / event_close`; `realized_direction` is `UP` when
the return is greater than `0.0005`, `DOWN` when less than `-0.0005`, and `FLAT`
otherwise.

### Missing Price Data Remains Explicit

Missing candles, provider failures, non-positive event prices, or non-finite
calculated returns must not become `0.0`. The affected movement fields stay
`null`, and the report includes warnings that distinguish missing/provider price
data from real flat movement.

## Phase 1: Price Movement Domain Contract

### Overview

Create the deterministic domain layer for price candles, movement calculation,
horizon conversion, and realized-direction classification without any database
or network dependency.

### Changes Required:

#### 1. Price enrichment package

**File**: `src/quantitative_sentiment_analysis/price_enrichment/__init__.py`

**Intent**: Establish a focused package for price enrichment so pricing logic
does not get mixed into dataset generation, quality metrics, or frontend code.

**Contract**: Export only stable domain types and service entry points needed by
later phases.

#### 2. Price candle and movement schemas

**File**: `src/quantitative_sentiment_analysis/price_enrichment/schemas.py`

**Intent**: Define immutable, validated price candle and movement objects.

**Contract**: Add Pydantic models or frozen dataclasses for `PriceCandle`,
`PriceMovement`, `PriceMovementStatus`, and `PriceMissingReason`. Candle fields
must include provider name, symbol, interval, aware UTC open/close times, and
finite positive OHLC prices. Movement fields must include event candle identity,
horizon candle identity, nullable `later_return`, nullable
`RealizedDirection`, and an optional missing reason.

#### 3. Movement calculation

**File**: `src/quantitative_sentiment_analysis/price_enrichment/movement.py`

**Intent**: Implement deterministic, provider-independent return and realized
direction rules.

**Contract**: Add helpers to convert `QualityHorizon` to `timedelta`, floor
aware datetimes to UTC minute candle open times, compute close-to-close
`later_return`, reject non-finite values, and classify realized direction using
epsilon `0.0005`.

#### 4. Unit tests

**File**: `tests/price_enrichment/test_movement.py`

**Intent**: Lock the movement policy before any provider or persistence work.

**Contract**: Cover all supported horizons, UTC minute flooring, close-to-close
return calculation, `UP`/`DOWN`/`FLAT` thresholds around epsilon `0.0005`, missing
event/horizon candles, zero or negative event price, and deterministic repeated
results.

### Success Criteria:

#### Automated Verification:

- Price movement unit tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment/test_movement.py -p no:cacheprovider`
- Backend lint/type checks pass for the new package: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check src/quantitative_sentiment_analysis/price_enrichment tests/price_enrichment && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright`

#### Manual Verification:

- Review the movement policy and confirm the close-to-close plus epsilon
  behavior matches the selected planning decisions.

**Implementation Note**: After completing this phase and automated verification,
pause for manual confirmation before adding persistence.

---

## Phase 2: Postgres Candle Cache

### Overview

Add durable 1 minute candle storage so repeated quality reports can reuse the
same provider data and remain deterministic across retries and horizon changes.

### Changes Required:

#### 1. Persistence model

**File**: `src/quantitative_sentiment_analysis/persistence/models.py`

**Intent**: Add a global candle cache table that is separate from workspace
dataset records.

**Contract**: Add `PriceCandleModel` with columns for UUID primary key,
`provider_name`, `symbol`, `interval`, `open_time`, `close_time`, OHLC prices,
optional volume/source metadata, and `created_at`. Add a unique constraint on
`provider_name`, `symbol`, `interval`, `open_time` plus an index supporting
range reads by `provider_name`, `symbol`, `interval`, and `open_time`.

#### 2. Alembic migration

**File**: `migrations/versions/20260616_0003_create_price_candles.py`

**Intent**: Make the candle cache deployable to local and Render Postgres.

**Contract**: Create and downgrade the `price_candles` table with constraints
matching `PriceCandleModel`. The migration must follow `20260616_0002` as its
down revision.

#### 3. Candle repository

**File**: `src/quantitative_sentiment_analysis/price_enrichment/repository.py`

**Intent**: Provide a storage boundary for cached candles.

**Contract**: Define a `PriceCandleRepository` protocol plus
`PostgresPriceCandleRepository`. It must support reading exact candle open times
or bounded ranges, upserting provider candles idempotently, and returning domain
`PriceCandle` objects sorted by open time. Upserts must not require a workspace
ID because market candles are shared reference data, but all quality report
entry points must still reach the cache only after workspace-owned dataset
resolution.

#### 4. Persistence tests

**File**: `tests/persistence/test_models.py`

**Intent**: Keep metadata and migration coverage aligned with the new table.

**Contract**: Extend expected table, constraint, index, and migration tests for
`price_candles`.

**File**: `tests/price_enrichment/test_postgres_repository.py`

**Intent**: Verify cache reads and idempotent upserts against Postgres.

**Contract**: Cover ordered range reads, exact timestamp reads, duplicate
upserts for the same provider/symbol/interval/open time, and rejection of
invalid candle data before storage.

### Success Criteria:

#### Automated Verification:

- Persistence metadata tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/persistence/test_models.py -p no:cacheprovider`
- Postgres candle repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment/test_postgres_repository.py -p no:cacheprovider`
- Migration applies cleanly on a test database: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run alembic upgrade head`

#### Manual Verification:

- Inspect the generated `price_candles` schema in local Postgres and confirm the
  unique provider/symbol/interval/open-time constraint exists.

**Implementation Note**: After this phase, pause to confirm the migration is
safe before wiring network-backed price data into request handling.

---

## Phase 3: Binance Price Provider

### Overview

Add the live, public-market-data price provider that can fetch missing Binance
Spot `BTCUSDT` 1 minute candles through an injectable, fixture-tested boundary.

### Changes Required:

#### 1. Price provider contract

**File**: `src/quantitative_sentiment_analysis/price_enrichment/provider.py`

**Intent**: Mirror the existing dataset provider pattern for price data.

**Contract**: Define typed price provider errors for configuration, unavailable
provider, unsupported scope, and limitation-like failures. Add a
`PriceFetchRequest` that accepts `BTCUSD` `BACKTEST`, aware UTC start/end times,
symbol `BTCUSDT`, interval `1m`, and provider metadata. Add a `HistoricalPriceProvider`
protocol and a deterministic fixture provider for automated tests.

#### 2. Binance client

**File**: `src/quantitative_sentiment_analysis/price_enrichment/binance.py`

**Intent**: Fetch historical 1 minute candles from Binance without making
automated tests depend on the live network.

**Contract**: Add `BinanceKlineClient` with injectable `fetch_json`, configurable
base URL for tests, provider name `Binance Spot`, symbol `BTCUSDT`, interval
`1m`, UTC `startTime` and `endTime` milliseconds, and `limit=1000` pagination.
Parse the kline array response into validated `PriceCandle` objects and map
HTTP/URL/parse failures to typed price provider errors.

#### 3. Provider dependency/configuration

**File**: `src/quantitative_sentiment_analysis/price_enrichment/dependencies.py`

**Intent**: Keep provider selection explicit and testable.

**Contract**: Add `QSA_PRICE_PROVIDER` with default `binance`. Support `fixture`
only when `QSA_RUNTIME_ENV=local`; unknown provider values should degrade to a
typed provider configuration failure that the quality adapter can report as
missing price movement rather than an unhandled 500.

#### 4. Provider tests

**File**: `tests/price_enrichment/test_provider.py`

**Intent**: Verify request validation and fixture behavior.

**Contract**: Cover BTCUSD/BACKTEST-only scope, aware datetime requirements,
fixture records, and local-only fixture configuration.

**File**: `tests/price_enrichment/test_binance.py`

**Intent**: Verify the Binance adapter without live network calls.

**Contract**: Cover URL/query construction, UTC millisecond conversion,
pagination when 1000 candles are returned, response parsing, malformed response
handling, HTTP/URL failures, non-finite or non-positive prices, and deterministic
output order.

### Success Criteria:

#### Automated Verification:

- Price provider tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment/test_provider.py tests/price_enrichment/test_binance.py -p no:cacheprovider`
- Backend lint/type checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check src/quantitative_sentiment_analysis/price_enrichment tests/price_enrichment && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright`

#### Manual Verification:

- With the local app configured for the default provider, run a controlled
  one-day candle fetch through a small script or REPL and confirm valid `BTCUSDT`
  1 minute candles are returned without requiring an API key.

**Implementation Note**: After completing this phase, pause for manual provider
smoke confirmation before placing provider fetches on the quality route path.

---

## Phase 4: Quality Adapter Enrichment

### Overview

Wire the selected quality horizon, cached/live candles, and movement calculator
into the completed-dataset quality adapter so real completed runs produce
numeric movement pairs when price data is available.

### Changes Required:

#### 1. Quality input batch schema

**File**: `src/quantitative_sentiment_analysis/backtest_quality/schemas.py`

**Intent**: Carry enrichment warnings through the quality boundary without
putting provider logic into metrics.

**Contract**: Add a small immutable `QualityInputBatch` or equivalent schema
that contains `records: tuple[QualityInputRecord, ...]` and
`extra_warnings: tuple[str, ...]`. It must validate records with the same
constraints as the existing metrics layer, while allowing warning-only metadata
to be passed alongside the records.

#### 2. Quality provider contract

**File**: `src/quantitative_sentiment_analysis/backtest_quality/repository.py`

**Intent**: Make quality inputs horizon-aware.

**Contract**: Change `QualityInputProvider.get_quality_inputs()` to accept a
validated `QualityHorizon` and return `QualityInputBatch` instead of a bare
sequence. Update `NotReadyQualityInputProvider`, `LocalFixtureQualityInputProvider`,
`CompletedDatasetQualityInputProvider`, and all test providers to the new
signature.

#### 3. Quality route wiring

**File**: `src/quantitative_sentiment_analysis/backtest_quality/router.py`

**Intent**: Validate horizon before enrichment and pass it through the adapter.

**Contract**: Build the supported `QualityHorizon` first, call
`provider.get_quality_inputs(workspace_id, run_id, horizon)`, and then pass
`batch.records`, the same horizon, and `batch.extra_warnings` to
`build_quality_report()`. Preserve current auth, workspace ownership, and
workspace/run mismatch checks.

#### 4. Enrichment service

**File**: `src/quantitative_sentiment_analysis/price_enrichment/service.py`

**Intent**: Coordinate cache reads, provider fetches, movement calculation, and
warning collection outside of the metrics layer.

**Contract**: Add a service that accepts canonical dataset records, the selected
`QualityHorizon`, and run summary timeframe metadata. It must determine required
1 minute candle open times for event and horizon timestamps, read cached
candles, fetch and upsert missing candle windows, compute movement per record,
and return enriched quality records plus warning strings. Provider failures
should produce missing movement for affected records and warnings, not unhandled
exceptions.

#### 5. Completed dataset adapter integration

**File**: `src/quantitative_sentiment_analysis/backtest_quality/repository.py`

**Intent**: Replace unconditional missing movement with deterministic price
enrichment for real completed datasets.

**Contract**: Inject the price enrichment service into
`CompletedDatasetQualityInputProvider`. The adapter must still reject
provider-limited, incomplete, empty, unsupported, or cross-workspace runs before
price enrichment. It must not enrich `NOISE` or `IRRELEVANT` differently for
storage/audit purposes; those records can receive movement values for chart
completeness but must remain excluded from metric denominators by existing
relevance logic.

#### 6. Report warning extension

**File**: `src/quantitative_sentiment_analysis/backtest_quality/metrics.py`

**Intent**: Allow the quality report to include enrichment warnings without
making metrics fetch prices.

**Contract**: Add an optional `extra_warnings` input to `build_quality_report()`
or append warnings via a deterministic report-copy step after metrics are built.
Keep existing missing movement, noise, and correlation warnings unchanged.

#### 7. Backend tests

**File**: `tests/backtest_quality/test_dataset_adapter.py`

**Intent**: Verify completed dataset enrichment through the adapter.

**Contract**: Cover successful 1 minute enrichment, selected 4 hour enrichment,
missing candle leaves null movement, provider failure leaves null movement with
warning, `NOISE`/`IRRELEVANT` preservation, and adapter workspace/run isolation.

**File**: `tests/backtest_quality/test_router.py`

**Intent**: Verify the authenticated quality route returns enriched real-run
reports.

**Contract**: Cover default 4 hour and selected 1 minute routes with fixture
price data, deterministic repeated JSON response, provider failure partial
report, unsupported horizon, and no 500 for configured provider errors.

**File**: `tests/backtest_quality/test_metrics.py`

**Intent**: Preserve existing quality metric behavior while accepting enrichment
warnings.

**Contract**: Cover that numeric movement reduces missing count, correlation
pairs are populated only from numeric returns, missing movement still counts as
miss under the selected contract, noise/irrelevant rows remain excluded from
metric denominators, and extra warnings are deterministic.

### Success Criteria:

#### Automated Verification:

- Quality adapter tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/backtest_quality/test_dataset_adapter.py -p no:cacheprovider`
- Quality router and metrics tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/backtest_quality/test_router.py tests/backtest_quality/test_metrics.py -p no:cacheprovider`
- Backend full checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright`

#### Manual Verification:

- On the local app, open a completed run quality report with fixture price data
  and confirm `1 minute` and `4 hours` horizons produce non-null
  `later_return` values and visible numeric chart points.
- Temporarily force the price provider to fail locally and confirm the route
  returns a partial report with warning copy instead of a 500.

**Implementation Note**: After this phase, pause for local browser confirmation
before changing frontend empty-state behavior.

---

## Phase 5: Frontend Empty State and UX

### Overview

Make the quality plot truthful when there are no numeric movement pairs and keep
the existing horizon selection experience intact for enriched reports.

### Changes Required:

#### 1. Plot empty state

**File**: `frontend/src/features/backtestQuality/SentimentReturnPlot.tsx`

**Intent**: Replace the misleading empty axes with explicit no-numeric-pairs UI.

**Contract**: When `points.length > 0` but `numericPoints.length === 0`, render a
status message explaining that no numeric later return pairs are available for
the selected BACKTEST horizon. Include the missing count and keep the panel
accessible. Do not draw the SVG axes in this state.

#### 2. Quality page copy and table consistency

**File**: `frontend/src/features/backtestQuality/BacktestQualityPage.tsx`

**Intent**: Keep metric and warning copy aligned with enriched and partially
missing reports.

**Contract**: Continue rendering backend warnings. Ensure table values show
numeric returns when present and `missing` only when the backend returns null.
Avoid wording that frames directional bias as an executable signal.

#### 3. Frontend tests

**File**: `frontend/src/features/backtestQuality/SentimentReturnPlot.test.tsx`

**Intent**: Lock the no-numeric-pairs state.

**Contract**: Cover empty report with no points, report with points but zero
numeric returns, report with mixed numeric/missing returns, and report with all
numeric returns.

**File**: `frontend/src/features/backtestQuality/BacktestQualityPage.test.tsx`

**Intent**: Verify enriched and partial reports from the user's perspective.

**Contract**: Cover numeric return display, backend enrichment warnings,
horizon selector behavior, and absence of forbidden live trading or investment
recommendation wording.

### Success Criteria:

#### Automated Verification:

- Quality frontend tests pass: `npm --prefix frontend run test -- src/features/backtestQuality`
- Frontend build passes: `npm --prefix frontend run build`

#### Manual Verification:

- In the browser, confirm an enriched report draws numeric dots and a report
  with zero numeric pairs shows a clear empty state instead of a flat-looking
  chart.

**Implementation Note**: After this phase, pause for browser confirmation before
final documentation and deployment smoke.

---

## Phase 6: Docs, Smoke, and Rollout

### Overview

Document the price enrichment policy, deployment configuration, migration needs,
and manual verification steps for local and Render environments.

### Changes Required:

#### 1. Foundation policy update

**File**: `context/foundation/news-sentiment-policy.md`

**Intent**: Record the selected V1 price enrichment policy next to the quality
horizon policy.

**Contract**: Add that completed BACKTEST quality reports use Binance Spot
`BTCUSDT` 1 minute candles as the V1 BTCUSD proxy, close-to-close movement,
epsilon `0.0005` for realized `FLAT`, and partial reports with warnings when
price data is unavailable.

#### 2. Quality contract update

**File**: `context/foundation/quality-contracts.md`

**Intent**: Close the previous downstream handoff that said price enrichment did
not exist.

**Contract**: Update S-04 downstream handoff language to say real completed
quality reports may enrich movement through the price-enrichment boundary while
canonical dataset/export records remain unchanged.

#### 3. Operator notes

**File**: `README.md`

**Intent**: Document local and Render operator expectations.

**Contract**: Add `QSA_PRICE_PROVIDER`, default `binance`, fixture local-only
behavior, Binance `BTCUSDT` proxy wording, and `uv run alembic upgrade head` as
the migration step after deployment.

#### 4. Verification report

**File**: `context/changes/price-enrichment-quality-movement/verification.md`

**Intent**: Capture automated commands and manual smoke results for the change.

**Contract**: Record the backend commands, frontend commands, local manual
quality smoke, and Render smoke. Render smoke must confirm either numeric pairs
for a completed run or a clear provider warning with no 500.

### Success Criteria:

#### Automated Verification:

- Backend test suite for affected areas passes: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment tests/backtest_quality tests/persistence/test_models.py -p no:cacheprovider`
- Frontend quality tests and build pass: `npm --prefix frontend run test -- src/features/backtestQuality && npm --prefix frontend run build`
- Final lint/type checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright`

#### Manual Verification:

- Local smoke: create or reuse a completed `demo-workspace` BACKTEST run, open
  quality for `1 minute`, and confirm numeric movement pairs or a specific price
  provider warning.
- Render smoke: after deploy and `alembic upgrade head`, open the deployed
  completed run quality route for `1 minute` and confirm numeric movement pairs
  or a specific price provider warning, with no `500 Internal Server Error`.
- Confirm JSONL export output for the same run remains canonical dataset output
  and does not include price movement fields.

**Implementation Note**: This phase completes the rollout only after automated
checks and both manual smoke paths are recorded.

---

## Testing Strategy

### Unit Tests:

- Price movement calculation for horizon conversion, UTC minute flooring,
  close-to-close returns, epsilon `FLAT`, and missing-data outcomes.
- Binance response parsing and provider error mapping with injected fetchers.
- Metrics tests proving numeric returns populate correlation pairs while
  missing movement and noise/irrelevant semantics remain deterministic.

### Integration Tests:

- Postgres candle cache migration, constraints, idempotent upserts, and ordered
  reads.
- Completed dataset quality adapter with fixture price provider and cache.
- Authenticated quality route for default and selected horizons, provider
  failure partial reports, and workspace/run isolation.

### Frontend Component/API Tests:

- Plot states for no points, zero numeric pairs, mixed numeric/missing pairs,
  and all numeric pairs.
- Quality page rendering for numeric returns, backend warnings, horizon changes,
  and semantic-safety wording.

### Manual Testing Steps:

1. Apply migrations locally with `uv run alembic upgrade head`.
2. Start the backend and frontend locally.
3. Log in as the seeded user and open run history for `demo-workspace`.
4. Create or reuse a completed BACKTEST run.
5. Open quality for `1 minute`, `4 hours`, and `24 hours`.
6. Confirm numeric chart dots appear when candles are available.
7. Force provider failure or fixture missing candles and confirm partial report
   warnings with no 500.
8. Deploy, run migrations on Render, and repeat a `1 minute` quality smoke on
   the deployed URL.
9. Download JSONL for the same run and confirm no movement fields were added to
   canonical export records.

## Performance Considerations

The price cache should avoid repeated provider calls for the same candle open
times. The enrichment service should derive all requested candle times from the
completed dataset timestamps and selected horizon, group missing times into
bounded fetch windows, and use Binance pagination with `limit=1000`. It must not
use wall-clock time to decide report contents.

The first quality request for a 30-day run may need many candles, especially for
the 24 hour horizon. Provider fetches should have timeouts and degrade to a
partial report with warnings rather than blocking until the request fails at the
ASGI/server boundary.

## Migration Notes

This change adds a new `price_candles` table. Existing users, workspaces, runs,
dataset summaries, dataset records, and JSONL exports do not need data backfill.
The cache fills lazily as quality reports request price movement.

On Render, deploy the code first, run `uv run alembic upgrade head` against the
Render Postgres database, then perform the manual quality smoke. If migration is
rolled back, quality reports should return missing movement warnings instead of
depending on a half-created cache table.

## References

- Change identity: `context/changes/price-enrichment-quality-movement/change.md`
- Quality contracts: `context/foundation/quality-contracts.md`
- News and sentiment policy: `context/foundation/news-sentiment-policy.md`
- Prior run history and horizon plan:
  `context/changes/run-history-quality-horizon/plan.md`
- Deterministic dataset plan:
  `context/changes/deterministic-news-dataset/plan.md`
- Provider switch plan:
  `context/changes/switch-news-provider-to-sharpe-terminal/plan.md`
- Test-plan risks: `context/foundation/test-plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` - <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Price Movement Domain Contract

#### Automated

- [x] 1.1 Price movement unit tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment/test_movement.py -p no:cacheprovider` — 21572cb
- [x] 1.2 Backend lint/type checks pass for the new package: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check src/quantitative_sentiment_analysis/price_enrichment tests/price_enrichment && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright` — 21572cb

#### Manual

- [x] 1.3 Review the movement policy and confirm the close-to-close plus epsilon behavior matches the selected planning decisions. — 21572cb

### Phase 2: Postgres Candle Cache

#### Automated

- [x] 2.1 Persistence metadata tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/persistence/test_models.py -p no:cacheprovider` — 3aa5734
- [x] 2.2 Postgres candle repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment/test_postgres_repository.py -p no:cacheprovider` — 3aa5734
- [x] 2.3 Migration applies cleanly on a test database: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run alembic upgrade head` — 3aa5734

#### Manual

- [x] 2.4 Inspect the generated `price_candles` schema in local Postgres and confirm the unique provider/symbol/interval/open-time constraint exists. — 3aa5734

### Phase 3: Binance Price Provider

#### Automated

- [x] 3.1 Price provider tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment/test_provider.py tests/price_enrichment/test_binance.py -p no:cacheprovider` — 866bc89
- [x] 3.2 Backend lint/type checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check src/quantitative_sentiment_analysis/price_enrichment tests/price_enrichment && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright` — 866bc89

#### Manual

- [x] 3.3 With the local app configured for the default provider, run a controlled one-day candle fetch through a small script or REPL and confirm valid `BTCUSDT` 1 minute candles are returned without requiring an API key. — 866bc89

### Phase 4: Quality Adapter Enrichment

#### Automated

- [x] 4.1 Quality adapter tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/backtest_quality/test_dataset_adapter.py -p no:cacheprovider` — 9069bef
- [x] 4.2 Quality router and metrics tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/backtest_quality/test_router.py tests/backtest_quality/test_metrics.py -p no:cacheprovider` — 9069bef
- [x] 4.3 Backend full checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright` — 9069bef

#### Manual

- [x] 4.4 On the local app, open a completed run quality report with fixture price data and confirm `1 minute` and `4 hours` horizons produce non-null `later_return` values and visible numeric chart points. — 9069bef
- [x] 4.5 Temporarily force the price provider to fail locally and confirm the route returns a partial report with warning copy instead of a 500. — 9069bef

### Phase 5: Frontend Empty State and UX

#### Automated

- [x] 5.1 Quality frontend tests pass: `npm --prefix frontend run test -- src/features/backtestQuality` — 9fb439f
- [x] 5.2 Frontend build passes: `npm --prefix frontend run build` — 9fb439f

#### Manual

- [x] 5.3 In the browser, confirm an enriched report draws numeric dots and a report with zero numeric pairs shows a clear empty state instead of a flat-looking chart. — 9fb439f

### Phase 6: Docs, Smoke, and Rollout

#### Automated

- [x] 6.1 Backend test suite for affected areas passes: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment tests/backtest_quality tests/persistence/test_models.py -p no:cacheprovider` — 2d8ae94
- [x] 6.2 Frontend quality tests and build pass: `npm --prefix frontend run test -- src/features/backtestQuality && npm --prefix frontend run build` — 2d8ae94
- [x] 6.3 Final lint/type checks pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright` — 2d8ae94

#### Manual

- [x] 6.4 Local smoke: create or reuse a completed `demo-workspace` BACKTEST run, open quality for `1 minute`, and confirm numeric movement pairs or a specific price provider warning. — 2d8ae94
- [x] 6.5 Render smoke: after deploy and `alembic upgrade head`, open the deployed completed run quality route for `1 minute` and confirm numeric movement pairs or a specific price provider warning, with no `500 Internal Server Error`. — 2d8ae94
- [x] 6.6 Confirm JSONL export output for the same run remains canonical dataset output and does not include price movement fields. — 2d8ae94
