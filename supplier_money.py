import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from database import (
    get_supplier, get_supplier_balance, get_purchase_order, get_po_due,
    record_supplier_payment, get_supplier_ledger
)
from stock import place_popup
from export_tools import export_table

PAYMENT_METHODS = ["Cash", "UPI", "Bank Transfer", "Cheque", "Card"]

def show_time(text):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except (ValueError, TypeError):
        return ""

# popup to pay a supplier, po_id is given when the payment is for one order
def open_payment_dialog(root, current_user, supplier_id, po_id=None, on_done=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can record supplier payments.")
        return

    supplier = get_supplier(supplier_id)
    if supplier is None:
        messagebox.showerror("Not Found", "This supplier no longer exists.")
        return

    balance = get_supplier_balance(supplier_id)
    order = get_purchase_order(po_id) if po_id else None
    po_due = get_po_due(po_id) if po_id else 0

    if balance <= 0:
        messagebox.showinfo("Nothing Owed", f"You don't owe '{supplier[1]}' anything right now.")
        return
    if order and po_due <= 0:
        messagebox.showinfo("Nothing Due", f"{order[1]} has no unpaid amount (nothing received yet, or already paid).")
        return

    popup = tk.Toplevel(root)
    popup.title("Pay Supplier")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.resizable(False, False)
    place_popup(root, popup, 430, 560)

    card = tk.Frame(popup, bg=CARD, padx=22, pady=20, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    tk.Label(card, text="💵  Pay Supplier", font=FONT_HEADING, bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(card, text=supplier[1], font=FONT_BODY, bg=CARD, fg=PURPLE_LIGHT).pack(anchor="w", pady=(2, 0))
    tk.Label(card, text=f"Total balance owed:  ₹{balance:,.2f}", font=FONT_SMALL, bg=CARD, fg=YELLOW).pack(anchor="w", pady=(2, 0))
    if order:
        tk.Label(card, text=f"For {order[1]}  ·  due ₹{po_due:,.2f}", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w")

    def field(label):
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(12, 2))

    field("AMOUNT (₹)")
    amount_entry = tk.Entry(card, width=16, font=FONT_INPUT)
    style_entry(amount_entry)
    amount_entry.insert(0, f"{po_due if order else balance:.2f}")
    amount_entry.pack(anchor="w", ipady=5)

    field("PAID BY")
    method_var = tk.StringVar(value=PAYMENT_METHODS[0])
    ttk.Combobox(card, textvariable=method_var, values=PAYMENT_METHODS, state="readonly", width=24, font=FONT_INPUT).pack(anchor="w", ipady=3)

    field("REFERENCE (cheque no / transaction id)")
    ref_entry = tk.Entry(card, width=32, font=FONT_INPUT)
    style_entry(ref_entry)
    ref_entry.pack(anchor="w", ipady=5)

    field("NOTE (optional)")
    note_entry = tk.Entry(card, width=32, font=FONT_INPUT)
    style_entry(note_entry)
    note_entry.pack(anchor="w", ipady=5)

    error_label = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=RED, wraplength=360, justify="left")
    error_label.pack(anchor="w", pady=(10, 0))

    def save():
        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            error_label.config(text="⚠  Enter the amount as a number.")
            return

        try:
            record_supplier_payment(
                supplier_id, amount, method_var.get(), ref_entry.get().strip(),
                note_entry.get().strip(), current_user["username"], po_id
            )
        except ValueError as e:
            error_label.config(text=f"⚠  {e}")
            return

        popup.destroy()
        messagebox.showinfo("Payment Saved", f"₹{amount:,.2f} paid to {supplier[1]}.")
        if on_done:
            on_done()

    btn_row = tk.Frame(card, bg=CARD)
    btn_row.pack(fill="x", pady=(14, 0))
    tk.Button(btn_row, text="💾  Save Payment", padx=16, pady=7, command=save, **BTN_PRIMARY).pack(side="left", padx=(0, 10))
    tk.Button(btn_row, text="Cancel", padx=16, pady=7, command=popup.destroy, **BTN_SECONDARY).pack(side="left")

    amount_entry.focus_set()

# statement of everything bought from and paid to one supplier
def open_ledger_window(root, supplier_id):
    supplier = get_supplier(supplier_id)
    if supplier is None:
        return

    popup = tk.Toplevel(root)
    popup.title(f"Supplier Ledger — {supplier[1]}")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.minsize(700, 420)
    place_popup(root, popup, 860, 540)

    tk.Label(popup, text=f"📒  {supplier[1]}", font=FONT_HEADING, bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 2))

    balance = get_supplier_balance(supplier_id)
    tk.Label(
        popup, text=f"Balance owed:  ₹{balance:,.2f}", font=FONT_BODY, bg=BG,
        fg=YELLOW if balance > 0 else GREEN
    ).pack(anchor="w", padx=16, pady=(0, 8))

    # buttons first so they stay visible
    bottom = tk.Frame(popup, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    frame = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    cols = ("Date", "Description", "Owed (+)", "Paid (−)", "Balance")
    table = ttk.Treeview(frame, columns=cols, show="headings")
    widths = {"Date": 150, "Description": 330, "Owed (+)": 100, "Paid (−)": 100, "Balance": 110}
    for col in cols:
        table.heading(col, text=col)
        table.column(col, width=widths[col], anchor="w" if col == "Description" else "center")

    scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    table.pack(fill="both", expand=True)

    ledger = get_supplier_ledger(supplier_id)
    export_rows = []
    for when, label, owed, paid, running in ledger:
        table.insert("", "end", values=(
            show_time(when), label,
            f"₹{owed:,.2f}" if owed else "", f"₹{paid:,.2f}" if paid else "", f"₹{running:,.2f}"
        ))
        export_rows.append((when if when != "0000" else "", label, owed, paid, running))

    tk.Label(bottom, text=f"{len(ledger)} entr{'y' if len(ledger) == 1 else 'ies'}", font=FONT_SMALL, bg=BG, fg=TEXT3).pack(side="left")
    tk.Button(bottom, text="Close", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=16, pady=6, command=popup.destroy).pack(side="right")
    tk.Button(
        bottom, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0, padx=12, pady=6,
        command=lambda: export_table(["Date", "Description", "Owed", "Paid", "Balance"], export_rows, f"Ledger_{supplier_id}.csv")
    ).pack(side="right", padx=(0, 10))
