# Promptfoo Eval Summary

Eval ID: `eval-5xm-2026-06-21T09:50:51`

Compared models:

- `openai:gpt-5-mini`
- `openai:gpt-5`

Diff sources:

- `tools/codex-review-agent/fixtures/simulated-qsa.diff` — expected verdict:
  `fail`
- `tools/codex-review-agent/fixtures/test-ai-agent-pr.diff` — generated from
  `6ca6a01...e8adc17`, expected verdict: `pass`

Aggregate:

- Passed: `1 / 4`
- Failed: `3 / 4`
- Total tokens: `21,884`
- Estimated total cost: `$0.10026980`
- Full promptfoo export: `/tmp/qsa-promptfoo-eval-two-diffs.json`

## Matrix

| Diff | Expected | Model | Result | Reason | Cost | Latency | Tokens |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| Known-bad QSA export diff | fail | `openai:gpt-5-mini` | FAIL | `findings[2].file must be a non-empty string` | `$0.00529705` | `28.523s` | `3,913` |
| Known-bad QSA export diff | fail | `openai:gpt-5` | FAIL | `missing expected evidence term from group: ordered = records \| stable sorting \| nondeterministic \| input order` | `$0.02820125` | `54.064s` | `4,099` |
| test_ai_Agent PR diff | pass | `openai:gpt-5-mini` | FAIL | `expected verdict pass, got fail` | `$0.00690525` | `30.886s` | `5,669` |
| test_ai_Agent PR diff | pass | `openai:gpt-5` | PASS | `All assertions passed` | `$0.05986625` | `77.465s` | `8,203` |

## Interpretation

The additional `test_ai_Agent` diff compares the real PR branch against `main`
before merge. It contains workflow/README changes for posting AI review summaries
to PR comments and does not touch QSA BACKTEST data contracts.

The stricter model, `openai:gpt-5`, matched the expected pass verdict for this
workflow-only diff. `openai:gpt-5-mini` failed that row by returning a fail
verdict, which is useful evidence that the smaller model is more conservative or
less aligned with the intended gate for CI workflow-only changes.

The known-bad QSA fixture produced fail verdicts, but both rows failed the eval's
deterministic assertions for different reasons: `gpt-5-mini` emitted one finding
with an invalid empty `file`, while `gpt-5` did not include one required evidence
term group in the JSON text. That means the eval is catching not only verdicts,
but also structured-output and evidence quality.
