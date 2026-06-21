# DDD L5: Anti-Corruption Layer

Data: 2026-06-19

Repozytorium: `E:\quantitative-sentiment-analysis` (`/mnt/e/quantitative-sentiment-analysis`)

## Wybrana zaleznosc

Zewnetrzny system: Sharpe Terminal News API.

Dlaczego ten wybor: projekt ma juz port `HistoricalNewsProvider`, ale szczegoly Sharpe Terminal nadal pojawiaja sie poza adapterem. To lepszy kandydat ACL niz Binance, bo Binance/BTCUSDT zostaje prawie w calosci w `price_enrichment`, a Sharpe przecina dataset, sentiment policy, router i test fixtures.

## Wynik grep/rg

Sprawdzone komendy:

```bash
rg -n "SharpeTerminalClient|Sharpe Terminal|SHARPE_|sharpe" src/quantitative_sentiment_analysis frontend/src tests
rg -n "BinanceKlineClient|Binance Spot|BINANCE_|BTCUSDT|binance" src/quantitative_sentiment_analysis frontend/src tests
```

Produkcja dla Sharpe Terminal:

- `backtest_dataset/sharpe.py` - wlasciwy adapter API, URL, auth, paginacja, mapowanie `data.articles`.
- `backtest_dataset/router.py` - router importuje `SharpeTerminalClient` i tworzy go w dependency.
- `backtest_dataset/__init__.py` - publiczny package API re-exportuje adapter i stale Sharpe.
- `sentiment_policy/config.py` - `SentimentPolicyConfig.provider_name = "Sharpe Terminal"`.

Testy i frontend fixtures maja wiele hard-coded wystapien `Sharpe Terminal`, ale produkcyjny frontend korzysta glownie z generycznego `provider_name` z DTO. Wniosek: leak produkcyjny obejmuje 4 pliki i 3 warstwy: adapter, application/API wiring, publiczny package API oraz sentiment policy.

Produkcja dla Binance/BTCUSDT:

- `price_enrichment/binance.py`, `provider.py`, `dependencies.py`, `service.py`.

To jest glownie jedna subdomena techniczna. Do poprawy jest opis proxy w `service.py`, ale blast radius jest mniejszy niz dla Sharpe.

## Obecna granica

Co jest dobre:

- `HistoricalNewsProvider` ukrywa sposob pobierania newsow za protokolem.
- `ProviderFetchRequest` wymusza `BTCUSD`, `BACKTEST`, aware datetimes i ordered timeframe.
- `normalize_provider_records()` mapuje raw provider records do wewnetrznego `NormalizedNewsRecord`.
- Orkiestrator operuje na porcie i mapuje provider failures na `DatasetProviderLimitation`.

Co przecieka:

- Router zna konkret `SharpeTerminalClient`.
- Sentiment policy zna nazwe news providera, mimo ze scoring powinien byc niezalezny od dostawcy.
- Publiczny `backtest_dataset.__init__` wystawia adapter i stale Sharpe tak samo latwo jak typy domenowe.
- Test fixtures i UI tests utrwalaja Sharpe jako domyslny provider w wielu miejscach.

## Docelowy ACL

Granica adaptera:

```text
backtest_dataset/
  provider.py              # port i bledy domenowe
  provider_registry.py     # wybor adaptera z env/config, zwraca HistoricalNewsProvider
  adapters/
    sharpe.py              # API URL, auth, response shape, data.articles
```

Regula:

- Kod domenowy zna tylko `HistoricalNewsProvider`, `ProviderFetchRequest`, `ProviderRawRecord` i `DatasetProviderLimitationError`.
- Router importuje `get_historical_news_provider()` z registry/factory, nie `SharpeTerminalClient`.
- `sentiment_policy` nie ma pola `provider_name`; provider name pochodzi z adaptera i jest zapisywany w dataset summary.
- DTO moze nadal zwracac `provider_name` jako string display/audit, ale UI nie powinien miec logiki zaleznosci od konkretnego providera.

## Kryterium sukcesu

Po refaktorze:

```bash
rg -n "SharpeTerminalClient|SHARPE_|SHARPE_NEWS_API_URL|www.sharpe.ai|data.articles" src/quantitative_sentiment_analysis
```

powinno wskazywac tylko adapter Sharpe i ewentualnie provider registry. Dodatkowo:

```bash
rg -n "\"Sharpe Terminal\"" src/quantitative_sentiment_analysis
```

nie powinno wskazywac `sentiment_policy/config.py` ani routerow. W testach dopuszczalne sa osobne testy adaptera oraz fixture names, ale testy domenowe powinny preferowac `FixtureNews`.

## Plan zmian

1. Dodac `backtest_dataset/provider_registry.py` i przeniesc tam `get_historical_news_provider()`.
2. Przeniesc `backtest_dataset/sharpe.py` do `backtest_dataset/adapters/sharpe.py` albo zostawic plik, ale usunac bezposredni import z routera.
3. Usunac `provider_name` z `SentimentPolicyConfig` albo oznaczyc jako deprecated i przestac go uzywac.
4. Ograniczyc re-export w `backtest_dataset/__init__.py` do portow, schemas i repozytoriow; adapter importowac jawnie tylko w registry/tests.
5. Zaktualizowac testy, zeby domena i routery podstawialy `FixtureNewsProvider`, a testy Sharpe sprawdzaly tylko adapter.

## Czego nie zmieniac

- Nie zmieniac kontraktu `DatasetRunSummary.provider_name`; jest potrzebny do audytu datasetu.
- Nie zmieniac formatow JSONL.
- Nie dodawac nowego runtime SDK, jesli obecny stdlib HTTP adapter wystarcza.
- Nie mieszac ACL news providera z price enrichment. Binance/BTCUSDT to osobny, slabszy leak.
