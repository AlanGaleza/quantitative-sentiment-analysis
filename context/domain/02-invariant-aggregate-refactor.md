# DDD L5: Invariant And Aggregate Refactor

Data: 2026-06-19

Repozytorium: `E:\quantitative-sentiment-analysis` (`/mnt/e/quantitative-sentiment-analysis`)

## Regula #1

Completed BACKTEST dataset moze zostac zapisany, eksportowany albo uzyty do quality report tylko wtedy, gdy `DatasetRunSummary` i wszystkie `DatasetRecord` tworza jeden spojny run:

- ten sam `workspace_id` i `run_id`;
- `instrument == BTCUSD` i `mode == BACKTEST`;
- ten sam `model_version` i `config_version`;
- `record_count` rowna sie liczbie rekordow;
- liczniki relevance w summary dokladnie odpowiadaja rekordom;
- status `FAILED_PROVIDER_LIMITATION` nie zapisuje zadnych rekordow;
- status `COMPLETED` nie ma provider limitation.

## Dlaczego to jest najwazniejszy invariant

| Os | Ocena | Uzasadnienie |
|---|---|---|
| Rdzeniowosc | Wysoka | Glownym produktem jest deterministyczny JSONL dataset. Jesli summary i records sie rozjada, eksport i quality report traca sens. |
| Rozsmarowanie | Srednio-wysokie | Regula zyje w Pydantic schemas, orchestratorze, repozytoriach, DB constraints, eksporcie i quality adapterze. |
| Egzekwowanie | Srednie | Jest sporo guardow, ale nie ma jednego agregatu z nazwa i publicznym API. Repozytorium broni zapisu, ale inne warstwy operuja osobnymi DTO. |

## Obecne miejsca egzekwowania

- `DatasetRunSummary.must_be_btcusd_backtest_with_consistent_counts()` pilnuje `BTCUSD`, `BACKTEST`, ordered timeframe, count sum i provider limitation shape.
- `DatasetRunPreview.records_must_match_summary()` pilnuje, zeby preview bylo spojne z summary, ale dopuszcza tylko subset rekordow.
- `CompletedDatasetRepository.save_run()` w obu implementacjach wywoluje `_ensure_terminal_state()` i `_ensure_records_match_summary()`.
- `PostgresCompletedDatasetRepository.save_run()` wymaga istniejacego `BacktestRunModel` dla workspace/run i usuwa poprzedni dataset przed zapisem nowego.
- `DatasetRunModel` i `DatasetRecordModel` maja constrainty dla `BTCUSD`, `BACKTEST`, relevance, score/confidence bounds i source identity.
- `export_dataset_jsonl_bytes()` sprawdza `COMPLETED`, ale potem ufa repozytorium i sortuje rekordy do stabilnego JSONL.
- `CompletedDatasetQualityInputProvider` wymaga completed statusu i niepustych rekordow przed price enrichment.

## Proponowany agregat

Nazwa: `CompletedDatasetRun`

Granica: `backtest_dataset/domain.py`

Root: summary terminalnego datasetu.

Owned data: pelna kolekcja `DatasetRecord`.

Publiczne operacje:

```python
@dataclass(frozen=True)
class CompletedDatasetRun:
    summary: DatasetRunSummary
    records: tuple[DatasetRecord, ...]

    @classmethod
    def complete(cls, summary: DatasetRunSummary, records: Iterable[DatasetRecord]) -> Self:
        ...

    @classmethod
    def provider_limited(cls, summary: DatasetRunSummary) -> Self:
        ...

    def preview(self) -> DatasetRunPreview:
        ...

    def export_records(self) -> tuple[DatasetRecord, ...]:
        ...
```

Agregat powinien przejac logike z `_ensure_terminal_state()` i `_ensure_records_match_summary()`. Repozytoria powinny zapisywac juz zwalidowany agregat albo tworzyc go na granicy `save_run()`. Wtedy invariant ma jedna nazwe i jedno miejsce rozbudowy.

## Minimalna refaktoryzacja

1. Dodac `CompletedDatasetRun` w `backtest_dataset/domain.py` i przeniesc do niego walidacje terminal state + records/summary consistency bez zmiany zachowania.
2. Zmienic `InMemoryCompletedDatasetRepository.save_run()` i `PostgresCompletedDatasetRepository.save_run()`, zeby budowaly agregat na wejsciu i korzystaly z `aggregate.preview()`.
3. Zmienic `export_dataset_jsonl_bytes()` tak, aby eksportowal rekordy przez metode agregatu albo przez repozytorium zwracajace agregat dla completed runu.
4. Dodac testy regresyjne dla mismatchy: workspace/run, model/config, counts, provider-limited with records, completed with provider limitation.
5. Pozostawic kompatybilne DTO API (`DatasetRunSummary`, `DatasetRunPreview`, `DatasetRecord`), zeby frontend i JSONL nie zmienily kontraktu.

## Czego nie robic w tym kroku

- Nie wprowadzac live mode, brokerow ani order execution.
- Nie przepisywac repozytoriow na event sourcing.
- Nie zmieniac JSONL schema ani nazw `directional_bias`, `LONG`, `SHORT`, `FLAT`.
- Nie laczyc quality report z agregatem datasetu. Quality report jest kolejnym widokiem na completed dataset, nie czescia jego zapisu.
- Nie przenosic SQLAlchemy modeli do domeny. Modele persistence powinny zostac mapperami.

## Kryteria sukcesu

- `CompletedDatasetRun` jest jedynym miejscem, gdzie opisano regule spojnosci summary/records.
- Helper `_ensure_records_match_summary()` znika albo staje sie prywatnym delegatem agregatu.
- Repozytoria nie powielaja tej samej walidacji.
- Testy dla obecnych przypadkow mismatch nadal przechodza.
- Eksport JSONL dla tego samego wejscia pozostaje byte-for-byte stabilny.

## Ryzyko i uwaga implementacyjna

Najwieksze ryzyko to zbyt szeroki refactor. Ten agregat powinien najpierw byc cienka warstwa nad istniejacym zachowaniem. Dopiero po ustabilizowaniu mozna rozwazyc silniejszy lifecycle model dla `BacktestRunShell -> CompletedDatasetRun -> QualityReport`.
