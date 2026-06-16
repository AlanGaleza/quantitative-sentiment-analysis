# Postgres Auth CRUD Persistence Rollout

## Scope

Roll out durable Postgres persistence, closed login, workspace ownership, saved
BTCUSD BACKTEST configuration CRUD, and the protected draft/dataset/quality
workflow on Render.

## Secret Handling

- Do not paste `DATABASE_URL`, passwords, `AUTH_SECRET`, `SHARPE_API_KEY`, or
  cookie values into chat, commits, issue comments, or verification notes.
- Configure secrets only in the Render backend service environment.
- Keep `VITE_API_BASE_URL` as a frontend public value; it is not a secret.

## Backend Environment Checklist

- `DATABASE_URL`: existing Render Postgres Internal Database URL.
- `AUTH_SECRET`: generated secret with at least 32 characters.
- `QSA_CORS_ALLOWED_ORIGINS`: deployed frontend origin only.
- `QSA_SESSION_COOKIE_SECURE`: omit or set `true` in production.
- `QSA_SESSION_COOKIE_SAMESITE`: omit for production default `none`.
- `SHARPE_API_KEY`: backend-only secret for real Sharpe Terminal smoke checks.

## Frontend Environment Checklist

- `VITE_API_BASE_URL`: deployed FastAPI service origin.
- No backend secrets in Vite env.

## Migration

Run from the Render backend service environment, where `DATABASE_URL` is already
loaded:

```bash
uv run alembic upgrade head
```

Expected result: Alembic reports the schema at `head`.

## Seed User

Run from the Render backend service environment:

```bash
QSA_SEED_USER_EMAIL="<admin email>" \
QSA_SEED_USER_PASSWORD="<admin password>" \
QSA_SEED_WORKSPACE_SLUG="demo-workspace" \
QSA_SEED_WORKSPACE_NAME="Demo Workspace" \
uv run python -m quantitative_sentiment_analysis.auth.seed_user
```

Expected result: the command prints the normalized email and workspace slug, but
does not print the password.

## Post-Deploy Smoke

1. Open the public frontend URL.
2. Visit `/workspaces/demo-workspace/backtest-configs` and confirm login is
   shown before authentication.
3. Log in with the seeded user.
4. Create, edit, and delete a saved BTCUSD BACKTEST configuration.
5. Create a draft run from a saved config.
6. Run deterministic dataset generation.
7. Open the quality route and confirm completed datasets do not show the old
   S-02 unavailable message.
8. Download JSONL.
9. Redeploy or restart the backend and confirm configs, runs, datasets, and
   exports remain available.
10. Try an unauthenticated protected request and a different workspace slug;
    expect `401` or not-found access.

## Rollback Notes

- Application rollback does not delete or roll back Postgres data.
- The initial schema is additive for this repository; destructive DB rollback
  should not be attempted without a separate reviewed migration plan.
- If frontend auth breaks but backend is healthy, verify `VITE_API_BASE_URL`,
  `QSA_CORS_ALLOWED_ORIGINS`, and cookie attributes before rolling back.
- If DB-backed routes fail after deploy, verify Render `DATABASE_URL`, Alembic
  head, and the seeded workspace before rolling back application code.
