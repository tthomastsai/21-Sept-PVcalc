"""
Bond Discount & Yield Calculator - Core Financial Logic (v2.0).

This module provides functions and data structures for:
1. Bond pricing, present value (PV), discount, premium, and cash flow calculations.
2. Yield to Maturity (YTM) and Effective Annual Rate (EAR) solver given bond price.
3. Amortisation schedules using the Effective Interest Method or Straight-Line Method
   (noting that the Straight-Line Method is prohibited by IFRS).
4. Exporting schedules to CSV with customisable decimal precision.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional
import csv


@dataclass
class BondResult:
    """Detailed summary of bond pricing, yields, and discount calculations."""
    face_value: float
    annual_coupon_rate: float       # In percent (e.g. 5.0 for 5%)
    annual_market_rate: float       # In percent (e.g. 7.0 for 7%) - nominal YTM
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
    net_interest_expense: float     # total cash paid + discount amortised
    effective_annual_rate: float = 0.0  # Annual Effective Rate (EAR / AER) in percent


@dataclass
class YieldResult:
    """Detailed result of calculating yield given bond price and characteristics."""
    nominal_yield: float           # Annual nominal yield (YTM) in percent (e.g. 6.0 for 6%)
    effective_annual_rate: float   # Annual effective yield rate (EAR) in percent (e.g. 6.09%)
    periodic_yield: float          # Periodic discount rate (decimal, e.g. 0.03)
    total_periods: int             # Total compounding periods
    years_to_maturity: float       # Years to maturity
    iterations: int                # Number of iterations used in numerical solver


@dataclass
class AmortizationRow:
    """A single period in a bond discount/premium amortisation schedule."""
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

    bond_price = pv_coupons + pv_face_value
    discount_amount = face_value - bond_price
    discount_percentage = (discount_amount / face_value) * 100.0

    if abs(discount_amount) < 0.005:
        status: Literal["Discount", "Par", "Premium"] = "Par"
        discount_amount = 0.0
        discount_percentage = 0.0
    elif discount_amount > 0:
        status = "Discount"
    else:
        status = "Premium"

    total_coupon_interest = periodic_coupon * total_periods
    total_cash_flows = total_coupon_interest + face_value
    net_interest_expense = total_coupon_interest + discount_amount

    # Annual Effective Rate (EAR / AER)
    effective_annual_rate = ((1.0 + periodic_market_rate) ** frequency - 1.0) * 100.0

    return BondResult(
        face_value=face_value,
        annual_coupon_rate=annual_coupon_rate,
        annual_market_rate=annual_market_rate,
        years_to_maturity=years_to_maturity,
        frequency=frequency,
        total_periods=total_periods,
        periodic_coupon_payment=periodic_coupon,
        periodic_market_rate=periodic_market_rate,
        pv_coupons=pv_coupons,
        pv_face_value=pv_face_value,
        bond_price=bond_price,
        discount_amount=discount_amount,
        discount_percentage=discount_percentage,
        status=status,
        total_coupon_interest=total_coupon_interest,
        total_cash_flows=total_cash_flows,
        net_interest_expense=net_interest_expense,
        effective_annual_rate=effective_annual_rate,
    )


def calculate_yield(
    face_value: float,
    bond_price: float,
    annual_coupon_rate: float,
    years_to_maturity: Optional[float] = None,
    periods: Optional[int] = None,
    frequency: int = 2,
    tolerance: float = 1e-9,
    max_iterations: int = 100,
) -> YieldResult:
    """
    Find the annual nominal yield to maturity (YTM) and annual effective rate (EAR)
    given face value, bond price (present value), coupon rate, maturity/periods, and frequency.

    Uses an analytical Newton-Raphson method with bracketed bisection fallback
    for guaranteed numerical convergence.

    :param face_value: Par value (e.g. 1000.0). Must be > 0.
    :param bond_price: Current market price / present value (e.g. 914.70). Must be > 0.
    :param annual_coupon_rate: Annual coupon rate in percent (e.g. 4.0 for 4%). Must be >= 0.
    :param years_to_maturity: Years to maturity (e.g. 5.0).
    :param periods: Total compounding periods (e.g. 10). Either years_to_maturity or periods must be specified.
    :param frequency: Compounding/payment frequency per year (1, 2, 4, 12).
    :param tolerance: Solver absolute convergence tolerance.
    :param max_iterations: Maximum number of solver iterations.
    :return: YieldResult containing nominal YTM (%), effective annual rate (%), periodic rate, and iterations.
    :raises ValueError: On invalid inputs or inability to solve.
    """
    if face_value <= 0:
        raise ValueError("Face value (par value) must be greater than 0.")
    if bond_price <= 0:
        raise ValueError("Bond price (present value) must be greater than 0.")
    if annual_coupon_rate < 0:
        raise ValueError("Annual coupon rate cannot be negative.")
    if frequency not in VALID_FREQUENCIES:
        raise ValueError(f"Frequency must be one of {list(VALID_FREQUENCIES.keys())} (got {frequency}).")

    if periods is not None:
        total_periods = int(periods)
        if total_periods < 1:
            raise ValueError("Total compounding periods must be at least 1.")
        years = total_periods / frequency
    elif years_to_maturity is not None:
        if years_to_maturity <= 0:
            raise ValueError("Years to maturity must be greater than 0.")
        total_periods = int(round(years_to_maturity * frequency))
        if total_periods < 1:
            raise ValueError("Total compounding periods must be at least 1.")
        years = years_to_maturity
    else:
        raise ValueError("Either years_to_maturity or periods must be provided.")

    c = (annual_coupon_rate / 100.0) / frequency
    periodic_coupon = face_value * c

    # Case 1: Zero-coupon bond - analytical closed-form solution
    if periodic_coupon == 0:
        # P = F / (1 + i)^n => 1 + i = (F / P)^(1 / n)
        periodic_yield = (face_value / bond_price) ** (1.0 / total_periods) - 1.0
        nominal_yield = periodic_yield * frequency * 100.0
        effective_annual_rate = ((1.0 + periodic_yield) ** frequency - 1.0) * 100.0
        return YieldResult(
            nominal_yield=nominal_yield,
            effective_annual_rate=effective_annual_rate,
            periodic_yield=periodic_yield,
            total_periods=total_periods,
            years_to_maturity=years,
            iterations=1,
        )

    # Case 2: Trading exactly at par
    if abs(bond_price - face_value) < 1e-7:
        periodic_yield = c
        nominal_yield = annual_coupon_rate
        effective_annual_rate = ((1.0 + periodic_yield) ** frequency - 1.0) * 100.0
        return YieldResult(
            nominal_yield=nominal_yield,
            effective_annual_rate=effective_annual_rate,
            periodic_yield=periodic_yield,
            total_periods=total_periods,
            years_to_maturity=years,
            iterations=1,
        )

    # Case 3: Coupon bond - iterative solver
    def price_func(rate: float) -> float:
        if abs(rate) < 1e-12:
            return periodic_coupon * total_periods + face_value
        factor = (1.0 + rate) ** (-total_periods)
        return periodic_coupon * (1.0 - factor) / rate + face_value * factor

    def price_derivative(rate: float) -> float:
        factor = 1.0 + rate
        # Lump sum derivative
        deriv = -total_periods * face_value * (factor ** (-(total_periods + 1)))
        # Coupon stream derivative: -sum_{k=1}^n k * C * (1 + rate)^(-(k+1))
        for k in range(1, total_periods + 1):
            deriv -= k * periodic_coupon * (factor ** (-(k + 1)))
        return deriv

    # Approximate initial guess (Fabozzi / Malkiel approximation)
    initial_guess = (periodic_coupon + (face_value - bond_price) / total_periods) / ((face_value + bond_price) / 2.0)
    if initial_guess <= -0.9 or initial_guess > 5.0:
        initial_guess = 0.05 / frequency

    # Bracket [low, high] for bisection safety
    # Price is monotonically decreasing with respect to rate for rate > -1
    low = -0.999
    high = max(1.0, initial_guess * 2.0)
    while price_func(high) > bond_price:
        high = high * 2.0 + 1.0

    current_i = initial_guess
    iterations = 0

    for it in range(1, max_iterations + 1):
        iterations = it
        f_val = price_func(current_i) - bond_price
        if abs(f_val) < tolerance:
            break

        f_prime = price_derivative(current_i)
        if f_prime != 0:
            next_i = current_i - f_val / f_prime
        else:
            next_i = (low + high) / 2.0

        if not (low < next_i < high):
            next_i = (low + high) / 2.0

        # Update brackets
        f_next = price_func(next_i) - bond_price
        if f_next > 0:
            low = next_i
        else:
            high = next_i

        if abs(next_i - current_i) < tolerance:
            current_i = next_i
            break

        current_i = next_i

    nominal_yield = current_i * frequency * 100.0
    effective_annual_rate = ((1.0 + current_i) ** frequency - 1.0) * 100.0

    return YieldResult(
        nominal_yield=nominal_yield,
        effective_annual_rate=effective_annual_rate,
        periodic_yield=current_i,
        total_periods=total_periods,
        years_to_maturity=years,
        iterations=iterations,
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
    Generate the period-by-period bond amortisation schedule.

    Supports:
    - "effective": Effective Interest Method.
    - "straight_line": Straight-Line Method (prohibited by IFRS).

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
            if abs(remaining_discount) < 1e-9:
                remaining_discount = 0.0
            running_carrying_value = ending_val

            schedule.append(
                AmortizationRow(
                    period=period,
                    beginning_carrying_value=beginning_val,
                    interest_expense=interest_expense,
                    coupon_payment=periodic_coupon,
                    discount_amortization=amort,
                    ending_carrying_value=ending_val,
                    remaining_discount=max(0.0, remaining_discount) if bond.status != "Premium" else remaining_discount,
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
            if abs(remaining_discount) < 1e-9:
                remaining_discount = 0.0
            running_carrying_value = ending_val

            schedule.append(
                AmortizationRow(
                    period=period,
                    beginning_carrying_value=beginning_val,
                    interest_expense=interest_expense,
                    coupon_payment=periodic_coupon,
                    discount_amortization=amort,
                    ending_carrying_value=ending_val,
                    remaining_discount=max(0.0, remaining_discount) if bond.status != "Premium" else remaining_discount,
                )
            )

    return schedule


def export_schedule_to_csv(
    schedule: List[AmortizationRow], filepath: str, decimals: int = 2
) -> None:
    """
    Export an amortisation schedule to a CSV file.

    :param schedule: List of AmortizationRow records.
    :param filepath: Destination file path.
    :param decimals: Number of decimal places to format numerical amounts.
    """
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "Period",
            "Beginning Carrying Value",
            "Interest Expense",
            "Coupon Payment",
            "Discount Amortisation",
            "Ending Carrying Value",
            "Remaining Unamortised Discount",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in schedule:
            writer.writerow({
                "Period": row.period,
                "Beginning Carrying Value": f"{row.beginning_carrying_value:.{decimals}f}",
                "Interest Expense": f"{row.interest_expense:.{decimals}f}",
                "Coupon Payment": f"{row.coupon_payment:.{decimals}f}",
                "Discount Amortisation": f"{row.discount_amortization:.{decimals}f}",
                "Ending Carrying Value": f"{row.ending_carrying_value:.{decimals}f}",
                "Remaining Unamortised Discount": f"{row.remaining_discount:.{decimals}f}",
            })
