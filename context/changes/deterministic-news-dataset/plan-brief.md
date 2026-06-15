# Deterministic News Dataset — Plan Brief

> Full plan: `context/changes/deterministic-news-dataset/plan.md`

## What & Why

This plan implements S-02: a trader can take the S-01 draft BTCUSD BACKTEST run shell and generate an auditable deterministic per-news dataset. It turns the F-02 provider/scoring policy into executable dataset generation while preserving BACKTEST-only analytical semantics and without adding export, live execution, broker integration, or investment advice.

## Starting Point

F-01 already defines workspace/run identity, canonical dataset records, run metadata, deterministic serialization, and semantic safety. F-02 already defines CryptoPanic, the 30-day default range, local rule/lexicon scoring, relevance labels, thresholds, classification confidence, and S-04 quality-view policy. S-01 already provides the draft workspace/run/timeframe shell and UI.

## Desired End State

The backend can start a deterministic dataset run for an existing draft BACKTEST shell, normalize provider records, label relevance, score sentiment, map directional bias, compute classification confidence, store completed records, and return a bounded metadata/preview response. The frontend shell shows a second explicit action for generating the dataset and displays status, counts, fingerprint, preview, and quality-route readiness. S-04 can read completed S-02 records through a real adapter, with missing movement fields surfaced as warnings until price enrichment exists.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Completed dataset storage | Local/dev in-memory completed-run store | Fastest way to close S-02 and unblock S-04 while keeping durable storage out of scope. |
| Provider testing | Real CryptoPanic client boundary with fixture provider for automated tests | Avoids network/secret-dependent tests while preserving the F-02 smoke-test requirement. |
| Provider limitation | Typed failed status plus HTTP 409 | Matches existing not-ready/unsupported semantics and gives the UI a clear state. |
| Quality movement fields | Adapter-ready, movement missing for now | Avoids inventing price data before a price-enrichment slice while letting S-04 consume real records. |
| Run trigger | Explicit second action after draft creation | Preserves S-01's no-side-effect draft creation contract. |
| Execution model | Synchronous MVP with explicit status lifecycle | Simple enough for current stack while preparing later async work. |
| Dataset response | Metadata summary plus bounded preview | Gives users visible verification without duplicating S-03 export. |
| Provider secret | Environment variable with explicit missing-config failure | Keeps secrets out of the repo and frontend. |
| Deduplication | Exact provider ID dedupe only | Preserves auditability while handling obvious provider duplicates deterministically. |
| S-04 integration | Real QualityInputProvider adapter over completed dataset store | Replaces fixture-only readiness without duplicating quality metrics. |
| Determinism tests | Full rerun tests across fixture/provider, normalization, scoring, storage, API preview | Protects the primary non-functional requirement. |

## Scope

**In scope:**

- Backend completed-run dataset schemas, statuses, metadata summaries, bounded preview, and typed provider limitation.
- Local/dev in-memory completed-run repository isolated by `workspace_id` and `run_id`.
- CryptoPanic provider boundary, env-var configuration, smoke-test contract, and fixture provider for tests.
- Deterministic provider normalization, exact provider-ID dedupe, relevance/scoring/confidence orchestration, fingerprinting, and stable record ordering.
- API endpoint to start dataset generation for an existing draft run and fetch completed status/summary.
- S-04 quality adapter over completed dataset records, with missing movement warnings.
- Frontend shell second action, status display, counts, fingerprint, preview records, provider limitation state, and quality link readiness.

**Out of scope:**

- JSONL/CSV export endpoints or file downloads; S-03 owns export.
- Durable database/storage and migrations.
- Price provider integration or real `later_return` / `realized_direction` enrichment.
- Multi-provider fallback, provider switching, or fabricated production data.
- LIVE streaming, broker integration, order execution, or investment-recommendation wording.
- Real auth/session/JWT implementation.

## Architecture / Approach

Add a focused backend package, `backtest_dataset`, parallel to `backtest_shell` and `backtest_quality`. It should contain schemas, completed-run repository, provider boundary, CryptoPanic normalization, deterministic orchestration, and a router. The S-02 router starts from the S-01 draft run, writes a completed dataset into the S-02 store, and S-04 reads that store through a `QualityInputProvider` adapter. The frontend extends the existing shell page rather than adding a new route.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Dataset Contracts and Store | Completed dataset schema, status, preview, in-memory store | Accidentally treating local/dev storage as production durable storage. |
| 2. Provider and Normalization Pipeline | Provider boundary, env config, fixture provider, exact-ID dedupe | Leaking provider/network instability into deterministic tests. |
| 3. Deterministic Dataset Orchestration | Draft-run to completed records, scoring, fingerprint, status lifecycle | Breaking determinism through ordering, IDs, or runtime values. |
| 4. Backend API and Quality Adapter | Start/status API and S-04 adapter over completed records | Blurring canonical dataset fields with quality-only movement fields. |
| 5. Frontend Shell Flow | User-visible run action, status, counts, preview, quality readiness | Copy implying analysis is live or executable. |
| 6. Verification and Handoff | Full checks and docs handoff to S-03/S-04 | Leaving export or price enrichment scope ambiguous. |

**Prerequisites:** F-01, F-02, and S-01 are implemented; CryptoPanic access is available only for manual smoke testing, not automated tests.
**Estimated effort:** ~4-6 focused sessions across 6 phases.

## Open Risks & Assumptions

- CryptoPanic endpoint details and token limits must be verified by controlled manual smoke test before real ingestion is trusted.
- In-memory completed-run storage is deliberately local/dev and must be replaced by a later durable storage slice before production use.
- S-04 quality reports will initially show missing movement warnings because price enrichment is out of scope.
- Real provider responses may have pagination/order quirks; normalization must impose a stable order.

## Success Criteria (Summary)

- Starting from a draft run, the app can generate a completed deterministic BTCUSD BACKTEST dataset summary and preview.
- Re-running with the same fixture input and run metadata produces identical records, counts, fingerprint, and preview serialization.
- Existing S-04 quality route can consume completed S-02 records through an adapter without fixture provider mode.

## Implementation Handoff

Phases 1-5 delivered the local/dev completed dataset store, provider boundary,
deterministic normalization and orchestration, backend dataset API, S-04 adapter,
and frontend shell flow. Phase 6 final verification keeps S-03 export and price
enrichment explicitly deferred: S-03 should consume completed canonical
`DatasetRecord` rows, and S-04 should continue warning on missing movement until
a future price-enrichment slice supplies `later_return` and `realized_direction`.
