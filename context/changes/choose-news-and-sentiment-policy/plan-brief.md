# Choose News and Sentiment Policy — Plan Brief

> Full plan: `context/changes/choose-news-and-sentiment-policy/plan.md`

## What & Why

This plan implements F-02 as a durable news and sentiment policy for BTCUSD BACKTEST datasets. It closes the provider, scoring, threshold, confidence, and visualization decisions that currently block S-02 deterministic dataset generation and real S-04 quality reports.

## Starting Point

F-01 already provides shared dataset/run contracts and stable JSONL serialization, but intentionally leaves provider and scoring policy out of scope. S-04 already has a fixture-backed quality view with 4-hour correlation, hit rate, and a sentiment-vs-return plot, but real S-02 payloads still need a bounded visualization policy.

## Desired End State

`context/foundation/news-sentiment-policy.md` becomes the human-readable source of truth for F-02. A small `sentiment_policy` backend package mirrors deterministic constants and pure scoring/relevance/confidence helpers for S-02. Tests prove that the policy is bounded, deterministic, auditable, and semantically safe.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Provider | CryptoPanic | Best fit for a single aggregated crypto-news feed, with mandatory S-02 smoke test before real ingestion. |
| Historical range | 30 days | Matches the PRD runtime expectation while keeping MVP runs bounded. |
| Relevance | Preserve all records with `RELEVANT`, `NOISE`, or `IRRELEVANT` labels | Keeps auditability and avoids silent filtering. |
| Scoring | Deterministic local rule/lexicon V1 | Reproducible, testable, and free of external model/API drift. |
| Directional bias | `>= 0.20 LONG`, `<= -0.20 SHORT`, otherwise `FLAT` | Transparent first threshold contract that can be tuned later. |
| Confidence | Deterministic classification confidence | Useful for audit without implying market certainty. |
| Quality horizon | 4 hours | Aligns with existing S-04 schema and fixture-backed UI. |
| Visualization | Correlation + hit rate + sampled sentiment-vs-return plot | Keeps the current S-04 signal while bounding real-run payload size. |

## Scope

**In scope:**

- F-02 foundation policy document.
- Executable policy constants and pure scoring/relevance/confidence helpers.
- Tests for thresholds, determinism, bounds, relevance preservation, confidence semantics, and documentation alignment.
- S-02/S-04 handoff notes, including CryptoPanic smoke-test requirement and bounded quality payload policy.

**Out of scope:**

- Real CryptoPanic ingestion/client implementation.
- Persistent storage, workspace shell, export endpoint, or full S-02 dataset generation.
- Multi-provider aggregation.
- LLM/ML sentiment scoring.
- Live streaming, broker integration, order execution, or investment recommendations.
- Advanced quality dashboard.

## Architecture / Approach

The plan keeps F-02 as policy plus executable contracts. Human-facing decisions live in `context/foundation/news-sentiment-policy.md`; provider-independent deterministic behavior lives in `src/quantitative_sentiment_analysis/sentiment_policy/`; S-02 later imports that package while owning provider ingestion and dataset generation.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Human-Readable F-02 Policy | Canonical policy doc and foundation links | Accidentally encoding unverified provider details as production behavior. |
| 2. Executable Policy Contracts | Importable constants and pure policy helpers | Letting policy code grow into ingestion or network behavior. |
| 3. Policy Verification Tests | Determinism, bounds, thresholds, relevance, and confidence tests | Tests becoming implementation trivia instead of policy guardrails. |
| 4. Downstream S-02/S-04 Handoff | Clear next-slice requirements and bounded quality payload policy | Expanding S-04 into an advanced dashboard or changing metric semantics. |

**Prerequisites:** F-01 quality contracts are implemented. CryptoPanic credentials are not required for this change, but S-02 must smoke-test them before real ingestion.

**Estimated effort:** ~2-3 focused sessions across 4 phases.

## Open Risks & Assumptions

- CryptoPanic is selected, but S-02 must verify token/API capability for 30-day BTCUSD BACKTEST before production ingestion.
- Initial rule/lexicon scoring is intentionally simple and auditable; signal-quality tuning is a later iteration.
- If Phase 4 changes S-04 chart payload behavior now, tests and UI copy must make sampling explicit.

## Success Criteria (Summary)

- F-02 decisions are documented once and referenced by foundation docs.
- Executable policy behavior is deterministic, bounded, importable without secrets/network, and covered by tests.
- S-02 can start without re-asking provider/scoring decisions, and S-04 has a bounded real-run visualization policy.
