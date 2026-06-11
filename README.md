# Quantitative Sentiment Analysis

FastAPI service for deterministic BTCUSD BACKTEST sentiment datasets.

## Local Development

Install locked backend dependencies:

`uv sync --locked`

On WSL projects mounted under `/mnt/e`, use an external Linux venv if `.venv` copy operations fail:

`UV_PROJECT_ENVIRONMENT=/tmp/qsa-render-venv UV_LINK_MODE=copy uv sync --locked`

Install locked frontend dependencies:

`npm --prefix frontend ci`

Run the API locally:

`uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`

Run the Vite frontend locally:

`npm --prefix frontend run dev`

Open a run-scoped quality path such as:

`http://127.0.0.1:5173/workspaces/workspace-alpha/backtests/run-001/quality`

Verify the deployment smoke endpoint:

`curl -fsS http://127.0.0.1:8000/health`

Run backend tests:

`uv run pytest`

Run frontend tests and build:

`npm --prefix frontend run test`

`npm --prefix frontend run build`

Local Vite development may leave `VITE_API_BASE_URL` unset; Vite proxies relative `/api` requests to FastAPI on `127.0.0.1:8000`. Deployed frontend builds must set `VITE_API_BASE_URL` to the FastAPI service origin. The API accepts cross-origin browser calls only from the comma-separated `QSA_CORS_ALLOWED_ORIGINS` list, with local Vite origins enabled by default and no wildcard production origin.

## Render Deployment

`render.yaml` defines two services:

- API web service:
  - runtime: Python
  - plan: free
  - region: Frankfurt
  - build: `uv sync --locked`
  - start: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`
  - health check: `/health`
  - configure `QSA_CORS_ALLOWED_ORIGINS` to the deployed frontend origin
- Frontend static site:
  - root directory: `frontend`
  - build: `npm ci && npm run build`
  - publish path: `frontend/dist`
  - SPA rewrite: `/*` to `/index.html`
  - configure `VITE_API_BASE_URL` to the deployed API origin

Create the first Render service from the GitHub repository Blueprint after pushing these files to `main`.
