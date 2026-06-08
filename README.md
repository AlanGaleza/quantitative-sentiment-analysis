# Quantitative Sentiment Analysis

FastAPI service for deterministic BTCUSD BACKTEST sentiment datasets.

## Local Development

Install locked dependencies:

`uv sync --locked`

On WSL projects mounted under `/mnt/e`, use an external Linux venv if `.venv` copy operations fail:

`UV_PROJECT_ENVIRONMENT=/tmp/qsa-render-venv UV_LINK_MODE=copy uv sync --locked`

Run the API locally:

`uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`

Verify the deployment smoke endpoint:

`curl -fsS http://127.0.0.1:8000/health`

## Render Deployment

`render.yaml` defines the MVP web service:

- runtime: Python
- plan: free
- region: Frankfurt
- build: `uv sync --locked`
- start: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`
- health check: `/health`

Create the first Render service from the GitHub repository Blueprint after pushing these files to `main`.
