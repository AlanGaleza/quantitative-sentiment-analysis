# Workspace BACKTEST Shell — Plan Brief

> Full plan: `context/changes/workspace-backtest-shell/plan.md`

## What & Why

This plan implements S-01: the trader can enter a workspace, keep the workflow explicitly BTCUSD BACKTEST-only, choose a timezone-aware 30-day-or-less timeframe, and create a draft BACKTEST run shell. It gives S-02 a concrete run/workspace/timeframe contract without pulling in real auth, persistent storage, news ingestion, scoring, or export.

## Starting Point

The backend already has FastAPI, shared F-01 contracts, and a workspace-scoped S-04 quality route. The frontend already has Vite/React and a quality-report route, but no operational shell route or form for creating BACKTEST runs.

## Desired End State

The app has a workspace-scoped draft run API and a single-screen operational UI at `/workspaces/:workspaceId/backtests/new`. A local/dev workspace identity stub is used deliberately, draft runs are stored in a non-production in-memory repository, and the existing quality route keeps working. Tests cover backend validation, frontend routing/form behavior, and semantic-safety wording.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Auth/workspace identity | Local/dev workspace identity stub | Unblocks S-02 without pretending real login is implemented. |
| Run semantics | Create draft BACKTEST run shell | Gives S-02 a concrete run contract. |
| Persistence | In-memory local repository | Testable and explicit, while avoiding premature database choices. |
| Default timeframe | Last 30 days | Aligns with F-02 policy and the runtime target. |
| Timeframe validation | Timezone-aware ISO, max 30 days, end >= start | Matches F-01 determinism constraints and protects S-02 runtime. |
| UX | Operational single-screen app | Fits a repeated workflow tool better than a landing page. |
| S-04 relation | Shell route coexists with quality route | Preserves S-04 while providing a future path to quality reports. |
| Testing | Backend + frontend + semantic safety | Covers the main contract and wording risks. |

## Scope

**In scope:**

- Backend draft BACKTEST run schema, status, validation, and in-memory repository.
- Workspace-scoped API routes to create and fetch draft runs.
- Frontend route `/workspaces/:workspaceId/backtests/new`.
- Single-screen shell UI for workspace, BTCUSD, BACKTEST, timeframe, run status, and future quality link.
- Backend and frontend tests, including semantic-safety checks.
- Roadmap/change handoff notes for S-02.

**Out of scope:**

- Real login/auth provider, sessions, roles, or auth middleware.
- Persistent database/storage and migrations.
- News ingestion, sentiment scoring execution, JSONL export, or price enrichment.
- Running the S-02 analysis from the shell.
- Broker integration, order execution, LIVE mode, or investment-recommendation wording.

## Architecture / Approach

Add a `backtest_shell` backend package parallel to `backtest_quality`, backed by shared F-01 contracts and an in-memory repository. Extend the existing FastAPI app with a workspace-scoped router, then extend the Vite app routing so the new shell route and the existing quality route coexist.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Backend Contract | Draft run schemas, status, validation, and repository | Accidentally creating production storage/auth scope. |
| 2. API Routes | Create/get draft run API and tests | Weak error semantics for S-02 handoff. |
| 3. Frontend Route + Client | Shell route parser, types, API client | Regressing existing S-04 quality route. |
| 4. Operational UI | Single-screen shell form and tests | UI implying live execution or analysis already runs. |
| 5. Verification + Handoff | Final docs, roadmap/brief alignment, full verification | Leaving S-02 without a clear next contract. |

**Prerequisites:** F-01 quality contracts are implemented; F-02 policy is implemented; existing S-04 route must remain compatible.

**Estimated effort:** ~3-4 focused sessions across 5 phases.

## Open Risks & Assumptions

- Local/dev workspace identity is intentionally not real login; FR-001 remains partially deferred.
- In-memory storage is non-production and must not be treated as durable completed-run storage.
- Default 30-day dates must be made deterministic in tests rather than tied to uncontrolled wall-clock behavior.

## Success Criteria (Summary)

- A user can open the shell route, create a draft BTCUSD BACKTEST run, and see its validated metadata.
- Backend contracts reject unsafe or invalid timeframe/workspace inputs.
- Existing S-04 quality route and tests continue to work unchanged.
