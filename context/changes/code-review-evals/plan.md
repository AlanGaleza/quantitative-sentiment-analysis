# Code Review Evals Implementation Plan

## Overview

Add a small promptfoo eval suite for `tools/codex-review-agent` so the same QSA
code-review prompt can be compared across two OpenAI models with deterministic
assertions. This implements M5L3 task 3 while keeping model evals separate from
the already implemented GitHub Actions review pipeline.

## Current State Analysis

The code review agent already has a prompt, schema, CLI gate, GitHub workflow,
and known-bad diff fixture. The `code-review-evals` change currently has only
requirements and no promptfoo configuration, assertion script, docs, or plan
progress.

## Desired End State

`tools/codex-review-agent` contains a promptfoo config that runs the QSA review
prompt against two OpenAI models, using `OPENAI_API_KEY` from the environment.
The eval checks that the known-bad diff produces valid review JSON, fails the
review gate, identifies semantic-safety and determinism regressions, and assigns
sub-threshold scores to those criteria. A maintainer can run the eval locally
and use promptfoo's matrix output for pass/fail, cost, and timing comparison.

### Key Discoveries

- Promptfoo can use `prompts`, `providers`, and `tests` in YAML and can load
  variables from `file://...` paths.
- Promptfoo OpenAI providers use `OPENAI_API_KEY`.
- Promptfoo JavaScript assertions can be loaded from `file://...`.
- The existing bad QSA fixture already covers nondeterminism, wall-clock output,
  and unsafe trading-signal wording.
- Importing `src/review.ts` into evals is unsafe without refactor because it
  runs `main()` at module load.

## What We're NOT Doing

- No GitHub Actions changes in this task.
- No OpenRouter or non-OpenAI providers.
- No `llm-rubric` model-graded assertions in the first version.
- No Codex SDK runtime changes unrelated to evalability.
- No generated datasets, product API changes, or QSA domain behavior changes.

## Implementation Approach

Keep evals inside `tools/codex-review-agent` and avoid adding heavy local
promptfoo dependencies to the repo. Add a pinned `npx promptfoo@0.121.17`
script, a `promptfooconfig.yaml`, a CommonJS assertion file, and a self-test for
the assertion logic. Use the existing prompt and fixture directly.

## Phase 1: Promptfoo Eval Harness

### Overview

Create the promptfoo config and deterministic assertion harness.

### Changes Required

#### 1. Promptfoo Config

**File**: `tools/codex-review-agent/promptfooconfig.yaml`

**Intent**: Define the prompt, OpenAI model pair, known-bad test case, and
assertion hook.

**Contract**: The config must use `prompts/qsa-code-review.md`, providers
`openai:gpt-5-mini` and `openai:gpt-5`, and the existing
`fixtures/simulated-qsa.diff` through `vars.DIFF`.

#### 2. Deterministic Assertion Script

**File**: `tools/codex-review-agent/evals/assert-qsa-review.cjs`

**Intent**: Validate model output without a judge model.

**Contract**: The assertion must parse plain or fenced JSON, check the review
contract shape, enforce expected verdict and criterion score bounds from
`context.config`, and verify required evidence groups in the output.

#### 3. Assertion Self-Test

**File**: `tools/codex-review-agent/evals/assert-qsa-review.self-test.cjs`

**Intent**: Make assertion logic testable without OpenAI calls.

**Contract**: The self-test must pass for a representative bad-review JSON and
fail for a representative false-pass JSON.

#### 4. Package Scripts

**File**: `tools/codex-review-agent/package.json`

**Intent**: Expose repeatable commands without forcing promptfoo into the local
lockfile.

**Contract**: Add `eval:review` using pinned `npx --yes promptfoo@0.121.17` and
`eval:assertions` using local Node only.

### Success Criteria

#### Automated Verification

- Assertion self-test passes:
  `npm --prefix tools/codex-review-agent run eval:assertions`
- TypeScript typecheck still passes:
  `npm --prefix tools/codex-review-agent run typecheck`
- Build still passes:
  `npm --prefix tools/codex-review-agent run build`
- Promptfoo config and assertion files pass whitespace check:
  `git diff --check -- tools/codex-review-agent context/changes/code-review-evals`

#### Manual Verification

- Review the promptfoo config and confirm it compares only OpenAI models.
- Confirm no API key or eval output is committed.

**Implementation Note**: After automated verification, continue to Phase 2
without running the real model eval unless a valid `OPENAI_API_KEY` is present
and the operator accepts the API-cost tradeoff.

---

## Phase 2: Evals Documentation And Real Run Path

### Overview

Document how to run the model comparison and how to interpret the promptfoo
matrix.

### Changes Required

#### 1. README Updates

**File**: `tools/codex-review-agent/README.md`

**Intent**: Add concise operator instructions for promptfoo evals.

**Contract**: Document `OPENAI_API_KEY`, `npm run eval:review`, the two OpenAI
models, expected failing fixture behavior, and the fact that promptfoo reports
pass/fail, cost, and timing.

#### 2. Change Plan Progress

**File**: `context/changes/code-review-evals/plan.md`

**Intent**: Track implementation state for the 10x workflow.

**Contract**: Flip only the canonical progress checkboxes as verification
passes; keep manual API-cost run separate from automated no-cost checks.

### Success Criteria

#### Automated Verification

- README mentions promptfoo eval command and `OPENAI_API_KEY`.
- Real eval command is available in package scripts:
  `npm --prefix tools/codex-review-agent run eval:review -- --help`

#### Manual Verification

- With `OPENAI_API_KEY` set, run:
  `npm --prefix tools/codex-review-agent run eval:review`
- Confirm promptfoo compares `gpt-5-mini` and `gpt-5` side by side.
- Confirm the promptfoo matrix shows pass/fail plus cost and timing.

---

## Testing Strategy

### Unit/Contract Checks

- Run the assertion self-test locally without network or OpenAI cost.
- Keep TypeScript typecheck/build passing for the existing agent.

### Integration Checks

- Use `npm run eval:review -- --help` to verify the pinned promptfoo runner is
  available without executing model calls.
- A real promptfoo eval is manual because it consumes `OPENAI_API_KEY`.

### Manual Testing Steps

1. Export `OPENAI_API_KEY` in the shell.
2. Run `npm --prefix tools/codex-review-agent run eval:review`.
3. Confirm both OpenAI providers appear in the matrix.
4. Confirm the known-bad QSA fixture fails unless the model identifies the
   determinism and semantic-safety problems.
5. Save screenshots or copied matrix output if needed for course evidence.

## Performance Considerations

The first eval suite uses one known-bad diff and two providers, limiting cost to
two model calls per run. Avoid `llm-rubric` until deterministic assertions are
insufficient.

## Migration Notes

No data migration is required. This change adds eval files and scripts only.

## References

- Related research: `context/changes/code-review-evals/research.md`
- Requirements: `context/changes/code-review-evals/requirements.md`
- Prompt: `tools/codex-review-agent/prompts/qsa-code-review.md`
- Schema: `tools/codex-review-agent/src/review-schema.ts`
- Fixture: `tools/codex-review-agent/fixtures/simulated-qsa.diff`
- Promptfoo configuration docs: <https://www.promptfoo.dev/docs/configuration/guide/>
- Promptfoo OpenAI provider docs: <https://www.promptfoo.dev/docs/providers/openai/>
- Promptfoo JavaScript assertion docs: <https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/>

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Promptfoo Eval Harness

#### Automated

- [x] 1.1 Assertion self-test passes
- [x] 1.2 TypeScript typecheck still passes
- [x] 1.3 Build still passes
- [x] 1.4 Promptfoo config and assertion files pass whitespace check

#### Manual

- [ ] 1.5 Promptfoo config compares only OpenAI models
- [ ] 1.6 No API key or eval output is committed

### Phase 2: Evals Documentation And Real Run Path

#### Automated

- [x] 2.1 README mentions promptfoo eval command and OPENAI_API_KEY
- [x] 2.2 Real eval command is available in package scripts

#### Manual

- [ ] 2.3 Real promptfoo eval runs with OPENAI_API_KEY
- [ ] 2.4 Promptfoo compares gpt-5-mini and gpt-5 side by side
- [ ] 2.5 Promptfoo matrix shows pass/fail plus cost and timing
