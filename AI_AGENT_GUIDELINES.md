# Wskazówki dotyczące budowy agenta AI

Dokument opracowany na podstawie materiału przekazanego przez użytkownika:
„AI Factory Stack” i jego rozszerzenia o obserwowalność. To wskazówki projektowe,
a nie opis już zaimplementowanych funkcji ani dodatkowe wymagania zadania.
Decyzje podjęte podczas rozwoju zapisujemy w `SOLUTION.md`.

## Cel

Agent powinien udzielać poprawnych odpowiedzi, a jego działanie powinno dać się
prześledzić. Sama odpowiedź końcowa nie wyjaśni, dlaczego proste pytanie zajęło
40 sekund. Potrzebujemy wiedzieć, jakie kroki wykonano, ile trwały i gdzie
wystąpił problem.

## Elementy systemu — analogia do fabryki

### 1. LLM — maszyna

Model generuje tekst i analizuje otrzymany kontekst. Jakość oraz trafność tego
kontekstu mają duże znaczenie; sam wybór modelu nie rozwiązuje problemów z danymi.

W CityWheels model wybiera narzędzia i wyjaśnia ich wyniki. Nie wymyśla danych
rezerwacji i nie oblicza samodzielnie kwot zwrotów.

### 2. RAG — pomieszczenie z surowcami

Wyszukiwanie dostarcza modelowi informacje potrzebne do odpowiedzi.

W naszym projekcie tę rolę pełni `search_policies`: znajduje odpowiednie fragmenty
polityk i zwraca je wraz ze źródłami. Wyszukiwanie nie wymaga od razu embeddingów
ani bazy wektorowej.

### 3. Baza wektorowa — magazyn

Baza wektorowa przechowuje embeddingi, czyli liczbowe reprezentacje informacji,
i umożliwia wyszukiwanie według podobieństwa.

To opcjonalny element. Przy trzech krótkich dokumentach zaczynamy od prostego
wyszukiwania. Rozbudowę uzasadniamy wynikami ewaluacji, np. problemami z parafrazami.

### 4. Agent AI — kierownik hali

Agent wybiera kolejny krok i wywołuje narzędzia, aby odpowiedzieć na pytanie.

Docelowy przebieg w CLI:

1. Użytkownik zadaje pytanie.
2. Model wybiera narzędzie i jego argumenty.
3. Aplikacja sprawdza argumenty i wykonuje narzędzie.
4. Wynik wraca do modelu.
5. Model wybiera kolejny krok albo zwraca odpowiedź końcową.

Pętla powinna mieć limit wywołań oraz kontrolowane zakończenie przy błędzie.

### 5. MCP — standard gniazdka

MCP to wspólny sposób podłączania narzędzi i danych do aplikacji AI. Samo
połączenie nie nadaje uprawnień — dostęp nadal wymaga odpowiedniej autoryzacji.

Na obecnym etapie CityWheels korzysta z lokalnych funkcji i plików. MCP nie jest
potrzebne do realizacji zadania; można je rozważyć przy przyszłych integracjach.

### 6. Guardrails — system zabezpieczeń

Reguły i limity obejmują dane wejściowe, odpowiedzi oraz wykonywane operacje.
Nie powinny opierać się wyłącznie na instrukcji dla modelu.

W CityWheels oznacza to przede wszystkim:

- walidację argumentów narzędzi i obsługę nieznanej rezerwacji;
- obliczanie pieniędzy w Pythonie z użyciem `Decimal`;
- stosowanie stałego czasu z zadania zamiast czasu systemowego;
- odpowiadanie na podstawie polityk i danych rezerwacji;
- kierowanie do obsługi przy brakujących informacjach i wyjątkach wymagających decyzji pracownika;
- limity wywołań narzędzi, timeouty i ograniczone ponawianie żądań.

Obecny zakres to wycena zwrotu, bez anulowania rezerwacji i bez wypłacania pieniędzy.
Jeżeli kiedyś dodamy rzeczywiste wypłaty, wymagania dotyczące autoryzacji i zgody
trzeba zaprojektować osobno.

### 7. Evals — kontrola jakości

Płynna odpowiedź nie musi być poprawna. Sprawdzamy, czy agent wykonał zadanie
zgodnie z danymi i regułami.

Testy pytest sprawdzają narzędzia oraz pętlę agenta z modelem testowym.
Ewaluacja obejmuje pytania użytkowników, oczekiwane fakty, kwoty, wywołania narzędzi
i odmowy odpowiedzi. Raportujemy rzeczywiste wyniki, również niepowodzenia.
Testy z modelem testowym nie zastępują ewaluacji z prawdziwym modelem.

### 8. Observability — sterownia

Obserwowalność pokazuje, co wydarzyło się podczas obsługi pytania. Trzy podstawowe
sygnały to ślady wykonania, metryki i logi.

| Sygnał | Co pokazuje | Przykład w CityWheels |
| --- | --- | --- |
| Ślad wykonania (trace) | Kolejne kroki jednego żądania i ich czasy | Wywołanie modelu → `get_booking` → `calculate_refund` → odpowiedź |
| Metryki | Powtarzające się wzorce i zmiany w czasie | Czas odpowiedzi, liczba błędów, tokenów i ponowień |
| Logi | Zdarzenia pomagające wyjaśnić konkretny problem | Timeout dostawcy, błędne argumenty, osiągnięty limit wywołań |

## Minimalna obserwowalność dla naszego CLI

Na początek wystarczą ustrukturyzowane logi i pomiary czasu. Nie musimy od razu
uruchamiać zewnętrznej platformy monitorującej.

Docelowo dla każdego pytania zapisujemy:

- identyfikator żądania łączący jego zdarzenia;
- dostawcę i nazwę modelu;
- czas całkowity oraz czas poszczególnych wywołań modelu i narzędzi;
- nazwę narzędzia, status wykonania i rodzaj błędu;
- liczbę wywołań, ponowień i przyczynę zakończenia;
- zużycie tokenów, jeżeli dostawca je udostępnia — brak danych nie oznacza zera.

Czasy trwania mierzymy zegarem monotonicznym, niezależnie od stałej daty używanej
do obliczania zwrotów. Diagnostykę kierujemy na stderr, a odpowiedź CLI na stdout.
Nie zapisujemy kluczy API ani domyślnie pełnych treści pytań i danych rezerwacji.

## Jak diagnozować wolną odpowiedź

Przykład: odpowiedź trwa 40 sekund, ponieważ system sześć razy próbuje połączyć
się z niedostępną usługą. Szybszy model może nie usunąć głównej przyczyny.

1. Odtwórz przebieg żądania i sprawdź czasy poszczególnych kroków.
2. Ustal, czy opóźnienie pochodzi z modelu, wyszukiwania, narzędzia czy ponowień.
3. Sprawdź politykę ponawiania, także tę wbudowaną w klienta dostawcy.
4. Zmień timeouty lub liczbę ponowień na podstawie obserwacji.
5. Powtórz to samo pytanie i porównaj czas, błędy oraz poprawność odpowiedzi.

Nie poprawiamy szybkości kosztem poprawności. Zmiana powinna mieć mierzalny efekt,
a jej uzasadnienie i wyniki powinny trafić do `SOLUTION.md`.

## Pytanie kontrolne

Jeżeli jutro odpowiedź potrwa dwa razy dłużej, czy potrafimy wyjaśnić dlaczego?
Powinniśmy umieć wskazać zarówno wynik działania agenta, jak i przebieg,
który do niego doprowadził, oraz miejsce ewentualnej awarii.
