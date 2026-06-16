# Quantitative Sentiment Analysis

FastAPI service for deterministic BTCUSD BACKTEST sentiment datasets.

## Local Development

Install locked backend dependencies:

`uv sync --locked`

On WSL projects mounted under `/mnt/e`, use an external Linux venv for backend install and `uv run` commands if `.venv` copy operations fail:

`UV_PROJECT_ENVIRONMENT=/tmp/qsa-render-venv UV_LINK_MODE=copy uv sync --locked --dev`

Then prefix backend `uv run ...` commands with the same `UV_PROJECT_ENVIRONMENT=/tmp/qsa-render-venv`.

Install locked frontend dependencies:

`npm --prefix frontend ci`

Run the API locally:

`uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`

Run the API with deterministic local fixture data for the S-04 quality view:

`QSA_RUNTIME_ENV=local QSA_BACKTEST_QUALITY_PROVIDER=local-fixture uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`

Run the Vite frontend locally:

`npm --prefix frontend run dev`

With the local fixture provider enabled, open a run-scoped quality path such as:

`http://127.0.0.1:5173/workspaces/workspace-alpha/backtests/run-001/quality`

Verify the deployment smoke endpoint:

`curl -fsS http://127.0.0.1:8000/health`

Run backend tests:

`uv run pytest`

Run database migrations against a configured local or test database:

`DATABASE_URL="<postgresql connection string>" uv run alembic upgrade head`

Seed or update the closed-registration workspace user from environment variables:

```bash
export DATABASE_URL="<postgresql connection string>"
export AUTH_SECRET="<at least 32 random characters>"
export QSA_SEED_USER_EMAIL="trader@example.test"
export QSA_SEED_USER_PASSWORD="<operator supplied password>"
export QSA_SEED_WORKSPACE_SLUG="demo-workspace"
export QSA_SEED_WORKSPACE_NAME="Demo Workspace"
uv run python -m quantitative_sentiment_analysis.auth.seed_user
```

For local HTTP browser testing, set `QSA_SESSION_COOKIE_SECURE=false` only in
the local shell. Production cookies should remain `Secure` with `SameSite=None`.

Smoke auth locally after seeding:

```bash
curl -i -c /tmp/qsa-cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"email":"trader@example.test","password":"<password>"}' \
  http://127.0.0.1:8000/api/auth/login

curl -i -b /tmp/qsa-cookies.txt http://127.0.0.1:8000/api/auth/me
```

Run frontend tests and build:

`npm --prefix frontend run test`

`npm --prefix frontend run build`

Run browser-level E2E against FastAPI, Vite, and a migrated test database:

```bash
export DATABASE_URL="${QSA_TEST_DATABASE_URL}"
export AUTH_SECRET="local-e2e-auth-secret-with-at-least-32-characters"
export QSA_SESSION_COOKIE_SECURE=false
npm ci
npm run e2e
```

Local Vite development may leave `VITE_API_BASE_URL` unset; Vite proxies relative `/api` requests to FastAPI on `127.0.0.1:8000`. Deployed frontend builds must set `VITE_API_BASE_URL` to the FastAPI service origin. The API accepts cross-origin browser calls only from the comma-separated `QSA_CORS_ALLOWED_ORIGINS` list, with local Vite origins enabled by default and no wildcard production origin. The fixture provider is only for local S-04 contract/UI verification and requires both `QSA_RUNTIME_ENV=local` and `QSA_BACKTEST_QUALITY_PROVIDER=local-fixture`; default quality behavior reads completed datasets from Postgres, with movement fields pending price enrichment.

`DATABASE_URL` is required only for Postgres-backed persistence and Alembic
migrations. Do not commit database URLs, passwords, or generated exports. For
local integration tests, prefer a disposable database URL in
`QSA_TEST_DATABASE_URL` and pass it to commands as `DATABASE_URL`.

`SHARPE_API_KEY` is separate from DB/auth setup. Store it only as a backend
secret when running real Sharpe Terminal BACKTEST smoke checks; CI and E2E do
not require it.

## CI/CD

`.github/workflows/ci.yml` runs three automated gates:

- backend: install with uv, migrate a PostgreSQL service database, run ruff,
  pyright, and pytest;
- frontend: `npm --prefix frontend ci`, Vitest, and Vite build;
- E2E: install backend/frontend dependencies, install Chromium, then run
  Playwright against FastAPI plus Vite with an env-seeded test user.

## Render Deployment

`render.yaml` defines two services:

- API web service:
  - runtime: Python
  - plan: free
  - region: Frankfurt
  - build: `uv sync --locked --no-dev`
  - start: `uv run --no-dev uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`
  - health check: `/health`
  - configure `DATABASE_URL` from the existing Render Postgres Internal Database URL
  - configure `AUTH_SECRET` as a generated Render secret
  - configure `QSA_CORS_ALLOWED_ORIGINS` to the deployed frontend origin
- Frontend static site:
  - root directory: `frontend`
  - build: `npm ci && npm run build`
  - publish path: `dist`
  - SPA rewrite: `/*` to `/index.html`
  - configure `VITE_API_BASE_URL` to the deployed API origin

Create the first Render service from the GitHub repository Blueprint after pushing these files to `main`.

Render Postgres migrations are manual operator actions. After `DATABASE_URL` is
configured on the backend service, run `uv run alembic upgrade head` from the
backend service environment or an equivalent Render shell/job that already has
the backend environment variables loaded. Do not paste the Internal Database URL
into chat or commit it to the repository.

After migrations, seed the first user from the Render backend service
environment:

```bash
QSA_SEED_USER_EMAIL="<admin email>" \
QSA_SEED_USER_PASSWORD="<admin password>" \
QSA_SEED_WORKSPACE_SLUG="demo-workspace" \
QSA_SEED_WORKSPACE_NAME="Demo Workspace" \
uv run python -m quantitative_sentiment_analysis.auth.seed_user
```

Post-deploy smoke path:

1. Open the public frontend URL.
2. Confirm protected workspace routes show login before authentication.
3. Log in, create/update/delete a saved BTCUSD BACKTEST configuration.
4. Create a draft run, run the deterministic dataset, open quality, and
   download JSONL.
5. Redeploy or restart the backend and confirm persisted configs/runs/datasets
   remain available.
6. Try an unauthenticated protected request and a different workspace slug; the
   expected behavior is `401` or not-found access.
