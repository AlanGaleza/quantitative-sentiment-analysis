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

Run frontend tests and build:

`npm --prefix frontend run test`

`npm --prefix frontend run build`

Local Vite development may leave `VITE_API_BASE_URL` unset; Vite proxies relative `/api` requests to FastAPI on `127.0.0.1:8000`. Deployed frontend builds must set `VITE_API_BASE_URL` to the FastAPI service origin. The API accepts cross-origin browser calls only from the comma-separated `QSA_CORS_ALLOWED_ORIGINS` list, with local Vite origins enabled by default and no wildcard production origin. The fixture provider is only for local S-04 contract/UI verification and requires both `QSA_RUNTIME_ENV=local` and `QSA_BACKTEST_QUALITY_PROVIDER=local-fixture`; default API behavior remains a 409 not-ready response until S-02 storage is integrated.

`DATABASE_URL` is required only for Postgres-backed persistence and Alembic
migrations. Do not commit database URLs, passwords, or generated exports. For
local integration tests, prefer a disposable database URL in
`QSA_TEST_DATABASE_URL` and pass it to commands as `DATABASE_URL`.

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
