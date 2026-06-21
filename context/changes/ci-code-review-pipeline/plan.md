# CI Code Review Pipeline Implementation Plan

## Overview

Build a separate GitHub Actions AI code-review pipeline on top of the existing
`tools/codex-review-agent` package. The pipeline will evaluate QSA pull-request
diffs against five repository-specific review criteria, emit a structured JSON
artifact, and fail mechanically when the review verdict or scores do not meet
the agreed gate.

## Current State Analysis

The repo already contains a local Codex SDK review agent and a separate product
CI workflow. The agent can review a diff and validate a JSON response, but it
does not yet accept PR metadata, does not write an artifact file, and cannot
fail on a valid but negative review result. The existing `.github/workflows/ci.yml`
must remain focused on backend, frontend, and E2E checks.

## Desired End State

After this change, pull requests from the main repository can run an independent
AI review job that:

- installs and builds only `tools/codex-review-agent`;
- calculates the PR diff against the base branch;
- passes PR title, PR body, and diff into the Codex SDK review agent;
- writes a JSON review artifact even when the review fails;
- fails the job when `verdict` is `fail`, any finding is `blocker`, any
  criterion score is below `7`, or `overall_score` is below `7`.

### Key Discoveries

- The current CLI only supports `--dry-run` and `--diff-file`
  (`tools/codex-review-agent/src/review.ts:14`).
- Prompt assembly currently injects only `{{DIFF}}`
  (`tools/codex-review-agent/src/review.ts:77`).
- The current schema has `contract_checks`, but no criterion scores, overall
  score, or verdict (`tools/codex-review-agent/src/review-schema.ts:3`).
- The existing product CI workflow already uses Node `24` and should not be
  modified for this AI review job (`.github/workflows/ci.yml:9`).
- The Codex TypeScript SDK supports `new Codex({ apiKey })`; the local SDK
  forwards that as `CODEX_API_KEY` only to the spawned Codex process.
- The Codex manual warns against exposing `OPENAI_API_KEY` or `CODEX_API_KEY`
  as job-level env in workflows that run repository-controlled code.

## What We're NOT Doing

- No promptfoo evals or model comparison; that belongs to
  `context/changes/code-review-evals/`.
- No OpenRouter or non-OpenAI providers.
- No PR comments, review comments, or write permissions in the first version.
- No changes to `.github/workflows/ci.yml`.
- No product-scope changes to QSA behavior.
- No live trading, broker integration, order execution, or investment
  recommendation wording.

## Implementation Approach

Implement this in two phases. First, upgrade the review agent contract so it can
act as a CI gate. Second, add the separate GitHub Actions workflow and update
operator documentation. Keep the workflow read-only and artifact-based so the
first version is useful without expanding GitHub permissions.

## Critical Implementation Details

### Codex SDK Authentication

Keep `OPENAI_API_KEY` scoped to the review step in GitHub Actions. In the Node
agent, read `process.env.OPENAI_API_KEY` and pass it to `new Codex({ apiKey })`
when present; otherwise keep local Codex auth behavior for developer runs.

### Artifact Before Failure

The review command must write `--output-file` before setting a non-zero exit
code for a failed verdict. This allows the GitHub workflow to upload the JSON
artifact with `if: always()` even when the review blocks the PR.

### Fork Pull Requests

The automatic AI review job should skip pull requests whose head repository is
not the current repository. Fork PRs do not receive non-`GITHUB_TOKEN` secrets,
and this pipeline should not expose an OpenAI key to untrusted code.

## Phase 1: Agent Review Contract and Gate

### Overview

Upgrade the local Codex SDK review agent so it accepts CI inputs, emits the M5L3
review contract, writes an artifact file, and exits non-zero for failed reviews.

### Changes Required

#### 1. Structured Review Schema

**File**: `tools/codex-review-agent/src/review-schema.ts`

**Intent**: Replace the M5L2 `contract_checks` shape with a CI-ready review
contract that carries five scored QSA review criteria, an `overall_score`, and a
mechanical `verdict`.

**Contract**: The exported `ReviewSchema` must validate:

- `summary: string`
- `risk_level: "low" | "medium" | "high"`
- `verdict: "pass" | "fail"`
- `overall_score: integer 1..10`
- `criteria` object with exactly these keys:
  - `qsa_semantic_safety`
  - `deterministic_data_contracts`
  - `workspace_security_boundaries`
  - `test_verification_discipline`
  - `scope_maintainability_discipline`
- each criterion has `score: integer 1..10`, `status: "pass" | "fail" |
  "unknown"`, and `rationale: string`
- `findings[]` keeps `severity`, `file`, `line`, `title`, `details`, and
  `recommendation`
- `tests_to_run: string[]`
- `cost_control_note: string`

#### 2. QSA Review Prompt

**File**: `tools/codex-review-agent/prompts/qsa-code-review.md`

**Intent**: Make the five review criteria first-class in the prompt and include
PR metadata as review context without letting the agent review outside the diff.

**Contract**: The prompt must include placeholders for `{{PR_TITLE}}`,
`{{PR_BODY}}`, and `{{DIFF}}`, describe the five criteria, require scores on a
1-10 scale, and require `verdict` to be `fail` when a blocker, score below `7`,
or overall score below `7` is present.

#### 3. CLI Inputs, Output File, and Gate

**File**: `tools/codex-review-agent/src/review.ts`

**Intent**: Extend the CLI so the same command can run locally and in GitHub
Actions while preserving the existing local diff workflow.

**Contract**: Preserve `--dry-run` and `--diff-file`. Add:

- `--pr-title <title>` with a local default;
- `--pr-body <body>` and/or `--pr-body-file <path>` for CI-safe multiline PR
  descriptions;
- `--output-file <path>` to write the validated JSON review.

The review gate fails when:

- `review.verdict === "fail"`;
- any finding has `severity === "blocker"`;
- any criterion score is below `7`;
- `overall_score` is below `7`.

When `OPENAI_API_KEY` is present, instantiate Codex with
`new Codex({ apiKey: process.env.OPENAI_API_KEY })`. Keep local cached Codex
auth as the fallback when the env var is absent. Run Codex in read-only intent
where SDK options support it.

#### 4. Package Scripts and README

**Files**:

- `tools/codex-review-agent/package.json`
- `tools/codex-review-agent/README.md`

**Intent**: Keep existing local commands working and document the new CI-oriented
options without implying promptfoo work is part of this change.

**Contract**: README must explain local dry-run, local real review with
`OPENAI_API_KEY` or existing Codex auth, `--output-file`, and the gate rules.
Package scripts should remain simple; add only scripts that materially simplify
verification.

### Success Criteria

#### Automated Verification

- TypeScript typecheck passes:
  `npm --prefix tools/codex-review-agent run typecheck`
- Build passes:
  `npm --prefix tools/codex-review-agent run build`
- Dry-run prompt generation accepts PR metadata:
  `npm --prefix tools/codex-review-agent run review:dry -- --diff-file fixtures/simulated-qsa.diff --pr-title "Simulated unsafe diff" --pr-body "Exercise the QSA review gate"`

#### Manual Verification

- With a valid local `OPENAI_API_KEY` or Codex login, the simulated unsafe diff
  writes JSON to a temporary output file.
- The simulated unsafe diff produces a failing gate because it contains
  BACKTEST/semantic-safety and determinism risks.
- The JSON output includes all five criteria, `overall_score`, `verdict`,
  findings, `tests_to_run`, and `cost_control_note`.

**Implementation Note**: After completing this phase and all automated
verification passes, pause for manual confirmation before proceeding to Phase 2.

---

## Phase 2: GitHub Actions Workflow and Operator Documentation

### Overview

Add a separate read-only GitHub Actions workflow that runs the review agent on
pull requests and manual dispatch, uploads the JSON result, and leaves the
existing product CI untouched.

### Changes Required

#### 1. AI Review Workflow

**File**: `.github/workflows/ai-code-review.yml`

**Intent**: Introduce a separate M5L3 AI review pipeline without modifying the
existing backend/frontend/E2E CI workflow.

**Contract**: The workflow must:

- trigger on `pull_request` and `workflow_dispatch`;
- expose a `workflow_dispatch` input `base_ref` defaulting to `main`;
- use `permissions: contents: read`;
- skip automatic runs for fork PRs;
- use `actions/checkout@v6` with `fetch-depth: 0` and
  `persist-credentials: false`;
- use Node `24`;
- install only `tools/codex-review-agent` dependencies;
- build the agent;
- calculate a unified diff against the PR base for PR runs and against
  `base_ref` for manual runs;
- pass PR title/body and diff path to the review command;
- scope `OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}` only to the review step;
- write the review result to a JSON file under `$RUNNER_TEMP`;
- upload the JSON artifact with `if: always()`.

#### 2. Workflow Result Handling

**File**: `.github/workflows/ai-code-review.yml`

**Intent**: Ensure a failed review blocks the job while still preserving the
artifact for inspection.

**Contract**: The review step may exit non-zero when the gate fails. The artifact
upload step must still run. The first version should rely on the job status and
artifact; it must not request `pull-requests: write` or post PR comments.

#### 3. Documentation

**File**: `tools/codex-review-agent/README.md`

**Intent**: Document how to run the agent locally, how the GitHub workflow uses
it, and what secret is required.

**Contract**: README must state that GitHub needs an `OPENAI_API_KEY` secret,
that fork PRs are skipped automatically, and that promptfoo/model comparison is
handled by the separate `code-review-evals` change.

### Success Criteria

#### Automated Verification

- Workflow file exists at `.github/workflows/ai-code-review.yml`.
- TypeScript typecheck still passes:
  `npm --prefix tools/codex-review-agent run typecheck`
- Build still passes:
  `npm --prefix tools/codex-review-agent run build`
- Git whitespace check passes for the changed workflow and agent files:
  `git diff --check -- .github/workflows/ai-code-review.yml tools/codex-review-agent context/changes/ci-code-review-pipeline`

#### Manual Verification

- A maintainer can trigger `AI Code Review` with `workflow_dispatch` on the
  branch after `OPENAI_API_KEY` is configured in GitHub Secrets.
- The workflow uploads a JSON review artifact.
- A failing review result fails the workflow job after the artifact is written.
- Existing `.github/workflows/ci.yml` still appears unchanged in this change.

**Implementation Note**: After completing this phase and all automated
verification passes, pause for manual confirmation before closing the plan.

---

## Testing Strategy

### Unit/Contract Checks

- TypeScript typecheck validates the CLI, schema, and gate helper types.
- Zod validation rejects malformed review JSON and score values outside `1..10`.
- The gate helper must treat `verdict=fail`, blocker findings, criterion scores
  below `7`, and `overall_score < 7` as failures.

### Integration Checks

- Dry-run verifies prompt assembly with PR title/body/diff inputs without making
  an API call.
- A real local review against `fixtures/simulated-qsa.diff` verifies the Codex
  SDK path, schema validation, output-file behavior, and failed gate behavior.
- GitHub `workflow_dispatch` verifies checkout, diff generation, scoped secret
  usage, artifact upload, and job failure behavior.

### Manual Testing Steps

1. Export or otherwise provide a valid `OPENAI_API_KEY` in the local shell.
2. Run the built review agent against `fixtures/simulated-qsa.diff` with
   `--output-file`.
3. Confirm the output JSON is valid and includes the five criteria.
4. Confirm the command exits non-zero for the unsafe fixture after writing the
   output file.
5. Trigger the GitHub workflow manually after pushing the branch and confirm the
   artifact exists.

## Performance Considerations

The workflow reviews only the PR diff and PR metadata, not the full repository
or generated artifacts. Keeping PR comments out of scope reduces permissions and
avoids extra API calls in the first version.

## Migration Notes

No database, API, or product data migration is required. This change adds a new
CI workflow and upgrades an isolated tool package.

## References

- Related research: `context/changes/ci-code-review-pipeline/research.md`
- Requirements: `context/changes/ci-code-review-pipeline/requirements.md`
- Separate evals change: `context/changes/code-review-evals/requirements.md`
- QSA quality contracts: `context/foundation/quality-contracts.md`
- Existing agent CLI: `tools/codex-review-agent/src/review.ts`
- Existing schema: `tools/codex-review-agent/src/review-schema.ts`
- Existing prompt: `tools/codex-review-agent/prompts/qsa-code-review.md`
- Existing product CI: `.github/workflows/ci.yml`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Agent Review Contract and Gate

#### Automated

- [x] 1.1 TypeScript typecheck passes
- [x] 1.2 Build passes
- [x] 1.3 Dry-run prompt generation accepts PR metadata

#### Manual

- [x] 1.4 Simulated unsafe diff writes JSON with a valid local OpenAI/Codex auth path
- [x] 1.5 Simulated unsafe diff fails the review gate
- [x] 1.6 JSON output includes all required M5L3 review fields

### Phase 2: GitHub Actions Workflow and Operator Documentation

#### Automated

- [ ] 2.1 Workflow file exists
- [ ] 2.2 TypeScript typecheck still passes
- [ ] 2.3 Build still passes
- [ ] 2.4 Git whitespace check passes

#### Manual

- [ ] 2.5 Workflow dispatch can be triggered by a maintainer
- [ ] 2.6 Workflow uploads a JSON review artifact
- [ ] 2.7 Failing review result fails the workflow job after artifact upload
- [ ] 2.8 Existing product CI workflow remains unchanged
