# Switch News Provider To Sharpe Terminal — Plan Brief

> Full plan: `context/changes/switch-news-provider-to-sharpe-terminal/plan.md`
> Research: `context/changes/switch-news-provider-to-sharpe-terminal/research.md`

## What & Why

Replace CryptoPanic with Sharpe Terminal as the single selected BTCUSD BACKTEST
news provider. The change keeps the deterministic dataset pipeline intact while
moving provider credentials to `SHARPE_API_KEY`.

## Starting Point

Provider access already flows through `HistoricalNewsProvider`, and the dataset
pipeline already handles typed provider limitations, normalization, scoring, and
storage. The runtime dependency and active provider copy are the main switch
points.

## Desired End State

Dataset generation uses Sharpe Terminal by default. Missing credentials produce
typed provider-limited previews, Sharpe articles normalize into existing dataset
records, and active policy/test/frontend copy no longer references CryptoPanic.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Provider boundary | Add a Sharpe adapter, keep orchestration unchanged | Existing protocol isolates provider behavior cleanly. | Research |
| Auth | `Authorization: Bearer <SHARPE_API_KEY>` | Matches Sharpe Terminal API key model and avoids query-string secrets. | Research |
| Timeframe end | Filter locally after fetch | Sharpe `since` is a lower-bound request parameter. | Research |
| Live API tests | Keep out of CI | Provider smoke is a manual pre-prod gate in the test plan. | Research |
| Historical docs | Do not rewrite `context/changes/**` history | Active foundation docs should change; historical plans remain evidence. | Plan |

## Scope

**In scope:**

- Sharpe Terminal provider client.
- Default dataset provider wiring.
- Active policy/config/foundation provider naming.
- Backend and frontend tests for provider limitation and deterministic behavior.

**Out of scope:**

- Multi-provider fallback or provider picker.
- Live Sharpe API calls in automated tests.
- Changes to JSONL schema, scoring, or quality movement enrichment.
- Handling or printing actual secret values.

## Architecture / Approach

`SharpeTerminalClient` maps `data.articles` into the raw keys already accepted by
normalization, then the existing orchestrator handles deterministic
fingerprinting, relevance, sentiment scoring, and persistence. API and frontend
surfaces continue to consume the same provider-limitation schema.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Provider adapter and runtime wiring | Sharpe client plus default API dependency | Provider response shape or timeframe filtering drift. |
| 2. Policy, copy, and regression coverage | Active docs/config/tests use Sharpe Terminal | Stale CryptoPanic copy or missed provider-limitation assertion. |

**Prerequisites:** `SHARPE_API_KEY` exists for manual smoke only; automated tests
must use stubs.
**Estimated effort:** One compact implementation session across two phases.

## Open Risks & Assumptions

- The exact Sharpe Terminal endpoint and envelope must be validated by manual
  smoke before pre-prod trust.
- If Sharpe changes field names, the adapter should fail with typed provider
  limitation or unavailable errors rather than fabricate records.

## Success Criteria (Summary)

- Default dataset generation routes through Sharpe Terminal.
- Automated tests pass offline and do not require `SHARPE_API_KEY`.
- Active docs and user-facing provider-limitation copy reference Sharpe Terminal.
