# Price Enrichment Quality Movement Verification

## Automated Commands

- `DATABASE_URL=$QSA_TEST_DATABASE_URL UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pytest tests/price_enrichment tests/backtest_quality tests/persistence/test_models.py -p no:cacheprovider`
  - Result: passed, `106 passed, 6 skipped`.
  - Skip note: Postgres integration tests were skipped because the configured
    test database host was not reachable from this runner.
- `npm --prefix frontend run test -- src/features/backtestQuality && npm --prefix frontend run build`
  - Result: passed, `16 passed`; Vite production build completed.
- `UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-price-enrichment-venv uv run pyright`
  - Result: passed, `ruff` clean and `pyright` reported `0 errors`.

## Manual Smoke Results

Operator confirmed on 2026-06-16:

- Local smoke: create or reuse a completed `demo-workspace` BACKTEST run, open
  quality for `1 minute`, and confirm numeric movement pairs or a specific price
  provider warning.
  - Result: passed by manual operator confirmation.
- Render smoke: after deploy and `alembic upgrade head`, open the deployed
  completed run quality route for `1 minute` and confirm numeric movement pairs
  or a specific price provider warning, with no `500 Internal Server Error`.
  - Result: passed by manual operator confirmation.
- JSONL export smoke: download JSONL for the same run and confirm canonical
  dataset records do not include price movement fields.
  - Result: passed by manual operator confirmation.
