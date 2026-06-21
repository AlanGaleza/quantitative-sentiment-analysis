# CI Code Review Pipeline Requirements

## Overall Concept

- Build on the existing local Codex SDK review agent in `tools/codex-review-agent/`.
- Add a separate GitHub Actions workflow for AI code review instead of modifying `.github/workflows/ci.yml`.
- Keep the existing CI pipeline independent: backend, frontend, and E2E checks stay in `ci.yml`.
- Use OpenAI/Codex authentication through the already configured `OPENAI_API_KEY` secret/runtime setup.
- Promptfoo/model comparison is handled by the separate `code-review-evals` change.

## Practical Tasks In Scope

### 1. Define good-review criteria

Produce five concrete criteria for QSA pull-request review:

- QSA semantic safety: `BACKTEST-only`, `directional bias`, no live/broker/order/investment-recommendation wording.
- Deterministic data contracts: JSONL stability, run metadata, source identity, no wall-clock/process randomness in exports.
- Workspace/security boundaries: `workspace_id` as the access boundary, no secret exposure, no generated real workspace datasets committed.
- Test and verification discipline: changed contracts have targeted tests and concrete verification commands.
- Scope and maintainability discipline: idiomatic, focused changes; no unrelated refactors or product-scope drift.

### 2. Wire criteria into structured agent output

- Update the existing Codex SDK prompt so the five criteria are part of the review contract.
- Extend the Zod schema so the agent returns criterion-level scores, an overall score, and a mechanical `pass` / `fail` verdict.
- Make the pipeline able to fail mechanically when the verdict fails, a blocking issue exists, or scores fall below a threshold.

## Expected Agent Inputs

- Pull request title.
- Pull request body/description.
- Git diff calculated on the runner against the PR base branch.
- For local tests, a diff file path remains supported.

## Expected Agent Outputs

- Valid JSON review result.
- Criterion-level scores on a 1-10 scale.
- Overall score.
- `pass` or `fail` verdict.
- Findings with severity, file, line, details, and recommendation.
- Tests to run.
- Cost/bounds note.
- Optional output file suitable for GitHub artifact upload.

## GitHub Actions Pipeline Scope

- Add a new workflow, for example `.github/workflows/ai-code-review.yml`.
- Trigger on `pull_request` and `workflow_dispatch`.
- Use `actions/checkout` with `fetch-depth: 0` so diff calculation can compare against the base branch.
- Set up Node.
- Install only `tools/codex-review-agent` dependencies.
- Build the agent.
- Calculate the PR diff.
- Run the review agent with `OPENAI_API_KEY` from GitHub Secrets.
- Upload the JSON result as an artifact.
- Keep PR comments/status checks as a later enhancement unless they are needed for the minimal working pipeline.

## Explicitly Out Of Scope

- Promptfoo evals and model comparison; see `context/changes/code-review-evals/`.
- OpenRouter and non-OpenAI providers.
- Live trading, broker integration, order execution, investment recommendations, or any product wording that violates QSA semantic safety.
