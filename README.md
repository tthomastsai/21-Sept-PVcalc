# Bond & Installment Accounts Calculator (v2.0.1)

Value long-term payables / receivables with live yield solving and amortisation.

---

## Key Features

- **IFRS 9 (*Financial Instruments*) Terminology Alignment**:
  - Measurement at **amortised cost** using the **effective interest method** and **effective interest rate (EIR)**.
  - Consistent use of **Carrying Amount** (rather than carrying value or book value) across KPI metrics, amortisation tables, CLI, and CSV exports.
  - Straight-line amortisation explicitly marked as **(prohibited by IFRS)**.
- **Debt & Instrument Types**:
  1. **Term Bond (Lump-Sum Par at Maturity)**: Standard bonds where periodic coupons are paid on full face value, and the entire principal $F$ is repaid at final maturity. Carrying amount converges to par $F$.
  2. **Serial Bond (Equal Principal Installments)**: Principal is retired in equal installments ($F / n$) each period. Coupon interest decreases over time as principal is paid down. Carrying amount converges to **$0.00**.
  3. **Installment Accounts Payable / Receivable (Equal Total Installments)**: Equal periodic payments ($PMT$, fully amortised note/annuity). Defaults to **Zero-Coupon / Non-Interest-Bearing** trade notes discounted at market yield $r$, or supports interest-bearing installment notes ($c > 0$). Carrying amount converges to **$0.00**.
- **Dual Calculation Modes**:
  - **Mode 1 (PV Mode)**: Calculate Present Value / Initial Carrying Amount given Market Yield.
  - **Mode 2 (Yield Mode)**: Solve Nominal Yield (YTM) and Annual Effective Rate (EAR / AER) given Present Value / Price.
- **Morandi Aesthetic Palette**:
  - Desktop GUI styled in Giorgio Morandi-inspired low-saturation, soothing earthy tones (warm greige canvas `#f4f1ea`, muted slate header `#4d5656`, dusty sage buttons `#6c8276`, and terracotta/olive/mauve KPI accents).
- **Amortisation Schedules**:
  - **Effective Interest Method**
  - **Straight-Line Method (prohibited by IFRS)**
  - Detailed period-by-period table displaying: Period, Beg Carrying Amount, Interest Expense, Coupon / Stated Interest, Principal Repaid, Total Cash Paid, Discount Amortisation, and End Carrying Amount.
- **British English Localization**:
  - Standardised on British English (*Amortisation*, *Unamortised Discount*, *Colour*).
- **Real-Time Decimal Precision Adjuster**:
  - `[ ➖ Less ]` and `[ ➕ Add ]` controls dynamically format all numbers from **0 up to 8 decimal places** without precision loss.
- **Export & Presets**:
  - One-click **Export to CSV** matching the active decimal precision with IFRS 9 headers.
  - Quick presets for Term Bonds, Serial Bonds, Installment Trade Notes, Par Bonds, and Yield Solvers.
- **Automated Unit Tests**:
  - 19 automated unit tests verifying term bonds, serial bonds, installment notes, yield solving, schedule convergence, and error bounds.

---

## How to Run

### 1. Launch Desktop GUI (Default)
```bash
python bond_app.py
```
*(or run `python app.py`)*

### 2. Launch Interactive CLI Mode
```bash
python bond_app.py --cli
```

### 3. Run Automated Tests
```bash
python -m unittest test_bond_calculator.py -v
```

---

## Financial Formulas

### 1. Term Bond (Lump-Sum at Maturity)

$$P(i) = C \times \left[ \frac{1 - (1 + i)^{-n}}{i} \right] + \frac{F}{(1 + i)^n}$$

Where:
- $F$ = Face / Par Value, $c$ = Annual coupon rate, $r$ = Annual market yield, $m$ = Payment frequency
- $n = \text{years} \times m$, $C = \frac{F \times c}{m}$, $i = \frac{r}{m}$

### 2. Serial Bond (Equal Principal Installments)

Principal is repaid in $n$ equal installments $P_{\text{prin}} = \frac{F}{n}$.
In period $t$, outstanding face value is $F_t = F - (t - 1) P_{\text{prin}}$ and coupon is $C_t = F_t \times \frac{c}{m}$.

$$P(i) = \sum_{t=1}^n \frac{P_{\text{prin}} + C_t}{(1 + i)^t}$$

### 3. Installment Note (Equal Total Installments)

Periodic installment:
- If $c > 0$: $PMT = F \times \frac{c/m}{1 - (1 + c/m)^{-n}}$
- If $c = 0$ (non-interest-bearing note): $PMT = \frac{F}{n}$

Present Value at market discount rate $i = \frac{r}{m}$:

$$P(i) = PMT \times \left[ \frac{1 - (1 + i)^{-n}}{i} \right]$$

### 4. Yield to Maturity (YTM) & Effective Annual Rate (EAR)

For any cash flow stream $CF_1, \dots, CF_n$, solve for periodic rate $i$ such that:

$$\sum_{t=1}^n \frac{CF_t}{(1 + i)^t} - P = 0$$

- **Nominal Annual Yield (YTM)**: $r_{\text{nominal}} = i \times m \times 100\%$
- **Annual Effective Rate (EAR / AER)**: $r_{\text{effective}} = \left( (1 + i)^m - 1 \right) \times 100\%$

---

## File Structure

```
21-Sept-PVcalc/
├── app.py                  # Standard entry point launcher
├── bond_app.py             # Desktop GUI (Morandi theme) & CLI application
├── bond_calculator.py      # Core financial calculations, yield solver & amortisation
├── test_bond_calculator.py # Comprehensive unit test suite (19 tests)
└── README.md               # Documentation & formula reference
```
