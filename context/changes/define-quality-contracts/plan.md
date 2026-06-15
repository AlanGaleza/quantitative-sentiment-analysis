# Define Quality Contracts Implementation Plan

## Overview

Define the foundation quality contracts for workspace isolation, deterministic run metadata, dataset/export records, JSONL stability, and non-advisory wording. This change turns the F-01 roadmap item into a documented and code-backed contract that S-01, S-02, S-03, and the existing S-04 quality view can share.

## Current State Analysis

F-01 is the first ready roadmap item and has no prerequisites. Its purpose is to fix contracts before the workspace shell, deterministic dataset generation, JSONL export, and quality view depend on them. F-02 remains blocked and owns the news-source, sentiment-threshold, directional-bias mapping, and visualization-scope decisions.

The repository already contains S-04 contract/UI work in the current worktree. `src/quantitative_sentiment_analysis/backtest_quality/schemas.py` defines Pydantic models for `workspace_id`, `run_id`, `source_id` or `source_name`, sentiment/confidence bounds, `directional_bias`, `relevance`, `model_version`, and `config_version`. That is useful prior art, but it is still a view-specific package, not a foundation contract.

There is no shared `src/quantitative_sentiment_analysis/contracts/` package yet. Future slices would either duplicate field definitions or import from `backtest_quality`, which would invert the dependency: dataset generation and export should not depend on the quality-view module.

The worktree is dirty with S-04-related changes and reviews. Implementation of this plan must work with those files and must not revert unrelated user or generated changes.

## Desired End State

After this plan is implemented, `context/foundation/quality-contracts.md` is the human-readable source of truth for F-01 contracts, and `src/quantitative_sentiment_analysis/contracts/` contains the matching executable Python contracts. The contracts define the minimal deterministic BTCUSD BACKTEST dataset record, run identity/fingerprint metadata, workspace privacy invariants, stable JSONL serialization expectations, and semantic-safety terms.

The shared contracts are covered by focused tests for enum values, score/confidence bounds, source identity, timezone-aware timestamps, deterministic serialization, fingerprint stability, workspace mismatch rejection, and user-facing wording checks. Existing S-04 schemas remain externally compatible while importing or validating against the shared foundation contract where appropriate.

### Key Discoveries:

- F-01 is ready and unlocks S-01, S-02, and S-03 in `context/foundation/roadmap.md:32` and `context/foundation/roadmap.md:68`.
- PRD guardrails require deterministic dataset output and BACKTEST-only framing in `context/foundation/prd.md:41`.
- PRD export records require timestamp, headline, sentiment score, directional bias, and confidence in `context/foundation/prd.md:56`.
- PRD NFRs require reproducibility, auditability, workspace privacy, and semantic safety in `context/foundation/prd.md:106`.
- Existing S-04 `QualityInputRecord` already validates many future dataset fields in `src/quantitative_sentiment_analysis/backtest_quality/schemas.py:53`.
- S-04 final review leaves a future S-02 risk: real completed-run quality reports must not expose unbounded chart payloads in `context/changes/s-04/reviews/impl-review-final.md:23`.

## What We're NOT Doing

- No F-02 decisions: do not choose the news provider, relevance policy, sentiment thresholds, confidence formula, or directional-bias threshold mapping.
- No S-01 implementation: do not add auth, login screens, workspace creation, or BACKTEST selection UI/API.
- No S-02 implementation: do not implement news ingestion, sentiment scoring, backtest orchestration, price movement enrichment, or persistent run storage.
- No S-03 implementation: do not build the actual export endpoint or storage-backed export workflow.
- No LIVE mode, broker integration, order execution, or investment-recommendation wording.
- No rewrite of the S-04 UI or metric engine beyond the compatibility work needed to align shared contract definitions.
- No database migration; this is a contract and validation foundation.

## Implementation Approach

Use a contract-first implementation. First write the foundation contract document, then add shared Python contracts, then add focused tests, and finally align S-04 imports/compatibility without changing the public S-04 API response shape.

The canonical dataset/export field for PRD and JSONL remains `timestamp`. Existing S-04 quality-view models may keep `event_timestamp` as their response-specific field in this change, but they should import shared enum values and shared validation helpers where that reduces drift.

## Critical Implementation Details

### Timing & lifecycle

F-01 must not absorb blocked F-02 decisions. The contracts can define fields such as `relevance`, `sentiment_score`, `directional_bias`, `confidence`, `seed`, `model_version`, and `config_version`, but they must not define the actual source provider, scoring thresholds, or confidence formula.

### State sequencing

Run determinism must be based on normalized inputs rather than current wall-clock time. The run contract should identify `workspace_id`, selected timeframe, `instrument=BTCUSD`, `mode=BACKTEST`, `seed`, `model_version`, `config_version`, and an input/news fingerprint so the same deterministic inputs can be compared across reruns.

### User experience spec

Semantic safety applies to user-facing API messages, frontend copy, README operator-facing copy, and export metadata. Historical planning notes can mention old wording only when documenting prior decisions, but new product-facing surfaces must use `directional bias`, `LONG`, `SHORT`, `FLAT`, and `BACKTEST-only` analytical framing.

## Phase 1: Foundation Contract Document

### Overview

Create the human-readable source of truth for quality contracts and make it easy for future plans to reference one document instead of rediscovering PRD and S-04 decisions.

### Changes Required:

#### 1. Quality contracts foundation document

**File**: `context/foundation/quality-contracts.md`

**Intent**: Define the canonical F-01 contracts for workspace identity, run metadata, dataset/export records, deterministic serialization, workspace privacy, semantic safety, and downstream handoffs.

**Contract**: The document must include sections for scope, non-scope, canonical dataset fields, run metadata/fingerprint inputs, JSONL stability, workspace isolation invariants, allowed and banned wording, and handoff notes for S-01/S-02/S-03/S-04. It must explicitly state that F-02 owns provider and scoring-policy decisions.

#### 2. Repository guideline pointer

**File**: `AGENTS.md`

**Intent**: Point future agents to `context/foundation/quality-contracts.md` from the Data Contracts section without duplicating the entire schema.

**Contract**: Keep existing hard rules intact. Add a concise reference that foundation quality contracts are the canonical source for workspace/run/dataset/export invariants once this change lands.

### Success Criteria:

#### Automated Verification:

- Foundation contract document exists and is non-empty: `test -s context/foundation/quality-contracts.md`
- Repository guideline file still exists and is non-empty: `test -s AGENTS.md`
- No archived context files are modified by this change: `git diff --name-only -- context/archive`

#### Manual Verification:

- `quality-contracts.md` is reviewed against PRD FR-001, FR-003, FR-012, FR-013, FR-014 and the reproducibility/auditability/workspace/privacy/safety NFRs.
- The document clearly separates F-01 contracts from blocked F-02 source/scoring/visualization decisions.
- The document captures the S-04 large-run payload observation as a downstream guard for real S-02 integration.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Shared Contract Package

### Overview

Add a shared package for reusable Python contracts that future backend modules can import without depending on `backtest_quality`.

### Changes Required:

#### 1. Contracts package namespace

**File**: `src/quantitative_sentiment_analysis/contracts/__init__.py`

**Intent**: Provide a stable import surface for shared contract models, enums, serialization helpers, and safety constants.

**Contract**: The package must have no runtime side effects and must not import FastAPI, frontend code, storage adapters, or `backtest_quality` modules.

#### 2. Shared schema contracts

**File**: `src/quantitative_sentiment_analysis/contracts/schemas.py`

**Intent**: Define canonical Pydantic contracts and enums for foundation data shapes.

**Contract**: Include these conceptual contracts and invariants:

- `Instrument` with `BTCUSD` as the only V1 value.
- `RunMode` with `BACKTEST` as the only V1 value.
- `DirectionalBias` with `LONG`, `SHORT`, and `FLAT`.
- `RelevanceLabel` with `RELEVANT`, `NOISE`, and `IRRELEVANT`.
- Workspace/run identity models carrying `workspace_id` and `run_id`.
- Run metadata covering workspace, run, selected timeframe, instrument, mode, seed, model version, config version, and input fingerprint.
- Dataset record model covering `workspace_id`, `run_id`, optional `record_id`, `timestamp`, `headline`, `source_id` or `source_name`, `sentiment_score`, `directional_bias`, `confidence`, `relevance`, `model_version`, and `config_version`.

Timestamps must be timezone-aware. Sentiment score must be bounded to `-1..1`, confidence must be bounded to `0..1`, and each record must include either `source_id` or `source_name`.

#### 3. Deterministic serialization contract

**File**: `src/quantitative_sentiment_analysis/contracts/serialization.py`

**Intent**: Centralize deterministic JSON/JSONL serialization and run fingerprint expectations.

**Contract**: Expose helpers for stable JSON-compatible model data, a stable JSONL line for one dataset record, and deterministic fingerprint material for run metadata. The contract must not include current time, process-local randomness, filesystem paths, or environment-specific values in deterministic output.

#### 4. Semantic safety contract

**File**: `src/quantitative_sentiment_analysis/contracts/safety.py`

**Intent**: Define allowed terms and banned user-facing wording for BACKTEST-only analytical surfaces.

**Contract**: Expose constants or validation helpers that make it easy to check text for approved terms and banned recommendation/execution wording. The helper must support explicit exemptions for historical planning context or tests that quote banned terms as examples.

### Success Criteria:

#### Automated Verification:

- Shared contract package imports cleanly: `uv run python -c "import quantitative_sentiment_analysis.contracts"`
- Source compiles: `uv run python -m compileall src`
- Existing backend tests still pass after adding the package: `uv run pytest tests/test_main.py tests/backtest_quality`

#### Manual Verification:

- The shared package does not depend on S-04 or any future S-02 storage implementation.
- Field names and enum values match `context/foundation/quality-contracts.md`.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Contract Verification Tests

### Overview

Add automated verification for the shared contracts so future slices fail fast when they drift from F-01 decisions.

### Changes Required:

#### 1. Contract test package

**File**: `tests/contracts/__init__.py`

**Intent**: Establish a test namespace for foundation contract tests.

**Contract**: The package contains no runtime fixtures with real workspace identifiers or real news exports.

#### 2. Schema invariant tests

**File**: `tests/contracts/test_schemas.py`

**Intent**: Verify enum values, required audit fields, score/confidence bounds, timezone-aware timestamps, source identity rules, and workspace/run identity constraints.

**Contract**: Tests must cover `BTCUSD`, `BACKTEST`, `LONG|SHORT|FLAT`, `RELEVANT|NOISE|IRRELEVANT`, sentiment outside `-1..1`, confidence outside `0..1`, missing source identity, naive timestamp rejection, and preservation of workspace/run/model/config metadata.

#### 3. Serialization and determinism tests

**File**: `tests/contracts/test_serialization.py`

**Intent**: Verify stable JSON-compatible data, stable JSONL lines, deterministic fingerprint material, and repeated output equality for equivalent inputs.

**Contract**: Tests must assert that repeated serialization of the same record is byte-stable, reordered input material does not change deterministic fingerprint output where order is declared irrelevant, and changed seed/model/config/timeframe/fingerprint material changes the run identity or fingerprint.

#### 4. Semantic safety tests

**File**: `tests/contracts/test_safety.py`

**Intent**: Verify the allowed/banned wording contract on curated product-facing surfaces.

**Contract**: Tests must check safety helpers directly and scan only agreed user-facing files or strings. Historical context docs may be excluded when they quote old terms as prior decisions.

### Success Criteria:

#### Automated Verification:

- Contract tests pass: `uv run pytest tests/contracts`
- Contract and S-04 tests pass together: `uv run pytest tests/contracts tests/backtest_quality`
- Full backend tests pass: `uv run pytest`
- Source and tests compile: `uv run python -m compileall src tests`
- Dependency lock remains valid: `uv lock --check`

#### Manual Verification:

- Test coverage is reviewed against `AGENTS.md` Data Contracts and Testing Guidelines.
- Safety tests are strict enough for product-facing copy but do not fail solely because historical planning docs quote banned terms.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: S-04 Compatibility and Downstream Handoff

### Overview

Align the existing S-04 quality-view contracts with the shared foundation contract while preserving the current API and frontend response shapes.

### Changes Required:

#### 1. Backtest quality schema compatibility

**File**: `src/quantitative_sentiment_analysis/backtest_quality/schemas.py`

**Intent**: Reduce drift by reusing shared enums and validation helpers where practical.

**Contract**: `DirectionalBias` and `RelevanceLabel` must come from the shared contract package or be compatibility aliases that remain value-identical to the shared contract. Existing S-04 response field names, including `event_timestamp`, must not change in this phase unless all backend and frontend tests are updated to preserve the external JSON contract intentionally.

#### 2. Backtest quality package exports

**File**: `src/quantitative_sentiment_analysis/backtest_quality/__init__.py`

**Intent**: Preserve existing imports used by tests and callers after shared contract extraction.

**Contract**: Existing imports from `quantitative_sentiment_analysis.backtest_quality` continue to work for S-04 tests, even if the underlying enum definitions move into `contracts`.

#### 3. Compatibility regression tests

**File**: `tests/contracts/test_backtest_quality_compatibility.py`

**Intent**: Verify that S-04 still accepts and returns contract-compatible values.

**Contract**: Tests must cover enum value identity, source identity compatibility, workspace/run/config/model metadata preservation, and unchanged JSON response shape for the fixture-backed quality report route.

#### 4. Downstream handoff note

**File**: `context/foundation/quality-contracts.md`

**Intent**: Record the S-04 large-run payload guard for later real S-02 integration.

**Contract**: The note must say that metrics may be computed over the full run, but real quality-report payloads must cap, sample, paginate, or explicitly limit large `chart_points`/detail outputs before exposing real S-02 data.

### Success Criteria:

#### Automated Verification:

- S-04 compatibility tests pass: `uv run pytest tests/contracts/test_backtest_quality_compatibility.py`
- Existing S-04 tests still pass: `uv run pytest tests/backtest_quality`
- Full backend tests pass: `uv run pytest`
- Local fixture quality route still returns a BTCUSD BACKTEST report when enabled: `QSA_RUNTIME_ENV=local QSA_BACKTEST_QUALITY_PROVIDER=local-fixture uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- Health endpoint still responds while the local API is running: `curl -fsS http://127.0.0.1:8000/health`

#### Manual Verification:

- S-04 UI/API language still says BACKTEST-only analytical quality and does not imply investment recommendations or executable trading behavior.
- Future S-02/S-04 integration notes are clear enough that real large-run payloads will not ship unbounded by accident.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 5: Final Verification and Handoff

### Overview

Run the full verification set, update the brief if implementation details changed, and leave the next slices with clear contract references.

### Changes Required:

#### 1. Plan brief alignment

**File**: `context/changes/define-quality-contracts/plan-brief.md`

**Intent**: Keep the brief aligned with any concrete contract decisions made during implementation.

**Contract**: The brief must identify the key decisions: docs plus code-backed contracts, shared `contracts` package, PRD-minimum dataset plus workspace/run/model/relevance fields, full deterministic run fingerprint material, route/record/storage/export workspace invariant, allowed/banned wording list, and unit plus S-04 compatibility tests.

#### 2. Change notes

**File**: `context/changes/define-quality-contracts/change.md`

**Intent**: Keep the change identity current while implementation progresses.

**Contract**: Preserve the `change_id`. Update `status` only according to the active 10x workflow; do not mark archived manually and do not write to `context/archive/`.

### Success Criteria:

#### Automated Verification:

- Backend lock remains valid: `uv lock --check`
- Full backend tests pass: `uv run pytest`
- Source and tests compile: `uv run python -m compileall src tests`
- Whitespace check passes: `git diff --check`
- No archived files are modified: `git diff --name-only -- context/archive`

#### Manual Verification:

- `context/foundation/quality-contracts.md` is accepted as the contract source for S-01/S-02/S-03 planning.
- The implementation does not include F-02 decisions about provider, thresholds, confidence formula, or visualization scope.
- The final handoff names the next sensible command as `/10x-plan choose-news-and-sentiment-policy` or `/10x-plan workspace-backtest-shell`, depending on which roadmap track the user wants next.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before closing the change.

---

## Testing Strategy

### Unit Tests:

- Shared enum values for `BTCUSD`, `BACKTEST`, `LONG`, `SHORT`, `FLAT`, `RELEVANT`, `NOISE`, and `IRRELEVANT`.
- Dataset record validation for required workspace/run/source/headline/model/config fields.
- Sentiment score `-1..1`, confidence `0..1`, and non-finite numeric rejection where numeric fields are present.
- Timezone-aware timestamp validation.
- Stable JSONL serialization and deterministic fingerprint material.
- Semantic safety helper behavior for allowed terms and banned product-facing wording.

### Integration Tests:

- S-04 schema compatibility with shared contract values.
- S-04 fixture-backed quality route still returns the same run-scoped JSON shape after shared contract extraction.
- Existing `/health` behavior remains unchanged.

### Manual Testing Steps:

1. Review `context/foundation/quality-contracts.md` against PRD and AGENTS data-contract rules.
2. Confirm the document excludes F-02 decisions.
3. Confirm user-facing copy still uses BACKTEST-only analytical wording.
4. Confirm future S-02/S-03 planning can point to the shared contract package and foundation doc.

## Performance Considerations

The shared contracts should be lightweight Pydantic models and pure helpers. Stable serialization and fingerprint material may process a run's normalized input metadata, but F-01 should not require hashing large raw files or storing generated exports in memory. Large-run chart/report payload limits are recorded as a downstream S-02/S-04 integration guard.

## Migration Notes

No database migration is planned. Existing S-04 JSON response shape should remain stable. If enums move into the shared `contracts` package, preserve `backtest_quality` re-exports so current imports and tests keep working.

## References

- Roadmap F-01: `context/foundation/roadmap.md`
- Product requirements: `context/foundation/prd.md`
- Repository rules: `AGENTS.md`
- Existing S-04 plan: `context/changes/s-04/plan.md`
- S-04 final review: `context/changes/s-04/reviews/impl-review-final.md`
- Current S-04 schemas: `src/quantitative_sentiment_analysis/backtest_quality/schemas.py`
- Current S-04 metrics: `src/quantitative_sentiment_analysis/backtest_quality/metrics.py`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` - <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Foundation Contract Document

#### Automated

- [x] 1.1 Foundation contract document exists and is non-empty: `test -s context/foundation/quality-contracts.md` — fdeac52
- [x] 1.2 Repository guideline file still exists and is non-empty: `test -s AGENTS.md` — fdeac52
- [x] 1.3 No archived context files are modified by this change: `git diff --name-only -- context/archive` — fdeac52

#### Manual

- [x] 1.4 `quality-contracts.md` is reviewed against PRD FR-001, FR-003, FR-012, FR-013, FR-014 and the reproducibility/auditability/workspace/privacy/safety NFRs. — fdeac52
- [x] 1.5 The document clearly separates F-01 contracts from blocked F-02 source/scoring/visualization decisions. — fdeac52
- [x] 1.6 The document captures the S-04 large-run payload observation as a downstream guard for real S-02 integration. — fdeac52

### Phase 2: Shared Contract Package

#### Automated

- [x] 2.1 Shared contract package imports cleanly: `uv run python -c "import quantitative_sentiment_analysis.contracts"` — 2c280c7
- [x] 2.2 Source compiles: `uv run python -m compileall src` — 2c280c7
- [x] 2.3 Existing backend tests still pass after adding the package: `uv run pytest tests/test_main.py tests/backtest_quality` — 2c280c7

#### Manual

- [x] 2.4 The shared package does not depend on S-04 or any future S-02 storage implementation. — 2c280c7
- [x] 2.5 Field names and enum values match `context/foundation/quality-contracts.md`. — 2c280c7

### Phase 3: Contract Verification Tests

#### Automated

- [x] 3.1 Contract tests pass: `uv run pytest tests/contracts`
- [x] 3.2 Contract and S-04 tests pass together: `uv run pytest tests/contracts tests/backtest_quality`
- [x] 3.3 Full backend tests pass: `uv run pytest`
- [x] 3.4 Source and tests compile: `uv run python -m compileall src tests`
- [x] 3.5 Dependency lock remains valid: `uv lock --check`

#### Manual

- [x] 3.6 Test coverage is reviewed against `AGENTS.md` Data Contracts and Testing Guidelines.
- [x] 3.7 Safety tests are strict enough for product-facing copy but do not fail solely because historical planning docs quote banned terms.

### Phase 4: S-04 Compatibility and Downstream Handoff

#### Automated

- [ ] 4.1 S-04 compatibility tests pass: `uv run pytest tests/contracts/test_backtest_quality_compatibility.py`
- [ ] 4.2 Existing S-04 tests still pass: `uv run pytest tests/backtest_quality`
- [ ] 4.3 Full backend tests pass: `uv run pytest`
- [ ] 4.4 Local fixture quality route still returns a BTCUSD BACKTEST report when enabled: `QSA_RUNTIME_ENV=local QSA_BACKTEST_QUALITY_PROVIDER=local-fixture uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
- [ ] 4.5 Health endpoint still responds while the local API is running: `curl -fsS http://127.0.0.1:8000/health`

#### Manual

- [ ] 4.6 S-04 UI/API language still says BACKTEST-only analytical quality and does not imply investment recommendations or executable trading behavior.
- [ ] 4.7 Future S-02/S-04 integration notes are clear enough that real large-run payloads will not ship unbounded by accident.

### Phase 5: Final Verification and Handoff

#### Automated

- [ ] 5.1 Backend lock remains valid: `uv lock --check`
- [ ] 5.2 Full backend tests pass: `uv run pytest`
- [ ] 5.3 Source and tests compile: `uv run python -m compileall src tests`
- [ ] 5.4 Whitespace check passes: `git diff --check`
- [ ] 5.5 No archived files are modified: `git diff --name-only -- context/archive`

#### Manual

- [ ] 5.6 `context/foundation/quality-contracts.md` is accepted as the contract source for S-01/S-02/S-03 planning.
- [ ] 5.7 The implementation does not include F-02 decisions about provider, thresholds, confidence formula, or visualization scope.
- [ ] 5.8 The final handoff names the next sensible command as `/10x-plan choose-news-and-sentiment-policy` or `/10x-plan workspace-backtest-shell`, depending on which roadmap track the user wants next.
