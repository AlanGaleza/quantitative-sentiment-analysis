---
project: quantitative-sentiment-analysis
researched_at: 2026-06-11T21:34:28+02:00
recommended_platform: Render
runner_up: Railway
context_type: mvp
tech_stack:
  language: Python 3.12
  framework: FastAPI
  runtime: uv + Uvicorn
  frontend: Vite static site
---

## Rekomendacja

**Deploy na Render.**

Render jest najlepszą decyzją dla tego MVP, bo obecne repo jest już ustawione pod Render: `render.yaml` definiuje backend FastAPI jako Python Web Service, frontend jako Static Site, region `frankfurt`, `uv sync --locked --no-dev` jako build command i `uv run --no-dev uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT` jako start command. Odpowiedzi z wywiadu wzmacniają tę decyzję: aplikacja jest stateless request/response, miesięczny koszt jest priorytetem, jeden region wystarczy, współlokacja usług jest preferowana, a konto i aplikacja na Render już istnieją.

Railway jest najlepszym runner-upem, jeśli ważniejszy stanie się DX i agent-friendly operability niż najtańszy start. Fly.io zostaje trzecią opcją dla bardziej kontenerowego modelu uruchomienia, ale ma większy narzut operacyjny i słabszy fit do aktualnego stanu projektu.

## Porównanie Platform

Źródła sprawdzone 2026-06-11: oficjalne docs Render dla FastAPI, `uv`, CLI, pricing, logs, rollback, MCP/LLM support; Railway FastAPI/Railpack/CLI/pricing/MCP; Fly.io FastAPI/flyctl/pricing/MCP; Cloudflare Python Workers/FastAPI/pricing/wrangler; Vercel Python Runtime/FastAPI/pricing/MCP; Netlify Functions/CLI/pricing/MCP.

| Platform | CLI-first | Managed/serverless | Docs dla agenta | Stabilny deploy API | MCP / integracja | Wynik | Decyzja |
|---|---|---|---|---|---|---|---|
| Render | Partial | Pass | Pass | Pass | Partial | 3 Pass / 2 Partial | Rekomendowany: najlepszy fit dla obecnego FastAPI/uv/Uvicorn repo i istniejącej aplikacji. |
| Railway | Pass | Pass | Pass | Partial | Pass | 4 Pass / 1 Partial | Runner-up: świetny DX i agent workflow, ale kosztowo przegrywa z istniejącym Render Free startem. |
| Fly.io | Pass | Partial | Pass | Pass | Pass | 4 Pass / 1 Partial | Trzecia opcja: mocny runtime kontenerowy, ale większy narzut i brak trwałego darmowego startu. |
| Cloudflare Workers + Pages | Pass | Pass | Pass | Pass | Pass | 5 Pass | Odrzucone dla tego repo: Python Workers/FastAPI to edge/ASGI model, nie natywny CPython + Uvicorn Web Service. |
| Vercel | Pass | Pass | Pass | Pass | Partial | 4 Pass / 1 Partial | Odrzucone dla tego repo: Python Functions są serverless, a nie uruchomieniem obecnego procesu Uvicorn 1:1. |
| Netlify | Pass | Pass | Pass | Pass | Pass | 5 Pass | Odrzucone twardo: Netlify Functions nie są naturalnym targetem dla Python FastAPI/Uvicorn backendu. |

Render: oficjalny workflow dla FastAPI wymaga wystawienia aplikacji przez Uvicorn na `0.0.0.0` i `$PORT`, co pasuje do obecnego `render.yaml`. Render wykrywa `uv.lock`, wspiera Python Web Services, env vars, logi przez CLI, deploye przez CLI/API oraz rollback przez dashboard/API. Słabości: rollback nie jest pełnym CLI-only flow, Free Web Service zasypia po bezczynności, a MCP/LLM support jest przydatny do pracy agenta, ale nie zastępuje pełnego operacyjnego API.

Railway: bardzo dobry agent-friendly workflow, Railpack wspiera Python i `uv.lock`, CLI obsługuje deploye/logi/status, a platforma ma projekty z prywatną siecią i bazami jako templates. Przegrywa tutaj, bo użytkownik ma już Render, koszt jest priorytetem, a Railway Hobby zaczyna się od płatnego minimum.

Fly.io: dobry wybór dla FastAPI, gdy projekt chce świadomie przejść w model kontenerowy lub potrzebuje większej kontroli nad runtime. Dla tego MVP oznaczałby jednak więcej decyzji infrastrukturalnych, więcej surface area dla deployu i brak przewagi przy jednym regionie oraz stateless API.

Cloudflare Workers + Pages: bardzo tanie i bardzo agent-readable, ale Python Workers są innym modelem wykonania. FastAPI może działać przez ASGI na Workers, ale nie jest to zwykły Uvicorn process. To byłby redesign deploymentu, nie naturalny deploy obecnej aplikacji.

Vercel: Python Runtime/FastAPI działa w modelu Functions i ma dobry CLI/MCP/docs story. Dla tego backendu ryzyko leży w serverless modelu, limitach runtime i braku zgodności z obecnym `uvicorn quantitative_sentiment_analysis.main:app` jako długotrwałym web processem.

Netlify: operacyjnie mocne CLI, MCP, previews i rollbacki, ale target funkcji nie pasuje do Python FastAPI/Uvicorn backendu. Netlify może hostować frontend albo proxy do backendu, ale nie powinno być platformą backendu w tym MVP.

### Shortlista

#### 1. Render (rekomendowane)

Render wygrywa, bo daje najkrótszą ścieżkę od obecnego repo do działającej aplikacji: backend jako Python Web Service, frontend jako Static Site, Git-backed deploye, env vars, health check i darmowy start. Istniejące konto i aplikacja są tutaj realnym argumentem, nie detalem.

#### 2. Railway

Railway jest najlepszą alternatywą, jeśli Render Free zacznie przeszkadzać albo jeśli priorytetem stanie się szybszy DX, prostsze projekty z usługami współlokowanymi i mocniejsze agent workflow. Kosztowo jest mniej atrakcyjny przy obecnym wymaganiu "minimalizować koszt".

#### 3. Fly.io

Fly.io jest sensowne, jeśli projekt potrzebuje kontenerów, pełniejszej kontroli nad procesem albo później persistent processes/WebSockets. Dla obecnego V1 BACKTEST-only API to byłby większy narzut niż wartość.

## Anti-Bias Cross-Check: Render

### Devil's Advocate - słabości

1. Render Free Web Service zasypia po bezczynności, więc pierwszy request i smoke test mogą mierzyć wake-up time, a nie zachowanie aplikacji.
2. PRD wymaga, aby 30 dni historycznych newsów dało się przetworzyć w <= 5 minut na standardowej maszynie deweloperskiej; Render Free nie jest wiarygodnym proxy dla tej wydajności.
3. Eksporty JSONL/CSV nie mogą polegać na lokalnym filesystemie instancji, bo lokalny stan nie jest trwałym magazynem danych dla reproducible datasetów.
4. Rollback deployu nie cofa danych, zewnętrznego storage, przyszłych migracji ani wygenerowanych eksportów.
5. Render API key, lokalny `RENDER_API_KEY.txt` i potencjalny MCP dostęp mogą mieć zbyt szerokie uprawnienia, więc agent nie powinien mieć swobody wykonywania destrukcyjnych operacji.

### Pre-Mortem - jak ta decyzja może się nie udać

Zespół deployuje MVP na Render Free i uznaje, że temat infrastruktury jest zamknięty. Endpoint BACKTEST powstaje jako synchroniczny request HTTP, testowany głównie lokalnie. W preview serwis najpierw budzi się po idle, potem przetwarza większy zakres newsów na słabej darmowej instancji, a użytkownik widzi niestabilne czasy odpowiedzi. Eksport JSONL trafia tymczasowo na lokalny dysk, po czym znika po redeployu albo restarcie. Późniejszy upgrade planu poprawia część objawów, ale projekt ma już sklejone w jednym miejscu request handling, długie przetwarzanie i storage eksportów. Render zostaje obwiniony za problem, którego prawdziwą przyczyną było potraktowanie darmowego web hostingu jak job runnera, benchmark environment i trwałego storage jednocześnie.

### Unknown Unknowns

- Render Free nadaje się do preview i wczesnej walidacji ścieżki deployu, ale nie do potwierdzenia runtime NFR dla BACKTEST.
- Jeśli pojawi się Render Postgres Free, nie wolno opierać na nim długoterminowej reprodukowalności workspace/run metadata bez świadomego planu upgrade.
- `uv.lock` musi zostać w repo root; jeśli build context albo root service zostanie zmieniony, automatyczna ścieżka `uv` może przestać być przewidywalna.
- Frontend Static Site i backend Web Service mają oddzielne env vars; `VITE_API_BASE_URL` i backendowe sekrety muszą być ustawiane osobno.
- MCP/LLM support Render jest pomocny do inspekcji, ale nie powinien zastępować ograniczonego, audytowalnego runbooka CLI/API dla deployów i logów.

## Operational Story

- **Preview deploys**: używaj Git-backed Render Blueprint z obecnym `render.yaml`. Backend `quantitative-sentiment-analysis` i frontend `quantitative-sentiment-analysis-frontend` deployują się z commitów; preview/staging nie może dostać produkcyjnych sekretów ani prawdziwych workspace datasetów.
- **Secrets**: backendowe wartości, np. `QSA_CORS_ALLOWED_ORIGINS`, przyszły klucz news API, auth secrets i storage credentials, trzymać w Render environment variables. `RENDER_API_KEY.txt` zostaje lokalnym sekretem operatora, ignorowanym przez git; nie ustawiać go jako env var aplikacji, chyba że aplikacja naprawdę musi wołać Render API w runtime.
- **Rollback**: użyj Render Events/dashboard albo Render API rollback. Przez CLI najpierw sprawdź historię `render deploys list <service_id> --output json`; jeśli zły commit nadal jest na gałęzi z auto-deploy, najpierw zatrzymaj auto-deploy albo zrób revert.
- **Approval**: człowiek zatwierdza publish na produkcję, upgrade planu, rotację głównego sekretu, usunięcie bazy/storage, zmianę regionu i każdą operację mogącą ujawnić workspace data. Agent może czytać logi, uruchamiać lokalne testy i przygotowywać komendy deployu do zatwierdzenia.
- **Logs**: runtime logs czytać przez `render logs --resources <service_id> --tail --output json`. Build/deploy stan sprawdzać przez `render deploys list <service_id> --output json` i szczegóły deployu w Render Events.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Cold start na Free fałszuje smoke testy i UX | Research finding / Devil's advocate | High | Medium | Traktować Free jako preview; po deployu rozgrzać `/health` przed testem albo przejść na paid plan przed pomiarem latency. |
| BACKTEST przekracza 5 minut na Render Free | Pre-mortem | Medium | High | Benchmarkować lokalnie i na docelowym planie; nie uznawać Free za runtime NFR; w razie potrzeby wydzielić przetwarzanie poza zwykły request. |
| Eksporty giną z lokalnego filesystemu | Devil's advocate / Research finding | Medium | High | Streamować JSONL/CSV jako odpowiedź albo zapisywać do trwałego external storage; nie używać lokalnego dysku jako źródła prawdy. |
| Rollback aplikacji nie cofa danych i migracji | Devil's advocate | Medium | High | Wprowadzić zasadę: każda zmiana schematu/storage ma osobny rollback note; deploy rollback nie oznacza data rollback. |
| Zbyt szeroki Render API/MCP dostęp | Unknown unknowns | Medium | High | Trzymać token poza repo i poza chatem; używać najmniejszych możliwych uprawnień; operacje destrukcyjne tylko ręcznie. |
| Frontend i backend mają rozjechane env vars | Unknown unknowns | Medium | Medium | Po każdym deployu sprawdzić backend `/health` i frontend `VITE_API_BASE_URL`; trzymać env var checklistę w deploy planie. |
| Pokusa migracji na edge/serverless powoduje runtime mismatch | Devil's advocate | Medium | Medium | Trzymać backend V1 na normalnym Python Web Service, dopóki nie ma świadomego planu redesignu pod Workers/Vercel/Netlify. |
| Railway/Fly stają się atrakcyjne dopiero po problemach z Render Free | Research finding | Low | Medium | Zapisać Railway jako runner-up i Fly.io jako trzecią opcję; decyzję zmieniać dopiero po konkretnym blockerze, nie prewencyjnie. |

## Getting Started

1. Utrzymaj backend importowalny jako `quantitative_sentiment_analysis.main:app`; to jest import path używany w `render.yaml`.
2. Utrzymaj w repo root pliki `pyproject.toml`, `uv.lock` i `render.yaml`; backendowy build command zostaje `uv sync --locked --no-dev`.
3. Utrzymaj backendowy start command: `uv run --no-dev uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`.
4. Ustaw w Render env vars backendu `QSA_CORS_ALLOWED_ORIGINS`, a we frontend Static Site `VITE_API_BASE_URL`; nie mieszaj sekretów backendu z publicznymi zmiennymi Vite.
5. Po deployu zweryfikuj backend przez `/health`, a dopiero potem dodawaj endpointy BACKTEST/export i sekrety do news ingestion.

## Out of Scope

Nie oceniano w tej decyzji:

- budowy obrazów Docker ani Dockerfile,
- pełnej konfiguracji CI/CD,
- produkcyjnej architektury multi-region, HA i DR,
- broker integration, order execution, live streaming ani inwestycyjnych rekomendacji.
