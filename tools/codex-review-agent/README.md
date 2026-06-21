# QSA Codex Review Agent

Codex SDK code-review agent for Quantitative Sentiment Analysis pull-request
review gates.

The package is intentionally separate from the FastAPI app. It reads a diff,
sends a focused review prompt to Codex, validates the JSON-shaped answer, and
prints the review. The same command can also write a JSON artifact and fail
mechanically when the review violates the QSA gate.

## Install

```bash
npm install --no-bin-links
```

On a normal Linux filesystem, plain `npm install` should also work. On this
`/mnt/e` workspace, `--no-bin-links` avoids Windows/WSL chmod issues for the
Codex runtime package.

## Dry run

Print the prompt without calling Codex:

```bash
npm run build
npm run review:dry
```

Pass PR metadata into the generated prompt:

```bash
npm run review:dry -- --diff-file fixtures/simulated-qsa.diff --pr-title "Simulated unsafe diff" --pr-body "Exercise the QSA review gate"
```

## Run

Use the bundled simulated diff:

```bash
npm run build
npm run review
```

Use another diff file:

```bash
npm run review -- --diff-file path/to/change.diff
```

Write a JSON artifact:

```bash
npm run review -- --diff-file path/to/change.diff --output-file /tmp/qsa-review.json
```

Use PR metadata from files when the body is multiline:

```bash
npm run review -- --diff-file path/to/change.diff --pr-title "Add JSONL export" --pr-body-file /tmp/pr-body.md --output-file /tmp/qsa-review.json
```

Local real review needs either an existing Codex login or `OPENAI_API_KEY` in
the current shell. In CI, keep `OPENAI_API_KEY` scoped to the review step and
let the agent pass it to `new Codex({ apiKey })`.

## Review gate

The command exits non-zero after writing the JSON output when any of these are
true:

- `verdict` is `fail`;
- any finding has `severity: "blocker"`;
- any criterion score is below `7`;
- `overall_score` is below `7`.

The JSON contract includes five scored criteria:

- `qsa_semantic_safety`;
- `deterministic_data_contracts`;
- `workspace_security_boundaries`;
- `test_verification_discipline`;
- `scope_maintainability_discipline`.

## GitHub Actions

The CI pipeline lives in `.github/workflows/ai-code-review.yml`. It runs as a
separate `AI Code Review` workflow instead of modifying the main product CI.

Triggers:

- `pull_request` for pull requests from this repository;
- `workflow_dispatch` for manual reviews, with optional `base_ref` defaulting to
  `main`.

The workflow skips fork pull requests automatically because non-`GITHUB_TOKEN`
secrets are not passed to fork PR runs. Configure `OPENAI_API_KEY` as a GitHub
repository or organization secret before using the workflow. The secret is scoped
only to the review step.

The workflow uploads `qsa-ai-code-review` as a JSON artifact. A failed review
still writes the artifact before the job fails when the gate is violated.

Promptfoo/model comparison is handled by the separate `code-review-evals`
change.

## Notes

- Requires Node.js 18+ and a working local Codex CLI/session.
- The prompt tells Codex to review only the diff, using PR title/body only as
  context, and return JSON.
- The agent must preserve QSA hard rules: `BACKTEST-only`, deterministic JSONL,
  workspace isolation, and `directional bias` wording instead of executable
  trading-signal language.
