# Test Plan

> Phased test rollout for this project. Strategy is frozen at the top
> (§1-§5); cookbook patterns at the bottom (§6) fill in as phases ship.
> Read before writing any new test.
>
> Refresh: re-run `/10x-test-plan --refresh` when stale (see §8).
>
> Last updated: 2026-06-15

## 1. Strategy

Tests follow three non-negotiable principles for this project:

1. **Cost x signal.** Najtanszy test, ktory daje realny sygnal dla danego
   ryzyka, wygrywa. Nie promuj do e2e tylko dlatego, ze e2e "wydaje sie
   bezpieczniejsze". Nie dokladaj warstwy AI-native nad deterministyczny test,
   ktory juz lapie ta regresje.
2. **User concerns are first-class evidence.** Ryzyka wskazane w wywiadzie
   maja taka sama wage jak PRD, roadmapa i churn: deterministycznosc datasetu,
   prawdziwosc metryk quality view, pipeline providera i granice relevance sa
   tu traktowane jako pierwszorzedne evidence.
3. **Risks are scenarios, not code locations.** This plan documents *what
   could fail* and *why we believe it's likely* -- drawn from documents,
   interview, and codebase *signal* (churn, structure, test base). It does
   NOT claim to know which line owns the failure. That knowledge is
   produced by `/10x-research` during each rollout phase. If the plan and
   research disagree about where the failure lives, research is the
   ground truth.

Hot-spot scope used for likelihood weighting: `src/quantitative_sentiment_analysis`,
`frontend/src`. Scoped history had 22 commits in the last 30 days; strongest
churn signals were `frontend/src/features` (27 changed-path hits),
`src/quantitative_sentiment_analysis/backtest_dataset` (15), and
`src/quantitative_sentiment_analysis/backtest_quality` (14).

## 2. Risk Map

The top failure scenarios this project must protect against, ordered by
risk = impact x likelihood. Risks are failure scenarios in user / business
terms, not test names. The Source column cites evidence that surfaced the
risk, never a specific file as the failure owner.

| # | Risk (failure scenario) | Impact | Likelihood | Source (evidence -- not anchor) |
|---|---|---|---|---|
| 1 | Ten sam news input, timeframe, workspace, seed, model version i config version daja inny dataset albo inne bajty JSONL. | High | High | PRD 41, 57, 94, 106; quality contracts 98-100, 133-143; interview Q1; hot-spot dir `src/quantitative_sentiment_analysis/backtest_dataset` (15 commits/30d) |
| 2 | Workspace/run boundary pozwala zapisac, odczytac albo wyeksportowac dataset nalezacy do innego workspace. | High | Medium | PRD 109, 122-128; quality contracts 57-70; tech-stack `has_auth`; abuse lens |
| 3 | `NOISE` albo `IRRELEVANT` sa po cichu usuwane z danych audytowych albo liczone w quality metrics tak, ze metryki sa falszywe. | High | High | PRD 79-80; policy 70-84, 157-160; interview Q4 |
| 4 | Quality dashboard pokazuje metryki mimo braku wiarygodnego pozniejszego ruchu ceny. | High | High | roadmap 132-143; quality contracts 233-254; policy 135-155; interview Q2; hot-spot dir `src/quantitative_sentiment_analysis/backtest_quality` (14 commits/30d) |
| 5 | Provider normalization/dedupe gubi rekordy, blednie scala duplikaty albo traci source identity/source name. | High | High | policy 42-56, 188-203; quality contracts 102-123; interview Q3; hot-spot dir `src/quantitative_sentiment_analysis/backtest_dataset` (15 commits/30d) |
| 6 | API, UI albo export metadata prezentuja `LONG`/`SHORT`/`FLAT` jako executable trading signal zamiast `directional bias` dla BACKTEST datasetu. | High | Medium | PRD 41-42, 110, 130-136; quality contracts 149-184; AGENTS hard rules |

### Risk Response Guidance

| Risk | What would prove protection | Must challenge | Context `/10x-research` must ground | Likely cheapest layer | Anti-pattern to avoid |
|---|---|---|---|---|---|
| #1 | Identyczne wejscie i deterministyczne run metadata produkuja identyczne rekordy oraz identyczne JSONL bytes. | To, ze obiekty walidacyjne sa takie same, nie znaczy, ze eksport bytes, ordering i timestamps sa stabilne. | Ordering guarantee, input fingerprint, serializer boundary, timestamp formatting, seed/config/model version handling. | contract + API integration | Oracle skopiowany z implementacji; test happy-path-only bez powtornego runu. |
| #2 | Kazdy storage/API/export boundary wymaga zgodnego `workspace_id`; sam `run_id` nie wystarcza do dostepu. | Login albo draft run nie oznacza ownership konkretnego completed datasetu. | Workspace identity shape, storage filters, route parameters, error semantics for mismatch. | integration + abuse contract | Over-mocking store boundary albo test bez negatywnego workspace mismatch. |
| #3 | `NOISE`/`IRRELEVANT` zostaja w canonical/audit dataset, ale nie zasilaja denominatorow quality metrics jako BTCUSD bias evidence. | Filtrowanie w UI/pagination nie moze byc mylone z zachowaniem canonical records. | Relevance policy, metric denominator rules, warnings/counts, dataset-to-quality adapter contract. | integration + metric tests | Assertion copied from current metric formula instead of policy oracle. |
| #4 | Brak movement fields daje explicit warning albo empty evaluable metrics, nigdy pozorna korelacje/hit rate. | Zero, null albo empty movement nie moze byc traktowane jak prawdziwy realized outcome. | Quality input contract, missing-data semantics, backend response shape, frontend rendering of warnings/empty states. | backend integration + frontend component | Meaningless snapshot albo happy path with complete movement data only. |
| #5 | Provider fixtures z missing fields, duplicates i source edge cases daja stabilne, audytowalne records bez silent drop. | Provider ID/source fields sa zawsze kompletne i unikalne. | External provider boundary, fixture source of truth, dedupe key, source fallback, provider limitation semantics. | fixture-backed integration | Brittle ordering assumption albo mockowanie internal normalization instead of provider edge. |
| #6 | Product-facing text and export metadata keep BACKTEST-only analytical wording and never frame directional bias as executable advice. | Copy tests sa kosmetyczne; wording is part of semantic safety. | API messages, frontend labels, export headers/metadata, allowed/forbidden wording contract. | contract + component | Broad snapshot without semantic assertions. |

## 3. Phased Rollout

Each row is a discrete rollout phase that will open its own change folder
via `/10x-new`. Status moves left-to-right through the values below; the
orchestrator updates Status as artifacts appear on disk.

| # | Phase name | Goal (one line) | Risks covered | Test types | Status | Change folder |
|---|---|---|---|---|---|---|
| 1 | Determinism and workspace contracts | Zablokowac regresje stabilnosci datasetu/JSONL oraz access boundary. | #1, #2 | contract + API integration | complete | context/changes/testing-determinism-and-workspace-contracts/ |
| 2 | Provider relevance pipeline | Utrwalic normalizacje, dedupe, source identity i relevance semantics. | #3, #5 | fixture-backed integration | not started | - |
| 3 | Quality view truthfulness | Zapobiec falszywym quality metrics i blednym warning/status UI. | #3, #4 | backend integration + frontend component | not started | - |
| 4 | Semantic safety and workflow gates | Zablokowac advisory wording i ustawic floor lokalnych/CI komend. | #6, cross-cutting | contract/component + gates | not started | - |

**Status vocabulary** (fixed -- parser literals): `not started`, `change opened`,
`researched`, `planned`, `implementing`, `complete`.

## 4. Stack

Classic test base is meaningful: 31 test files across backend contracts/features
and frontend feature/component tests. This rollout extends the suite instead of
bootstrapping it from zero.

| Layer | Tool | Version | Notes |
|---|---|---|---|
| Backend unit + integration | pytest | >=9.0.3 | `uv run pytest`; pytest discovery uses `test_*.py`/`*_test.py` conventions. |
| Backend API route tests | FastAPI TestClient | FastAPI >=0.136.3 | Context7-confirmed documented layer for normal `def` pytest route tests; async tests should use HTTPX async clients only when needed. |
| Frontend component/API tests | Vitest + jsdom | Vitest ^4.1.8, jsdom ^29.1.1 | `npm test` in `frontend`; `frontend/vite.config.ts` sets jsdom, globals, and setup file. |
| Frontend framework | React + Vite | React ^19.2.7, Vite ^8.0.16 | DOM/component tests are the default signal layer for current UI risks. |
| E2E/browser | none wired | n/a | Use `/10x-e2e` only if a later risk requires full browser workflow signal beyond API/component tests. |
| Provider smoke | manual controlled smoke | n/a | Real Sharpe Terminal API access stays out of CI; automated tests should use fixture-backed provider boundaries. |

**Stack grounding tools (current session):**
- Docs: Context7 -- checked FastAPI TestClient guidance, pytest discovery, and Vitest jsdom/setup guidance; checked: 2026-06-15
- Search: Exa.ai/web search MCP available -- not used because official docs via Context7 and local manifests were enough; checked: 2026-06-15
- Runtime/browser: no Playwright/browser MCP exposed by tool discovery -- not used; checked: 2026-06-15
- Provider/platform: Linear MCP available, no GitHub/Cloudflare/Supabase/database provider MCP used for this rollout; checked: 2026-06-15

## 5. Quality Gates

The full set of gates that must pass before a change reaches production. Before
a named rollout phase lands, its gate is planned rather than enforced.

| Gate | Where | Required? | Catches |
|---|---|---|---|
| Backend pytest | local + CI | required; strengthened by §3 Phase 1-3 | Dataset determinism, API contracts, workspace mismatch, relevance/quality regressions. |
| Frontend Vitest | local + CI | required; strengthened by §3 Phase 3-4 | Broken workflow rendering, warnings, copy/semantic-safety regressions. |
| Type/build checks | local + CI | required after §3 Phase 4 | Type drift and broken frontend build. |
| Provider smoke | manual pre-prod | planned after §3 Phase 2 | Sharpe Terminal token/range/provider limitation mismatch without putting live provider calls in CI. |
| E2E critical flow | optional via `/10x-e2e` | not required until a researched risk justifies it | Full browser workflow breakage that API/component tests cannot catch. |
| Semantic-safety review | local + CI | required after §3 Phase 4 | Advisory wording, broker/order/live implications. |

## 6. Cookbook Patterns

How to add new tests in this project. Each sub-section is filled in once the
relevant rollout phase ships; before that, the sub-section reads "TBD -- see
§3 Phase N."

### 6.1 Adding a determinism or JSONL stability test

- Use isolated in-memory repositories for independent reruns; shared repository
  state can accidentally prove cache reuse instead of determinism.
- When asserting byte-identical JSONL, keep the same deterministic `run_id`.
  Canonical export records include `run_id`, so different run IDs should not be
  expected to produce identical bytes unless the test explicitly normalizes that
  field outside the product contract.
- Assert real response bytes from `GET /dataset/export.jsonl` when covering API
  determinism. Object equality alone does not prove stable ordering,
  serialization, timestamp formatting, or newline behavior.

### 6.2 Adding a workspace/access-boundary API test

- Use the same `run_id` under different `workspace_id` values. This proves
  `run_id` alone is not an access boundary.
- Cover the boundary closest to the risk: repository `get_run`/`list_records`
  for storage, `GET /dataset` for preview reads, and `GET /dataset/export.jsonl`
  for export.
- For JSONL export, assert both response metadata headers and per-record
  `workspace_id` in the decoded JSONL body.
- Negative read tests should not trigger provider generation. Override the
  provider with a fail-fast fixture when needed to prove reads are storage-only.

### 6.3 Adding a provider normalization/relevance test

- TBD -- see §3 Phase 2 for provider fixture, dedupe, source identity, and relevance preservation pattern.

### 6.4 Adding a quality metrics or missing-movement test

- TBD -- see §3 Phase 3 for missing movement warnings, denominator rules, and frontend empty-state pattern.

### 6.5 Adding a semantic-safety wording test

- TBD -- see §3 Phase 4 for BACKTEST-only, non-advisory wording assertions across API/UI/export surfaces.

### 6.6 Per-rollout-phase notes

- TBD -- append short notes as rollout phases complete.

## 7. What We Deliberately Don't Test

Exclusions agreed during the rollout. Q5 did not identify any area to avoid:
the user stated that test budget is not a constraint.

- **No explicit negative-space exclusions yet** -- keep using cost x signal anyway. Re-evaluate if future tests become slow, flaky, provider-dependent, or duplicate cheaper deterministic coverage. (Source: Phase 2 interview Q5.)

## 8. Freshness Ledger

- Strategy (§1-§5) last reviewed: 2026-06-15
- Stack versions last verified: 2026-06-15
- AI-native tool references last verified: 2026-06-15

Refresh (`/10x-test-plan --refresh`) when:

- a new top-3 risk surfaces from the roadmap or archive,
- a recommended tool's `checked:` date is older than three months,
- the project's tech stack changes (new framework, new test runner),
- §7 negative-space no longer matches what the team believes.
