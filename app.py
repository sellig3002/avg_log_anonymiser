"""Lokale webapp voor log-anonimisatie. Draait op http://127.0.0.1:5000"""
from pathlib import Path
from flask import Flask, request, Response
from pipeline import anonymize

app = Flask(__name__)
PAGE = Path(__file__).with_name("index.html").read_text(encoding="utf-8")


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/anonymize", methods=["POST"])
def do_anonymize():
    text = request.get_data(as_text=True)
    try:
        return Response(anonymize(text), mimetype="text/plain; charset=utf-8")
    except Exception as e:
        return Response("Fout: " + str(e), status=400, mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
