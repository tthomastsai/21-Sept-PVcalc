# Bond Discount & Yield Calculator (v2.0)

A financial engineering application to value bonds, solve for yields and effective rates, calculate discounts or premiums, and generate period-by-period amortisation schedules.

---

## What's New in Version 2.0

- **Yield & Effective Rate Solver**:
  - Solve for the annual nominal **Yield to Maturity (YTM)** and **Annual Effective Rate (EAR / AER)** when entering **Face Value**, **Present Value (Bond Price)**, **Coupon Rate**, **Compounding Frequency**, and **Period** (Maturity).
  - Uses an analytical Newton-Raphson numerical engine with bracketed bisection fallback for rapid, guaranteed convergence.
- **Morandi Aesthetic Palette**:
  - Desktop GUI styled in Giorgio Morandi-inspired muted, low-saturation tones: warm greige/oatmeal background, dusty slate header, dusty sage action buttons, and muted terracotta/olive/mauve KPI accents.
- **Accounting Method Labels**:
  - `Effective Interest Method` (clean standard).
  - `Straight-Line Method (prohibited by IFRS)` (noting IFRS non-compliance).
- **British English Localization**:
  - User interface, tables, export headers, and interpretations standardise on British English (*Amortisation*, *Unamortised*, *Colour*).
- **Real-Time Decimal Precision Adjuster**:
  - `[ ➖ Less ]` and `[ ➕ Add ]` controls allow adjusting display precision from **0 up to 8 decimal places** in real time across KPI cards, breakdown tables, and amortisation schedules.

---

## Features

- **Dual Calculation Modes**:
  - **Mode 1 (PV Mode)**: Calculate Bond Market Price and Present Value given Yield.
  - **Mode 2 (Yield Mode)**: Solve Nominal Yield (YTM) and Annual Effective Rate (EAR) given Bond Price.
- **Compounding Frequencies**:
  - Annual ($m=1$)
  - Semi-Annual ($m=2$, standard for corporate and treasury bonds)
  - Quarterly ($m=4$)
  - Monthly ($m=12$)
- **Amortisation Schedules**:
  - **Effective Interest Method**
  - **Straight-Line Method (prohibited by IFRS)**
  - Guaranteed convergence of ending carrying value to Par Value at maturity.
- **Desktop Graphical Interface (GUI)**:
  - Morandi-themed dashboard with live KPI cards.
  - Component breakdown tab with plain-English financial interpretations.
  - Alternating-row formatted table (`ttk.Treeview`) with vertical scrollbar.
  - One-click **Export to CSV** with custom decimal precision.
  - Quick presets (Discount, Deep Discount, Zero-Coupon, Par, and Yield Solver).
  - Zero-Coupon bond toggle.
- **Terminal CLI Mode (`--cli`)**:
  - Interactive terminal mode supporting both calculation modes, British English prompts, and custom decimal tables.
- **Automated Unit Tests**:
  - 15 unit test cases covering pricing, yield solving, schedule convergence, frequencies, and input validation.

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

### 1. Bond Price / Present Value ($P$)

$$P(i) = C \times \left[ \frac{1 - (1 + i)^{-n}}{i} \right] + \frac{F}{(1 + i)^n}$$

Where:
- $F$ = Face / Par Value
- $c$ = Annual Coupon Rate ($c \ge 0$)
- $r$ = Annual Nominal Market Rate / Yield to Maturity (YTM)
- $m$ = Compounding Frequency per year ($m \in \{1, 2, 4, 12\}$)
- $n = \text{years} \times m$ (Total compounding periods)
- $C = \frac{F \times c}{m}$ (Periodic coupon payment)
- $i = \frac{r}{m}$ (Periodic discount rate)
- $\text{Discount Amount} = F - P$ (Positive when $P < F$)
- $\text{Discount \%} = \frac{F - P}{F} \times 100\%$

### 2. Yield to Maturity (YTM) & Annual Effective Rate (EAR)

When given Bond Price $P$, solve for periodic rate $i$ such that:

$$f(i) = C \left[ \frac{1 - (1 + i)^{-n}}{i} \right] + F(1 + i)^{-n} - P = 0$$

- **Nominal Annual Yield (YTM)**:
  $$r_{\text{nominal}} = i \times m \times 100\%$$
- **Annual Effective Rate (EAR / AER)**:
  $$r_{\text{effective}} = \left( (1 + i)^m - 1 \right) \times 100\%$$

---

## File Structure

```
21-Sept-PVcalc/
├── app.py                  # Standard entry point launcher
├── bond_app.py             # Desktop GUI (Morandi theme) & CLI application
├── bond_calculator.py      # Core financial calculations, yield solver & amortisation
├── test_bond_calculator.py # Comprehensive unit test suite (15 tests)
└── README.md               # Documentation & formula reference
```
