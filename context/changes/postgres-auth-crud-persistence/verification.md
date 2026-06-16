# Verification: Postgres Auth CRUD Persistence

Date: 2026-06-16

## Automated Results

### Passed

- Backend lint/type:
  `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run ruff check . && UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pyright`
  - Result: passed.
  - Output summary: `All checks passed!` and `0 errors, 0 warnings`.

- Backend CI-equivalent pytest:
  `QSA_TEST_DATABASE_URL=postgresql:///qsa_test DATABASE_URL=postgresql:///qsa_test UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run pytest -p no:cacheprovider`
  - Result: passed.
  - Pytest summary: 258 tests passed.
  - Local test database: `postgresql:///qsa_test`.

- Frontend CI-equivalent:
  `npm --prefix frontend ci && npm --prefix frontend run test && npm --prefix frontend run build`
  - Result: passed.
  - Vitest summary: 10 files passed, 61 tests passed.
  - Build summary: Vite production build completed.

- Root E2E dependency install:
  `npm ci`
  - Result: passed.

- Playwright test discovery:
  `DATABASE_URL=postgresql:///postgres npm run e2e -- --list`
  - Result: passed.
  - Discovered tests:
    - `auth-crud.spec.ts`
    - `seed.spec.ts`
  - Note: this used a placeholder URL only to load config and list tests. It did
    not start servers or mutate Postgres.

- Playwright E2E:
  `QSA_TEST_DATABASE_URL=postgresql:///qsa_test DATABASE_URL=postgresql:///qsa_test AUTH_SECRET=local-e2e-auth-secret-with-at-least-32-characters QSA_SESSION_COOKIE_SECURE=false npm run e2e`
  - Result: passed.
  - Playwright summary: 2 tests passed.
  - Tests:
    - `seed.spec.ts`
    - `auth-crud.spec.ts`

- GitHub Actions workflow YAML parse:
  `UV_PROJECT_ENVIRONMENT=/tmp/qsa-postgres-auth-venv uv run python - <<'PY' ...`
  - Result: passed.

### Pending / Blocked Locally

- GitHub Actions workflow:
  - Status: workflow file added and syntax-parsed locally.
  - Pending: pass/fail status from a GitHub branch or PR run. This cannot be
    truthfully marked complete until the workflow has run on GitHub.

## Manual Verification Checklist

Pending operator checks after deploy:

1. Render production deployment has migrated schema and seeded user.
2. Public URL supports login -> config CRUD -> draft run -> deterministic
   dataset -> quality route -> JSONL export.
3. Backend restart or Render redeploy does not lose draft runs, configs,
   completed datasets, or exports.
4. Cross-workspace URL tampering returns `404`; unauthenticated protected routes
   return `401`.
5. Final notes contain no secrets.

## Real Provider Notes

No real Sharpe Terminal smoke check was run in this local verification pass.
`SHARPE_API_KEY` remains a backend-only secret and is not required for CI or the
auth/config CRUD Playwright test.
