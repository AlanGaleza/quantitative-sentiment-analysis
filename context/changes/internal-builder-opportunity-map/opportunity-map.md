# Internal Builder Opportunity Map

Artifact for the practical tasks from `ai-internal-builders-wewnetrzne-narzedzia-serwisy-i-automatyzacje.md`.

Project context: Quantitative Sentiment Analysis, a Python/FastAPI service for deterministic BTCUSD BACKTEST sentiment datasets.

## Krok 1: sygnaly tarcia

1. Przed review trudno szybko sprawdzic, czy zmiana nie narusza zasad `BACKTEST-only`, `directional bias`, `LONG` / `SHORT` / `FLAT` i zakazu sugerowania wykonawczych decyzji rynkowych.
2. Kontrakty deterministycznego JSONL, workspace isolation, run metadata i source identity sa rozproszone miedzy `quality-contracts.md`, Pydantic schemas, route tests, export code i dokumentacja.
3. Przy zmianach w backendzie lub frontendzie recenzent musi recznie zgadywac, ktore testy sa najbardziej istotne dla dotknietych kontraktow.
4. Foldery `context/changes/*` zawieraja plany, research, review i verification w roznych stanach, wiec trudno szybko zobaczyc, ktore watki sa gotowe, a ktore wymagaja follow-upu.
5. Typy i kontrakty miedzy API backendu a frontendem moga sie rozjechac, bo Pydantic schemas, TypeScript types i testy API sa utrzymywane w kilku miejscach.

## Krok 2: mapa okazji

| Sygnał tarcia                                                                                                                                                                          | SaaS / domyślna odpowiedź                                                                                                                              | Cienki helper                                                                                                                                            | Pierwsza użyteczna wersja                                                                                |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Przed review trudno szybko sprawdzic, czy zmiana nie narusza zasad `BACKTEST-only`, `directional bias`, `LONG` / `SHORT` / `FLAT` i zakazu sugerowania wykonawczych decyzji rynkowych. | `rg`, review PR, istniejace testy safety, AGENTS.md i `context/foundation/quality-contracts.md`. To dziala, ale wymaga pamieci recenzenta.             | Digest semantycznego ryzyka, ktory czyta diff i wskazuje podejrzane slowa, dotkniete powierzchnie UI/API/docs oraz testy do uruchomienia.                | Statyczny Markdown generowany recznie z kilku komend `rg` i listy zmienionych plikow.                    |
| Kontrakty deterministycznego JSONL, workspace isolation, run metadata i source identity sa rozproszone miedzy dokumentami, schematami, route tests, export code i dokumentacja.        | Testy kontraktowe, `quality-contracts.md`, PR review i lokalne uruchamianie pytest. Sa dobre, ale nie pokazuja recenzentowi mapy ryzyka przed testami. | Contract impact digest, ktory mapuje zmienione pliki na kontrakty: JSONL stability, workspace isolation, run metadata, dataset record i semantic safety. | Raport Markdown z sekcjami: dotkniete kontrakty, pliki do review, sugerowane testy, brakujace dowody.    |
| Przy zmianach w backendzie lub frontendzie recenzent musi recznie zgadywac, ktore testy sa najbardziej istotne dla dotknietych kontraktow.                                             | Pelne `pytest`, testy frontendowe, ewentualnie CI. Pelny zestaw jest najbezpieczniejszy, ale wolniejszy i mniej informacyjny dla malej zmiany.         | Test selection helper, ktory na podstawie zmienionych sciezek sugeruje minimalny zestaw testow oraz pelny zestaw dla wysokiego ryzyka.                   | Lokalna tabela sciezka -> testy, utrzymywana w Markdown albo prostym skrypcie tylko do odczytu.          |
| Foldery `context/changes/*` zawieraja plany, research, review i verification w roznych stanach, wiec trudno szybko zobaczyc, ktore watki sa gotowe, a ktore wymagaja follow-upu.       | Reczne `find`, `rg`, git status i przeglad folderow. Wystarcza przy kilku zmianach, ale koszt rosnie wraz z historia projektu.                         | Change status digest, ktory wypisuje foldery zmian, brakujace artefakty, status w `change.md` i ostatnie review/verification.                            | Jednorazowy raport Markdown tworzony z lokalnego skanu `context/changes`, bez bazy i bez UI.             |
| Typy i kontrakty miedzy API backendu a frontendem moga sie rozjechac, bo Pydantic schemas, TypeScript types i testy API sa utrzymywane w kilku miejscach.                              | Testy API, testy frontendowe i review. Sa wystarczajace dla wykrywania czesci bledow, ale nie zawsze pokazuja zrodlo rozjazdu.                         | API drift helper, ktory porownuje dotkniete backend schemas/routes z frontend `api.ts`, `types.ts` i testami.                                            | Checklista Markdown dla recenzenta: zmieniony endpoint, powiazany typ TS, test backendu, test frontendu. |

## Krok 3: wybrany helper

Wybrany sygnal: kontrakty deterministycznego JSONL, workspace isolation, run metadata, source identity i semantic safety sa rozproszone po repo, przez co review wymaga recznego skladania kontekstu.

Powod wyboru: ten problem powtarza sie przy wielu zmianach, laczy dokumentacje, backend, frontend i testy, a pierwsza wersja moze byc tylko raportem tylko do odczytu. Helper nie musi podejmowac decyzji za recenzenta; ma pokazac, gdzie spojrzec najpierw.

```text
Helper:
QSA Contract Risk Digest

Czyta:
git diff, context/foundation/prd.md, context/foundation/quality-contracts.md,
AGENTS.md, tests/contracts/*, tests/backtest_dataset/*, tests/backtest_quality/*
oraz zmienione pliki backendu i frontendu.

Zwraca:
Raport Markdown z lista dotknietych kontraktow, podejrzanych sformulowan,
powiazanych plikow do review, sugerowanych testow i brakujacych dowodow
walidacji.

Nie robi:
Nie blokuje merge, nie poprawia kodu, nie wysyla danych poza repo, nie analizuje
prawdziwych datasetow i nie przedstawia `directional bias` jako rekomendacji ani
wykonawczego sygnalu.

Ryzyko danych:
Niskie. Pierwsza wersja czyta tylko lokalne pliki repo i diff. Nie wymaga danych
firmowych, klienckich, produkcyjnych ani sekretow. Jezeli kiedys mialaby czytac
realne eksporty, musi najpierw dostac ograniczenia dostepu i sanitizacje.
```

Pierwsza wersja `QSA Contract Risk Digest` powinna byc raportem Markdown tworzonym lokalnie dla jednej zmiany. Raport powinien zaczynac sie od listy zmienionych plikow i mapowania ich na kontrakty z `quality-contracts.md`. Nastepnie powinien pokazac ostrzezenia semantyczne, na przyklad uzycie slow sugerujacych live trading, broker integration, order execution albo inwestycyjna rekomendacje w powierzchniach produktowych. Trzecia sekcja powinna proponowac testy do uruchomienia, oddzielajac szybki zestaw kontraktowy od pelniejszej walidacji. Czwarta sekcja powinna nazwac brakujace dowody, na przykład brak testu JSONL stability po zmianie eksportu. Wersja poczatkowa nie potrzebuje UI, bazy danych, CI ani automatycznego komentowania PR. Wystarczy, ze raz na realnej zmianie skroci czas review albo wskaze ryzyko, ktore latwo byloby przeoczyc.
