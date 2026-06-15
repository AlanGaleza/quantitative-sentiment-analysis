---
project: Quantitative Sentiment Analysis
version: 1
status: active
created: 2026-06-11
updated: 2026-06-15
roadmap_id: F-01
change_id: define-quality-contracts
---

# Quality Contracts

This document is the foundation contract for workspace identity, deterministic run
metadata, dataset/export records, JSONL stability, workspace isolation, and
BACKTEST-only semantic safety. It is the human-readable source of truth for
F-01 and should be mirrored by shared Python contracts under
`src/quantitative_sentiment_analysis/contracts/`.

## Scope

These contracts apply to:

- workspace-scoped API routes, storage records, generated datasets, and exports;
- BTCUSD BACKTEST run metadata;
- per-news dataset records used for JSONL export and later model-training input;
- semantic-safety wording in product-facing API messages, frontend copy, README
  operator copy, and export metadata;
- downstream handoffs for S-01, S-02, S-03, and S-04.

## Non-Scope

F-01 does not decide:

- the news provider or provider API shape;
- the relevance labeling policy beyond the allowed label values;
- sentiment thresholds, directional-bias thresholds, or confidence formula;
- price movement enrichment or quality-view visualization scope;
- persistent storage technology or migration design;
- authentication provider implementation.

Those decisions belong to later roadmap items, especially F-02 and S-02. The
current F-02 decision source is `context/foundation/news-sentiment-policy.md`.

## Canonical Terms

| Term | Contract |
| --- | --- |
| Instrument | V1 supports `BTCUSD` only. |
| Mode | V1 supports `BACKTEST` only. |
| Directional bias | One of `LONG`, `SHORT`, or `FLAT`. Use `directional bias` in product-facing copy. |
| Relevance | One of `RELEVANT`, `NOISE`, or `IRRELEVANT`. Noise or irrelevant records are marked, not silently deleted. |
| Confidence | Classification confidence in `0..1`, not market certainty. |
| Sentiment score | Text sentiment in `-1..1`, not market-impact certainty. |
| Timestamp | A timezone-aware event timestamp. Export field name is `timestamp`. |
| Source identity | Each record must include `source_id` or `source_name`. |

## Workspace Isolation Contract

Workspace identity is explicit at every boundary:

- API routes that operate on workspace data include `workspace_id` in the route
  or authenticated workspace context.
- Run metadata includes `workspace_id`.
- Dataset records include `workspace_id`.
- Generated exports include `workspace_id` per record unless a later privacy
  review deliberately replaces it with a stable workspace alias.
- Storage reads and writes must filter by `workspace_id`; `run_id` alone is not
  a sufficient access boundary.
- Cross-workspace mixed records are invalid input for one deterministic run,
  export, or quality report.

Generated datasets containing real workspace identifiers or unsanitized news
exports must not be committed to the repository.

## Run Metadata Contract

A BACKTEST run is identified by a `run_id`, but reproducibility is established
by the deterministic run metadata, not by `run_id` alone.

Required run metadata:

- `workspace_id`
- `run_id`
- `instrument`: `BTCUSD`
- `mode`: `BACKTEST`
- `timeframe_start`
- `timeframe_end`
- `seed`
- `model_version`
- `config_version`
- `input_fingerprint`

`input_fingerprint` represents the normalized historical news input used by the
run. It should be based on stable input content and metadata, not on local file
paths, current wall-clock time, process-local randomness, or environment-specific
values.

The same normalized news input, timeframe, workspace, instrument, mode, seed,
model version, and config version must produce identical dataset records and
identical JSONL bytes.

## Dataset Record Contract

The canonical per-news dataset/export record contains:

| Field | Required | Contract |
| --- | --- | --- |
| `workspace_id` | yes | Workspace boundary for storage, export, and audit. |
| `run_id` | yes | Run identifier tying the record to run metadata. |
| `record_id` | optional | Stable per-record identifier when available. |
| `timestamp` | yes | Timezone-aware event timestamp. |
| `headline` | yes | Non-empty news headline text. |
| `source_id` | conditional | Required when `source_name` is absent. |
| `source_name` | conditional | Required when `source_id` is absent. |
| `instrument` | yes | `BTCUSD` in V1. |
| `mode` | yes | `BACKTEST` in V1. |
| `sentiment_score` | yes | Numeric value in `-1..1`. |
| `directional_bias` | yes | `LONG`, `SHORT`, or `FLAT`. |
| `confidence` | yes | Numeric value in `0..1`. |
| `relevance` | yes | `RELEVANT`, `NOISE`, or `IRRELEVANT`. |
| `model_version` | yes | Non-empty deterministic model/version identity. |
| `config_version` | yes | Non-empty deterministic configuration identity. |

The export-facing field is `timestamp`. Feature-specific response models may use
derived field names, such as S-04 `event_timestamp`, but they must map cleanly
from the canonical dataset timestamp.

## JSONL Stability Contract

JSONL is the primary export format. CSV is optional and must derive from the same
validated record set.

JSONL output rules:

- one dataset record per line;
- UTF-8 text with `\n` line endings;
- no blank lines;
- deterministic field ordering or deterministic JSON serialization;
- deterministic timestamp formatting;
- no current wall-clock timestamp in record bodies;
- no process-local randomness;
- no environment-specific paths or hostnames;
- stable output bytes for identical normalized inputs and run metadata.

If records are sorted before export, the sort key must be documented and stable.
Recommended default ordering is `timestamp`, then `record_id` when present, then
source identity, then headline.

## Semantic Safety Contract

Product-facing surfaces must frame outputs as analytical BACKTEST dataset fields.
They must not imply live trading readiness, broker integration, order execution,
or investment advice.

Allowed product-facing terms:

- `BACKTEST-only`
- `analytical dataset`
- `ML dataset`
- `directional bias`
- `LONG`
- `SHORT`
- `FLAT`
- `classification confidence`
- `not an investment recommendation`
- `not an executable trading signal`

Avoid these terms as positive product framing:

- `trading signal`
- `signal generation` when presented as executable output
- `buy recommendation`
- `sell recommendation`
- `investment recommendation`
- `trade now`
- `execute trade`
- `place order`
- `broker integration`
- `live-ready`
- `guaranteed profit`

Documentation and tests may quote avoided terms only to define or verify the
safety rule. Product UI, API success messages, and export metadata should use
the allowed terms instead.

## Downstream Handoffs

### S-01: Workspace BACKTEST Shell

S-01 should use the workspace/run identity contract and keep `BTCUSD` plus
`BACKTEST` explicit. The shell must not introduce LIVE mode or execution wording.
`workspace-backtest-shell` supplies a local/dev draft run shell for S-02: the
workspace, draft `run_id`, `BTCUSD`, `BACKTEST`, and timezone-aware timeframe are
fixed before deterministic news ingestion starts. The in-memory draft shell is
not durable completed-run storage.

### F-02: News and Sentiment Policy

F-02 policy decisions are defined in
`context/foundation/news-sentiment-policy.md`. That document owns provider
choice, relevance policy details, sentiment thresholds, directional-bias
threshold mapping, confidence meaning beyond classification confidence, and
visualization scope. F-01 only defines the field names and allowed value ranges
those decisions must populate.

### S-02: Deterministic News Dataset

S-02 should produce records matching the Dataset Record Contract and run metadata
matching the Run Metadata Contract. It should preserve noise or irrelevant
records with `relevance` labels and reject or surface records that cannot be
audited by source identity.

S-02 should consume the S-01 draft workspace/run/timeframe shell instead of
re-deciding workspace identity, instrument, mode, or timeframe semantics.

### S-03: JSONL Export

S-03 should serialize the validated dataset records as stable JSONL. Export tests
must cover repeated identical output for identical inputs and the absence of
broker/order side effects.

### S-04: Backtest Quality View

S-04 may use response-specific fields such as `event_timestamp`, but its input
records must remain compatible with the foundation dataset contract. S-04 must
not fetch prices directly or fabricate production run data before S-02 supplies
completed deterministic BACKTEST records.

S-04 compatibility aliases should reuse the shared `DirectionalBias` and
`RelevanceLabel` contract values while preserving the existing quality response
shape. In particular, S-04 JSON responses may keep `event_timestamp`; export and
dataset contracts continue to use canonical `timestamp`.

Before real S-02 data is exposed through S-04, quality-report payloads must cap,
sample, paginate, or explicitly limit large `chart_points` and detail outputs.
Metrics may still be computed over the full deterministic run; the response
payload should not become unbounded.

## Acceptance Checklist

- Shared Python contracts mirror this document.
- Tests cover score/confidence bounds, enum values, source identity, timezone-aware
  timestamps, deterministic JSONL serialization, run fingerprint stability, and
  workspace mismatch rejection.
- Product-facing wording uses BACKTEST-only analytical framing.
- F-02 decisions are referenced from `context/foundation/news-sentiment-policy.md`.
