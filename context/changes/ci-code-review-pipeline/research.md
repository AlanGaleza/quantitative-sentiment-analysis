---
date: 2026-06-21T09:56:27+02:00
researcher: Codex
git_commit: 1dccbf39f552777f373403df9873b027fd4809b1
branch: main
repository: quantitative-sentiment-analysis
topic: "CI code review pipeline for codex-review-agent"
tags: [research, ci, github-actions, codex-review-agent, code-review]
status: complete
last_updated: 2026-06-21
last_updated_by: Codex
---

# Research: CI code review pipeline for codex-review-agent

**Date**: 2026-06-21T09:56:27+02:00
**Researcher**: Codex
**Git Commit**: 1dccbf39f552777f373403df9873b027fd4809b1
**Branch**: main
**Repository**: quantitative-sentiment-analysis

## Research Question

How should the existing local Codex SDK review agent be turned into a separate GitHub Actions code-review pipeline for M5L3, without mixing in the promptfoo/model-comparison work?

## Summary

The repo already has a local Codex SDK review agent under `tools/codex-review-agent/` and a separate production CI workflow at `.github/workflows/ci.yml`. The new AI review pipeline should be a separate workflow, not a modification of the existing backend/frontend/e2e CI. The agent needs M5L3 structured output upgrades before the workflow can act as a real gate: five criterion scores, `overall_score`, `verdict`, PR title/body inputs, output-file artifact support, and deterministic non-zero exit behavior for failed verdicts.

Promptfoo evals are explicitly out of this change and belong to `context/changes/code-review-evals/`.

## Detailed Findings

### Existing Codex review agent

- The agent package is isolated from the main FastAPI app at `tools/codex-review-agent/` and has its own package metadata and lockfile.
- Runtime scripts are local-focused: `build`, `review`, `review:dry`, and `typecheck` ([tools/codex-review-agent/package.json:7](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/package.json:7)).
- The package depends on `@openai/codex-sdk` and `zod` ([tools/codex-review-agent/package.json:13](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/package.json:13)).
- The README still describes the package as an M5L2 local experiment and says M5L3 CI wiring is future work ([tools/codex-review-agent/README.md:3](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/README.md:3), [tools/codex-review-agent/README.md:7](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/README.md:7)).
- Local `/mnt/e` installs need `npm install --no-bin-links` because regular npm bin links hit chmod problems on the Windows/WSL mount ([tools/codex-review-agent/README.md:12](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/README.md:12)).

### Agent input/output limitations

- Current CLI options support only `--dry-run` and `--diff-file`; there is no PR title/body input and no output artifact path ([tools/codex-review-agent/src/review.ts:14](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review.ts:14), [tools/codex-review-agent/src/review.ts:31](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review.ts:31)).
- Prompt assembly only replaces `{{DIFF}}`, so the prompt cannot yet receive PR title/body or explicit CI context ([tools/codex-review-agent/src/review.ts:77](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review.ts:77)).
- The agent prints validated JSON to stdout only; it cannot write a stable JSON artifact file for GitHub Actions upload ([tools/codex-review-agent/src/review.ts:110](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review.ts:110)).
- The process exits non-zero only for invalid JSON/schema/runtime failures. A valid response with blocking findings would still exit 0 because there is no `verdict` gate yet ([tools/codex-review-agent/src/review.ts:100](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review.ts:100)).

### Structured output gap

- Current schema validates `summary`, `risk_level`, `findings`, `contract_checks`, `tests_to_run`, and `cost_control_note` ([tools/codex-review-agent/src/review-schema.ts:3](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review-schema.ts:3)).
- The prompt asks for a `contract_checks` object, not scored M5L3 review criteria ([tools/codex-review-agent/prompts/qsa-code-review.md:14](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/prompts/qsa-code-review.md:14), [tools/codex-review-agent/prompts/qsa-code-review.md:30](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/prompts/qsa-code-review.md:30)).
- M5L3 needs first-class criterion-level scoring on five QSA dimensions, an `overall_score`, and a mechanical `pass` / `fail` verdict before the CI workflow can fail for review reasons.

### Existing CI workflow

- Existing `.github/workflows/ci.yml` is the main product CI and should stay independent ([.github/workflows/ci.yml:1](/mnt/e/quantitative-sentiment-analysis/.github/workflows/ci.yml:1)).
- It runs on pushes to `main` and pull requests ([.github/workflows/ci.yml:3](/mnt/e/quantitative-sentiment-analysis/.github/workflows/ci.yml:3)).
- It uses Python `3.12` and Node `24` as global workflow env values ([.github/workflows/ci.yml:9](/mnt/e/quantitative-sentiment-analysis/.github/workflows/ci.yml:9)).
- Backend CI runs PostgreSQL, `uv sync --locked --dev`, Alembic migrations, ruff, pyright, and pytest ([.github/workflows/ci.yml:16](/mnt/e/quantitative-sentiment-analysis/.github/workflows/ci.yml:16)).
- Frontend CI installs `frontend` dependencies and runs tests/build ([.github/workflows/ci.yml:53](/mnt/e/quantitative-sentiment-analysis/.github/workflows/ci.yml:53)).
- E2E CI installs root Playwright dependencies and frontend dependencies before `npm run e2e` ([.github/workflows/ci.yml:70](/mnt/e/quantitative-sentiment-analysis/.github/workflows/ci.yml:70)).
- Root `package.json` is E2E-only and should not be used for review-agent dependency installation ([package.json:2](/mnt/e/quantitative-sentiment-analysis/package.json:2)).

### GitHub Actions design constraints

- The AI review workflow should use a new `.github/workflows/ai-code-review.yml`.
- The workflow should use `pull_request` and `workflow_dispatch`.
- The job should request minimal permissions, initially `contents: read`, because PR comments/status checks are out of scope.
- GitHub secrets should be passed through the `secrets` context and scoped only to the review step. GitHub documents that non-`GITHUB_TOKEN` secrets are not passed to workflows triggered from forked repositories, and Dependabot events also do not receive secrets. Source: GitHub Docs, "Using secrets in GitHub Actions" (lines 413-434 from the fetched page).
- `actions/checkout` fetches one commit by default; use `fetch-depth: 0` for full history when calculating diffs against the base branch. It also persists credentials by default, so set `persist-credentials: false` when write access is not needed. Source: `actions/checkout` README (fetched lines 329-334, 423-425).
- Review should install only `tools/codex-review-agent` dependencies, then run `npm run build` from that working directory.
- `dist/` and `node_modules/` are ignored globally, so CI must build the agent from source every run ([.gitignore:14](/mnt/e/quantitative-sentiment-analysis/.gitignore:14), [.gitignore:18](/mnt/e/quantitative-sentiment-analysis/.gitignore:18)).
- Use artifact upload after the review step with `if: always()` so failed reviews still leave a JSON result. `actions/upload-artifact` supports `if-no-files-found: error` and `retention-days` for short-lived artifacts. Source: `actions/upload-artifact` README (fetched lines 368-390 and 586-599).

### Codex authentication and runtime

- Local `codex login status` reports `Logged in using ChatGPT`, so local runs can use existing Codex auth.
- The CI path should use the already configured GitHub secret `OPENAI_API_KEY`; plan should verify how the Codex SDK consumes it in GitHub Actions.
- Codex docs distinguish CLI/session authentication from API-key automation. The local SDK run starts `new Codex()` and relies on local Codex runtime/auth ([tools/codex-review-agent/src/review.ts:95](/mnt/e/quantitative-sentiment-analysis/tools/codex-review-agent/src/review.ts:95)).
- Current OpenAI Codex manual says Codex SDK is intended for CI/CD and internal tools, and the TypeScript library requires Node 18+; this package already satisfies the Node version when CI uses Node 24.

## Code References

- `context/changes/ci-code-review-pipeline/requirements.md` - Source requirements for the split pipeline-only change.
- `context/changes/code-review-evals/requirements.md` - Separate promptfoo/model-comparison change.
- `tools/codex-review-agent/src/review.ts:14` - CLI option shape currently lacks PR metadata and artifact output.
- `tools/codex-review-agent/src/review.ts:77` - Prompt assembly currently injects only diff content.
- `tools/codex-review-agent/src/review.ts:95` - SDK starts `new Codex()`.
- `tools/codex-review-agent/src/review.ts:100` - Schema validation is the only current gate.
- `tools/codex-review-agent/src/review.ts:110` - Valid JSON currently prints to stdout only.
- `tools/codex-review-agent/src/review-schema.ts:3` - Existing Zod schema.
- `tools/codex-review-agent/prompts/qsa-code-review.md:6` - Existing QSA-specific rules.
- `tools/codex-review-agent/prompts/qsa-code-review.md:14` - Existing JSON output contract.
- `.github/workflows/ci.yml:1` - Existing product CI workflow.
- `.github/workflows/ci.yml:9` - Existing CI Node/Python versions.
- `tools/codex-review-agent/package.json:7` - Existing agent scripts.
- `tools/codex-review-agent/README.md:12` - `/mnt/e` install caveat.
- `.gitignore:14` and `.gitignore:18` - Build outputs and root `node_modules` are ignored.

## Architecture Insights

- Keep AI review as a separate workflow from product CI. This isolates LLM runtime/secrets from backend/frontend/e2e checks and makes 10xChampion evidence easier to capture.
- Upgrade the agent before the workflow becomes a gate. Without `verdict` and criterion scores, GitHub Actions can only fail on runtime errors, not review quality.
- Keep PR comments/status checks out of the first implementation. They require write permissions, broader prompt-injection analysis, and more GitHub API behavior than the required M5L3 minimum.
- Prefer artifact output over parsing stdout in workflow glue. `--output-file` makes local and CI behavior explicit and allows `actions/upload-artifact` to publish the result even when the agent exits non-zero.
- Promptfoo belongs to a separate change. The pipeline can create the structured output contract that promptfoo later evaluates.

## Historical Context

- `context/changes/codex-review-agent/verification.md` records the M5L2 local agent verification: typecheck/build/dry-run passed, and a real Codex SDK run returned valid JSON identifying deterministic JSONL and semantic-safety failures.
- `context/team/opportunity-map.md` selected `QSA Contract Risk Digest` as a valuable internal helper for contract-aware reviews. The CI review pipeline is a concrete continuation of that idea.
- `context/foundation/quality-contracts.md` is the canonical source for deterministic JSONL, workspace isolation, dataset record, and semantic-safety contracts that should drive the five review criteria.

## Related Research

- `context/changes/codex-review-agent/verification.md`
- `context/team/opportunity-map.md`
- `context/foundation/quality-contracts.md`
- `context/changes/code-review-evals/requirements.md`

## Open Questions

None for research. Planning should still confirm the exact CI trigger behavior for fork PRs, verdict threshold, and whether `workflow_dispatch` needs base/head inputs or can use a default local diff strategy.
