import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from database import get_product, adjust_stock, get_stock_movements
from export_tools import export_table

ADD_REASONS = ["Received from supplier", "Customer return", "Stock count correction", "Other"]
REMOVE_REASONS = ["Damaged", "Expired", "Lost / stolen", "Stock count correction", "Other"]

# puts a popup in the middle of the main window
def place_popup(root, popup, width, height):
    popup.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - width) // 2
    y = root.winfo_rooty() + (root.winfo_height() - height) // 2
    popup.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    # grab_set fails if the window isn't on screen yet, so wait for it first
    try:
        popup.wait_visibility()
        popup.grab_set()
    except tk.TclError:
        pass

# popup to add or remove stock by hand
def open_adjust_dialog(root, current_user, product_id, on_done=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can adjust stock.")
        return

    product = get_product(product_id)
    if not product:
        messagebox.showerror("Not Found", "This product no longer exists.")
        return

    name = product[1]
    current_qty = product[6]

    popup = tk.Toplevel(root)
    popup.title("Adjust Stock")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.resizable(False, False)
    place_popup(root, popup, 420, 460)

    card = tk.Frame(popup, bg=CARD, padx=22, pady=20, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    tk.Label(card, text="± Adjust Stock", font=FONT_HEADING, bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(card, text=f"{name}  ({product_id})", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(2, 0))
    tk.Label(card, text=f"Current stock: {current_qty} {product[8] or ''}", font=FONT_BODY, bg=CARD, fg=PURPLE_LIGHT).pack(anchor="w", pady=(2, 12))

    mode_var = tk.StringVar(value="add")
    mode_row = tk.Frame(card, bg=CARD)
    mode_row.pack(fill="x")

    reason_var = tk.StringVar(value=ADD_REASONS[0])

    def change_mode():
        reasons = ADD_REASONS if mode_var.get() == "add" else REMOVE_REASONS
        reason_combo.config(values=reasons)
        reason_var.set(reasons[0])
        update_preview()

    for text, value in [("➕  Add stock", "add"), ("➖  Remove stock", "remove")]:
        tk.Radiobutton(
            mode_row, text=text, variable=mode_var, value=value, command=change_mode,
            font=FONT_BODY, bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
            activeforeground=TEXT, bd=0, highlightthickness=0
        ).pack(side="left", padx=(0, 14))

    tk.Label(card, text="QUANTITY", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(12, 2))
    qty_entry = tk.Entry(card, width=12, font=FONT_INPUT)
    style_entry(qty_entry)
    qty_entry.pack(anchor="w", ipady=5)

    tk.Label(card, text="REASON", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(12, 2))
    reason_combo = ttk.Combobox(card, textvariable=reason_var, values=ADD_REASONS, state="readonly", width=30, font=FONT_INPUT)
    reason_combo.pack(anchor="w", ipady=3)

    tk.Label(card, text="NOTE (optional)", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(12, 2))
    note_entry = tk.Entry(card, width=34, font=FONT_INPUT)
    style_entry(note_entry)
    note_entry.pack(anchor="w", ipady=5)

    preview_label = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=TEXT3)
    preview_label.pack(anchor="w", pady=(10, 0))

    error_label = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=RED)
    error_label.pack(anchor="w")

    # works out the signed change from the radio button and the quantity box
    def read_change():
        try:
            amount = int(qty_entry.get().strip())
        except ValueError:
            return None
        if amount <= 0:
            return None
        return amount if mode_var.get() == "add" else -amount

    def update_preview(event=None):
        change = read_change()
        if change is None:
            preview_label.config(text="")
        else:
            preview_label.config(text=f"New stock will be: {current_qty + change}")

    qty_entry.bind("<KeyRelease>", update_preview)

    def save():
        change = read_change()
        if change is None:
            error_label.config(text="⚠  Enter a whole number greater than 0.")
            return
        try:
            adjust_stock(product_id, change, reason_var.get(), current_user["username"], note_entry.get().strip())
        except ValueError as e:
            error_label.config(text=f"⚠  {e}")
            return

        popup.destroy()
        messagebox.showinfo("Stock Updated", f"'{name}' stock changed by {change:+d}.")
        if on_done:
            on_done()

    btn_row = tk.Frame(card, bg=CARD)
    btn_row.pack(fill="x", pady=(10, 0))

    tk.Button(btn_row, text="💾  Save", padx=18, pady=7, command=save, **BTN_PRIMARY).pack(side="left", padx=(0, 10))
    tk.Button(btn_row, text="Cancel", padx=18, pady=7, command=popup.destroy, **BTN_SECONDARY).pack(side="left")

    qty_entry.focus_set()

# popup that lists the stock log, for one product or for all of them
def open_history_window(root, product_id=None):

    popup = tk.Toplevel(root)
    popup.configure(bg=BG)
    popup.transient(root)
    popup.minsize(760, 420)
    place_popup(root, popup, 900, 560)

    if product_id:
        product = get_product(product_id)
        title = f"Stock History — {product[1]}" if product else "Stock History"
    else:
        title = "Stock History — All Products"
    popup.title(title)

    tk.Label(popup, text=f"📋  {title}", font=FONT_HEADING, bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 8))

    # buttons go at the bottom first so they always stay visible
    bottom = tk.Frame(popup, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    table_frame = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    cols = ("Date & Time", "Product", "Change", "Stock After", "Reason", "Reference", "By")
    table = ttk.Treeview(table_frame, columns=cols, show="headings")
    widths = {"Date & Time": 150, "Product": 180, "Change": 70, "Stock After": 90, "Reason": 170, "Reference": 120, "By": 90}
    for col in cols:
        table.heading(col, text=col)
        table.column(col, width=widths[col], anchor="center")

    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    table.pack(fill="both", expand=True)

    table.tag_configure("plus", foreground=GREEN)
    table.tag_configure("minus", foreground=RED)

    rows = get_stock_movements(product_id)
    export_rows = []

    for created_at, pid, pname, change, after, reason, reference, user in rows:
        try:
            shown_time = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
        except (ValueError, TypeError):
            shown_time = created_at or ""

        table.insert("", "end", tags=("plus" if change > 0 else "minus",),
                     values=(shown_time, pname, f"{change:+d}", after, reason, reference or "", user or ""))
        export_rows.append((created_at, pid, pname, change, after, reason, reference or "", user or ""))

    tk.Label(bottom, text=f"{len(rows)} movement(s)", font=FONT_SMALL, bg=BG, fg=TEXT3).pack(side="left")

    tk.Button(
        bottom, text="Close", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE,
        relief="flat", cursor="hand2", bd=0, padx=16, pady=6, command=popup.destroy
    ).pack(side="right")

    tk.Button(
        bottom, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE, fg=TEXT,
        relief="flat", cursor="hand2", bd=0, padx=12, pady=6,
        command=lambda: export_table(
            ["Date & Time", "Product ID", "Product", "Change", "Stock After", "Reason", "Reference", "By"],
            export_rows, "Stock_History.csv"
        )
    ).pack(side="right", padx=(0, 10))
