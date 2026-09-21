# Bond Discount & Present Value (PV) Calculator

A comprehensive financial application to calculate bond prices, discounts or premiums, yields, cash flows, and full period-by-period amortization schedules.

---

## Features

- **Bond Valuation & Pricing**:
  - Calculates Present Value of Coupon Annuity Payments + Present Value of Lump-Sum Par Value.
  - Automatically identifies whether a bond trades at a **Discount** ($P < F$), **Par** ($P = F$), or **Premium** ($P > F$).
  - Computes discount dollar amount ($F - P$) and discount percentage of face value.
- **Multiple Compounding Frequencies**:
  - Annual ($m=1$)
  - Semi-Annual ($m=2$, standard for US corporate & Treasury bonds)
  - Quarterly ($m=4$)
  - Monthly ($m=12$)
- **Amortization Schedules**:
  - **Effective Interest Method** (US GAAP & IFRS required standard).
  - **Straight-Line Method** (Linear amortization).
  - Guaranteed convergence of ending book value to Par Value at maturity.
- **Desktop Graphical Interface (GUI)**:
  - Clean dashboard design with live KPI cards.
  - Component breakdown tab with plain-English financial interpretations.
  - Scrollable, formatted table (`ttk.Treeview`) with alternating row colors.
  - One-click **Export to CSV** for spreadsheets (Excel, Google Sheets).
  - Quick presets: 5-Year Discount, Deep Discount, Zero-Coupon, and Par bonds.
  - Zero-Coupon bond toggle.
- **Terminal CLI Mode (`--cli`)**:
  - Headless execution with default prompts and formatted ASCII tables.
- **Automated Unit Tests**:
  - Fully tested with 9 test cases verifying calculations, schedules, and edge cases.

---

## How to Run

### 1. Launch Desktop GUI (Default)
```powershell
python bond_app.py
```
*(or run `python app.py`)*

### 2. Launch Interactive CLI Mode
```powershell
python bond_app.py --cli
```

### 3. Run Automated Tests
```powershell
python -m unittest test_bond_calculator.py -v
```

---

## Financial Formulas

$$\text{Bond Price } (P) = C \times \left[ \frac{1 - (1 + i)^{-n}}{i} \right] + \frac{F}{(1 + i)^n}$$

Where:
- $F$ = Face / Par Value
- $c$ = Annual Coupon Rate
- $r$ = Annual Market Rate / Yield to Maturity (YTM)
- $m$ = Payment Frequency per year
- $n = \text{years} \times m$ (Total compounding periods)
- $C = \frac{F \times c}{m}$ (Periodic coupon payment)
- $i = \frac{r}{m}$ (Periodic market discount rate)
- $\text{Discount} = F - P$ (Positive when $P < F$)
- $\text{Discount \%} = \frac{F - P}{F} \times 100\%$

---

## File Structure

```
21-Sept-PVcalc/
├── app.py                  # Standard entry point launcher
├── bond_app.py             # Desktop GUI & CLI application
├── bond_calculator.py      # Core financial calculations & amortization engine
├── test_bond_calculator.py # Unit tests
└── README.md               # Documentation & formula reference
```
