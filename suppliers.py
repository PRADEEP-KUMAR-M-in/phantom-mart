import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from export_tools import export_table
from supplier_money import open_payment_dialog, open_ledger_window
from database import (
    load_suppliers, search_suppliers, save_supplier,
    update_supplier, delete_supplier, get_supplier,
    get_supplier_count, get_all_supplier_balances, supplier_has_history
)

SEARCH_HINT = "Search by name, phone or city..."

# main suppliers page
def show_suppliers(root, current_user, go_home):

    for widget in root.winfo_children():
        widget.destroy()

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "suppliers", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "🚚  Suppliers", current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=16)

    # supplier stat cards
    stats_row = tk.Frame(content, bg=BG)
    stats_row.pack(anchor="w", pady=(0, 14))

    total = get_supplier_count()
    stat = tk.Frame(stats_row, bg=CARD, padx=20, pady=12, highlightthickness=1, highlightbackground=BORDER)
    stat.pack(side="left")
    tk.Frame(stat, bg=TEAL, height=2).pack(fill="x", pady=(0, 8))
    tk.Label(stat, text=str(total), font=("Segoe UI", 20, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(stat, text="Total Suppliers", font=FONT_SMALL, bg=CARD, fg=TEAL).pack(anchor="w")

    # what we owe is only shown to admin / manager
    if can_edit(current_user):
        owed = sum(b for b in get_all_supplier_balances().values() if b > 0)
        owed_card = tk.Frame(stats_row, bg=CARD, padx=20, pady=12, highlightthickness=1, highlightbackground=BORDER)
        owed_card.pack(side="left", padx=(12, 0))
        tk.Frame(owed_card, bg=YELLOW, height=2).pack(fill="x", pady=(0, 8))
        tk.Label(owed_card, text=f"₹{owed:,.2f}", font=("Segoe UI", 20, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(owed_card, text="Owed to Suppliers", font=FONT_SMALL, bg=CARD, fg=YELLOW).pack(anchor="w")

    # search toolbar
    toolbar = tk.Frame(content, bg=BG)
    toolbar.pack(fill="x", pady=(0, 10))

    search_frame = tk.Frame(toolbar, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    search_frame.pack(side="left")

    tk.Label(search_frame, text="🔍", bg=CARD, fg=TEXT3, font=("Segoe UI", 12)).pack(side="left", padx=(8, 2))

    search_entry = tk.Entry(
        search_frame, width=28, font=FONT_INPUT,
        bg=CARD, fg=TEXT_DIM, insertbackground=PURPLE_LIGHT, relief="flat", bd=0
    )
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

    if can_edit(current_user):
        tk.Button(
            toolbar, text="➕  Add Supplier", font=FONT_BUTTON,
            bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0,
            padx=16, pady=6,
            command=lambda: open_supplier_form(root, current_user, go_home, None)
        ).pack(side="right")

    # suppliers treeview table
    table_frame = tk.Frame(content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True)

    cols = ["ID", "Supplier Name", "Contact Person", "Phone", "Email", "City", "State", "GST Number"]
    if can_edit(current_user):
        cols.append("Balance Owed")
    table = ttk.Treeview(table_frame, columns=cols, show="headings", height=16)

    widths = {
        "ID": 90,
        "Supplier Name": 180,
        "Contact Person": 140,
        "Phone": 120,
        "Email": 180,
        "City": 100,
        "State": 100,
        "GST Number": 140,
        "Balance Owed": 120,
    }

    for col in cols:
        table.heading(col, text=col)
        table.column(col, width=widths[col], anchor="center")

    h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
    v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    v_scroll.pack(side="right", fill="y")
    h_scroll.pack(side="bottom", fill="x")
    table.pack(fill="both", expand=True)

    # table actions row
    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(fill="x", pady=10)

    def edit_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a supplier to edit.")
            return
        sid = table.item(selected[0], "values")[0]
        open_supplier_form(root, current_user, go_home, sid)

    def delete_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a supplier to delete.")
            return
        vals = table.item(selected[0], "values")
        sid = vals[0]
        name = vals[1]
        if supplier_has_history(sid):
            messagebox.showerror(
                "Cannot Delete",
                f"'{name}' has purchase orders or payments recorded.\n"
                "Deleting it would break those records."
            )
            return
        if messagebox.askyesno("Delete Supplier", f"Delete '{name}'?\nThis cannot be undone."):
            delete_supplier(sid)
            refresh_table()
            messagebox.showinfo("Deleted", f"'{name}' deleted successfully!")

    def pay_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a supplier to pay.")
            return
        open_payment_dialog(root, current_user, table.item(selected[0], "values")[0], None,
                            lambda: show_suppliers(root, current_user, go_home))

    def ledger_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a supplier first.")
            return
        open_ledger_window(root, table.item(selected[0], "values")[0])

    if can_edit(current_user):
        tk.Button(btn_row, text="✏  Edit", command=edit_selected, padx=14, pady=6, **BTN_SECONDARY).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="🗑  Delete", command=delete_selected, padx=14, pady=6, **BTN_DANGER).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="💵  Pay Supplier", command=pay_selected, padx=14, pady=6, **BTN_SUCCESS).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="📒  Ledger", command=ledger_selected, padx=14, pady=6, **BTN_SECONDARY).pack(side="left")
        table.bind("<Double-1>", lambda e: edit_selected())

    count_label = tk.Label(btn_row, text="", font=FONT_SMALL, bg=BG, fg=TEXT3)
    count_label.pack(side="right")

    shown_suppliers = {"rows": []}

    tk.Button(
        btn_row, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE,
        relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
        command=lambda: export_table(
            ["Supplier ID", "Name", "Contact Person", "Phone", "Email", "GST Number", "Address", "City", "State", "Opening Balance"],
            shown_suppliers["rows"], "Suppliers.csv"
        )
    ).pack(side="left", padx=(10, 0))

    # refresh supplier records
    def refresh_table():
        keyword = search_entry.get()
        if keyword == SEARCH_HINT:
            keyword = ""

        suppliers = search_suppliers(keyword) if keyword else load_suppliers()
        balances = get_all_supplier_balances() if can_edit(current_user) else {}

        for row in table.get_children():
            table.delete(row)

        for s in suppliers:
            values = [s[0], s[1], s[2], s[3], s[4], s[7], s[8], s[5]]
            if can_edit(current_user):
                values.append(f"₹{balances.get(s[0], 0):,.2f}")
            table.insert("", "end", values=values)

        shown_suppliers["rows"] = suppliers
        count_label.config(text=f"{len(suppliers)} supplier(s) found")

    refresh_table()

# add or edit supplier form
def open_supplier_form(root, current_user, go_home, supplier_id=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can add or edit suppliers.")
        return

    is_edit = supplier_id is not None
    form_title = "✏  Edit Supplier" if is_edit else "➕  Add Supplier"

    for widget in root.winfo_children():
        widget.destroy()

    def go_back():
        show_suppliers(root, current_user, go_home)

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "suppliers", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, form_title, current_user)

    content = make_scrollable(right, BG)

    # supplier form container
    card = tk.Frame(content, bg=CARD, padx=30, pady=24, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="x", padx=30, pady=20)
    card.columnconfigure(0, weight=1)
    card.columnconfigure(2, weight=1)

    tk.Label(card, text=form_title, font=FONT_HEADING, bg=CARD, fg=TEXT).grid(
        row=0, column=0, columnspan=4, sticky="w", pady=(0, 20)
    )

    def make_field(label, row, col, width=26):
        tk.Label(card, text=label, font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(
            row=row, column=col, sticky="w",
            padx=(0 if col == 0 else 20, 0), pady=(10, 2)
        )
        e = tk.Entry(card, width=width, font=FONT_INPUT)
        style_entry(e)
        e.grid(row=row + 1, column=col, sticky="ew", padx=(0 if col == 0 else 20, 0), ipady=5)
        return e

    id_entry = make_field("Supplier ID *", 1, 0)
    name_entry = make_field("Supplier Name *", 1, 2)
    contact_entry = make_field("Contact Person", 3, 0)
    phone_entry = make_field("Phone Number *", 3, 2)
    email_entry = make_field("Email", 5, 0)
    gst_entry = make_field("GST Number", 5, 2)
    city_entry = make_field("City", 7, 0)
    state_entry = make_field("State", 7, 2)
    balance_entry = make_field("Opening Balance ₹ (owed before this app)", 9, 0)
    balance_entry.insert(0, "0")

    # full width address box
    tk.Label(card, text="Address", font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(
        row=11, column=0, columnspan=4, sticky="w", pady=(14, 2)
    )

    address_box = tk.Text(
        card, width=60, height=3, font=FONT_INPUT, bg=BG, fg=TEXT,
        insertbackground=PURPLE_LIGHT, relief="flat",
        highlightthickness=1, highlightbackground=BORDER
    )
    address_box.grid(row=12, column=0, columnspan=4, sticky="ew", ipady=4)

    # populate fields if editing
    if is_edit:
        s = get_supplier(supplier_id)
        if s:
            id_entry.insert(0, s[0])
            id_entry.config(state="disabled")
            name_entry.insert(0, s[1] or "")
            contact_entry.insert(0, s[2] or "")
            phone_entry.insert(0, s[3] or "")
            email_entry.insert(0, s[4] or "")
            gst_entry.insert(0, s[5] or "")
            address_box.insert("1.0", s[6] or "")
            city_entry.insert(0, s[7] or "")
            state_entry.insert(0, s[8] or "")
            balance_entry.delete(0, tk.END)
            balance_entry.insert(0, f"{(s[9] or 0):g}" if len(s) > 9 else "0")

    error_label = tk.Label(content, text="", font=FONT_SMALL, bg=BG, fg=RED)
    error_label.pack(pady=(12, 4))

    # save or update details
    def save():
        sid = supplier_id if is_edit else id_entry.get().strip()
        name = name_entry.get().strip()
        contact = contact_entry.get().strip()
        phone = phone_entry.get().strip()
        email = email_entry.get().strip()
        gst = gst_entry.get().strip()
        address = address_box.get("1.0", tk.END).strip()
        city = city_entry.get().strip()
        state = state_entry.get().strip()

        if not sid or not name or not phone:
            error_label.config(text="⚠  Supplier ID, Name and Phone are required.")
            return

        try:
            opening = float(balance_entry.get().strip() or 0)
        except ValueError:
            error_label.config(text="⚠  Opening balance must be a number.")
            return
        if not (opening >= 0) or opening == float("inf"):
            error_label.config(text="⚠  Opening balance can't be negative.")
            return

        if is_edit:
            update_supplier(sid, name, contact, phone, email, gst, address, city, state, opening)
            messagebox.showinfo("Updated", f"'{name}' updated successfully!")
        else:
            try:
                save_supplier(sid, name, contact, phone, email, gst, address, city, state, opening)
                messagebox.showinfo("Saved", f"'{name}' added successfully!")
            except Exception as e:
                if "UNIQUE" in str(e):
                    error_label.config(text="⚠  Supplier ID already exists.")
                    return
                error_label.config(text=f"⚠  Error: {e}")
                return

        go_back()

    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(pady=10)

    tk.Button(
        btn_row,
        text="💾  Save Supplier" if not is_edit else "💾  Update Supplier",
        padx=20, pady=8,
        command=save,
        **BTN_PRIMARY
    ).pack(side="left", padx=(0, 12))

    tk.Button(btn_row, text="← Back", padx=20, pady=8, command=go_back, **BTN_SECONDARY).pack(side="left")
