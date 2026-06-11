<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Backtest Quality View Post-Triage

- **Plan**: context/changes/s-04/plan.md
- **Scope**: Phases 1-5 of 5
- **Date**: 2026-06-11
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical 2 warnings 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 - Render API service installs dev dependencies

- **Severity**: WARNING
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: render.yaml:7
- **Detail**: The API service build command is `uv sync --locked` and the start command is `uv run uvicorn ...`. After S-04, `pyproject.toml` has a dev dependency group for pytest, httpx, and pyyaml. `uv sync` and `uv run` support `--no-dev`, but the Render API service does not use it, so production can carry unnecessary dev/test tooling.
- **Fix**: Use `uv sync --locked --no-dev` for the API build command and `uv run --no-dev uvicorn ...` for the API start command, then update README if it documents those commands.
- **Decision**: FIXED - updated Render API build/start commands to exclude the dev dependency group and aligned README deployment documentation.

### F2 - later_return accepts non-finite floats

- **Severity**: WARNING
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: src/quantitative_sentiment_analysis/backtest_quality/schemas.py:69
- **Detail**: `QualityInputRecord.later_return` and `QualityChartPoint.later_return` are plain `float | None` fields. Direct verification showed Pydantic accepts `NaN`, `Infinity`, and `-Infinity` and serializes them as `null`, which can silently change metric/chart semantics and blur the difference between missing movement and invalid numeric data.
- **Fix**: Reject non-finite `later_return` values with `Field(allow_inf_nan=False)` or a validator on input/chart models, with schema regression tests.
- **Decision**: FIXED - rejected non-finite `later_return` values on input records and chart points, with schema regression tests for `NaN`, `Infinity`, and `-Infinity`.

### F3 - Representative records are currently unbounded

- **Severity**: OBSERVATION
- **Impact**: MEDIUM - real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: src/quantitative_sentiment_analysis/backtest_quality/metrics.py:106
- **Detail**: `representative_records` currently returns every ordered input record. This is fine for the S-04 fixture path, and the plan explicitly defers pagination/sampling until large S-02 runs exist, but the later integration should not ship real large runs with unbounded record samples in the report body.
- **Fix**: Before real S-02 wiring, add deterministic sampling or capping for representative records while keeping metrics over the full denominator.
- **Decision**: FIXED - added deterministic capping for representative records while keeping metrics and chart points over the full record set.

### F4 - Malformed encoded route can throw during route parsing

- **Severity**: OBSERVATION
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: frontend/src/App.tsx:18
- **Detail**: `parseQualityRoute()` calls `decodeURIComponent()` directly. Malformed URL encoding can throw and blank the app instead of returning `null` and showing the existing route error state.
- **Fix**: Wrap route decoding in `try/catch` and return `null` for malformed path segments, with a small route parsing test.
- **Decision**: FIXED - wrapped route decoding in `try/catch` and added route parsing regression tests for malformed encoded segments.

## Verification Notes

Passed:

- `uv lock --check`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv UV_LINK_MODE=copy uv sync --locked --dev`
- `npm --prefix frontend ci`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run pytest tests/backtest_quality/test_schemas.py`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run pytest tests/backtest_quality`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run pytest`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run python -m compileall src tests`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('render.yaml').read_text())"`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- `git diff --check`
- `QSA_RUNTIME_ENV=local QSA_BACKTEST_QUALITY_PROVIDER=local-fixture UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- `curl -fsS http://127.0.0.1:8000/health`
- `curl -fsS http://127.0.0.1:8000/api/workspaces/workspace-alpha/backtests/run-001/quality`

Notes:

- Backend commands were run through the documented external Linux venv path for this `/mnt/e` workspace.
- The local fixture quality endpoint returned deterministic BTCUSD BACKTEST report data with hit rate, warnings, missing movement, and LONG/SHORT/FLAT chart rows.
