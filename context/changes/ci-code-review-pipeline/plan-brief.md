# CI Code Review Pipeline - Plan Brief

> Full plan: `context/changes/ci-code-review-pipeline/plan.md`
> Research: `context/changes/ci-code-review-pipeline/research.md`

## What & Why

We are turning the local Codex SDK review agent into a separate AI code-review
pipeline for M5L3. The goal is to produce a real CI artifact and gate for QSA
pull requests without mixing in promptfoo/model-comparison work.

## Starting Point

`tools/codex-review-agent` already reviews a diff locally and validates JSON, but
it lacks PR metadata, criterion scores, `overall_score`, `verdict`,
`--output-file`, and CI failure behavior. The existing `.github/workflows/ci.yml`
runs backend/frontend/E2E checks and should stay independent.

## Desired End State

Pull requests from the main repo can run a separate `AI Code Review` workflow.
The job builds the agent, reviews the PR diff with Codex SDK, uploads a JSON
artifact, and fails if the review verdict, blocker findings, or scores violate
the agreed gate.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Change split | Pipeline only; promptfoo stays in `code-review-evals` | Keeps M5L3 CI wiring separate from eval/model comparison work. | Requirements |
| Workflow location | New `.github/workflows/ai-code-review.yml` | Avoids coupling LLM/secrets behavior to product CI. | Research |
| Fork PR behavior | Skip automatic AI review for forks | Non-`GITHUB_TOKEN` secrets are not available to fork PRs and should not be exposed. | Plan |
| Gate threshold | Fail on `verdict=fail`, blocker, any criterion `<7`, or `overall_score <7` | Gives a clear mechanical DoD gate. | Plan |
| Workflow dispatch | Add optional `base_ref`, default `main` | Allows manual branch testing without hard-coding only PR context. | Plan |
| Output handling | Always write and upload JSON artifact | Preserves evidence even when the review blocks the job. | Plan |
| PR comments | Out of scope for first version | Keeps permissions at `contents: read`. | Plan |
| Auth path | Pass step-scoped `OPENAI_API_KEY` into `new Codex({ apiKey })` | Uses the SDK-supported API-key path without job-level secret exposure. | Research / Plan |

## Scope

**In scope:**

- Five QSA review criteria with 1-10 scores.
- Zod schema update with `overall_score` and `verdict`.
- PR title/body/diff inputs for the agent.
- `--output-file` JSON artifact support.
- Mechanical gate and non-zero exit for failed review.
- Separate GitHub Actions workflow.
- README updates for local and CI usage.

**Out of scope:**

- Promptfoo evals and model comparison.
- OpenRouter or non-OpenAI providers.
- PR comments or write permissions.
- Changes to existing product CI.
- Any live/broker/order/investment-recommendation product behavior.

## Architecture / Approach

The agent remains an isolated Node package under `tools/codex-review-agent`.
GitHub Actions checks out the repo, installs only that package, builds it,
generates a PR diff, then runs the compiled CLI with a step-scoped
`OPENAI_API_KEY`. The CLI validates Codex output, writes JSON, evaluates the
gate, and exits with the correct status.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Agent Review Contract and Gate | Schema, prompt, CLI inputs, artifact output, and gate behavior | Codex SDK auth/output handling must work in both local and CI contexts. |
| 2. GitHub Actions Workflow and Operator Documentation | Separate read-only workflow plus README updates | Diff generation and secret scoping must be correct on PR and manual runs. |

**Prerequisites:** GitHub repository secret `OPENAI_API_KEY` must exist for CI
runs. Local real-review verification needs either `OPENAI_API_KEY` in the shell
or an existing Codex login.

**Estimated effort:** ~1-2 focused sessions across 2 phases.

## Open Risks & Assumptions

- GitHub-hosted CI should use normal `npm ci`; the local `/mnt/e` `--no-bin-links`
  workaround remains documented only for local installs.
- The first version depends on artifacts rather than PR comments, so reviewers
  must open the uploaded JSON to inspect details.
- Fork PRs are intentionally skipped until a safer review policy is defined.

## Success Criteria (Summary)

- The agent emits valid JSON with five criterion scores, `overall_score`, and
  `verdict`.
- Unsafe QSA diffs fail the review gate after writing the JSON artifact.
- A separate GitHub workflow can run manually or on trusted PRs without changing
  the existing product CI workflow.
