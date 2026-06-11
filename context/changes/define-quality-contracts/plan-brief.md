# Define Quality Contracts - Plan Brief

> Full plan: `context/changes/define-quality-contracts/plan.md`

## What & Why

Define the F-01 quality contracts that future slices must share: workspace identity, deterministic run metadata, dataset/export fields, JSONL stability, and BACKTEST-only non-advisory wording. This matters because S-01, S-02, S-03, and the existing S-04 quality view would otherwise duplicate or drift on core fields such as `workspace_id`, `run_id`, `config_version`, `directional_bias`, and source identity.

## Starting Point

The PRD already defines the required dataset fields and guardrails, while S-04 already has view-specific Pydantic schemas and tests for many of the same concepts. There is no shared `contracts` package yet, so dataset generation and export would either duplicate definitions or depend on the quality-view module.

## Desired End State

The project has `context/foundation/quality-contracts.md` as the human-readable source of truth and `src/quantitative_sentiment_analysis/contracts/` as the executable contract package. Tests verify schema bounds, audit fields, workspace isolation, deterministic serialization/fingerprint behavior, semantic safety wording, and compatibility with S-04.

## Key Decisions Made

| Decision | Choice | Why |
| --- | --- | --- |
| Scope | Docs plus code-backed contracts | Keeps the contract readable and enforceable. |
| Contract surface | Shared `contracts` package | Lets S-01/S-02/S-03/S-04 share foundation types without importing from a feature module. |
| Dataset record | PRD minimum plus workspace/run/model/relevance fields | Matches PRD and aligns with existing S-04 metadata. |
| Determinism | Full input fingerprint plus workspace/timeframe/instrument/mode/seed/model/config | Makes rerun identity auditable instead of relying on `run_id` alone. |
| Workspace privacy | Route, record, storage, and export invariant | Prevents cross-workspace leakage across future APIs and exports. |
| Semantic safety | Allowed terms plus banned wording list | Makes BACKTEST-only analytical framing testable. |
| Verification | Unit tests plus S-04 compatibility tests | Catches drift between the foundation contract and existing quality-view work. |

## Scope

**In scope:**

- `context/foundation/quality-contracts.md`.
- Shared Python contracts under `src/quantitative_sentiment_analysis/contracts/`.
- Contract tests for schemas, serialization/fingerprints, safety wording, and S-04 compatibility.
- Minimal S-04 compatibility alignment without changing the public S-04 response shape.
- Downstream handoff notes for S-01/S-02/S-03/S-04.

**Out of scope:**

- Choosing news provider, sentiment thresholds, confidence formula, or visualization scope.
- Implementing auth/workspace UI, news ingestion, sentiment scoring, backtest orchestration, export endpoint, or storage.
- LIVE mode, broker integration, order execution, or investment recommendations.
- Database migrations.

## Architecture / Approach

The plan creates a foundation document first, then mirrors it in a shared Python package. Future feature modules import shared enums/models/helpers from `contracts`; S-04 keeps its API shape but can reuse shared enum definitions and validation helpers. Deterministic JSONL and fingerprint behavior are verified by tests before S-02/S-03 build real dataset/export flows.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Foundation Contract Document | Human-readable source of truth and AGENTS pointer | Accidentally including F-02 policy decisions. |
| 2. Shared Contract Package | Reusable Python contracts and helpers | Creating a dependency from foundation code back into S-04. |
| 3. Contract Verification Tests | Automated schema, serialization, safety tests | Tests becoming too broad and failing on historical planning docs. |
| 4. S-04 Compatibility and Downstream Handoff | Existing quality view aligned with shared contracts | Breaking the current S-04 JSON shape. |
| 5. Final Verification and Handoff | Full verification and next-slice readiness | Calling the contract complete without clear downstream references. |

**Prerequisites:** None; this is the first ready roadmap item.
**Estimated effort:** ~2-3 focused sessions across 5 phases.

## Open Risks & Assumptions

- S-04 is already present in the current worktree, so implementation must preserve its behavior and not revert unrelated changes.
- F-02 still owns provider/scoring/visualization policy, so F-01 must stop at fields and invariants.
- Real S-02 quality-report integration must later cap, sample, paginate, or explicitly limit large chart/detail payloads while keeping metric denominators correct.

## Success Criteria (Summary)

- Future slices can import shared contract definitions instead of duplicating dataset/run/workspace fields.
- Deterministic JSONL/fingerprint behavior is covered by tests.
- Product-facing wording remains BACKTEST-only and analytical, with no recommendation or execution framing.
