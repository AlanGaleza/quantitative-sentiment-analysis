# Code Review Evals Requirements

## Overall Concept

- Add promptfoo evals for the code review prompt/agent under `tools/codex-review-agent/`.
- Compare OpenAI models only, using `OPENAI_API_KEY`.
- Keep evals separate from GitHub Actions pipeline implementation in `context/changes/ci-code-review-pipeline/`.
- Use the same review prompt/schema contract that the CI review agent uses after the structured-output work lands.

## Practical Task In Scope

### Compare models with evals

- Create a small promptfoo setup over the same review prompt and prepared diffs.
- Run 2 OpenAI model configurations side by side.
- Produce a pass/fail matrix with cost and timing so model choice is based on eval output, not a single PR intuition.
- Leave the eval suite as a regression gate for future prompt/schema changes.

## Expected Inputs

- Review prompt from `tools/codex-review-agent/prompts/qsa-code-review.md` or an eval wrapper that imports/stays synchronized with it.
- Prepared diff fixtures, starting with the existing bad QSA diff.
- OpenAI API key from local environment or GitHub secret.

## Expected Eval Assertions

- Output is valid JSON.
- Known-bad diffs produce `verdict: "fail"`.
- Expected findings are present for:
  - nondeterministic JSONL ordering;
  - wall-clock timestamp in export output;
  - unsafe `live-ready trading signals` wording.
- `overall_score` and criterion scores are integers in the `1..10` range.
- Bad semantic-safety and determinism cases score below the chosen pass threshold.

## Implementation Notes

- Do not use OpenRouter.
- Prefer deterministic JavaScript assertions for gating.
- Use `llm-rubric` only if explicitly needed later, because model-graded assertions add cost and possible flake.
- Promptfoo evaluates direct provider responses; it does not by itself test the Codex SDK wrapper's JSON extraction or artifact-writing behavior.

## Explicitly Out Of Scope

- GitHub Actions workflow implementation.
- Codex SDK runtime changes unrelated to evalability.
- Non-OpenAI providers.
