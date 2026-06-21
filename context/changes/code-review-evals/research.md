---
date: 2026-06-21T11:18:50+02:00
researcher: Codex
git_commit: 4904cacde371dac3a19f0006b31d58095da42088
branch: main
repository: quantitative-sentiment-analysis
topic: "Promptfoo evals for the QSA code review agent"
tags: [research, promptfoo, code-review-agent, evals]
status: complete
last_updated: 2026-06-21
last_updated_by: Codex
---

# Research: Promptfoo Evals For The QSA Code Review Agent

**Date**: 2026-06-21T11:18:50+02:00
**Researcher**: Codex
**Git Commit**: 4904cacde371dac3a19f0006b31d58095da42088
**Branch**: main
**Repository**: quantitative-sentiment-analysis

## Research Question

How should `code-review-evals` introduce promptfoo evals for the existing QSA
code review prompt/agent, comparing OpenAI models only and keeping evals
separate from the GitHub Actions pipeline?

## Summary

The existing review agent already has the important reusable assets: a strict
JSON review schema, a prompt with PR title/body/diff placeholders, and a bad
QSA diff fixture that combines determinism and semantic-safety regressions.
Promptfoo can use the prompt file directly, load the diff as a test variable,
run two OpenAI providers side by side, and apply deterministic JavaScript
assertions against the JSON-like output.

The cleanest first version avoids importing `src/review.ts` because it has a
top-level `main()` call. Instead, evals should reuse the prompt template and
mirror the schema contract in a small CommonJS assertion file. This keeps
promptfoo focused on prompt/model behavior, while the Codex SDK wrapper remains
covered by the existing CLI/workflow checks.

## Detailed Findings

### Current Agent Package

- The review agent is a private ESM Node package (`"type": "module"`) with
  scripts for build, real review, dry-run prompt generation, and typecheck
  (`tools/codex-review-agent/package.json:5`, `tools/codex-review-agent/package.json:7`).
- TypeScript compiles with `module: "NodeNext"` and outputs to `dist/`
  (`tools/codex-review-agent/tsconfig.json:3`).
- Runtime dependencies are only `@openai/codex-sdk` and `zod`; promptfoo is not
  currently installed (`tools/codex-review-agent/package.json:13`).

### Prompt And Schema Reuse

- The prompt template accepts `{{PR_TITLE}}`, `{{PR_BODY}}`, and `{{DIFF}}`
  (`tools/codex-review-agent/prompts/qsa-code-review.md:7`,
  `tools/codex-review-agent/prompts/qsa-code-review.md:9`,
  `tools/codex-review-agent/prompts/qsa-code-review.md:89`).
- The prompt defines the five QSA review criteria and the fail gate rule
  (`tools/codex-review-agent/prompts/qsa-code-review.md:19`,
  `tools/codex-review-agent/prompts/qsa-code-review.md:26`).
- `ReviewSchema` strictly requires `summary`, `risk_level`, `verdict`,
  `overall_score`, the five fixed criteria, `findings`, `tests_to_run`, and
  `cost_control_note` (`tools/codex-review-agent/src/review-schema.ts:24`).
- The existing `src/review.ts` should not be imported directly by evals because
  helper functions are not exported and `main()` runs at module load
  (`tools/codex-review-agent/src/review.ts:241`).

### Fixtures

- The existing fixture already contains the target known-bad behaviors:
  nondeterministic record order, a wall-clock `datetime.now().isoformat()`, and
  unsafe "live-ready trading signals" copy
  (`tools/codex-review-agent/fixtures/simulated-qsa.diff:5`,
  `tools/codex-review-agent/fixtures/simulated-qsa.diff:11`,
  `tools/codex-review-agent/fixtures/simulated-qsa.diff:21`).
- This fixture is enough for the first regression gate because it exercises the
  two most important QSA criteria from the requirements:
  `qsa_semantic_safety` and `deterministic_data_contracts`.

### Promptfoo Documentation

- Promptfoo YAML configs run prompts through test cases and assertions; common
  top-level keys are `prompts`, `providers`, and `tests`.
  Source: <https://www.promptfoo.dev/docs/configuration/guide/>
- Promptfoo supports OpenAI providers such as `openai:gpt-5-mini` and reads the
  API key from `OPENAI_API_KEY`.
  Source: <https://www.promptfoo.dev/docs/providers/openai/>
- JavaScript assertions can be inline or loaded from `file://...`, and throwing
  or returning a failed result marks the assertion failed.
  Source: <https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/>
- `promptfoo eval` exits with code `100` for test failures or pass-rate
  threshold failures, and `1` for other errors.
  Source: <https://www.promptfoo.dev/docs/usage/command-line/>

## Code References

- `tools/codex-review-agent/package.json:7` - existing package scripts.
- `tools/codex-review-agent/prompts/qsa-code-review.md:19` - five review
  criteria in the prompt.
- `tools/codex-review-agent/src/review-schema.ts:24` - strict JSON review
  schema.
- `tools/codex-review-agent/fixtures/simulated-qsa.diff:1` - existing known-bad
  diff fixture.
- `context/changes/code-review-evals/requirements.md:5` - evals are scoped to
  `tools/codex-review-agent`.
- `context/changes/code-review-evals/requirements.md:39` - deterministic
  JavaScript assertions are preferred.

## Architecture Insights

The eval surface should remain side-effect free: promptfoo sends a prompt to
OpenAI and checks the model output. It should not exercise the Codex SDK
runtime, GitHub Actions workflow, artifact writing, or PR comments. That
division keeps M5L3's pipeline and model-eval tasks separate.

Because the package is ESM, promptfoo assertion files should use `.cjs` when
they rely on `module.exports`. That avoids ambiguity with the package-level
`"type": "module"`.

## Historical Context

- `context/changes/ci-code-review-pipeline/plan.md` split promptfoo/model
  comparison out of the CI pipeline change.
- `context/changes/ci-code-review-pipeline/change.md` marks the pipeline change
  implemented, so evals can build on the now-current prompt/schema contract.

## Related Research

- `context/changes/ci-code-review-pipeline/research.md`
- `context/changes/code-review-evals/requirements.md`

## Open Questions

None blocking. The model pair is constrained to OpenAI-only by the user and the
requirements; the first implementation can use `gpt-5-mini` and `gpt-5` as the
small/strong comparison pair.
