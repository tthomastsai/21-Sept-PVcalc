"""
Bond Discount & Yield Calculator - GUI & CLI Application (v2.0.1).

Provides:
- Morandi-themed Tkinter desktop graphical interface.
- Instrument types:
    1. Term Bond (Lump-Sum Par at Maturity).
    2. Serial Bond (Equal Principal Installments with declining interest).
    3. Installment Note (Equal Total Installments / Accounts Payable & Receivable).
- Dual calculation modes:
    1. Calculate Present Value / Bond Price from Market Yield.
    2. Solve Yield to Maturity (YTM) and Effective Annual Rate (EAR) from Price.
- Amortisation methods:
    - Effective Interest Method
    - Straight-Line Method (prohibited by IFRS)
- Real-time adjustable decimal precision (+ / -).
- British English localization throughout.
- Interactive terminal CLI mode (--cli).
"""

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List

# Ensure local directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bond_calculator import (
    calculate_bond,
    calculate_yield,
    generate_amortization_schedule,
    export_schedule_to_csv,
    BondResult,
    YieldResult,
    AmortizationRow,
    VALID_FREQUENCIES,
    VALID_INSTRUMENT_TYPES,
)

__version__ = "2.0.1"

# Morandi Aesthetic Colour Palette (Giorgio Morandi-inspired low-saturation tones)
PALETTE = {
    "bg_main": "#f4f1ea",         # Warm oatmeal / greige background
    "bg_header": "#4d5656",       # Muted slate / charcoal header
    "text_header": "#f5f3ef",     # Warm bone white text
    "sub_header": "#b8c0bc",      # Soft sage-grey subtitle text
    "card_bg": "#fcfbf9",         # Soft warm ivory card surface
    "card_border": "#dfdad2",     # Gentle muted border
    "text_primary": "#2d3232",    # Dark charcoal body text
    "text_muted": "#757c7c",      # Muted slate label text
    "text_accent": "#5b6b64",     # Muted forest/sage
    # Action buttons
    "btn_primary": "#6c8276",     # Dusty sage green primary button
    "btn_primary_hover": "#5a6f64",
    "btn_primary_text": "#ffffff",
    "btn_secondary": "#ded8ce",   # Muted warm stone secondary button
    "btn_secondary_hover": "#d0c9bd",
    "btn_preset": "#ede8e0",      # Pale dust preset button
    "btn_preset_hover": "#dfd9cf",
    # KPI Accent top bars (Morandi dusty tones)
    "kpi_bar_1": "#687d8c",       # Dusty slate blue
    "kpi_bar_2": "#b37b67",       # Dusty terracotta
    "kpi_bar_3": "#7d8c70",       # Muted olive / sage
    "kpi_bar_4": "#8c747a",       # Dusty mauve
    # Table styling
    "table_header_bg": "#eae5dc", # Muted sand table heading
    "table_header_fg": "#373c3d",
    "table_row_even": "#f8f6f1",  # Soft warm ivory alternate row
    "table_row_odd": "#ffffff",
    "table_select_bg": "#849890", # Dusty sage table selection
    "table_select_fg": "#ffffff",
    # Badges
    "badge_discount": "#b37b67",  # Dusty terracotta
    "badge_premium": "#687d8c",   # Dusty slate blue
    "badge_par": "#7d8c70",       # Muted olive
}

# Frequency label mapping
FREQ_LABEL_TO_INT = {
    "Semi-Annual (2/year)": 2,
    "Annual (1/year)": 1,
    "Quarterly (4/year)": 4,
    "Monthly (12/year)": 12,
}
FREQ_INT_TO_LABEL = {v: k for k, v in FREQ_LABEL_TO_INT.items()}

# Instrument mapping
INSTRUMENT_LABEL_TO_KEY = {
    "Term Bond (Lump-Sum at Maturity)": "term",
    "Serial Bond (Equal Principal Installments)": "serial_equal_principal",
    "Installment Note (Equal Total Installments)": "serial_equal_payment",
}
INSTRUMENT_KEY_TO_LABEL = {v: k for k, v in INSTRUMENT_LABEL_TO_KEY.items()}

# Method mapping (British English & IFRS note)
METHOD_LABEL_TO_KEY = {
    "Effective Interest Method": "effective",
    "Straight-Line Method (prohibited by IFRS)": "straight_line",
}
METHOD_KEY_TO_LABEL = {v: k for k, v in METHOD_LABEL_TO_KEY.items()}


class BondCalculatorApp(tk.Tk):
    """Modern Desktop GUI for Bond Valuation, Yield Solving, and Amortisation."""

    def __init__(self):
        super().__init__()
        self.title("Bond & Installment Calculator (v2.0.1)")
        self.geometry("1100x760")
        self.minsize(960, 680)
        self.configure(bg=PALETTE["bg_main"])

        # Typography
        self.font_title = ("Segoe UI", 15, "bold")
        self.font_subtitle = ("Segoe UI", 9)
        self.font_section = ("Segoe UI", 11, "bold")
        self.font_body = ("Segoe UI", 9)
        self.font_bold = ("Segoe UI", 9, "bold")
        self.font_metric_val = ("Segoe UI", 16, "bold")
        self.font_metric_sub = ("Segoe UI", 8)

        # State: Mode & Instrument
        self.var_mode = tk.StringVar(value="price")
        self.var_instrument = tk.StringVar(value="Term Bond (Lump-Sum at Maturity)")

        # Input Variables
        self.var_face_value = tk.StringVar(value="1000.00")
        self.var_price = tk.StringVar(value="914.70")
        self.var_coupon_rate = tk.StringVar(value="4.00")
        self.var_market_rate = tk.StringVar(value="6.00")
        self.var_years = tk.StringVar(value="5.0")
        self.var_periods_display = tk.StringVar(value="10 compounding periods")
        self.var_freq = tk.StringVar(value="Semi-Annual (2/year)")
        self.var_method = tk.StringVar(value="Effective Interest Method")
        self.var_zero_coupon = tk.BooleanVar(value=False)

        # Decimal Precision State (default 2, range 0-8)
        self.current_decimals = 2
        self.lbl_decimals_text = tk.StringVar(value="2 Decimals")

        # Results State
        self.last_bond_result: Optional[BondResult] = None
        self.last_yield_result: Optional[YieldResult] = None
        self.last_schedule: List[AmortizationRow] = []

        self._init_styles()
        self._create_widgets()
        self._on_mode_change()
        self.calculate()

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", font=self.font_body, background=PALETTE["bg_main"])
        style.configure("TFrame", background=PALETTE["bg_main"])
        style.configure("Card.TFrame", background=PALETTE["card_bg"], relief="flat")
        style.configure("TLabel", background=PALETTE["card_bg"], font=self.font_body, foreground=PALETTE["text_primary"])
        style.configure("Header.TLabel", font=self.font_section, foreground=PALETTE["text_primary"])

        # Primary Button (Dusty Sage)
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background=PALETTE["btn_primary"],
            foreground=PALETTE["btn_primary_text"],
            padding=(12, 7),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", PALETTE["btn_primary_hover"]), ("pressed", PALETTE["btn_primary_hover"])],
        )

        # Secondary Button (Muted Warm Stone)
        style.configure(
            "Secondary.TButton",
            font=self.font_body,
            background=PALETTE["btn_secondary"],
            foreground=PALETTE["text_primary"],
            padding=(8, 5),
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", PALETTE["btn_secondary_hover"]), ("pressed", PALETTE["btn_secondary_hover"])],
        )

        # Preset Button
        style.configure(
            "Preset.TButton",
            font=("Segoe UI", 8),
            background=PALETTE["btn_preset"],
            foreground=PALETTE["text_primary"],
            padding=(6, 3),
            borderwidth=1,
        )
        style.map(
            "Preset.TButton",
            background=[("active", PALETTE["btn_preset_hover"]), ("pressed", PALETTE["btn_preset_hover"])],
        )

        # Radiobuttons & Checkbuttons
        style.configure("TRadiobutton", background=PALETTE["card_bg"], foreground=PALETTE["text_primary"], font=self.font_body)
        style.configure("TCheckbutton", background=PALETTE["card_bg"], foreground=PALETTE["text_primary"], font=self.font_body)

        # Treeview styling (Morandi tones)
        style.configure(
            "Treeview",
            background=PALETTE["table_row_odd"],
            foreground=PALETTE["text_primary"],
            fieldbackground=PALETTE["table_row_odd"],
            rowheight=25,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=PALETTE["table_header_bg"],
            foreground=PALETTE["table_header_fg"],
            font=("Segoe UI", 8, "bold"),
            padding=(4, 4),
        )
        style.map("Treeview", background=[("selected", PALETTE["table_select_bg"])], foreground=[("selected", PALETTE["table_select_fg"])])

        # Notebook tabs
        style.configure("TNotebook", background=PALETTE["bg_main"])
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=(14, 6))

    def _create_widgets(self):
        # 1. Top Header (Dusty Slate)
        header = tk.Frame(self, bg=PALETTE["bg_header"], padx=22, pady=12)
        header.pack(fill="x")

        title_row = tk.Frame(header, bg=PALETTE["bg_header"])
        title_row.pack(fill="x")

        title = tk.Label(
            title_row,
            text="Bond & Installment Accounts Calculator",
            font=self.font_title,
            fg=PALETTE["text_header"],
            bg=PALETTE["bg_header"],
        )
        title.pack(side="left")

        ver_badge = tk.Label(
            title_row,
            text=f"v{__version__}",
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg=PALETTE["kpi_bar_1"],
            padx=6,
            pady=2,
        )
        ver_badge.pack(side="left", padx=(10, 0))

        subtitle = tk.Label(
            header,
            text="Value long-term payables / receivables with live yield solving and amortisation.",
            font=self.font_subtitle,
            fg=PALETTE["sub_header"],
            bg=PALETTE["bg_header"],
        )
        subtitle.pack(anchor="w", pady=(3, 0))

        # 2. Main Container
        main_container = tk.Frame(self, bg=PALETTE["bg_main"], padx=16, pady=12)
        main_container.pack(fill="both", expand=True)

        # Left Column: Inputs (Fixed width)
        left_col = tk.Frame(
            main_container,
            bg=PALETTE["card_bg"],
            bd=1,
            relief="solid",
            highlightbackground=PALETTE["card_border"],
            highlightthickness=1,
            padx=16,
            pady=12,
            width=350,
        )
        left_col.pack(side="left", fill="y", padx=(0, 12))
        left_col.pack_propagate(False)

        # Right Column: Toolbar + KPI Cards + Tabs
        right_col = tk.Frame(main_container, bg=PALETTE["bg_main"])
        right_col.pack(side="right", fill="both", expand=True)

        self._build_input_form(left_col)
        self._build_results_area(right_col)

    def _build_input_form(self, parent: tk.Frame):
        # Section 1: Calculation Mode
        tk.Label(
            parent,
            text="Calculation Mode",
            font=self.font_section,
            bg=PALETTE["card_bg"],
            fg=PALETTE["text_primary"],
        ).pack(anchor="w", pady=(0, 4))

        mode_box = tk.Frame(
            parent,
            bg=PALETTE["bg_main"],
            bd=1,
            relief="solid",
            highlightbackground=PALETTE["card_border"],
            highlightthickness=1,
            padx=8,
            pady=5,
        )
        mode_box.pack(fill="x", pady=(0, 8))

        rb_price = ttk.Radiobutton(
            mode_box,
            text="Calculate Price from Yield (PV Mode)",
            variable=self.var_mode,
            value="price",
            command=self._on_mode_change,
        )
        rb_price.pack(anchor="w", pady=1)

        rb_yield = ttk.Radiobutton(
            mode_box,
            text="Solve Yield & Effective Rate from Price",
            variable=self.var_mode,
            value="yield",
            command=self._on_mode_change,
        )
        rb_yield.pack(anchor="w", pady=1)

        # Section 2: Instrument Type
        f_inst = tk.Frame(parent, bg=PALETTE["card_bg"])
        f_inst.pack(fill="x", pady=2)
        tk.Label(f_inst, text="Instrument Type", font=self.font_bold, bg=PALETTE["card_bg"], fg=PALETTE["text_primary"]).pack(anchor="w")
        self.cb_inst = ttk.Combobox(
            f_inst,
            textvariable=self.var_instrument,
            values=list(INSTRUMENT_LABEL_TO_KEY.keys()),
            state="readonly",
        )
        self.cb_inst.pack(fill="x", pady=(1, 4))
        self.cb_inst.bind("<<ComboboxSelected>>", lambda e: self._on_instrument_change())

        # Section 3: Financial Parameters
        def add_field(label_text: str, var: tk.StringVar, suffix: str = ""):
            f = tk.Frame(parent, bg=PALETTE["card_bg"])
            f.pack(fill="x", pady=2)
            lbl = tk.Label(f, text=label_text, font=self.font_bold, bg=PALETTE["card_bg"], fg=PALETTE["text_primary"])
            lbl.pack(anchor="w")
            row = tk.Frame(f, bg=PALETTE["card_bg"])
            row.pack(fill="x", pady=(1, 0))
            ent = ttk.Entry(row, textvariable=var, font=self.font_body)
            ent.pack(side="left", fill="x", expand=True)
            if suffix:
                s_lbl = tk.Label(row, text=suffix, font=self.font_body, bg=PALETTE["card_bg"], fg=PALETTE["text_muted"], padx=4)
                s_lbl.pack(side="right")
            return ent, lbl

        self.entry_face, self.lbl_face_field = add_field("Face Value / Note Principal", self.var_face_value, "$")
        self.entry_price, self.lbl_price_field = add_field("Present Value (Issue Price)", self.var_price, "$")
        self.entry_coupon, self.lbl_coupon_field = add_field("Annual Coupon / Stated Rate", self.var_coupon_rate, "%")
        self.entry_market_rate, self.lbl_market_field = add_field("Annual Market Rate / Yield (YTM)", self.var_market_rate, "%")

        # Years to Maturity
        f_years = tk.Frame(parent, bg=PALETTE["card_bg"])
        f_years.pack(fill="x", pady=2)
        lbl_years = tk.Label(f_years, text="Years to Maturity / Term", font=self.font_bold, bg=PALETTE["card_bg"], fg=PALETTE["text_primary"])
        lbl_years.pack(anchor="w")
        row_years = tk.Frame(f_years, bg=PALETTE["card_bg"])
        row_years.pack(fill="x", pady=(1, 0))
        self.entry_years = ttk.Entry(row_years, textvariable=self.var_years, font=self.font_body)
        self.entry_years.pack(side="left", fill="x", expand=True)
        lbl_years_unit = tk.Label(row_years, text="Years", font=self.font_body, bg=PALETTE["card_bg"], fg=PALETTE["text_muted"], padx=4)
        lbl_years_unit.pack(side="right")

        self.lbl_periods_note = tk.Label(
            parent,
            textvariable=self.var_periods_display,
            font=("Segoe UI", 8),
            bg=PALETTE["card_bg"],
            fg=PALETTE["text_accent"],
        )
        self.lbl_periods_note.pack(anchor="w", pady=(0, 2))

        # Zero-coupon / Non-interest bearing toggle
        def on_toggle_zero():
            if self.var_zero_coupon.get():
                self.saved_coupon = self.var_coupon_rate.get()
                self.var_coupon_rate.set("0.00")
                self.entry_coupon.configure(state="disabled")
            else:
                self.entry_coupon.configure(state="normal")
                if hasattr(self, "saved_coupon"):
                    self.var_coupon_rate.set(self.saved_coupon)
            self.calculate()

        chk_zero = ttk.Checkbutton(
            parent,
            text="Non-Interest-Bearing / Zero-Coupon",
            variable=self.var_zero_coupon,
            command=on_toggle_zero,
        )
        chk_zero.pack(anchor="w", pady=(1, 3))

        # Compounding Frequency
        f_freq = tk.Frame(parent, bg=PALETTE["card_bg"])
        f_freq.pack(fill="x", pady=2)
        tk.Label(f_freq, text="Payment Frequency", font=self.font_bold, bg=PALETTE["card_bg"], fg=PALETTE["text_primary"]).pack(anchor="w")
        self.cb_freq = ttk.Combobox(
            f_freq,
            textvariable=self.var_freq,
            values=list(FREQ_LABEL_TO_INT.keys()),
            state="readonly",
        )
        self.cb_freq.pack(fill="x", pady=(1, 0))
        self.cb_freq.bind("<<ComboboxSelected>>", lambda e: self._on_freq_change())

        # Amortisation Method
        f_method = tk.Frame(parent, bg=PALETTE["card_bg"])
        f_method.pack(fill="x", pady=2)
        tk.Label(f_method, text="Amortisation Method", font=self.font_bold, bg=PALETTE["card_bg"], fg=PALETTE["text_primary"]).pack(anchor="w")
        self.cb_method = ttk.Combobox(
            f_method,
            textvariable=self.var_method,
            values=list(METHOD_LABEL_TO_KEY.keys()),
            state="readonly",
        )
        self.cb_method.pack(fill="x", pady=(1, 0))
        self.cb_method.bind("<<ComboboxSelected>>", lambda e: self.calculate())

        # Action Buttons
        btn_frame = tk.Frame(parent, bg=PALETTE["card_bg"])
        btn_frame.pack(fill="x", pady=(8, 6))

        btn_calc = ttk.Button(btn_frame, text="Calculate", style="Primary.TButton", command=self.calculate)
        btn_calc.pack(fill="x", pady=(0, 4))

        btn_reset = ttk.Button(btn_frame, text="Reset Defaults", style="Secondary.TButton", command=self.reset_defaults)
        btn_reset.pack(fill="x")

        # Quick Presets
        tk.Label(
            parent,
            text="Presets & Examples",
            font=self.font_bold,
            bg=PALETTE["card_bg"],
            fg=PALETTE["text_muted"],
        ).pack(anchor="w", pady=(6, 2))

        p_frame = tk.Frame(parent, bg=PALETTE["card_bg"])
        p_frame.pack(fill="x")

        ttk.Button(
            p_frame,
            text="Term Bond: 5Y (4% vs 6%)",
            style="Preset.TButton",
            command=lambda: self.load_preset(1000, 4.0, 6.0, 5, 2, inst="term", mode="price"),
        ).pack(fill="x", pady=1)

        ttk.Button(
            p_frame,
            text="Serial Bond: $100k, 5Y (4% vs 6%)",
            style="Preset.TButton",
            command=lambda: self.load_preset(100000, 4.0, 6.0, 5, 1, inst="serial_equal_principal", mode="price"),
        ).pack(fill="x", pady=1)

        ttk.Button(
            p_frame,
            text="Installment Note: $30k @ 6% (0% Note)",
            style="Preset.TButton",
            command=lambda: self.load_preset(30000, 0.0, 6.0, 3, 1, inst="serial_equal_payment", zero=True, mode="price"),
        ).pack(fill="x", pady=1)

        ttk.Button(
            p_frame,
            text="Installment Note: $50k @ 5% Par",
            style="Preset.TButton",
            command=lambda: self.load_preset(50000, 5.0, 5.0, 4, 1, inst="serial_equal_payment", mode="price"),
        ).pack(fill="x", pady=1)

        ttk.Button(
            p_frame,
            text="Yield Solver: $914.70 -> 6% YTM",
            style="Preset.TButton",
            command=lambda: self.load_preset(1000, 4.0, 6.0, 5, 2, price=914.70, inst="term", mode="yield"),
        ).pack(fill="x", pady=1)

        self.bind("<Return>", lambda event: self.calculate())

    def _on_instrument_change(self):
        inst_str = self.var_instrument.get()
        inst_type = INSTRUMENT_LABEL_TO_KEY.get(inst_str, "term")
        if inst_type == "serial_equal_payment":
            # For installment notes (payables/receivables), auto-tick zero-coupon by default
            if not hasattr(self, "saved_coupon"):
                self.saved_coupon = self.var_coupon_rate.get()
            self.var_zero_coupon.set(True)
            self.var_coupon_rate.set("0.00")
            self.entry_coupon.configure(state="disabled")
        else:
            # If switching away from installment note and coupon was zeroed out, restore previous rate
            if hasattr(self, "saved_coupon") and self.var_zero_coupon.get() and self.var_coupon_rate.get() == "0.00":
                self.var_zero_coupon.set(False)
                self.var_coupon_rate.set(self.saved_coupon if self.saved_coupon != "0.00" else "4.00")
                self.entry_coupon.configure(state="normal")
        self.calculate()

    def _on_freq_change(self):
        try:
            years = float(self.var_years.get().strip())
            freq = FREQ_LABEL_TO_INT.get(self.var_freq.get(), 2)
            periods = int(round(years * freq))
            self.var_periods_display.set(f"{periods} compounding periods ({years:g} yrs @ {freq}/yr)")
        except ValueError:
            pass
        self.calculate()

    def _on_mode_change(self):
        mode = self.var_mode.get()
        if mode == "price":
            self.entry_market_rate.configure(state="normal")
            self.entry_price.configure(state="disabled")
            self.lbl_market_field.config(text="Annual Market Rate / Yield (YTM) *")
            self.lbl_price_field.config(text="Present Value (Calculated)")
        else:
            self.entry_price.configure(state="normal")
            self.entry_market_rate.configure(state="disabled")
            self.lbl_price_field.config(text="Present Value (Issue Price) *")
            self.lbl_market_field.config(text="Annual Market Rate (Calculated)")
        self.calculate()

    def _build_results_area(self, parent: tk.Frame):
        # 1. Top Control Bar: Mode indicator + Decimal Precision (+ / -)
        control_bar = tk.Frame(parent, bg=PALETTE["bg_main"])
        control_bar.pack(fill="x", pady=(0, 8))

        self.lbl_mode_status = tk.Label(
            control_bar,
            text="Mode: Calculate Price from Yield (PV Mode)",
            font=self.font_bold,
            bg=PALETTE["bg_main"],
            fg=PALETTE["text_accent"],
        )
        self.lbl_mode_status.pack(side="left")

        # Decimal adjustment controls
        dec_frame = tk.Frame(
            control_bar,
            bg=PALETTE["card_bg"],
            bd=1,
            relief="solid",
            highlightbackground=PALETTE["card_border"],
            highlightthickness=1,
            padx=6,
            pady=2,
        )
        dec_frame.pack(side="right")

        tk.Label(
            dec_frame,
            text="Display Precision:",
            font=("Segoe UI", 8, "bold"),
            bg=PALETTE["card_bg"],
            fg=PALETTE["text_muted"],
        ).pack(side="left", padx=(2, 6))

        btn_dec_minus = tk.Button(
            dec_frame,
            text="  ➖ Less  ",
            font=("Segoe UI", 8, "bold"),
            bg=PALETTE["btn_secondary"],
            fg=PALETTE["text_primary"],
            activebackground=PALETTE["btn_secondary_hover"],
            relief="flat",
            bd=0,
            padx=4,
            pady=1,
            cursor="hand2",
            command=self.decrease_decimals,
        )
        btn_dec_minus.pack(side="left", padx=2)

        lbl_dec = tk.Label(
            dec_frame,
            textvariable=self.lbl_decimals_text,
            font=("Segoe UI", 9, "bold"),
            bg=PALETTE["card_bg"],
            fg=PALETTE["text_primary"],
            width=10,
        )
        lbl_dec.pack(side="left", padx=4)

        btn_dec_plus = tk.Button(
            dec_frame,
            text="  ➕ Add  ",
            font=("Segoe UI", 8, "bold"),
            bg=PALETTE["btn_secondary"],
            fg=PALETTE["text_primary"],
            activebackground=PALETTE["btn_secondary_hover"],
            relief="flat",
            bd=0,
            padx=4,
            pady=1,
            cursor="hand2",
            command=self.increase_decimals,
        )
        btn_dec_plus.pack(side="left", padx=2)

        # 2. KPI Summary Cards (4 cards)
        cards_frame = tk.Frame(parent, bg=PALETTE["bg_main"])
        cards_frame.pack(fill="x", pady=(0, 10))

        self.kpi_c1_title = tk.StringVar(value="Present Value / Price")
        self.kpi_c1_val = tk.StringVar(value="$0.00")
        self.kpi_c1_sub = tk.StringVar(value="Initial Carrying Amount")

        self.kpi_c2_title = tk.StringVar(value="Discount / Premium")
        self.kpi_c2_val = tk.StringVar(value="$0.00")
        self.kpi_c2_sub = tk.StringVar(value="PAR VALUE")

        self.kpi_c3_title = tk.StringVar(value="Annual Effective Rate (EAR)")
        self.kpi_c3_val = tk.StringVar(value="0.00%")
        self.kpi_c3_sub = tk.StringVar(value="Compounded Annual Yield")

        self.kpi_c4_title = tk.StringVar(value="Periodic Payment")
        self.kpi_c4_val = tk.StringVar(value="$0.00")
        self.kpi_c4_sub = tk.StringVar(value="Cash Paid Each Period")

        c1 = self._create_kpi_card(cards_frame, self.kpi_c1_title, self.kpi_c1_val, self.kpi_c1_sub, PALETTE["kpi_bar_1"])
        c1.pack(side="left", fill="both", expand=True, padx=(0, 5))

        c2 = self._create_kpi_card(cards_frame, self.kpi_c2_title, self.kpi_c2_val, self.kpi_c2_sub, PALETTE["kpi_bar_2"])
        c2.pack(side="left", fill="both", expand=True, padx=3)

        c3 = self._create_kpi_card(cards_frame, self.kpi_c3_title, self.kpi_c3_val, self.kpi_c3_sub, PALETTE["kpi_bar_3"])
        c3.pack(side="left", fill="both", expand=True, padx=3)

        c4 = self._create_kpi_card(cards_frame, self.kpi_c4_title, self.kpi_c4_val, self.kpi_c4_sub, PALETTE["kpi_bar_4"])
        c4.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # 3. Tabbed Interface
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)

        tab_overview = ttk.Frame(notebook, style="Card.TFrame")
        tab_schedule = ttk.Frame(notebook, style="Card.TFrame")

        notebook.add(tab_overview, text="  Valuation Breakdown  ")
        notebook.add(tab_schedule, text="  Amortisation Schedule  ")

        self._build_overview_tab(tab_overview)
        self._build_schedule_tab(tab_schedule)

    def _create_kpi_card(
        self, parent: tk.Frame, title_var: tk.StringVar, val_var: tk.StringVar, sub_var: tk.StringVar, accent_color: str
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=PALETTE["card_bg"],
            bd=1,
            relief="solid",
            highlightbackground=PALETTE["card_border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        bar = tk.Frame(card, bg=accent_color, height=4)
        bar.pack(fill="x", pady=(0, 6))

        lbl_title = tk.Label(card, textvariable=title_var, font=("Segoe UI", 8, "bold"), fg=PALETTE["text_muted"], bg=PALETTE["card_bg"])
        lbl_title.pack(anchor="w")

        lbl_val = tk.Label(card, textvariable=val_var, font=self.font_metric_val, fg=PALETTE["text_primary"], bg=PALETTE["card_bg"])
        lbl_val.pack(anchor="w", pady=(2, 0))

        lbl_sub = tk.Label(card, textvariable=sub_var, font=self.font_metric_sub, fg=PALETTE["text_muted"], bg=PALETTE["card_bg"])
        lbl_sub.pack(anchor="w")
        return card

    def _build_overview_tab(self, parent: ttk.Frame):
        container = tk.Frame(parent, bg=PALETTE["card_bg"], padx=18, pady=14)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Component Present Value & Yield Breakdown",
            font=self.font_section,
            fg=PALETTE["text_primary"],
            bg=PALETTE["card_bg"],
        ).pack(anchor="w", pady=(0, 8))

        grid_frame = tk.Frame(
            container,
            bg=PALETTE["bg_main"],
            bd=1,
            relief="solid",
            highlightbackground=PALETTE["card_border"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        grid_frame.pack(fill="x", pady=(0, 12))

        self.lbl_inst_type = tk.Label(grid_frame, text="Term Bond", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_pv_coupons = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_pv_par = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_yield_nominal = tk.Label(grid_frame, text="0.00%", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_yield_effective = tk.Label(grid_frame, text="0.00%", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_periods_info = tk.Label(grid_frame, text="0 periods", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_total_coupons = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_total_inflow = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])
        self.lbl_net_profit = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg=PALETTE["bg_main"], fg=PALETTE["text_primary"])

        rows = [
            ("Debt / Instrument Classification:", self.lbl_inst_type),
            ("Present Value of Interest / Annuity Stream:", self.lbl_pv_coupons),
            ("Present Value of Principal Stream:", self.lbl_pv_par),
            ("Nominal Market Yield to Maturity (YTM):", self.lbl_yield_nominal),
            ("Annual Effective Rate (EAR / AER):", self.lbl_yield_effective),
            ("Compounding Periods:", self.lbl_periods_info),
            ("Total Interest Paid / Received over Life:", self.lbl_total_coupons),
            ("Total Cash Outflow / Inflow to Maturity:", self.lbl_total_inflow),
            ("Net Interest Expense / Return:", self.lbl_net_profit),
        ]

        for i, (label_text, widget) in enumerate(rows):
            tk.Label(grid_frame, text=label_text, font=self.font_body, bg=PALETTE["bg_main"], fg=PALETTE["text_muted"]).grid(
                row=i, column=0, sticky="w", pady=2
            )
            widget.grid(row=i, column=1, sticky="e", padx=(20, 0), pady=2)

        grid_frame.columnconfigure(0, weight=1)

        # Financial Interpretation Card
        tk.Label(
            container,
            text="Financial Interpretation",
            font=self.font_section,
            fg=PALETTE["text_primary"],
            bg=PALETTE["card_bg"],
        ).pack(anchor="w", pady=(0, 4))

        self.text_explanation = tk.Label(
            container,
            text="",
            font=self.font_body,
            fg=PALETTE["text_primary"],
            bg=PALETTE["bg_main"],
            bd=1,
            relief="solid",
            highlightbackground=PALETTE["card_border"],
            highlightthickness=1,
            justify="left",
            wraplength=660,
            padx=12,
            pady=10,
        )
        self.text_explanation.pack(fill="x")

    def _build_schedule_tab(self, parent: ttk.Frame):
        container = tk.Frame(parent, bg=PALETTE["card_bg"], padx=10, pady=10)
        container.pack(fill="both", expand=True)

        top_bar = tk.Frame(container, bg=PALETTE["card_bg"])
        top_bar.pack(fill="x", pady=(0, 8))

        self.lbl_schedule_title = tk.Label(
            top_bar,
            text="Amortisation Table",
            font=self.font_section,
            fg=PALETTE["text_primary"],
            bg=PALETTE["card_bg"],
        )
        self.lbl_schedule_title.pack(side="left")

        btn_export = ttk.Button(
            top_bar,
            text="📥 Export to CSV",
            style="Secondary.TButton",
            command=self.export_csv,
        )
        btn_export.pack(side="right")

        # Treeview with columns: period, beg_val, interest_exp, coupon, principal, total_cash, amort, end_val
        cols = ("period", "beg_val", "interest_exp", "coupon", "principal", "total_cash", "amort", "end_val")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("period", text="Period")
        self.tree.heading("beg_val", text="Beg Carrying Amount")
        self.tree.heading("interest_exp", text="Interest Expense")
        self.tree.heading("coupon", text="Coupon / Int")
        self.tree.heading("principal", text="Principal Repaid")
        self.tree.heading("total_cash", text="Total Cash Paid")
        self.tree.heading("amort", text="Discount Amort.")
        self.tree.heading("end_val", text="End Carrying Amount")

        self.tree.column("period", width=50, anchor="center")
        self.tree.column("beg_val", width=125, anchor="e")
        self.tree.column("interest_exp", width=100, anchor="e")
        self.tree.column("coupon", width=90, anchor="e")
        self.tree.column("principal", width=95, anchor="e")
        self.tree.column("total_cash", width=95, anchor="e")
        self.tree.column("amort", width=90, anchor="e")
        self.tree.column("end_val", width=125, anchor="e")

        scroll_y = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree.tag_configure("even", background=PALETTE["table_row_even"])
        self.tree.tag_configure("odd", background=PALETTE["table_row_odd"])

    def increase_decimals(self):
        if self.current_decimals < 8:
            self.current_decimals += 1
            self.lbl_decimals_text.set(f"{self.current_decimals} Decimals")
            self.update_display()

    def decrease_decimals(self):
        if self.current_decimals > 0:
            self.current_decimals -= 1
            self.lbl_decimals_text.set(f"{self.current_decimals} Decimals")
            self.update_display()

    def calculate(self):
        try:
            face_value = float(self.var_face_value.get().replace(",", "").replace("$", "").strip())
            coupon_rate = float(self.var_coupon_rate.get().replace("%", "").strip())
            years = float(self.var_years.get().strip())
            freq_str = self.var_freq.get()
            freq = FREQ_LABEL_TO_INT.get(freq_str, 2)
            method_str = self.var_method.get()
            method = METHOD_LABEL_TO_KEY.get(method_str, "effective")
            inst_str = self.var_instrument.get()
            inst_type = INSTRUMENT_LABEL_TO_KEY.get(inst_str, "term")

            total_periods = int(round(years * freq))
            self.var_periods_display.set(f"{total_periods} compounding periods ({years:g} yrs @ {freq}/yr)")

            mode = self.var_mode.get()

            if mode == "price":
                market_rate = float(self.var_market_rate.get().replace("%", "").strip())
                res = calculate_bond(face_value, coupon_rate, market_rate, years, freq, inst_type)
                self.var_price.set(f"{res.bond_price:.{self.current_decimals}f}")
                self.last_yield_result = None
            else:
                price = float(self.var_price.get().replace(",", "").replace("$", "").strip())
                y_res = calculate_yield(
                    face_value=face_value,
                    bond_price=price,
                    annual_coupon_rate=coupon_rate,
                    years_to_maturity=years,
                    frequency=freq,
                    instrument_type=inst_type,
                )
                self.last_yield_result = y_res
                market_rate = y_res.nominal_yield
                self.var_market_rate.set(f"{market_rate:.{self.current_decimals}f}")
                res = calculate_bond(face_value, coupon_rate, market_rate, years, freq, inst_type)

            schedule = generate_amortization_schedule(face_value, coupon_rate, market_rate, years, freq, method, inst_type)

            self.last_bond_result = res
            self.last_schedule = schedule

            self.update_display()

        except ValueError as err:
            messagebox.showerror("Input Error", f"Invalid input parameter:\n{err}")

    def update_display(self):
        res = self.last_bond_result
        if not res:
            return

        d = self.current_decimals
        mode = self.var_mode.get()
        years = res.years_to_maturity
        freq = res.frequency
        coupon_rate = res.annual_coupon_rate
        market_rate = res.annual_market_rate
        inst_type = res.instrument_type
        method_str = self.var_method.get()
        method_short = "Effective Interest" if "Effective" in method_str else "Straight-Line"

        # Update KPI Cards
        if mode == "price":
            self.lbl_mode_status.config(text="Mode: Calculate Price from Yield (PV Mode)")
            self.kpi_c1_title.set("Present Value / Price")
            self.kpi_c1_val.set(f"${res.bond_price:,.{d}f}")
            self.kpi_c1_sub.set("Initial Carrying Amount")

            self.kpi_c2_title.set("Discount / Premium")
            if res.status == "Discount":
                self.kpi_c2_val.set(f"${res.discount_amount:,.{d}f}")
                self.kpi_c2_sub.set(f"DISCOUNT ({res.discount_percentage:.{d}f}% of Par)")
            elif res.status == "Premium":
                self.kpi_c2_val.set(f"${abs(res.discount_amount):,.{d}f}")
                self.kpi_c2_sub.set(f"PREMIUM ({abs(res.discount_percentage):.{d}f}% of Par)")
            else:
                self.kpi_c2_val.set(f"$0.{'0'*d}")
                self.kpi_c2_sub.set("PAR VALUE")

            self.kpi_c3_title.set("Annual Effective Rate (EAR)")
            self.kpi_c3_val.set(f"{res.effective_annual_rate:.{d}f}%")
            self.kpi_c3_sub.set(f"Nominal YTM: {market_rate:.{d}f}%")

            if inst_type == "serial_equal_principal":
                self.kpi_c4_title.set("Periodic Principal Repayment")
                self.kpi_c4_val.set(f"${res.periodic_principal_payment:,.{d}f}")
                self.kpi_c4_sub.set(f"+ Initial Coupon ${res.periodic_coupon_payment:,.{d}f}")
            elif inst_type == "serial_equal_payment":
                self.kpi_c4_title.set("Periodic Installment (PMT)")
                self.kpi_c4_val.set(f"${res.periodic_total_payment:,.{d}f}")
                self.kpi_c4_sub.set(f"Equal payment {freq}x/year")
            else:
                self.kpi_c4_title.set("Periodic Coupon")
                self.kpi_c4_val.set(f"${res.periodic_coupon_payment:,.{d}f}")
                self.kpi_c4_sub.set(f"Paid {freq}x per year")

        else:  # yield mode
            self.lbl_mode_status.config(text="Mode: Solve Yield & Effective Rate from Price")
            self.kpi_c1_title.set("Nominal Yield to Maturity (YTM)")
            self.kpi_c1_val.set(f"{market_rate:.{d}f}%")
            self.kpi_c1_sub.set(f"Annual Nominal Rate ({freq}x/yr)")

            self.kpi_c2_title.set("Annual Effective Rate (EAR)")
            self.kpi_c2_val.set(f"{res.effective_annual_rate:.{d}f}%")
            self.kpi_c2_sub.set("Compounded Annual Rate")

            self.kpi_c3_title.set("Discount / Premium")
            if res.status == "Discount":
                self.kpi_c3_val.set(f"${res.discount_amount:,.{d}f}")
                self.kpi_c3_sub.set(f"DISCOUNT ({res.discount_percentage:.{d}f}% of Par)")
            elif res.status == "Premium":
                self.kpi_c2_val.set(f"${abs(res.discount_amount):,.{d}f}")
                self.kpi_c3_sub.set(f"PREMIUM ({abs(res.discount_percentage):.{d}f}% of Par)")
            else:
                self.kpi_c3_val.set(f"$0.{'0'*d}")
                self.kpi_c3_sub.set("PAR VALUE")

            self.kpi_c4_title.set("Periodic Cash Payment")
            self.kpi_c4_val.set(f"${res.periodic_total_payment:,.{d}f}")
            self.kpi_c4_sub.set(f"Present Value: ${res.bond_price:,.{d}f}")

        # Update Overview Breakdown
        self.lbl_inst_type.config(text=INSTRUMENT_KEY_TO_LABEL.get(inst_type, inst_type))
        self.lbl_pv_coupons.config(text=f"${res.pv_coupons:,.{d}f}")
        self.lbl_pv_par.config(text=f"${res.pv_face_value:,.{d}f}")
        self.lbl_yield_nominal.config(text=f"{res.annual_market_rate:.{d}f}%")
        self.lbl_yield_effective.config(text=f"{res.effective_annual_rate:.{d}f}%")
        self.lbl_periods_info.config(text=f"{res.total_periods} periods ({years:g} yrs @ {freq}/yr)")
        self.lbl_total_coupons.config(text=f"${res.total_coupon_interest:,.{d}f}")
        self.lbl_total_inflow.config(text=f"${res.total_cash_flows:,.{d}f}")
        self.lbl_net_profit.config(text=f"${res.net_interest_expense:,.{d}f}")

        # Financial Interpretation (British English & IFRS 9)
        if inst_type == "serial_equal_principal":
            explanation = (
                f"• SERIAL BOND: Total principal of ${res.face_value:,.{d}f} is repaid in {res.total_periods} equal installments "
                f"of ${res.periodic_principal_payment:,.{d}f} per period.\n"
                f"• Periodic coupon interest decreases each period as outstanding principal is retired.\n"
                f"• Present Value / Issue Price: ${res.bond_price:,.{d}f} (Discount/Premium: ${res.discount_amount:,.{d}f}).\n"
                f"• Ending carrying amount converges to $0.00 at the end of period {res.total_periods} as the issue is fully retired.\n"
                f"• Total cash paid over life: ${res.total_cash_flows:,.{d}f} (Total interest expense: ${res.net_interest_expense:,.{d}f}, EAR: {res.effective_annual_rate:.{d}f}%)."
            )
        elif inst_type == "serial_equal_payment":
            explanation = (
                f"• INSTALLMENT NOTE / ACCOUNTS PAYABLE & RECEIVABLE: Repaid in {res.total_periods} equal periodic installments "
                f"of ${res.periodic_total_payment:,.{d}f} each.\n"
                f"• Each payment covers interest on the carrying amount, with the remainder amortising the principal.\n"
                f"• Present Value / Initial Carrying Amount: ${res.bond_price:,.{d}f} (Discount: ${res.discount_amount:,.{d}f}).\n"
                f"• Ending carrying amount converges exactly to $0.00 at maturity.\n"
                f"• Total cash paid: ${res.total_cash_flows:,.{d}f} (Total net interest: ${res.net_interest_expense:,.{d}f}, EAR: {res.effective_annual_rate:.{d}f}%)."
            )
        else:
            if res.status == "Discount":
                explanation = (
                    f"• TERM BOND: Trades at a DISCOUNT of ${res.discount_amount:,.{d}f} ({res.discount_percentage:.{d}f}% of par).\n"
                    f"• Because coupon rate ({coupon_rate:.{d}f}%) < market rate ({market_rate:.{d}f}%), "
                    f"investors purchase the bond below par at ${res.bond_price:,.{d}f} to achieve the market yield.\n"
                    f"• Entire principal of ${res.face_value:,.{d}f} is repaid at maturity, converging carrying amount to par.\n"
                    f"• Total return: ${res.net_interest_expense:,.{d}f} (EAR: {res.effective_annual_rate:.{d}f}%)."
                )
            elif res.status == "Premium":
                explanation = (
                    f"• TERM BOND: Trades at a PREMIUM of ${abs(res.discount_amount):,.{d}f} ({abs(res.discount_percentage):.{d}f}% of par).\n"
                    f"• Because coupon rate ({coupon_rate:.{d}f}%) > market rate ({market_rate:.{d}f}%), "
                    f"investors pay ${res.bond_price:,.{d}f} upfront for the higher coupon payments.\n"
                    f"• Effective Annual Rate: {res.effective_annual_rate:.{d}f}% (Nominal YTM: {market_rate:.{d}f}%)."
                )
            else:
                explanation = (
                    f"• TERM BOND: Trades exactly at PAR VALUE (${res.face_value:,.{d}f}).\n"
                    f"• Coupon rate equals required market yield ({market_rate:.{d}f}%).\n"
                    f"• Effective Annual Rate: {res.effective_annual_rate:.{d}f}%."
                )

        self.text_explanation.config(text=explanation)

        # Update Treeview Schedule Table
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.lbl_schedule_title.config(text=f"Amortisation Table ({method_short})")

        for i, row in enumerate(self.last_schedule):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(
                    row.period,
                    f"${row.beginning_carrying_amount:,.{d}f}",
                    f"${row.interest_expense:,.{d}f}",
                    f"${row.coupon_payment:,.{d}f}",
                    f"${row.principal_repayment:,.{d}f}",
                    f"${row.total_cash_payment:,.{d}f}",
                    f"${row.discount_amortization:,.{d}f}",
                    f"${row.ending_carrying_amount:,.{d}f}",
                ),
                tags=(tag,),
            )

    def reset_defaults(self):
        self.var_mode.set("price")
        self.var_instrument.set("Term Bond (Lump-Sum at Maturity)")
        self.var_face_value.set("1000.00")
        self.var_price.set("914.70")
        self.var_coupon_rate.set("4.00")
        self.var_market_rate.set("6.00")
        self.var_years.set("5.0")
        self.var_freq.set("Semi-Annual (2/year)")
        self.var_method.set("Effective Interest Method")
        self.var_zero_coupon.set(False)
        self.current_decimals = 2
        self.lbl_decimals_text.set("2 Decimals")
        self.entry_coupon.configure(state="normal")
        self._on_mode_change()

    def load_preset(
        self,
        face: float,
        coupon: float,
        market: float,
        years: float,
        freq: int,
        price: Optional[float] = None,
        inst: str = "term",
        zero: bool = False,
        mode: str = "price",
    ):
        self.var_mode.set(mode)
        self.var_instrument.set(INSTRUMENT_KEY_TO_LABEL.get(inst, "Term Bond (Lump-Sum at Maturity)"))
        self.var_face_value.set(f"{face:.{self.current_decimals}f}")
        self.var_coupon_rate.set(f"{coupon:.{self.current_decimals}f}")
        self.var_market_rate.set(f"{market:.{self.current_decimals}f}")
        self.var_years.set(f"{years:g}")
        self.var_freq.set(FREQ_INT_TO_LABEL.get(freq, "Semi-Annual (2/year)"))
        self.var_zero_coupon.set(zero)

        if price is not None:
            self.var_price.set(f"{price:.{self.current_decimals}f}")

        if zero:
            self.entry_coupon.configure(state="disabled")
        else:
            self.entry_coupon.configure(state="normal")

        self._on_mode_change()

    def export_csv(self):
        if not self.last_schedule:
            messagebox.showinfo("Export", "No amortisation schedule available to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV file (*.csv)", "*.csv"), ("All files (*.*)", "*.*")],
            title="Export Amortisation Schedule to CSV",
            initialfile="bond_amortisation_schedule.csv",
        )
        if filepath:
            try:
                export_schedule_to_csv(self.last_schedule, filepath, decimals=self.current_decimals)
                messagebox.showinfo("Export Successful", f"Amortisation schedule successfully saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not write CSV file:\n{e}")


# =====================================================================
# CLI MODE (British English)
# =====================================================================


def run_cli():
    """Run bond discount & yield calculator interactively in terminal mode."""
    print("=" * 68)
    print("      BOND & INSTALLMENT CALCULATOR & AMORTISATION (v2.0.1 CLI)   ")
    print("=" * 68)
    print("Press Enter to accept [default values] shown in brackets.\n")

    def prompt(msg: str, default: str) -> str:
        val = input(f"{msg} [{default}]: ").strip()
        return val if val else default

    try:
        print("Select Instrument Type:")
        print("  1 = Term Bond (Lump-Sum Par at Maturity)")
        print("  2 = Serial Bond (Equal Principal Installments)")
        print("  3 = Installment Note (Equal Total Installments / Payable & Receivable)")
        raw_inst = prompt("Select Instrument (1, 2, 3)", "1")
        if raw_inst == "2":
            inst_type = "serial_equal_principal"
        elif raw_inst == "3":
            inst_type = "serial_equal_payment"
        else:
            inst_type = "term"

        print("\nSelect Calculation Mode:")
        print("  1 = Calculate Present Value / Price from Yield (PV Mode)")
        print("  2 = Solve Yield & Effective Rate from Price")
        raw_mode = prompt("Select Mode (1 or 2)", "1")
        is_yield_mode = raw_mode == "2"

        raw_face = prompt("Enter Face Value / Note Amount ($)", "1000" if inst_type == "term" else "100000")
        face_value = float(raw_face.replace(",", "").replace("$", ""))

        if is_yield_mode:
            raw_price = prompt("Enter Present Value / Issue Price ($)", "914.70")
            bond_price = float(raw_price.replace(",", "").replace("$", ""))
        else:
            bond_price = 0.0

        raw_coupon = prompt("Enter Annual Coupon / Stated Rate (%)", "4.0")
        coupon_rate = float(raw_coupon.replace("%", ""))

        if not is_yield_mode:
            raw_market = prompt("Enter Market Rate / YTM (%)", "6.0")
            market_rate = float(raw_market.replace("%", ""))
        else:
            market_rate = 0.0

        raw_years = prompt("Enter Years to Maturity / Term", "5.0")
        years = float(raw_years)

        print("\nPayment / Compounding Frequencies:")
        print("  1 = Annual")
        print("  2 = Semi-Annual (Standard)")
        print("  4 = Quarterly")
        print("  12 = Monthly")
        raw_freq = prompt("Select Frequency (1, 2, 4, 12)", "2" if inst_type == "term" else "1")
        freq = int(raw_freq)

        print("\nAmortisation Method:")
        print("  1 = Effective Interest Method")
        print("  2 = Straight-Line Method (prohibited by IFRS)")
        raw_method = prompt("Select Method (1 or 2)", "1")
        method = "straight_line" if raw_method == "2" else "effective"

        raw_dec = prompt("Enter Display Decimal Places (0-8)", "2")
        d = max(0, min(8, int(raw_dec)))

        # Calculations
        if is_yield_mode:
            y_res = calculate_yield(
                face_value=face_value,
                bond_price=bond_price,
                annual_coupon_rate=coupon_rate,
                years_to_maturity=years,
                frequency=freq,
                instrument_type=inst_type,
            )
            market_rate = y_res.nominal_yield
            res = calculate_bond(face_value, coupon_rate, market_rate, years, freq, inst_type)
        else:
            res = calculate_bond(face_value, coupon_rate, market_rate, years, freq, inst_type)

        schedule = generate_amortization_schedule(face_value, coupon_rate, market_rate, years, freq, method, inst_type)

        print("\n" + "=" * 68)
        print(f"                       VALUATION SUMMARY                  ")
        print("=" * 68)
        print(f"  Instrument:                    {VALID_INSTRUMENT_TYPES.get(res.instrument_type, res.instrument_type)}")
        print(f"  Face Value / Principal:       ${res.face_value:>16,.{d}f}")
        print(f"  Coupon / Stated Rate:          {res.annual_coupon_rate:>16.{d}f}%")
        print(f"  Nominal Yield (YTM):           {res.annual_market_rate:>16.{d}f}%")
        print(f"  Annual Effective Rate (EAR):   {res.effective_annual_rate:>16.{d}f}%")
        print(f"  Years to Maturity:             {res.years_to_maturity:>16.{d}f}")
        print(f"  Compounding Frequency:         {VALID_FREQUENCIES.get(res.frequency, str(res.frequency)):>16}")
        print(f"  Total Compounding Periods:     {res.total_periods:>16}")
        if inst_type == "serial_equal_principal":
            print(f"  Periodic Principal Repaid:    ${res.periodic_principal_payment:>16,.{d}f}")
        elif inst_type == "serial_equal_payment":
            print(f"  Periodic Total Payment:       ${res.periodic_total_payment:>16,.{d}f}")
        else:
            print(f"  Periodic Coupon Payment:      ${res.periodic_coupon_payment:>16,.{d}f}")
        print("-" * 68)
        print(f"  PV of Interest Component:     ${res.pv_coupons:>16,.{d}f}")
        print(f"  PV of Principal Component:    ${res.pv_face_value:>16,.{d}f}")
        print(f"  PRESENT VALUE / PRICE:        ${res.bond_price:>16,.{d}f}  <<<")
        print("-" * 68)
        if res.status == "Discount":
            print(f"  Status:                        {'DISCOUNT':>16}")
            print(f"  Discount Amount:              ${res.discount_amount:>16,.{d}f}")
            print(f"  Discount Percentage:           {res.discount_percentage:>16.{d}f}% of Par")
        elif res.status == "Premium":
            print(f"  Status:                        {'PREMIUM':>16}")
            print(f"  Premium Amount:               ${abs(res.discount_amount):>16,.{d}f}")
            print(f"  Premium Percentage:            {abs(res.discount_percentage):>16.{d}f}% of Par")
        else:
            print(f"  Status:                        {'PAR VALUE':>16}")
            print(f"  Discount / Premium:           ${'0':>16}")

        print(f"  Total Cash Flows:             ${res.total_cash_flows:>16,.{d}f}")
        print(f"  Net Interest Expense / Return:${res.net_interest_expense:>16,.{d}f}")
        print("=" * 68)

        show_table = input("\nPrint full amortisation schedule table? (y/n) [y]: ").strip().lower()
        if show_table != "n":
            col_w = max(11, d + 8)
            print("\n" + "-" * 110)
            print(
                f"{'Per':>4} | {'Beg Amount':>{col_w}} | {'Interest Exp':>{col_w}} | "
                f"{'Coupon Paid':>{col_w}} | {'Principal':>{col_w}} | {'Total Cash':>{col_w}} | "
                f"{'Amortisation':>{col_w}} | {'End Amount':>{col_w}}"
            )
            print("-" * 110)
            for row in schedule:
                print(
                    f"{row.period:4d} | "
                    f"${row.beginning_carrying_amount:{col_w},.{d}f} | "
                    f"${row.interest_expense:{col_w},.{d}f} | "
                    f"${row.coupon_payment:{col_w},.{d}f} | "
                    f"${row.principal_repayment:{col_w},.{d}f} | "
                    f"${row.total_cash_payment:{col_w},.{d}f} | "
                    f"${row.discount_amortization:{col_w},.{d}f} | "
                    f"${row.ending_carrying_amount:{col_w},.{d}f}"
                )
            print("-" * 110)

        do_export = input("\nExport schedule to CSV? (y/n) [n]: ").strip().lower()
        if do_export == "y":
            out_file = input("Enter destination filename [installment_schedule.csv]: ").strip()
            if not out_file:
                out_file = "installment_schedule.csv"
            export_schedule_to_csv(schedule, out_file, decimals=d)
            print(f"Saved amortisation schedule to '{out_file}'.")

        print("\nThank you for using Bond & Installment Calculator!")

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nExiting: {e}")


def main():
    parser = argparse.ArgumentParser(description="Bond & Installment Accounts Calculator (v2.0.1)")
    parser.add_argument("--cli", action="store_true", help="Launch in interactive command-line terminal mode")
    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        app = BondCalculatorApp()
        app.mainloop()


if __name__ == "__main__":
    main()
