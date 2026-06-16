# Postgres Auth CRUD Persistence Implementation Plan

## Overview

Implement durable Render Postgres persistence, login-based access control, workspace ownership, saved BACKTEST configuration CRUD, and CI/E2E verification for the existing BTCUSD BACKTEST workflow. The implementation must preserve the existing deterministic dataset/export contracts while replacing process-local production storage with Postgres-backed repositories.

## Current State Analysis

The application already has strong BACKTEST-only domain contracts and a working draft-run to dataset to quality workflow, but the production boundary is still unauthenticated and process-local. Render Postgres exists, but the backend does not yet use `DATABASE_URL`, does not run migrations, and does not persist workspace data across service restarts.

The current API accepts `workspace_id` path parameters and repositories key data by `(workspace_id, run_id)`, which prevents some accidental run-only reads, but it does not prove that the caller owns the workspace. The frontend also has no login route, no session bootstrap, and no `credentials: "include"` on API requests, so cookie-based auth will not work until the frontend clients are updated.

## Desired End State

After this plan is complete, a seeded/admin trader can log in through the frontend, receive an HttpOnly session cookie, land in their default workspace, create/read/update/delete saved BTCUSD BACKTEST configurations, create draft runs, generate completed deterministic datasets, view quality reports, and export JSONL from durable Postgres state. Unauthenticated requests return `401`; authenticated users attempting to access another user's workspace/config/run/dataset/export get `404`.

Render production uses `DATABASE_URL` and auth secrets stored in Render environment variables. Migrations are explicit and operator-run, not hidden in app startup. CI runs backend, frontend, and one browser-level auth plus CRUD path against a test database.

### Key Discoveries:

- `src/quantitative_sentiment_analysis/backtest_shell/repository.py:45` stores draft runs in an in-memory dict and exposes a module-level default repository at `src/quantitative_sentiment_analysis/backtest_shell/repository.py:121`.
- `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56` stores completed dataset previews and full records in memory, with full-record consistency checks that Postgres storage must preserve.
- Existing shell, dataset, export, and quality routes use FastAPI `Depends`, giving a clean place to add auth, workspace ownership, and Postgres repositories without rewriting the full orchestration path.
- `src/quantitative_sentiment_analysis/main.py:51` configures CORS without credentials and only `GET`/`POST`, which is insufficient for cookie auth plus CRUD.
- `frontend/src/features/backtestShell/api.ts:77` and related API calls omit `credentials: "include"`, so browser sessions will not be sent to the backend until the API client layer changes.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:31` sorts full records before stable JSONL serialization; Postgres natural row order must not become part of the export contract.
- `context/foundation/prd.md:64` and `context/foundation/prd.md:109` make login/workspace privacy product requirements, not only badge requirements.
- Render documentation supports passing database connection strings into services through environment variables, including Blueprint `fromDatabase` when the database is managed by the Blueprint; for the existing manually created Render DB, this plan uses Render backend env vars and does not paste secrets into chat or files.

## What We're NOT Doing

- No open registration, invite-code system, password reset flow, or external auth provider.
- No reversible password encryption; only password hashes are stored.
- No user roles beyond a single trader/admin seed account.
- No workspace CRUD UI in this change; each user gets an owned default workspace.
- No raw provider payload persistence; only metadata and canonical dataset records are stored.
- No app-start automatic schema mutation or hidden `create_all()` in production.
- No LIVE mode, broker integration, order execution, or investment-recommendation wording.
- No migration of previously process-local in-memory data; there is no durable source to migrate.

## Implementation Approach

Use SQLAlchemy 2.x and Alembic as the DB and migration foundation. Keep the existing repository protocols and add Postgres implementations behind dependency providers, so current route/orchestrator behavior stays recognizable and tests can still use overrides. Add an auth module with Argon2id password hashing, opaque server-side sessions stored as token hashes in Postgres, and FastAPI dependencies for `require_current_user` plus workspace ownership.

Saved BACKTEST configurations become the user-visible CRUD object. Existing draft runs and dataset runs remain domain artifacts, but their storage moves to Postgres and all access is checked through the current user and owned workspace.

## Critical Implementation Details

### Credentialed CORS and CSRF Boundary

Production uses separate Render frontend and backend origins, so session cookies require explicit allowed origins, `allow_credentials=True`, and frontend `credentials: "include"`. Because `SameSite=None` cookies can be sent cross-site, unsafe mutating requests should validate `Origin` against configured allowed frontend origins before accepting cookie-authenticated state changes.

### Migration Lifecycle

Alembic migrations are the schema source of truth. The app must not silently create or modify tables at startup; Render migrations are run manually from the backend service environment with `DATABASE_URL` already configured.

### Deterministic Dataset Storage

Postgres storage may persist rows in any physical order. Preview and export code must return validated `DatasetRecord` models and keep deterministic JSONL ordering through the existing stable sort key, not database insertion order.

## Phase 1: Database Foundation and Render Wiring

### Overview

Add the database/migration foundation and Render environment contract without changing user-facing behavior yet.

### Changes Required:

#### 1. Backend dependencies

**File**: `pyproject.toml`

**Intent**: Add runtime dependencies for durable Postgres access, migrations, and password hashing.

**Contract**: Add SQLAlchemy 2.x, Alembic, psycopg for PostgreSQL, and Argon2 password hashing support. Update `uv.lock` through `uv add`/`uv lock`; do not hand-edit lockfile contents.

#### 2. Database settings and session lifecycle

**File**: `src/quantitative_sentiment_analysis/persistence/database.py`

**Intent**: Provide one application-owned DB engine/session boundary that reads `DATABASE_URL` and can be overridden by tests.

**Contract**: Expose a SQLAlchemy engine/sessionmaker provider and a FastAPI dependency that yields one session per request. Missing `DATABASE_URL` should be explicit for production Postgres paths, while tests can inject a test sessionmaker. No production `create_all()` is allowed.

#### 3. SQLAlchemy models

**File**: `src/quantitative_sentiment_analysis/persistence/models.py`

**Intent**: Define the relational schema that mirrors auth, workspace, config, run, dataset summary, and dataset record contracts.

**Contract**: Model at least these tables:

- `users`: UUID primary key, normalized email unique, password hash, disabled flag, timestamps.
- `sessions`: UUID primary key, user FK, token hash unique, expiry/revocation timestamps, timestamps.
- `workspaces`: UUID primary key, unique slug used as route `workspace_id`, owner user FK, display name, timestamps.
- `backtest_configs`: UUID primary key, workspace FK, name, `BTCUSD`, `BACKTEST`, timeframe defaults, timestamps, unique config name per workspace.
- `backtest_runs`: workspace FK, run ID, nullable config FK, instrument, mode, timeframe, status, created timestamp, unique `(workspace, run_id)`.
- `dataset_runs`: workspace/run FK, status, provider, counts, model/config versions, input fingerprint, provider-limitation fields.
- `dataset_records`: workspace/run FK, optional record ID, timestamp, headline, source identity/name, instrument, mode, sentiment score, directional bias, confidence, relevance, model/config versions.

#### 4. Alembic environment and initial migration

**File**: `alembic.ini`

**Intent**: Make migrations runnable from local development, CI, and Render service shell.

**Contract**: Configure Alembic to load the app model metadata and database URL from the environment. The migration command must work as `uv run alembic upgrade head` when `DATABASE_URL` or a test DB URL is present.

**File**: `migrations/env.py`

**Intent**: Wire Alembic to the SQLAlchemy metadata without importing the ASGI app.

**Contract**: Import persistence models only, set `target_metadata`, and fail clearly when no DB URL is configured for a migration run.

**File**: `migrations/versions/<revision>_create_auth_workspace_backtest_tables.py`

**Intent**: Create the initial schema in one transactional migration.

**Contract**: Include primary keys, foreign keys, indexes needed for `(workspace, run_id)` lookups, unique email/config constraints, and numeric bounds where practical. Downgrade should drop the created tables in dependency order.

#### 5. Render and local documentation

**File**: `render.yaml`

**Intent**: Document the backend env var surface without committing secret values or accidentally requiring the user to paste a DB URL into chat.

**Contract**: Add backend env keys for `DATABASE_URL` as `sync: false`, `AUTH_SECRET` as generated or dashboard-managed, and session/CORS settings as needed. Because the Render Postgres database already exists, do not add a Blueprint `databases:` block unless the implementation deliberately adopts the existing DB into the Blueprint.

**File**: `README.md`

**Intent**: Give the operator a safe Render setup and migration runbook.

**Contract**: Document that `DATABASE_URL` is set in the Render backend service from the existing Render Postgres Internal Database URL, `AUTH_SECRET` is generated/stored in Render, and migrations are run manually from the backend service environment. Do not include real hostnames, passwords, or URLs.

### Success Criteria:

#### Automated Verification:

- Dependencies install from the lockfile: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv UV_LINK_MODE=copy uv sync --locked --dev`
- Alembic migration applies to a test Postgres database: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run alembic upgrade head`
- Persistence module tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/persistence -p no:cacheprovider`
- Backend imports still compile: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run python -m compileall src`

#### Manual Verification:

- Render backend has `DATABASE_URL`, `AUTH_SECRET`, and session/CORS env vars configured without exposing values in git or chat.
- Manual Render migration command runs against the Render backend service environment and reports Alembic at `head`.
- `/health` still returns OK after migration and redeploy.

**Implementation Note**: Pause after this phase for human confirmation that Render env vars and the manual migration path are correct before implementing auth on top of the schema.

---

## Phase 2: Backend Auth and Session Cookies

### Overview

Add closed user management, password verification, server-side sessions, session cookies, auth endpoints, and backend dependencies.

### Changes Required:

#### 1. Auth schemas and security helpers

**File**: `src/quantitative_sentiment_analysis/auth/schemas.py`

**Intent**: Define stable request/response contracts for login and current-user bootstrap.

**Contract**: Include `LoginRequest`, `CurrentUser`, `CurrentWorkspace`, and `AuthSessionResponse` models. Responses may include owned workspaces and the default workspace slug, but must not expose password hashes or raw session tokens.

**File**: `src/quantitative_sentiment_analysis/auth/security.py`

**Intent**: Centralize password hashing, session token generation, token hashing, cookie settings, and auth errors.

**Contract**: Hash passwords with Argon2id. Generate opaque high-entropy session tokens, store only a hash/HMAC digest in Postgres, and set cookies as HttpOnly. Production cookies must support `Secure; SameSite=None`; local development may opt into non-secure cookies through explicit env configuration.

#### 2. Auth repository

**File**: `src/quantitative_sentiment_analysis/auth/repository.py`

**Intent**: Encapsulate user/session/workspace DB reads and writes.

**Contract**: Provide methods to find a user by normalized email, verify active users, create/revoke sessions, resolve a current user from a cookie token, and load owned workspaces. Expired or revoked sessions must not authenticate.

#### 3. Auth router

**File**: `src/quantitative_sentiment_analysis/auth/router.py`

**Intent**: Add the browser-facing auth API.

**Contract**: Add:

- `POST /api/auth/login`: accepts email/password JSON, verifies credentials, creates a server-side session, sets session cookie, returns current user and workspaces.
- `POST /api/auth/logout`: revokes the current session when present and clears the cookie.
- `GET /api/auth/me`: returns current user and workspaces or `401`.

Invalid credentials return `401` with a generic message.

#### 4. Current-user and workspace dependencies

**File**: `src/quantitative_sentiment_analysis/auth/dependencies.py`

**Intent**: Give routes a reusable backend-enforced auth boundary.

**Contract**: Add `require_current_user` and `require_owned_workspace(workspace_id)` style dependencies. No route may rely on frontend-only route protection for workspace privacy.

#### 5. Seed/admin user command

**File**: `src/quantitative_sentiment_analysis/auth/seed_user.py`

**Intent**: Support the selected closed-registration model without a public signup route.

**Contract**: Provide a module command such as `uv run python -m quantitative_sentiment_analysis.auth.seed_user` that reads email/password/default workspace from environment variables, hashes the password, creates or updates the user safely, and auto-creates the default workspace when absent. Passwords must not be accepted through command-line arguments that can end up in shell history.

#### 6. App wiring and CORS credentials

**File**: `src/quantitative_sentiment_analysis/main.py`

**Intent**: Include auth routes and make browser cookie sessions work across the deployed Render frontend/backend origins.

**Contract**: Include the auth router. Configure CORS with explicit origins, explicit methods including CRUD methods, explicit headers, and `allow_credentials=True`. Add or call an Origin guard for unsafe cookie-authenticated requests.

### Success Criteria:

#### Automated Verification:

- Auth unit tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/auth/test_security.py tests/auth/test_schemas.py -p no:cacheprovider`
- Auth integration tests pass against a migrated test DB: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/auth/test_router.py -p no:cacheprovider`
- CORS credential tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/test_main.py -p no:cacheprovider`
- Existing unauthenticated route tests are updated or explicitly overridden and still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_shell tests/backtest_dataset tests/backtest_quality -p no:cacheprovider`

#### Manual Verification:

- Seed command creates the initial user and default workspace without printing the password.
- Login from the deployed frontend origin sets an HttpOnly session cookie.
- Logout revokes the session; a new `/api/auth/me` request returns `401`.
- Browser devtools show production cookie attributes as `Secure`, `HttpOnly`, and `SameSite=None`.

**Implementation Note**: Pause after this phase for manual login/logout confirmation before protecting the existing BACKTEST workflow routes.

---

## Phase 3: Workspace Ownership and Persistent Existing Runs

### Overview

Move draft runs, completed dataset runs, dataset records, export, and quality inputs to Postgres-backed storage with backend-enforced workspace ownership.

### Changes Required:

#### 1. Persistent draft-run repository

**File**: `src/quantitative_sentiment_analysis/backtest_shell/repository.py`

**Intent**: Keep the current repository protocol while adding a durable implementation for production.

**Contract**: Add a Postgres-backed repository that creates and reads `BacktestRunShell` rows by owned workspace slug plus run ID. Preserve BTCUSD/BACKTEST/timeframe validation through existing schemas. Keep the in-memory implementation available for focused tests and explicit local/dev overrides.

#### 2. Persistent completed-dataset repository

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py`

**Intent**: Persist completed dataset summaries and full canonical records in Postgres.

**Contract**: Add a Postgres-backed `CompletedDatasetRepository` implementation whose `save_run`, `get_run`, and `list_records` methods return the same Pydantic models as the in-memory repository. `save_run` must be atomic for summary plus records. Provider-limited runs store a terminal summary with no records. Full-record count/relevance/source/workspace checks must remain enforced.

#### 3. Repository dependency providers

**File**: `src/quantitative_sentiment_analysis/backtest_shell/repository.py`

**Intent**: Route production requests to Postgres without breaking dependency override tests.

**Contract**: Update `get_backtest_shell_repository` to return the Postgres implementation when a DB session is available in app dependencies. Existing tests can override this provider directly.

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py`

**Intent**: Route dataset storage through Postgres in production.

**Contract**: Update `get_completed_dataset_repository` to use the request DB session and keep dependency override support.

#### 4. Route ownership enforcement

**File**: `src/quantitative_sentiment_analysis/backtest_shell/router.py`

**Intent**: Require a logged-in owner before creating or reading draft runs.

**Contract**: Add current-user/workspace dependencies. Create and read routes return `401` without a valid session and `404` for workspace slugs not owned by the current user.

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/router.py`

**Intent**: Protect dataset generation, preview, and JSONL export.

**Contract**: Add the same ownership dependency to dataset run, preview, and export routes. `run_id` alone must never authorize access. Provider limitation responses keep their existing `409` preview payload behavior.

**File**: `src/quantitative_sentiment_analysis/backtest_quality/router.py`

**Intent**: Protect quality reports and remove the false S-02-not-ready production behavior once completed dataset storage exists.

**Contract**: Add workspace ownership dependency. Quality route reads completed dataset records through the Postgres repository by default. Missing price movement remains an explicit quality warning, not fabricated movement data.

#### 5. Quality input provider compatibility

**File**: `src/quantitative_sentiment_analysis/backtest_quality/repository.py`

**Intent**: Keep quality input mapping compatible with persisted completed datasets.

**Contract**: `CompletedDatasetQualityInputProvider` must work with the Postgres completed dataset repository and continue mapping canonical `timestamp` to quality `event_timestamp`, with `later_return` and `realized_direction` missing until price enrichment exists.

#### 6. Stable export behavior

**File**: `src/quantitative_sentiment_analysis/backtest_dataset/export.py`

**Intent**: Preserve byte-stable JSONL exports after records move to Postgres.

**Contract**: Keep sorting by the documented stable key before serialization. Do not use database physical order or insertion order as the export contract.

### Success Criteria:

#### Automated Verification:

- Postgres shell repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_shell/test_postgres_repository.py -p no:cacheprovider`
- Postgres dataset repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_dataset/test_postgres_repository.py -p no:cacheprovider`
- Authenticated shell/dataset/export route tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_shell/test_router.py tests/backtest_dataset/test_router.py -p no:cacheprovider`
- Quality route reads persisted completed datasets: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_quality/test_router.py tests/backtest_quality/test_dataset_adapter.py -p no:cacheprovider`
- JSONL determinism still passes after Postgres persistence: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_dataset/test_export.py tests/backtest_dataset/test_determinism.py tests/contracts/test_serialization.py -p no:cacheprovider`

#### Manual Verification:

- A logged-in user can create a draft run, generate a dataset, refresh the browser, and still fetch the run/dataset from Postgres.
- The quality route no longer shows an S-02 unavailable message for a completed deterministic dataset.
- Manually changing the URL to another workspace slug returns not found behavior instead of showing data.
- JSONL export downloaded before and after a backend restart is byte-identical for the same completed run.

**Implementation Note**: Pause after this phase for manual confirmation that the existing BACKTEST workflow survives backend restart and ownership checks.

---

## Phase 4: Saved Backtest Configurations CRUD

### Overview

Add the user-visible CRUD object required by the badge: saved BTCUSD BACKTEST configurations owned by a workspace.

### Changes Required:

#### 1. Config schemas

**File**: `src/quantitative_sentiment_analysis/backtest_configs/schemas.py`

**Intent**: Define the API contract for saved BACKTEST configurations.

**Contract**: Add request/response models for create, update, list item, detail, and draft creation from config. Fields include config ID, workspace ID, name, instrument `BTCUSD`, mode `BACKTEST`, timeframe start/end, created timestamp, and updated timestamp. Timeframe validation must match the existing 30-day aware timestamp rules.

#### 2. Config repository

**File**: `src/quantitative_sentiment_analysis/backtest_configs/repository.py`

**Intent**: Encapsulate config CRUD and ownership-safe lookup.

**Contract**: Provide create/list/get/update/delete methods scoped by owned workspace. Config names are unique per workspace. Delete removes the saved config only; historical backtest runs and dataset runs remain auditable.

#### 3. Config router

**File**: `src/quantitative_sentiment_analysis/backtest_configs/router.py`

**Intent**: Add REST endpoints for the saved-config workflow.

**Contract**: Add:

- `POST /api/workspaces/{workspace_id}/backtest-configs`
- `GET /api/workspaces/{workspace_id}/backtest-configs`
- `GET /api/workspaces/{workspace_id}/backtest-configs/{config_id}`
- `PUT /api/workspaces/{workspace_id}/backtest-configs/{config_id}`
- `DELETE /api/workspaces/{workspace_id}/backtest-configs/{config_id}`
- `POST /api/workspaces/{workspace_id}/backtest-configs/{config_id}/drafts`

All routes require the current user to own the workspace. Missing auth returns `401`; missing/cross-owned configs return `404`.

#### 4. Draft-run linkage

**File**: `src/quantitative_sentiment_analysis/backtest_shell/repository.py`

**Intent**: Let a saved config create a durable draft run without duplicating shell logic.

**Contract**: Add a repository method or service boundary that creates `BacktestRunShell` from a validated config and records nullable `config_id` in `backtest_runs`. Deleting a config must not delete the draft/completed run audit trail.

#### 5. App wiring

**File**: `src/quantitative_sentiment_analysis/main.py`

**Intent**: Include the config router.

**Contract**: Config routes are available under `/api/workspaces/{workspace_id}/backtest-configs` and participate in the same CORS/auth/Origin checks as other mutating routes.

### Success Criteria:

#### Automated Verification:

- Config schema tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_schemas.py -p no:cacheprovider`
- Config repository CRUD tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_repository.py -p no:cacheprovider`
- Config API ownership tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_router.py -p no:cacheprovider`
- Draft-from-config route creates a normal durable draft run: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_draft_from_config.py -p no:cacheprovider`
- Backend regression suite passes: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest -p no:cacheprovider`

#### Manual Verification:

- A logged-in user can create, view, edit, and delete a saved BTCUSD BACKTEST configuration.
- Creating a draft from a saved config produces the same shell UX and dataset workflow as direct draft creation.
- Deleting a saved config does not delete already-created runs, datasets, or exports.
- Cross-workspace config URLs return not found.

**Implementation Note**: Pause after this phase for manual CRUD confirmation before building the frontend workflow around these APIs.

---

## Phase 5: Frontend Auth and Config Workflow

### Overview

Add login/session bootstrap and a saved-config CRUD workflow to the Vite frontend, while preserving the existing shell, dataset, quality, and JSONL user path.

### Changes Required:

#### 1. Auth API client

**File**: `frontend/src/features/auth/api.ts`

**Intent**: Provide typed frontend calls for login, logout, and current-user bootstrap.

**Contract**: All auth requests use the configured API base URL and `credentials: "include"`. Login posts JSON credentials; logout clears session state after the backend clears the cookie; `me` loads the current user/default workspace.

**File**: `frontend/src/features/auth/types.ts`

**Intent**: Mirror backend auth response types.

**Contract**: Include current user, workspace list, default workspace slug, and auth error shape. Do not model or store raw session tokens.

#### 2. Shared authenticated fetch behavior

**File**: `frontend/src/features/backtestShell/api.ts`

**Intent**: Ensure existing shell/dataset/export calls send the session cookie and handle empty/non-JSON responses safely.

**Contract**: Add `credentials: "include"` to all API calls. Preserve existing typed `BacktestShellApiError` behavior and avoid calling `response.json()` blindly on empty responses.

**File**: `frontend/src/features/backtestQuality/api.ts`

**Intent**: Send auth cookies for quality reports.

**Contract**: Add `credentials: "include"` and keep existing quality error semantics.

#### 3. App routing and auth state

**File**: `frontend/src/App.tsx`

**Intent**: Add routes and state for login, config list/detail workflow, existing shell route, and quality route.

**Contract**: Support at least `/login`, `/workspaces/{workspace_id}/backtest-configs`, `/workspaces/{workspace_id}/backtests/new`, and `/workspaces/{workspace_id}/backtests/{run_id}/quality`. Protected routes wait for `/api/auth/me`; unauthenticated users see login; authenticated users are not blocked by frontend-only checks if the backend rejects access.

#### 4. Login view

**File**: `frontend/src/features/auth/LoginPage.tsx`

**Intent**: Provide the required access-control UI for the public deployed app.

**Contract**: Form fields use accessible labels and submit through the auth API. Invalid credentials show a generic alert. On success, navigate to the default workspace config list or shell entry route.

#### 5. Config CRUD UI

**File**: `frontend/src/features/backtestConfigs/api.ts`

**Intent**: Provide typed calls for config CRUD and draft-from-config.

**Contract**: Build URLs under `/api/workspaces/{workspace_id}/backtest-configs`, use `credentials: "include"`, and handle `401`/`404`/validation errors deterministically.

**File**: `frontend/src/features/backtestConfigs/BacktestConfigPage.tsx`

**Intent**: Let the user create, read, update, and delete saved BACKTEST configurations from the browser.

**Contract**: Use accessible controls (`getByRole`-friendly labels/buttons), timezone-aware timeframe fields, and existing BTCUSD/BACKTEST/30-day validation language. Deleting a config requires an explicit user action and updates the visible list.

#### 6. Shell workflow integration

**File**: `frontend/src/features/backtestShell/BacktestShellPage.tsx`

**Intent**: Keep direct draft creation working and remove stale local-storage wording.

**Contract**: Replace `Storage: Local draft` with durable/session-aware copy such as Postgres-backed workspace storage. Optionally allow the shell route to receive a config-created run, but do not make config CRUD a prerequisite for direct draft creation.

#### 7. Styles and frontend docs

**File**: `frontend/src/styles.css`

**Intent**: Add restrained operational UI styles for login and config management consistent with the current tool UI.

**Contract**: Do not introduce marketing landing pages or advisory trading wording. Text must fit on mobile and desktop.

**File**: `frontend/.env.example`

**Intent**: Document frontend API origin expectations.

**Contract**: Keep `VITE_API_BASE_URL` as the public frontend value; do not add backend secrets to Vite env.

### Success Criteria:

#### Automated Verification:

- Auth API client tests pass: `npm --prefix frontend run test -- src/features/auth`
- Config API and component tests pass: `npm --prefix frontend run test -- src/features/backtestConfigs`
- Existing shell and quality tests pass with credentialed fetch expectations: `npm --prefix frontend run test -- src/features/backtestShell src/features/backtestQuality`
- App routing/auth bootstrap tests pass: `npm --prefix frontend run test -- src/App.test.ts`
- Frontend typecheck and build pass: `npm --prefix frontend run build`

#### Manual Verification:

- Public deployed frontend shows login before protected workspace routes.
- Logging in navigates to the user's default workspace and shows saved BACKTEST configurations.
- The browser workflow can create/update/delete a config, create a draft run, run a dataset, open quality, and download JSONL.
- Refreshing the page keeps the user logged in until logout/session expiry.
- UI copy remains BACKTEST-only analytical wording and does not present outputs as executable trading signals.

**Implementation Note**: Pause after this phase for manual browser verification before locking the flow into E2E and CI.

---

## Phase 6: Tests, E2E, CI/CD, and Rollout Docs

### Overview

Make the badge requirements verifiable: backend tests, frontend tests, one user-perspective Playwright test, and GitHub Actions quality gates.

### Changes Required:

#### 1. Playwright auth plus CRUD test

**File**: `tests/e2e/auth-crud.spec.ts`

**Intent**: Add one browser-level test that verifies the highest-risk user path instead of only mocked UI behavior.

**Contract**: Test name references the access-control/CRUD risk. Use unique identifiers in config names, `getByRole`/`getByLabel` selectors, waits for state/responses rather than timeouts, and cleanup by deleting the created config and logging out. Path: login -> create config -> update config -> create draft run from config -> delete config.

#### 2. Playwright server configuration

**File**: `playwright.config.ts`

**Intent**: Support E2E against both frontend and backend in CI.

**Contract**: Use Playwright's multiple `webServer` entries: one for FastAPI and one for Vite. Keep `baseURL` pointed at the frontend. CI should run with one worker and a migrated test DB. Do not use `storageState` for this app yet because login is part of the required user-perspective test.

#### 3. GitHub Actions workflow

**File**: `.github/workflows/ci.yml`

**Intent**: Add automated build and quality verification.

**Contract**: Include jobs for:

- backend: install with uv, run Alembic against a Postgres service, run ruff/pyright/pytest;
- frontend: `npm --prefix frontend ci`, tests, typecheck/build;
- e2e: start backend and frontend through Playwright config against the CI Postgres service, seed the test user via env-only seed command, run `npm run e2e`.

No real Render, Sharpe, or production DB secrets are required in CI.

#### 4. README and rollout checklist

**File**: `README.md`

**Intent**: Document the finished local, CI, and Render operator path.

**Contract**: Add commands for local migration, seed user, auth smoke checks, frontend env, E2E, and Render deployment. Clarify that `SHARPE_API_KEY` is separate from DB/auth setup and remains a backend secret.

**File**: `context/changes/postgres-auth-crud-persistence/rollout.md`

**Intent**: Leave a concise implementation-era checklist for Render.

**Contract**: Include env var checklist, manual migration command, seed-user command, post-deploy smoke steps, rollback notes, and secret handling rules. Do not include secret values.

#### 5. Full verification pass

**File**: `context/changes/postgres-auth-crud-persistence/verification.md`

**Intent**: Record the final commands and manual checks after implementation.

**Contract**: Capture command results for backend, frontend, E2E, migration, and deployment smoke checks. Mention any skipped real-provider checks explicitly.

### Success Criteria:

#### Automated Verification:

- Backend CI-equivalent gate passes locally or in CI: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest -p no:cacheprovider`
- Backend lint/type gates pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run ruff check .` and `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pyright`
- Frontend CI-equivalent gate passes: `npm --prefix frontend ci && npm --prefix frontend run test && npm --prefix frontend run build`
- Playwright E2E passes: `npm run e2e`
- GitHub Actions workflow passes on the branch/PR.

#### Manual Verification:

- Render production deployment has migrated schema and seeded user.
- Public URL supports login -> config CRUD -> draft run -> deterministic dataset -> quality route -> JSONL export.
- Backend restart or Render redeploy does not lose draft runs, configs, completed datasets, or exports.
- Cross-workspace URL tampering returns `404`; unauthenticated protected routes return `401`.
- Final verification notes are saved without secrets.

**Implementation Note**: After this phase passes, the change is ready for implementation review and normal commit/archive workflow.

---

## Testing Strategy

### Unit Tests:

- Password hashing, session token hashing, cookie settings, and expiry/revocation behavior.
- Pydantic schema validation for auth, configs, draft runs, dataset summaries, and dataset records.
- Stable JSONL serialization remains unchanged for canonical `DatasetRecord` rows.

### Integration Tests:

- Alembic migration applies to a clean Postgres test database.
- Auth login/logout/me work against Postgres-backed users and sessions.
- Every storage/API/export/quality route requires a matching logged-in user and owned workspace.
- Config CRUD is scoped to the owner workspace and returns `404` for cross-owned IDs.
- Dataset summary plus full records persist atomically and remain exportable after repository re-instantiation.

### Manual Testing Steps:

1. Configure Render backend `DATABASE_URL`, `AUTH_SECRET`, CORS, cookie, and Sharpe env vars without exposing values.
2. Run Alembic migration from the Render backend service environment.
3. Run the seed-user command from the Render backend service environment.
4. Open the public frontend URL and log in.
5. Create, update, and delete a saved BTCUSD BACKTEST configuration.
6. Create a draft run, run deterministic dataset generation, open quality, and download JSONL.
7. Restart/redeploy backend and confirm persisted data remains available.
8. Attempt unauthenticated and cross-workspace requests and confirm `401`/`404` behavior.

## Performance Considerations

The MVP target is small scale, but dataset records can grow for 30-day news windows. Index `(workspace_id, run_id)` on runs, dataset summaries, and records. Keep preview bounded by `MAX_DATASET_PREVIEW_RECORDS`; quality responses should remain bounded according to `context/foundation/quality-contracts.md`. JSONL export can stream later if needed, but this plan keeps existing bytes response behavior unless large exports become a measured issue.

## Migration Notes

This is a no-data migration from in-memory production state to durable Postgres. There is no reliable previous production data source to migrate. Rollback of application code does not roll back data; any future destructive migration needs its own rollback note. Phase 1's initial migration is additive from the current repository perspective.

## References

- Research: `context/changes/postgres-auth-crud-persistence/research.md`
- Product auth/workspace requirement: `context/foundation/prd.md:64`, `context/foundation/prd.md:109`
- Workspace and JSONL contracts: `context/foundation/quality-contracts.md:57`, `context/foundation/quality-contracts.md:98`, `context/foundation/quality-contracts.md:133`
- Current CORS setup: `src/quantitative_sentiment_analysis/main.py:51`
- Current shell repository: `src/quantitative_sentiment_analysis/backtest_shell/repository.py:45`
- Current completed dataset repository: `src/quantitative_sentiment_analysis/backtest_dataset/repository.py:56`
- Current stable export sort: `src/quantitative_sentiment_analysis/backtest_dataset/export.py:31`
- Current frontend fetch layer: `frontend/src/features/backtestShell/api.ts:77`
- E2E seed conventions: `tests/e2e/seed.spec.ts:8`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Database Foundation and Render Wiring

#### Automated

- [x] 1.1 Dependencies install from the lockfile: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv UV_LINK_MODE=copy uv sync --locked --dev` — ae7f549
- [x] 1.2 Alembic migration applies to a test Postgres database: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run alembic upgrade head` — ae7f549
- [x] 1.3 Persistence module tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/persistence -p no:cacheprovider` — ae7f549
- [x] 1.4 Backend imports still compile: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run python -m compileall src` — ae7f549

#### Manual

- [x] 1.5 Render backend has `DATABASE_URL`, `AUTH_SECRET`, and session/CORS env vars configured without exposing values in git or chat. — ae7f549
- [x] 1.6 Manual Render migration command runs against the Render backend service environment and reports Alembic at `head`. — ae7f549
- [x] 1.7 `/health` still returns OK after migration and redeploy. — ae7f549

### Phase 2: Backend Auth and Session Cookies

#### Automated

- [x] 2.1 Auth unit tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/auth/test_security.py tests/auth/test_schemas.py -p no:cacheprovider` — c9fb325
- [x] 2.2 Auth integration tests pass against a migrated test DB: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/auth/test_router.py -p no:cacheprovider` — c9fb325
- [x] 2.3 CORS credential tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/test_main.py -p no:cacheprovider` — c9fb325
- [x] 2.4 Existing unauthenticated route tests are updated or explicitly overridden and still pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_shell tests/backtest_dataset tests/backtest_quality -p no:cacheprovider` — c9fb325

#### Manual

- [x] 2.5 Seed command creates the initial user and default workspace without printing the password. — c9fb325
- [x] 2.6 Login from the deployed frontend origin sets an HttpOnly session cookie. — c9fb325
- [x] 2.7 Logout revokes the session; a new `/api/auth/me` request returns `401`. — c9fb325
- [x] 2.8 Browser devtools show production cookie attributes as `Secure`, `HttpOnly`, and `SameSite=None`. — c9fb325

### Phase 3: Workspace Ownership and Persistent Existing Runs

#### Automated

- [x] 3.1 Postgres shell repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_shell/test_postgres_repository.py -p no:cacheprovider` — 8562a24
- [x] 3.2 Postgres dataset repository tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_dataset/test_postgres_repository.py -p no:cacheprovider` — 8562a24
- [x] 3.3 Authenticated shell/dataset/export route tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_shell/test_router.py tests/backtest_dataset/test_router.py -p no:cacheprovider` — 8562a24
- [x] 3.4 Quality route reads persisted completed datasets: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_quality/test_router.py tests/backtest_quality/test_dataset_adapter.py -p no:cacheprovider` — 8562a24
- [x] 3.5 JSONL determinism still passes after Postgres persistence: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_dataset/test_export.py tests/backtest_dataset/test_determinism.py tests/contracts/test_serialization.py -p no:cacheprovider` — 8562a24

#### Manual

- [x] 3.6 A logged-in user can create a draft run, generate a dataset, refresh the browser, and still fetch the run/dataset from Postgres. — 8562a24
- [x] 3.7 The quality route no longer shows an S-02 unavailable message for a completed deterministic dataset. — 8562a24
- [x] 3.8 Manually changing the URL to another workspace slug returns not found behavior instead of showing data. — 8562a24
- [x] 3.9 JSONL export downloaded before and after a backend restart is byte-identical for the same completed run. — 8562a24

### Phase 4: Saved Backtest Configurations CRUD

#### Automated

- [x] 4.1 Config schema tests pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_schemas.py -p no:cacheprovider` — dc3c972
- [x] 4.2 Config repository CRUD tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_repository.py -p no:cacheprovider` — dc3c972
- [x] 4.3 Config API ownership tests pass: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_router.py -p no:cacheprovider` — dc3c972
- [x] 4.4 Draft-from-config route creates a normal durable draft run: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest tests/backtest_configs/test_draft_from_config.py -p no:cacheprovider` — dc3c972
- [x] 4.5 Backend regression suite passes: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest -p no:cacheprovider` — dc3c972

#### Manual

- [x] 4.6 A logged-in user can create, view, edit, and delete a saved BTCUSD BACKTEST configuration. — dc3c972
- [x] 4.7 Creating a draft from a saved config produces the same shell UX and dataset workflow as direct draft creation. — dc3c972
- [x] 4.8 Deleting a saved config does not delete already-created runs, datasets, or exports. — dc3c972
- [x] 4.9 Cross-workspace config URLs return not found. — dc3c972

### Phase 5: Frontend Auth and Config Workflow

#### Automated

- [x] 5.1 Auth API client tests pass: `npm --prefix frontend run test -- src/features/auth` — a8be700
- [x] 5.2 Config API and component tests pass: `npm --prefix frontend run test -- src/features/backtestConfigs` — a8be700
- [x] 5.3 Existing shell and quality tests pass with credentialed fetch expectations: `npm --prefix frontend run test -- src/features/backtestShell src/features/backtestQuality` — a8be700
- [x] 5.4 App routing/auth bootstrap tests pass: `npm --prefix frontend run test -- src/App.test.ts` — a8be700
- [x] 5.5 Frontend typecheck and build pass: `npm --prefix frontend run build` — a8be700

#### Manual

- [x] 5.6 Public deployed frontend shows login before protected workspace routes. — a8be700
- [x] 5.7 Logging in navigates to the user's default workspace and shows saved BACKTEST configurations. — a8be700
- [x] 5.8 The browser workflow can create/update/delete a config, create a draft run, run a dataset, open quality, and download JSONL. — a8be700
- [x] 5.9 Refreshing the page keeps the user logged in until logout/session expiry. — a8be700
- [x] 5.10 UI copy remains BACKTEST-only analytical wording and does not present outputs as executable trading signals. — a8be700

### Phase 6: Tests, E2E, CI/CD, and Rollout Docs

#### Automated

- [x] 6.1 Backend CI-equivalent gate passes locally or in CI: `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest -p no:cacheprovider`
- [x] 6.2 Backend lint/type gates pass: `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run ruff check .` and `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pyright`
- [x] 6.3 Frontend CI-equivalent gate passes: `npm --prefix frontend ci && npm --prefix frontend run test && npm --prefix frontend run build`
- [x] 6.4 Playwright E2E passes: `npm run e2e`
- [ ] 6.5 GitHub Actions workflow passes on the branch/PR.

#### Manual

- [ ] 6.6 Render production deployment has migrated schema and seeded user.
- [ ] 6.7 Public URL supports login -> config CRUD -> draft run -> deterministic dataset -> quality route -> JSONL export.
- [ ] 6.8 Backend restart or Render redeploy does not lose draft runs, configs, completed datasets, or exports.
- [ ] 6.9 Cross-workspace URL tampering returns `404`; unauthenticated protected routes return `401`.
- [ ] 6.10 Final verification notes are saved without secrets.
