# Code Review Evals Verification

## Automated No-Cost Checks

Command:

```bash
npm --prefix tools/codex-review-agent run eval:assertions
npm --prefix tools/codex-review-agent run typecheck
npm --prefix tools/codex-review-agent run build
git diff --check -- tools/codex-review-agent context/changes/code-review-evals
```

Result: passed.

## Promptfoo Runner Check

Command:

```bash
npm --prefix tools/codex-review-agent run eval:review -- --help
```

Result: passed. The pinned `npx --yes promptfoo@0.121.17` runner printed the
`promptfoo eval` help without making model calls.

## Real OpenAI Promptfoo Eval

Command:

```bash
npm --prefix tools/codex-review-agent run eval:review -- --no-share --no-cache --no-progress-bar --max-concurrency 1
```

Result:

- Eval ID: `eval-s7A-2026-06-21T09:36:30`
- Providers compared:
  - `openai:gpt-5-mini`
  - `openai:gpt-5`
- Pass/fail:
  - `2 passed (100%)`
  - `0 failed`
  - `0 errors`
- Duration: `1m 23s`
- Total tokens: `7,740`
- Provider token breakdown:
  - `openai:gpt-5-mini`: `3,567` tokens, 1 request, `25.075s`
    latency, estimated cost `$0.00486425`
  - `openai:gpt-5`: `4,173` tokens, 1 request, `58.118s` latency,
    estimated cost `$0.03038125`

Notes:

- The terminal table displayed pass/fail and the run summary displayed duration
  and token usage. The dollar-denominated costs were read from a local promptfoo
  export written to `/tmp/qsa-promptfoo-eval.json`; that file is not part of the
  repository.
- No API key, model output artifact, or promptfoo result file was committed.

## Real OpenAI Promptfoo Eval With test_ai_Agent Diff

Command:

```bash
npm --prefix tools/codex-review-agent run eval:review -- --no-share --no-cache --no-progress-bar --max-concurrency 1 -o /tmp/qsa-promptfoo-eval-two-diffs.json
```

Result:

- Eval ID: `eval-5xm-2026-06-21T09:50:51`
- Diffs compared:
  - `tools/codex-review-agent/fixtures/simulated-qsa.diff`
  - `tools/codex-review-agent/fixtures/test-ai-agent-pr.diff`
- `test-ai-agent-pr.diff` source range: `6ca6a01...e8adc17`
- Providers compared:
  - `openai:gpt-5-mini`
  - `openai:gpt-5`
- Pass/fail:
  - `1 passed (25%)`
  - `3 failed (75%)`
  - `0 errors`
- Total tokens: `21,884`
- Estimated total cost: `$0.10026980`

Sanitized summaries:

- `context/changes/code-review-evals/eval-summary.md`
- `context/changes/code-review-evals/eval-summary.json`

The full promptfoo export is stored outside the repo at
`/tmp/qsa-promptfoo-eval-two-diffs.json`.
