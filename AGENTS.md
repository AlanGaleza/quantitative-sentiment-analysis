# Repository Guidelines

Quantitative Sentiment Analysis is a greenfield Python 3.12 FastAPI/uv service for deterministic BTCUSD BACKTEST sentiment datasets. Treat @context/foundation/prd.md and @context/foundation/tech-stack.md as the product and stack sources of truth.

## Hard Rules

- Do not write to `context/archive/`; archived changes are immutable. If a target path resolves there, abort and open a new change instead.
- Keep V1 BACKTEST-only. Do not add live streaming, broker integration, order execution, or investment-recommendation wording.
- Use the PRD terms `directional bias`, `LONG`, `SHORT`, and `FLAT`; do not present outputs as executable trading signals.
- Deterministic output is required: the same news input, timeframe, workspace, seed, model version, and config must produce identical JSONL.

## Project Structure & Module Organization

- `pyproject.toml` and `uv.lock` define the uv-managed FastAPI/Uvicorn project with Python `>=3.12`.
- `main.py` is a thin ASGI compatibility entrypoint. Put application code in `src/quantitative_sentiment_analysis/`.
- Keep API routes, Pydantic schemas, ingestion, sentiment scoring, backtest orchestration, and export code under the package root instead of new root-level scripts.
- `render.yaml` defines the Render web service blueprint. Keep its start command aligned with the app import path.
- `context/foundation/` holds living planning docs; `context/changes/` holds generated verification notes.

## Build, Test, and Development Commands

- `uv sync` installs locked dependencies from `pyproject.toml` and `uv.lock`.
- On `/mnt/e` or WSL permission/hardlink failures, rerun dependency installation as `UV_LINK_MODE=copy uv sync`.
- `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000` starts the local API.
- `curl -fsS http://127.0.0.1:8000/health` verifies the deployment health endpoint.
- `uv add <package>` adds runtime dependencies; use `uv add --dev <package>` for dev tools and commit both `pyproject.toml` and `uv.lock`.

## Data Contracts

Export records must preserve `timestamp`, `headline`, source identity or `source_name`, sentiment score `-1..1`, directional bias, confidence `0..1`, `run_id`, and `config_version`. Mark noise or irrelevant records instead of silently deleting them. Keep workspace input data, generated datasets, and exports isolated per workspace.

## Testing Guidelines

No test runner is configured yet. When adding the first feature, add a `tests/` tree that mirrors the package and document the chosen runner in `pyproject.toml`. Name tests `test_*.py`. Cover deterministic reruns, score/confidence bounds, noise labeling, stable JSONL output, and absence of broker/order side effects.

## Commit & Pull Request Guidelines

Git history only shows `Initial commit`, so no project-specific commit convention is established. Use concise imperative commits with optional scope, for example `feat(api): add backtest export endpoint`. PRs should cite relevant PRD or FR IDs, list commands run, call out schema/export changes, and mention any `uv.lock` update.

## Security & Configuration Tips

Keep secrets in `.env` or `.env.*`; these are ignored by `.gitignore`. Do not commit generated datasets containing real workspace identifiers or unsanitized news exports.
`RENDER_API_KEY.txt` is a local operator secret file for Render API/CLI access and is ignored by git. Load it only into the current shell with `export RENDER_API_KEY="$(tr -d '\r\n' < RENDER_API_KEY.txt)"`; never print the token, commit the file, or set `RENDER_API_KEY` as a Render app environment variable unless the app itself must call Render at runtime.
