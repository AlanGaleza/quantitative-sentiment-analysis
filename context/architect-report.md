# Raport architektoniczny modulu 4 - 10xArchitect

Data: 2026-06-19

## 1. Opisane projekty

| Repo | Artefakty | Stack i skala | Uwagi o pochodzeniu |
|---|---|---|---|
| `E:\usun_po_kursie\react` (`/mnt/e/usun_po_kursie/react`) | L2, L3, L4 | Monorepo Reacta: runtime core, DOM renderer, server rendering, RSC/Flight, DevTools, React Compiler. Mapa L2 i artefakty L3/L4 opisuja HEAD `b1786c319e5647678d7fb9922743f56078062b73`. | Artefakty sa w `E:\usun_po_kursie\react\context\`. |
| `E:\quantitative-sentiment-analysis` (`/mnt/e/quantitative-sentiment-analysis`) | L5 | Greenfield Python 3.12 FastAPI/uv + SQLAlchemy/Postgres + React/Vite/TypeScript dla deterministycznych BTCUSD BACKTEST sentiment datasets. | Artefakty DDD sa w `context/domain/*.md`. |

## 2. Mapa projektu z L2

L2 (`E:\usun_po_kursie\react\context\map\repo-map.md`) pokazuje, ze najgoretszym obszarem React repo w badanym oknie jest React Compiler, szczegolnie HIR, Validation, Entrypoint/Pipeline i fixtures. Drugie centrum ryzyka to `packages/react-devtools-shared`, gdzie backend renderer, store i UI historycznie zmieniaja sie razem. Runtime core pozostaje ryzykowny przez `react-reconciler`, `react-dom-bindings`, Flight/Fizz i feature flags.

Mapa rozroznia plytkie entry pointy (`index.js`, `flight.js`, `server.js`) od glebokiej logiki, np. `ReactFizzServer.js`, `ReactFlightServer.js`, `ReactFiberWorkLoop.js`, `ReactFiberConfigDOM.js`, `backend/fiber/renderer.js` i `Entrypoint/Pipeline.ts`. Najwazniejszy unknown z L2: dependency-cruiser byl uruchamiany bez pelnej konfiguracji resolverow aliasow, wiec `couldNotResolve` jest ograniczeniem narzedzia, nie dowodem braku zaleznosci.

Przy pierwszym czytaniu L2 sugeruje zaczac od Compiler pipeline/HIR, DevTools renderer/store, WorkLoop, DOM host config, Flight client/server, Fizz i `ReactFeatureFlags`. To mapa ryzyka i wspolzmian, nie instrukcja bezpiecznej refaktoryzacji.

## 3. Analiza ficzera z L3

L3 (`E:\usun_po_kursie\react\context\changes\post-flow-analysis\research.md`) badal proces zapisu postow/wiadomosci. Najwazniejszy wniosek: w React repo nie ma domenowego CRUD dla posts/messages, DB ani migracji. Najblizszy realny przeplyw to `fixtures/flight-esm`: klient wysyla `POST /` z server action, serwer dekoduje action i argumenty, mutuje in-memory `ServerState`, renderuje nowy RSC payload, Flight serializuje model do chunkow, a klient przetwarza stream i aktualizuje root.

Drugim powiazanym obszarem jest DevTools messaging: `window.postMessage`, extension ports, `Bridge`, `Agent` i `Store`. L3 podkresla, ze sa trzy znaczenia slowa "message": snackbar w Compiler Playground, protokol/event w DevTools i row/chunk payload w Flight. Mieszanie ich w jednym planie byloby blednym zalozeniem.

Najwazniejsze ryzyka z L3: brak domenowego modulu postow oznacza, ze planowanie CRUD w tym repo byloby zlym zakresem; DevTools ma stringly typed granice przez event names i `postMessage`; Flight/Fizz maja skomplikowane kontrakty atomowosci chunkow, backpressure i resume state. Statyczna weryfikacja kierunku refaktoru jest w L4: `ast-grep` byl dostepny, ale blokowal sie w workspace, wiec twierdzenia o listach content scripts potwierdzono fallbackiem `rg` i recznym odczytem linii.

## 4. Plan refaktoryzacji z L4

L4 (`E:\usun_po_kursie\react\context\changes\refactor-opportunities\plan.md`) wybiera najprostsza okazje: test-only guard dla DevTools extension content-script wiring. Refaktoryzowany problem to recznie utrzymywana spojnosc miedzy webpack entries, dynamiczna rejestracja Chrome MV3 i manifestami Chrome/Edge/Firefox.

Docelowy ksztalt fazy 1: jeden test `packages/react-devtools-extensions/src/__tests__/contentScriptRegistry.test.js`, ktory potwierdza, ze dynamiczne content scripts maja matching webpack entry, trzy manifesty zgadzaja sie co do statycznego `prepareInjection`, a wyjatki sa jawne: `backendManager` jest on-demand, `prepareInjection` jest bootstrapem.

Swiadomie nie robimy zmian runtime, nie ruszamy DevTools message envelopes, `Bridge`, `Store`, `BRIDGE_PROTOCOL`, Flight/Fizz/Scheduler, generatorow manifestow ani browser E2E. Weryfikacja automatyczna: targeted Jest wrapper oraz CI-equivalent `yarn test --project devtools --build ...`, gdy istnieje `build/`. Weryfikacja manualna: porownanie oczekiwanych nazw scriptow z webpack config, dynamic registry i trzema manifestami oraz potwierdzenie, ze nie zmieniono plikow produkcyjnych.

## 5. Domena wg DDD z L5

L5 (`E:\quantitative-sentiment-analysis\context\domain\*.md`) dotyczy innego repo niz L2/L3. Ubiquitous language QSA koncentruje sie na `workspace`, `backtest run shell`, `completed dataset run`, `DatasetRecord`, `HistoricalNewsProvider`, `sentiment_score`, `directional_bias`, `confidence`, `relevance`, JSONL export, quality report i price movement.

Najwazniejszy rozjazd model-vs-kod: completed BACKTEST dataset jest rdzeniem domeny, ale nie ma jednej klasy agregatu. Kod sklada go z `DatasetRunSummary`, `DatasetRecord`, `DatasetRunPreview`, repozytoriow, walidatorow i constraintow DB. Drugi rozjazd to lifecycle: shell ma `DRAFT` i `READY_FOR_DATASET`, lecz dataset orchestration nie ma jawnego przejscia przez `READY_FOR_DATASET`.

Niezmiennik #1: summary i rekordy completed datasetu musza tworzyc jeden spojny run: ten sam workspace/run, `BTCUSD`, `BACKTEST`, model/config version, zgodne liczniki relevance, zgodny `record_count`, provider-limited bez rekordow, completed bez provider limitation. Proponowany agregat to `CompletedDatasetRun`, ktory powinien przejac walidacje z helperow repozytorium i stac sie jedna nazwana granica dla zapisu, eksportu i quality input.

ACL #1: Sharpe Terminal News API. `rg` pokazal produkcyjne wystapienia w adapterze `backtest_dataset/sharpe.py`, routerze, publicznym `backtest_dataset.__init__` oraz `sentiment_policy/config.py`. To 4 pliki i 3 warstwy. Docelowo router powinien znac tylko provider factory/registry, `sentiment_policy` nie powinno znac nazwy Sharpe, a szczegoly `SHARPE_API_KEY`, URL i response `data.articles` powinny zostac w adapterze.

## 6. Decyzje, ktore naleza do mnie

W tej pracy swiadomie rozdzielilem dwa watki: React posluzyl mi do mapy, researchu i planu refaktoryzacji, a QSA do cwiczenia DDD. Nie probowalem na sile laczyc DevTools albo Flight z domena BTCUSD, bo wtedy raport wygladalby spojniej, ale bylby mniej uczciwy wobec materialu.

W L4 wybralem najmniejszy sensowny krok: guard dla list content scripts, zamiast od razu ruszac `Bridge`, Flight albo Fizz. To byla moja decyzja po przeczytaniu researchu: najpierw zabezpieczyc miejsce, ktore moze dryfowac, a dopiero potem myslec o wiekszym refaktorze.

W QSA za najwazniejszy invariant uznalem spojny completed dataset, a nie quality report. Quality jest wazne, ale opiera sie na danych z datasetu; jesli tam pojawi sie rozjazd summary i rekordow, eksport JSONL oraz raport jakosci tylko przeniosa ten blad dalej. Event stormingu nie uruchamialem, bo byl opcjonalny i w tym zadaniu zostal wykluczony.
