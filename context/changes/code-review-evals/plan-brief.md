# Code Review Evals - Plan Brief

> Full plan: `context/changes/code-review-evals/plan.md`
> Research: `context/changes/code-review-evals/research.md`

## What & Why

Add promptfoo evals for the QSA code-review prompt so model choice is based on a
repeatable pass/fail matrix rather than one PR run. This covers M5L3 task 3 and
stays separate from the GitHub Actions pipeline.

## Starting Point

The review agent already has a strict JSON schema, a QSA review prompt, and a
known-bad diff fixture. The eval change currently has requirements only.

## Desired End State

`tools/codex-review-agent` has a promptfoo config comparing `gpt-5-mini` and
`gpt-5` using `OPENAI_API_KEY`. Deterministic JS assertions verify valid JSON,
failed verdict, expected findings, and low scores for known bad semantic-safety
and determinism cases.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Provider scope | OpenAI only | Matches user request and avoids OpenRouter/non-OpenAI setup. | Requirements |
| Model pair | `gpt-5-mini` and `gpt-5` | Gives small/strong comparison while staying in one provider family. | Plan |
| Assertions | Deterministic JS | Avoids judge-model cost and flake for the first regression gate. | Requirements |
| Prompt reuse | Use prompt file directly | Avoids importing `review.ts`, which runs `main()` on load. | Research |
| Dependency path | Pinned `npx promptfoo@0.121.17` | Keeps promptfoo out of the local lockfile after install proved heavy on `/mnt/e`. | Plan |

## Scope

**In scope:**

- Promptfoo config under `tools/codex-review-agent`.
- JS assertion script and no-cost self-test.
- README instructions for running real model evals.
- 10x research, plan, and progress tracking.

**Out of scope:**

- GitHub Actions changes.
- OpenRouter or non-OpenAI providers.
- `llm-rubric` judge assertions.
- Codex SDK runtime refactors.

## Architecture / Approach

Promptfoo loads `prompts/qsa-code-review.md`, injects PR metadata and the
existing simulated diff, runs two OpenAI providers, and calls a local CommonJS
assertion script. The script parses model output and checks the review contract
plus QSA-specific expected failures.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Promptfoo Eval Harness | Config, assertion script, self-test, package scripts | Assertion too strict or too loose |
| 2. Evals Documentation And Real Run Path | README and operator run path | Real eval consumes API cost |

**Prerequisites:** local or GitHub `OPENAI_API_KEY` for real eval runs.
**Estimated effort:** one short implementation session plus one manual API run.

## Open Risks & Assumptions

- Promptfoo's matrix output is the source of pass/fail, timing, and cost
  evidence; generated eval outputs should not be committed by default.
- If model output is consistently fenced or explanatory, the assertion parser
  must tolerate fenced JSON but still reject non-JSON final answers.

## Success Criteria

- No-cost assertion self-test passes.
- Existing review agent typecheck/build still pass.
- Real `npm run eval:review` can compare two OpenAI models when
  `OPENAI_API_KEY` is set.
