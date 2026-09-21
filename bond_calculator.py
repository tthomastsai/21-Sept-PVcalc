"""
Bond Discount & Yield Calculator - Core Financial Logic (v2.0).

This module provides functions and data structures for:
1. Bond pricing, present value (PV), discount, premium, and cash flow calculations.
2. Term bonds (lump-sum par at maturity).
3. Serial bonds (equal principal installments with declining interest).
4. Installment accounts payable / receivable (equal total installments / amortised notes).
5. Yield to Maturity (YTM) and Effective Annual Rate (EAR) solver given bond price.
6. Amortisation schedules using the Effective Interest Method or Straight-Line Method
   (noting that the Straight-Line Method is prohibited by IFRS).
7. Exporting schedules to CSV with customisable decimal precision.
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
    pv_coupons: float               # Present value of coupon / interest stream
    pv_face_value: float            # Present value of principal repayment stream
    bond_price: float               # Present value of instrument (pv_coupons + pv_face_value)
    discount_amount: float          # face_value - bond_price (positive = discount, negative = premium)
    discount_percentage: float      # (discount_amount / face_value) * 100
    status: Literal["Discount", "Par", "Premium"]
    total_coupon_interest: float    # total interest cash paid over life
    total_cash_flows: float         # total coupons + face value
    net_interest_expense: float     # total cash paid + discount amortised / total gain
    effective_annual_rate: float = 0.0  # Annual Effective Rate (EAR / AER) in percent
    instrument_type: str = "term"   # "term", "serial_equal_principal", "serial_equal_payment"
    periodic_principal_payment: float = 0.0
    periodic_total_payment: float = 0.0


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
    """A single period in a bond or installment amortisation schedule."""
    period: int
    beginning_carrying_value: float
    interest_expense: float
    coupon_payment: float
    discount_amortization: float
    ending_carrying_value: float
    remaining_discount: float
    principal_repayment: float = 0.0
    total_cash_payment: float = 0.0
    outstanding_face_value: float = 0.0


VALID_FREQUENCIES = {
    1: "Annual (1/year)",
    2: "Semi-Annual (2/year)",
    4: "Quarterly (4/year)",
    12: "Monthly (12/year)",
}

VALID_INSTRUMENT_TYPES = {
    "term": "Term Bond (Lump-Sum Par at Maturity)",
    "serial_equal_principal": "Serial Bond (Equal Principal Installments)",
    "serial_equal_payment": "Installment Note (Equal Total Installments)",
}


def calculate_bond(
    face_value: float,
    annual_coupon_rate: float,
    annual_market_rate: float,
    years_to_maturity: float,
    frequency: int = 2,
    instrument_type: Literal["term", "serial_equal_principal", "serial_equal_payment"] = "term",
) -> BondResult:
    """
    Calculate bond present value, discount or premium, and cash flow metrics.

    :param face_value: Par / maturity value of the bond or note (e.g. 1000.0). Must be > 0.
    :param annual_coupon_rate: Annual coupon interest rate in percent (e.g. 4.0 for 4%). Must be >= 0.
    :param annual_market_rate: Annual market discount rate / required yield to maturity in percent (e.g. 6.0). Must be >= 0.
    :param years_to_maturity: Time to maturity in years (e.g. 5.0). Must be > 0.
    :param frequency: Payment frequency per year (1=Annual, 2=Semi-Annual, 4=Quarterly, 12=Monthly).
    :param instrument_type: "term" (lump-sum par), "serial_equal_principal" (serial bond),
                            or "serial_equal_payment" (installment accounts payable/receivable).
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
    if instrument_type not in VALID_INSTRUMENT_TYPES:
        raise ValueError(f"Instrument type must be one of {list(VALID_INSTRUMENT_TYPES.keys())} (got {instrument_type}).")

    total_periods = int(round(years_to_maturity * frequency))
    if total_periods < 1:
        raise ValueError("Total compounding periods must be at least 1.")

    c = annual_coupon_rate / 100.0
    r = annual_market_rate / 100.0
    periodic_market_rate = r / frequency

    if instrument_type == "serial_equal_principal":
        # Serial Bond: Equal principal repayment each period + interest on declining balance
        p_prin = face_value / total_periods
        periodic_coupon = face_value * (c / frequency)
        periodic_principal_payment = p_prin
        periodic_total_payment = p_prin + periodic_coupon

        pv_coupons = 0.0
        pv_face_value = 0.0
        total_coupon_interest = 0.0

        for t in range(1, total_periods + 1):
            f_beg = face_value - (t - 1) * p_prin
            coupon_t = f_beg * (c / frequency)
            total_coupon_interest += coupon_t

            df = 1.0 if periodic_market_rate == 0 else (1.0 + periodic_market_rate) ** (-t)
            pv_face_value += p_prin * df
            pv_coupons += coupon_t * df

        bond_price = pv_coupons + pv_face_value
        total_cash_flows = face_value + total_coupon_interest

    elif instrument_type == "serial_equal_payment":
        # Installment Accounts Payable/Receivable: Equal total periodic installment (annuity)
        if c > 0:
            rate_c = c / frequency
            pmt = face_value * rate_c / (1.0 - (1.0 + rate_c) ** (-total_periods))
        else:
            pmt = face_value / total_periods

        periodic_principal_payment = pmt
        periodic_total_payment = pmt
        periodic_coupon = pmt - (face_value / total_periods) if c > 0 else 0.0

        if periodic_market_rate == 0:
            bond_price = pmt * total_periods
        else:
            bond_price = pmt * (1.0 - (1.0 + periodic_market_rate) ** (-total_periods)) / periodic_market_rate

        total_cash_flows = pmt * total_periods
        total_coupon_interest = max(0.0, total_cash_flows - face_value)
        pv_face_value = min(face_value, bond_price)
        pv_coupons = max(0.0, bond_price - pv_face_value)

    else:  # "term" bond (Lump sum at maturity)
        periodic_coupon = face_value * (c / frequency)
        periodic_principal_payment = face_value
        periodic_total_payment = periodic_coupon

        if periodic_market_rate == 0:
            pv_face_value = face_value
            pv_coupons = periodic_coupon * total_periods
        else:
            pv_face_value = face_value / ((1.0 + periodic_market_rate) ** total_periods)
            if periodic_coupon == 0:
                pv_coupons = 0.0
            else:
                pv_coupons = periodic_coupon * (1.0 - (1.0 + periodic_market_rate) ** (-total_periods)) / periodic_market_rate

        bond_price = pv_coupons + pv_face_value
        total_coupon_interest = periodic_coupon * total_periods
        total_cash_flows = total_coupon_interest + face_value

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

    net_interest_expense = total_cash_flows - bond_price
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
        instrument_type=instrument_type,
        periodic_principal_payment=periodic_principal_payment,
        periodic_total_payment=periodic_total_payment,
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
    instrument_type: Literal["term", "serial_equal_principal", "serial_equal_payment"] = "term",
) -> YieldResult:
    """
    Find the annual nominal yield to maturity (YTM) and annual effective rate (EAR)
    given face value, bond price (present value), coupon rate, maturity/periods, frequency,
    and instrument type.

    Uses an analytical Newton-Raphson method with bracketed bisection fallback
    for guaranteed numerical convergence.
    """
    if face_value <= 0:
        raise ValueError("Face value (par value) must be greater than 0.")
    if bond_price <= 0:
        raise ValueError("Bond price (present value) must be greater than 0.")
    if annual_coupon_rate < 0:
        raise ValueError("Annual coupon rate cannot be negative.")
    if frequency not in VALID_FREQUENCIES:
        raise ValueError(f"Frequency must be one of {list(VALID_FREQUENCIES.keys())} (got {frequency}).")
    if instrument_type not in VALID_INSTRUMENT_TYPES:
        raise ValueError(f"Instrument type must be one of {list(VALID_INSTRUMENT_TYPES.keys())} (got {instrument_type}).")

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

    # Build cash flow schedule based on instrument type
    cash_flows = []
    if instrument_type == "serial_equal_principal":
        p_prin = face_value / total_periods
        for t in range(1, total_periods + 1):
            f_beg = face_value - (t - 1) * p_prin
            cash_flows.append(p_prin + f_beg * c)
    elif instrument_type == "serial_equal_payment":
        if c > 0:
            pmt = face_value * c / (1.0 - (1.0 + c) ** (-total_periods))
        else:
            pmt = face_value / total_periods
        cash_flows = [pmt] * total_periods
    else:  # "term"
        periodic_coupon = face_value * c
        for t in range(1, total_periods):
            cash_flows.append(periodic_coupon)
        cash_flows.append(periodic_coupon + face_value)

    # Par check
    if abs(bond_price - face_value) < 1e-7 and annual_coupon_rate > 0:
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

    def price_func(rate: float) -> float:
        if abs(rate) < 1e-12:
            return sum(cash_flows)
        pv = 0.0
        for t, cf in enumerate(cash_flows, start=1):
            pv += cf * ((1.0 + rate) ** (-t))
        return pv

    def price_derivative(rate: float) -> float:
        factor = 1.0 + rate
        deriv = 0.0
        for t, cf in enumerate(cash_flows, start=1):
            deriv -= t * cf * (factor ** (-(t + 1)))
        return deriv

    # Initial guess
    total_cf = sum(cash_flows)
    total_interest = total_cf - face_value
    avg_annual_int = (total_interest / years) if years > 0 else 0.0
    approx_yield = (avg_annual_int + (face_value - bond_price) / years) / ((face_value + bond_price) / 2.0)
    initial_guess = approx_yield / frequency
    if initial_guess <= -0.9 or initial_guess > 5.0:
        initial_guess = 0.05 / frequency

    # Bracket [low, high]
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
    instrument_type: Literal["term", "serial_equal_principal", "serial_equal_payment"] = "term",
) -> List[AmortizationRow]:
    """
    Generate the period-by-period amortisation schedule.

    Supports:
    - Term Bonds (carrying value converges to Par Value).
    - Serial Bonds with equal principal installments (converges to 0.00).
    - Installment Notes Payable/Receivable with equal total payments (converges to 0.00).

    Methods:
    - "effective": Effective Interest Method.
    - "straight_line": Straight-Line Method (prohibited by IFRS).
    """
    bond = calculate_bond(face_value, annual_coupon_rate, annual_market_rate, years_to_maturity, frequency, instrument_type)
    schedule: List[AmortizationRow] = []

    carrying_value = bond.bond_price
    total_periods = bond.total_periods
    periodic_rate = bond.periodic_market_rate
    total_discount = bond.discount_amount

    if instrument_type == "serial_equal_principal":
        p_prin = face_value / total_periods
        running_carrying_value = carrying_value
        periodic_amort_sl = total_discount / total_periods if total_periods > 0 else 0.0

        for period in range(1, total_periods + 1):
            beginning_val = running_carrying_value
            f_beg = face_value - (period - 1) * p_prin
            f_end = face_value - period * p_prin
            coupon_t = f_beg * (bond.annual_coupon_rate / 100.0 / frequency)
            principal_t = p_prin
            total_cash_t = principal_t + coupon_t

            if method == "straight_line":
                if period == total_periods:
                    ending_val = 0.0
                    amort = - (beginning_val - principal_t)
                    interest_expense = coupon_t + amort
                else:
                    amort = periodic_amort_sl
                    interest_expense = coupon_t + amort
                    ending_val = beginning_val + amort - principal_t
            else:  # effective interest method
                if period == total_periods:
                    ending_val = 0.0
                    interest_expense = total_cash_t - beginning_val
                    amort = interest_expense - coupon_t
                else:
                    interest_expense = beginning_val * periodic_rate
                    amort = interest_expense - coupon_t
                    ending_val = beginning_val + amort - principal_t

            remaining_discount = f_end - ending_val
            if abs(remaining_discount) < 1e-9:
                remaining_discount = 0.0
            if abs(ending_val) < 1e-9:
                ending_val = 0.0

            running_carrying_value = ending_val

            schedule.append(
                AmortizationRow(
                    period=period,
                    beginning_carrying_value=beginning_val,
                    interest_expense=interest_expense,
                    coupon_payment=coupon_t,
                    discount_amortization=amort,
                    ending_carrying_value=ending_val,
                    remaining_discount=max(0.0, remaining_discount) if bond.status != "Premium" else remaining_discount,
                    principal_repayment=principal_t,
                    total_cash_payment=total_cash_t,
                    outstanding_face_value=f_end,
                )
            )

    elif instrument_type == "serial_equal_payment":
        pmt = bond.periodic_total_payment
        running_carrying_value = carrying_value

        for period in range(1, total_periods + 1):
            beginning_val = running_carrying_value

            if period == total_periods:
                ending_val = 0.0
                principal_t = beginning_val
                interest_expense = pmt - principal_t
                coupon_t = interest_expense
                amort = interest_expense
                remaining_discount = 0.0
            else:
                interest_expense = beginning_val * periodic_rate
                principal_t = pmt - interest_expense
                ending_val = beginning_val - principal_t
                coupon_t = interest_expense
                amort = interest_expense
                remaining_discount = max(0.0, ending_val)

            if abs(ending_val) < 1e-9:
                ending_val = 0.0

            running_carrying_value = ending_val

            schedule.append(
                AmortizationRow(
                    period=period,
                    beginning_carrying_value=beginning_val,
                    interest_expense=interest_expense,
                    coupon_payment=coupon_t,
                    discount_amortization=amort,
                    ending_carrying_value=ending_val,
                    remaining_discount=remaining_discount,
                    principal_repayment=principal_t,
                    total_cash_payment=pmt,
                    outstanding_face_value=ending_val,
                )
            )

    else:  # "term" bond
        periodic_coupon = bond.periodic_coupon_payment
        if method == "straight_line":
            periodic_amortization = total_discount / total_periods if total_periods > 0 else 0.0
            running_carrying_value = carrying_value

            for period in range(1, total_periods + 1):
                beginning_val = running_carrying_value
                if period == total_periods:
                    amort = face_value - beginning_val
                    ending_val = face_value
                    principal_t = face_value
                    total_cash_t = periodic_coupon + face_value
                else:
                    amort = periodic_amortization
                    ending_val = beginning_val + amort
                    principal_t = 0.0
                    total_cash_t = periodic_coupon

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
                        principal_repayment=principal_t,
                        total_cash_payment=total_cash_t,
                        outstanding_face_value=face_value,
                    )
                )

        else:  # effective interest method
            running_carrying_value = carrying_value
            for period in range(1, total_periods + 1):
                beginning_val = running_carrying_value

                if period == total_periods:
                    amort = face_value - beginning_val
                    interest_expense = periodic_coupon + amort
                    ending_val = face_value
                    principal_t = face_value
                    total_cash_t = periodic_coupon + face_value
                else:
                    interest_expense = beginning_val * periodic_rate
                    amort = interest_expense - periodic_coupon
                    ending_val = beginning_val + amort
                    principal_t = 0.0
                    total_cash_t = periodic_coupon

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
                        principal_repayment=principal_t,
                        total_cash_payment=total_cash_t,
                        outstanding_face_value=face_value,
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
            "Principal Repaid",
            "Total Payment",
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
                "Principal Repaid": f"{row.principal_repayment:.{decimals}f}",
                "Total Payment": f"{row.total_cash_payment:.{decimals}f}",
                "Discount Amortisation": f"{row.discount_amortization:.{decimals}f}",
                "Ending Carrying Value": f"{row.ending_carrying_value:.{decimals}f}",
                "Remaining Unamortised Discount": f"{row.remaining_discount:.{decimals}f}",
            })
