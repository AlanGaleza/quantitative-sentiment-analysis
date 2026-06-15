# Switch News Provider To Sharpe Terminal Implementation Plan

## Overview

Replace the default BTCUSD BACKTEST news provider from CryptoPanic to Sharpe
Terminal while preserving deterministic dataset contracts, provider-limitation
semantics, and offline automated verification. The production provider should
read credentials from `SHARPE_API_KEY` and keep real provider smoke tests out of
CI.

## Current State Analysis

The dataset pipeline already routes provider access through the
`HistoricalNewsProvider` protocol, normalizes provider-independent raw records,
and converts provider failures into typed `FAILED_PROVIDER_LIMITATION` summaries.
The default provider dependency is the only runtime switch point, while policy
docs, config defaults, backend tests, and frontend provider-limitation tests
carry user-facing provider copy.

## Desired End State

The default dataset API uses Sharpe Terminal for real BACKTEST news retrieval.
Missing `SHARPE_API_KEY` produces the same typed provider-limitation behavior as
before, Sharpe response records are mapped into existing normalization keys, and
all active docs/tests refer to Sharpe Terminal instead of CryptoPanic.

### Key Discoveries:

- Provider request validation already enforces workspace/run, BTCUSD, BACKTEST,
  timezone-aware timeframe, and non-reversed timeframes:
  `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:59`.
- Normalization already accepts generic keys that can be produced by a Sharpe
  adapter: `id`, `published_at`, `title`, `body`/`summary`, `source_id`, and
  `source_name`:
  `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:72`.
- Provider-limited runs are already stored as terminal summaries with zero
  records:
  `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:171`.

## What We're NOT Doing

- No live Sharpe Terminal API calls in automated tests.
- No printing, validating, or committing the actual `SHARPE_API_KEY` value.
- No multi-provider fallback, provider selection UI, or provider aggregation.
- No changes to BACKTEST-only scope, scoring thresholds, JSONL schema, or quality
  movement enrichment.

## Implementation Approach

Add a Sharpe Terminal adapter under `backtest_dataset`, wire it as the default
provider dependency, and update the active policy/config/test surfaces to Sharpe
Terminal. The adapter should translate Sharpe’s `data.articles` envelope into
the raw-record keys already consumed by normalization, use Bearer auth, paginate
with `limit`/`offset`, pass `coin=BTC` and `since=<timeframe_start>`, and locally
filter records after `timeframe_end`.

## Phase 1: Provider Adapter And Runtime Wiring

### Overview

Introduce the Sharpe Terminal provider client and route dataset generation
through it by default.

### Changes Required:

#### 1. Sharpe Terminal provider client

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/sharpe.py`

**Intent**: Add a provider adapter that satisfies the existing
`HistoricalNewsProvider` boundary without changing orchestration or
normalization. It should keep configuration and provider failures typed.

**Contract**: Expose `SharpeTerminalClient`, `SHARPE_API_KEY_ENV`,
`SHARPE_NEWS_API_URL`, and `fetch_historical_news(request)`. Authentication uses
`Authorization: Bearer <SHARPE_API_KEY>`. The response contract is
`data.articles`, and returned raw records must include the keys accepted by
existing normalization.

#### 2. Default provider dependency

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/router.py`

**Intent**: Make Sharpe Terminal the default provider for dataset generation API
calls.

**Contract**: `get_historical_news_provider()` returns `SharpeTerminalClient()`
while preserving FastAPI dependency override behavior used by tests.

#### 3. Public package exports

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/__init__.py`

**Intent**: Make Sharpe provider symbols importable from the package boundary
for tests and future smoke tooling.

**Contract**: Include Sharpe provider symbols in `__all__` without changing
existing exported dataset contracts.

### Success Criteria:

#### Automated Verification:

- Provider tests cover missing `SHARPE_API_KEY`, Bearer auth headers, Sharpe
  request params, `data.articles` parsing, pagination, local `timeframe_end`
  filtering, unexpected payloads, and unavailable-provider errors.
- Backend dataset tests pass with the new provider dependency.
- Ruff passes for the provider and touched backend tests.

#### Manual Verification:

- No phase-level manual verification is required for local/CI completion. Live
  Sharpe Terminal smoke remains a pre-prod gate outside automated tests.

**Implementation Note**: Phase blocks use plain bullets; the corresponding
checkboxes live only in `## Progress`.

---

## Phase 2: Policy, Copy, And Regression Coverage

### Overview

Update active policy/config/docs/tests so the product no longer presents
CryptoPanic as the selected provider.

### Changes Required:

#### 1. Sentiment policy config

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/config.py`

**Intent**: Keep generated dataset metadata aligned with the new selected
provider.

**Contract**: `DEFAULT_POLICY_CONFIG.provider_name` is `Sharpe Terminal`.

#### 2. Active foundation policy documents

**Files**:
`context/foundation/news-sentiment-policy.md`,
`context/foundation/test-plan.md`,
`context/foundation/roadmap.md`,
`context/foundation/shape-notes.md`

**Intent**: Keep living foundation docs consistent with the provider switch.

**Contract**: Active foundation references name Sharpe Terminal and
`SHARPE_API_KEY`. Historical `context/changes/**` documents remain historical
and should not be rewritten for this change.

#### 3. Backend and frontend regression fixtures

**Files**:
`tests/backtest_dataset/**`,
`tests/backtest_quality/test_dataset_adapter.py`,
`tests/sentiment_policy/**`,
`frontend/src/features/backtestShell/*.test.tsx`,
`frontend/src/features/backtestShell/*.test.ts`

**Intent**: Update user-facing provider-limitation copy and fixture IDs while
preserving deterministic dataset, export, repository, policy, and UI/API
behavior tests.

**Contract**: Tests continue to assert typed provider limitation payloads,
stable JSONL behavior, source identity, and policy-document load-bearing
decisions with Sharpe Terminal naming.

### Success Criteria:

#### Automated Verification:

- Full backend pytest suite passes.
- Frontend Vitest suite passes.
- `git diff --check` reports no whitespace errors.
- No active source, test, frontend, or foundation file outside historical
  `context/changes/**` still references CryptoPanic.

#### Manual Verification:

- No phase-level manual verification is required for local/CI completion. Copy
  is covered by focused backend and frontend assertions.

**Implementation Note**: Phase blocks use plain bullets; the corresponding
checkboxes live only in `## Progress`.

---

## Testing Strategy

### Unit Tests:

- Provider client construction and missing API key handling.
- Response-envelope parsing and raw-record mapping.
- Pagination and local timeframe filtering.
- Existing policy and normalization tests with Sharpe provider naming.

### Integration Tests:

- Existing dataset router/orchestrator tests for provider-limited states and
  successful fixture-backed dataset generation.
- Existing frontend API/component tests for provider-limitation copy.

### Manual Testing Steps:

1. Confirm `SHARPE_API_KEY` is set only in the operator environment when running
   a manual provider smoke.
2. Run a controlled local BACKTEST smoke outside CI and verify provider
   limitations do not leak secrets.
3. Review the dataset preview copy for BACKTEST-only analytical wording.

## Performance Considerations

The adapter should use bounded page sizes and stop when a returned page is
shorter than `page_limit`. Local filtering by `timeframe_end` is intentionally
cheap and deterministic.

## Migration Notes

No persisted production data migration is required. Existing local/dev in-memory
repositories are process-local and do not need conversion.

## References

- Related research: `context/changes/switch-news-provider-to-sharpe-terminal/research.md`
- Provider protocol: `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:83`
- Normalization mapping: `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:72`
- Default provider dependency: `src/quantitative_sentiment_analysis/backtest_dataset/router.py:43`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Provider Adapter And Runtime Wiring

#### Automated

- [x] 1.1 Provider tests cover missing `SHARPE_API_KEY`, Bearer auth headers, Sharpe request params, `data.articles` parsing, pagination, local `timeframe_end` filtering, unexpected payloads, and unavailable-provider errors. — 03ec574
- [x] 1.2 Backend dataset tests pass with the new provider dependency. — 03ec574
- [x] 1.3 Ruff passes for the provider and touched backend tests. — 03ec574

### Phase 2: Policy, Copy, And Regression Coverage

#### Automated

- [x] 2.1 Full backend pytest suite passes. — 03ec574
- [x] 2.2 Frontend Vitest suite passes. — 03ec574
- [x] 2.3 `git diff --check` reports no whitespace errors. — 03ec574
- [x] 2.4 No active source, test, frontend, or foundation file outside historical `context/changes/**` still references CryptoPanic. — 03ec574
