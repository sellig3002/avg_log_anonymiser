"""
Extra Flask-routes waarmee de webapp de systeemprompt en rules.conf kan tonen.

Los gehouden van app.py zodat de kern klein blijft. Registreer met:

    from settings_routes import register
    register(app)

De endpoints geven alleen de *huidige standaardwaarden* terug (de prompt uit
classify.py en de inhoud van rules.conf). Het daadwerkelijk toepassen van een
aangepaste prompt of aangepaste rules gebeurt per request in /anonymize: de
browser stuurt de overrides mee. Er wordt dus niets op de server opgeslagen —
aanpassingen zijn lokaal aan de browser van de gebruiker.
"""

from pathlib import Path

from flask import Response, jsonify

from classify import SYSTEM_PROMPT

RULES_FILE = Path(__file__).with_name("rules.conf")


def _read_rules():
    """Geef de huidige inhoud van rules.conf terug (leeg als het bestand ontbreekt)."""
    if RULES_FILE.exists():
        return RULES_FILE.read_text(encoding="utf-8")
    return ""


def register(app):
    """Voeg de settings-endpoints toe aan een bestaande Flask-app."""

    @app.route("/defaults")
    def defaults():
        """De standaard systeemprompt en rules.conf, voor het vullen van de UI."""
        return jsonify({
            "system_prompt": SYSTEM_PROMPT,
            "rules": _read_rules(),
        })

    # Losse plain-text endpoints, handig om even te controleren of terug te zetten.
    @app.route("/defaults/system_prompt")
    def default_system_prompt():
        return Response(SYSTEM_PROMPT, mimetype="text/plain; charset=utf-8")

    @app.route("/defaults/rules")
    def default_rules():
        return Response(_read_rules(), mimetype="text/plain; charset=utf-8")

    return app
