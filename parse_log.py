#!/usr/bin/env python3
"""
Parse een log (JSON of losse key/value-regels) en verdeel de key/value-paren
over twee lijsten:

    anonymize -> zeker persoonsgegevens
    llm       -> twijfelgeval (mogelijk AVG, laat een LLM beslissen)

Velden die zeker niet onder de AVG vallen worden weggegooid.
De regels komen uit rules.conf in dezelfde map.

Gebruik:
    python parse_log.py <logbestand>
    cat log.txt | python parse_log.py
"""

import json
import re
import sys
from pathlib import Path

RULES_FILE = Path(__file__).with_name("rules.conf")

# key = [\w.]+  , waarde tussen quotes (QUOTED) of tot einde regel (UNQUOTED).
QUOTED = re.compile(r'([\w.]+)\s*[:=]\s*(["\'])(.*?)\2')
UNQUOTED = re.compile(r'^\W*([\w.]+)\s*[:=]\s*(.+?)\s*$')

# Ruisdetectie.
GUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
TOKEN_CHARS = re.compile(r'^[A-Za-z0-9_\-+/=]+$')  # tekens die in base64-achtige tokens voorkomen
NULLISH = ("null", "none", "false", "true")

# Bij dubbele values houden we het paar met de "waardevolste" key. Een key is
# waardevoller naarmate hij meer van deze woorden bevat (hoofdletter-ongevoelig).
PRIORITY_KEYS = ("name", "user", "id", "email", "phone", "address", "principal")


def parse_rules(text):
    """Parse rules-tekst als dict: sectie (lowercase) -> lijst met (lowercase) woorden."""
    sections = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line.lower())
    return sections


def load_rules(path):
    """Lees rules.conf van schijf en parse het."""
    if not path.exists():
        return {}
    return parse_rules(path.read_text(encoding="utf-8"))


def flatten_json(data):
    """Loop recursief door JSON en geef (key, value) van elke leaf terug."""
    pairs = []

    def walk(key, value):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(k, v)
        elif isinstance(value, list):
            for item in value:
                walk(key, item)
        else:
            pairs.append((key, "" if value is None else str(value)))

    walk("", data)
    return pairs


def parse_text(text):
    """Val terug op regexen als het geen JSON is."""
    pairs = []
    for line in text.splitlines():
        quoted = QUOTED.findall(line)
        if quoted:
            for key, _quote, value in quoted:
                pairs.append((key, value))
        else:
            m = UNQUOTED.match(line)
            if m:
                pairs.append((m.group(1), m.group(2).strip("\"'")))
    return pairs


def extract_pairs(text):
    """Probeer eerst JSON, val anders terug op losse regels."""
    try:
        return flatten_json(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        return parse_text(text)


def is_nullish(value):
    """True voor 'lege' waarden die NOOIT een persoonsgegeven kunnen zijn.

    Dit zijn null/none/false/true en waarden zonder enkele letter of cijfer
    (bv. "//]"). Deze mogen altijd weg, ook als de key normaal geanonimiseerd
    wordt -- een lege waarde bevat immers geen persoonsgegeven om te redigeren.
    Bewust GEEN cijfer-only / GUID / token hier: die horen wél afhankelijk te
    zijn van de key (bv. phoneNumber = "0612345678").
    """
    v = value.strip().lower()
    # null/none/false/true
    if v in NULLISH:
        return True
    # geen enkele letter of cijfer, bv. "//]"
    if not any(c.isalnum() for c in v):
        return True
    return False


def is_noise(value):
    """True voor waarden die duidelijk geen persoonsgegeven zijn (ruis)."""
    v = value.strip()
    # null/none/false/true of alleen symbolen
    if is_nullish(v):
        return True
    # uitsluitend cijfers, bv. "200"
    if v.isdigit():
        return True
    # GUID / UUID
    if GUID_RE.match(v):
        return True
    # base64-achtige token: één lang woord met letters EN cijfers, gemengd of met scheidingstekens
    if (len(v) >= 16 and TOKEN_CHARS.match(v)
            and any(c.isalpha() for c in v) and any(c.isdigit() for c in v)
            and (v.lower() != v or any(c in "_-+/=" for c in v))):
        return True
    return False


def classify(key, value, rules):
    """Geef 'anonymize', 'llm' of None (weggooien) terug."""
    key_l = key.lower()
    value_l = value.lower()

    # 0) Lege / null-achtige waarde (null, none, false, true, of alleen symbolen)
    #    is nooit een persoonsgegeven -- ook niet als de key normaal onder de
    #    anonymize-regels valt. Dit staat expres vóór alle andere checks, zodat
    #    bv. "ipAddress: null" niet de waarde "null" in de redigeer-lijst zet.
    if is_nullish(value):
        return None

    # 1) Harde override: woord uit valueContains -> altijd anonymize, key maakt niet uit.
    if any(word in value_l for word in rules.get("anonymize.valuecontains", [])):
        return "anonymize"

    # Valt de key onder de anonymize- en/of skip-regels?
    is_anon = (
        key_l in rules.get("anonymize.keyequals", [])
        or any(word in key_l for word in rules.get("anonymize.keycontains", []))
    )
    is_skip = (
        key_l in rules.get("skip.keyequals", [])
        or any(word in key_l for word in rules.get("skip.keycontains", []))
    )

    # 2) Duidelijk persoonsgegeven via de key wint ook van de ruisfilter
    #    (bv. phoneNumber = "0612345678" is enkel cijfers, maar wel een telefoonnummer).
    if is_anon and not is_skip:
        return "anonymize"

    # 3) Ruis (token, GUID, null/false/true, alleen cijfers of alleen symbolen) -> weggooien.
    if is_noise(value):
        return None

    # 4) Duidelijk géén persoonsgegeven via de key -> weggooien.
    if is_skip and not is_anon:
        return None

    # 5) Botsing (beide) of geen van beide -> geen "sowieso" -> twijfel -> llm.
    return "llm"


def dedupe(pairs):
    """Hou per unieke value één paar over.

    Winnaar = de key met de meeste PRIORITY_KEYS-woorden; bij gelijkspel (of als
    geen enkele key een keyword bevat) de alfabetisch eerste key. De volgorde
    volgt het eerste voorkomen van elke value.
    """
    groups = {}   # value -> lijst van (key, value)
    order = []    # values in volgorde van eerste voorkomen
    for pair in pairs:
        (key, value), = pair.items()
        if value not in groups:
            groups[value] = []
            order.append(value)
        groups[value].append((key, value))

    def score(key):
        low = key.lower()
        return sum(1 for word in PRIORITY_KEYS if word in low)

    result = []
    for value in order:
        # meeste keywords eerst (-score), daarna alfabetisch op key
        best_key, best_value = min(groups[value], key=lambda kv: (-score(kv[0]), kv[0].lower()))
        result.append({best_key: best_value})
    return result


def split(text, rules=None):
    """Parse de tekst en geef {'llm': [...], 'anonymize': [...]} terug (ontdubbeld)."""
    if rules is None:
        rules = load_rules(RULES_FILE)

    result = {"llm": [], "anonymize": []}
    for key, value in extract_pairs(text):
        value = value.strip()
        if len(value) < 2:            # lege of te korte waarde overslaan
            continue
        bucket = classify(key, value, rules)
        if bucket:
            result[bucket].append({key: value})

    result["llm"] = dedupe(result["llm"])
    result["anonymize"] = dedupe(result["anonymize"])
    return result


def main():
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    print(json.dumps(split(text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
