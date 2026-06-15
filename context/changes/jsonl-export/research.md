---
date: 2026-06-15T17:17:23+02:00
researcher: Codex
git_commit: 9da0772e574b0de7fe8f5bbbee6448a4575f1359
branch: sketch
repository: quantitative-sentiment-analysis
topic: "Jak działa eksport JSONL i które pliki odpowiadają za backend API, deterministyczną serializację oraz frontendowy download?"
tags: [research, codebase, jsonl-export, backtest-dataset, frontend-download]
status: complete
last_updated: 2026-06-15
last_updated_by: Codex
---

# Research: Jak działa eksport JSONL i które pliki odpowiadają za backend API, deterministyczną serializację oraz frontendowy download?

**Date**: 2026-06-15T17:17:23+02:00  
**Researcher**: Codex  
**Git Commit**: 9da0772e574b0de7fe8f5bbbee6448a4575f1359  
**Branch**: sketch  
**Repository**: quantitative-sentiment-analysis

## Research Question

Jak działa eksport JSONL i które pliki odpowiadają za backend API, deterministyczną serializację oraz frontendowy download?

## Summary

Eksport JSONL jest pionowym przepływem nad ukończonym S-02 datasetem BACKTEST. Backend route `GET /api/workspaces/{workspace_id}/backtests/{run_id}/dataset/export.jsonl` pobiera ukończony run z `CompletedDatasetRepository`, deleguje budowę bajtów JSONL do `backtest_dataset/export.py`, a potem zwraca download response z `application/x-ndjson`, `Content-Disposition` i metadanymi w headers.

Deterministyczność jest rozbita na dwa poziomy: shared serialization w `contracts/serialization.py` odpowiada za stabilny JSON, timestampy UTC i newline per record, a `backtest_dataset/export.py` narzuca stabilny sort po `timestamp`, `record_id`, source identity i `headline`. Frontend dodaje URL builder, fetch blob, browser download helper i przycisk widoczny tylko po stanie `completed`, bez renderowania treści JSONL w DOM.

## Detailed Findings

### Backend Export Contract

- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:18` definiuje `export_dataset_jsonl_bytes(repository, workspace_id, run_id)`. Funkcja najpierw czyta preview/summary przez `repository.get_run(...)`, a dopiero potem eksportuje pełne rekordy przez `repository.list_records(...)`.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:23` sprawdza status runu. Jeżeli summary nie ma `DatasetRunStatus.COMPLETED`, rzucany jest `DatasetExportNotReadyError`, więc provider-limited terminal state nie staje się pustym lub częściowym JSONL.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:30` pobiera pełny zestaw rekordów, nie bounded preview. To odpowiada wymaganiu S-03, że eksport jest training datasetem, a nie UI preview.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:31` składa body z `dataset_record_jsonl_line(record)` po deterministycznym sortowaniu. Wynikiem są bajty UTF-8 z newline po każdej linii.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:38` definiuje sort key: stable timestamp, `record_id`, source identity i `headline`. Source identity łączy `source_id` i `source_name`, więc rekordy z tylko jednym z tych pól nadal mają stabilny porządek.

### Deterministic Serialization

- `src/quantitative_sentiment_analysis/contracts/serialization.py:18` normalizuje Pydantic models, datetimes, enums, mappings i sekwencje do stabilnej struktury danych.
- `src/quantitative_sentiment_analysis/contracts/serialization.py:35` serializuje JSON z `allow_nan=False`, `ensure_ascii=False`, compact separators i `sort_keys=True`. To chroni key ordering i zakazuje NaN/Infinity.
- `src/quantitative_sentiment_analysis/contracts/serialization.py:45` definiuje `dataset_record_jsonl_line(record)` jako `stable_json_dumps(record) + "\n"`. To jest centralny kontrakt "one dataset record per line".
- `src/quantitative_sentiment_analysis/contracts/serialization.py:60` wymaga timezone-aware datetime i zapisuje timestamp jako UTC ISO z `Z`, co stabilizuje timestamp formatting.
- `tests/contracts/test_serialization.py:68` sprawdza byte-stable JSONL line, newline na końcu i brak newline wewnątrz record body.

### Backend API Route

- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:89` rejestruje endpoint `GET /{run_id}/dataset/export.jsonl` pod prefixem `/api/workspaces/{workspace_id}/backtests`.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:93` używa `get_completed_dataset_repository`, czyli export czyta istniejący completed dataset store i nie wstrzykuje providera ani orchestratora.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:99` pobiera preview summary do headers, a `src/quantitative_sentiment_analysis/backtest_dataset/router.py:100` pobiera body z `export_dataset_jsonl_bytes(...)`.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:101` mapuje brak completed datasetu na `404`; `src/quantitative_sentiment_analysis/backtest_dataset/router.py:103` mapuje non-exportable state na `409`.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:110` zwraca `Response` z `media_type="application/x-ndjson"`. Headers ustawiają attachment filename oraz `X-QSA-Workspace-Id`, `X-QSA-Run-Id`, `X-QSA-Config-Version` i `X-QSA-Model-Version`.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:138` sanityzuje filename do ASCII alnum plus `-`, `_`, `.`, a inne znaki zamienia na `_`.

### Backend Tests

- `tests/backtest_dataset/test_export.py:68` sprawdza stabilne UTF-8 JSONL bytes, brak metadata line, newline ending i zachowanie canonical fields.
- `tests/backtest_dataset/test_export.py:129` sprawdza, że sort eksportu jest niezależny od kolejności repository.
- `tests/backtest_dataset/test_export.py:169` sprawdza, że eksport obejmuje 105 rekordów, czyli pełne records z repository, nie bounded preview 100.
- `tests/backtest_dataset/test_export.py:188` sprawdza, że provider-limited terminal run rzuca `DatasetExportNotReadyError`.
- `tests/backtest_dataset/test_router.py:203` sprawdza sukces route, download headers, content type, pełne 105 lines i brak `provider_name` w JSONL body.
- `tests/backtest_dataset/test_router.py:240` sprawdza `404` dla missing completed dataset i dodatkowo używa providera, który rzuciłby `AssertionError`, gdyby export próbował implicit generation.
- `tests/backtest_dataset/test_router.py:261` sprawdza workspace boundary; `tests/backtest_dataset/test_router.py:277` sprawdza `409` dla provider-limited run; `tests/backtest_dataset/test_router.py:325` sprawdza CORS preflight dla GET export route.

### Frontend API and Browser Download

- `frontend/src/features/backtestShell/api.ts:62` buduje export URL jako `/dataset/export.jsonl`, z tym samym `VITE_API_BASE_URL` mechanizmem co inne shell API.
- `frontend/src/features/backtestShell/api.ts:130` definiuje `fetchBacktestDatasetExport(...)`, wysyła `Accept: application/x-ndjson`, mapuje non-OK przez istniejący `BacktestShellApiError`, a sukces zwraca jako `Blob`.
- `frontend/src/features/backtestShell/api.ts:148` definiuje `downloadBacktestDatasetExport(...)`: fetchuje blob i przekazuje go do `downloadBlob(...)` z deterministycznym filename.
- `frontend/src/features/backtestShell/api.ts:156` tworzy object URL, tymczasowy anchor, wykonuje click, usuwa anchor i odwołuje object URL. Dzięki temu JSONL nie jest renderowany w UI.
- `frontend/src/features/backtestShell/api.ts:195` buduje filename z workspace/run id i sufiksem `-dataset.jsonl`; `frontend/src/features/backtestShell/api.ts:199` zamienia znaki spoza `[A-Za-z0-9._-]` na `_`.

### Frontend UI Flow

- `frontend/src/features/backtestShell/BacktestShellPage.tsx:47` dodaje osobny `ExportState` (`idle`, `downloading`, `error`). To oddziela "generate dataset" od "download existing export".
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:52` przyjmuje `downloadDatasetExport` jako injectable prop, więc testy nie muszą wykonywać prawdziwego browser download.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:95` resetuje export state przy ponownym uruchomieniu dataset generation.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:118` obsługuje kliknięcie download: ustawia `downloading`, wywołuje helper i pokazuje error przez istniejący `errorMessage(...)`.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:358` branch provider-limited nie pokazuje download action. Przycisk jest tylko w non-provider-limited branch, czyli dla completed dataset.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:367` renderuje `Download JSONL dataset`; `frontend/src/features/backtestShell/BacktestShellPage.tsx:371` blokuje go podczas `downloading`; `frontend/src/features/backtestShell/BacktestShellPage.tsx:378` pokazuje błąd exportu jako alert.

### Frontend Tests

- `frontend/src/features/backtestShell/api.test.ts:45` i `frontend/src/features/backtestShell/api.test.ts:65` sprawdzają export URL z base URL i local `/api`.
- `frontend/src/features/backtestShell/api.test.ts:193` sprawdza fetch blob oraz `Accept: application/x-ndjson`.
- `frontend/src/features/backtestShell/api.test.ts:222` sprawdza stabilny filename, object URL, click, cleanup i brak pozostawionego anchor w DOM.
- `frontend/src/features/backtestShell/api.test.ts:312` sprawdza typed error dla non-2xx export response.
- `frontend/src/features/backtestShell/BacktestShellPage.test.tsx:145` sprawdza, że completed dataset pokazuje przycisk `Download JSONL dataset`.
- `frontend/src/features/backtestShell/BacktestShellPage.test.tsx:158` sprawdza, że download action nie istnieje przed completed dataset i wywołuje injected downloader po completion.
- `frontend/src/features/backtestShell/BacktestShellPage.test.tsx:200` sprawdza disabled/progress state podczas download.
- `frontend/src/features/backtestShell/BacktestShellPage.test.tsx:238` sprawdza error alert i brak renderowania JSONL body.
- `frontend/src/features/backtestShell/BacktestShellPage.test.tsx:323` sprawdza brak download button przy provider limitation.

## Code References

- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:18` - Główna funkcja budująca JSONL bytes z completed repository.
- `src/quantitative_sentiment_analysis/backtest_dataset/export.py:38` - Stabilny sort key eksportu.
- `src/quantitative_sentiment_analysis/contracts/serialization.py:35` - Deterministyczny JSON dump.
- `src/quantitative_sentiment_analysis/contracts/serialization.py:45` - Canonical JSONL line per `DatasetRecord`.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:89` - Backend export route.
- `src/quantitative_sentiment_analysis/backtest_dataset/router.py:110` - Download response, content type i headers.
- `frontend/src/features/backtestShell/api.ts:62` - Frontend export URL builder.
- `frontend/src/features/backtestShell/api.ts:130` - Frontend fetch blob helper.
- `frontend/src/features/backtestShell/api.ts:148` - Browser download entrypoint.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:47` - Export state model.
- `frontend/src/features/backtestShell/BacktestShellPage.tsx:367` - Completed dataset download action.

## Architecture Insights

- Export jest read-only i completed-run-only. Nie zależy od providera ani orchestratora, więc nie może przypadkowo uruchomić dataset generation.
- Deterministyczność nie jest zakodowana tylko w testach. Produkcyjna ścieżka wymusza sort i używa shared serialization helperów.
- Body JSONL pozostaje czyste: jedna linia to jeden `DatasetRecord`. Metadane run/config są albo w rekordach, albo w HTTP headers; nie ma manifest line.
- Frontend download jest izolowany w API helperze. React component zarządza tylko stanem UX i wstrzykniętym callbackiem.
- Error semantics są spójne z resztą backendu: missing completed run to `404`, provider-limited/not exportable to `409`.
- Implementacja zostawia CSV, durable export storage i implicit generation poza zakresem, zgodnie z roadmapą i quality contracts.

## Historical Context (from prior changes)

- `context/changes/jsonl-export/plan.md` - Plan S-03 zdecydował JSONL-only, GET `/dataset/export.jsonl`, HTTP download/stream, metadata in headers, `404/409`, stable sort, frontend download button, no local artifacts.
- `context/changes/jsonl-export/plan-brief.md` - Brief streszcza decyzje: JSONL jako jedyny format, completed dataset source, no CSV, no durable export storage.
- `context/foundation/quality-contracts.md:224` - S-03 ma serializować validated dataset records jako stable JSONL; po implementacji dokument wskazuje endpoint i potwierdza brak CSV/storage/implicit generation w scope.
- `context/foundation/roadmap.md:125` - S-03 handoff wskazuje aktualny endpoint i deferred CSV/durable storage.

## Related Research

No prior `research.md` artifact existed for `context/changes/jsonl-export/` before this command. Related planning artifacts:

- `context/changes/jsonl-export/plan.md`
- `context/changes/jsonl-export/plan-brief.md`
- `context/foundation/quality-contracts.md`
- `context/foundation/roadmap.md`

## Open Questions

- Durable export storage remains intentionally unsolved. A later production-storage slice should decide whether downloads stream from database/object storage rather than in-memory completed-run storage.
- CSV remains deferred. If added later, it should derive from the same canonical `DatasetRecord` set and preserve deterministic ordering.
- Very large datasets may eventually require chunked streaming. Current implementation returns bytes from in-memory records, which is sufficient for the local/dev MVP boundary described by S-02/S-03.
