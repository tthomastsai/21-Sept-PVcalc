"""
Bond & Installment Accounts Calculator - HTML GUI server (v2.0.1).

Serves the browser-based GUI (web/index.html) and a small JSON API that reuses
the exact same financial logic as the Tkinter GUI and CLI (bond_calculator.py).

Standard library only - no extra dependencies. The server binds to 127.0.0.1
(this computer only).

Endpoints:
    GET  /               -> web/index.html
    POST /api/calculate  -> valuation, yield and amortisation schedule (JSON)
    POST /api/export     -> amortisation schedule as CSV (same format as the Tk export)
"""

import argparse
import json
import math
import os
import sys
import tempfile
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bond_calculator import (
    VALID_FREQUENCIES,
    VALID_INSTRUMENT_TYPES,
    calculate_bond,
    calculate_yield,
    export_schedule_to_csv,
    generate_amortization_schedule,
)

__version__ = "2.0.1"

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
MAX_BODY_BYTES = 16 * 1024
MAX_PERIODS = 1200  # 100 years of monthly payments; keeps the schedule responsive
VALID_METHODS = ("effective", "straight_line")
VALID_MODES = ("price", "yield")
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]"}


class InputError(ValueError):
    """Raised for invalid user input (reported to the browser as HTTP 400)."""


def _number(payload: Dict[str, Any], key: str, label: str) -> float:
    raw = payload.get(key)
    if isinstance(raw, bool) or raw is None:
        raise InputError(f"{label} is required.")
    if isinstance(raw, str):
        raw = raw.replace(",", "").replace("$", "").replace("%", "").strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise InputError(f"{label} must be a number (got {payload.get(key)!r}).")
    if not math.isfinite(value):
        raise InputError(f"{label} must be a finite number.")
    return value


def parse_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalise a calculation request."""
    if not isinstance(payload, dict):
        raise InputError("Request body must be a JSON object.")

    mode = payload.get("mode", "price")
    if mode not in VALID_MODES:
        raise InputError(f"Mode must be one of {list(VALID_MODES)}.")
    instrument = payload.get("instrument", "term")
    if instrument not in VALID_INSTRUMENT_TYPES:
        raise InputError(f"Instrument must be one of {list(VALID_INSTRUMENT_TYPES)}.")
    method = payload.get("method", "effective")
    if method not in VALID_METHODS:
        raise InputError(f"Method must be one of {list(VALID_METHODS)}.")

    try:
        freq = int(payload.get("frequency", 2))
    except (TypeError, ValueError):
        raise InputError("Frequency must be an integer.")
    if freq not in VALID_FREQUENCIES:
        raise InputError(f"Frequency must be one of {list(VALID_FREQUENCIES)}.")

    face = _number(payload, "face", "Face value")
    coupon = _number(payload, "coupon", "Coupon rate")
    years = _number(payload, "years", "Years to maturity")
    if years * freq > MAX_PERIODS + 0.5:
        raise InputError(f"Term is too long: at most {MAX_PERIODS} compounding periods are supported.")

    req: Dict[str, Any] = {
        "mode": mode,
        "instrument": instrument,
        "method": method,
        "frequency": freq,
        "face": face,
        "coupon": coupon,
        "years": years,
    }
    if mode == "price":
        req["market"] = _number(payload, "market", "Market rate")
    else:
        req["price"] = _number(payload, "price", "Present value")
    return req


def _run(req: Dict[str, Any]):
    """Same pipeline as BondCalculatorApp.calculate(): returns (bond, yield_result, market, schedule)."""
    inst, freq = req["instrument"], req["frequency"]
    y_res = None
    try:
        if req["mode"] == "price":
            market = req["market"]
        else:
            y_res = calculate_yield(
                face_value=req["face"],
                bond_price=req["price"],
                annual_coupon_rate=req["coupon"],
                years_to_maturity=req["years"],
                frequency=freq,
                instrument_type=inst,
            )
            market = y_res.nominal_yield

        bond = calculate_bond(req["face"], req["coupon"], market, req["years"], freq, inst)
        schedule = generate_amortization_schedule(
            req["face"], req["coupon"], market, req["years"], freq, req["method"], inst
        )
    except ValueError as err:
        raise InputError(str(err))
    return bond, y_res, market, schedule


def compute(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a request, run the calculation and return JSON-ready data."""
    req = parse_request(payload)
    bond, y_res, market, schedule = _run(req)
    return {
        "mode": req["mode"],
        "bond": asdict(bond),
        "yield": asdict(y_res) if y_res else None,
        "market_rate": market,
        "schedule": [asdict(row) for row in schedule],
    }


def schedule_csv(payload: Dict[str, Any]) -> str:
    """Build the CSV text with the existing exporter so headers/format stay identical."""
    try:
        decimals = int(payload.get("decimals", 2))
    except (TypeError, ValueError):
        raise InputError("Decimals must be an integer.")
    decimals = max(0, min(8, decimals))

    _, _, _, schedule = _run(parse_request(payload))
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        export_schedule_to_csv(schedule, path, decimals=decimals)
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    finally:
        os.unlink(path)


class Handler(BaseHTTPRequestHandler):
    server_version = "PVCalc/" + __version__

    def log_message(self, fmt: str, *args: Any) -> None:  # keep the terminal quiet
        pass

    # -- helpers ---------------------------------------------------------
    def _host_ok(self) -> bool:
        """Reject requests whose Host header is not this computer (blocks DNS-rebinding)."""
        header = self.headers.get("Host") or ""
        host = header.split("]")[0] + "]" if header.startswith("[") else header.split(":")[0]
        return host in ALLOWED_HOSTS

    def _send(self, status: int, body: bytes, content_type: str, extra: Tuple[Tuple[str, str], ...] = ()) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: Dict[str, Any]) -> None:
        self._send(status, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> Dict[str, Any]:
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            raise InputError("Content-Type must be application/json.")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise InputError("Invalid Content-Length.")
        if length <= 0 or length > MAX_BODY_BYTES:
            raise InputError("Request body is empty or too large.")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise InputError("Request body is not valid JSON.")

    # -- routes ----------------------------------------------------------
    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden host."})
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as fh:
                    return self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError:
                return self._json(500, {"error": "web/index.html is missing."})
        return self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden host."})
        try:
            if self.path == "/api/calculate":
                return self._json(200, compute(self._read_json()))
            if self.path == "/api/export":
                csv_text = schedule_csv(self._read_json())
                return self._send(
                    200,
                    csv_text.encode("utf-8"),
                    "text/csv; charset=utf-8",
                    (("Content-Disposition", 'attachment; filename="bond_amortisation_schedule.csv"'),),
                )
            return self._json(404, {"error": "Not found."})
        except InputError as err:
            return self._json(400, {"error": str(err)})
        except Exception:  # never leak internals to the browser
            return self._json(500, {"error": "Unexpected calculation error."})


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Bond & Installment Calculator - HTML GUI")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default 8765; 0 = any free port)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    args = parser.parse_args(argv)

    try:
        server = make_server(args.port)
    except OSError as err:
        sys.exit(f"Could not start the server on port {args.port}: {err}\nTry another port with --port 0")

    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Bond & Installment Calculator (HTML GUI) running at {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
