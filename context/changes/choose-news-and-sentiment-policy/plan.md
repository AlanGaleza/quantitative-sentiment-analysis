# Choose News and Sentiment Policy Implementation Plan

## Overview

Define the F-02 foundation policy for BTCUSD BACKTEST news sourcing, relevance labeling, deterministic sentiment scoring, directional-bias thresholds, classification confidence, and the first quality-view visualization scope. This plan turns the user-owned F-02 decisions into a documented and executable policy contract that S-02 can consume without rediscovering provider/scoring rules.

## Current State Analysis

F-01 has already established the shared workspace, run metadata, dataset record, JSONL determinism, and semantic-safety contracts. Those contracts intentionally stop before choosing a provider, relevance policy, sentiment thresholds, confidence formula, or visualization scope.

The codebase already has reusable contract models for `DatasetRecord`, `DirectionalBias`, `RelevanceLabel`, bounded `sentiment_score`, bounded `confidence`, source identity, timezone-aware timestamps, and deterministic JSONL serialization. S-04 also has a fixture-backed quality view with a default 4-hour horizon, correlation, hit rate, and a sentiment-vs-later-return plot, but it currently produces all chart points from input records and needs a real-data payload policy before S-02 connects completed runs.

## Desired End State

After this plan is implemented, `context/foundation/news-sentiment-policy.md` is the human-readable source of truth for F-02. It locks the MVP source to CryptoPanic, the default historical window to 30 days, the relevance policy to preserve all retrieved records while labeling them `RELEVANT`, `NOISE`, or `IRRELEVANT`, the scoring approach to deterministic local rule/lexicon scoring, directional-bias thresholds to `>= 0.20 LONG`, `<= -0.20 SHORT`, and otherwise `FLAT`, confidence to deterministic classification confidence, and the quality view to 4-hour correlation + hit rate + sampled sentiment-vs-return visualization.

The backend also has a small executable policy module that future S-02 implementation can import for configuration constants, scoring contract behavior, threshold mapping, confidence calculation, and deterministic policy version identity. Focused tests prove determinism, bounds, relevance preservation, directional-bias mapping, confidence semantics, semantic-safety wording, and S-04 payload-limit expectations.

### Key Discoveries:

- F-02 is explicitly blocked until source, relevance labels, sentiment thresholds, directional-bias mapping, confidence meaning, and visualization scope are decided in `context/foundation/roadmap.md:76`.
- F-01 documents that provider choice, relevance policy details, thresholds, confidence formula, and visualization scope belong to F-02 in `context/foundation/quality-contracts.md:192`.
- Shared dataset contracts already validate required fields and bounds in `src/quantitative_sentiment_analysis/contracts/schemas.py:67`.
- Stable JSON serialization and run fingerprint helpers already exist in `src/quantitative_sentiment_analysis/contracts/serialization.py:35`.
- S-04 uses a default 4-hour quality horizon in `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:34`.
- S-04 currently builds `chart_points` for every quality input record in `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:43`, while F-01 already warns that real S-02 quality payloads must be capped, sampled, paginated, or explicitly limited in `context/foundation/quality-contracts.md:224`.

## What We're NOT Doing

- No full S-02 news ingestion implementation.
- No persistent run storage, database schema, or workspace shell implementation.
- No provider API client that downloads real CryptoPanic data for production use.
- No multi-provider aggregation or fallback provider scope.
- No live streaming, broker integration, order execution, or investment-recommendation wording.
- No ML/LLM sentiment model integration in V1.
- No advanced quality dashboard beyond the minimal S-04-compatible metrics and sampled plot.
- No generated datasets containing real workspace identifiers or unsanitized news exports committed to the repository.

## Implementation Approach

Treat F-02 as a policy-and-contract slice. First write the policy document so humans and future agents have a single source of truth. Then mirror only the deterministic, provider-independent parts into a small Python policy package that S-02 can import. Add tests around the policy behavior and update downstream handoff notes so S-02 and S-04 inherit the decisions without changing their existing external contracts prematurely.

## Critical Implementation Details

### Provider Verification Boundary

CryptoPanic is the selected MVP provider, but this F-02 implementation must not bake in unverified endpoint details as production behavior. The policy should require S-02 to perform a token/API smoke test before implementing real ingestion, and S-02 must fail explicitly if CryptoPanic access cannot support the 30-day BTCUSD BACKTEST use case.

### Quality Payload Limit

Metrics should be computed over the full deterministic run when real S-02 data exists, but response payloads for chart/detail rows must be capped, sampled, paginated, or explicitly limited before exposing large real runs through S-04. This is a policy requirement, not an optional frontend optimization.

## Phase 1: Human-Readable F-02 Policy

### Overview

Create the canonical foundation policy document and connect it to existing foundation docs without duplicating the whole F-01 contract.

### Changes Required:

#### 1. News sentiment policy document

**File**: `context/foundation/news-sentiment-policy.md`

**Intent**: Define the F-02 decisions in one durable document that S-02, S-03, S-04, and future planning can cite.

**Contract**: The document must include sections for scope, non-scope, provider policy, default historical range, relevance policy, deterministic scoring policy, directional-bias thresholds, confidence semantics, quality horizon, visualization payload policy, semantic-safety wording, and downstream handoffs. It must lock these choices:

- Provider: CryptoPanic for MVP, as a single aggregated crypto-news feed.
- Provider verification: S-02 must run a controlled token/API smoke test before production ingestion.
- Historical range: default 30-day BTCUSD BACKTEST window.
- Relevance: preserve all retrieved records and mark each as `RELEVANT`, `NOISE`, or `IRRELEVANT`.
- Scoring: deterministic local rule/lexicon scoring for V1.
- Thresholds: `sentiment_score >= 0.20` maps to `LONG`; `sentiment_score <= -0.20` maps to `SHORT`; otherwise `FLAT`.
- Confidence: deterministic classification confidence in `0..1`, not market certainty.
- Quality horizon: default 4 hours.
- Visualization: correlation + hit rate + sampled sentiment-vs-later-return plot; metrics may use the full run, but chart/detail payloads are bounded.

#### 2. Quality contracts handoff

**File**: `context/foundation/quality-contracts.md`

**Intent**: Replace the F-02 "owns this later" note with a concise pointer to the new F-02 policy while keeping F-01 field contracts canonical.

**Contract**: The F-02 downstream handoff must cite `context/foundation/news-sentiment-policy.md` as the source for provider, scoring, confidence, and visualization-scope decisions. It must not duplicate all policy details or change the F-01 dataset field contract.

#### 3. Roadmap status handoff

**File**: `context/foundation/roadmap.md`

**Intent**: Make the roadmap reflect that F-02 policy decisions are planned/ready for implementation handoff after this change lands.

**Contract**: Update only the F-02 handoff language needed to point at the new policy document after implementation. Do not mark S-02 or S-04 complete, and do not remove their dependencies on implemented upstream work unless the implementation phase actually satisfies the roadmap status convention used in the file.

### Success Criteria:

#### Automated Verification:

- Policy document exists and is non-empty: `test -s context/foundation/news-sentiment-policy.md`
- Policy document names the selected provider and thresholds: `rg -n "CryptoPanic|0\\.20|LONG|SHORT|FLAT|30-day|4 hours" context/foundation/news-sentiment-policy.md`
- Foundation docs reference the policy: `rg -n "news-sentiment-policy" context/foundation/quality-contracts.md context/foundation/roadmap.md`

#### Manual Verification:

- `news-sentiment-policy.md` is reviewed against PRD FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, and FR-015.
- The policy preserves BACKTEST-only analytical wording and does not introduce live trading, broker, order execution, or investment recommendation scope.
- The policy clearly says CryptoPanic must be smoke-tested before S-02 real ingestion.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Executable Policy Contracts

### Overview

Add a lightweight Python policy package that mirrors the deterministic parts of the F-02 decision without implementing external provider ingestion.

### Changes Required:

#### 1. Sentiment policy package

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/__init__.py`

**Intent**: Provide stable imports for the executable F-02 policy without coupling dataset generation to S-04 quality modules.

**Contract**: Re-export the policy configuration, directional-bias mapping, scoring helper, relevance helper, and confidence helper. The package must have no FastAPI, storage, network, frontend, or provider-client side effects.

#### 2. Policy configuration

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/config.py`

**Intent**: Centralize versioned constants that future S-02 can stamp into run metadata and generated dataset records.

**Contract**: Define immutable configuration values for provider name `CryptoPanic`, default instrument `BTCUSD`, default mode `BACKTEST`, default historical range of 30 days, default quality horizon of 4 hours, `LONG` threshold `0.20`, `SHORT` threshold `-0.20`, scoring model/version identity, and configuration version identity. The config must not include API tokens, URLs requiring secrets, or production endpoint behavior.

#### 3. Directional-bias mapping

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/scoring.py`

**Intent**: Encode the deterministic sentiment-to-bias threshold contract.

**Contract**: Provide a pure mapping function equivalent to `directional_bias_for_score(score: float) -> DirectionalBias`. It must reject non-finite values, enforce `-1..1`, map `>= 0.20` to `LONG`, map `<= -0.20` to `SHORT`, and map the open interval between those thresholds to `FLAT`.

#### 4. Rule/lexicon scoring contract

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/scoring.py`

**Intent**: Provide deterministic local V1 sentiment scoring that S-02 can call for headline/body text after provider normalization.

**Contract**: Provide a pure scoring function for headline text and optional body/metadata text. It must return a bounded score in `-1..1`, use deterministic local word/phrase weights, not call external services, not read current time, and not use randomness. The plan should keep the initial lexicon intentionally small and auditable; quality tuning belongs to later signal-quality iteration.

#### 5. Relevance labeling contract

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/relevance.py`

**Intent**: Preserve all provider records while assigning deterministic relevance labels that downstream metrics can interpret.

**Contract**: Provide a pure relevance function that returns `RELEVANT`, `NOISE`, or `IRRELEVANT`. Initial rules should classify BTC/BTCUSD/Bitcoin-market items as `RELEVANT`, obvious non-market duplicates/spam/provider placeholders as `NOISE`, and non-BTC crypto/general off-topic items as `IRRELEVANT`. The function must not silently drop records; filtering is a downstream presentation/storage decision, not a policy output.

#### 6. Classification confidence contract

**File**: `src/quantitative_sentiment_analysis/sentiment_policy/confidence.py`

**Intent**: Define deterministic `confidence` as classification confidence, not market certainty.

**Contract**: Provide a pure confidence function based on score strength, relevance label, and source/headline completeness. It must return `0..1`, be deterministic for identical normalized inputs, and avoid language implying probability of future price movement or trading success.

### Success Criteria:

#### Automated Verification:

- Policy package imports cleanly: `uv run python -c "import quantitative_sentiment_analysis.sentiment_policy"`
- Existing backend tests still pass: `uv run pytest tests/test_main.py tests/contracts tests/backtest_quality`
- Policy constants can be imported without network or environment secrets: `uv run python -c "from quantitative_sentiment_analysis.sentiment_policy import DEFAULT_POLICY_CONFIG; print(DEFAULT_POLICY_CONFIG.provider_name)"`

#### Manual Verification:

- Module names and exports make it clear this is policy/scoring, not provider ingestion.
- The executable constants match `context/foundation/news-sentiment-policy.md`.
- No API token, endpoint secret, or production CryptoPanic request logic is introduced in this phase.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Policy Verification Tests

### Overview

Add focused tests proving that the executable policy is deterministic, bounded, auditable, and aligned with F-01/S-04 contracts.

### Changes Required:

#### 1. Policy configuration tests

**File**: `tests/sentiment_policy/test_config.py`

**Intent**: Verify that the executable constants match the F-02 decisions and are safe to import.

**Contract**: Tests must cover provider name, default 30-day range, default 4-hour quality horizon, threshold values, model/config version non-emptiness, and absence of required secrets for import.

#### 2. Directional-bias and scoring tests

**File**: `tests/sentiment_policy/test_scoring.py`

**Intent**: Verify threshold boundaries and deterministic local scoring behavior.

**Contract**: Tests must cover exact threshold behavior at `0.20`, just below `0.20`, exact `-0.20`, just above `-0.20`, neutral text mapping to `FLAT`, positive/negative lexicon examples, invalid non-finite values, invalid out-of-range scores, and repeated identical output for identical input.

#### 3. Relevance tests

**File**: `tests/sentiment_policy/test_relevance.py`

**Intent**: Verify that records are labeled, not silently removed.

**Contract**: Tests must cover BTC-relevant records, non-BTC crypto/off-topic records, noise/spam/placeholder cases, and preservation semantics. The test names should make it clear that relevance labels are output metadata, not filter decisions.

#### 4. Confidence tests

**File**: `tests/sentiment_policy/test_confidence.py`

**Intent**: Verify deterministic classification-confidence bounds and semantics.

**Contract**: Tests must cover bounds `0..1`, stronger absolute scores producing no lower confidence than weaker comparable scores, relevance/source completeness effects, deterministic repeated output, and absence of market-certainty wording in helper names/docstrings where practical.

#### 5. Policy documentation alignment tests

**File**: `tests/sentiment_policy/test_policy_documentation.py`

**Intent**: Guard against drift between the human-readable policy and executable constants.

**Contract**: Tests may read `context/foundation/news-sentiment-policy.md` and assert the presence of the load-bearing decisions: `CryptoPanic`, `30 days`, `0.20`, `-0.20`, `4 hours`, `RELEVANT`, `NOISE`, `IRRELEVANT`, `classification confidence`, and sampled/limited quality payload wording.

### Success Criteria:

#### Automated Verification:

- Sentiment policy tests pass: `uv run pytest tests/sentiment_policy`
- Contract and quality tests still pass with policy tests: `uv run pytest tests/contracts tests/backtest_quality tests/sentiment_policy`
- Determinism checks pass repeatedly: `uv run pytest tests/sentiment_policy/test_scoring.py tests/sentiment_policy/test_confidence.py`

#### Manual Verification:

- Test names and failure messages explain policy intent rather than implementation trivia.
- Tests do not require network access, CryptoPanic credentials, current time, or generated real-news datasets.
- Tests verify semantic-safety boundaries without introducing product-facing trading recommendation wording.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Downstream S-02/S-04 Handoff

### Overview

Make the new F-02 policy easy for the next implementation slices to consume, especially S-02 deterministic dataset generation and S-04 real-run quality reports.

### Changes Required:

#### 1. S-02 handoff section

**File**: `context/foundation/news-sentiment-policy.md`

**Intent**: Give S-02 concrete policy requirements without making F-02 implement ingestion.

**Contract**: The S-02 handoff must say future ingestion should normalize CryptoPanic records into the F-01 `DatasetRecord` fields, preserve retrieved records with relevance labels, stamp policy `model_version` and `config_version`, compute deterministic `input_fingerprint` from normalized input, and fail explicitly if CryptoPanic access cannot support the 30-day BTCUSD BACKTEST use case.

#### 2. S-04 visualization handoff

**File**: `context/foundation/news-sentiment-policy.md`

**Intent**: Close the S-04 open visualization question from the roadmap.

**Contract**: The S-04 handoff must specify 4-hour default horizon, correlation, hit rate, sampled sentiment-vs-later-return plot, metrics over the full deterministic run when available, and bounded chart/detail payloads. It must preserve S-04 semantics that noise/irrelevant records are excluded from metric denominators but still counted/preserved where relevant.

#### 3. Quality metric payload guard

**File**: `src/quantitative_sentiment_analysis/backtest_quality/metrics.py`

**Intent**: Prepare S-04 for future real S-02 data by making the chart payload limit policy explicit in code-level constants or helper boundaries if the current implementation exposes unbounded chart points.

**Contract**: If this phase changes code, it should add a deterministic chart-point sampling cap consistent with the policy while preserving existing metric semantics. Metrics must still be computed from the full ordered record set; only the response payload list should be bounded. If the implementer determines this code change belongs better in the later S-02/S-04 integration pass, they must instead add an explicit documented TODO or guard test that fails only when real-provider mode is introduced without a cap.

#### 4. Frontend copy/checks if payload semantics change

**File**: `frontend/src/features/backtestQuality/SentimentReturnPlot.tsx`

**Intent**: Keep the chart honest if the backend begins returning sampled chart points.

**Contract**: If Phase 4 bounds `chart_points` in the backend, update user-facing chart copy only as needed to avoid implying every record is plotted. Do not add a new advanced dashboard or new metrics.

#### 5. Change metadata and brief

**File**: `context/changes/choose-news-and-sentiment-policy/change.md`

**Intent**: Keep the change metadata aligned with implementation status.

**Contract**: At final implementation, update `status` and `updated` consistently with the repository's change-folder convention.

**File**: `context/changes/choose-news-and-sentiment-policy/plan-brief.md`

**Intent**: Keep the brief aligned if implementation changes scope or phase sequencing.

**Contract**: Update key decisions, phase summary, and success criteria if actual implementation differs from this plan.

### Success Criteria:

#### Automated Verification:

- Full backend test suite passes: `uv run pytest tests/test_main.py tests/contracts tests/backtest_quality tests/sentiment_policy`
- Frontend tests pass if S-04 UI copy or payload semantics change: `cd frontend && npm test -- --run`
- Foundation docs still point to the policy: `rg -n "news-sentiment-policy|CryptoPanic|sampled|4 hours" context/foundation`

#### Manual Verification:

- S-02 handoff is specific enough to start `/10x-plan deterministic-news-dataset` without re-asking provider/scoring decisions.
- S-04 handoff closes the roadmap's visualization question without expanding into an advanced dashboard.
- Existing quality view still presents BACKTEST-only analytical quality and does not imply trading recommendations or executable signals.
- The final handoff names the next sensible command as `/10x-plan deterministic-news-dataset` or `/10x-plan workspace-backtest-shell`, depending on which dependency track the user wants next.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- Policy constants match selected F-02 decisions.
- Threshold mapping handles exact boundaries and near-boundary values.
- Rule/lexicon scoring is bounded, deterministic, and local.
- Relevance labeling preserves records by returning labels instead of filtering.
- Confidence is bounded, deterministic, and framed as classification confidence.
- Documentation alignment tests guard the human-readable policy against drift from executable constants.

### Integration Tests:

- Existing contract tests still pass with the new policy package.
- Existing backtest-quality tests still pass after any chart payload limit change.
- If chart payload sampling is implemented in this change, tests verify metrics use the full input set while chart points are bounded.

### Manual Testing Steps:

1. Review `context/foundation/news-sentiment-policy.md` against the eight user decisions from planning.
2. Confirm the policy remains BTCUSD BACKTEST-only and avoids investment recommendation or executable trading wording.
3. Confirm the executable constants and tests mirror the policy document.
4. Confirm no network call or CryptoPanic token is required by tests or import-time code.
5. Confirm the S-02 handoff names the required CryptoPanic smoke test before real ingestion.
6. Confirm the S-04 handoff requires sampled/limited chart payloads while preserving full-run metrics.

## Performance Considerations

F-02 itself should not download or process real provider data. Its performance responsibility is to keep future S-02 and S-04 bounded: default 30-day runs, deterministic pure scoring functions, no external scoring calls, no import-time network work, and bounded quality-view chart/detail payloads for real completed runs. If Phase 4 introduces chart sampling now, it must preserve full-run metric calculations while limiting only response payload size.

## Migration Notes

No database migration is planned. Existing `DatasetRecord` and S-04 response shapes should remain compatible. If S-04 chart payload semantics change from "all points" to "sampled points", update tests and copy intentionally while preserving the API envelope fields unless a later S-04 integration plan changes the contract explicitly.

## References

- Roadmap F-02: `context/foundation/roadmap.md:76`
- F-01 quality contracts: `context/foundation/quality-contracts.md:192`
- Shared dataset contracts: `src/quantitative_sentiment_analysis/contracts/schemas.py:67`
- Stable serialization helpers: `src/quantitative_sentiment_analysis/contracts/serialization.py:35`
- S-04 quality horizon and response schema: `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:34`
- S-04 current chart point construction: `src/quantitative_sentiment_analysis/backtest_quality/metrics.py:43`
- S-04 payload-limit warning: `context/foundation/quality-contracts.md:224`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Human-Readable F-02 Policy

#### Automated

- [x] 1.1 Policy document exists and is non-empty: `test -s context/foundation/news-sentiment-policy.md` — 1f7e08c
- [x] 1.2 Policy document names the selected provider and thresholds: `rg -n "CryptoPanic|0\\.20|LONG|SHORT|FLAT|30-day|4 hours" context/foundation/news-sentiment-policy.md` — 1f7e08c
- [x] 1.3 Foundation docs reference the policy: `rg -n "news-sentiment-policy" context/foundation/quality-contracts.md context/foundation/roadmap.md` — 1f7e08c

#### Manual

- [x] 1.4 `news-sentiment-policy.md` is reviewed against PRD FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, and FR-015. — 1f7e08c
- [x] 1.5 The policy preserves BACKTEST-only analytical wording and does not introduce live trading, broker, order execution, or investment recommendation scope. — 1f7e08c
- [x] 1.6 The policy clearly says CryptoPanic must be smoke-tested before S-02 real ingestion. — 1f7e08c

### Phase 2: Executable Policy Contracts

#### Automated

- [x] 2.1 Policy package imports cleanly: `uv run python -c "import quantitative_sentiment_analysis.sentiment_policy"`
- [x] 2.2 Existing backend tests still pass: `uv run pytest tests/test_main.py tests/contracts tests/backtest_quality`
- [x] 2.3 Policy constants can be imported without network or environment secrets: `uv run python -c "from quantitative_sentiment_analysis.sentiment_policy import DEFAULT_POLICY_CONFIG; print(DEFAULT_POLICY_CONFIG.provider_name)"`

#### Manual

- [x] 2.4 Module names and exports make it clear this is policy/scoring, not provider ingestion.
- [x] 2.5 The executable constants match `context/foundation/news-sentiment-policy.md`.
- [x] 2.6 No API token, endpoint secret, or production CryptoPanic request logic is introduced in this phase.

### Phase 3: Policy Verification Tests

#### Automated

- [ ] 3.1 Sentiment policy tests pass: `uv run pytest tests/sentiment_policy`
- [ ] 3.2 Contract and quality tests still pass with policy tests: `uv run pytest tests/contracts tests/backtest_quality tests/sentiment_policy`
- [ ] 3.3 Determinism checks pass repeatedly: `uv run pytest tests/sentiment_policy/test_scoring.py tests/sentiment_policy/test_confidence.py`

#### Manual

- [ ] 3.4 Test names and failure messages explain policy intent rather than implementation trivia.
- [ ] 3.5 Tests do not require network access, CryptoPanic credentials, current time, or generated real-news datasets.
- [ ] 3.6 Tests verify semantic-safety boundaries without introducing product-facing trading recommendation wording.

### Phase 4: Downstream S-02/S-04 Handoff

#### Automated

- [ ] 4.1 Full backend test suite passes: `uv run pytest tests/test_main.py tests/contracts tests/backtest_quality tests/sentiment_policy`
- [ ] 4.2 Frontend tests pass if S-04 UI copy or payload semantics change: `cd frontend && npm test -- --run`
- [ ] 4.3 Foundation docs still point to the policy: `rg -n "news-sentiment-policy|CryptoPanic|sampled|4 hours" context/foundation`

#### Manual

- [ ] 4.4 S-02 handoff is specific enough to start `/10x-plan deterministic-news-dataset` without re-asking provider/scoring decisions.
- [ ] 4.5 S-04 handoff closes the roadmap's visualization question without expanding into an advanced dashboard.
- [ ] 4.6 Existing quality view still presents BACKTEST-only analytical quality and does not imply trading recommendations or executable signals.
- [ ] 4.7 The final handoff names the next sensible command as `/10x-plan deterministic-news-dataset` or `/10x-plan workspace-backtest-shell`, depending on which dependency track the user wants next.
