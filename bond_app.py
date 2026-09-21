"""
Bond Discount Calculator - GUI & CLI Application.

Provides a modern Tkinter desktop graphical interface and an interactive
terminal CLI mode (--cli).
"""

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

# Ensure directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bond_calculator import (
    calculate_bond,
    generate_amortization_schedule,
    export_schedule_to_csv,
    BondResult,
    AmortizationRow,
    VALID_FREQUENCIES,
)

__version__ = "1.0.0"

# Frequency label mapping
FREQ_LABEL_TO_INT = {
    "Semi-Annual (2/year)": 2,
    "Annual (1/year)": 1,
    "Quarterly (4/year)": 4,
    "Monthly (12/year)": 12,
}
FREQ_INT_TO_LABEL = {v: k for k, v in FREQ_LABEL_TO_INT.items()}

METHOD_LABEL_TO_KEY = {
    "Effective Interest Method (GAAP/IFRS)": "effective",
    "Straight-Line Method": "straight_line",
}


class BondCalculatorApp(tk.Tk):
    """Modern Desktop GUI for Bond Discount & Amortization Calculations."""

    def __init__(self):
        super().__init__()
        self.title("Bond Discount Calculator & Amortization Schedule")
        self.geometry("1000x720")
        self.minsize(880, 640)
        self.configure(bg="#f8fafc")

        self.font_title = ("Segoe UI", 15, "bold")
        self.font_subtitle = ("Segoe UI", 9)
        self.font_section = ("Segoe UI", 11, "bold")
        self.font_body = ("Segoe UI", 9)
        self.font_bold = ("Segoe UI", 9, "bold")
        self.font_metric_val = ("Segoe UI", 16, "bold")
        self.font_metric_sub = ("Segoe UI", 8)

        # State
        self.var_face_value = tk.StringVar(value="1000.00")
        self.var_coupon_rate = tk.StringVar(value="4.00")
        self.var_market_rate = tk.StringVar(value="6.00")
        self.var_years = tk.StringVar(value="5.0")
        self.var_freq = tk.StringVar(value="Semi-Annual (2/year)")
        self.var_method = tk.StringVar(value="Effective Interest Method (GAAP/IFRS)")
        self.var_zero_coupon = tk.BooleanVar(value=False)

        self.last_bond_result: Optional[BondResult] = None
        self.last_schedule: list[AmortizationRow] = []

        self._init_styles()
        self._create_widgets()
        self.calculate()

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", font=self.font_body)
        style.configure("TFrame", background="#f8fafc")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#ffffff", font=self.font_body, foreground="#1e293b")
        style.configure("Header.TLabel", font=self.font_section, foreground="#0f172a")

        # Buttons
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#2563eb",
            foreground="#ffffff",
            padding=(12, 7),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1d4ed8"), ("pressed", "#1e40af")],
        )

        style.configure(
            "Secondary.TButton",
            font=self.font_body,
            background="#e2e8f0",
            foreground="#1e293b",
            padding=(8, 5),
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#cbd5e1"), ("pressed", "#94a3b8")],
        )

        style.configure(
            "Preset.TButton",
            font=("Segoe UI", 8),
            background="#f1f5f9",
            foreground="#334155",
            padding=(6, 4),
            borderwidth=1,
        )
        style.map(
            "Preset.TButton",
            background=[("active", "#e2e8f0"), ("pressed", "#cbd5e1")],
        )

        # Treeview styling
        style.configure(
            "Treeview",
            background="#ffffff",
            foreground="#1e293b",
            fieldbackground="#ffffff",
            rowheight=24,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#f1f5f9",
            foreground="#0f172a",
            font=("Segoe UI", 9, "bold"),
            padding=(4, 4),
        )
        style.map("Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

        # Notebook
        style.configure("TNotebook", background="#f8fafc")
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=(12, 6))

    def _create_widgets(self):
        # 1. Top Header
        header = tk.Frame(self, bg="#1e293b", padx=20, pady=12)
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="Bond Discount Calculator & Amortization Schedule",
            font=self.font_title,
            fg="#ffffff",
            bg="#1e293b",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="Value corporate & treasury bonds, calculate discounts or premiums, and inspect full amortization schedules.",
            font=self.font_subtitle,
            fg="#94a3b8",
            bg="#1e293b",
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # 2. Main body container
        main_container = tk.Frame(self, bg="#f8fafc", padx=16, pady=12)
        main_container.pack(fill="both", expand=True)

        # Left Column: Input Form (Fixed width)
        left_col = tk.Frame(main_container, bg="#ffffff", bd=1, relief="solid", padx=16, pady=14, width=320)
        left_col.pack(side="left", fill="y", padx=(0, 12))
        left_col.pack_propagate(False)

        # Right Column: KPI Cards + Tabs
        right_col = tk.Frame(main_container, bg="#f8fafc")
        right_col.pack(side="right", fill="both", expand=True)

        self._build_input_form(left_col)
        self._build_results_area(right_col)

    def _build_input_form(self, parent: tk.Frame):
        tk.Label(parent, text="Bond Parameters", font=self.font_section, bg="#ffffff", fg="#0f172a").pack(
            anchor="w", pady=(0, 10)
        )

        def add_field(label_text: str, var: tk.StringVar, suffix: str = ""):
            f = tk.Frame(parent, bg="#ffffff")
            f.pack(fill="x", pady=4)
            lbl = tk.Label(f, text=label_text, font=self.font_bold, bg="#ffffff", fg="#334155")
            lbl.pack(anchor="w")
            row = tk.Frame(f, bg="#ffffff")
            row.pack(fill="x", pady=(2, 0))
            ent = ttk.Entry(row, textvariable=var, font=self.font_body)
            ent.pack(side="left", fill="x", expand=True)
            if suffix:
                s_lbl = tk.Label(row, text=suffix, font=self.font_body, bg="#ffffff", fg="#64748b", padx=4)
                s_lbl.pack(side="right")
            return ent

        add_field("Face Value (Par Value)", self.var_face_value, "$")
        self.entry_coupon = add_field("Annual Coupon Rate", self.var_coupon_rate, "%")
        add_field("Market Rate / Yield (YTM)", self.var_market_rate, "%")
        add_field("Years to Maturity", self.var_years, "Years")

        # Zero-coupon toggle
        def on_toggle_zero_coupon():
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
            text="Zero-Coupon Bond (0% coupon)",
            variable=self.var_zero_coupon,
            command=on_toggle_zero_coupon,
        )
        chk_zero.pack(anchor="w", pady=(2, 8))

        # Payment Frequency
        f_freq = tk.Frame(parent, bg="#ffffff")
        f_freq.pack(fill="x", pady=4)
        tk.Label(f_freq, text="Payment Frequency", font=self.font_bold, bg="#ffffff", fg="#334155").pack(anchor="w")
        self.cb_freq = ttk.Combobox(
            f_freq,
            textvariable=self.var_freq,
            values=list(FREQ_LABEL_TO_INT.keys()),
            state="readonly",
        )
        self.cb_freq.pack(fill="x", pady=(2, 0))

        # Amortization Method
        f_method = tk.Frame(parent, bg="#ffffff")
        f_method.pack(fill="x", pady=4)
        tk.Label(f_method, text="Amortization Method", font=self.font_bold, bg="#ffffff", fg="#334155").pack(anchor="w")
        self.cb_method = ttk.Combobox(
            f_method,
            textvariable=self.var_method,
            values=list(METHOD_LABEL_TO_KEY.keys()),
            state="readonly",
        )
        self.cb_method.pack(fill="x", pady=(2, 0))

        # Action Buttons
        btn_frame = tk.Frame(parent, bg="#ffffff")
        btn_frame.pack(fill="x", pady=(14, 10))

        btn_calc = ttk.Button(btn_frame, text="Calculate", style="Primary.TButton", command=self.calculate)
        btn_calc.pack(fill="x", pady=(0, 6))

        btn_reset = ttk.Button(btn_frame, text="Reset Defaults", style="Secondary.TButton", command=self.reset_defaults)
        btn_reset.pack(fill="x")

        # Quick Presets
        tk.Label(parent, text="Presets / Examples", font=self.font_bold, bg="#ffffff", fg="#64748b").pack(
            anchor="w", pady=(12, 4)
        )
        p_frame = tk.Frame(parent, bg="#ffffff")
        p_frame.pack(fill="x")

        ttk.Button(
            p_frame,
            text="Discount: 5Y (4% vs 6%)",
            style="Preset.TButton",
            command=lambda: self.load_preset(1000, 4.0, 6.0, 5, 2),
        ).pack(fill="x", pady=2)

        ttk.Button(
            p_frame,
            text="Deep Discount: 10Y (2% vs 8%)",
            style="Preset.TButton",
            command=lambda: self.load_preset(1000, 2.0, 8.0, 10, 2),
        ).pack(fill="x", pady=2)

        ttk.Button(
            p_frame,
            text="Zero-Coupon: 10Y @ 5%",
            style="Preset.TButton",
            command=lambda: self.load_preset(1000, 0.0, 5.0, 10, 2, zero=True),
        ).pack(fill="x", pady=2)

        ttk.Button(
            p_frame,
            text="Par Bond: 5Y (5% vs 5%)",
            style="Preset.TButton",
            command=lambda: self.load_preset(1000, 5.0, 5.0, 5, 2),
        ).pack(fill="x", pady=2)

        # Bind Enter to calculate
        self.bind("<Return>", lambda event: self.calculate())

    def _build_results_area(self, parent: tk.Frame):
        # Top: KPI summary cards (4 cards)
        cards_frame = tk.Frame(parent, bg="#f8fafc")
        cards_frame.pack(fill="x", pady=(0, 10))

        self.kpi_price_val = tk.StringVar(value="$0.00")
        self.kpi_price_sub = tk.StringVar(value="Present Value")
        self.kpi_discount_val = tk.StringVar(value="$0.00")
        self.kpi_discount_badge = tk.StringVar(value="PAR")
        self.kpi_pct_val = tk.StringVar(value="0.00%")
        self.kpi_coupon_val = tk.StringVar(value="$0.00")

        # Card 1: Bond Price
        c1 = self._create_kpi_card(cards_frame, "Bond Market Price", self.kpi_price_val, self.kpi_price_sub, "#2563eb")
        c1.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Card 2: Discount Amount & Badge
        c2 = self._create_kpi_card(
            cards_frame, "Discount / Premium", self.kpi_discount_val, self.kpi_discount_badge, "#d97706"
        )
        c2.pack(side="left", fill="both", expand=True, padx=3)

        # Card 3: Discount %
        c3 = self._create_kpi_card(
            cards_frame, "Discount Rate (% of Par)", self.kpi_pct_val, tk.StringVar(value="Relative to Par Value"), "#059669"
        )
        c3.pack(side="left", fill="both", expand=True, padx=3)

        # Card 4: Periodic Payment
        c4 = self._create_kpi_card(
            cards_frame, "Periodic Coupon", self.kpi_coupon_val, tk.StringVar(value="Cash Paid Each Period"), "#475569"
        )
        c4.pack(side="left", fill="both", expand=True, padx=(6, 0))

        # Bottom: Tabbed interface
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)

        tab_overview = ttk.Frame(notebook, style="Card.TFrame")
        tab_schedule = ttk.Frame(notebook, style="Card.TFrame")

        notebook.add(tab_overview, text="  Valuation Breakdown  ")
        notebook.add(tab_schedule, text="  Amortization Schedule  ")

        self._build_overview_tab(tab_overview)
        self._build_schedule_tab(tab_schedule)

    def _create_kpi_card(
        self, parent: tk.Frame, title: str, val_var: tk.StringVar, sub_var: tk.StringVar, accent_color: str
    ) -> tk.Frame:
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid", padx=12, pady=10)
        # Top colored accent bar
        bar = tk.Frame(card, bg=accent_color, height=3)
        bar.pack(fill="x", pady=(0, 6))

        lbl_title = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff")
        lbl_title.pack(anchor="w")

        lbl_val = tk.Label(card, textvariable=val_var, font=self.font_metric_val, fg="#0f172a", bg="#ffffff")
        lbl_val.pack(anchor="w", pady=(2, 0))

        lbl_sub = tk.Label(card, textvariable=sub_var, font=self.font_metric_sub, fg="#64748b", bg="#ffffff")
        lbl_sub.pack(anchor="w")
        return card

    def _build_overview_tab(self, parent: ttk.Frame):
        container = tk.Frame(parent, bg="#ffffff", padx=18, pady=14)
        container.pack(fill="both", expand=True)

        tk.Label(
            container, text="Component Present Value Breakdown", font=self.font_section, fg="#0f172a", bg="#ffffff"
        ).pack(anchor="w", pady=(0, 8))

        # Table-like breakdown
        grid_frame = tk.Frame(container, bg="#f8fafc", bd=1, relief="solid", padx=14, pady=10)
        grid_frame.pack(fill="x", pady=(0, 14))

        self.lbl_pv_coupons = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg="#f8fafc", fg="#0f172a")
        self.lbl_pv_par = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg="#f8fafc", fg="#0f172a")
        self.lbl_total_coupons = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg="#f8fafc", fg="#0f172a")
        self.lbl_total_inflow = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg="#f8fafc", fg="#0f172a")
        self.lbl_net_profit = tk.Label(grid_frame, text="$0.00", font=self.font_bold, bg="#f8fafc", fg="#0f172a")
        self.lbl_periods_info = tk.Label(grid_frame, text="0 periods", font=self.font_bold, bg="#f8fafc", fg="#0f172a")

        rows = [
            ("Present Value of Coupon Stream (Annuity):", self.lbl_pv_coupons),
            ("Present Value of Face Value (Lump Sum):", self.lbl_pv_par),
            ("Compounding Periods:", self.lbl_periods_info),
            ("Total Coupon Payments Received:", self.lbl_total_coupons),
            ("Total Cash Inflow to Maturity:", self.lbl_total_inflow),
            ("Net Investor Return / Interest Expense:", self.lbl_net_profit),
        ]

        for i, (label_text, widget) in enumerate(rows):
            tk.Label(grid_frame, text=label_text, font=self.font_body, bg="#f8fafc", fg="#475569").grid(
                row=i, column=0, sticky="w", pady=3
            )
            widget.grid(row=i, column=1, sticky="e", padx=(20, 0), pady=3)

        grid_frame.columnconfigure(0, weight=1)

        # Financial Explanation Card
        tk.Label(
            container, text="Financial Interpretation", font=self.font_section, fg="#0f172a", bg="#ffffff"
        ).pack(anchor="w", pady=(0, 4))

        self.text_explanation = tk.Label(
            container,
            text="",
            font=self.font_body,
            fg="#334155",
            bg="#f1f5f9",
            bd=1,
            relief="solid",
            justify="left",
            wraplength=560,
            padx=12,
            pady=10,
        )
        self.text_explanation.pack(fill="x")

    def _build_schedule_tab(self, parent: ttk.Frame):
        container = tk.Frame(parent, bg="#ffffff", padx=12, pady=10)
        container.pack(fill="both", expand=True)

        top_bar = tk.Frame(container, bg="#ffffff")
        top_bar.pack(fill="x", pady=(0, 8))

        self.lbl_schedule_title = tk.Label(
            top_bar,
            text="Amortization Table",
            font=self.font_section,
            fg="#0f172a",
            bg="#ffffff",
        )
        self.lbl_schedule_title.pack(side="left")

        btn_export = ttk.Button(
            top_bar,
            text="📥 Export to CSV",
            style="Secondary.TButton",
            command=self.export_csv,
        )
        btn_export.pack(side="right")

        # Treeview for table
        cols = ("period", "beg_val", "interest_exp", "coupon", "amort", "end_val", "rem_disc")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("period", text="Period")
        self.tree.heading("beg_val", text="Beginning Value")
        self.tree.heading("interest_exp", text="Interest Expense")
        self.tree.heading("coupon", text="Coupon Cash")
        self.tree.heading("amort", text="Amortization")
        self.tree.heading("end_val", text="Ending Value")
        self.tree.heading("rem_disc", text="Unamortized Disc")

        self.tree.column("period", width=55, anchor="center")
        self.tree.column("beg_val", width=105, anchor="e")
        self.tree.column("interest_exp", width=105, anchor="e")
        self.tree.column("coupon", width=95, anchor="e")
        self.tree.column("amort", width=95, anchor="e")
        self.tree.column("end_val", width=105, anchor="e")
        self.tree.column("rem_disc", width=115, anchor="e")

        # Scrollbar
        scroll_y = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        # Tag for alternating row colors
        self.tree.tag_configure("even", background="#f8fafc")
        self.tree.tag_configure("odd", background="#ffffff")

    def calculate(self):
        try:
            face_value = float(self.var_face_value.get().replace(",", "").replace("$", "").strip())
            coupon_rate = float(self.var_coupon_rate.get().replace("%", "").strip())
            market_rate = float(self.var_market_rate.get().replace("%", "").strip())
            years = float(self.var_years.get().strip())
            freq_str = self.var_freq.get()
            freq = FREQ_LABEL_TO_INT.get(freq_str, 2)
            method_str = self.var_method.get()
            method = METHOD_LABEL_TO_KEY.get(method_str, "effective")

            res = calculate_bond(face_value, coupon_rate, market_rate, years, freq)
            schedule = generate_amortization_schedule(face_value, coupon_rate, market_rate, years, freq, method)

            self.last_bond_result = res
            self.last_schedule = schedule

            # Update KPI cards
            self.kpi_price_val.set(f"${res.bond_price:,.2f}")
            if res.status == "Discount":
                self.kpi_discount_val.set(f"${res.discount_amount:,.2f}")
                self.kpi_discount_badge.set("DISCOUNT (Below Par)")
                self.kpi_pct_val.set(f"{res.discount_percentage:.2f}%")
            elif res.status == "Premium":
                self.kpi_discount_val.set(f"${abs(res.discount_amount):,.2f}")
                self.kpi_discount_badge.set("PREMIUM (Above Par)")
                self.kpi_pct_val.set(f"{abs(res.discount_percentage):.2f}%")
            else:
                self.kpi_discount_val.set("$0.00")
                self.kpi_discount_badge.set("PAR VALUE")
                self.kpi_pct_val.set("0.00%")

            freq_desc = {1: "per year", 2: "every 6 months", 4: "every quarter", 12: "per month"}.get(freq, "")
            self.kpi_coupon_val.set(f"${res.periodic_coupon_payment:,.2f}")

            # Update Overview
            self.lbl_pv_coupons.config(text=f"${res.pv_coupons:,.2f}")
            self.lbl_pv_par.config(text=f"${res.pv_face_value:,.2f}")
            self.lbl_periods_info.config(text=f"{res.total_periods} periods ({years:g} yrs @ {freq}/yr)")
            self.lbl_total_coupons.config(text=f"${res.total_coupon_interest:,.2f}")
            self.lbl_total_inflow.config(text=f"${res.total_cash_flows:,.2f}")
            self.lbl_net_profit.config(text=f"${res.net_interest_expense:,.2f}")

            # Explanation
            if res.status == "Discount":
                explanation = (
                    f"• This bond trades at a DISCOUNT of ${res.discount_amount:,.2f} ({res.discount_percentage:.2f}%).\n"
                    f"• Because the annual coupon rate ({coupon_rate:.2f}%) is lower than the market rate ({market_rate:.2f}%), "
                    f"investors require a lower purchase price (${res.bond_price:,.2f}) to achieve the market yield.\n"
                    f"• Over {years:g} years, the investor pays ${res.bond_price:,.2f} upfront and collects "
                    f"${res.total_coupon_interest:,.2f} in coupons plus ${face_value:,.2f} at maturity, yielding a total gain of ${res.net_interest_expense:,.2f}."
                )
            elif res.status == "Premium":
                explanation = (
                    f"• This bond trades at a PREMIUM of ${abs(res.discount_amount):,.2f} ({abs(res.discount_percentage):.2f}%).\n"
                    f"• Because the annual coupon rate ({coupon_rate:.2f}%) exceeds the market rate ({market_rate:.2f}%), "
                    f"investors are willing to pay above par value (${res.bond_price:,.2f}) for the higher coupon payments."
                )
            else:
                explanation = (
                    f"• This bond trades exactly at PAR VALUE (${res.face_value:,.2f}).\n"
                    f"• The coupon rate equals the market required rate of return ({market_rate:.2f}%)."
                )

            self.text_explanation.config(text=explanation)

            # Update Treeview
            for item in self.tree.get_children():
                self.tree.delete(item)

            self.lbl_schedule_title.config(
                text=f"Amortization Table ({'Effective Interest Method' if method == 'effective' else 'Straight-Line Method'})"
            )

            for i, row in enumerate(schedule):
                tag = "even" if i % 2 == 0 else "odd"
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row.period,
                        f"${row.beginning_carrying_value:,.2f}",
                        f"${row.interest_expense:,.2f}",
                        f"${row.coupon_payment:,.2f}",
                        f"${row.discount_amortization:,.2f}",
                        f"${row.ending_carrying_value:,.2f}",
                        f"${row.remaining_discount:,.2f}",
                    ),
                    tags=(tag,),
                )

        except ValueError as err:
            messagebox.showerror("Input Error", f"Invalid input parameter:\n{err}")

    def reset_defaults(self):
        self.var_face_value.set("1000.00")
        self.var_coupon_rate.set("4.00")
        self.var_market_rate.set("6.00")
        self.var_years.set("5.0")
        self.var_freq.set("Semi-Annual (2/year)")
        self.var_method.set("Effective Interest Method (GAAP/IFRS)")
        self.var_zero_coupon.set(False)
        self.entry_coupon.configure(state="normal")
        self.calculate()

    def load_preset(
        self,
        face: float,
        coupon: float,
        market: float,
        years: float,
        freq: int,
        zero: bool = False,
    ):
        self.var_face_value.set(f"{face:.2f}")
        self.var_coupon_rate.set(f"{coupon:.2f}")
        self.var_market_rate.set(f"{market:.2f}")
        self.var_years.set(f"{years:.1f}")
        self.var_freq.set(FREQ_INT_TO_LABEL.get(freq, "Semi-Annual (2/year)"))
        self.var_zero_coupon.set(zero)
        if zero:
            self.entry_coupon.configure(state="disabled")
        else:
            self.entry_coupon.configure(state="normal")
        self.calculate()

    def export_csv(self):
        if not self.last_schedule:
            messagebox.showinfo("Export", "No amortization schedule available to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV file (*.csv)", "*.csv"), ("All files (*.*)", "*.*")],
            title="Export Amortization Schedule to CSV",
            initialfile="bond_amortization_schedule.csv",
        )
        if filepath:
            try:
                export_schedule_to_csv(self.last_schedule, filepath)
                messagebox.showinfo("Export Successful", f"Schedule successfully saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not write CSV file:\n{e}")


# =====================================================================
# CLI MODE
# =====================================================================


def run_cli():
    """Run bond discount calculator interactively in the terminal."""
    print("=" * 64)
    print("         BOND DISCOUNT CALCULATOR & AMORTIZATION (CLI)        ")
    print("=" * 64)
    print("Press Enter to accept [default values] shown in brackets.\n")

    def prompt(msg: str, default: str) -> str:
        val = input(f"{msg} [{default}]: ").strip()
        return val if val else default

    try:
        raw_face = prompt("Enter Face Value ($)", "1000")
        face_value = float(raw_face.replace(",", "").replace("$", ""))

        raw_coupon = prompt("Enter Annual Coupon Rate (%)", "4.0")
        coupon_rate = float(raw_coupon.replace("%", ""))

        raw_market = prompt("Enter Market Rate / YTM (%)", "6.0")
        market_rate = float(raw_market.replace("%", ""))

        raw_years = prompt("Enter Years to Maturity", "5.0")
        years = float(raw_years)

        print("\nPayment Frequencies:")
        print("  1 = Annual")
        print("  2 = Semi-Annual (Standard)")
        print("  4 = Quarterly")
        print("  12 = Monthly")
        raw_freq = prompt("Select Frequency (1, 2, 4, 12)", "2")
        freq = int(raw_freq)

        print("\nAmortization Method:")
        print("  1 = Effective Interest Method (GAAP/IFRS)")
        print("  2 = Straight-Line Method")
        raw_method = prompt("Select Method (1 or 2)", "1")
        method = "straight_line" if raw_method == "2" else "effective"

        # Calculate
        res = calculate_bond(face_value, coupon_rate, market_rate, years, freq)
        schedule = generate_amortization_schedule(face_value, coupon_rate, market_rate, years, freq, method)

        print("\n" + "=" * 64)
        print(f"                       BOND VALUATION SUMMARY                  ")
        print("=" * 64)
        print(f"  Face Value (Par):             ${res.face_value:>14,.2f}")
        print(f"  Annual Coupon Rate:            {res.annual_coupon_rate:>14.2f}%")
        print(f"  Market Yield (YTM):            {res.annual_market_rate:>14.2f}%")
        print(f"  Years to Maturity:             {res.years_to_maturity:>14.2f}")
        print(f"  Payment Frequency:             {VALID_FREQUENCIES.get(res.frequency, str(res.frequency)):>14}")
        print(f"  Total Compounding Periods:     {res.total_periods:>14}")
        print(f"  Periodic Coupon Payment:      ${res.periodic_coupon_payment:>14,.2f}")
        print("-" * 64)
        print(f"  PV of Coupon Payments:        ${res.pv_coupons:>14,.2f}")
        print(f"  PV of Par (Lump Sum):         ${res.pv_face_value:>14,.2f}")
        print(f"  BOND MARKET PRICE:            ${res.bond_price:>14,.2f}  <<<")
        print("-" * 64)
        if res.status == "Discount":
            print(f"  Status:                        {'DISCOUNT (Below Par)':>14}")
            print(f"  Discount Amount:              ${res.discount_amount:>14,.2f}")
            print(f"  Discount Percentage:           {res.discount_percentage:>14.2f}% of Par")
        elif res.status == "Premium":
            print(f"  Status:                        {'PREMIUM (Above Par)':>14}")
            print(f"  Premium Amount:               ${abs(res.discount_amount):>14,.2f}")
            print(f"  Premium Percentage:            {abs(res.discount_percentage):>14.2f}% of Par")
        else:
            print(f"  Status:                        {'PAR VALUE':>14}")
            print(f"  Discount / Premium:           $          0.00")

        print(f"  Total Coupon Cash Flows:      ${res.total_coupon_interest:>14,.2f}")
        print(f"  Total Inflow at Maturity:     ${res.total_cash_flows:>14,.2f}")
        print(f"  Net Return / Total Gain:      ${res.net_interest_expense:>14,.2f}")
        print("=" * 64)

        # Prompt for schedule
        show_table = input("\nPrint full amortization schedule table? (y/n) [y]: ").strip().lower()
        if show_table != "n":
            print("\n" + "-" * 78)
            print(f"{'Per':>4} | {'Beg Value':>11} | {'Interest Exp':>12} | {'Coupon Paid':>11} | {'Amortization':>12} | {'End Value':>11}")
            print("-" * 78)
            for row in schedule:
                print(
                    f"{row.period:4d} | "
                    f"${row.beginning_carrying_value:10,.2f} | "
                    f"${row.interest_expense:11,.2f} | "
                    f"${row.coupon_payment:10,.2f} | "
                    f"${row.discount_amortization:11,.2f} | "
                    f"${row.ending_carrying_value:10,.2f}"
                )
            print("-" * 78)

        # Export prompt
        do_export = input("\nExport schedule to CSV? (y/n) [n]: ").strip().lower()
        if do_export == "y":
            out_file = input("Enter destination filename [bond_schedule.csv]: ").strip()
            if not out_file:
                out_file = "bond_schedule.csv"
            export_schedule_to_csv(schedule, out_file)
            print(f"Saved amortization schedule to '{out_file}'.")

        print("\nThank you for using Bond Discount Calculator!")

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nExiting: {e}")


def main():
    parser = argparse.ArgumentParser(description="Bond Discount Calculator & Amortization Schedule")
    parser.add_argument("--cli", action="store_true", help="Launch in interactive command-line terminal mode")
    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        app = BondCalculatorApp()
        app.mainloop()


if __name__ == "__main__":
    main()
