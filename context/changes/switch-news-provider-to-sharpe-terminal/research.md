---
date: 2026-06-15T19:53:41+02:00
researcher: Codex
git_commit: ce208ad1fedd3fa8b9a14987a55a3f13de97e19c
branch: sketch
repository: quantitative-sentiment-analysis
topic: "Switch BACKTEST news provider from CryptoPanic to Sharpe Terminal"
tags: [research, codebase, backtest-dataset, provider, sentiment-policy]
status: complete
last_updated: 2026-06-15
last_updated_by: Codex
---

# Research: Switch BACKTEST news provider from CryptoPanic to Sharpe Terminal

**Date**: 2026-06-15T19:53:41+02:00
**Researcher**: Codex
**Git Commit**: ce208ad1fedd3fa8b9a14987a55a3f13de97e19c
**Branch**: sketch
**Repository**: quantitative-sentiment-analysis

## Research Question

How should the existing deterministic BTCUSD BACKTEST news provider boundary move
from CryptoPanic to Sharpe Terminal while preserving workspace isolation,
deterministic dataset generation, provider-limitation semantics, and offline
automated verification?

## Summary

The provider switch is a bounded S-02 provider-boundary change. The existing
architecture already isolates provider access behind `HistoricalNewsProvider`,
converts provider failures to typed provider-limited dataset summaries, and
normalizes generic provider record keys before scoring. The safest path is to
replace the default provider dependency with a Sharpe Terminal adapter, map
Sharpe `data.articles` into the existing raw-record keys, keep live provider
access out of CI, and update active policy/test copy from CryptoPanic to Sharpe
Terminal.

Sharpe Terminal access must remain a manual smoke dependency via
`SHARPE_API_KEY`; automated tests should stub HTTP and assert the request
contract, response-envelope parsing, pagination, local `timeframe_end`
filtering, and typed provider limitations. The quality-contract and test-plan
foundation docs keep the important invariants: deterministic JSONL, source
identity, workspace/run boundaries, preserved `NOISE`/`IRRELEVANT`, and no
provider-dependent CI.

## Detailed Findings

### Provider Boundary

- `ProviderFetchRequest` already enforces non-empty `workspace_id` and `run_id`,
  BTCUSD-only scope, BACKTEST-only mode, timezone-aware timeframe values, and
  non-reversed timeframes in `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:59`.
- The provider protocol is intentionally small: implementations expose
  `provider_name` and `fetch_historical_news(request)` returning raw mapping
  records in `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:83`.
- Provider failures already have typed categories:
  configuration, unavailable, unsupported scope, and limitation errors in
  `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:17`.

### Normalization Contract

- Normalization accepts provider-independent keys: IDs from `id`,
  `provider_record_id`, or `record_id`; timestamps from `published_at`,
  `timestamp`, or `created_at`; headlines from `title` or `headline`; and body
  text from `body`, `text`, or `summary` in
  `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:72`.
- The dedupe boundary is exact provider-record ID dedupe, followed by stable
  ordering on timestamp, provider ID, source identity, headline, and original
  index in
  `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:99`.
- Timestamp normalization requires timezone-aware datetimes or ISO-8601 strings
  with timezone in
  `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:124`.

### Orchestrator And API Integration

- `DatasetOrchestrator` consumes only the `HistoricalNewsProvider` protocol,
  then normalizes, fingerprints, scores, and persists records in
  `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:44`.
- Provider limitations are saved as terminal
  `FAILED_PROVIDER_LIMITATION` summaries with zero records and deterministic
  limitation fingerprints in
  `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:171`.
- The FastAPI dataset route maps provider-limited previews to HTTP `409` and
  uses the dependency returned by `get_historical_news_provider()` in
  `src/quantitative_sentiment_analysis/backtest_dataset/router.py:43`.

### Policy And Frontend Copy

- `DEFAULT_POLICY_CONFIG.provider_name` is the source imported by dataset
  orchestration for provider metadata defaults in
  `src/quantitative_sentiment_analysis/sentiment_policy/config.py:8`.
- The active policy document names the selected provider, manual smoke
  requirement, and `SHARPE_API_KEY` handoff in
  `context/foundation/news-sentiment-policy.md:42` and
  `context/foundation/news-sentiment-policy.md:186`.
- Frontend API tests assert provider-limitation detail text and preview payload
  propagation, so provider-name and env-var copy must be updated there too:
  `frontend/src/features/backtestShell/api.test.ts:333`.

### Test Strategy

- Existing provider tests are offline and should remain offline. They already
  assert fixture-provider immutability and unsupported scope validation in
  `tests/backtest_dataset/test_provider.py:41`.
- Sharpe-specific provider tests should cover env-var configuration,
  `Authorization: Bearer` headers, query params, `data.articles` response
  envelope, local upper-bound timeframe filtering, pagination, unexpected
  payloads, and provider-unavailable mapping.
- The project test plan explicitly keeps real provider access out of CI and
  treats provider smoke as a manual pre-prod gate in
  `context/foundation/test-plan.md:93`.

## Code References

- `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:59` -
  provider request scope and timeframe validation.
- `src/quantitative_sentiment_analysis/backtest_dataset/provider.py:83` -
  provider protocol to satisfy.
- `src/quantitative_sentiment_analysis/backtest_dataset/normalization.py:72` -
  generic raw-provider key mapping.
- `src/quantitative_sentiment_analysis/backtest_dataset/orchestrator.py:68` -
  provider call and failure handling.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:43` -
  default provider dependency.
- `src/quantitative_sentiment_analysis/sentiment_policy/config.py:8` -
  provider name policy config.
- `tests/backtest_dataset/test_provider.py:63` - provider-configuration tests.
- `frontend/src/features/backtestShell/api.test.ts:333` - frontend provider
  limitation copy tests.

## Architecture Insights

The provider integration point is intentionally narrow. A Sharpe adapter should
translate Sharpe Terminal’s API shape into the generic raw-record keys already
consumed by normalization rather than adding Sharpe-specific branching to
normalization or orchestration. This preserves existing deterministic
fingerprinting, exact ID dedupe, source-identity fallback, and scoring behavior.

Because the provider’s `since` parameter is a lower bound only, the client must
filter records beyond `timeframe_end` locally before returning raw records.
That keeps the rest of the dataset pipeline deterministic and prevents records
outside the user-selected BACKTEST timeframe from entering canonical data.

## Historical Context

- `context/changes/deterministic-news-dataset/plan.md` introduced the provider
  boundary, typed provider-limitation failures, deterministic normalization, and
  bounded preview behavior. This provider switch should reuse that boundary
  instead of changing orchestration semantics.
- `context/changes/testing-determinism-and-workspace-contracts/research.md`
  grounded recent test rollout around dataset determinism and workspace
  contracts. This switch must not weaken those tests or introduce run-id-only
  access behavior.
- `context/foundation/test-plan.md` identifies provider normalization/dedupe and
  source identity as a high-risk Phase 2 area. This switch should add
  fixture-backed provider tests without relying on live Sharpe Terminal access.

## Related Research

- `context/changes/testing-determinism-and-workspace-contracts/research.md`
- `context/changes/jsonl-export/research.md`

## Open Questions

- None for local implementation. A real Sharpe Terminal smoke test remains a
  manual pre-prod activity because automated verification must stay offline and
  must not print or depend on `SHARPE_API_KEY`.
