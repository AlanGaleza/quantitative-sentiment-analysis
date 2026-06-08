# Deploy Plan

## Cel

Pierwsze wdrozenie MVP na Render w oparciu o `context/foundation/infrastructure.md` oraz stack z `context/foundation/tech-stack.md`.

## Zasada wykonania

Ten dokument jest planem do weryfikacji. Nie wykonywac zmian aplikacyjnych, commita, pusha, tworzenia uslugi Render ani konfiguracji sekretow przed jawna akceptacja planu przez uzytkownika.

## Aktualny stan i caveat

- Platforma docelowa: Render.
- Runtime: Python 3.12 / FastAPI / uv + Uvicorn.
- Docelowy health check: `/health`.
- Poprzednia przerwana proba utworzyla lokalny commit `57bfa9d` (`chore(deploy): add Render deployment scaffold`), ale push na GitHub nie przeszedl z powodu braku interaktywnej autoryzacji HTTPS.
- Uzyc tego lokalnego commita jako startu i odtworzyc zmiany zgodnie z planem.

## Zakres po akceptacji

- Dodac importowalny FastAPI app object pod `src/quantitative_sentiment_analysis/main.py`.
- Zostawic root `main.py` jako cienki ASGI compatibility entrypoint importujacy `app`.
- Upewnic sie, ze `pyproject.toml` pakuje `src/quantitative_sentiment_analysis/`.
- Dodac Render Blueprint `render.yaml`.
- Zweryfikowac lokalnie `uv sync --locked`, start Uvicorn oraz `GET /health`.
- Dopiero po lokalnej weryfikacji przygotowac commit i push na `origin/main`.
- Utworzyc Render Web Service z repozytorium GitHub albo Render Blueprint.
- Zweryfikowac publiczny URL Render przez `/health`.

## Render Blueprint

Docelowa konfiguracja:

- service type: web
- runtime: python
- name: `quantitative-sentiment-analysis`
- region: `frankfurt`
- plan: `free`
- build command: `uv sync --locked`
- start command: `uv run uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`
- health check path: `/health`
- auto deploy trigger: commit

## Manualne bramki

- GitHub push wykonywas przez ssh
- Render połączony jest z github poprzez blueprint Name "quantitative-sentiment-analysis", blueprintId: exs-d8jf4g7lk1mc7394vo20
- Render service id: `srv-d8jf7dmrnols738dca3g`
- Render pozwala na sprawdzenie health poprzez link https://quantitative-sentiment-analysis.onrender.com/health
- `RENDER_API_KEY.txt` istnieje lokalnie i jest ignorowany przez git. Nie commitowac tego pliku ani nie wklejac wartosci tokena do rozmowy.
- `RENDER_API_KEY` jest sekretem operatorskim dla lokalnego agenta/CLI/API Render. Nie ustawiac go jako Environment Variable aplikacji Render, chyba ze sama aplikacja musi wywolywac Render API w runtime.
- Sekrety produkcyjne, upgrade planu, persistent disk, baza danych i operacje destrukcyjne wymagaja recznej zgody uzytkownika.

## Dostep agenta do Render API

Klucz operatorski jest przechowywany lokalnie w ignorowanym pliku `RENDER_API_KEY.txt`. Agent moze go zaladowac tylko do zmiennej procesu:

`export RENDER_API_KEY="$(tr -d '\r\n' < RENDER_API_KEY.txt)"`

Do read-only sprawdzenia dostepu uzyc:

`curl -fsS -H "Accept: application/json" -H "Authorization: Bearer $RENDER_API_KEY" "https://api.render.com/v1/services?limit=20"`

Zasady:

- Nie wypisywac wartosci `RENDER_API_KEY`.
- Nie commitowac `RENDER_API_KEY.txt`.
- Nie dodawac `RENDER_API_KEY` do Render Environment Variables aplikacji.
- Domyslnie wykonywac tylko operacje read-only: status uslugi, lista deployow, logi.
- Operacje mutujace Render, sekrety, billing, plan, baza danych i rollback wymagaja jawnej zgody uzytkownika.

## Weryfikacja lokalna po zmianach

1. `uv lock --check`
2. `uv sync --locked`
3. `uv run uvicorn quantitative_sentiment_analysis.main:app --host 127.0.0.1 --port 8000`
4. `curl -fsS http://127.0.0.1:8000/health`
5. Parse `render.yaml` i sprawdzic pola `runtime`, `plan`, `region`, `startCommand`, `healthCheckPath`.

Na WSL/DrvFS, jezeli `.venv` na `/mnt/e` blokuje kopiowanie plikow, uzyc tymczasowego Linux venv:

`UV_PROJECT_ENVIRONMENT=/tmp/qsa-render-venv UV_LINK_MODE=copy uv sync --locked`

## Weryfikacja po deployu

1. Sprawdzic status deployu w Render.
2. Odczytac build/runtime logs tylko read-only.
3. Wejsc na `https://<render-service>.onrender.com/health`.
4. Oczekiwany wynik: status HTTP 200 i JSON zawierajacy `status: ok`.
5. Zapisac finalny URL i wynik w tym pliku lub w osobnym raporcie deploymentu.

## Rollback

- Jezeli deploy nie przejdzie: nie dodawac sekretow ani kolejnych zmian; najpierw odczytac build logs.
- Jezeli aplikacja startuje, ale `/health` nie odpowiada: sprawdzic `startCommand`, import path i `$PORT`.
- Jezeli zly commit zostal wypchniety: zatrzymac auto-deploy albo revertowac commit przed uzyciem rollbacku Render.

## Kryteria akceptacji pierwszego wdrozenia

- Render service istnieje i jest polaczony z repozytorium.
- Build konczy sie sukcesem.
- Runtime startuje bez import error.
- `/health` odpowiada HTTP 200.
- Brak live tradingu, broker integration, order execution i investment-recommendation wording.
- Plan i wynik wdrozenia sa zapisane w repo.
