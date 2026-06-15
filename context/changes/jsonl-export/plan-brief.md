# JSONL Export — Plan Brief

> Full plan: `context/changes/jsonl-export/plan.md`

## What & Why

This plan implements S-03: a trader can download a complete deterministic BTCUSD BACKTEST dataset as JSONL after a dataset run has completed. The export turns the S-02 completed records into reproducible training-data bytes without creating durable local export artifacts, triggering new dataset generation, or adding CSV.

## Starting Point

S-02 already stores completed canonical `DatasetRecord` rows by `workspace_id` and `run_id`, exposes a bounded dataset preview API, and has stable JSON serialization helpers. The current router intentionally has no export route yet, and the frontend shell shows completed dataset metadata plus preview records but no download action.

## Desired End State

The backend exposes `GET /api/workspaces/{workspace_id}/backtests/{run_id}/dataset/export.jsonl` for completed datasets. The response is a downloadable JSONL body where every line is one canonical `DatasetRecord`, sorted deterministically, UTF-8 encoded, newline terminated, and repeatable byte-for-byte for identical stored records. The frontend shows a download action only for completed datasets and handles export failures without showing a large JSONL text preview.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Export formats | JSONL only | S-03's primary roadmap goal is JSONL; CSV is deferred to avoid widening the deterministic contract. |
| Delivery model | HTTP download/stream response | Exports should not depend on local filesystem durability or committed artifacts. |
| API shape | `GET .../dataset/export.jsonl` | The operation reads an existing completed dataset and has one supported format. |
| File contents | Canonical `DatasetRecord` lines only | Preserves the quality contract that one JSONL line equals one dataset record. |
| Metadata placement | Headers plus record fields | `run_id` and `config_version` already exist in records; headers can aid download/debugging without changing the file body. |
| Error semantics | `404` missing, `409` not exportable | Matches existing dataset/quality not-ready semantics and avoids silent empty files. |
| Frontend UX | Explicit download button after completion | Gives the trader a visible export path without rendering the whole JSONL file in the UI. |
| Ordering | Stable export-time sort | Protects deterministic bytes from repository insertion-order drift. |
| Privacy/storage | No generated local artifacts | Keeps workspace data out of the repo and avoids treating local files as source of truth. |

## Scope

**In scope:**

- Backend JSONL export service over completed S-02 `DatasetRecord` rows.
- Deterministic export sorting, serialization, media type, filename, and headers.
- Export API route with `404`/`409` semantics and no implicit dataset generation.
- Frontend API helper and completed-dataset download action.
- Backend and frontend tests for route behavior, stable bytes, URL construction, and UX states.
- Documentation handoff showing S-03 complete and CSV still out of scope.

**Out of scope:**

- CSV export, multi-format negotiation, or sidecar manifest endpoint.
- Durable database/object storage for exports.
- Local generated `.jsonl` files committed to the repo.
- New provider ingestion, price enrichment, live streaming, broker integration, order execution, or investment-recommendation wording.
- Auth/session work beyond preserving existing workspace/run path boundaries.

## Architecture / Approach

Add a small export boundary inside `backtest_dataset` that reads all records through `CompletedDatasetRepository.list_records()`, rejects non-completed/provider-limited runs, sorts records by the quality-contract keys, and emits stable JSONL lines using existing serialization helpers. Wire that into the existing dataset router as a download response. Extend the existing backtest shell frontend, not a new route, so the export action appears where the completed dataset is already visible.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Backend Export Contract | Deterministic JSONL byte/iterator contract and unit tests | Accidentally exporting preview order or non-stable bytes. |
| 2. Backend Export API | Download endpoint, headers, and error semantics | Blurring missing, provider-limited, and completed states. |
| 3. Frontend Download Flow | Completed-dataset JSONL download action | Browser download code becoming hard to test or leaking text preview data. |
| 4. Verification and Handoff | Regression checks and docs/status updates | Leaving CSV/storage/export artifact scope ambiguous. |

**Prerequisites:** S-02 completed dataset storage and frontend shell flow are implemented; no durable export storage exists.
**Estimated effort:** ~2-3 focused sessions across 4 phases.

## Open Risks & Assumptions

- The current completed-run repository is local/dev in-memory; this plan exports from that existing boundary and does not solve production durability.
- Large datasets may eventually need chunked streaming from durable storage; S-03 should keep the interface stream-friendly but test against current in-memory records.
- Browser download behavior has environment-specific details; tests should isolate URL/blob mechanics without depending on a real browser download prompt.
- Provider-limited runs are stored as terminal summaries but are not exportable as completed datasets.

## Success Criteria (Summary)

- A completed BACKTEST dataset can be downloaded as deterministic JSONL from the backend and from the shell UI.
- Repeating the same export for the same stored records produces identical UTF-8 bytes with one canonical dataset record per line.
- Missing, cross-workspace, and provider-limited states fail clearly without generating a dataset or writing local export files.
