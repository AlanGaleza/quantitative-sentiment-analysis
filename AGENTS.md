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
Use `context/foundation/quality-contracts.md` as the canonical source for workspace, run metadata, dataset/export, JSONL determinism, and semantic-safety invariants.

## Testing Guidelines

No test runner is configured yet. When adding the first feature, add a `tests/` tree that mirrors the package and document the chosen runner in `pyproject.toml`. Name tests `test_*.py`. Cover deterministic reruns, score/confidence bounds, noise labeling, stable JSONL output, and absence of broker/order side effects.

## Commit & Pull Request Guidelines

Git history only shows `Initial commit`, so no project-specific commit convention is established. Use concise imperative commits with optional scope, for example `feat(api): add backtest export endpoint`. PRs should cite relevant PRD or FR IDs, list commands run, call out schema/export changes, and mention any `uv.lock` update.

## Security & Configuration Tips

Keep secrets in `.env` or `.env.*`; these are ignored by `.gitignore`. Do not commit generated datasets containing real workspace identifiers or unsanitized news exports.
`RENDER_API_KEY.txt` is a local operator secret file for Render API/CLI access and is ignored by git. Load it only into the current shell with `export RENDER_API_KEY="$(tr -d '\r\n' < RENDER_API_KEY.txt)"`; never print the token, commit the file, or set `RENDER_API_KEY` as a Render app environment variable unless the app itself must call Render at runtime.

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
Use `context/foundation/quality-contracts.md` as the canonical source for workspace, run metadata, dataset/export, JSONL determinism, and semantic-safety invariants.

## Testing Guidelines

No test runner is configured yet. When adding the first feature, add a `tests/` tree that mirrors the package and document the chosen runner in `pyproject.toml`. Name tests `test_*.py`. Cover deterministic reruns, score/confidence bounds, noise labeling, stable JSONL output, and absence of broker/order side effects.

## Commit & Pull Request Guidelines

Git history only shows `Initial commit`, so no project-specific commit convention is established. Use concise imperative commits with optional scope, for example `feat(api): add backtest export endpoint`. PRs should cite relevant PRD or FR IDs, list commands run, call out schema/export changes, and mention any `uv.lock` update.

## Security & Configuration Tips

Keep secrets in `.env` or `.env.*`; these are ignored by `.gitignore`. Do not commit generated datasets containing real workspace identifiers or unsanitized news exports.
`RENDER_API_KEY.txt` is a local operator secret file for Render API/CLI access and is ignored by git. Load it only into the current shell with `export RENDER_API_KEY="$(tr -d '\r\n' < RENDER_API_KEY.txt)"`; never print the token, commit the file, or set `RENDER_API_KEY` as a Render app environment variable unless the app itself must call Render at runtime.

<!-- BEGIN @przeprogramowani/10x-cli -->

## 10xDevs AI Toolkit - Module 2, Lesson 3

Review AI-generated code before merge with the **implementation review chain**:

```
/10x-implement -> /10x-impl-review -> triage -> (/10x-lesson | fix | skip | disagree)
```

`/10x-impl-review` is the lesson focus. Review is a quality gate, not an instruction to fix every finding.

### Task Router - Where to start

| Skill | Use it when |
| --- | --- |
| **Code review (lesson focus)** | |
| `/10x-impl-review <change-id>` | You have implemented code and want a structured review before merge. The skill checks plan adherence, scope discipline, safety and quality, architecture, pattern consistency, and success criteria, then presents findings for triage. |
| **Recurring lesson outcome** | |
| `/10x-lesson` | A finding reveals a recurring project rule or agent failure pattern. Record it in `context/foundation/lessons.md` instead of treating it as a one-off note. |

### Triage discipline

- Severity says how bad the finding is. Impact says how much the decision matters now.
- Valid outcomes: fix now, fix differently, skip, accept as risk, record as recurring rule (`/10x-lesson`), disagree.
- Fix critical findings. Do not burn hours on low-impact observations just because the agent found them.
- Conscious skipping of low-impact findings is a valid review outcome, not negligence.
- If you disagree with a finding, record why. Wrong agent reasoning is also signal.

### Review boundaries

- This lesson reviews implemented code. It does not create the plan, execute new phases, or teach CI review.
- Testing strategy and quality gates are introduced in Module 3.
- Do not use `/10x-contract` as a triage outcome in this lesson.

### Paths used by this lesson

- `context/changes/<change-id>/plan.md` - expected implementation contract
- `context/changes/<change-id>/reviews/` - review output
- `context/foundation/lessons.md` - recurring lessons

Skills must not write to `context/archive/`. Archived changes are immutable; if a resolved target path starts with `context/archive/`, abort with: "This change is archived. Open a new change with `/10x-new` instead."

<!-- END @przeprogramowani/10x-cli -->
