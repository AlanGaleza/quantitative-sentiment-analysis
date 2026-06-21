# Mom Test Validation Plan

## Input Idea

`QSA Contract Risk Digest` is a thin internal helper for Quantitative Sentiment Analysis. It would read local repo context and a change diff, then return a Markdown digest of touched quality contracts, semantic-safety risks, related files, suggested tests, and missing validation evidence before review or merge.

The helper is not a product feature. It is a read-only review aid for maintaining deterministic JSONL behavior, workspace isolation, BACKTEST-only wording, and backend/frontend contract alignment.

## Hypotheses

- **User/role**: Primary users are the developer, reviewer, or future maintainer reviewing changes in this repository.
- **Friction**: Contract review requires manually combining AGENTS.md, PRD rules, `quality-contracts.md`, source files, frontend copy, and several test suites.
- **Current workaround**: Reviewers use memory, `rg`, git diff, manual file browsing, and broad test runs.
- **Proposed solution**: A local/read-only Markdown digest that highlights likely contract risks and the tests/evidence to check.
- **Risky assumptions**:
  - Reviewers actually lose time on this often enough to justify a helper.
  - The risks are repeated and pattern-like, not just one-off complexity.
  - A digest would be trusted and read instead of ignored.
  - Existing tests and docs are not already enough for the current project scale.
  - The helper can stay thin and avoid becoming an overbuilt CI product.
- **Evidence already present**:
  - AGENTS.md defines hard semantic and determinism rules.
  - `context/foundation/quality-contracts.md` defines canonical contracts.
  - Tests already cover contracts, safety, dataset export, and quality behavior.
  - Multiple active `context/changes/*` folders show recurring planned/reviewed changes.
  - No direct interview evidence yet from reviewers or future users.

## Critique

The idea may be confusing "I want safer reviews" with "I need a new tool." Existing docs, tests, and search may already be sufficient if changes are small and review is mostly solo. The strongest reason to proceed would not be that a digest sounds useful, but that recent reviews repeatedly required the same manual contract checks or missed the same classes of risk.

The main falsifier is simple: if reviewers cannot name recent situations where contract context was slow, forgotten, or error-prone, this should not be built yet. Another warning sign is if the digest would mostly restate what `pytest` and existing docs already make obvious. Strong evidence would be repeated recent examples where a reviewer had to cross-check docs, schemas, frontend copy, and tests to answer a concrete review question.

## Interview Guide

Target length: 20-30 minutes. Interview 3-5 people who review or maintain this repo, or use the same process in a similar repo. Do not pitch the helper first.

1. What kinds of changes in this repo are hardest for you to review safely?
   - Follow-up: Which files or contracts do you usually check for those?
2. Walk me through the last time you reviewed or made a change that touched dataset export, workspace identity, BACKTEST wording, or frontend/API contracts.
   - Follow-up: What did you actually open first?
3. How did you decide which tests to run for that change?
   - Follow-up: Did you run more tests than needed, or later discover a missing test?
4. When was the last time wording like "signal", "recommendation", "broker", "live", or execution language caused concern in review?
   - Follow-up: How did you catch it?
5. What do you currently do when you need to know whether a changed file affects JSONL determinism or workspace isolation?
   - Follow-up: Is that documented anywhere you trust?
6. Tell me about a recent review where you had to jump between docs, tests, backend, and frontend files.
   - Follow-up: How much time did that take?
7. Have you seen a contract risk caught late, after implementation or after a broad test run?
   - Follow-up: What would have helped catch it earlier?
8. Which current workflow already handles this well enough?
   - Follow-up: What would make you choose the current workflow over any new helper?
9. If you had a short Markdown report before review, what would make it worth reading?
   - Follow-up: What would make you ignore it?
10. Can I look at one recent safe-to-share diff or review where this kind of contract checking happened?

## Survey

Use only after a few interviews, or for broader signal in similar repos.

1. In the last month, how often did you review or make changes that touched repository-level contracts such as determinism, workspace isolation, semantic-safety wording, or API/frontend schemas?
   - Never
   - Once
   - 2-3 times
   - Weekly or more
2. How often do you manually search docs/tests/source files to understand which contract a change affects?
   - Never
   - Rarely
   - Sometimes
   - Often
3. The last time this happened, how long did it take to gather enough context?
   - Under 5 minutes
   - 5-15 minutes
   - 15-30 minutes
   - More than 30 minutes
   - I do not remember a recent case
4. Which areas most often require manual cross-checking? Select all that apply.
   - JSONL determinism
   - Workspace isolation
   - Run metadata
   - Source identity
   - BACKTEST-only wording
   - Backend/frontend API contract
   - Test selection
5. What workaround do you use today when you need to check those areas?
6. Describe one recent example where contract context slowed review or caused rework.
7. How often do existing tests and docs answer the question clearly enough without extra searching?
   - Almost always
   - Often
   - Sometimes
   - Rarely
8. What would be the most useful output from a read-only Markdown digest?
   - Touched contracts
   - Suspicious wording
   - Related source/test files
   - Suggested tests
   - Missing evidence
   - Other
9. What would make this kind of digest not worth using?

## Decision Criteria

- **Proceed**: At least 3 of 5 interviewees describe a recent manual contract-checking situation without being prompted, and at least 2 say it caused 10+ minutes of review delay, extra test churn, or rework.
- **Narrow scope**: Interviewees agree the pain exists but only for one category, such as semantic-safety wording or backend/frontend API drift. Build only that section first.
- **Do not build yet**: Interviewees mostly cannot recall recent examples, the issue appears rare, or the digest would only repeat existing test output.
- **Try existing tool/process first**: If reviewers say a checklist in AGENTS.md, better test naming, or one documented `rg` command would solve the pain, update that process before building a helper.
