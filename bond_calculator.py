"""
Bond Discount Calculator - Core Financial Logic.

This module provides functions and data structures for calculating bond pricing,
discounts, premiums, yields, cash flows, and generating full amortization schedules
using either the Effective Interest Method or the Straight-Line Method.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional
import csv


@dataclass
class BondResult:
    """Detailed summary of bond pricing and discount calculations."""
    face_value: float
    annual_coupon_rate: float       # In percent (e.g. 5.0 for 5%)
    annual_market_rate: float       # In percent (e.g. 7.0 for 7%)
    years_to_maturity: float
    frequency: int                  # 1=Annual, 2=Semi-Annual, 4=Quarterly, 12=Monthly
    total_periods: int
    periodic_coupon_payment: float
    periodic_market_rate: float     # Decimal (e.g. 0.035 for 3.5%)
    pv_coupons: float               # Present value of annuity payments
    pv_face_value: float            # Present value of lump-sum par value
    bond_price: float               # Present value of bond (pv_coupons + pv_face_value)
    discount_amount: float          # face_value - bond_price (positive = discount, negative = premium)
    discount_percentage: float      # (discount_amount / face_value) * 100
    status: Literal["Discount", "Par", "Premium"]
    total_coupon_interest: float    # total coupon cash paid over life
    total_cash_flows: float         # total coupons + face value
    net_interest_expense: float     # total cash paid + discount amortized


@dataclass
class AmortizationRow:
    """A single period in a bond discount/premium amortization schedule."""
    period: int
    beginning_carrying_value: float
    interest_expense: float
    coupon_payment: float
    discount_amortization: float
    ending_carrying_value: float
    remaining_discount: float


VALID_FREQUENCIES = {
    1: "Annual (1/year)",
    2: "Semi-Annual (2/year)",
    4: "Quarterly (4/year)",
    12: "Monthly (12/year)",
}


def calculate_bond(
    face_value: float,
    annual_coupon_rate: float,
    annual_market_rate: float,
    years_to_maturity: float,
    frequency: int = 2,
) -> BondResult:
    """
    Calculate bond present value, discount or premium, and cash flow metrics.

    :param face_value: Par / maturity value of the bond (e.g. 1000.0). Must be > 0.
    :param annual_coupon_rate: Annual coupon interest rate in percent (e.g. 4.0 for 4%). Must be >= 0.
    :param annual_market_rate: Annual market discount rate / required yield to maturity in percent (e.g. 6.0). Must be >= 0.
    :param years_to_maturity: Time to maturity in years (e.g. 5.0). Must be > 0.
    :param frequency: Payment frequency per year (1=Annual, 2=Semi-Annual, 4=Quarterly, 12=Monthly).
    :return: BondResult dataclass instance.
    :raises ValueError: If parameters are outside valid numerical ranges.
    """
    if face_value <= 0:
        raise ValueError("Face value (par value) must be greater than 0.")
    if annual_coupon_rate < 0:
        raise ValueError("Annual coupon rate cannot be negative.")
    if annual_market_rate < 0:
        raise ValueError("Annual market rate cannot be negative.")
    if years_to_maturity <= 0:
        raise ValueError("Years to maturity must be greater than 0.")
    if frequency not in VALID_FREQUENCIES:
        raise ValueError(f"Frequency must be one of {list(VALID_FREQUENCIES.keys())} (got {frequency}).")

    total_periods = int(round(years_to_maturity * frequency))
    if total_periods < 1:
        raise ValueError("Total compounding periods must be at least 1.")

    c = annual_coupon_rate / 100.0
    r = annual_market_rate / 100.0

    periodic_market_rate = r / frequency
    periodic_coupon = face_value * (c / frequency)

    # Present Value of Face Value (Lump Sum)
    if periodic_market_rate == 0:
        pv_face_value = face_value
    else:
        pv_face_value = face_value / ((1.0 + periodic_market_rate) ** total_periods)

    # Present Value of Coupons (Ordinary Annuity)
    if periodic_coupon == 0:
        pv_coupons = 0.0
    elif periodic_market_rate == 0:
        pv_coupons = periodic_coupon * total_periods
    else:
        pv_coupons = periodic_coupon * (1.0 - (1.0 + periodic_market_rate) ** (-total_periods)) / periodic_market_rate

    bond_price = round(pv_coupons + pv_face_value, 4)
    discount_amount = round(face_value - bond_price, 4)
    discount_percentage = round((discount_amount / face_value) * 100.0, 4)

    if abs(discount_amount) < 0.005:
        status: Literal["Discount", "Par", "Premium"] = "Par"
        discount_amount = 0.0
        discount_percentage = 0.0
    elif discount_amount > 0:
        status = "Discount"
    else:
        status = "Premium"

    total_coupon_interest = round(periodic_coupon * total_periods, 4)
    total_cash_flows = round(total_coupon_interest + face_value, 4)
    net_interest_expense = round(total_coupon_interest + discount_amount, 4)

    return BondResult(
        face_value=face_value,
        annual_coupon_rate=annual_coupon_rate,
        annual_market_rate=annual_market_rate,
        years_to_maturity=years_to_maturity,
        frequency=frequency,
        total_periods=total_periods,
        periodic_coupon_payment=round(periodic_coupon, 4),
        periodic_market_rate=round(periodic_market_rate, 6),
        pv_coupons=round(pv_coupons, 2),
        pv_face_value=round(pv_face_value, 2),
        bond_price=round(bond_price, 2),
        discount_amount=round(discount_amount, 2),
        discount_percentage=round(discount_percentage, 2),
        status=status,
        total_coupon_interest=round(total_coupon_interest, 2),
        total_cash_flows=round(total_cash_flows, 2),
        net_interest_expense=round(net_interest_expense, 2),
    )


def generate_amortization_schedule(
    face_value: float,
    annual_coupon_rate: float,
    annual_market_rate: float,
    years_to_maturity: float,
    frequency: int = 2,
    method: Literal["effective", "straight_line"] = "effective",
) -> List[AmortizationRow]:
    """
    Generate the period-by-period bond amortization schedule.

    Supports:
    - "effective": Effective Interest Method (US GAAP / IFRS requirement).
    - "straight_line": Straight-Line Amortization Method.

    :return: List of AmortizationRow items for periods 1 to N.
    """
    bond = calculate_bond(face_value, annual_coupon_rate, annual_market_rate, years_to_maturity, frequency)
    schedule: List[AmortizationRow] = []

    carrying_value = bond.bond_price
    total_periods = bond.total_periods
    periodic_coupon = bond.periodic_coupon_payment
    periodic_rate = bond.periodic_market_rate
    total_discount = bond.discount_amount

    if method == "straight_line":
        periodic_amortization = total_discount / total_periods if total_periods > 0 else 0.0
        running_carrying_value = carrying_value

        for period in range(1, total_periods + 1):
            beginning_val = running_carrying_value
            if period == total_periods:
                # Final period adjustment to absorb rounding and hit exact face value
                amort = face_value - beginning_val
                ending_val = face_value
            else:
                amort = periodic_amortization
                ending_val = beginning_val + amort

            interest_expense = periodic_coupon + amort
            remaining_discount = face_value - ending_val
            running_carrying_value = ending_val

            schedule.append(
                AmortizationRow(
                    period=period,
                    beginning_carrying_value=round(beginning_val, 2),
                    interest_expense=round(interest_expense, 2),
                    coupon_payment=round(periodic_coupon, 2),
                    discount_amortization=round(amort, 2),
                    ending_carrying_value=round(ending_val, 2),
                    remaining_discount=round(max(0.0, remaining_discount) if bond.status != "Premium" else remaining_discount, 2),
                )
            )

    else:  # effective interest method
        running_carrying_value = carrying_value
        for period in range(1, total_periods + 1):
            beginning_val = running_carrying_value

            if period == total_periods:
                # Final period: adjust amortization so carrying value converges exactly to face value
                amort = face_value - beginning_val
                interest_expense = periodic_coupon + amort
                ending_val = face_value
            else:
                interest_expense = beginning_val * periodic_rate
                amort = interest_expense - periodic_coupon
                ending_val = beginning_val + amort

            remaining_discount = face_value - ending_val
            running_carrying_value = ending_val

            schedule.append(
                AmortizationRow(
                    period=period,
                    beginning_carrying_value=round(beginning_val, 2),
                    interest_expense=round(interest_expense, 2),
                    coupon_payment=round(periodic_coupon, 2),
                    discount_amortization=round(amort, 2),
                    ending_carrying_value=round(ending_val, 2),
                    remaining_discount=round(max(0.0, remaining_discount) if bond.status != "Premium" else remaining_discount, 2),
                )
            )

    return schedule


def export_schedule_to_csv(schedule: List[AmortizationRow], filepath: str) -> None:
    """
    Export an amortization schedule to a CSV file.

    :param schedule: List of AmortizationRow records.
    :param filepath: Destination file path.
    """
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "Period",
            "Beginning Carrying Value ($)",
            "Interest Expense ($)",
            "Coupon Payment ($)",
            "Discount Amortization ($)",
            "Ending Carrying Value ($)",
            "Remaining Unamortized Discount ($)",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in schedule:
            writer.writerow({
                "Period": row.period,
                "Beginning Carrying Value ($)": f"{row.beginning_carrying_value:.2f}",
                "Interest Expense ($)": f"{row.interest_expense:.2f}",
                "Coupon Payment ($)": f"{row.coupon_payment:.2f}",
                "Discount Amortization ($)": f"{row.discount_amortization:.2f}",
                "Ending Carrying Value ($)": f"{row.ending_carrying_value:.2f}",
                "Remaining Unamortized Discount ($)": f"{row.remaining_discount:.2f}",
            })
