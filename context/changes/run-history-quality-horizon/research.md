---
date: 2026-06-16T12:57:13+02:00
researcher: Codex
git_commit: 99b8cb745ef4ef814bd4013de47d91fbac6edbb8
branch: main
repository: quantitative-sentiment-analysis
topic: "Run history discovery and configurable quality horizon"
tags: [research, backtest-runs, quality-horizon, frontend, api]
status: complete
last_updated: 2026-06-16
last_updated_by: Codex
---

# Research: Run history discovery and configurable quality horizon

**Date**: 2026-06-16T12:57:13+02:00
**Researcher**: Codex
**Git Commit**: 99b8cb745ef4ef814bd4013de47d91fbac6edbb8
**Branch**: main
**Repository**: quantitative-sentiment-analysis

## Research Question

Ground the change needed to let a logged-in user recover historical BACKTEST runs
after logout/login and make the backtest-quality evaluation horizon explicit and
configurable, while preserving deterministic BACKTEST-only semantics and not
fabricating missing price movement values.

## Summary

The durable data already exists. `backtest_runs`, `dataset_runs`, and
`dataset_records` are persisted in Postgres and remain workspace-scoped, but the
API exposes only exact-run routes and the frontend exposes only saved configs,
new BACKTEST creation, and direct quality URLs. A user who no longer knows the
run ID has no workspace-level run-history discovery path.

The quality horizon already has a domain type and metrics support. `QualityHorizon`
defaults to `4 hours`, and `build_quality_report(records, horizon=...)` can accept
an explicit horizon. The route and frontend client do not pass one, so the
horizon is hidden rather than user-selectable.

This change should add a workspace run-history API/UI and a query-backed quality
horizon selector. It should not attempt to populate `later_return` or
`realized_direction`; current foundation docs explicitly keep price enrichment as
a separate future slice.

## Detailed Findings

### Durable Run State Exists But Has No List Contract

- `BacktestRunModel` stores workspace-owned draft run metadata with unique
  `(workspace_id, run_id)`, optional `config_id`, timeframe, status, and created
  timestamp. It also has a relationship to a single `DatasetRunModel`
  (`src/quantitative_sentiment_analysis/persistence/models.py:186`,
  `src/quantitative_sentiment_analysis/persistence/models.py:189`,
  `src/quantitative_sentiment_analysis/persistence/models.py:217`,
  `src/quantitative_sentiment_analysis/persistence/models.py:241`).
- `DatasetRunModel` stores terminal dataset status, provider metadata, relevance
  counts, model/config versions, input fingerprint, provider-limitation details,
  and a workspace/run index (`src/quantitative_sentiment_analysis/persistence/models.py:248`,
  `src/quantitative_sentiment_analysis/persistence/models.py:251`,
  `src/quantitative_sentiment_analysis/persistence/models.py:311`,
  `src/quantitative_sentiment_analysis/persistence/models.py:312`,
  `src/quantitative_sentiment_analysis/persistence/models.py:319`).
- The shell router exposes `POST /api/workspaces/{workspace_id}/backtests/drafts`
  and `GET /api/workspaces/{workspace_id}/backtests/{run_id}`, but no
  workspace-level `GET /api/workspaces/{workspace_id}/backtests` list route
  (`src/quantitative_sentiment_analysis/backtest_shell/router.py:20`,
  `src/quantitative_sentiment_analysis/backtest_shell/router.py:26`,
  `src/quantitative_sentiment_analysis/backtest_shell/router.py:42`).
- The dataset router also exposes only run-scoped operations: run dataset, export
  JSONL, and fetch exact dataset preview (`src/quantitative_sentiment_analysis/backtest_dataset/router.py:70`,
  `src/quantitative_sentiment_analysis/backtest_dataset/router.py:92`,
  `src/quantitative_sentiment_analysis/backtest_dataset/router.py:127`).

### Existing Repository Patterns Are Item-Scoped

- `BacktestShellRepository` defines `create_draft_run` and `get_run` only, so a
  history feature needs a new method/DTO rather than overloading the existing
  shell response (`src/quantitative_sentiment_analysis/backtest_shell/repository.py:36`,
  `src/quantitative_sentiment_analysis/backtest_shell/repository.py:39`,
  `src/quantitative_sentiment_analysis/backtest_shell/repository.py:47`).
- `PostgresBacktestShellRepository.get_run` already joins `WorkspaceModel` and
  filters by workspace slug plus run ID, which is the access pattern a list query
  should preserve (`src/quantitative_sentiment_analysis/backtest_shell/repository.py:197`,
  `src/quantitative_sentiment_analysis/backtest_shell/repository.py:199`,
  `src/quantitative_sentiment_analysis/backtest_shell/repository.py:201`).
- `PostgresCompletedDatasetRepository.get_run` and `list_records` separately
  resolve the workspace slug before filtering `DatasetRunModel`/`DatasetRecordModel`;
  the list contract should keep this workspace boundary and not accept `run_id`
  alone (`src/quantitative_sentiment_analysis/backtest_dataset/repository.py:201`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:207`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:224`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:246`).

### Frontend Navigation Cannot Discover Historical Runs

- `AppRoute` currently supports only login, saved configs, new shell, and direct
  quality report routes. There is no run-history route (`frontend/src/App.tsx:13`,
  `frontend/src/App.tsx:17`, `frontend/src/App.tsx:22`,
  `frontend/src/App.tsx:27`, `frontend/src/App.tsx:33`).
- `parseAppRoute` recognizes config, shell, and quality paths only
  (`frontend/src/App.tsx:106`, `frontend/src/App.tsx:108`,
  `frontend/src/App.tsx:109`, `frontend/src/App.tsx:110`,
  `frontend/src/App.tsx:111`).
- Authenticated navigation exposes only "Saved configs" and "New BACKTEST"; users
  have no visible "Run history" entry after login (`frontend/src/App.tsx:275`,
  `frontend/src/App.tsx:283`, `frontend/src/App.tsx:286`).
- `BacktestConfigPage` keeps the result of `Create draft run from <config>` in
  local `draftState`, then renders a transient `DraftWorkflowPanel`. This state
  is lost after logout/login or browser refresh (`frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:71`,
  `frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:125`,
  `frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:220`,
  `frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:231`,
  `frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:511`).
- `BacktestShellPage` has the same transient shape for direct draft creation and
  dataset execution; it can show a completed dataset result only inside the
  current component state (`frontend/src/features/backtestShell/BacktestShellPage.tsx:34`,
  `frontend/src/features/backtestShell/BacktestShellPage.tsx:40`,
  `frontend/src/features/backtestShell/BacktestShellPage.tsx:63`,
  `frontend/src/features/backtestShell/BacktestShellPage.tsx:95`,
  `frontend/src/features/backtestShell/BacktestShellPage.tsx:219`).

### Quality Horizon Is a Hidden Default, Not a Request Contract

- `QualityHorizon` is already a typed Pydantic value with `value` and `unit`, and
  its default is `4 hours` (`src/quantitative_sentiment_analysis/backtest_quality/schemas.py:28`,
  `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:34`,
  `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:37`,
  `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:38`).
- `BacktestQualityReport` already echoes the selected horizon in the response
  (`src/quantitative_sentiment_analysis/backtest_quality/schemas.py:105`,
  `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:112`).
- `build_quality_report` accepts an optional horizon and falls back to the
  default only when none is passed (`src/quantitative_sentiment_analysis/backtest_quality/metrics.py:26`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:28`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:100`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:103`).
- The quality route currently calls `build_quality_report(records)` with no
  horizon argument (`src/quantitative_sentiment_analysis/backtest_quality/router.py:31`,
  `src/quantitative_sentiment_analysis/backtest_quality/router.py:39`,
  `src/quantitative_sentiment_analysis/backtest_quality/router.py:40`).
- The frontend quality API client builds `/quality` without query parameters and
  `fetchBacktestQualityReport` accepts only `workspaceId` and `runId`
  (`frontend/src/features/backtestQuality/api.ts:17`,
  `frontend/src/features/backtestQuality/api.ts:21`,
  `frontend/src/features/backtestQuality/api.ts:33`,
  `frontend/src/features/backtestQuality/api.ts:34`,
  `frontend/src/features/backtestQuality/api.ts:35`).
- The quality page displays the report horizon but offers no selector or URL
  persistence for changing it (`frontend/src/features/backtestQuality/BacktestQualityPage.tsx:10`,
  `frontend/src/features/backtestQuality/BacktestQualityPage.tsx:26`,
  `frontend/src/features/backtestQuality/BacktestQualityPage.tsx:113`,
  `frontend/src/features/backtestQuality/BacktestQualityPage.tsx:115`).

### Price Movement Remains Separate

- The completed-dataset quality adapter maps canonical dataset records into
  quality inputs but deliberately sets `later_return=None` and
  `realized_direction=None` (`src/quantitative_sentiment_analysis/backtest_quality/repository.py:79`,
  `src/quantitative_sentiment_analysis/backtest_quality/repository.py:109`,
  `src/quantitative_sentiment_analysis/backtest_quality/repository.py:124`,
  `src/quantitative_sentiment_analysis/backtest_quality/repository.py:125`).
- Quality metrics warn about missing later movement rather than fabricating it
  (`src/quantitative_sentiment_analysis/backtest_quality/metrics.py:60`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:95`,
  `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:198`).
- Foundation contracts explicitly say S-04 must not fetch prices directly or
  fabricate production run data, and completed S-02 records should leave movement
  fields missing until a price-enrichment slice exists
  (`context/foundation/quality-contracts.md:235`,
  `context/foundation/quality-contracts.md:237`,
  `context/foundation/quality-contracts.md:245`,
  `context/foundation/quality-contracts.md:247`,
  `context/foundation/quality-contracts.md:248`).
- The roadmap also names deterministic price enrichment as a separate future
  need before expecting non-empty movement fields (`context/foundation/roadmap.md:137`,
  `context/foundation/roadmap.md:140`, `context/foundation/roadmap.md:141`,
  `context/foundation/roadmap.md:142`).

## Code References

- `src/quantitative_sentiment_analysis/backtest_shell/router.py:26` - create
  draft BACKTEST run shell route.
- `src/quantitative_sentiment_analysis/backtest_shell/router.py:42` - exact-run
  shell read route; no list sibling exists.
- `src/quantitative_sentiment_analysis/backtest_shell/repository.py:197` -
  Postgres exact-run lookup by workspace slug and run ID.
- `src/quantitative_sentiment_analysis/persistence/models.py:186` - durable
  `backtest_runs` model.
- `src/quantitative_sentiment_analysis/persistence/models.py:248` - durable
  `dataset_runs` model.
- `src/quantitative_sentiment_analysis/backtest_quality/router.py:40` - current
  quality route uses hidden default horizon.
- `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:34` - typed
  `QualityHorizon`.
- `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:28` -
  metrics builder already accepts an explicit horizon.
- `frontend/src/App.tsx:106` - route parser lacks run-history path support.
- `frontend/src/App.tsx:283` - authenticated nav lacks run-history entry.
- `frontend/src/features/backtestConfigs/BacktestConfigPage.tsx:71` - draft
  from saved config is transient component state.
- `frontend/src/features/backtestQuality/api.ts:17` - quality URL builder lacks
  horizon query support.
- `frontend/src/features/backtestQuality/BacktestQualityPage.tsx:113` - quality
  page displays horizon but cannot change it.

## Architecture Insights

Run history should be a workspace-scoped read model, not a migration-heavy data
model change. The data already exists in normalized tables, and the existing
route/repository pattern already uses workspace slug plus run ID. A list endpoint
can left join saved config names and dataset summary rows, then return action
paths so the UI does not infer backend route details.

Quality horizon configurability should stay in the quality boundary. The schema
and metrics code already support an explicit `QualityHorizon`; the missing work
is query validation, API-client parameters, a frontend selector, and tests that
prove the selected horizon is echoed in the report. The selector must be honest:
without price enrichment, changing from 4 hours to 1 minute changes the requested
evaluation window metadata, not the availability of plotted price-movement values.

## Historical Context

- `context/changes/workspace-backtest-shell/plan.md` introduced the S-01 route
  and shell contract, including the current exact-run route shape and explicit
  BACKTEST-only framing.
- `context/changes/deterministic-news-dataset/plan.md` added the explicit
  dataset run action and completed-run storage boundary, but deferred durable
  production storage and price enrichment.
- `context/changes/postgres-auth-crud-persistence/plan.md` moved auth,
  workspaces, saved configs, draft runs, dataset runs, and dataset records into
  Postgres. Its progress notes say a browser can create configs, draft runs, and
  datasets, but remaining manual acceptance still calls out public URL persistence
  after restart/redeploy.
- `context/foundation/test-plan.md:46` and `context/foundation/test-plan.md:47`
  treat determinism and workspace/run access boundaries as high-impact risks.
  New history list tests should preserve those access-boundary expectations.
- `context/foundation/test-plan.md:49` treats misleading quality metrics without
  reliable later movement as a high-impact risk. The horizon UI must keep missing
  movement warnings visible.

## Related Research

- `context/changes/postgres-auth-crud-persistence/research.md` - Postgres/auth
  persistence grounding.
- `context/changes/testing-determinism-and-workspace-contracts/research.md` -
  determinism and workspace-boundary test grounding.
- `context/changes/switch-news-provider-to-sharpe-terminal/research.md` -
  provider boundary context.

## Open Questions

- The plan should choose whether login lands on run history by default or only
  adds a visible nav entry. The user workflow points toward making run history
  visible immediately after login, but this is a UX decision rather than a data
  constraint.
