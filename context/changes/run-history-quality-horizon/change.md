---
change_id: run-history-quality-horizon
title: Run history and quality horizon
status: implemented
created: 2026-06-16
updated: 2026-06-16
archived_at: null
---

## Notes

User-observed workflow gap after Postgres persistence: after a user creates a
draft run from a saved config and runs the deterministic BACKTEST dataset, the
run exists in durable storage but the frontend does not expose a historical run
list after logout/login. The same workflow also exposes that quality reports use
a hard-coded 4 hour horizon; the horizon should be explicit and configurable
instead of hidden in the report default.
