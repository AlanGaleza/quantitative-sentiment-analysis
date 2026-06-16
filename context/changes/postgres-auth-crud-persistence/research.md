---
date: 2026-06-15T22:45:24+02:00
researcher: Codex
git_commit: 6f10becea927468297834b8fdc3d138ea8df9bea
branch: main
repository: quantitative-sentiment-analysis
topic: "Render Postgres auth CRUD persistence"
tags: [research, postgres, auth, crud, persistence, render]
status: complete
last_updated: 2026-06-15
last_updated_by: Codex
---

# Research: Render Postgres auth CRUD persistence

**Date**: 2026-06-15T22:45:24+02:00
**Researcher**: Codex
**Git Commit**: 6f10becea927468297834b8fdc3d138ea8df9bea
**Branch**: main
**Repository**: quantitative-sentiment-analysis

## Research Question

Ground the change needed to use Render Postgres from the backend service
for user management/auth, workspace ownership, CRUD, draft runs, completed
dataset runs, and dataset records. The user selected Render-side migration and
runtime access using `DATABASE_URL` stored in Render, not pasted into chat.

## Summary

The current product has strong BTCUSD BACKTEST domain logic, workspace/run
identity checks, and tests, but it still uses process-local repositories and
does not authenticate end users. The Postgres/auth/CRUD change needs to add a
real persistence layer, migration tooling, auth/session boundaries, workspace
ownership checks, and a domain CRUD surface while preserving deterministic
dataset/export contracts.

Secrets should stay in Render. The backend service should receive
`DATABASE_URL` from Render Postgres, ideally through `render.yaml`
`fromDatabase` or a Dashboard env var. The Internal Database URL should not be
pasted into chat or committed.

## Detailed Findings

### Current Storage Is In-Memory

- Draft run shell storage is explicitly process-local. `InMemoryBacktestShellRepository`
  keeps runs in a dict keyed by `(workspace_id, run_id)` and is exposed by a
  module-level `_default_repository`.
  Reference: `src/quantitative_sentiment_analysis/backtest_shell/repository.py:45`,
  `src/quantitative_sentiment_analysis/backtest_shell/repository.py:58`,
  `src/quantitative_sentiment_analysis/backtest_shell/repository.py:121`.
- Completed dataset storage is also process-local. It stores previews and full
  records in dicts keyed by `(workspace_id, run_id)`, then serves previews and
  JSONL exports from that in-memory state.
  Reference: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:65`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:165`.
- This means Render restarts/free-tier sleep can lose draft and completed
  dataset state. Postgres-backed repositories are required for a credible CRUD
  and access-control implementation.

### Current API Has Workspace Boundaries But No User Boundary

- Existing routes accept `workspace_id` as a path parameter and pass it into
  repositories. There is no `current_user` dependency on shell, dataset, or
  quality routes.
  Reference: `src/quantitative_sentiment_analysis/backtest_shell/router.py:24`,
  `src/quantitative_sentiment_analysis/backtest_dataset/router.py:121`,
  `src/quantitative_sentiment_analysis/backtest_dataset/router.py:142`,
  `src/quantitative_sentiment_analysis/backtest_quality/router.py:228`.
- Repositories enforce workspace/run lookup by tuple, which prevents accidental
  run-id-only reads, but it does not prove ownership by a logged-in user.
  Reference: `src/quantitative_sentiment_analysis/backtest_shell/repository.py:88`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:87`,
  `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:97`.
- Auth must therefore introduce a dependency such as `require_current_user`,
  resolve workspace ownership from Postgres, and reject or hide resources not
  owned by that user.

### Existing Domain Schemas Are Good Persistence Inputs

- `CreateBacktestRunRequest` already validates BTCUSD/BACKTEST and a 30-day
  aware-timeframe bound. This should remain the write contract for draft runs.
  Reference: `src/quantitative_sentiment_analysis/backtest_shell/schemas.py:21`,
  `src/quantitative_sentiment_analysis/backtest_shell/schemas.py:34`,
  `src/quantitative_sentiment_analysis/backtest_shell/schemas.py:73`.
- `BacktestRunShell` defines the draft run response shape: workspace, run,
  instrument, mode, timeframe, status, created time, and quality path.
  Reference: `src/quantitative_sentiment_analysis/backtest_shell/schemas.py:41`.
- `DatasetRunSummary` and `DatasetRecord` already define the data that must
  survive in Postgres for completed run previews and JSONL export.
  Reference: `src/quantitative_sentiment_analysis/backtest_dataset/schemas.py:117`,
  `src/quantitative_sentiment_analysis/contracts/schemas.py:291`.
- `DatasetRunPreview` enforces preview bounds and record-summary consistency;
  Postgres repositories should return the same Pydantic models rather than
  weakening contracts at the persistence boundary.
  Reference: `src/quantitative_sentiment_analysis/backtest_dataset/schemas.py:172`.

### Frontend Currently Has No Login Or CRUD View

- `App.tsx` only recognizes direct workspace shell and quality routes. There is
  no login/register route, auth callback, or current-user bootstrapping.
  Reference: `frontend/src/App.tsx:17`, `frontend/src/App.tsx:34`,
  `frontend/src/App.tsx:58`.
- The shell page takes `workspaceId` from the URL and uses it directly to create
  runs. The UI displays `Storage` as `Local draft`, which will become stale once
  Postgres lands.
  Reference: `frontend/src/features/backtestShell/BacktestShellPage.tsx:135`,
  `frontend/src/features/backtestShell/BacktestShellPage.tsx:226`.
- The current user-facing flow can create draft runs and trigger dataset
  generation, but there is no list/update/delete UI for saved configs or runs.
  CRUD should be introduced as a separate user-visible workflow, likely saved
  BACKTEST configurations first.

### Render Is Ready For DB Wiring But Needs Blueprint/Env Updates

- Backend currently has no DB dependency in `pyproject.toml`; runtime deps are
  FastAPI and Uvicorn only.
  Reference: `pyproject.toml:7`.
- `render.yaml` defines the backend service and frontend static service, but no
  `databases:` block and no `DATABASE_URL` env var yet.
  Reference: `render.yaml:47`, `render.yaml:57`, `render.yaml:61`.
- README already documents the deployment env split and CORS/base-URL setup.
  This should be extended for `DATABASE_URL`, migrations, and auth secrets.
  Reference: `README.md:125`, `README.md:131`.

## Code References

- `src/quantitative_sentiment_analysis/backtest_shell/repository.py:45` -
  current in-memory draft-run repository.
- `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56` -
  current in-memory completed-dataset repository.
- `src/quantitative_sentiment_analysis/backtest_shell/router.py:24` -
  unauthenticated draft creation route.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:121` -
  unauthenticated dataset generation route.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:142` -
  unauthenticated JSONL export route.
- `src/quantitative_sentiment_analysis/backtest_quality/router.py:228` -
  unauthenticated quality route.
- `frontend/src/App.tsx:58` - route switch lacks login/auth routes.
- `render.yaml:47` - backend service lacks `DATABASE_URL`.
- `pyproject.toml:7` - backend runtime lacks DB/auth dependencies.

## Architecture Insights

- Keep existing repository protocols and add Postgres implementations behind
  the dependency providers. That limits route/orchestrator churn and preserves
  current tests through dependency overrides.
- Add auth as a backend dependency, not as frontend-only route protection.
  Frontend checks improve UX, but backend must enforce ownership.
- Prefer server-side session cookies for the first implementation. They support
  logout/revocation and avoid putting bearer tokens in browser localStorage.
- Hash passwords with Argon2id/bcrypt; never store reversibly encrypted
  passwords and never rely on a Render secret to decrypt user passwords.
- Use migrations as the schema source of truth. App startup should not silently
  create or mutate tables in production.

## Proposed Initial Tables

- `users`: id, email, password_hash, disabled, created_at.
- `sessions`: id/token hash, user_id, expires_at, revoked_at, created_at.
- `workspaces`: id/slug, owner_user_id, name, created_at.
- `backtest_configs`: id, workspace_id, name, instrument, mode,
  timeframe defaults or saved parameters, created_at, updated_at.
- `backtest_runs`: run_id, workspace_id, config_id nullable, instrument, mode,
  timeframe_start, timeframe_end, status, created_at.
- `dataset_runs`: workspace_id, run_id, provider/status/counts/model/config,
  input_fingerprint, provider limitation fields.
- `dataset_records`: workspace_id, run_id, record_id, timestamp, headline,
  source_id/source_name, sentiment_score, directional_bias, confidence,
  relevance, model_version, config_version.

## Historical Context

- `context/foundation/test-plan.md` already treats workspace/run boundary as a
  top risk, but the current protection is storage/API workspace matching, not
  authenticated ownership.
- `context/foundation/prd.md` calls for login-based access and workspace
  privacy, so auth is a product requirement rather than only badge work.
- `context/foundation/infrastructure.md` recommends Render and notes separate
  frontend/backend env vars; this change extends that deployment model with
  Render Postgres.

## Open Questions

- How should migration execution be triggered on Render: manual Render shell
  command, deploy-time migration command, or a separate one-off job/service?
- Should initial registration be open to anyone, or should it be invite/admin
  seeded while the app is public?
- Should session cookies be same-site cross-origin compatible for the separate
  frontend/backend domains, or should the app move toward same-site API proxying
  later?
