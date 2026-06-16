# Postgres Auth CRUD Persistence - Plan Brief

> Full plan: `context/changes/postgres-auth-crud-persistence/plan.md`
> Research: `context/changes/postgres-auth-crud-persistence/research.md`

## What & Why

This plan adds durable Render Postgres persistence, login-based access control, workspace ownership, saved BACKTEST configuration CRUD, and CI/E2E verification. It closes the badge gaps around auth, CRUD, persistence, user-perspective tests, and automated quality while preserving the existing deterministic BTCUSD BACKTEST dataset/export contracts.

## Starting Point

The backend already has BTCUSD BACKTEST domain schemas, deterministic dataset generation, JSONL export, and a quality adapter. The missing pieces are durable storage, authenticated user ownership, login UI, CRUD around a domain object, and CI/CD gates.

## Desired End State

A seeded/admin trader logs in, works inside their owned default workspace, manages saved BACKTEST configurations, creates draft runs, generates persisted deterministic datasets, views quality reports, and exports JSONL after backend restarts. Unauthenticated requests return `401`; cross-owned workspace/config/run/dataset/export requests return `404`.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Registration model | Closed seed/admin user | Lowest abuse risk for a public MVP and enough for the badge. | Plan |
| Session model | Server-side sessions + HttpOnly cookie | Supports logout/revocation and avoids browser token storage. | Research / Plan |
| Production cookie model | `Secure; HttpOnly; SameSite=None` with credentialed CORS | Fits the current separate Render frontend/backend origins. | Plan |
| Migrations | Manual Alembic command on Render | Keeps schema changes explicit and avoids app-start mutation. | Plan |
| CRUD object | Saved BTCUSD BACKTEST configurations | Domain-meaningful CRUD without deleting completed dataset audit trails. | Plan |
| Initial workspace | Auto-created default workspace | Lets the seeded user use the product immediately after login. | Plan |
| Dataset persistence | Metadata + full canonical records | Supports preview/export/determinism without raw provider payload risk. | Research / Plan |
| Access errors | `401` unauthenticated, `404` cross-owned resources | Protects workspace privacy and prevents resource enumeration. | Plan |
| Verification | Backend integration + frontend tests + Playwright auth/CRUD in CI | Covers the badge and the main regression risks. | Plan |

## Scope

**In scope:**

- SQLAlchemy/Alembic persistence foundation.
- Render env wiring for `DATABASE_URL`, auth secret, CORS, and session settings.
- Closed user management through a seed/admin command.
- Server-side sessions stored as token hashes in Postgres.
- Workspace ownership checks on shell, dataset, export, and quality routes.
- Postgres repositories for draft runs, dataset summaries, and canonical dataset records.
- Saved BACKTEST configuration CRUD plus draft-from-config.
- Login UI, session bootstrap, protected routes, and credentialed frontend API calls.
- GitHub Actions and one Playwright login -> config CRUD -> draft path.

**Out of scope:**

- Open signup, invite codes, reset password, external auth providers.
- Workspace CRUD UI.
- Raw provider payload persistence.
- Automatic migrations during backend startup.
- LIVE mode, broker/order execution, or investment-recommendation wording.

## Architecture / Approach

The plan keeps existing FastAPI route and repository boundaries, then swaps production storage from process-local repositories to SQLAlchemy-backed repositories. Auth is enforced in backend dependencies: current user -> owned workspace -> repository operation. The frontend only improves UX; the backend remains the source of truth for access control.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. DB Foundation and Render Wiring | SQLAlchemy, Alembic, schema, Render env/runbook | Secret handling and migration lifecycle |
| 2. Backend Auth and Session Cookies | Seed user, Argon2id hashes, sessions, login/logout/me | Cross-origin cookie and CSRF/CORS correctness |
| 3. Workspace Ownership and Persistent Runs | Postgres shell/dataset records plus protected existing routes | Breaking determinism or quality/export behavior |
| 4. Saved Backtest Configurations CRUD | Domain CRUD API and draft-from-config | Deleting configs must not delete audit history |
| 5. Frontend Auth and Config Workflow | Login UI, protected routes, config CRUD UI, credentialed fetch | Browser session handling on deployed Render origins |
| 6. Tests, E2E, CI/CD, Rollout Docs | Playwright path, GitHub Actions, verification/runbook | CI DB setup and avoiding real production secrets |

**Prerequisites:** Render backend env vars must be configured by the operator; do not paste DB URLs or passwords into chat. A CI/test Postgres URL is needed for integration and E2E gates.

**Estimated effort:** Approximately 4-6 implementation sessions across 6 phases, with manual confirmation after DB/migration, auth, persistence, CRUD, frontend, and final rollout phases.

## Open Risks & Assumptions

- The existing Render Postgres database is manually created, so `render.yaml` should not create a duplicate database unless the team intentionally adopts Blueprint-managed DB resources.
- Cross-origin cookie auth depends on exact frontend/backend origins and credentialed CORS settings.
- Render app rollback will not roll back data or migrations; schema changes need explicit migration discipline.
- Existing in-memory production data is not migrated because it was never durable.

## Success Criteria (Summary)

- A public user must log in before accessing workspace BACKTEST data.
- Saved BACKTEST configs, draft runs, completed datasets, and JSONL exports persist across backend restart/redeploy.
- CI verifies backend, frontend, and one browser-level login -> CRUD -> draft workflow without using production secrets.
