<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Backtest Quality View Final Pass

- **Plan**: context/changes/s-04/plan.md
- **Scope**: Phases 1-5 of 5
- **Date**: 2026-06-11
- **Verdict**: APPROVED
- **Findings**: 0 critical 0 warnings 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 - Future S-02 large runs still need chart-point bounds

- **Severity**: 🔎 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: src/quantitative_sentiment_analysis/backtest_quality/metrics.py:107; frontend/src/features/backtestQuality/SentimentReturnPlot.tsx:102
- **Detail**: The post-triage implementation now caps `representative_records` deterministically, while metrics still cover the full input as required. `chart_points` intentionally still contains every input record and the frontend renders every point plus every outcome list item. This is acceptable for the S-04 local fixture and contract/UI boundary, but the later real `S-02` wiring should not expose unbounded chart payloads or render unbounded chart outcome lists for large completed BACKTEST runs.
- **Fix**: Before connecting real completed-run data from `S-02`, add deterministic chart-point capping/downsampling or document and enforce a maximum completed-run size while keeping metric denominators over the full input.
  - Strength: Preserves current S-04 contract behavior while preventing the future large-run UI/API path from growing without bounds.
  - Tradeoff: Needs a product decision on whether the report contract should expose sampled chart points, paginated detail, or an explicit run-size limit.
  - Confidence: MEDIUM — the current fixture scope is small and tested, but real `S-02` run sizes are not defined yet.
  - Blind spot: No real completed-run storage shape exists yet, so the final cap/downsampling strategy should be chosen with `S-02`.
- **Decision**: PENDING

## Verification Notes

Passed in the final review pass:

- `uv lock --check`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-venv UV_LINK_MODE=copy uv sync --locked --dev`
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-review-prod-venv UV_LINK_MODE=copy uv sync --locked --no-dev`
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

- All prior implementation-review findings in `impl-review.md` and `impl-review-post-triage.md` are marked fixed in their saved reports and follow-up queues.
- The final API smoke check used the explicit local fixture provider gate: `QSA_RUNTIME_ENV=local` plus `QSA_BACKTEST_QUALITY_PROVIDER=local-fixture`.
- No critical or warning-level finding remains for the S-04 contract/UI fixture boundary.
