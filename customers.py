import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from export_tools import export_table
from customer_history import open_customer_history, open_points_dialog
from database import (
    load_customers, search_customers, save_customer,
    update_customer, delete_customer, get_customer,
    get_customer_count
)

SEARCH_HINT = "Search by name, phone or ID..."

# main customers page
def show_customers(root, current_user, go_home):

    for widget in root.winfo_children():
        widget.destroy()

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "customers", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "👥  Customers", current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=16)

    # total customer stat card
    total = get_customer_count()
    stat_card = tk.Frame(content, bg=CARD, padx=20, pady=12, highlightthickness=1, highlightbackground=BORDER)
    stat_card.pack(anchor="w", pady=(0, 14))

    tk.Frame(stat_card, bg=PURPLE_LIGHT, height=2).pack(fill="x", pady=(0, 8))
    tk.Label(stat_card, text=str(total), font=("Segoe UI", 20, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(stat_card, text="Total Customers", font=FONT_SMALL, bg=CARD, fg=PURPLE_LIGHT).pack(anchor="w")

    # top toolbar
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

    # table actions
    def edit_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a customer to edit.")
            return
        cid = table.item(selected[0], "values")[0]
        open_customer_form(root, current_user, go_home, cid)

    def delete_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a customer to delete.")
            return
        vals = table.item(selected[0], "values")
        cid = vals[0]
        name = vals[1]
        if messagebox.askyesno("Delete Customer", f"Delete '{name}'?\nThis cannot be undone."):
            delete_customer(cid)
            refresh_table()
            messagebox.showinfo("Deleted", f"'{name}' deleted successfully!")

    if can_edit(current_user):
        action_group = tk.Frame(toolbar, bg=BG)
        action_group.pack(side="right")

        tk.Button(
            action_group, text="➕  Add Customer", font=FONT_BUTTON,
            bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0,
            padx=16, pady=6,
            command=lambda: open_customer_form(root, current_user, go_home, None)
        ).pack(side="left")

        tk.Button(action_group, text="✏  Edit Selected", command=edit_selected, padx=14, pady=6, **BTN_SECONDARY).pack(side="left", padx=(10, 0))
        tk.Button(action_group, text="🗑  Delete Selected", command=delete_selected, padx=14, pady=6, **BTN_DANGER).pack(side="left", padx=(10, 0))

    # customers table
    table_frame = tk.Frame(content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True)

    cols = ("ID", "Name", "Phone", "Email", "Address", "Points")
    table = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)

    widths = {
        "ID": 100,
        "Name": 200,
        "Phone": 130,
        "Email": 200,
        "Address": 300,
        "Points": 80,
    }

    for col in cols:
        table.heading(col, text=col)
        table.column(col, width=widths[col], anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    table.pack(fill="both", expand=True)

    # the button row is packed first, so a tall table can never squeeze it
    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(side="bottom", fill="x", pady=10, before=table_frame)

    count_label = tk.Label(btn_row, text="", font=FONT_SMALL, bg=BG, fg=TEXT3)
    count_label.pack(side="right")

    def history_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a customer first.")
            return
        open_customer_history(root, current_user, table.item(selected[0], "values")[0], refresh_table)

    def points_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a customer first.")
            return
        open_points_dialog(root, current_user, table.item(selected[0], "values")[0], refresh_table)

    # everyone can look at a customer's history, only admin / manager can change points
    tk.Button(btn_row, text="🧾  Purchase History", command=history_selected, padx=14, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 10))
    if can_edit(current_user):
        tk.Button(btn_row, text="⭐  Adjust Points", command=points_selected, padx=14, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 10))

    shown_customers = {"rows": []}

    if can_edit(current_user):
        table.bind("<Double-1>", lambda e: edit_selected())
        tk.Button(
            btn_row, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE,
            relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
            command=lambda: export_table(
                ["Customer ID", "Name", "Phone", "Email", "Address", "Points"],
                shown_customers["rows"], "Customers.csv"
            )
        ).pack(side="left")

    # refresh table data
    def refresh_table():
        keyword = search_entry.get()
        if keyword == SEARCH_HINT:
            keyword = ""

        customers = search_customers(keyword) if keyword else load_customers()

        for row in table.get_children():
            table.delete(row)

        for c in customers:
            table.insert("", "end", values=(c[0], c[1], c[2], c[3], c[4], c[5] or 0))

        shown_customers["rows"] = customers
        count_label.config(text=f"{len(customers)} customer(s) found")

    refresh_table()

# add/edit customer form
def open_customer_form(root, current_user, go_home, customer_id=None):

    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can add or edit customers.")
        return

    is_edit = customer_id is not None
    form_title = "✏  Edit Customer" if is_edit else "➕  Add Customer"

    for widget in root.winfo_children():
        widget.destroy()

    def go_back():
        show_customers(root, current_user, go_home)

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "customers", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, form_title, current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=30, pady=20)

    # form card
    card = tk.Frame(content, bg=CARD, padx=30, pady=24, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="x")
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

    id_entry = make_field("Customer ID *", 1, 0)
    name_entry = make_field("Customer Name *", 1, 2)
    phone_entry = make_field("Phone Number *", 3, 0)
    email_entry = make_field("Email", 3, 2)

    # address box
    tk.Label(card, text="Address", font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(
        row=5, column=0, columnspan=4, sticky="w", pady=(14, 2)
    )

    address_box = tk.Text(
        card, width=60, height=3, font=FONT_INPUT,
        bg=BG, fg=TEXT, insertbackground=PURPLE_LIGHT,
        relief="flat", highlightthickness=1, highlightbackground=BORDER
    )
    address_box.grid(row=6, column=0, columnspan=4, sticky="ew", ipady=4)

    # pre-fill form data if editing
    if is_edit:
        c = get_customer(customer_id)
        if c:
            id_entry.insert(0, c[0])
            id_entry.config(state="disabled")
            name_entry.insert(0, c[1] or "")
            phone_entry.insert(0, c[2] or "")
            email_entry.insert(0, c[3] or "")
            address_box.insert("1.0", c[4] or "")

    error_label = tk.Label(content, text="", font=FONT_SMALL, bg=BG, fg=RED)
    error_label.pack(pady=(12, 4))

    def save():
        cid = customer_id if is_edit else id_entry.get().strip()
        name = name_entry.get().strip()
        phone = phone_entry.get().strip()
        email = email_entry.get().strip()
        address = address_box.get("1.0", tk.END).strip()

        if not cid or not name or not phone:
            error_label.config(text="⚠  Customer ID, Name and Phone are required.")
            return

        if is_edit:
            update_customer(cid, name, phone, email, address)
            messagebox.showinfo("Updated", f"'{name}' updated successfully!")
        else:
            try:
                save_customer(cid, name, phone, email, address)
                messagebox.showinfo("Saved", f"'{name}' added successfully!")
            except Exception as e:
                if "UNIQUE" in str(e):
                    error_label.config(text="⚠  Customer ID already exists.")
                    return
                error_label.config(text=f"⚠  Error: {e}")
                return

        go_back()

    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(pady=6)

    tk.Button(
        btn_row,
        text="💾  Save Customer" if not is_edit else "💾  Update Customer",
        padx=20, pady=8,
        command=save,
        **BTN_PRIMARY
    ).pack(side="left", padx=(0, 12))

    tk.Button(
        btn_row, text="← Back", padx=20, pady=8, command=go_back, **BTN_SECONDARY
    ).pack(side="left")
