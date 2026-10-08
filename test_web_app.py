"""Tests for the HTML GUI back end (web_app.py)."""

import csv
import http.client
import io
import json
import threading
import unittest

import web_app
from bond_calculator import calculate_bond, generate_amortization_schedule
from web_app import InputError, compute, parse_request, schedule_csv

BASE = {
    "mode": "price", "instrument": "term", "method": "effective", "frequency": 2,
    "face": "1000.00", "coupon": "4.00", "market": "6.00", "years": "5.0",
}


def req(**overrides):
    out = dict(BASE)
    out.update(overrides)
    return out


class ComputeTests(unittest.TestCase):
    def test_matches_core_calculator_for_every_instrument(self):
        for inst in ("term", "serial_equal_principal", "serial_equal_payment"):
            for method in ("effective", "straight_line"):
                with self.subTest(inst=inst, method=method):
                    out = compute(req(instrument=inst, method=method))
                    bond = calculate_bond(1000.0, 4.0, 6.0, 5.0, 2, inst)
                    sched = generate_amortization_schedule(1000.0, 4.0, 6.0, 5.0, 2, method, inst)
                    self.assertAlmostEqual(out["bond"]["bond_price"], bond.bond_price, places=9)
                    self.assertEqual(len(out["schedule"]), len(sched))
                    self.assertAlmostEqual(out["schedule"][-1]["ending_carrying_amount"],
                                           sched[-1].ending_carrying_amount, places=9)
                    self.assertIsNone(out["yield"])

    def test_term_bond_known_price(self):
        out = compute(req())
        self.assertAlmostEqual(out["bond"]["bond_price"], 914.70, places=2)
        self.assertEqual(out["bond"]["status"], "Discount")

    def test_schedule_convergence(self):
        term = compute(req())["schedule"][-1]
        self.assertAlmostEqual(term["ending_carrying_amount"], 1000.0, places=6)
        for inst in ("serial_equal_principal", "serial_equal_payment"):
            self.assertAlmostEqual(compute(req(instrument=inst))["schedule"][-1]["ending_carrying_amount"], 0.0, places=6)

    def test_yield_mode_round_trip(self):
        for inst in ("term", "serial_equal_principal", "serial_equal_payment"):
            with self.subTest(inst=inst):
                price = compute(req(instrument=inst))["bond"]["bond_price"]
                out = compute(req(mode="yield", instrument=inst, price=price, market=None))
                self.assertAlmostEqual(out["market_rate"], 6.0, places=5)
                self.assertIsNotNone(out["yield"])

    def test_formatted_strings_are_accepted(self):
        out = compute(req(face="$1,000.00", coupon="4%", market="6 %"))
        self.assertAlmostEqual(out["bond"]["bond_price"], 914.70, places=2)

    def test_par_bond(self):
        out = compute(req(coupon="6", market="6"))
        self.assertEqual(out["bond"]["status"], "Par")


class ValidationTests(unittest.TestCase):
    def assertRejected(self, **overrides):
        with self.assertRaises(InputError):
            compute(req(**overrides))

    def test_bad_enums(self):
        self.assertRejected(mode="nope")
        self.assertRejected(instrument="nope")
        self.assertRejected(method="nope")
        self.assertRejected(frequency=3)
        self.assertRejected(frequency="abc")

    def test_bad_numbers(self):
        for bad in ("abc", "", None, True, "nan", "inf", float("nan"), float("inf")):
            with self.subTest(bad=bad):
                self.assertRejected(face=bad)

    def test_domain_errors_come_from_core_as_input_errors(self):
        self.assertRejected(face="0")
        self.assertRejected(face="-5")
        self.assertRejected(coupon="-1")
        self.assertRejected(market="-1")
        self.assertRejected(years="0")
        self.assertRejected(years="0.0001")       # rounds to 0 periods

    def test_term_limits(self):
        compute(req(frequency=12, years="100"))   # exactly MAX_PERIODS is fine
        self.assertRejected(frequency=12, years="100.1")
        self.assertRejected(years="1e308", frequency=12)

    def test_missing_required_field_per_mode(self):
        payload = req()
        del payload["market"]
        with self.assertRaises(InputError):
            compute(payload)
        with self.assertRaises(InputError):
            compute(req(mode="yield"))            # no price supplied

    def test_non_object_body(self):
        with self.assertRaises(InputError):
            parse_request([1, 2, 3])


class CsvTests(unittest.TestCase):
    def test_csv_matches_exporter_format(self):
        text = schedule_csv(dict(req(), decimals=3))
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[0][0], "Period")
        self.assertIn("Ending Carrying Amount", rows[0])
        self.assertEqual(len(rows), 1 + 10)
        self.assertRegex(rows[1][1], r"^\d+\.\d{3}$")

    def test_csv_decimals_are_clamped(self):
        rows = list(csv.reader(io.StringIO(schedule_csv(dict(req(), decimals=99)))))
        self.assertRegex(rows[1][1], r"^\d+\.\d{8}$")
        rows = list(csv.reader(io.StringIO(schedule_csv(dict(req(), decimals=-4)))))
        self.assertRegex(rows[1][1], r"^\d+$")


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = web_app.make_server(0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, method, path, body=None, headers=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.putrequest(method, path, skip_host=True)
        conn.putheader("Host", host or f"127.0.0.1:{self.port}")
        for k, v in (headers or {}).items():
            conn.putheader(k, v)
        if body is not None:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp, data

    def post_json(self, path, payload, **kw):
        body = json.dumps(payload).encode()
        return self.request("POST", path, body, {"Content-Type": "application/json"}, **kw)

    def test_serves_index(self):
        resp, data = self.request("GET", "/")
        self.assertEqual(resp.status, 200)
        self.assertIn("text/html", resp.getheader("Content-Type"))
        self.assertIn(b"Bond &amp; Installment Accounts Calculator", data)
        self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")

    def test_calculate_ok(self):
        resp, data = self.post_json("/api/calculate", req())
        self.assertEqual(resp.status, 200)
        self.assertAlmostEqual(json.loads(data)["bond"]["bond_price"], 914.70, places=2)

    def test_calculate_bad_input_is_400_with_message(self):
        resp, data = self.post_json("/api/calculate", req(face="0"))
        self.assertEqual(resp.status, 400)
        self.assertIn("Face value", json.loads(data)["error"])

    def test_requires_json_content_type(self):
        resp, _ = self.request("POST", "/api/calculate", json.dumps(req()).encode(), {"Content-Type": "text/plain"})
        self.assertEqual(resp.status, 400)

    def test_invalid_json_and_oversized_body(self):
        resp, _ = self.request("POST", "/api/calculate", b"{not json", {"Content-Type": "application/json"})
        self.assertEqual(resp.status, 400)
        resp, _ = self.request("POST", "/api/calculate", b"x" * (web_app.MAX_BODY_BYTES + 1), {"Content-Type": "application/json"})
        self.assertEqual(resp.status, 400)

    def test_foreign_host_header_is_rejected(self):
        resp, _ = self.request("GET", "/", host="evil.example.com")
        self.assertEqual(resp.status, 403)
        resp, _ = self.post_json("/api/calculate", req(), host="evil.example.com")
        self.assertEqual(resp.status, 403)

    def test_localhost_host_header_is_accepted(self):
        resp, _ = self.request("GET", "/", host=f"localhost:{self.port}")
        self.assertEqual(resp.status, 200)

    def test_unknown_paths(self):
        self.assertEqual(self.request("GET", "/nope")[0].status, 404)
        self.assertEqual(self.post_json("/api/nope", {})[0].status, 404)

    def test_export_returns_csv_attachment(self):
        resp, data = self.post_json("/api/export", dict(req(), decimals=2))
        self.assertEqual(resp.status, 200)
        self.assertIn("text/csv", resp.getheader("Content-Type"))
        self.assertIn("attachment", resp.getheader("Content-Disposition"))
        self.assertTrue(data.decode().startswith("Period,Beginning Carrying Amount"))


if __name__ == "__main__":
    unittest.main()
