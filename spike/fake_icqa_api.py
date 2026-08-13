#!/usr/bin/env python3
"""Stub of the Generalitat de Catalunya ICQA air-quality endpoint.

Third target's vendor cloud. Unlike the other two this is a public, credential-
free endpoint fetched with GET, which is why the integration declares no auth —
the manifest still has to name the host before the request is allowed out.

The payload is the GeoJSON-ish shape models.py parses: a `fecha` timestamp and a
`features` list, each feature carrying station `properties` (including its
measured `contaminants`) and a `geometry`. NO2 rises between the two polls.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

STATION_ID = "8019004"

_state = {"polls": 0}


def _contaminant(cid: str, abbr: str, name: str, value: str, unit: str, quality: str) -> dict:
    return {
        "id": cid,
        "abbr": abbr,
        "nom": {"ca": name},
        "valor": value,
        "um": unit,
        "qualitat2021": quality,
        "qualitat": quality,
        "historic": [
            {"data": "2026-08-13 06:00", "valor": value, "qualitat2021": quality, "qualitat": quality},
        ],
    }


def _payload() -> dict:
    # Catalan decimal comma, as the real endpoint publishes.
    no2 = "41,7" if _state["polls"] > 1 else "28,3"
    no2_quality = "regular" if _state["polls"] > 1 else "bona"
    now = datetime.now(timezone.utc) - timedelta(minutes=10)

    return {
        "fecha": now.strftime("%d/%m/%Y %H:%M"),
        "features": [
            {
                "id": STATION_ID,
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": {"lat": "41,3874", "lon": "2,1686", "alt": "12"}},
                "properties": {
                    "id": STATION_ID,
                    "nom": "Barcelona (Eixample)",
                    "localitat": "Barcelona",
                    "direccio": "Av. Roma - C. Urgell",
                    "codiPostal": "08011",
                    "zona": {"id": "ZQA1", "nom": "Àrea de Barcelona"},
                    "qualitat2021": "regular" if _state["polls"] > 1 else "bona",
                    "qualitat": "regular" if _state["polls"] > 1 else "bona",
                    "dataActualitzacio": now.strftime("%d/%m/%Y %H:%M"),
                    "dataInst": "01/01/1991",
                    "fontEmissio": "trànsit",
                    "grauUrbanitzacio": "urbana",
                    "elevacio": "26",
                    "contaminantsEstacio": [
                        {"abbr": "NO2", "nom": {"ca": "Diòxid de nitrogen"}},
                        {"abbr": "PM10", "nom": {"ca": "Partícules < 10 µm"}},
                        {"abbr": "O3", "nom": {"ca": "Ozó"}},
                    ],
                    "contaminants": [
                        _contaminant("no2", "NO2", "Diòxid de nitrogen", no2, "ug/m3", no2_quality),
                        _contaminant("pm10", "PM10", "Partícules < 10 µm", "19,4", "ug/m3", "bona"),
                        _contaminant("o3", "O3", "Ozó", "62,0", "ug/m3", "raonablement_bona"),
                    ],
                },
            },
            {
                # A second station, so the integration has to select by id rather
                # than take whatever the payload happens to contain first.
                "id": "4319006",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": {"lat": "41,1189", "lon": "1,2445", "alt": "45"}},
                "properties": {
                    "id": "4319006",
                    "nom": "Tarragona (Parc de la Ciutat)",
                    "localitat": "Tarragona",
                    "zona": {"id": "ZQA4", "nom": "Camp de Tarragona"},
                    "qualitat2021": "bona",
                    "dataActualitzacio": now.strftime("%d/%m/%Y %H:%M"),
                    "contaminantsEstacio": [{"abbr": "NO2", "nom": {"ca": "Diòxid de nitrogen"}}],
                    "contaminants": [
                        _contaminant("no2", "NO2", "Diòxid de nitrogen", "12,1", "ug/m3", "bona"),
                    ],
                },
            },
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        _state["polls"] += 1
        body = json.dumps(_payload(), ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        # The real endpoint serves this as text/plain, which is why the client
        # passes content_type=None to .json(); keep that faithful.
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"  [vendor cloud] {fmt % args}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address; use 0.0.0.0 to reach it from a container")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), Handler)
    print(f"fake ICQA endpoint on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
