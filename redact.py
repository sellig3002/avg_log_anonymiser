#!/usr/bin/env python3
"""
Redactie-stap. Vervangt in de originele tekst elke waarde door <redacted> die:
  - in de anonymize-lijst staat (sowieso persoonsgegeven), of
  - in de llm-lijst staat en van classify.py het label 1 kreeg.

De rest van de tekst blijft ongewijzigd.
"""

PLACEHOLDER = "<redacted>"


def values_to_redact(anonymize_list, llm_list, labels):
    """Verzamel alle waarden die geredigeerd moeten worden."""
    values = [next(iter(d.values())) for d in anonymize_list]
    values += [next(iter(d.values())) for d, label in zip(llm_list, labels) if label == 1]
    return values


def redact(text, values):
    """Vervang elke waarde (langste eerst, zodat een korte waarde geen langere breekt)."""
    for value in sorted(set(values), key=len, reverse=True):
        text = text.replace(value, PLACEHOLDER)
    return text
