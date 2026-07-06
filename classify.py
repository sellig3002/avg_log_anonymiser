#!/usr/bin/env python3
"""
Classificeer de 'llm'-lijst uit parse_log.py met de llama.cpp-server.

Elk JSON-veld wordt één voor één aan het model voorgelegd; het model geeft per
veld precies één teken terug: 1 = persoonsgegeven, 0 = niet.

Input : een JSON-lijst van {key: value}-velden, óf de volledige output van
        parse_log.py (dan wordt de 'llm'-lijst er zelf uit gepakt).
        Via een bestand als argument, of via stdin.
Output: een JSON-lijst met per veld een 0 of 1, in dezelfde volgorde.

Gebruik:
    python3 classify.py llm.json
    python3 parse_log.py log | python3 classify.py        # pakt zelf .llm
    python3 parse_log.py log | jq '.llm' | python3 classify.py

Alleen de standaardbibliotheek nodig. Endpoint via CLASSIFIER_URL te overriden.
"""

import json
import os
import sys
import urllib.request

URL = os.environ.get("CLASSIFIER_URL", "http://127.0.0.1:8080/v1/chat/completions")
TIMEOUT = 60  # seconden per request

SYSTEM_PROMPT = (
    "Classify whether the VALUE in the given JSON field is personal data under the GDPR"
    "identifies a specific person: name, email, phone, address, username, laptopname, IP etc.)"
    "Reply with exactly one character: 1 = personal data, 0 = not"
    'Examples: {"Name":"joshuajohn"}->1 ; {"Color":"blue"}->0 ;'
    '{"Phone":"0612345678"}->1 ; {"Country":"Netherlands"}->0 ;'
    '{"host":"laptop of bob"}->1 ; {"name":"microsoft threat intel"}->0'
)

GRAMMAR = 'root ::= "1" | "0"'


def classify_field(field, system_prompt=None):
    """Stuur één JSON-veld naar het model en geef 0 of 1 terug.

    system_prompt overschrijft de standaard SYSTEM_PROMPT als het is meegegeven
    (en niet leeg is). Zo kan de webapp per request een eigen prompt gebruiken
    zonder de module-globale te muteren.
    """
    prompt = system_prompt if system_prompt else SYSTEM_PROMPT
    payload = {
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(field)},
        ],
        "cache_prompt": True,
        "temperature": 0,
        "seed": 42,
        "max_tokens": 2,
        "grammar": GRAMMAR,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.load(resp)
    content = body["choices"][0]["message"]["content"].strip()
    return 1 if content.startswith("1") else 0


def load_fields(text):
    """Accepteer een kale lijst of de volledige parse_log.py-output."""
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("llm", [])
    return data


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    fields = load_fields(text)
    labels = [classify_field(field) for field in fields]
    print(json.dumps(labels))


if __name__ == "__main__":
    main()
