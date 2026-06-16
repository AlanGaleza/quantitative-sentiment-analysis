---
change_id: price-enrichment-quality-movement
title: Price enrichment for quality movement
status: implementing
created: 2026-06-16
updated: 2026-06-16
archived_at: null
---

## Notes

Add the missing quality enrichment phase for completed BTCUSD BACKTEST datasets.
For each news record, resolve BTCUSD price at the event timestamp and at the
selected quality horizon, then compute `later_return` and `realized_direction`
so the quality plot can show numeric movement pairs instead of only missing
movement warnings. Keep V1 BACKTEST-only and preserve explicit missing-data
warnings when price data is unavailable.
