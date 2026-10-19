import datetime
import os
import sys
import tkinter as tk
from tkinter import ttk
from styles import *
from database import get_daily_sales, get_top_products

RANGES = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}

def day_label(iso_date):
    return datetime.date.fromisoformat(iso_date).strftime("%d %b")

def rupees(amount):
    return f"₹{amount:,.0f}"

def short_name(name, limit=24):
    return name if len(name) <= limit else name[:limit - 1] + "…"

# the pip command for the Python that is running this app
# (the app and "pip" in a console are often two different Pythons)
def pip_command():
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        exe = os.path.join(os.path.dirname(exe), "python.exe")
    return f'"{exe}" -m pip install matplotlib'

# the card on the dashboard with the two charts
# if matplotlib isn't installed it shows the same numbers as plain text
def build_sales_insights(parent):

    card = tk.Frame(parent, bg=CARD, padx=18, pady=14, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="x", padx=20, pady=(0, 14))

    # ---- header with the controls
    header = tk.Frame(card, bg=CARD)
    header.pack(fill="x")

    tk.Label(header, text="📈  Sales Insights", font=FONT_SUB, bg=CARD, fg=TEXT2).pack(side="left")

    range_var = tk.StringVar(value="Last 30 days")
    range_box = ttk.Combobox(header, textvariable=range_var, values=list(RANGES), state="readonly", width=14, font=FONT_SMALL)
    range_box.pack(side="right", ipady=2)

    metric_var = tk.StringVar(value="qty")
    for text, value in (("Revenue", "revenue"), ("Units sold", "qty")):
        tk.Radiobutton(
            header, text=text, variable=metric_var, value=value, font=FONT_SMALL,
            bg=CARD, fg=TEXT3, selectcolor=BG, activebackground=CARD, activeforeground=TEXT,
            bd=0, highlightthickness=0, command=lambda: draw()
        ).pack(side="right", padx=(0, 10))
    tk.Label(header, text="Top products by:", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(side="right", padx=(0, 6))

    range_box.bind("<<ComboboxSelected>>", lambda e: draw())

    # ---- two columns: sales trend on the left, top products on the right
    body = tk.Frame(card, bg=CARD)
    body.pack(fill="x", pady=(10, 0))
    body.columnconfigure(0, weight=1, uniform="charts")
    body.columnconfigure(1, weight=1, uniform="charts")

    left = tk.Frame(body, bg=CARD)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    right = tk.Frame(body, bg=CARD)
    right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    sales_title = tk.Label(left, text="", font=FONT_SMALL, bg=CARD, fg=TEXT3, anchor="w")
    sales_title.pack(fill="x")
    top_title = tk.Label(right, text="", font=FONT_SMALL, bg=CARD, fg=TEXT3, anchor="w")
    top_title.pack(fill="x")

    # matplotlib is optional
    try:
        from matplotlib.figure import Figure
        from matplotlib.ticker import FuncFormatter
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    except ImportError:
        Figure = None

    card.charts = {"range_var": range_var, "metric_var": metric_var}

    # ------------------------------------------------------------------
    # with matplotlib
    # ------------------------------------------------------------------
    if Figure is not None:
        fig_sales = Figure(figsize=(5.6, 3.0), dpi=100, facecolor=CARD)
        fig_top = Figure(figsize=(5.6, 3.0), dpi=100, facecolor=CARD)

        canvas_sales = FigureCanvasTkAgg(fig_sales, master=left)
        canvas_sales.get_tk_widget().pack(fill="both", expand=True)
        canvas_top = FigureCanvasTkAgg(fig_top, master=right)
        canvas_top.get_tk_widget().pack(fill="both", expand=True)

        card.charts["fig_sales"] = fig_sales
        card.charts["fig_top"] = fig_top

        # dark look to match the app
        def style_axes(ax):
            ax.set_facecolor(CARD)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(BORDER)
            ax.tick_params(colors=TEXT3, labelsize=8)
            ax.grid(True, color=BORDER, linewidth=0.6, alpha=0.8)
            ax.set_axisbelow(True)

        def empty_message(ax, text):
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            ax.text(0.5, 0.5, text, transform=ax.transAxes, ha="center", va="center", color=TEXT_DIM, fontsize=11)

        def draw_sales(daily):
            fig_sales.clear()
            ax = fig_sales.add_subplot(111)
            style_axes(ax)

            totals = [d[1] for d in daily]
            positions = list(range(len(daily)))

            if sum(totals) == 0:
                empty_message(ax, "No sales in this period yet")
            else:
                ax.plot(
                    positions, totals, color=PURPLE_LIGHT, linewidth=2,
                    marker="o" if len(positions) <= 31 else None, markersize=4
                )
                ax.fill_between(positions, totals, color=PURPLE_LIGHT, alpha=0.18)
                ax.set_ylim(bottom=0)

                # about 8 date labels, counted back from today so today is always shown
                step = max(1, len(positions) // 8)
                ticks = positions[::-1][::step][::-1]
                ax.set_xticks(ticks)
                ax.set_xticklabels([day_label(daily[i][0]) for i in ticks], fontsize=8)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: rupees(value)))

            fig_sales.subplots_adjust(left=0.14, right=0.97, top=0.96, bottom=0.14)
            canvas_sales.draw_idle()

        def draw_top(top, by):
            fig_top.clear()
            ax = fig_top.add_subplot(111)
            style_axes(ax)

            if not top:
                empty_message(ax, "No sales in this period yet")
            else:
                values = [row[2] if by == "revenue" else row[1] for row in top]
                names = [short_name(row[0]) for row in top]
                rows = list(range(len(values)))

                ax.barh(rows, values, color=PURPLE_LIGHT, height=0.6)
                ax.set_yticks(rows)
                ax.set_yticklabels(names, fontsize=9, color=TEXT2)
                ax.invert_yaxis()                       # best seller at the top
                ax.grid(False)
                ax.grid(True, axis="x", color=BORDER, linewidth=0.6, alpha=0.8)
                ax.set_xlim(0, max(values) * 1.28)

                for row, value in zip(rows, values):
                    text = rupees(value) if by == "revenue" else f"{value:,}"
                    ax.text(value, row, f"  {text}", va="center", color=TEXT, fontsize=9)

                if by == "revenue":
                    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: rupees(value)))

            fig_top.subplots_adjust(left=0.36, right=0.97, top=0.96, bottom=0.12)
            canvas_top.draw_idle()

        draw_sales_chart = draw_sales
        draw_top_chart = draw_top

    # ------------------------------------------------------------------
    # without matplotlib: the same numbers as text with little bars
    # ------------------------------------------------------------------
    else:
        version = sys.version.split()[0]
        notice = tk.Frame(card, bg=CARD)
        notice.pack(fill="x", pady=(6, 0))

        tk.Label(
            notice, text=f"Charts need matplotlib, and the Python running this app (version {version}) doesn't have it. "
                         "Showing a text summary instead.\nInstall it for this Python by running this in a command prompt:",
            font=("Segoe UI", 9), bg=CARD, fg=YELLOW, justify="left", anchor="w"
        ).pack(anchor="w")

        command_row = tk.Frame(notice, bg=CARD)
        command_row.pack(fill="x", pady=(4, 0))
        tk.Label(command_row, text=pip_command(), font=("Courier New", 9), bg=BG, fg=TEXT, padx=8, pady=4).pack(side="left")

        def copy_command():
            card.clipboard_clear()
            card.clipboard_append(pip_command())

        tk.Button(
            command_row, text="📋  Copy", font=("Segoe UI", 9), bg=PURPLE_BG, fg=PURPLE_PALE,
            relief="flat", cursor="hand2", bd=0, padx=8, pady=3, command=copy_command
        ).pack(side="left", padx=8)

        sales_text = tk.Label(left, text="", font=("Courier New", 9), bg=CARD, fg=TEXT2, justify="left", anchor="w")
        sales_text.pack(fill="x", pady=(6, 0))
        top_text = tk.Label(right, text="", font=("Courier New", 9), bg=CARD, fg=TEXT2, justify="left", anchor="w")
        top_text.pack(fill="x", pady=(6, 0))

        def bar(value, biggest, width=22):
            return "█" * int(round(width * value / biggest)) if biggest else ""

        def draw_sales_chart(daily):
            recent = daily[-14:]
            biggest = max(d[1] for d in recent)
            lines = [f"{day_label(d[0])}  {bar(d[1], biggest):<22} {rupees(d[1])}" for d in recent]
            sales_text.config(text="\n".join(lines) if biggest else "No sales in this period yet")

        def draw_top_chart(top, by):
            if not top:
                top_text.config(text="No sales in this period yet")
                return
            values = [row[2] if by == "revenue" else row[1] for row in top]
            lines = []
            for row, value in zip(top, values):
                shown = rupees(value) if by == "revenue" else f"{value:,}"
                lines.append(f"{short_name(row[0], 16):<16} {bar(value, max(values)):<22} {shown}")
            top_text.config(text="\n".join(lines))

    # ------------------------------------------------------------------
    # fills in both charts and the small headings above them
    # ------------------------------------------------------------------
    def draw():
        days = RANGES[range_var.get()]
        by = metric_var.get()

        daily = get_daily_sales(days)
        top = get_top_products(days, 5, by)

        total = sum(d[1] for d in daily)
        bills = sum(d[2] for d in daily)
        if total:
            best = max(daily, key=lambda d: d[1])
            sales_title.config(text=f"Daily sales  ·  ₹{total:,.2f} from {bills} bills  ·  best day {day_label(best[0])} (₹{best[1]:,.2f})")
        else:
            sales_title.config(text="Daily sales")

        top_title.config(text="Top 5 products  ·  by " + ("revenue" if by == "revenue" else "units sold"))

        draw_sales_chart(daily)
        draw_top_chart(top, by)

    card.redraw = draw
    draw()
    return card
