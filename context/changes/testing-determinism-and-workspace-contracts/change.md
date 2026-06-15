---
change_id: testing-determinism-and-workspace-contracts
title: Test determinism and workspace contracts
status: implemented
created: 2026-06-15
updated: 2026-06-15
archived_at: null
---

## Notes

Open a change folder for rollout Phase 1 of context/foundation/test-plan.md: "Determinism and workspace contracts".
Risks covered: #1, #2. Test types planned: contract + API integration.
Risk response intent:
- #1: prove identical input and deterministic run metadata produce identical records and identical JSONL bytes.
- #2: prove every storage/API/export boundary requires matching workspace_id; run_id alone is not sufficient for access.
After creating the folder, follow the downstream continuation rule.
