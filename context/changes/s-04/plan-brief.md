# Backtest Quality View — Plan Brief

> Full plan: `context/changes/s-04/plan.md`

## What & Why

Build the contract/UI portion of the `S-04` BTCUSD BACKTEST quality view: a run-scoped report showing whether sentiment and directional bias had a useful relationship with later BTCUSD price movement. This is the roadmap north star, but this plan deliberately ships the report contract and fixture-backed UI first, then leaves real completed-run wiring to a later `S-02` integration pass.

## Starting Point

The repo currently has only a FastAPI smoke app with `/` and `/health`; there is no frontend, no backtest dataset route, no metric engine, and no test runner. The roadmap marks `S-04` blocked by `S-02`, so this plan preserves a strict boundary: this change defines and verifies the consumer contract and UI, while real run data remains blocked until `S-02`.

## Desired End State

After this plan, the app has a tested quality-report schema, metric engine, fixture-capable API boundary, and React/Vite view. In local development and tests, the view can render a deterministic fixture-backed BTCUSD BACKTEST report with correlation, hit rate, a sentiment-vs-later-return plot, counts, warnings, and representative rows. A later `S-02` integration pass wires the same provider contract to real completed BACKTEST run records.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Scope | Contract/UI now, real `S-02` integration later | Unblocks `S-04` design while preventing fixture-backed work from masquerading as production run data. |
| Metrics | Correlation, hit rate, and sentiment-vs-return plot | Gives both summary metrics and inspectable raw relationship. |
| Horizon | Configurable fixed horizon, default 4 hours | Keeps the first view deterministic and auditable without multi-horizon bloat. |
| API shape | Full report object | Gives the React UI a stable contract with metrics, chart rows, warnings, samples, and metadata. |
| Price movement source | Consume from `S-02` output later; use deterministic fixtures now | Preserves reproducibility and prevents direct price fetching in the view slice. |
| Missing/noise semantics | Missing movement counts as miss; noise is preserved but excluded from metric denominators | Keeps source coverage gaps visible while avoiding noise rows distorting directional-bias quality metrics. |
| Frontend | Root `frontend/` React/Vite app | Matches common frontend conventions and keeps backend/frontend surfaces clear. |
| Entry point | Run-scoped view after BACKTEST completion | Avoids hidden latest-run state and keeps workspace/run identity explicit. |
| Tests | Backend pytest plus frontend Vitest/RTL | Covers deterministic report logic and visible UI states without full e2e overhead. |
| Safety copy | Explicit analytical disclaimer | Matches PRD semantic safety and avoids recommendation wording. |

## Scope

**In scope:**

- Backend quality report schemas and deterministic metric engine.
- Run-scoped API route shape for `GET /api/workspaces/{workspace_id}/backtests/{run_id}/quality`, with fixture/local providers now and default not-ready behavior until `S-02`.
- React/Vite frontend under `frontend/`.
- Correlation, hit rate, sentiment-vs-return plot, warnings, and record samples.
- pytest and Vitest/React Testing Library coverage.
- README and Render integration notes for frontend/backend development.

**Out of scope:**

- News ingestion, sentiment scoring, backtest orchestration, direct price fetching, `S-02` implementation, or real completed-run provider wiring.
- LIVE mode, broker integration, order execution, or investment recommendations.
- Multi-instrument, multi-source, multi-horizon, or advanced dashboard features.
- Full auth implementation beyond explicit workspace/run contracts.

## Architecture / Approach

This plan defines the provider boundary that later consumes `S-02` completed BACKTEST records with deterministic later price movement fields. For now, the backend computes a deterministic `BacktestQualityReport` from injected fixtures, exposes the route shape through FastAPI, and renders it in a root React/Vite app. The frontend builds API URLs from `VITE_API_BASE_URL` when set, falls back to relative `/api` only for local proxy development, and displays backend-provided metrics and chart points without recomputing quality metrics.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Quality Report Contract | Pydantic report/input schemas and schema tests | Contract drift with future `S-02` output. |
| 2. Metric Engine and Quality API | Deterministic metrics plus fixture-capable run-scoped FastAPI route | Accidentally fabricating production data before `S-02`. |
| 3. React/Vite Quality View | Browser UI for report metrics, plot, warnings, and safety copy | Frontend bloat or misleading wording. |
| 4. Frontend/Backend Deployment Integration | Local and Render integration docs/config | Replacing or breaking existing API health deployment. |
| 5. Contract/UI Verification and Handoff | Final fixtures, verification, and implementation handoff | Treating fixture-backed UI as production-ready. |

**Prerequisites:** None for contract/UI work; `S-02` must provide deterministic completed-run records with later price movement before real production quality reports can be shown.
**Estimated effort:** ~4-5 focused sessions across 5 phases for contract/UI; a later integration pass is required after `S-02`.

## Open Risks & Assumptions

- `S-02` has not landed, so this plan is complete only as contract/UI work; real completed-run reports require a later provider integration pass.
- Render frontend deployment may require a separate static-site service; the API health service must stay intact.
- Missing later price movement is intentionally counted as a miss, while noise is preserved but excluded from metric denominators.

## Success Criteria (Summary)

- The backend returns a deterministic full quality report from injected fixtures and returns explicit not-ready behavior for real run data until `S-02` is integrated.
- The React/Vite UI renders correlation, hit rate, sentiment-vs-return plot, warnings, missing-as-miss counts, and report metadata from the report API contract.
- Automated pytest and Vitest/RTL tests cover metric determinism, schema bounds, API errors, and visible safety wording.
