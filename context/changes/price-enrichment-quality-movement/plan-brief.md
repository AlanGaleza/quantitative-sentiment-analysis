# Price Enrichment for Quality Movement - Plan Brief

> Full plan: `context/changes/price-enrichment-quality-movement/plan.md`

## What & Why

Completed BACKTEST quality reports currently lack real later price movement, so the plot can show missing movement and a misleading empty axis. This plan adds deterministic price enrichment so selected horizons can produce numeric `later_return` and `realized_direction` for completed BTCUSD BACKTEST datasets.

## Starting Point

The backend already stores completed dataset records, validates quality horizons, and computes metrics from `QualityInputRecord`. The completed-dataset adapter leaves movement missing, and the frontend plot draws only points with numeric `later_return`.

## Desired End State

A user can reopen a completed run, select any supported V1 horizon, and see numeric movement pairs when price candles are available. If candles or the provider are unavailable, the report remains partial, explicit, and non-misleading.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Price source | Binance Spot `BTCUSDT` 1m klines as BTCUSD proxy | Clear public historical candle contract; no API key required. |
| Enrichment timing | Quality-report read time | One completed run can be evaluated for every supported horizon. |
| Persistence | Cache candles, not movement fields | Reuses deterministic price data without changing dataset/JSONL contracts. |
| Candle alignment | Close of containing 1m candle to close of horizon candle | Deterministic, easy to test, and works for all presets. |
| `FLAT` threshold | `abs(later_return) <= 0.0005` | Tiny price noise does not become directional movement. |
| Missing price data | Partial report with null movement and warnings | Honest report without hiding the completed dataset. |
| Horizon scope | All V1 presets | Existing UI/API presets remain fully supported. |
| Zero numeric pairs UX | Explicit empty state | Avoids the current flat-looking chart. |
| Provider failure | Warning/missing movement, not 500 | Production reports degrade gracefully. |
| Provider config | `QSA_PRICE_PROVIDER`, default `binance`, local fixture only | Matches existing provider patterns and stays simple on Render. |
| Smoke scope | Local plus Render | Verifies code and deployed environment behavior. |

## Scope

**In scope:** price-enrichment package, Postgres `price_candles` cache, Binance `BTCUSDT` provider, horizon-aware quality adapter, plot empty state, docs, local/Render smoke.

**Out of scope:** live trading, broker/order/recommendation wording, Sharpe price candles, movement fields in dataset/JSONL, background jobs, full dashboard redesign.

## Architecture / Approach

The quality route validates the horizon, asks a horizon-aware `QualityInputProvider` for records plus enrichment warnings, then passes enriched records to the existing pure `build_quality_report()` metrics function. The completed-dataset provider reads workspace-owned records, the price-enrichment service resolves cached/live candles, and movement is computed close-to-close.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Price Movement Domain Contract | Deterministic movement and `UP`/`DOWN`/`FLAT` rules | Wrong timestamp alignment or threshold semantics. |
| 2. Postgres Candle Cache | Durable reusable candle cache and migration | Schema mismatch or cache uniqueness errors. |
| 3. Binance Price Provider | Fixture-tested live price provider boundary | Provider response/rate/failure behavior. |
| 4. Quality Adapter Enrichment | Real completed runs get enriched movement values | Provider failures must not become false metrics or 500s. |
| 5. Frontend Empty State and UX | Clear plot behavior for zero numeric pairs | UI could still imply flat movement. |
| 6. Docs, Smoke, and Rollout | Policy docs, operator notes, local and Render verification | Deployment/migration/config drift. |

**Prerequisites:** Postgres locally and on Render; at least one completed BACKTEST run for smoke.  
**Estimated effort:** About 3-5 implementation sessions across 6 phases.

## Open Risks & Assumptions

- Binance `BTCUSDT` is accepted as the V1 BTCUSD proxy price source.
- First quality read for a large 30-day run may need multiple provider calls, so cache and timeouts matter.
- Missing movement still counts as a miss under the current metric contract; this plan makes missing price data explicit rather than redefining hit-rate semantics.
- Render migration must be run after deploy before the candle cache is usable.

## Success Criteria (Summary)

- Completed run quality reports for `1 minute` and `4 hours` can show numeric `later_return` values when candles are available.
- Missing price data yields null movement plus explicit warnings, not fabricated zero returns and not a 500.
- JSONL export remains unchanged and does not include price movement fields.
