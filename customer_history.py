import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from database import (
    get_customer, get_customer_summary, get_customer_bills, get_points_history,
    get_sale_items, adjust_customer_points
)
from stock import place_popup
from export_tools import export_table

ADD_REASONS = ["Welcome bonus", "Goodwill / correction", "Other"]
REMOVE_REASONS = ["Points expired", "Goodwill / correction", "Other"]

def show_time(text):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except (ValueError, TypeError):
        return ""

# popup with everything a customer bought, plus their points
# on_change is called when the points were adjusted here (so the page can refresh)
def open_customer_history(root, current_user, customer_id, on_change=None):
    customer = get_customer(customer_id)
    if customer is None:
        messagebox.showerror("Not Found", "This customer no longer exists.")
        return

    total, count, average, last_date = get_customer_summary(customer_id)
    points = customer[5] or 0

    popup = tk.Toplevel(root)
    popup.title(f"Customer History — {customer[1]}")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.minsize(760, 520)
    place_popup(root, popup, 920, 640)

    # buttons first so they stay visible
    bottom = tk.Frame(popup, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    header = tk.Frame(popup, bg=CARD, padx=18, pady=12, highlightthickness=1, highlightbackground=BORDER)
    header.pack(fill="x", padx=16, pady=(16, 10))
    tk.Label(header, text=f"👤  {customer[1]}", font=("Segoe UI", 15, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(header, text=f"{customer[0]}  ·  {customer[2] or '—'}  ·  {customer[3] or '—'}", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(2, 0))

    stats = tk.Frame(popup, bg=BG)
    stats.pack(fill="x", padx=16, pady=(0, 10))
    for i, (label, value, color) in enumerate([
        ("Lifetime spent", f"₹{total:,.2f}", GREEN),
        ("Bills", str(count), TEAL),
        ("Average bill", f"₹{average:,.2f}", PURPLE_LIGHT),
        ("Last purchase", last_date or "—", TEXT2),
        ("Loyalty points", str(points), YELLOW),
    ]):
        card = tk.Frame(stats, bg=CARD, padx=12, pady=8, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="ew")
        stats.columnconfigure(i, weight=1)
        tk.Frame(card, bg=color, height=2).pack(fill="x", pady=(0, 6))
        tk.Label(card, text=value, font=("Segoe UI", 13, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(card, text=label, font=FONT_SMALL, bg=CARD, fg=color).pack(anchor="w")

    book = ttk.Notebook(popup)
    book.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    # ---- tab 1: purchases
    bills_tab = tk.Frame(book, bg=CARD)
    book.add(bills_tab, text="  🧾  Purchases  ")

    bill_cols = ("Bill No", "Date", "Time", "Items", "Total", "Payment", "Points")
    bill_table = ttk.Treeview(bills_tab, columns=bill_cols, show="headings")
    for col, w in zip(bill_cols, (90, 110, 90, 60, 100, 100, 110)):
        bill_table.heading(col, text=col)
        bill_table.column(col, width=w, anchor="center")
    bill_scroll = ttk.Scrollbar(bills_tab, orient="vertical", command=bill_table.yview)
    bill_table.configure(yscrollcommand=bill_scroll.set)
    bill_scroll.pack(side="right", fill="y")
    bill_table.pack(fill="both", expand=True)

    bills = get_customer_bills(customer_id)
    for bill_no, date, time, qty, grand, method, earned, redeemed, sale_id in bills:
        points_text = []
        if earned:
            points_text.append(f"+{earned}")
        if redeemed:
            points_text.append(f"−{redeemed}")
        bill_table.insert("", "end", iid=str(sale_id), values=(
            bill_no, date, time, qty, f"₹{grand:,.2f}", method, " / ".join(points_text)
        ))

    if not bills:
        tk.Label(bills_tab, text="No purchases yet.", font=FONT_BODY, bg=CARD, fg=TEXT_DIM).place(relx=0.5, rely=0.5, anchor="center")

    # double-click a bill to see what was on it
    def show_bill_items(event=None):
        selected = bill_table.selection()
        if not selected:
            return
        bill_no = bill_table.item(selected[0], "values")[0]

        items_popup = tk.Toplevel(popup)
        items_popup.title(f"Items — {bill_no}")
        items_popup.configure(bg=BG)
        items_popup.transient(popup)
        place_popup(root, items_popup, 560, 380)

        tk.Label(items_popup, text=f"🧾  {bill_no}", font=FONT_HEADING, bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 8))
        tk.Button(items_popup, text="Close", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=16, pady=6, command=items_popup.destroy).pack(side="bottom", anchor="e", padx=16, pady=(0, 14))

        frame = tk.Frame(items_popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        item_table = ttk.Treeview(frame, columns=("Product", "Qty", "Price", "Total"), show="headings")
        for col, w in zip(("Product", "Qty", "Price", "Total"), (240, 60, 90, 100)):
            item_table.heading(col, text=col)
            item_table.column(col, width=w, anchor="center")
        item_table.pack(fill="both", expand=True)
        for pid, name, qty, price, line_total in get_sale_items(int(selected[0])):
            item_table.insert("", "end", values=(name, qty, f"₹{price:.2f}", f"₹{line_total:.2f}"))

    bill_table.bind("<Double-1>", show_bill_items)

    # ---- tab 2: points
    points_tab = tk.Frame(book, bg=CARD)
    book.add(points_tab, text="  ⭐  Points  ")

    point_cols = ("Date & Time", "Change", "Balance", "Reason", "Reference", "By")
    point_table = ttk.Treeview(points_tab, columns=point_cols, show="headings")
    for col, w in zip(point_cols, (160, 80, 80, 200, 110, 90)):
        point_table.heading(col, text=col)
        point_table.column(col, width=w, anchor="center")
    point_scroll = ttk.Scrollbar(points_tab, orient="vertical", command=point_table.yview)
    point_table.configure(yscrollcommand=point_scroll.set)
    point_scroll.pack(side="right", fill="y")
    point_table.pack(fill="both", expand=True)

    point_table.tag_configure("plus", foreground=GREEN)
    point_table.tag_configure("minus", foreground=RED)

    history = get_points_history(customer_id)
    for created_at, change, balance, reason, reference, user in history:
        point_table.insert("", "end", tags=("plus" if change > 0 else "minus",), values=(
            show_time(created_at), f"{change:+d}", balance, reason, reference or "", user or ""
        ))

    if not history:
        tk.Label(points_tab, text="No points activity yet.", font=FONT_BODY, bg=CARD, fg=TEXT_DIM).place(relx=0.5, rely=0.5, anchor="center")

    # ---- buttons
    tk.Label(bottom, text=f"{count} bill(s)  ·  double-click a bill to see its items", font=FONT_SMALL, bg=BG, fg=TEXT3).pack(side="left")
    tk.Button(bottom, text="Close", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=16, pady=6, command=popup.destroy).pack(side="right")

    tk.Button(
        bottom, text="⬇  Export Bills CSV", font=FONT_SMALL, bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0, padx=12, pady=6,
        command=lambda: export_table(
            ["Bill No", "Date", "Time", "Items", "Total", "Payment", "Points Earned", "Points Used"],
            [b[:8] for b in bills], f"Bills_{customer_id}.csv"
        )
    ).pack(side="right", padx=(0, 10))

    if can_edit(current_user):
        def adjust():
            def done():
                popup.destroy()
                if on_change:
                    on_change()
                open_customer_history(root, current_user, customer_id, on_change)
            open_points_dialog(root, current_user, customer_id, done)

        tk.Button(bottom, text="⭐  Adjust Points", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=12, pady=6, command=adjust).pack(side="right", padx=(0, 10))

# popup to add or remove points by hand
def open_points_dialog(root, current_user, customer_id, on_done=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can adjust points.")
        return

    customer = get_customer(customer_id)
    if customer is None:
        messagebox.showerror("Not Found", "This customer no longer exists.")
        return

    current_points = customer[5] or 0

    popup = tk.Toplevel(root)
    popup.title("Adjust Points")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.resizable(False, False)
    place_popup(root, popup, 420, 430)

    card = tk.Frame(popup, bg=CARD, padx=22, pady=20, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    tk.Label(card, text="⭐  Adjust Points", font=FONT_HEADING, bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(card, text=f"{customer[1]}  ({customer[0]})", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(2, 0))
    tk.Label(card, text=f"Current points: {current_points}", font=FONT_BODY, bg=CARD, fg=YELLOW).pack(anchor="w", pady=(2, 12))

    mode_var = tk.StringVar(value="add")
    reason_var = tk.StringVar(value=ADD_REASONS[0])
    mode_row = tk.Frame(card, bg=CARD)
    mode_row.pack(fill="x")

    def change_mode():
        reasons = ADD_REASONS if mode_var.get() == "add" else REMOVE_REASONS
        reason_combo.config(values=reasons)
        reason_var.set(reasons[0])
        update_preview()

    for text, value in [("➕  Add points", "add"), ("➖  Remove points", "remove")]:
        tk.Radiobutton(
            mode_row, text=text, variable=mode_var, value=value, command=change_mode,
            font=FONT_BODY, bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
            activeforeground=TEXT, bd=0, highlightthickness=0
        ).pack(side="left", padx=(0, 14))

    tk.Label(card, text="POINTS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(12, 2))
    amount_entry = tk.Entry(card, width=12, font=FONT_INPUT)
    style_entry(amount_entry)
    amount_entry.pack(anchor="w", ipady=5)

    tk.Label(card, text="REASON", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(12, 2))
    reason_combo = ttk.Combobox(card, textvariable=reason_var, values=ADD_REASONS, state="readonly", width=28, font=FONT_INPUT)
    reason_combo.pack(anchor="w", ipady=3)

    preview_label = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=TEXT3)
    preview_label.pack(anchor="w", pady=(10, 0))
    error_label = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=RED)
    error_label.pack(anchor="w")

    def read_change():
        text = amount_entry.get().strip()
        if not text.isdigit() or int(text) <= 0:
            return None
        return int(text) if mode_var.get() == "add" else -int(text)

    def update_preview(event=None):
        change = read_change()
        preview_label.config(text="" if change is None else f"New balance will be: {current_points + change}")

    amount_entry.bind("<KeyRelease>", update_preview)

    def save():
        change = read_change()
        if change is None:
            error_label.config(text="⚠  Enter a whole number greater than 0.")
            return
        try:
            adjust_customer_points(customer_id, change, reason_var.get(), current_user["username"])
        except ValueError as e:
            error_label.config(text=f"⚠  {e}")
            return

        popup.destroy()
        messagebox.showinfo("Points Updated", f"{customer[1]}'s points changed by {change:+d}.")
        if on_done:
            on_done()

    btn_row = tk.Frame(card, bg=CARD)
    btn_row.pack(fill="x", pady=(10, 0))
    tk.Button(btn_row, text="💾  Save", padx=18, pady=7, command=save, **BTN_PRIMARY).pack(side="left", padx=(0, 10))
    tk.Button(btn_row, text="Cancel", padx=18, pady=7, command=popup.destroy, **BTN_SECONDARY).pack(side="left")

    amount_entry.focus_set()
