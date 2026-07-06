#!/usr/bin/env python3
"""
Pipeline: ruwe log-tekst -> geanonimiseerde tekst.

    parse_log.split   -> {'llm': [...], 'anonymize': [...]}
    classify.classify_field per llm-veld -> 0/1
    redact            -> vervang de te anonimiseren waarden door <redacted>
"""

from parse_log import split, parse_rules
from classify import classify_field
from redact import values_to_redact, redact


def anonymize(text, system_prompt=None, rules_text=None):
    """Anonimiseer log-tekst.

    system_prompt : optionele override voor de LLM-systeemprompt.
    rules_text    : optionele override voor rules.conf (als ruwe tekst).
    Beide vallen terug op de standaardwaarden als ze leeg/None zijn.
    """
    rules = parse_rules(rules_text) if rules_text else None
    buckets = split(text, rules=rules)
    labels = [classify_field(field, system_prompt=system_prompt) for field in buckets["llm"]]
    values = values_to_redact(buckets["anonymize"], buckets["llm"], labels)
    return redact(text, values)


if __name__ == "__main__":
    import sys

    data = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    print(anonymize(data))
