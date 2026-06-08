---
project: "Quantitative Sentiment Analysis"
context_type: greenfield
product_type: api
target_scale:
  users: small
  qps: null
  data_volume: null
timeline_budget:
  mvp_weeks: 3
  hard_deadline: null
  after_hours_only: true
created: 2026-06-08
updated: 2026-06-08
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  gray_areas_resolved:
    - topic: "context type"
      decision: "greenfield"
    - topic: "pain category"
      decision: "decision paralysis, workflow friction, missing capability, data trapped somewhere"
    - topic: "primary persona scope"
      decision: "individual intraday / swing trader"
    - topic: "auth strategy"
      decision: "login-based account for MVP"
    - topic: "role model"
      decision: "single trader role; no admin/viewer roles in MVP"
    - topic: "MVP scope"
      decision: "scoped down to BTCUSD BACKTEST thin vertical slice using one historical crypto-news source and dataset export"
    - topic: "timeline budget"
      decision: "3 weeks after-hours as a thin vertical slice"
    - topic: "Socrates round"
      decision: "shared auth softened, BTCUSD kept but later-swappable, BACKTEST kept with no live-ready implication, basic filtering marks noise rather than hiding it, directional bias wording preferred over trading signal, JSONL primary export"
    - topic: "product framing"
      decision: "API/backend service for a small single-user or handful-user audience; no hard deadline; after-hours work"
    - topic: "non-goals"
      decision: "no live streaming, no broker/order execution, no multi-instrument support, no multi-source aggregation, no production-grade trading recommendations, no advanced quality dashboard in MVP, no probabilistic multi-asset mapping"
  frs_drafted: 15
  quality_check_status: accepted
---

## Seed Idea

aplikacja do analizy sentymentu newsów finansowych i generowania sygnałów inwestycyjnych

## Vision & Problem Statement

Indywidualny trader aktywnie handlujący intraday / swing w trakcie sesji, szczególnie przy ważnych newsach makro i nagłych wydarzeniach rynkowych, nie jest w stanie wystarczająco szybko i obiektywnie ocenić sentymentu informacji, które czyta. Kosztem obecnego sposobu pracy są opóźnione reakcje, chaotyczne decyzje, utracone okazje i błędne wejścia na rynek.

Kluczowy insight: przewaga nie ginie na samym dostępie do informacji, tylko na zbyt wolnym i subiektywnym mapowaniu tekst -> sentyment -> wpływ na instrument w konkretnej chwili. Standardowe feedy newsów, X/Twitter i TradingView zostawiają ten krok traderowi, a w warunkach live tradingu interpretacja jest dokładnie tym miejscem, w którym znika przewaga informacyjna.

Pain categories: decision paralysis, workflow friction, missing capability, data trapped somewhere.

Scale note: at 100x scale, the domain rule would shift from one instrument and one source generating a deterministic dataset to a multi-instrument, multi-source, streaming event system with normalization and impact weighting, where each news item maps probabilistically to many assets in real time instead of deterministically to one context.

## User & Persona

Primary persona: indywidualny trader aktywnie handlujący intraday / swing, który podejmuje decyzje w krótkich oknach czasowych i potrzebuje natychmiastowej, uproszczonej warstwy decyzyjnej nad newsami zamiast surowych, rozproszonych informacji.

## Success Criteria

### Primary

- Trader can log in, select BTCUSD, run a BACKTEST over historical crypto news from one source such as CryptoPanic or an aggregated crypto-news feed, and export a training dataset as JSONL, with CSV as optional secondary output.
- Each exported dataset record contains timestamp, news headline, sentiment score in the range -1..+1, directional bias LONG/SHORT/FLAT, and confidence in the range 0..1.

### Secondary

- A minimal backtest-quality dashboard can show whether sentiment direction had a useful relationship with later BTCUSD price movement, using simple metrics such as correlation or hit rate and a basic sentiment-vs-price-movement view.

### Guardrails

- Dataset generation must be deterministic and reproducible: the same news input and timeframe produce the same output dataset, with no unseeded randomness in sentiment or signal generation.
- V1 must not imply live execution: BACKTEST output is a dataset only, with no broker integration, no order execution layer, and no suggestion that generated signals are ready for real trading.

## Scope Decision Log

- Initial flow included BACKTEST, LIVE streaming, multiple news sources, relevance filtering, NLP feature vectors, UI timeline, and integration with quantum-trading-system. This was flagged as MVP-too-big.
- V1 was scoped down to a thin vertical slice: BTCUSD only, BACKTEST only, one historical crypto-news source, simple sentiment/signal generation, and CSV/JSONL dataset export.

## User Stories

### US-01: Trader exports a BTCUSD sentiment training dataset

- **Given** a logged-in trader in their workspace
- **When** they select BTCUSD, choose a BACKTEST time range, run the analysis, and export the result
- **Then** they receive a JSONL dataset, optionally also CSV, whose records contain timestamp, headline, sentiment score, directional bias, and confidence

#### Acceptance Criteria

- The selected instrument is BTCUSD.
- The selected mode is BACKTEST, not LIVE.
- The exported records include timestamp, headline, sentiment score in the range -1..+1, directional bias LONG/SHORT/FLAT, and confidence in the range 0..1.
- Running the same input and timeframe again produces the same dataset.
- The output is a dataset only and does not trigger broker integration or order execution.

## Functional Requirements

### Access & Setup

- FR-001: Trader can log in to a workspace with account identity suitable for later quantum-trading-system integration. Priority: must-have
  > Socratic: Counter-argument considered: shared auth may bind the MVP too tightly to the larger system. Resolution: revised; login and workspace identity remain must-have, but shared auth with quantum-trading-system is not a hard dependency for v1.
- FR-002: Trader can select BTCUSD as the MVP instrument, with the instrument choice kept explicit so it can be swapped later. Priority: must-have
  > Socratic: Counter-argument considered: BTCUSD is a good first instrument, but must be easy to replace later. Resolution: kept BTCUSD for v1 and made future replaceability explicit.
- FR-003: Trader can run the BACKTEST mode without the product implying live-readiness. Priority: must-have
  > Socratic: Counter-argument considered: BACKTEST is the right first step, but the UI must not suggest the output is live-ready. Resolution: kept BACKTEST and made the no-live implication explicit.
- FR-004: Trader can define the BACKTEST time range, such as the last X days or a predefined range. Priority: must-have
  > Socratic: Counter-argument considered: without a time range, the dataset is not controllable or reproducible. Resolution: kept as must-have.

### News Ingestion & Context

- FR-005: System can retrieve historical news from one source, either CryptoPanic or one aggregated crypto-news feed. Priority: must-have
  > Socratic: Counter-argument considered: one source may bias the dataset but keeps scope bounded. Resolution: kept one source for v1.
- FR-006: System can attach each news item to a timestamp and crypto-relevance context for BTCUSD analysis. Priority: must-have
  > Socratic: Counter-argument considered: hard BTCUSD mapping may be falsely precise; crypto-relevant context may be enough. Resolution: revised wording to avoid over-precise mapping while preserving BTCUSD analysis context.
- FR-007: System can label news as noise or irrelevant without silently removing records from the dataset. Priority: must-have
  > Socratic: Counter-argument considered: filtering could hide important news. Resolution: revised; MVP should mark noise rather than drop it invisibly.
- FR-008: System can group news into time windows when producing export-ready model features. Priority: nice-to-have
  > Socratic: Counter-argument considered: grouping is only needed when exporting model features; per-news dataset is simpler. Resolution: demoted to nice-to-have for v1.

### Signal Generation

- FR-009: System can generate a sentiment score from -1 to +1 for each news item or time window. Priority: must-have
  > Socratic: Counter-argument considered: text sentiment and market impact are not the same thing. Resolution: kept text sentiment for MVP; market-impact modeling comes later.
- FR-010: System can generate a LONG, SHORT, or FLAT directional bias from sentiment. Priority: must-have
  > Socratic: Counter-argument considered: calling the output a trading signal may imply too much certainty in v1. Resolution: revised terminology to directional bias.
- FR-011: System can generate a confidence score from 0 to 1 that reflects classification confidence, not market certainty. Priority: must-have
  > Socratic: Counter-argument considered: confidence could be arbitrary or misleading without calibration. Resolution: revised; confidence means classification confidence only.
- FR-012: System can combine timestamp, headline, source identity, sentiment score, directional bias, and confidence into one structured record. Priority: must-have
  > Socratic: Counter-argument considered: a record without source_id or source_name is not auditable. Resolution: revised; source identity is part of the structured record.
- FR-013: System can produce deterministic output for the same input, timeframe, seed, and configuration. Priority: must-have
  > Socratic: Counter-argument considered: determinism may limit future probabilistic models. Resolution: revised; determinism applies to the same seed and configuration.

### Export & Evaluation

- FR-014: Trader can export the resulting dataset as JSONL, with CSV as an optional secondary format. Priority: must-have
  > Socratic: Counter-argument considered: two export formats increase scope; JSONL should be primary and CSV optional. Resolution: revised.
- FR-015: Trader can view a simple backtest-quality dashboard showing sentiment versus later BTCUSD price movement with basic correlation or hit-rate metrics. Priority: nice-to-have
  > Socratic: Counter-argument considered: dashboard must not block v1. Resolution: kept as nice-to-have only.

## Non-Functional Requirements

- Reproducibility: the same input, including time range, BTCUSD instrument, config, seed, and model version, always generates an identical JSONL dataset regardless of run count.
- Backtest runtime: processing 30 days of historical CryptoPanic news and generating the full dataset completes in <= 5 minutes on a standard developer machine.
- Auditability: every dataset record includes source_name, timestamp, run_id, and config_version so the result can be reproduced and debugged.
- Workspace privacy: inputs, outputs, and exports are isolated per workspace and visible only to the logged-in trader, with no cross-workspace leakage.
- Semantic safety: outputs are clearly presented as analytical/ML dataset fields and directional bias, not as investment recommendations or executable trading signals.

## Business Logic

Aplikacja bierze historyczne newsy dotyczace rynku crypto (CryptoPanic) w wybranym przedziale czasu dla BTCUSD i dla kazdego wydarzenia wyznacza sentyment, kierunkowy bias oraz confidence, zeby trader otrzymal deterministyczny dataset treningowy gotowy do uzycia w modelach w quantum-trading-system.

Inputs consumed by the rule: historical crypto news from CryptoPanic or a single aggregated crypto-news feed, selected BACKTEST time range, BTCUSD as the selected instrument, run configuration, seed, and model version.

Output produced by the rule: a reproducible JSONL dataset, optionally also CSV, with timestamp, headline, source identity, sentiment score, directional bias LONG/SHORT/FLAT, confidence, run_id, and config_version.

How the user encounters the rule: the trader logs in, chooses BTCUSD and a BACKTEST time range, runs the analysis, and exports the dataset for analytical and model-training use.

## Access Control

MVP uses login-based access with a single role: trader. The account identity is needed to connect historical signals, configurations, experiments, and live feeds into a reproducible workspace. Shared auth with quantum-trading-system is a desired integration direction, but it is not a hard dependency for the first thin vertical slice.

No admin/viewer split is planned for MVP. The product is single-user or experimental at this stage, and role complexity would not help the primary goal: iterating on signal quality.

Workspace separation matters: different sentiment-engine approaches, instrument sets, generated historical signals, and model-training data should remain attributable to the correct account/workspace.

## Non-Goals

- No LIVE streaming in v1: MVP does not stream current news or directional bias in real time.
- No broker/order execution: MVP does not place orders, integrate with brokers, or automate trading.
- No multi-instrument support: MVP is limited to BTCUSD.
- No multi-source aggregation: MVP uses CryptoPanic or one aggregated crypto-news feed only.
- No production-grade trading recommendations: output is a dataset and directional bias for analytical/ML use, not an investment recommendation.
- No advanced quality dashboard: dashboard remains nice-to-have and does not block MVP delivery.
- No probabilistic multi-asset mapping: probabilistic mapping of one news item to many assets is deferred to a later scale stage.

## Open Questions

None.

## Quality cross-check

Accepted on 2026-06-08: no gaps identified.

## Product Framing

- Product shape: API/backend service.
- First-version audience: only the user or a handful of users.
- Hard deadline: none.
- Work mode: after-hours.

## Forward: technical-roadmap

The product is expected to become part of a larger quantum-trading-system workflow. The user described two later integration stages: first, generating historical signals for model-training data; second, streaming real-time decisions to the main trading application.
