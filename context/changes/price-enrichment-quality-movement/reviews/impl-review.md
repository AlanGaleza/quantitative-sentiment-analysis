<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Price Enrichment for Quality Movement

- **Plan**: `context/changes/price-enrichment-quality-movement/plan.md`
- **Scope**: Phases 1-6 of 6
- **Date**: 2026-06-16
- **Verdict**: APPROVED after triage
- **Findings**: 0 critical, 3 warnings fixed, 1 observation closed

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

### F1 — Missing route-level deterministic JSON test

- **Severity**: WARNING
- **Impact**: LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: `tests/backtest_quality/test_router.py`
- **Detail**: Plan required a router test for repeated deterministic JSON response. Determinism was covered in metrics tests, but not at the authenticated route boundary.
- **Fix**: Add a route test that calls the same quality endpoint twice with fixture data and asserts identical `response.json()` payloads.
- **Decision**: FIXED in `3ab1464`

### F2 — Public warnings expose raw exception details

- **Severity**: WARNING
- **Impact**: MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: `src/quantitative_sentiment_analysis/price_enrichment/service.py`
- **Detail**: Partial-report warnings included raw exception details for cache/provider failures. Those warnings are returned to API/UI and could expose SQL, hostnames, URLs, or environment details.
- **Fix**: Return stable high-level warnings only; log exception details server-side with `exc_info=True`.
- **Decision**: FIXED in `3ab1464`

### F3 — Sparse datasets can trigger many sequential provider calls

- **Severity**: WARNING
- **Impact**: HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Safety & Quality
- **Location**: `src/quantitative_sentiment_analysis/price_enrichment/service.py`
- **Detail**: Missing candles were fetched per contiguous minute window. Sparse multi-day records could trigger many sequential Binance requests, each with a 20s timeout.
- **Fix**: Add a per-request enrichment budget, bounded fetch windows, provider-failure short-circuiting, and sparse timestamp call-count coverage.
- **Decision**: FIXED in `3ab1464`

### F4 — Migration re-run blocked by current test DB DNS

- **Severity**: OBSERVATION
- **Impact**: LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: N/A
- **Detail**: The configured external `QSA_TEST_DATABASE_URL` host did not resolve during review, blocking migration re-run against that URL.
- **Fix**: Re-run migration verification with a reachable test Postgres URL.
- **Decision**: CLOSED. `DATABASE_URL=postgresql+psycopg:///qsa_test uv run alembic upgrade head` passed locally and `alembic current` reported `20260616_0003 (head)`.

## Verification After Triage

- `DATABASE_URL=postgresql+psycopg:///qsa_test UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment tests/backtest_quality tests/persistence/test_models.py -p no:cacheprovider` — 117 passed.
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check .` — passed.
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright` — passed.
- `npm --prefix frontend run test -- src/features/backtestQuality` — 16 passed.
- `npm --prefix frontend run build` — passed.
