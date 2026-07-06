"""Lokale webapp voor log-anonimisatie. Draait op http://127.0.0.1:5000"""
from pathlib import Path
from flask import Flask, request, Response
from pipeline import anonymize
from settings_routes import register

app = Flask(__name__)
register(app)  # voegt /defaults toe (systeemprompt + rules.conf voor de UI)
PAGE = Path(__file__).with_name("index.html").read_text(encoding="utf-8")


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/anonymize", methods=["POST"])
def do_anonymize():
    # Twee vormen worden geaccepteerd:
    #  - JSON body {"text": ..., "system_prompt": ..., "rules": ...}
    #    waarbij system_prompt/rules optioneel zijn (leeg = standaard gebruiken).
    #  - Kale tekst als body (oude gedrag, zonder overrides).
    system_prompt = None
    rules_text = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        system_prompt = data.get("system_prompt") or None
        rules_text = data.get("rules") or None
    else:
        text = request.get_data(as_text=True)

    try:
        result = anonymize(text, system_prompt=system_prompt, rules_text=rules_text)
        return Response(result, mimetype="text/plain; charset=utf-8")
    except Exception as e:
        return Response("Fout: " + str(e), status=400, mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
