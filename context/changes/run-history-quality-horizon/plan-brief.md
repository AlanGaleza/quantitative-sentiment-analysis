# Run History and Quality Horizon - Plan Brief

> Full plan: `context/changes/run-history-quality-horizon/plan.md`
> Frame brief: `context/changes/run-history-quality-horizon/frame.md`
> Research: `context/changes/run-history-quality-horizon/research.md`

## What & Why

Durable BACKTEST run and dataset state exists, but the product lacks a workspace
run-history discovery contract and treats quality horizon as a hidden fixed
default instead of an explicit, user-selectable report parameter.

This plan makes historical runs recoverable after logout/login and makes the
quality horizon configurable without pretending that price movement enrichment
already exists.

## Starting Point

Postgres already stores `backtest_runs`, `dataset_runs`, and `dataset_records`.
The backend exposes exact-run shell/dataset/quality routes, while the frontend
only exposes saved configs, new BACKTEST, and direct quality URLs.

`QualityHorizon` already defaults to 4 hours and metrics can accept an explicit
horizon, but the route and frontend API do not pass one.

## Desired End State

After login, the user lands on run history and can recover prior draft,
completed, and provider-limited BACKTEST runs. Completed runs expose quality and
JSONL actions; draft/no-dataset runs can start deterministic dataset generation.

Quality reports support a visible, URL-backed horizon selector with V1 presets:
1 minute, 15 minutes, 1 hour, 4 hours, and 24 hours. Missing movement warnings
remain visible until a separate price-enrichment change populates movement
fields.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| History scope | Workspace-level run-history API/UI | Durable data exists but cannot be discovered after relogin. | Frame / Research |
| Landing route | `/workspaces/:workspaceId/backtests` after login | The user's pain is recovering historical work immediately after returning. | Plan |
| Backend model | Read model over existing Postgres tables | Existing tables already hold the needed run and dataset summary data. | Research |
| Horizon API | `horizon_value` + `horizon_unit` query params | Matches existing `QualityHorizon` shape and avoids a custom parser. | Plan |
| Horizon options | Controlled V1 presets | Gives 1 minute support while avoiding fake precision before price enrichment. | Plan |
| Price movement | Out of scope | Foundation contracts forbid fabricating `later_return`/`realized_direction`. | Frame / Research |

## Scope

**In scope:**

- `GET /api/workspaces/{workspace_id}/backtests` history endpoint.
- Postgres-backed run-history repository/read model.
- Frontend run-history route, nav link, and default post-login landing.
- History actions for run dataset, open quality, and download JSONL.
- Backend and frontend quality horizon query/selector.
- Tests for workspace isolation, history recovery, horizon defaults/options, and missing-movement truthfulness.

**Out of scope:**

- Price/candle provider integration.
- Fabricated movement fields.
- Live mode, broker integration, order execution, or investment recommendations.
- Broad saved-config CRUD redesign.
- Advanced dashboarding beyond the existing quality page.

## Architecture / Approach

Backend adds a workspace-scoped read model over `backtest_runs` left joined to
saved config names and `dataset_runs`. Frontend adds a `backtestRuns` feature
package and route. Quality horizon stays in `backtest_quality`: query params
build a `QualityHorizon`, metrics echo it, and the UI selector keeps the URL
shareable.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Backend Run History Contract | Workspace history API over durable run/dataset summaries | Workspace leakage or route ambiguity |
| 2. Frontend Run History and Re-Entry | Post-login history view with actions for historical runs | Reintroducing transient-only state |
| 3. Configurable Quality Horizon | API/UI horizon selector with 4h default and 1m support | Implying missing price movement is solved |

**Prerequisites:** Postgres/auth persistence already deployed; no schema migration expected.
**Estimated effort:** ~2-3 focused implementation sessions across 3 phases.

## Open Risks & Assumptions

- The plan assumes existing Postgres tables are migrated on Render and contain the
  user's historical runs.
- If run volume grows, history may need pagination; the plan allows a bounded
  newest-first response.
- The 1 minute horizon will be selectable, but real plotted return values still
  require a future deterministic price-enrichment change.

## Success Criteria (Summary)

- A user can log out, log back in, and recover prior BACKTEST runs from run history.
- A completed historical run can be opened for quality and JSONL export from the history view.
- Quality horizon can be changed to 1 minute or back to 4 hours, and missing-movement warnings remain honest.
