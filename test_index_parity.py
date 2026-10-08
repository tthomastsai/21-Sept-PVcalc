"""
Parity test: the JavaScript calculator inside index.html must agree with bond_calculator.py.

The real <script> code is extracted from index.html and run with Node on many random inputs;
every number, error message and the CSV text are compared with the Python implementation.
Skipped automatically when Node.js is not installed.
"""

import csv
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest

from bond_calculator import (
    calculate_bond,
    calculate_yield,
    export_schedule_to_csv,
    generate_amortization_schedule,
)

HERE = os.path.dirname(os.path.abspath(__file__))
NODE = shutil.which("node")

RUNNER = r"""
const fs = require('fs');
const [fixedSrc, coreSrc] = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).sources;
const core = new Function(fixedSrc + coreSrc +
  ';return {compute, scheduleToCsv, InputError};')();
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = cases.map((c) => {
  try {
    const r = core.compute(c);
    return { ok: true, result: r, csv: [0, 2, 5].map((d) => core.scheduleToCsv(r.schedule, d)) };
  } catch (e) {
    return { ok: false, error: e.message, input: e instanceof core.InputError };
  }
});
process.stdout.write(JSON.stringify(out));
"""


def extract_sources():
    with open(os.path.join(HERE, "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    fixed = re.search(r"  function fixed\(x, d\) \{.*?\n  \}\n  function group\(s\) \{.*?\n  \}\n", html, re.S)
    core = re.search(r"/\* ===== calculator core START.*?calculator core END ===== \*/", html, re.S)
    assert fixed and core, "could not find the calculator core inside index.html"
    return [fixed.group(0), core.group(0)]


def py_compute(p):
    """Python reference with the same pipeline as the GUI."""
    face, coupon, years = float(p["face"]), float(p["coupon"]), float(p["years"])
    freq, inst = int(p["frequency"]), p["instrument"]
    y_res = None
    if p["mode"] == "yield":
        y_res = calculate_yield(face_value=face, bond_price=float(p["price"]), annual_coupon_rate=coupon,
                                years_to_maturity=years, frequency=freq, instrument_type=inst)
        market = y_res.nominal_yield
    else:
        market = float(p["market"])
    bond = calculate_bond(face, coupon, market, years, freq, inst)
    sched = generate_amortization_schedule(face, coupon, market, years, freq, p["method"], inst)
    return bond, y_res, market, sched


def close(a, b):
    if isinstance(a, str) or isinstance(b, str) or isinstance(a, bool):
        return a == b
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def make_cases(n=600, seed=20260101):
    rnd = random.Random(seed)
    cases = []
    for _ in range(n):
        inst = rnd.choice(["term", "serial_equal_principal", "serial_equal_payment"])
        freq = rnd.choice([1, 2, 4, 12])
        # .5 years at annual frequency gives an exact half-period: Python rounds it to even
        years = rnd.choice([1, 2, 2.5, 3, 3.5, 5, 7.25, 10, 0.5, 15])
        face = rnd.choice([500, 1000, 12345.67, 100000, 30000, 1e6])
        coupon = rnd.choice([0, 0, 2.5, 4, 5, 8.75, 12])
        market = rnd.choice([0, 1, 4, 5, 6, 7.5, 10, 15, 22])
        mode = rnd.choice(["price", "price", "yield"])
        case = dict(mode=mode, instrument=inst, method=rnd.choice(["effective", "straight_line"]),
                    frequency=freq, face=face, coupon=coupon, years=years, market=market)
        if mode == "yield":
            # A true yield of exactly 0 sits on a numerical cliff in bond_calculator.py itself
            # ((1-(1+i)^-n)/i collapses for i < ~1e-14), so Python and JS may land on either side.
            if market == 0:
                continue
            try:
                price = calculate_bond(face, coupon, market, years, freq, inst).bond_price
            except ValueError:
                continue
            case["price"] = price * rnd.choice([1.0, 1.0, 0.93, 1.07])
            del case["market"]
        cases.append(case)
    # explicit error cases
    base = dict(mode="price", instrument="term", method="effective", frequency=2, face=1000, coupon=4, market=6, years=5)
    for k, v in [("face", 0), ("face", -5), ("coupon", -1), ("market", -1), ("years", 0), ("years", 0.0001)]:
        cases.append(dict(base, **{k: v}))
    cases.append(dict(base, mode="yield", price=-3, market=None))
    return cases


@unittest.skipUnless(NODE, "Node.js is not installed")
class IndexParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = make_cases()
        with tempfile.TemporaryDirectory() as tmp:
            runner = os.path.join(tmp, "runner.js")
            sources = os.path.join(tmp, "sources.json")
            with open(runner, "w") as fh:
                fh.write(RUNNER)
            with open(sources, "w") as fh:
                json.dump({"sources": extract_sources()}, fh)
            proc = subprocess.run([NODE, runner, sources], input=json.dumps(cls.cases),
                                  capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stderr
        cls.js = json.loads(proc.stdout)

    def test_every_case_matches_python(self):
        checked = errors = 0
        for case, js in zip(self.cases, self.js):
            with self.subTest(case=case):
                try:
                    bond, y_res, market, sched = py_compute(case)
                except ValueError as err:
                    errors += 1
                    self.assertFalse(js["ok"], "JS accepted input that Python rejects")
                    self.assertEqual(js["error"], str(err))
                    self.assertTrue(js["input"])
                    continue
                self.assertTrue(js["ok"], js.get("error"))
                res = js["result"]
                self.assertTrue(close(res["market_rate"], market))
                for key, want in bond.__dict__.items():
                    self.assertTrue(close(res["bond"][key], want), f"bond.{key}: {res['bond'][key]!r} != {want!r}")
                if y_res is None:
                    self.assertIsNone(res["yield"])
                else:
                    for key, want in y_res.__dict__.items():
                        if key == "iterations":      # pow() can differ by 1 ulp between libms
                            self.assertLessEqual(abs(res["yield"][key] - want), 1)
                        else:
                            self.assertTrue(close(res["yield"][key], want), f"yield.{key}")
                self.assertEqual(len(res["schedule"]), len(sched))
                for r_js, r_py in zip(res["schedule"], sched):
                    for key, want in r_py.__dict__.items():
                        self.assertTrue(close(r_js[key], want), f"period {r_py.period} {key}: {r_js[key]!r} != {want!r}")
                checked += 1
        self.assertGreater(checked, 400)
        self.assertGreaterEqual(errors, 6)

    def test_csv_text_matches_python_exporter(self):
        compared = 0
        for case, js in zip(self.cases, self.js):
            if not js["ok"] or compared >= 120:
                continue
            _, _, _, sched = py_compute(case)
            for decimals, text in zip([0, 2, 5], js["csv"]):
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, "x.csv")
                    export_schedule_to_csv(sched, path, decimals=decimals)
                    with open(path, newline="", encoding="utf-8") as fh:
                        want = fh.read()
                # JS prints -0.00 as 0.00 on purpose; Python keeps the sign of a tiny negative
                want = re.sub(r"(?<![\d.])-(0(?:\.0+)?)(?=[,\r\n])", r"\1", want)
                with self.subTest(case=case, decimals=decimals):
                    self.assertEqual(text, want)
            compared += 1
        self.assertEqual(compared, 120)


if __name__ == "__main__":
    unittest.main()
