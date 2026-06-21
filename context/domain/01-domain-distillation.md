# DDD L5: Domain Distillation

Data: 2026-06-19

Repozytorium: `E:\quantitative-sentiment-analysis` (`/mnt/e/quantitative-sentiment-analysis`)

Zakres: destylacja domeny na podstawie `context/foundation/*.md`, backendu w `src/quantitative_sentiment_analysis/` i typow frontendu w `frontend/src/features/*`.

## Krotki obraz domeny

Projekt buduje deterministyczne datasety sentymentu dla historycznych BACKTESTow BTCUSD. Najwazniejszy produkt domenowy to nie pojedyncza klasyfikacja, tylko audytowalny completed BACKTEST dataset: workspace/run, ramy czasu, provider newsow, rekordy JSONL, `sentiment_score`, `directional_bias`, `confidence`, `relevance`, `model_version`, `config_version` i `input_fingerprint`.

Drugi wazny strumien to quality view: completed dataset jest wzbogacany o pozniejszy ruch ceny, a raport liczy korelacje, hit rate i ostrzezenia o brakujacych candle'ach. To nadal jest BACKTEST-only i nie powinno byc modelowane jako rekomendacja wykonawcza.

## Ubiquitous language

| Pojecie | Znaczenie domenowe | Gdzie zyje w kodzie | Status |
|---|---|---|---|
| Workspace | Granica izolacji danych uzytkownika i runow. | `auth/*`, `BacktestRunShell.workspace_id`, `DatasetRecord.workspace_id`, repozytoria Postgres. | Jest w kodzie. |
| Backtest run shell | Szkielet historycznego runu: workspace, `run_id`, `BTCUSD`, `BACKTEST`, timeframe, status. | `backtest_shell/schemas.py`, `backtest_shell/repository.py`, `backtest_shell/router.py`, frontend `backtestShell/types.ts`. | Jest w kodzie. |
| Completed dataset run | Terminalny wynik datasetu: summary + rekordy + status `COMPLETED` albo `FAILED_PROVIDER_LIMITATION`. | `DatasetRunSummary`, `DatasetRunPreview`, `CompletedDatasetRepository`, `DatasetRunModel`, `DatasetRecordModel`. | W kodzie jako zestaw typow, BRAK jednej klasy agregatu. |
| Dataset record | Kanoniczny rekord JSONL: news, source identity, score, `directional_bias`, confidence, relevance, model/config. | `contracts/schemas.py:67`, `backtest_dataset/orchestrator.py:148`, `contracts/serialization.py:45`. | Jest w kodzie i DB. |
| Historical news provider | Zewnetrzne zrodlo historycznych newsow mapowane na provider raw records. | Port `HistoricalNewsProvider` w `backtest_dataset/provider.py`, adapter `SharpeTerminalClient` w `backtest_dataset/sharpe.py`. | Jest port, ale adapter przecieka do routera i policy config. |
| Normalized news record | Wewnetrzny, posortowany i odduplikowany zapis providerowego newsa przed scoringiem. | `backtest_dataset/normalization.py`. | Jest w kodzie. |
| Sentiment policy | Deterministyczna klasyfikacja tekstu na score, `directional_bias`, confidence i relevance. | `sentiment_policy/scoring.py`, `confidence.py`, `relevance.py`, `config.py`. | Jest w kodzie, rule-based. |
| Relevance | Rozroznienie `RELEVANT`, `NOISE`, `IRRELEVANT`; noise zostaje w danych, ale jest inaczej liczony. | `RelevanceLabel`, `relevance_for_text`, dataset/quality schemas. | Jest w kodzie. |
| JSONL export | Stabilny, deterministycznie sortowany eksport completed datasetu. | `backtest_dataset/export.py`, `contracts/serialization.py`, frontend download API. | Jest w kodzie. |
| Quality report | Widok jak `directional_bias` ma sie do pozniejszego ruchu ceny w wybranym horyzoncie. | `backtest_quality/schemas.py`, `metrics.py`, `repository.py`, `router.py`. | Jest w kodzie. |
| Price movement | Later return i realized direction obliczone z historycznych candle'i. | `price_enrichment/movement.py`, `price_enrichment/service.py`, `price_enrichment/schemas.py`. | Jest w kodzie. |
| Price provider proxy | Techniczny proxy BTCUSD przez Binance Spot `BTCUSDT` 1m. | `price_enrichment/provider.py`, `binance.py`, `dependencies.py`, `service.py`. | Jest w kodzie, ale to techniczny szczegol adaptera. |

## Subdomeny

| Typ | Subdomena | Uzasadnienie |
|---|---|---|
| Core domain | Deterministic BACKTEST dataset generation/export | To glowny efekt produktu: historyczne newsy -> kanoniczne rekordy -> stabilny JSONL. Tu siedza najwazniejsze invarianty. |
| Core/supporting boundary | Sentiment policy | W V1 to deterministyczny rule-based mechanizm, ale jezyk `sentiment_score`, `directional_bias`, confidence i relevance jest centralny dla datasetu. |
| Supporting | Quality evaluation | Wazne dla oceny datasetu, ale zalezy od completed datasetu i price enrichment. |
| Supporting | Price enrichment | Dostarcza candle i price movement dla quality view. Dostawca i symbol proxy sa techniczne. |
| Supporting | Workspace/auth/config | Umozliwia izolacje i zapisywanie runow, ale nie jest rdzeniem analityki sentymentu. |
| Generic/infrastructure | FastAPI, SQLAlchemy/Postgres, React/Vite, session cookies | Dostarczaja transport, persistence i UI. Nie powinny definiowac jezyka domenowego. |

## Model vs kod

1. Completed dataset run jest najwazniejszym bytem domenowym, ale kod nie ma pierwszoklasowego agregatu. Sprawnosc jest obecnie zlozona z `DatasetRunSummary`, `DatasetRecord`, `DatasetRunPreview`, helperow `_ensure_records_match_summary` i constraintow DB.
2. Lifecycle runu jest rozbity. `BacktestRunStatus` ma `DRAFT` i `READY_FOR_DATASET`, ale tworzenie draftu ustawia `DRAFT`, a orkiestrator datasetu pobiera run i startuje dataset bez jawnego przejscia przez `READY_FOR_DATASET`.
3. Policy config zawiera `provider_name = "Sharpe Terminal"`. To miesza konfiguracje scoringu z wyborem zewnetrznego news providera.
4. Provider limitation jest dobrze nazwane jako terminalny status `FAILED_PROVIDER_LIMITATION`, ale szczegoly zewnetrznego providera trafiaja az do API/frontendu jako display payload. To jest akceptowalne dla UI, lecz powinno zostac oddzielone od modelu scoringu.
5. "Dataset artifact" brzmi jak niezmienny wynik, ale `PostgresCompletedDatasetRepository.save_run()` usuwa poprzedni dataset dla tej samej pary workspace/run i zapisuje nowy. Determinizm moze to uzasadniac, ale semantyka "artifact immutability" nie jest nazwana.

## BRAK w kodzie albo slabe nazwanie

| Brak/slabosc | Dlaczego ma znaczenie |
|---|---|
| BRAK klasy `CompletedDatasetRun` | Najwazniejsza regola spojnosci summary/records nie ma jednego miejsca i nazwy domenowej. |
| BRAK jawnej polityki przejsc statusow runu | Dataset mozna uruchomic z draftu bez osobnego domain transition. |
| BRAK wartosci `ProviderCapability` / `ProviderCoverage` | Limitacje providera sa obslugiwane jako bledy, ale nie ma modelu opisujacego, co provider obiecuje w BACKTEST. |
| BRAK osobnej granicy wyboru news providera | `SharpeTerminalClient` jest konstruowany w routerze, a nazwa providera jest tez w sentiment policy. |
| BRAK domenowej nazwy dla "BTCUSD via BTCUSDT" | Price proxy jest technicznie zapisane w price enrichment; powinno zostac adapter/infrastructure detail. |

## Najwazniejsze ryzyka jezykowe

- "Run" oznacza co najmniej shell/draft, completed dataset i quality report. W planach zmian trzeba zawsze dopowiadac, o ktory run chodzi.
- "Provider" oznacza news provider i price provider. W kodzie sa osobne porty, ale nazewnictwo w raportach powinno byc bardziej precyzyjne.
- "Quality" nie oznacza jakosci danych wejsciowych ogolnie, tylko porownanie `directional_bias` z pozniejszym price movement w wybranym horyzoncie.
- "Signal" nie powinien byc jezykiem produktu. Poprawny termin w tej domenie to `directional bias`.

## Wniosek

Najbardziej oplacalne DDD usprawnienie to nazwac completed BACKTEST dataset jako agregat i przeniesc do niego reguly spojnosci summary/records. Drugim krokiem powinno byc domkniecie ACL dla Sharpe Terminal, zeby wybor zewnetrznego providera nie przeciekal do sentiment policy ani routerow.
