---
project: Quantitative Sentiment Analysis
version: 1
status: active
created: 2026-06-15
updated: 2026-06-15
roadmap_id: F-02
change_id: choose-news-and-sentiment-policy
---

# News and Sentiment Policy

This document is the foundation policy for V1 BTCUSD BACKTEST news sourcing,
relevance labeling, deterministic sentiment scoring, directional-bias mapping,
classification confidence, and the first backtest-quality visualization scope.
It fills the F-02 gap left intentionally open by
`context/foundation/quality-contracts.md`.

## Scope

This policy applies to:

- historical BTCUSD BACKTEST news retrieval decisions for S-02;
- relevance labels assigned to retrieved provider records;
- deterministic V1 sentiment score generation;
- deterministic mapping from sentiment score to `LONG`, `SHORT`, or `FLAT`
  directional bias;
- classification confidence semantics for generated dataset records;
- the minimum S-04 quality-view scope for real completed BACKTEST runs.

## Non-Scope

F-02 does not implement:

- a production Sharpe Terminal API client;
- persistent run storage, workspace shell, or export endpoints;
- multi-provider aggregation or provider fallback routing;
- LIVE streaming, broker integration, order execution, or investment advice;
- ML/LLM sentiment scoring;
- advanced quality dashboards beyond the minimal quality-view policy below.

## Provider Policy

V1 uses **Sharpe Terminal** as the single selected aggregated crypto-news feed for
MVP historical BTCUSD BACKTEST datasets.

Sharpe Terminal is selected because it is crypto-focused and better aligned with a
single-feed BTCUSD MVP than a broad general-news provider. S-02 must still treat
provider access as a verified dependency, not as an assumed implementation
detail: before production ingestion, S-02 must run a controlled token/API smoke
test proving that the configured Sharpe Terminal access can support the selected
BTCUSD BACKTEST use case and the required historical range.

If the Sharpe Terminal smoke test fails, S-02 must fail explicitly and surface the
provider limitation. It must not silently switch to another provider, fabricate
news records, or broaden the MVP into multi-source aggregation.

## Historical Range Policy

The default MVP BACKTEST historical range is a **30-day** window for BTCUSD.

This range is the first reproducibility and runtime target for S-02. It aligns
with the PRD expectation that processing 30 days of historical crypto news and
generating the dataset completes within the MVP runtime budget on a standard
developer machine.

S-02 may later expose shorter or longer ranges, but the 30-day range is the
required baseline for verification and documentation.

## Relevance Policy

Provider records are labeled, not silently removed.

Every retrieved and normalized provider record that reaches dataset generation
must receive one of the shared `RelevanceLabel` values:

| Label | Meaning |
| --- | --- |
| `RELEVANT` | BTC, BTCUSD, Bitcoin, or crypto-market news that can reasonably contribute to BTCUSD sentiment analysis. |
| `NOISE` | Provider placeholders, duplicates, spam-like items, malformed headlines, or operational artifacts that should be preserved for audit but excluded from quality metric denominators. |
| `IRRELEVANT` | Non-BTC crypto, off-topic market, general business, or unrelated records that should be preserved for audit but not treated as BTCUSD directional-bias evidence. |

S-02 may filter for UI presentation or pagination after labeling, but it must
not make the canonical dataset look as if excluded records never existed.

## Deterministic Scoring Policy

V1 sentiment scoring is deterministic local rule/lexicon scoring.

The scorer must:

- use normalized provider text such as headline, optional body, and available
  source metadata;
- return a bounded `sentiment_score` in `-1..1`;
- use versioned local rules or lexicon weights;
- avoid network calls, model APIs, wall-clock time, unseeded randomness, and
  environment-specific behavior;
- produce identical output for identical normalized input and policy version.

The initial lexicon should be intentionally small and auditable. Improving
sentiment quality is a later iteration; V1 prioritizes reproducibility and
inspection over linguistic sophistication.

## Directional-Bias Thresholds

Directional bias is derived from the deterministic text sentiment score:

| Sentiment score | Directional bias |
| --- | --- |
| `sentiment_score >= 0.20` | `LONG` |
| `sentiment_score <= -0.20` | `SHORT` |
| `-0.20 < sentiment_score < 0.20` | `FLAT` |

These thresholds are the first V1 policy, not a claim of market optimality. They
must be versioned through the generated record `config_version` so later tuning
can remain reproducible and auditable.

## Confidence Semantics

`confidence` is deterministic classification confidence in `0..1`, not market
certainty and not a probability that BTCUSD will move in the directional-bias
direction.

The V1 confidence formula should be based on deterministic inputs such as:

- absolute sentiment-score strength;
- relevance label;
- source identity completeness;
- headline/text completeness.

The formula must be bounded, auditable, and versioned. Product copy, API
messages, and exports must keep the phrase `classification confidence` when
explaining this field.

## Quality Horizon

The default backtest-quality horizon is **4 hours**, but V1 exposes a controlled
set of report horizons through the API and UI:

- **1 minute**
- **15 minutes**
- **1 hour**
- **4 hours**
- **24 hours**

The selected horizon is report metadata: it defines the requested evaluation
window for quality reporting. It does not by itself enrich completed BACKTEST
records with later BTCUSD movement. Deterministic price enrichment remains a
separate prerequisite before real completed runs can produce non-missing
`later_return` and `realized_direction` values.

S-04 already uses a 4-hour default fixture horizon. A later price-enrichment
slice should enrich completed BACKTEST records with deterministic later BTCUSD
movement fields that map cleanly into the S-04 quality input contract for the
selected supported horizon.

## Visualization Payload Policy

The minimum quality view for real completed runs is:

- correlation between sentiment score and later BTCUSD return;
- hit rate for `LONG`, `SHORT`, and `FLAT` directional bias versus realized
  later direction;
- a sampled sentiment-vs-later-return plot.

Metrics may be computed over the full deterministic run, but chart and detail
payloads must be bounded before real S-02 data is exposed through S-04. The
response may cap, sample, paginate, or explicitly limit `chart_points` and
detail rows. The UI must not imply that a sampled plot contains every record.

Noise and irrelevant records remain preserved for audit. They are excluded from
quality metric denominators when they are not evaluable as BTCUSD
directional-bias quality evidence, while still contributing to counts and
warnings where relevant.

## Semantic Safety

All product-facing surfaces must frame outputs as BACKTEST-only analytical
dataset fields.

Allowed framing:

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

Avoid product framing that implies live readiness, broker integration, order
execution, or investment recommendations. Documentation and tests may mention
avoided phrases only to define or verify the semantic-safety boundary.

## Downstream Handoffs

### S-02: Deterministic News Dataset

S-02 should normalize Sharpe Terminal records into the F-01 `DatasetRecord` fields,
preserve retrieved records with `relevance` labels, stamp the F-02 policy
`model_version` and `config_version`, and compute `input_fingerprint` from
normalized input content and deterministic run metadata.

Before real ingestion, S-02 must run a controlled Sharpe Terminal token/API smoke
test. If the configured access cannot support the 30-day BTCUSD BACKTEST use
case, S-02 must return an explicit provider limitation instead of silently
switching providers or fabricating data.

`deterministic-news-dataset` implements this as a provider boundary with
Sharpe Terminal configured by `SHARPE_API_KEY`, fixture-backed automated tests,
deterministic normalization, exact provider-ID dedupe, local rule/lexicon
scoring, bounded preview responses, and typed provider-limitation failures.
Automated verification remains offline; real Sharpe Terminal access is a controlled
manual smoke dependency.

### S-03: JSONL Export

S-03 should export records after S-02 has applied this policy. JSONL stability
continues to follow `context/foundation/quality-contracts.md`; F-02 supplies the
provider/scoring/config decisions that populate the existing fields.

### S-04: Backtest Quality View

S-04 should use the 4 hours default horizon, allow the supported V1 horizon
presets, and show correlation, hit rate, and sampled sentiment-vs-later-return
plot as the first required quality view. Metrics may use the full deterministic
run, but real-run chart/detail payloads must be bounded. The current backend
policy caps chart points deterministically while keeping metric denominators on
the full input set.

S-04 must keep BACKTEST-only analytical wording and must not fetch prices
directly or fabricate production run data before S-02 supplies completed
deterministic BACKTEST records.

The S-02 quality adapter feeds completed canonical dataset records to S-04 while
leaving `later_return` and `realized_direction` missing until deterministic price
enrichment exists. JSONL/CSV export remains deferred to S-03.

## Acceptance Checklist

- Sharpe Terminal is documented as the single MVP provider.
- S-02 is required to smoke-test Sharpe Terminal access before real ingestion.
- The default historical range is 30-day BTCUSD BACKTEST.
- Retrieved records are preserved with `RELEVANT`, `NOISE`, or `IRRELEVANT`.
- Sentiment scoring is deterministic local rule/lexicon scoring.
- Directional-bias thresholds are `>= 0.20 LONG`, `<= -0.20 SHORT`, otherwise
  `FLAT`.
- Confidence is classification confidence, not market certainty.
- The default quality horizon is 4 hours, with V1 report presets for 1 minute,
  15 minutes, 1 hour, 4 hours, and 24 hours.
- The first quality view uses correlation, hit rate, and a sampled plot with
  bounded payloads.
