import datetime
import math
import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from database import (
    get_purchase_orders, get_purchase_order, get_po_items, get_po_payments, get_po_due,
    create_purchase_order, update_purchase_order, set_po_status, receive_po_items,
    get_all_supplier_balances, load_suppliers, load_products
)
from supplier_money import open_payment_dialog, show_time
from stock import place_popup
from export_tools import export_table

SEARCH_HINT = "Search PO number or supplier..."
STATUS_LIST = ["All Statuses", "Draft", "Ordered", "Partially Received", "Received", "Cancelled"]

# row colours for each status
STATUS_COLORS = {
    "Draft": TEXT3,
    "Ordered": TEAL,
    "Partially Received": YELLOW,
    "Received": GREEN,
    "Cancelled": RED,
}

def to_number(text):
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None

# main purchase orders page
def show_purchases(root, current_user, go_home):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can open purchase orders.")
        return

    for widget in root.winfo_children():
        widget.destroy()

    def reload():
        show_purchases(root, current_user, go_home)

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "purchases", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "📋  Purchase Orders", current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=16)

    # stat cards
    all_orders = get_purchase_orders()
    open_orders = len([o for o in all_orders if o[5] in ("Ordered", "Partially Received")])
    owed = sum(b for b in get_all_supplier_balances().values() if b > 0)

    stats_row = tk.Frame(content, bg=BG)
    stats_row.pack(fill="x", pady=(0, 14))

    for i, (label, value, color) in enumerate([
        ("Open Orders", str(open_orders), TEAL),
        ("Total Orders", str(len(all_orders)), PURPLE_LIGHT),
        ("Owed to Suppliers", f"₹{owed:,.2f}", YELLOW),
    ]):
        card = tk.Frame(stats_row, bg=CARD, padx=16, pady=10, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="ew")
        stats_row.columnconfigure(i, weight=1)
        tk.Frame(card, bg=color, height=2).pack(fill="x", pady=(0, 8))
        tk.Label(card, text=value, font=("Segoe UI", 18, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(card, text=label, font=FONT_SMALL, bg=CARD, fg=color).pack(anchor="w")

    # toolbar
    toolbar = tk.Frame(content, bg=BG)
    toolbar.pack(fill="x", pady=(0, 10))

    search_frame = tk.Frame(toolbar, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    search_frame.pack(side="left")

    tk.Label(search_frame, text="🔍", bg=CARD, fg=TEXT3, font=("Segoe UI", 12)).pack(side="left", padx=(8, 2))

    search_entry = tk.Entry(search_frame, width=28, font=FONT_INPUT, bg=CARD, fg=TEXT_DIM, insertbackground=PURPLE_LIGHT, relief="flat", bd=0)
    search_entry.pack(side="left", ipady=7, padx=(0, 8))
    search_entry.insert(0, SEARCH_HINT)

    def on_focus_in(e):
        if search_entry.get() == SEARCH_HINT:
            search_entry.delete(0, tk.END)
            search_entry.config(fg=TEXT)

    def on_focus_out(e):
        if search_entry.get() == "":
            search_entry.insert(0, SEARCH_HINT)
            search_entry.config(fg=TEXT_DIM)

    search_entry.bind("<FocusIn>", on_focus_in)
    search_entry.bind("<FocusOut>", on_focus_out)
    search_entry.bind("<KeyRelease>", lambda e: refresh_table())

    status_var = tk.StringVar(value="All Statuses")
    status_combo = ttk.Combobox(toolbar, textvariable=status_var, values=STATUS_LIST, state="readonly", width=18, font=FONT_INPUT)
    status_combo.pack(side="left", padx=10, ipady=4)
    status_combo.bind("<<ComboboxSelected>>", lambda e: refresh_table())

    tk.Button(
        toolbar, text="➕  New Purchase Order", font=FONT_BUTTON, bg=PURPLE, fg=TEXT,
        relief="flat", cursor="hand2", bd=0, padx=16, pady=6,
        command=lambda: open_po_form(root, current_user, go_home, None)
    ).pack(side="right")

    # table
    table_frame = tk.Frame(content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True)

    cols = ("PO No", "Supplier", "Date", "Expected", "Status", "Items", "Total", "Received", "Paid", "Due")
    table = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)

    widths = {
        "PO No": 90, "Supplier": 170, "Date": 100, "Expected": 100, "Status": 130,
        "Items": 55, "Total": 100, "Received": 100, "Paid": 100, "Due": 100,
    }
    for col in cols:
        table.heading(col, text=col)
        table.column(col, width=widths[col], anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    table.pack(fill="both", expand=True)

    for status, color in STATUS_COLORS.items():
        table.tag_configure(status, foreground=color)

    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(fill="x", pady=10)

    def selected_po():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a purchase order first.")
            return None
        # the row id is the po_id
        return get_purchase_order(int(selected[0]))

    def edit_selected():
        order = selected_po()
        if order is None:
            return
        if order[4] != "Draft":
            messagebox.showwarning("Cannot Edit", "Only a Draft order can be edited.")
            return
        open_po_form(root, current_user, go_home, order[0])

    def change_status(new_status, question):
        order = selected_po()
        if order is None:
            return
        if not messagebox.askyesno(f"{new_status}", f"{question}\n\n{order[1]} — {order[3]}"):
            return
        try:
            set_po_status(order[0], new_status)
        except ValueError as e:
            messagebox.showerror("Cannot Change Status", str(e))
            return
        reload()

    def receive_selected():
        order = selected_po()
        if order is not None:
            open_receive_dialog(root, current_user, order[0], reload)

    def pay_selected():
        order = selected_po()
        if order is not None:
            open_payment_dialog(root, current_user, order[2], order[0], reload)

    def details_selected(event=None):
        selected = table.selection()
        if not selected:
            if event is None:
                messagebox.showwarning("No Selection", "Please select a purchase order first.")
            return
        open_po_details(root, current_user, int(selected[0]), reload)

    tk.Button(btn_row, text="👁  Details", command=details_selected, padx=12, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="✏  Edit Draft", command=edit_selected, padx=12, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="✔  Mark Ordered", command=lambda: change_status("Ordered", "Mark this order as sent to the supplier?"), padx=12, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="📥  Receive Stock", command=receive_selected, padx=12, pady=5, **BTN_SUCCESS).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="💵  Pay Supplier", command=pay_selected, padx=12, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="✕  Cancel Order", command=lambda: change_status("Cancelled", "Cancel this order? This cannot be undone."), padx=12, pady=5, **BTN_DANGER).pack(side="left")

    count_label = tk.Label(btn_row, text="", font=FONT_SMALL, bg=BG, fg=TEXT3)
    count_label.pack(side="right")

    shown = {"rows": []}
    tk.Button(
        btn_row, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE,
        relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
        command=lambda: export_table(
            ["PO No", "Supplier", "Order Date", "Expected", "Status", "Items", "Total", "Received Value", "Paid", "Due"],
            [r[1:] for r in shown["rows"]], "Purchase_Orders.csv"
        )
    ).pack(side="right", padx=(0, 10))

    table.bind("<Double-1>", details_selected)

    def refresh_table():
        keyword = search_entry.get()
        if keyword == SEARCH_HINT:
            keyword = ""
        status = status_var.get()
        orders = get_purchase_orders(None if status == "All Statuses" else status, keyword)

        for row in table.get_children():
            table.delete(row)

        for o in orders:
            table.insert("", "end", iid=str(o[0]), tags=(o[5],), values=(
                o[1], o[2], o[3], o[4] or "", o[5], o[6],
                f"₹{o[7]:,.2f}", f"₹{o[8]:,.2f}", f"₹{o[9]:,.2f}", f"₹{o[10]:,.2f}"
            ))

        shown["rows"] = orders
        count_label.config(text=f"{len(orders)} order(s)")

    refresh_table()

# new / edit draft order form
def open_po_form(root, current_user, go_home, po_id=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can create purchase orders.")
        return

    is_edit = po_id is not None
    order = None
    if is_edit:
        order = get_purchase_order(po_id)
        if order is None or order[4] != "Draft":
            messagebox.showwarning("Cannot Edit", "Only a Draft order can be edited.")
            return

    suppliers = load_suppliers()
    if not suppliers:
        messagebox.showwarning("No Suppliers", "Add a supplier first (Suppliers page), then create the order.")
        return

    form_title = f"✏  Edit {order[1]}" if is_edit else "➕  New Purchase Order"

    for widget in root.winfo_children():
        widget.destroy()

    def go_back():
        show_purchases(root, current_user, go_home)

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "purchases", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, form_title, current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=14)

    # ---- top card: supplier, expected date, notes
    top = tk.Frame(content, bg=CARD, padx=18, pady=14, highlightthickness=1, highlightbackground=BORDER)
    top.pack(fill="x", pady=(0, 12))
    top.columnconfigure(2, weight=1)

    tk.Label(top, text="SUPPLIER *", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).grid(row=0, column=0, sticky="w")
    supplier_values = [f"{s[0]}  —  {s[1]}" for s in suppliers]
    supplier_var = tk.StringVar()
    supplier_combo = ttk.Combobox(top, textvariable=supplier_var, values=supplier_values, state="readonly", width=30, font=FONT_INPUT)
    supplier_combo.grid(row=1, column=0, sticky="w", ipady=3, padx=(0, 18))

    tk.Label(top, text="EXPECTED DATE (e.g. 15 Oct 2026)", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).grid(row=0, column=1, sticky="w")
    expected_entry = tk.Entry(top, width=18, font=FONT_INPUT)
    style_entry(expected_entry)
    expected_entry.grid(row=1, column=1, sticky="w", ipady=5, padx=(0, 18))

    tk.Label(top, text="NOTES", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).grid(row=0, column=2, sticky="w")
    notes_entry = tk.Entry(top, font=FONT_INPUT)
    style_entry(notes_entry)
    notes_entry.grid(row=1, column=2, sticky="ew", ipady=5)

    # ---- body: product picker on the left, order lines on the right
    body = tk.Frame(content, bg=BG)
    body.pack(fill="both", expand=True)

    picker_card = tk.Frame(body, bg=CARD, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
    picker_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

    tk.Label(picker_card, text="📦  PICK PRODUCTS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(0, 6))

    search_entry = tk.Entry(picker_card, font=FONT_INPUT)
    style_entry(search_entry)
    search_entry.pack(fill="x", ipady=5, pady=(0, 8))

    pick_frame = tk.Frame(picker_card, bg=CARD)
    pick_frame.pack(fill="both", expand=True)

    pick_cols = ("ID", "Product", "Stock", "Cost")
    picker = ttk.Treeview(pick_frame, columns=pick_cols, show="headings", height=10)
    for col, w in zip(pick_cols, (70, 190, 60, 80)):
        picker.heading(col, text=col)
        picker.column(col, width=w, anchor="center")
    pick_scroll = ttk.Scrollbar(pick_frame, orient="vertical", command=picker.yview)
    picker.configure(yscrollcommand=pick_scroll.set)
    pick_scroll.pack(side="right", fill="y")
    picker.pack(fill="both", expand=True)

    add_row = tk.Frame(picker_card, bg=CARD)
    add_row.pack(fill="x", pady=(10, 0))

    tk.Label(add_row, text="Qty:", font=FONT_BODY, bg=CARD, fg=TEXT3).pack(side="left")
    qty_entry = tk.Entry(add_row, width=7, font=FONT_INPUT)
    style_entry(qty_entry)
    qty_entry.insert(0, "1")
    qty_entry.pack(side="left", padx=(4, 12), ipady=4)

    tk.Label(add_row, text="Unit cost ₹:", font=FONT_BODY, bg=CARD, fg=TEXT3).pack(side="left")
    cost_entry = tk.Entry(add_row, width=9, font=FONT_INPUT)
    style_entry(cost_entry)
    cost_entry.pack(side="left", padx=(4, 12), ipady=4)

    products = load_products()

    def refresh_picker(keyword=""):
        for row in picker.get_children():
            picker.delete(row)
        for p in products:
            if keyword and keyword.lower() not in p[1].lower() and keyword.lower() not in p[0].lower():
                continue
            picker.insert("", "end", iid=p[0], values=(p[0], p[1], p[6], f"₹{p[4]:.2f}"))

    refresh_picker()
    search_entry.bind("<KeyRelease>", lambda e: refresh_picker(search_entry.get().strip()))

    # picking a product fills in its usual purchase price
    def on_pick(event=None):
        selected = picker.selection()
        if not selected:
            return
        for p in products:
            if p[0] == selected[0]:
                cost_entry.delete(0, tk.END)
                cost_entry.insert(0, f"{p[4]:.2f}")
                break

    picker.bind("<<TreeviewSelect>>", on_pick)

    lines_card = tk.Frame(body, bg=CARD, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
    lines_card.pack(side="right", fill="both", expand=True)

    tk.Label(lines_card, text="🧾  ORDER LINES", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(0, 6))

    # bottom part of the lines card is packed first so it stays visible
    footer = tk.Frame(lines_card, bg=CARD)
    footer.pack(side="bottom", fill="x", pady=(10, 0))

    line_frame = tk.Frame(lines_card, bg=CARD)
    line_frame.pack(fill="both", expand=True)

    line_cols = ("Product", "Qty", "Unit Cost", "Total")
    line_table = ttk.Treeview(line_frame, columns=line_cols, show="headings", height=10)
    for col, w in zip(line_cols, (200, 60, 90, 100)):
        line_table.heading(col, text=col)
        line_table.column(col, width=w, anchor="center")
    line_scroll = ttk.Scrollbar(line_frame, orient="vertical", command=line_table.yview)
    line_table.configure(yscrollcommand=line_scroll.set)
    line_scroll.pack(side="right", fill="y")
    line_table.pack(fill="both", expand=True)

    lines = []   # dicts: id, name, qty, cost

    total_label = tk.Label(footer, text="Order total:  ₹0.00", font=("Segoe UI", 13, "bold"), bg=CARD, fg=GREEN)
    total_label.pack(anchor="e")

    error_label = tk.Label(footer, text="", font=FONT_SMALL, bg=CARD, fg=RED, wraplength=420, justify="left")
    error_label.pack(anchor="w", pady=(4, 0))

    def render_lines():
        for row in line_table.get_children():
            line_table.delete(row)
        total = 0
        for i, line in enumerate(lines):
            amount = line["qty"] * line["cost"]
            total += amount
            line_table.insert("", "end", iid=str(i), values=(line["name"], line["qty"], f"₹{line['cost']:.2f}", f"₹{amount:.2f}"))
        total_label.config(text=f"Order total:  ₹{total:,.2f}")

    def add_line():
        selected = picker.selection()
        if not selected:
            error_label.config(text="⚠  Pick a product from the list first.")
            return
        try:
            qty = int(qty_entry.get().strip())
        except ValueError:
            qty = 0
        cost = to_number(cost_entry.get().strip())

        if qty <= 0:
            error_label.config(text="⚠  Quantity must be a whole number above 0.")
            return
        if cost is None or cost < 0:
            error_label.config(text="⚠  Enter the unit cost as a number.")
            return

        product = next(p for p in products if p[0] == selected[0])

        # same product again: add to the quantity and use the new cost
        for line in lines:
            if line["id"] == product[0]:
                line["qty"] += qty
                line["cost"] = cost
                break
        else:
            lines.append({"id": product[0], "name": product[1], "qty": qty, "cost": cost})

        error_label.config(text="")
        qty_entry.delete(0, tk.END)
        qty_entry.insert(0, "1")
        render_lines()

    def remove_line():
        selected = line_table.selection()
        if not selected:
            return
        del lines[int(selected[0])]
        render_lines()

    tk.Button(add_row, text="➕  Add to Order", font=FONT_SMALL, bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0, padx=10, pady=5, command=add_line).pack(side="left")
    tk.Button(footer, text="✕  Remove Selected Line", font=FONT_SMALL, bg=RED_BG, fg=RED, relief="flat", cursor="hand2", bd=0, padx=10, pady=4, command=remove_line).pack(anchor="w")

    # prefill when editing
    if is_edit:
        for value in supplier_values:
            if value.startswith(order[2] + "  —  "):
                supplier_var.set(value)
        expected_entry.insert(0, order[6] or "")
        notes_entry.insert(0, order[8] or "")
        for item in get_po_items(po_id):
            lines.append({"id": item[1], "name": item[2], "qty": item[3], "cost": item[4]})
        render_lines()

    def save(status):
        if not supplier_var.get():
            error_label.config(text="⚠  Please choose a supplier.")
            return

        expected = expected_entry.get().strip()
        if expected:
            try:
                expected = datetime.datetime.strptime(expected, "%d %b %Y").strftime("%d %b %Y")
            except ValueError:
                error_label.config(text="⚠  Write the date like 15 Oct 2026, or leave it empty.")
                return

        supplier_id = supplier_var.get().split("  —  ")[0]
        notes = notes_entry.get().strip()

        try:
            if is_edit:
                update_purchase_order(po_id, supplier_id, expected, notes, lines, status)
            else:
                create_purchase_order(supplier_id, expected, notes, lines, current_user["username"], status)
        except ValueError as e:
            error_label.config(text=f"⚠  {e}")
            return

        messagebox.showinfo("Saved", f"Order saved as {status}.")
        go_back()

    btn_row = tk.Frame(footer, bg=CARD)
    btn_row.pack(fill="x", pady=(10, 0))

    tk.Button(btn_row, text="💾  Save Draft", padx=14, pady=7, command=lambda: save("Draft"), **BTN_SECONDARY).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="✔  Save & Mark Ordered", padx=14, pady=7, command=lambda: save("Ordered"), **BTN_PRIMARY).pack(side="left", padx=(0, 8))
    tk.Button(btn_row, text="← Back", padx=14, pady=7, command=go_back, **BTN_SECONDARY).pack(side="left")

# popup to receive the stock (a part of the order is fine)
def open_receive_dialog(root, current_user, po_id, on_done=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can receive stock.")
        return

    order = get_purchase_order(po_id)
    if order is None:
        messagebox.showerror("Not Found", "This order no longer exists.")
        return
    if order[4] not in ("Ordered", "Partially Received"):
        messagebox.showwarning("Cannot Receive", f"Stock can't be received on a {order[4]} order.\nMark it as Ordered first.")
        return

    waiting = [i for i in get_po_items(po_id) if i[5] < i[3]]

    popup = tk.Toplevel(root)
    popup.title(f"Receive Stock — {order[1]}")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.minsize(640, 380)
    place_popup(root, popup, 760, 560)

    tk.Label(popup, text=f"📥  Receive Stock — {order[1]}", font=FONT_HEADING, bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 2))
    tk.Label(popup, text=f"{order[3]}  ·  enter how many of each item arrived", font=FONT_SMALL, bg=BG, fg=TEXT3).pack(anchor="w", padx=16, pady=(0, 8))

    # buttons packed first so they stay visible
    bottom = tk.Frame(popup, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    update_var = tk.BooleanVar(value=True)
    tk.Checkbutton(
        popup, text="Update each product's purchase price to this order's cost", variable=update_var,
        font=FONT_SMALL, bg=BG, fg=TEXT2, selectcolor=BG2, activebackground=BG, activeforeground=TEXT,
        bd=0, highlightthickness=0
    ).pack(side="bottom", anchor="w", padx=16, pady=(0, 6))

    error_label = tk.Label(popup, text="", font=FONT_SMALL, bg=BG, fg=RED)
    error_label.pack(side="bottom", anchor="w", padx=16)

    card = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="both", expand=True, padx=16, pady=(0, 10))
    inner = make_scrollable(card, CARD)

    for col, text in enumerate(["Product", "Ordered", "Received", "Still expected", "Receiving now"]):
        tk.Label(inner, text=text, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).grid(row=0, column=col, padx=10, pady=(10, 6), sticky="w")
    inner.columnconfigure(0, weight=1)

    entries = {}
    for r, (item_id, product_id, name, quantity, cost, got) in enumerate(waiting, start=1):
        tk.Label(inner, text=name, font=FONT_BODY, bg=CARD, fg=TEXT).grid(row=r, column=0, padx=10, pady=4, sticky="w")
        tk.Label(inner, text=str(quantity), font=FONT_BODY, bg=CARD, fg=TEXT2).grid(row=r, column=1, padx=10, sticky="w")
        tk.Label(inner, text=str(got), font=FONT_BODY, bg=CARD, fg=TEXT2).grid(row=r, column=2, padx=10, sticky="w")
        tk.Label(inner, text=str(quantity - got), font=FONT_BODY, bg=CARD, fg=YELLOW).grid(row=r, column=3, padx=10, sticky="w")

        entry = tk.Entry(inner, width=8, font=FONT_INPUT)
        style_entry(entry)
        entry.insert(0, str(quantity - got))
        entry.grid(row=r, column=4, padx=10, pady=4, sticky="w", ipady=3)
        entries[item_id] = entry

    def save():
        received = {}
        for item_id, entry in entries.items():
            text = entry.get().strip() or "0"
            if not text.isdigit():
                error_label.config(text="⚠  Use whole numbers (0 or more) only.")
                return
            received[item_id] = int(text)

        try:
            status = receive_po_items(po_id, received, current_user["username"], update_var.get())
        except ValueError as e:
            error_label.config(text=f"⚠  {e}")
            return

        popup.destroy()
        messagebox.showinfo("Stock Received", f"Stock added.\n{order[1]} is now: {status}.")
        if on_done:
            on_done()

    tk.Button(bottom, text="📥  Add to Stock", padx=16, pady=7, command=save, **BTN_PRIMARY).pack(side="left", padx=(0, 10))
    tk.Button(bottom, text="Cancel", padx=16, pady=7, command=popup.destroy, **BTN_SECONDARY).pack(side="left")

# read-only view of one order, with receive / pay shortcuts
def open_po_details(root, current_user, po_id, on_done=None):
    order = get_purchase_order(po_id)
    if order is None:
        return

    items = get_po_items(po_id)
    payments = get_po_payments(po_id)
    received_value = sum(i[5] * i[4] for i in items)
    paid = sum(p[4] for p in payments)
    due = get_po_due(po_id)

    popup = tk.Toplevel(root)
    popup.title(f"Purchase Order — {order[1]}")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.minsize(720, 560)
    place_popup(root, popup, 860, 680)

    # buttons first so they stay visible
    bottom = tk.Frame(popup, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    header = tk.Frame(popup, bg=CARD, padx=18, pady=12, highlightthickness=1, highlightbackground=BORDER)
    header.pack(fill="x", padx=16, pady=(16, 10))

    tk.Label(header, text=f"📋  {order[1]}", font=("Segoe UI", 15, "bold"), bg=CARD, fg=TEXT).pack(side="left")
    tk.Label(header, text=order[4], font=FONT_SUB, bg=CARD, fg=STATUS_COLORS.get(order[4], TEXT)).pack(side="right")

    info = tk.Frame(popup, bg=BG)
    info.pack(fill="x", padx=18)
    for text in (
        f"Supplier: {order[3]}",
        f"Ordered: {order[5]}    Expected: {order[6] or '—'}    Received: {order[7] or '—'}",
        f"Created by: {order[10] or '—'}" + (f"    Notes: {order[8]}" if order[8] else ""),
    ):
        tk.Label(info, text=text, font=FONT_SMALL, bg=BG, fg=TEXT3, anchor="w").pack(fill="x")

    totals = tk.Frame(popup, bg=CARD, padx=16, pady=10, highlightthickness=1, highlightbackground=BORDER)
    totals.pack(side="bottom", fill="x", padx=16, pady=(0, 10))
    for label, value, color in (
        ("Order total", order[9], TEXT2), ("Goods received", received_value, TEAL),
        ("Paid", paid, GREEN), ("Due", due, YELLOW if due > 0 else GREEN),
    ):
        box = tk.Frame(totals, bg=CARD)
        box.pack(side="left", expand=True)
        tk.Label(box, text=f"₹{value:,.2f}", font=("Segoe UI", 13, "bold"), bg=CARD, fg=color).pack()
        tk.Label(box, text=label, font=FONT_SMALL, bg=CARD, fg=TEXT3).pack()

    pay_frame = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    pay_frame.pack(side="bottom", fill="x", padx=16, pady=(0, 10))
    pay_table = ttk.Treeview(pay_frame, columns=("Date", "Method", "Reference", "Amount"), show="headings", height=3)
    for col, w in zip(("Date", "Method", "Reference", "Amount"), (170, 120, 200, 100)):
        pay_table.heading(col, text=col)
        pay_table.column(col, width=w, anchor="center")
    pay_table.pack(fill="x")
    for paid_at, method, reference, note, amount in payments:
        pay_table.insert("", "end", values=(show_time(paid_at), method, reference or "", f"₹{amount:,.2f}"))
    tk.Label(popup, text="Payments made against this order", font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT3).pack(side="bottom", anchor="w", padx=18)

    items_frame = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    items_frame.pack(fill="both", expand=True, padx=16, pady=(10, 10))

    item_cols = ("Product", "Ordered", "Received", "Remaining", "Unit Cost", "Line Total")
    item_table = ttk.Treeview(items_frame, columns=item_cols, show="headings", height=6)
    for col, w in zip(item_cols, (230, 80, 80, 90, 100, 110)):
        item_table.heading(col, text=col)
        item_table.column(col, width=w, anchor="center")
    scroll = ttk.Scrollbar(items_frame, orient="vertical", command=item_table.yview)
    item_table.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    item_table.pack(fill="both", expand=True)

    for item_id, product_id, name, quantity, cost, got in items:
        item_table.insert("", "end", values=(name, quantity, got, quantity - got, f"₹{cost:.2f}", f"₹{quantity * cost:,.2f}"))

    def finish():
        popup.destroy()
        if on_done:
            on_done()

    if order[4] in ("Ordered", "Partially Received"):
        tk.Button(
            bottom, text="📥  Receive Stock", padx=14, pady=6,
            command=lambda: (popup.destroy(), open_receive_dialog(root, current_user, po_id, on_done)), **BTN_SUCCESS
        ).pack(side="left", padx=(0, 8))
    if due > 0:
        tk.Button(
            bottom, text="💵  Pay Supplier", padx=14, pady=6,
            command=lambda: (popup.destroy(), open_payment_dialog(root, current_user, order[2], po_id, on_done)), **BTN_SECONDARY
        ).pack(side="left")
    tk.Button(bottom, text="Close", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=16, pady=6, command=popup.destroy).pack(side="right")
