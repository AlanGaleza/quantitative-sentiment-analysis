# Deployment Plan

## Scope

First Render deployment for the FastAPI/uv MVP described in `context/foundation/infrastructure.md` and `context/foundation/tech-stack.md`.

## Status

- [x] Add importable FastAPI app at `quantitative_sentiment_analysis.main:app`.
- [x] Add `/health` smoke endpoint for Render health checks.
- [x] Package the `src/quantitative_sentiment_analysis/` module through `pyproject.toml`.
- [x] Add `render.yaml` Blueprint for a Render Free web service in Frankfurt.
- [x] Verify `uv sync --locked` in a Linux venv outside the `/mnt/e` DrvFS mount.
- [x] Verify local Uvicorn startup with the same app import path as Render.
- [ ] Push deployment files to GitHub `main`.
- [ ] Create the Render Blueprint service from the GitHub repo.
- [ ] Verify the public Render `/health` URL after the first deploy.

## Render Configuration

- Service name: `quantitative-sentiment-analysis`
- Runtime: Python
- Plan: free
- Region: Frankfurt
- Build command: `uv sync --locked`
- Start command: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

## Manual Gate

Actual Render service creation is blocked until a human provides Render/GitHub authorization in this environment or creates the Blueprint from the Render dashboard. Production secrets and plan upgrades remain human-approved actions.
