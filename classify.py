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
    "Read the VALUE of the given JSON field and ignore the field name. Reply 1 if the "
    "value contains any of these, even buried inside a longer string: a real person's "
    "name (a human first/last name), an email address, an IP address (IPv4 or IPv6), or "
    "a postal/street address. Reply 0 for everything else, especially machine or "
    "software identifiers: service and system accounts, hostnames, process and file "
    "names, rule or alert names, and event categories. Judge by the value, not the key: "
    "a string built from symbols (\\ $ / . ::) or words like service, agent, daemon, "
    "system, rule, alert is a machine, not a person. Reply with exactly one character: "
    '1 or 0. Examples: {"submitter":"Ruben Haaksma"}->1 ; '
    '{"note":"escalated by Wouter Kalf on friday"}->1 ; {"reply":"t.smid@bedrijf.be"}->1 ; '
    '{"peer":"172.19.4.88"}->1 ; {"loc":"Molenweg 8, 3512 AB Deventer"}->1 ; '
    '{"svc":"agent-updater"}->0 ; {"node":"prod-web-03"}->0 ; ' 
    '{"given":"Franka"}->1 ; '
    '{"alert":"Rare Port Scan Detected"}->0 ; {"bin":"lsass.exe"}->0'
)

GRAMMAR = 'root ::= "1" | "0"'


def classify_field(field):
    """Stuur één JSON-veld naar het model en geef 0 of 1 terug."""
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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
