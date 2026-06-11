<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Backtest Quality View

- **Plan**: context/changes/s-04/plan.md
- **Scope**: Phases 1-5 of 5
- **Date**: 2026-06-11
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical 6 warnings 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | FAIL |

## Findings

### F1 - Local fixture-backed quality view is not actually available

- **Severity**: WARNING
- **Impact**: MEDIUM - real tradeoff; pause to reason through it
- **Dimension**: Plan Adherence
- **Location**: src/quantitative_sentiment_analysis/backtest_quality/repository.py:45
- **Detail**: The plan says local development and tests can render a fixture-backed BTCUSD BACKTEST quality report. The implementation only injects fixtures in tests; the default local API provider always raises the S-02 not-ready 409. README.md:27 tells the operator to open a local quality path, but that path cannot render a fixture-backed report with the documented API and Vite commands.
- **Fix A Recommended**: Add an explicit local-only fixture provider switch, for example an env-gated provider mode, and document it.
  - Strength: Satisfies the checked manual criteria without pretending production run data exists.
  - Tradeoff: Needs a small config boundary and regression test so fake fixture data cannot be enabled accidentally in production.
  - Confidence: HIGH - the provider dependency boundary already exists.
  - Blind spot: Exact env name and production guard have not been chosen.
- **Fix B**: Update the plan/README/manual criteria to say fixture-backed rendering is test-only until S-02.
  - Strength: Keeps runtime behavior strictly not-ready.
  - Tradeoff: Weakens the delivered local UI verification promised by S-04.
  - Confidence: MEDIUM - acceptable only if the manual browser criteria were intentionally overstated.
  - Blind spot: Does not prove the integrated UI/API path outside tests.
- **Decision**: FIXED via Fix A - added a local-only fixture provider switch gated by `QSA_RUNTIME_ENV=local` and `QSA_BACKTEST_QUALITY_PROVIDER=local-fixture`, with README documentation and router regression tests.

### F2 - Unsupported run cases are collapsed into one generic test path

- **Severity**: WARNING
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: tests/backtest_quality/test_router.py:66
- **Detail**: The Phase 2 contract says router tests cover missing run, incomplete run, non-BTCUSD rejection, non-BACKTEST rejection, and unchanged /health. The implementation only tests one generic QualityRunUnsupportedError case.
- **Fix**: Add distinct provider-error tests/messages for wrong instrument and wrong mode, or document that S-02 owns those two branches.
- **Decision**: FIXED - added distinct router tests for unsupported non-BTCUSD instrument and non-BACKTEST mode provider errors.

### F3 - Render static publish path does not match the rooted frontend service

- **Severity**: WARNING
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: render.yaml:20
- **Detail**: Phase 4 specifies a frontend service rooted at frontend/ with publish directory dist. The blueprint sets rootDir: frontend and staticPublishPath: frontend/dist, and README.md:62 repeats the same path. That is internally inconsistent with the implementation contract.
- **Fix**: Change staticPublishPath to dist and update README.md to list publish path dist for the rooted static service.
- **Decision**: FIXED - changed the rooted frontend Render publish path to `dist` and updated README deployment documentation.

### F4 - CORS env accepts wildcard origins despite the no-wildcard contract

- **Severity**: WARNING
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: src/quantitative_sentiment_analysis/main.py:60
- **Detail**: configured_cors_allowed_origins() accepts any non-empty comma-separated token, including "*". Defaults are local-only, but the Phase 4 contract requires avoiding wildcard production origins.
- **Fix**: Reject "*" and invalid non-http origins in configured CORS parsing, then add a regression test in tests/test_main.py.
- **Decision**: FIXED - rejected wildcard and malformed CORS origins with regression tests for env parsing and normalization.

### F5 - Exact backend verification commands fail in the current workspace

- **Severity**: WARNING
- **Impact**: MEDIUM - real tradeoff; pause to reason through it
- **Dimension**: Success Criteria
- **Location**: N/A
- **Detail**: uv lock --check passed, but the exact planned command UV_LINK_MODE=copy uv sync --locked --dev failed while copying the editable package .pth into .venv on /mnt/e with Operation not permitted. Exact uv run pytest then fails for the same .venv repair path. Using UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv with the same lockfile passes backend install, tests, compileall, uvicorn startup, and /health.
- **Fix**: Repair/remove the local .venv or standardize the /mnt/e verification command on an external Linux venv, then rerun the exact checklist.
- **Decision**: FIXED - confirmed a regenerated `.venv` on `/mnt/e` still fails, standardized README verification guidance on an external Linux venv, and reran backend checks through `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv`.

### F6 - Unplanned AGENTS.md and LICENSE churn is included in the S-04 diff

- **Severity**: WARNING
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: AGENTS.md:88
- **Detail**: The S-04 plan does not mention AGENTS.md or LICENSE. The committed diff changes the 10x lesson block in AGENTS.md and rewrites LICENSE line endings, creating unrelated review noise.
- **Fix**: Keep only intentional S-04 files in this change; move agent-rule updates and license line-ending normalization to separate commits or revert them from this change.
- **Decision**: FIXED - reverted the unplanned AGENTS.md lesson-block churn to the pre-S-04 content and normalized LICENSE line endings; AGENTS.md also trims one final blank line so `git diff --check` stays clean.

### F7 - Plot domain calculation spreads all return values

- **Severity**: OBSERVATION
- **Impact**: LOW - quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: frontend/src/features/backtestQuality/SentimentReturnPlot.tsx:119
- **Detail**: buildReturnDomain() calls Math.min(0, ...values) and Math.max(0, ...values). S-04 reports are expected to be small, but future S-02-backed large runs could hit JavaScript argument limits or freeze the UI.
- **Fix**: Compute min/max with a single-pass loop or reducer before wiring large completed-run datasets.
- **Decision**: FIXED - replaced spread-based min/max with a single-pass loop.

## Verification Notes

Passed:

- `uv lock --check`
- `npm --prefix frontend ci`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run pytest tests/backtest_quality`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run pytest`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run python -m compileall src tests`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('render.yaml').read_text())"`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- `curl -fsS http://127.0.0.1:8000/health`

Failed:

- `UV_LINK_MODE=copy uv sync --locked --dev`
- `uv run pytest tests/backtest_quality/test_schemas.py`, due to the same `.venv` install/copy failure before pytest started.
