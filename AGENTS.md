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

<!-- BEGIN @przeprogramowani/10x-cli -->

## 10xDevs AI Toolkit - Module 2, Lesson 2

Turn one roadmap item into the first implementation cycle with the **change planning chain**:

```
/10x-roadmap -> /10x-new -> /10x-plan -> /10x-plan-review -> /10x-implement
```

`/10x-new`, `/10x-plan`, `/10x-plan-review`, and `/10x-implement` are the lesson focus. `/10x-frame` and `/10x-research` are not required rituals here; they are escalation paths introduced in the next lesson.

### Task Router - Where to start

| Skill | Use it when |
| --- | --- |
| **Change setup (lesson focus)** | |
| `/10x-new <change-id>` | You selected a roadmap item and need a stable change folder. Creates `context/changes/<change-id>/change.md` so planning, implementation, progress, commits, and later review all share one identity. Use AFTER roadmap selection, BEFORE `/10x-plan`. |
| **Planning (lesson focus)** | |
| `/10x-plan <change-id>` | You have a change folder and need a reviewable implementation plan. Reads roadmap context, foundation docs, codebase evidence, and any existing change notes; writes `plan.md` and `plan-brief.md` with phases, file contracts, success criteria, and `## Progress`. |
| **Plan readiness (lesson focus)** | |
| `/10x-plan-review <change-id>` | You have `plan.md` and need a light pre-code readiness check. Use it to catch missing end state, weak contracts, malformed progress, scope drift, or blind spots before code changes begin. |
| **Implementation (lesson focus)** | |
| `/10x-implement <change-id> phase <n>` | You have an approved plan and want to execute one phase with verification, manual gate, commit ritual, and SHA write-back to `## Progress`. |
| **Lifecycle closure** | |
| `/10x-archive <change-id>` | A change is merged or intentionally closed. Move it out of active `context/changes/` into archive state. |

### How the chain hands off

- `/10x-new` creates the durable change identity.
- `/10x-plan` turns that identity into an implementation contract.
- `/10x-plan-review` checks the plan before the agent mutates code.
- `/10x-implement` executes one planned phase, verifies, asks for manual confirmation when needed, commits, and records progress.

### Lesson boundaries

- Plan is the default router after roadmap selection. Start with `/10x-plan` unless the problem is unclear or external evidence is blocking.
- Do not run `/10x-frame + /10x-research` as ceremony for every change.
- Do not turn this lesson into a full end-to-end product build. A checkpoint with a planned and partially or fully implemented stream is valid.
- Code review of the implemented diff belongs to Lesson 3 via `/10x-impl-review`.
- Lifecycle closure via `/10x-archive` after a change is merged or intentionally closed.

### Paths used by this lesson

- `context/foundation/roadmap.md` - upstream roadmap
- `context/changes/<change-id>/change.md` - change identity
- `context/changes/<change-id>/plan.md` - implementation contract
- `context/changes/<change-id>/plan-brief.md` - compressed handoff
- `context/foundation/lessons.md` - recurring rules and pitfalls
- `docs/reference/contract-surfaces.md` - load-bearing names registry

Skills must not write to `context/archive/`. Archived changes are immutable; if a resolved target path starts with `context/archive/`, abort with: "This change is archived. Open a new change with `/10x-new` instead."

<!-- END @przeprogramowani/10x-cli -->
