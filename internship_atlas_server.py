"""Backend for the DTSC Internship Atlas map.

Reads the internship CSV, aggregates it per state (reusing internship_backend.aggregate),
and serves the Atlas page -- the same US map, employer badges, tooltip, dossier modal and
field legend as the Claude artifact -- populated with the real numbers.

    python internship_atlas_server.py                     # serve http://localhost:8002 and open it
    python internship_atlas_server.py --csv other.csv     # use a different CSV
    python internship_atlas_server.py --port 5000 --no-open
    python internship_atlas_server.py --export atlas_live.html   # write a standalone page and exit

Routes:
    /                  the map page, with the aggregated data inlined
    /api/state_data    the aggregated data as JSON (same shape internship_backend.py writes)

The CSV is re-read whenever its modified time changes, so edit it and refresh the page.
Needs: flask, pandas.  The page loads d3, topojson and fonts from CDNs, so it needs internet.
"""

import argparse
import json
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from flask import Flask, Response, jsonify

from internship_backend import FIELDS, STATE_FIELD, aggregate

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "atlas.html"
DATA_MARKER = "/*__ATLAS_DATA__*/null"
REQUIRED = {"state", "field", "role", "company", "company_hq", "degree_level"}

app = Flask(__name__)
app.config["CSV_PATH"] = HERE / "internship_records.csv"
_cache = {"mtime": None, "data": None}


def load_data(csv_path):
    """Aggregate the CSV, reusing the cached result until the file changes."""
    csv_path = Path(csv_path)
    mtime = csv_path.stat().st_mtime
    if _cache["mtime"] == mtime and _cache["data"] is not None:
        return _cache["data"]

    df = pd.read_csv(csv_path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path.name} is missing required columns: {sorted(missing)}")
    unknown = sorted(set(df["field"]) - set(FIELDS))
    if unknown:
        raise ValueError(f"{csv_path.name} has field values the Atlas doesn't know: {unknown}")

    states = aggregate(df)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": int(len(df)),
        "fields": {k: {"label": v["label"]} for k, v in FIELDS.items()},
        "states": states,
    }
    _cache.update(mtime=mtime, data=data)
    return data


def render_page(data):
    html = TEMPLATE.read_text(encoding="utf-8")
    if DATA_MARKER not in html:
        raise RuntimeError("atlas.html has no data marker; was it edited?")
    payload = json.dumps(data).replace("</", "<\\/")   # keep the JSON from closing the <script> tag
    return html.replace(DATA_MARKER, payload)


def error_page(message, status=500):
    body = (f"<!doctype html><meta charset=utf-8><title>Atlas error</title>"
            f"<body style='font:16px system-ui;padding:40px;max-width:720px'><h1>Couldn't build the Atlas</h1>"
            f"<p>{message}</p></body>")
    return Response(body, status=status, mimetype="text/html")


@app.get("/")
def index():
    try:
        return Response(render_page(load_data(app.config["CSV_PATH"])), mimetype="text/html")
    except FileNotFoundError:
        return error_page(f"CSV not found: {app.config['CSV_PATH']}. Run "
                          f"<code>python internship_backend.py --generate-sample</code> to make one.")
    except (ValueError, RuntimeError) as exc:
        return error_page(str(exc))


@app.get("/api/state_data")
def state_data():
    try:
        return jsonify(load_data(app.config["CSV_PATH"]))
    except FileNotFoundError:
        return jsonify(error=f"CSV not found: {app.config['CSV_PATH']}"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 422


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="internship CSV (default: internship_records.csv next to this script)")
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--no-open", action="store_true", help="don't open a browser tab")
    ap.add_argument("--export", metavar="FILE", help="write a standalone HTML page with the data inlined, then exit")
    args = ap.parse_args()

    if args.csv:
        app.config["CSV_PATH"] = Path(args.csv).resolve()
    csv_path = app.config["CSV_PATH"]

    data = load_data(csv_path)       # fail fast with a clear message if the CSV is bad
    covered = len(data["states"])
    print(f"Read {data['source_rows']:,} rows from {csv_path.name}: {covered} of {len(STATE_FIELD)} states have records")

    if args.export:
        Path(args.export).write_text(render_page(data), encoding="utf-8")
        print(f"Wrote {args.export}")
        return

    url = f"http://localhost:{args.port}/"
    print(f"Serving {url}  (Ctrl+C to stop)")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
