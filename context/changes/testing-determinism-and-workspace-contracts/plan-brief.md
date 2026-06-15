# Test Determinism and Workspace Contracts — Plan Brief

> Full plan: `context/changes/testing-determinism-and-workspace-contracts/plan.md`
> Research: `context/changes/testing-determinism-and-workspace-contracts/research.md`

## What & Why

This plan executes Phase 1 of the test rollout: protect deterministic BACKTEST dataset generation/export and prove workspace boundaries cannot be bypassed by `run_id` alone.

The user concern is direct: the same news scope must not produce a different dataset on rerun, and a completed dataset must not leak across workspaces at storage, API, or export boundaries.

## Starting Point

The implementation already has deterministic dataset generation, canonical JSONL serialization, and in-memory completed-run storage keyed by `(workspace_id, run_id)`. Research found one real gap: storage validates only the bounded preview slice before storing all records, so a bad record beyond the first 100 could later be exported.

## Desired End State

Two independent API generation/export flows using identical deterministic input and the same deterministic `run_id` produce identical preview records and identical JSONL bytes. Completed-run storage rejects mixed workspace/run/config records across the full tuple before they can be read or exported.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Normalization `body` tie-breaker | Defer to Phase 2 | It is a real provider-pipeline determinism edge, but Phase 1 should stay on dataset/export contracts. | Plan |
| Quality route defensive `409` | Defer to Phase 3 | Quality workspace behavior belongs with quality truthfulness tests. | Plan |
| Repository validation strictness | Full identity + count validation | Preview-only validation leaves a concrete export leak beyond 100 records. | Research + Plan |
| JSONL byte equality oracle | Same `run_id` in isolated repositories | JSONL includes `run_id`, so this matches the product byte contract. | Research + Plan |
| Verification scope | Focused backend suite; full pytest if cheap | Risks #1/#2 are backend contracts, not frontend or E2E. | Test Plan + Plan |

## Scope

**In scope:**

- Full stored record validation in `InMemoryCompletedDatasetRepository`.
- Repository tests for records beyond the preview window.
- `list_records` workspace isolation tests.
- `GET /dataset` cross-workspace route test.
- JSONL per-record `workspace_id` assertions.
- API-level repeated generation/export determinism test.
- Phase 1 cookbook notes in `context/foundation/test-plan.md`.

**Out of scope:**

- Auth/session/JWT/workspace membership.
- Frontend, browser, or E2E tests.
- Quality dashboard or quality route mismatch tests.
- Provider normalization `body` sort tie-breaker.
- Durable storage migrations or JSONL schema changes.

## Architecture / Approach

Use existing pytest and FastAPI `TestClient` patterns. Add failing tests around storage validation and boundary gaps, then implement the smallest repository validation change needed before storage/export. Determinism tests use fixed fixtures, fixed timestamps, fixed deterministic `run_id`, and fresh in-memory repositories for independent reruns.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Full-Record Storage Contract | Repository rejects invalid full record tuples, including records outside preview. | Bad records exported after preview-only validation. |
| 2. Workspace Boundary Coverage | `list_records` and `GET /dataset` prove `workspace_id` is required. | Same `run_id` crossing workspaces. |
| 3. API Determinism and JSONL Bytes | Independent API flows produce identical records and JSONL bytes. | API/export drift despite lower-level determinism. |
| 4. Verification and Rollout Notes | Focused backend gate passes and cookbook guidance is updated. | Future tests repeat weak patterns. |

**Prerequisites:** Existing research doc remains the codebase grounding; no new dependency or frontend setup is required.

**Estimated effort:** One focused backend implementation session across four small phases.

## Open Risks & Assumptions

- Current workspace isolation is structural, not authenticated; real ownership enforcement is a future auth slice.
- Provider normalization still has a known `body` tie-breaker edge to handle in Phase 2.
- Full backend pytest is preferred if cheap, but the focused backend gate is the required signal for this rollout phase.

## Success Criteria (Summary)

- Full-record repository validation blocks mixed workspace/run/config records and count drift before storage.
- API route tests prove identical deterministic input yields identical preview JSON and JSONL response bytes.
- Workspace mismatch tests cover repository, `GET /dataset`, and export boundaries with the same `run_id`.
