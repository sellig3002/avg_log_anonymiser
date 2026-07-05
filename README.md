# avg_log_anonymiser

Kleine lokale tool die logs (JSON of losse `key: value`-regels) anonimiseert volgens de AVG.
Je plakt een log in, en je krijgt dezelfde log terug waarin persoonsgegevens vervangen zijn
door `<redacted>`.

Aanpak in het kort: alle key/value-paren worden uit de log gehaald en verdeeld in drie groepen —
zeker persoonsgegeven (`anonymize`), zeker niet (weggegooid), en twijfel (`llm`). De
twijfelgevallen gaan één voor één langs een lokaal draaiend taalmodel dat per veld `0` of `1`
teruggeeft. Alles uit `anonymize`, plus elk twijfelveld dat als persoonsgegeven (`1`) wordt
aangemerkt, wordt in de uitvoer geredigeerd.

## Bestanden

- `parse_log.py` — haalt de key/value-paren uit de log, filtert ruis (tokens, GUID's, alleen
  cijfers/symbolen, null/true/false), ontdubbelt gelijke waarden en verdeelt de rest over
  `llm` en `anonymize`. Leest de regels uit `rules.conf`.
- `rules.conf` — de instelbare regels: welke keys/values sowieso wél of niet persoonsgegeven
  zijn. Hierin pas je het gedrag aan zonder de code te wijzigen.
- `classify.py` — stuurt elk twijfelveld apart naar het lokale LLM en geeft een lijst met
  `0`/`1` terug.
- `redact.py` — vervangt de te anonimiseren waarden door `<redacted>`.
- `pipeline.py` — rijgt de stappen aaneen tot één functie `anonymize(text)`.
- `app.py` — Flask-webapp op http://127.0.0.1:5000 die `pipeline.anonymize` aanroept.
- `index.html` — de pagina (los van de server).
- `requirements.txt` — Python-afhankelijkheden (Flask).

## Wat waar aanpassen

- Filterregels (keys/values die wél of niet persoonsgegeven zijn): `rules.conf`.
- Prioriteit bij dubbele waarden (welke key de LLM te zien krijgt): `PRIORITY_KEYS` bovenin
  `parse_log.py`.
- Ruisdetectie, bijv. GUID's wel/niet weggooien: `is_noise` in `parse_log.py`.
- Model-endpoint, systeemprompt en grammar: bovenin `classify.py`, of via de omgevingsvariabele
  `CLASSIFIER_URL`.
- De placeholdertekst: `PLACEHOLDER` in `redact.py`.

## Vereiste: een lokaal draaiend LLM

`classify.py` praat met een OpenAI-compatibele endpoint op
`http://127.0.0.1:8080/v1/chat/completions` (een llama.cpp-server). Zonder draaiend model werkt
de anonimisatie niet.

Het standaardmodel is **Qwen2.5-1.5B**, maar elk model kan gebruikt worden; pas zo nodig de
systeemprompt in `classify.py` aan.

De server draait als systemd-service `llm.service`:

```
sudo systemctl status llm.service
sudo systemctl restart llm.service
```

Draait je server op een ander adres of poort, zet dan `CLASSIFIER_URL`, bijvoorbeeld:

```
export CLASSIFIER_URL=http://127.0.0.1:9000/v1/chat/completions
```

## Installeren en draaien

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Daarna staat de webapp op http://127.0.0.1:5000.

De onderdelen werken ook los via de CLI:

```
python parse_log.py log.txt                        # de drie groepen als JSON
python parse_log.py log.txt | python classify.py   # 0/1-labels voor de llm-lijst
python pipeline.py log.txt                          # volledige geanonimiseerde tekst
```
