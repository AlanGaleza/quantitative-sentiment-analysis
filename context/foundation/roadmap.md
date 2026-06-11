---
project: Quantitative Sentiment Analysis
version: 1
status: draft
created: 2026-06-08
updated: 2026-06-08
prd_version: 1
main_goal: quality
top_blocker: decisions
---

# Roadmap: Quantitative Sentiment Analysis

> Derived from `context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

Trader traci przewagę nie dlatego, że nie ma dostępu do informacji, tylko dlatego, że w trakcie sesji zbyt wolno mapuje tekst newsa na sentyment i wpływ na BTCUSD. MVP ma dostarczyć deterministyczny, audytowalny dataset treningowy z historycznych newsów oraz wymaganą wizualizację jakości backtestu, bez udawania live tradingu ani rekomendacji inwestycyjnych.

## North star

**S-04: Trader widzi jakość backtestu w UI** — to pierwszy dowód wartości produktu, bo pokazuje nie tylko wygenerowany dataset, ale też czy sentyment ma czytelny związek z ruchem ceny.

> "North star" oznacza tutaj najmniejszy pełny przepływ, którego dowiezienie udowadnia główną tezę produktu; jest ustawiony tak wcześnie, jak pozwalają zależności, bo pozostałe prace mają sens dopiero wtedy, gdy ten przepływ działa.

## At a glance

| ID | Change ID | Outcome (user can ...) | Prerequisites | PRD refs | Status |
|---|---|---|---|---|---|
| F-01 | define-quality-contracts | (foundation) contracts for workspace, run metadata, dataset schema, and non-advisory wording are fixed | — | FR-001, FR-003, FR-012, FR-013, FR-014, NFR-Reproducibility, NFR-Auditability, NFR-Workspace privacy, NFR-Semantic safety | ready |
| F-02 | choose-news-and-sentiment-policy | (foundation) source, relevance labeling, sentiment thresholds, and visualization scope are decided | F-01 | FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, FR-015 | blocked |
| S-01 | workspace-backtest-shell | trader can enter a workspace, select BTCUSD, choose BACKTEST, and define a time range | F-01 | US-01, FR-001, FR-002, FR-003, FR-004, NFR-Workspace privacy, NFR-Semantic safety | proposed |
| S-02 | deterministic-news-dataset | trader can run BTCUSD BACKTEST and receive auditable per-news records | F-02, S-01 | US-01, FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, FR-012, FR-013, NFR-Reproducibility, NFR-Backtest runtime, NFR-Auditability | blocked |
| S-03 | jsonl-export | trader can export the reproducible training dataset as JSONL | S-02 | US-01, FR-014, NFR-Reproducibility, NFR-Auditability | proposed |
| S-04 | backtest-quality-view | trader can view a basic backtest-quality visualization for BTCUSD | S-02 | FR-015 | blocked |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme | Chain | Note |
|---|---|---|---|
| A | Quality contracts | `F-01` -> `S-01` | Establishes identity, safety wording, and the BACKTEST shell before data work. |
| B | Dataset core | `F-02` -> `S-02` -> `S-03` | Turns the domain decisions into the training dataset and export. |
| C | Visualization | `S-04` | Joins Stream B at `S-02`; proves the chosen validation milestone after records exist. |

## Baseline

What's already in place in the codebase as of `2026-06-08` (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** absent but required — no UI framework is present; user corrected the baseline so visualization is now required in the roadmap.
- **Backend / API:** partial — FastAPI smoke app exists with `/` and `/health` in `src/quantitative_sentiment_analysis/main.py`, but no backtest, ingestion, sentiment, export, or auth endpoints.
- **Data:** absent — no database driver, ORM, migrations, storage, dataset schema, or seeded data layer exists.
- **Auth:** absent — PRD requires login/workspace identity, but there is no provider integration, token/session handling, or auth middleware.
- **Deploy / infra:** partial — Render Blueprint and public `/health` exist, but CI/CD and deploy verification are not automated.
- **Observability:** absent — no application logging policy, metrics, tracing, or error tracking exists.

## Foundations

### F-01: Define quality contracts

- **Outcome:** (foundation) contracts for workspace isolation, run metadata, dataset fields, deterministic configuration, and non-advisory wording are fixed.
- **Change ID:** define-quality-contracts
- **PRD refs:** FR-001, FR-003, FR-012, FR-013, FR-014, NFR-Reproducibility, NFR-Auditability, NFR-Workspace privacy, NFR-Semantic safety
- **Unlocks:** S-01, S-02, S-03; verification paths for reproducible JSONL and non-execution wording.
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Sequenced first because quality is the chosen goal; without contracts, later slices can accidentally produce non-reproducible or advisory outputs.
- **Status:** ready

### F-02: Choose news and sentiment policy

- **Outcome:** (foundation) the source, relevance labels, sentiment thresholds, directional-bias mapping, confidence meaning, and visualization scope are decided.
- **Change ID:** choose-news-and-sentiment-policy
- **PRD refs:** FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, FR-015
- **Unlocks:** S-02, S-04; resolves roadmap-wide decisions that block data generation and UI interpretation.
- **Prerequisites:** F-01
- **Parallel with:** S-01
- **Blockers:** —
- **Unknowns:**
  - Confirm whether the MVP source is CryptoPanic or another single aggregated crypto-news feed — Owner: user. Block: yes.
  - Define the first deterministic sentiment and directional-bias thresholds — Owner: user. Block: yes.
  - Define the minimum visualization that satisfies the required frontend view — Owner: user. Block: yes.
- **Risk:** The selected blocker is decisions; implementing scoring or UI before these calls would hide product uncertainty inside code.
- **Status:** blocked

## Slices

### S-01: Workspace BACKTEST shell

- **Outcome:** trader can enter a workspace, select BTCUSD, choose BACKTEST, and define a time range.
- **Change ID:** workspace-backtest-shell
- **PRD refs:** US-01, FR-001, FR-002, FR-003, FR-004, NFR-Workspace privacy, NFR-Semantic safety
- **Prerequisites:** F-01
- **Parallel with:** F-02
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Gives the workflow a safe BACKTEST-only frame before any dataset can be produced or interpreted.
- **Status:** proposed

### S-02: Deterministic news dataset

- **Outcome:** trader can run BTCUSD BACKTEST and receive auditable per-news records with sentiment, directional bias, confidence, source, run, and config metadata.
- **Change ID:** deterministic-news-dataset
- **PRD refs:** US-01, FR-005, FR-006, FR-007, FR-009, FR-010, FR-011, FR-012, FR-013, NFR-Reproducibility, NFR-Backtest runtime, NFR-Auditability
- **Prerequisites:** F-02, S-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Verify that the chosen source can provide the needed historical range for BTCUSD backtests — Owner: user. Block: yes.
- **Risk:** This is the core data path; if it is not deterministic and auditable, both export and visualization become misleading.
- **Status:** blocked

### S-03: JSONL export

- **Outcome:** trader can export the reproducible training dataset as JSONL for later model-training use.
- **Change ID:** jsonl-export
- **PRD refs:** US-01, FR-014, NFR-Reproducibility, NFR-Auditability
- **Prerequisites:** S-02
- **Parallel with:** S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Export is sequenced after dataset generation so the first artifact mirrors the audited records instead of inventing a second schema.
- **Status:** proposed

### S-04: Backtest quality view

- **Outcome:** trader can view a basic BTCUSD backtest-quality visualization showing sentiment against later price movement.
- **Change ID:** backtest-quality-view
- **PRD refs:** FR-015
- **Prerequisites:** S-02
- **Parallel with:** S-03
- **Blockers:** —
- **Unknowns:**
  - Decide whether the first view uses correlation, hit rate, sentiment-vs-price movement, or the smallest useful combination — Owner: user. Block: yes.
- **Risk:** This is the chosen validation milestone; shipping it before S-02 would create a visualization without trusted data.
- **Status:** blocked

## Backlog Handoff

| Roadmap ID | Change ID | Suggested issue title | Ready for `/10x-plan` | Notes |
|---|---|---|---|---|
| F-01 | define-quality-contracts | Define dataset and workspace quality contracts | yes | Run `/10x-plan define-quality-contracts` |
| F-02 | choose-news-and-sentiment-policy | Decide source, scoring, and visualization policy | no | Resolve blocking decisions first. |
| S-01 | workspace-backtest-shell | Add workspace and BACKTEST selection shell | no | Depends on F-01. |
| S-02 | deterministic-news-dataset | Generate deterministic BTCUSD news dataset | no | Depends on F-02 and S-01. |
| S-03 | jsonl-export | Export reproducible dataset as JSONL | no | Depends on S-02. |
| S-04 | backtest-quality-view | Show BTCUSD backtest quality view | no | Depends on S-02 and visualization decision. |

## Open Roadmap Questions

1. **Which exact news source is locked for MVP: CryptoPanic or another single aggregated crypto-news feed?** — Owner: user. Block: F-02, S-02.
2. **What deterministic sentiment and directional-bias thresholds should define LONG, SHORT, and FLAT in v1?** — Owner: user. Block: F-02, S-02.
3. **What is the smallest required frontend visualization: correlation, hit rate, sentiment-vs-price movement, or a combination?** — Owner: user. Block: F-02, S-04.

## Parked

- **LIVE streaming** — Why parked: PRD Non-Goals says v1 does not stream current news or directional bias in real time.
- **Broker/order execution** — Why parked: PRD Non-Goals says v1 does not place orders, integrate with brokers, or automate trading.
- **Multi-instrument support** — Why parked: PRD Non-Goals limits MVP to BTCUSD.
- **Multi-source aggregation** — Why parked: PRD Non-Goals keeps v1 to CryptoPanic or one aggregated crypto-news feed.
- **Production-grade trading recommendations** — Why parked: PRD Non-Goals frame output as dataset and directional bias for analytical/ML use only.
- **Advanced dashboard** — Why parked: the required frontend is limited to the smallest useful quality view; advanced dashboarding remains out of scope.
- **Probabilistic multi-asset mapping** — Why parked: PRD Non-Goals defer mapping one news item to many assets.

## Done

(Empty on first generation. `/10x-archive` appends an entry here — and flips that item's `Status` to `done` — when a change whose `Change ID` matches the item is archived.)
