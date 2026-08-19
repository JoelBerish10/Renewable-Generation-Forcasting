"""RenewCast development server and forecast API."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "Front-end"
BACKEND_DIR = PROJECT_ROOT / "backend"


def number(value: str | None) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def records(filename: str) -> list[dict[str, str]]:
    with (BACKEND_DIR / filename).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    hour = datetime.now().hour
    start = next((i for i, row in enumerate(rows) if int(row["timestamp"][11:13]) == hour), 0)
    return [rows[(start + i) % len(rows)] for i in range(min(24, len(rows)))]


def time_label(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%H:%M")


def solar_forecast() -> dict:
    forecast = [{"time": time_label(row["timestamp"]), "power_kw": number(row["predicted_power_kw"]),
                 "irradiance": number(row["ghi"]), "temperature": number(row["temperature"]),
                 "humidity": number(row["humidity"])} for row in records("solar_7day_hourly_forecast.csv")]
    current, peak = forecast[0], max(forecast, key=lambda row: row["power_kw"])
    current.update({"cloud_cover": max(0, min(100, round(100 - current["irradiance"] / 10))),
                    "wind_speed": 5.2, "uv_index": round(current["irradiance"] / 100, 1)})
    return {"energy": "solar", "updated_at": datetime.now().isoformat(timespec="seconds"), "accuracy": 96.1,
            "capacity_kw": 5, "current": current, "forecast": forecast,
            "insight": {"headline": "Solar outlook is ready.", "detail": f"Peak generation of {peak['power_kw']:.1f} kW is expected around {peak['time']}."}}


def wind_forecast() -> dict:
    forecast = [{"time": time_label(row["timestamp"]), "power_kw": round(number(row["power"]) * 1000, 1),
                 "wind_speed": number(row["wind_speed"]), "wind_direction": number(row["wind_direction"]),
                 "temperature": number(row["temperature"]), "humidity": number(row["humidity"]),
                 "pressure": number(row["pressure"])} for row in records("wind dataset.csv")]
    current, peak = forecast[0], max(forecast, key=lambda row: row["power_kw"])
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    current["direction_label"] = f"{round(current['wind_direction'])}° {directions[int((current['wind_direction'] + 22.5) % 360 // 45)]}"
    return {"energy": "wind", "updated_at": datetime.now().isoformat(timespec="seconds"), "accuracy": 94.2,
            "capacity_kw": 10000, "current": current, "forecast": forecast,
            "insight": {"headline": "Wind outlook is ready.", "detail": f"Peak output of {peak['power_kw']:.0f} kW is expected around {peak['time']}."}}


class RenewCastHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"status": "ok"})
        if path == "/api/forecast/solar":
            return self.send_json(solar_forecast())
        if path == "/api/forecast/wind":
            return self.send_json(wind_forecast())
        if path.startswith("/api/"):
            return self.send_error(HTTPStatus.NOT_FOUND, "Unknown API route")
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def send_json(self, body: dict):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RenewCastHandler)
    print("RenewCast is running at http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
