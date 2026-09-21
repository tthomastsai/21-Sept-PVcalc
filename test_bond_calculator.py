"""
Unit tests for bond_calculator.py (v2.0)
"""

import os
import sys
import tempfile
import unittest

# Ensure the local directory is on sys.path regardless of execution CWD
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bond_calculator import (
    calculate_bond,
    calculate_yield,
    generate_amortization_schedule,
    export_schedule_to_csv,
    VALID_FREQUENCIES,
    BondResult,
    YieldResult,
)


class TestBondCalculator(unittest.TestCase):

    def test_standard_discount_bond(self):
        # 5 years, $1,000 face value, 4% annual coupon, 6% market rate, semi-annual (freq=2)
        # 10 periods, coupon payment = $20, periodic rate = 3%
        # PV of coupons = 20 * (1 - 1.03^-10) / 0.03 = 170.60
        # PV of face value = 1000 / (1.03^10) = 744.09
        # Price = 914.70, Discount = 85.30 (approx 8.53%)
        res = calculate_bond(
            face_value=1000.0,
            annual_coupon_rate=4.0,
            annual_market_rate=6.0,
            years_to_maturity=5.0,
            frequency=2,
        )

        self.assertEqual(res.status, "Discount")
        self.assertEqual(res.total_periods, 10)
        self.assertEqual(res.periodic_coupon_payment, 20.0)
        self.assertAlmostEqual(res.periodic_market_rate, 0.03, places=4)
        self.assertAlmostEqual(res.bond_price, 914.70, places=2)
        self.assertAlmostEqual(res.discount_amount, 85.30, places=2)
        self.assertAlmostEqual(res.discount_percentage, 8.53, places=2)
        self.assertEqual(res.total_coupon_interest, 200.0)
        self.assertEqual(res.total_cash_flows, 1200.0)
        self.assertAlmostEqual(res.net_interest_expense, 285.30, places=2)
        # Effective annual rate: (1 + 0.03)^2 - 1 = 6.09%
        self.assertAlmostEqual(res.effective_annual_rate, 6.09, places=2)

    def test_par_bond(self):
        # When coupon rate equals market rate, bond is priced at par ($1,000)
        res = calculate_bond(
            face_value=1000.0,
            annual_coupon_rate=5.0,
            annual_market_rate=5.0,
            years_to_maturity=10.0,
            frequency=2,
        )

        self.assertEqual(res.status, "Par")
        self.assertAlmostEqual(res.bond_price, 1000.0, places=2)
        self.assertAlmostEqual(res.discount_amount, 0.0, places=2)
        self.assertAlmostEqual(res.discount_percentage, 0.0, places=2)
        self.assertAlmostEqual(res.effective_annual_rate, ((1.025**2) - 1.0) * 100, places=3)

    def test_premium_bond(self):
        # When coupon rate > market rate, bond trades at a premium
        res = calculate_bond(
            face_value=1000.0,
            annual_coupon_rate=8.0,
            annual_market_rate=5.0,
            years_to_maturity=3.0,
            frequency=1,
        )

        self.assertEqual(res.status, "Premium")
        self.assertGreater(res.bond_price, 1000.0)
        self.assertLess(res.discount_amount, 0.0)

    def test_zero_coupon_bond(self):
        # Zero coupon bond has no periodic coupon payments
        res = calculate_bond(
            face_value=1000.0,
            annual_coupon_rate=0.0,
            annual_market_rate=5.0,
            years_to_maturity=2.0,
            frequency=1,
        )

        # Price = 1000 / (1.05^2) = 907.03
        self.assertEqual(res.status, "Discount")
        self.assertEqual(res.periodic_coupon_payment, 0.0)
        self.assertEqual(res.pv_coupons, 0.0)
        self.assertAlmostEqual(res.bond_price, 907.03, places=2)
        self.assertAlmostEqual(res.discount_amount, 92.97, places=2)

    def test_frequency_variations(self):
        # Annual
        res_ann = calculate_bond(1000, 6, 8, 2, frequency=1)
        self.assertEqual(res_ann.total_periods, 2)
        self.assertEqual(res_ann.periodic_coupon_payment, 60.0)

        # Quarterly
        res_qtr = calculate_bond(1000, 6, 8, 2, frequency=4)
        self.assertEqual(res_qtr.total_periods, 8)
        self.assertEqual(res_qtr.periodic_coupon_payment, 15.0)

        # Monthly
        res_mth = calculate_bond(1000, 6, 8, 2, frequency=12)
        self.assertEqual(res_mth.total_periods, 24)
        self.assertEqual(res_mth.periodic_coupon_payment, 5.0)

    def test_calculate_yield_discount_bond(self):
        # Given bond price = 914.70, Face = 1000, Coupon = 4%, Years = 5, Freq = 2
        # Solved nominal yield should be ~6.00%, effective rate ~6.09%
        y_res = calculate_yield(
            face_value=1000.0,
            bond_price=914.70,
            annual_coupon_rate=4.0,
            years_to_maturity=5.0,
            frequency=2,
        )
        self.assertAlmostEqual(y_res.nominal_yield, 6.00, places=2)
        self.assertAlmostEqual(y_res.effective_annual_rate, 6.09, places=2)
        self.assertAlmostEqual(y_res.periodic_yield, 0.03, places=4)
        self.assertEqual(y_res.total_periods, 10)

        # Test passing periods directly
        y_res_p = calculate_yield(
            face_value=1000.0,
            bond_price=914.70,
            annual_coupon_rate=4.0,
            periods=10,
            frequency=2,
        )
        self.assertAlmostEqual(y_res_p.nominal_yield, 6.00, places=2)
        self.assertEqual(y_res_p.years_to_maturity, 5.0)

    def test_calculate_yield_par_bond(self):
        y_res = calculate_yield(
            face_value=1000.0,
            bond_price=1000.0,
            annual_coupon_rate=5.5,
            years_to_maturity=10.0,
            frequency=2,
        )
        self.assertAlmostEqual(y_res.nominal_yield, 5.50, places=4)
        self.assertAlmostEqual(y_res.effective_annual_rate, ((1 + 0.055 / 2) ** 2 - 1) * 100, places=3)

    def test_calculate_yield_premium_bond(self):
        # 3 years, 8% coupon, 5% market yield, annual freq
        b_res = calculate_bond(1000.0, 8.0, 5.0, 3.0, frequency=1)
        # Invert: pass calculated price to yield solver
        y_res = calculate_yield(
            face_value=1000.0,
            bond_price=b_res.bond_price,
            annual_coupon_rate=8.0,
            years_to_maturity=3.0,
            frequency=1,
        )
        self.assertAlmostEqual(y_res.nominal_yield, 5.0, places=4)
        self.assertAlmostEqual(y_res.effective_annual_rate, 5.0, places=4)

    def test_calculate_yield_zero_coupon(self):
        # 2 years, 0% coupon, market rate 5% -> price ~907.03
        y_res = calculate_yield(
            face_value=1000.0,
            bond_price=907.029478,
            annual_coupon_rate=0.0,
            years_to_maturity=2.0,
            frequency=1,
        )
        self.assertAlmostEqual(y_res.nominal_yield, 5.00, places=3)
        self.assertAlmostEqual(y_res.effective_annual_rate, 5.00, places=3)

    def test_calculate_yield_multi_frequencies(self):
        for freq in [1, 2, 4, 12]:
            b_res = calculate_bond(1000.0, 5.0, 7.5, 4.0, frequency=freq)
            y_res = calculate_yield(1000.0, b_res.bond_price, 5.0, years_to_maturity=4.0, frequency=freq)
            self.assertAlmostEqual(y_res.nominal_yield, 7.5, places=3)

    def test_calculate_yield_validation(self):
        with self.assertRaises(ValueError):
            calculate_yield(0, 950, 5, years_to_maturity=5)  # face value 0
        with self.assertRaises(ValueError):
            calculate_yield(1000, 0, 5, years_to_maturity=5)  # price 0
        with self.assertRaises(ValueError):
            calculate_yield(1000, -100, 5, years_to_maturity=5)  # negative price
        with self.assertRaises(ValueError):
            calculate_yield(1000, 950, -1, years_to_maturity=5)  # negative coupon
        with self.assertRaises(ValueError):
            calculate_yield(1000, 950, 5, years_to_maturity=-2)  # negative years
        with self.assertRaises(ValueError):
            calculate_yield(1000, 950, 5, periods=0)  # periods 0
        with self.assertRaises(ValueError):
            calculate_yield(1000, 950, 5)  # neither periods nor years
        with self.assertRaises(ValueError):
            calculate_yield(1000, 950, 5, years_to_maturity=5, frequency=5)  # invalid freq

    def test_effective_interest_amortization_schedule(self):
        schedule = generate_amortization_schedule(
            face_value=1000.0,
            annual_coupon_rate=4.0,
            annual_market_rate=6.0,
            years_to_maturity=5.0,
            frequency=2,
            method="effective",
        )

        self.assertEqual(len(schedule), 10)
        # First period beginning carrying value equals initial bond price
        self.assertAlmostEqual(schedule[0].beginning_carrying_value, 914.70, places=2)
        # First period coupon payment
        self.assertEqual(schedule[0].coupon_payment, 20.0)
        # Ending carrying value of final period converges exactly to face value
        self.assertEqual(schedule[-1].ending_carrying_value, 1000.0)
        # Remaining discount at maturity is zero
        self.assertEqual(schedule[-1].remaining_discount, 0.0)

        # Total discount amortized should equal initial discount amount
        total_amortized = sum(r.discount_amortization for r in schedule)
        self.assertAlmostEqual(total_amortized, 85.30, places=1)

    def test_straight_line_amortization_schedule(self):
        schedule = generate_amortization_schedule(
            face_value=1000.0,
            annual_coupon_rate=4.0,
            annual_market_rate=6.0,
            years_to_maturity=5.0,
            frequency=2,
            method="straight_line",
        )

        self.assertEqual(len(schedule), 10)
        # For straight line, amortizations except possible final cent adjust should be ~8.53
        for row in schedule[:-1]:
            self.assertAlmostEqual(row.discount_amortization, 8.53, delta=0.01)

        # Final ending carrying value equals face value
        self.assertEqual(schedule[-1].ending_carrying_value, 1000.0)

    def test_csv_export(self):
        schedule = generate_amortization_schedule(1000, 4, 6, 2, frequency=2)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            temp_path = tf.name

        try:
            export_schedule_to_csv(schedule, temp_path, decimals=4)
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Period", content)
                self.assertIn("Beginning Carrying Value", content)
                self.assertIn("Ending Carrying Value", content)
                self.assertIn("Discount Amortisation", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            calculate_bond(0, 5, 5, 5)  # face value 0
        with self.assertRaises(ValueError):
            calculate_bond(-1000, 5, 5, 5)  # negative face value
        with self.assertRaises(ValueError):
            calculate_bond(1000, -2, 5, 5)  # negative coupon
        with self.assertRaises(ValueError):
            calculate_bond(1000, 5, -1, 5)  # negative market rate
        with self.assertRaises(ValueError):
            calculate_bond(1000, 5, 5, 0)  # zero years
        with self.assertRaises(ValueError):
            calculate_bond(1000, 5, 5, 5, frequency=3)  # unsupported frequency


if __name__ == "__main__":
    unittest.main()
