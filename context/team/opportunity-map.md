# Opportunity Map

## Context

- **Project / context**: Quantitative Sentiment Analysis - Python/FastAPI service for deterministic BTCUSD BACKTEST sentiment datasets.
- **Data constraint**: Mock / local / read-only / non-sensitive. The first version reads only repository files, git diff, docs, and tests. It must not read real customer data, production data, secrets, or generated datasets with real workspace identifiers.
- **Date**: 2026-06-20

## Map

| Signal | Existing / default response | Thin complement | First useful version | Data risk | Direction if valuable |
|---|---|---|---|---|---|
| Review must repeatedly check whether a change violates `BACKTEST-only`, `directional bias`, `LONG` / `SHORT` / `FLAT`, or semantic-safety wording. | Manual review, `rg`, AGENTS.md, `quality-contracts.md`, and existing safety tests. | Semantic risk digest over diff, docs, API/UI copy, and tests. | Local Markdown report listing suspicious wording, touched surfaces, and suggested tests. | Local/read-only/non-sensitive. | Internal tool - Review / CI gate. |
| JSONL determinism, workspace isolation, run metadata, source identity, and semantic-safety contracts are spread across docs, schemas, exports, and tests. | Contract docs, Pydantic models, route tests, export tests, and reviewer memory. | Contract impact digest mapping changed paths to known quality contracts. | Markdown report with touched contracts, files to inspect, test commands, and missing evidence. | Local/read-only/non-sensitive. | Internal tool - Review / CI gate. |
| For backend/frontend changes, reviewers manually infer the smallest relevant test set. | Run broad pytest/frontend test suites or rely on CI. | Test selection helper based on changed paths and contract categories. | Static path-to-test checklist maintained in Markdown or a simple read-only script. | Local/read-only/non-sensitive. | Internal tool - Review / CI gate. |
| `context/changes/*` contains plans, research, reviews, follow-ups, and verification in mixed states. | Manual `find`, `rg`, `git status`, and folder browsing. | Change status digest for missing artifacts and incomplete follow-up evidence. | One-off Markdown scan of active change folders, statuses, reviews, and verification files. | Local/read-only/non-sensitive. | Internal tool - Async / remote work. |
| Backend API schemas and frontend TypeScript types can drift across several files. | API tests, frontend tests, and manual review. | API drift checklist linking changed routes/schemas to frontend `api.ts`, `types.ts`, and tests. | Markdown checklist for one change: endpoint, backend schema, frontend type, backend test, frontend test. | Local/read-only/non-sensitive. | Internal tool - Review / CI gate. |

## Recommended First Candidate

```text
Candidate:
QSA Contract Risk Digest

Reads:
git diff, AGENTS.md, context/foundation/prd.md,
context/foundation/quality-contracts.md, tests/contracts/*,
tests/backtest_dataset/*, tests/backtest_quality/*, changed backend files,
changed frontend API/type files, and product-facing copy touched by the change.

Returns:
A Markdown report with touched contracts, suspicious semantic-safety wording,
related source/test files, suggested test commands, and missing validation evidence.

Does not do:
It does not block merges, edit code, replace human review, send data outside the
repository, analyze real datasets, read secrets, or frame directional bias as an
investment recommendation or executable trading signal.

Data risk:
Local/read-only/non-sensitive. If a later version reads real exports or customer
workspace data, access limits, sanitization, and auditability must be designed
before implementation.

Direction if it proves valuable:
Internal tool - Review / CI gate.
```

## Why This Candidate

This candidate earns the first slot because the friction repeats across many changes and combines several sources: product rules, quality contracts, backend schemas, frontend copy, and tests. The current response is workable but depends heavily on reviewer memory. A thin digest can help without replacing existing tools or becoming a new system of record. The first version is cheap: a local Markdown report for one real change is enough to test whether it shortens review or catches a missed contract risk.

The other candidates are useful but slightly less urgent. Test selection and API drift checks can become sections inside the same digest. The `context/changes/*` status digest is valuable, but it is more about project hygiene than product safety. Starting with contract risk keeps the helper tied to the repository's strongest hard rules: determinism, workspace isolation, and BACKTEST-only semantic safety.

## Next Direction If Valuable

Validate first with `10x-mom-test`. The first validation should ask reviewers and future users about recent review situations, current workarounds, missed risks, and the cost of manually assembling contract context. If the signal survives, shape a narrow first implementation through `/10x-shape` or, if the scope stays small, use `/10x-new` -> `/10x-research` -> `/10x-plan` -> `/10x-implement`.
