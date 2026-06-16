---
change_id: postgres-auth-crud-persistence
title: Postgres auth CRUD persistence
status: implementing
created: 2026-06-15
updated: 2026-06-16
archived_at: null
---

## Notes

Render Postgres has been created. Use Option B: migrations and runtime access
should run from the Render backend service using `DATABASE_URL` stored in Render,
not pasted into the chat. Scope includes all persistence needed for the badge:
user management/auth, workspace ownership, CRUD, draft runs, completed dataset
runs, and dataset records. Confirmed frontend origin:
`https://quantitative-sentiment-analysis-frontend.onrender.com`.
