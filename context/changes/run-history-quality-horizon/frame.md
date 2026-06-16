# Frame Brief: Run history and quality horizon

> Framing step before /10x-plan. This document captures what is *actually*
> at issue, separated from what was initially assumed.

## Reported Observation

After a user creates a draft run from a saved configuration and runs the
deterministic BACKTEST dataset, logout/login leaves no visible way to find that
historical run or reopen its quality route. Quality reports also expose a fixed
4 hour horizon even though the user expects the quality window to be explicit
and configurable.

## Initial Framing (preserved)

- **User's stated cause or approach**: Add a historical correction and
  configurable quality time.
- **User's proposed direction**: Use the 10x skills to plan a fix that lets a
  user find historical runs after re-login and choose the quality horizon
  instead of relying on a hidden 4 hour default.
- **Pre-dispatch narrowing**: Treat this as one workflow: a user must first
  discover a historical run, then open a quality report with an explicit
  horizon.

## Dimension Map

The observation could originate at any of these dimensions:

1. **Frontend navigation and state** - The result panel may be transient React
   state with no rehydration path after logout/login.
2. **Backend/API discovery contract** - Durable run and dataset state may exist,
   but the API may expose only exact-run access and no workspace history list.
3. **Quality horizon contract** - The quality route may hide a fixed default
   horizon instead of accepting and displaying an explicit request horizon.
4. **Later movement / price-enrichment boundary** - The chart may remain empty
   because completed dataset records intentionally lack `later_return` and
   `realized_direction` until price enrichment exists.

## Hypothesis Investigation

| Hypothesis | Evidence | Verdict |
| --- | --- | --- |
| Frontend navigation/state is the only gap | `BacktestConfigPage` stores the draft workflow in local `draftState`, and the quality link exists only in that transient panel; nav exposes only saved configs and new BACKTEST. However, no backend list API exists either. | WEAK |
| Backend/API discovery is missing | `BacktestRunModel`, `DatasetRunModel`, and `DatasetRecordModel` persist workspace/run data, but routers expose only `POST /drafts`, `GET /{run_id}`, run dataset, exact dataset, export, and exact quality. There is no run-history DTO, repository method, or route. | STRONG |
| Quality horizon is hidden/defaulted | `QualityHorizon` defaults to `4 hours`; `build_quality_report` can accept a horizon but `backtest_quality/router.py` passes none, and the frontend quality API has no horizon input. | STRONG |
| Later movement is missing | The completed dataset adapter maps records to quality input with `later_return=None` and `realized_direction=None`; foundation docs say this is intentional until a price-enrichment slice exists. | STRONG, but adjacent |

## Narrowing Signals

- The user specifically asked how they can inspect a chart later if they cannot
  re-enter a historical run. That rules in discovery/history as a product gap,
  not only a quality chart issue.
- The current app can open a direct quality URL if the user already knows the
  `run_id`, which means direct report rendering exists but is not discoverable.
- The user challenged why the horizon is `4h` rather than `1 minute`, which
  rules in the need for an explicit horizon contract.
- The current report still lacks movement values; a horizon selector alone will
  not create real plotted points without a later price-enrichment change.

## Cross-System Convention

Tools that create durable jobs usually provide a workspace-level job/run
history with status, source config, timestamps, and actions for rerun, details,
download, and report. Metric/report pages also make evaluation parameters
explicit, commonly through query parameters or saved report metadata. The
leading hypothesis matches this convention: durable state exists but lacks the
discovery and parameterization contract that makes it usable after the original
page state is gone.

## Reframed (or Confirmed) Problem Statement

> **The actual problem to plan around is**: durable BACKTEST run and dataset
> state exists, but the product lacks a workspace run-history discovery
> contract and treats quality horizon as a hidden fixed default instead of an
> explicit, user-selectable report parameter.

This change should plan a run-history API/UI and an explicit quality-horizon
contract. It should not pretend that a horizon selector alone makes the chart
meaningful: real plotted values still require price enrichment that populates
`later_return` and `realized_direction`.

## Confidence

- **HIGH** - Strong evidence exists in backend routers/repositories, frontend
  routing/component state, quality schemas/routes, and foundation contracts.

## What Changes for /10x-plan

- Plan a backend workspace run-history API that joins draft run metadata,
  saved config name when available, dataset summary/status when available, and
  action paths.
- Plan a frontend historical runs view reachable from the authenticated nav and
  suitable as the post-login place to recover completed work.
- Plan quality horizon as an explicit request/UI parameter, preserving `4 hours`
  as the default option while allowing shorter windows such as `1 minute` only
  when the system can represent the requested horizon honestly.
- Keep price enrichment either explicitly out of scope or as a separate phase
  with its own provider/storage contract; do not fabricate movement values.
