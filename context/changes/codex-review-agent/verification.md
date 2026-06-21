# Verification

## Scope

Implemented a local, independent Codex SDK code-review agent under:

- `tools/codex-review-agent/`

The agent reviews a supplied diff, asks Codex for JSON output, validates that output with Zod, and prints the structured review.

## Commands

From `tools/codex-review-agent/`:

```bash
npm install --no-bin-links
npm run typecheck
npm run build
npm run review:dry
npm run review
```

## Results

- `npm install --no-bin-links`: passed, `0 vulnerabilities`.
- `npm run typecheck`: passed.
- `npm run build`: passed.
- `npm run review:dry`: passed; printed the expected QSA review prompt and simulated diff.
- `npm run review`: passed with escalated local runtime permissions because Codex SDK needs to start the local app-server and write local session state.

## Codex SDK Response Summary

The model returned valid JSON and identified the intended high-risk review issues in the simulated diff:

- JSONL export order became nondeterministic after replacing a stable sort with input order.
- `generated_at = datetime.now().isoformat()` made JSONL bytes nondeterministic.
- Frontend copy changed from analytical `directional bias` wording to `live-ready trading signals`, violating BACKTEST-only semantic safety.

Suggested test:

```bash
uv run pytest tests/backtest_dataset/test_export.py
```

## Notes For M5L3

The current implementation is local-only. The next step is to call the same package from CI/CD, feed it a real PR diff, publish the JSON as a review artifact or PR comment, and keep a human reviewer as the final decision-maker.
