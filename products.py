import os
import shutil
import filecmp
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from styles import *
from security import can_edit
from database import (
    load_products, search_products, save_product,
    update_product, delete_product, get_product,
    get_category_names, get_product_count,
    get_low_stock_products, get_out_of_stock_products,
    barcode_in_use, get_setting
)
from pdf_export import generate_products_pdf
from export_tools import export_table
from stock import open_adjust_dialog, open_history_window

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

SEARCH_HINT = "Search products..."

# product pictures get copied in here so they don't break if the original file moves
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_images")

# main products page
def show_products(root, current_user, go_home):

    for widget in root.winfo_children():
        widget.destroy()

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "products", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "📦  Products", current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=16)

    # stat cards
    stats_row = tk.Frame(content, bg=BG)
    stats_row.pack(fill="x", pady=(0, 14))

    total = get_product_count()
    low = len(get_low_stock_products())
    out = len(get_out_of_stock_products())
    in_stock = total - out

    stat_cards = [
        ("Total Products", total, PURPLE_LIGHT),
        ("In Stock", in_stock, GREEN),
        ("Low Stock", low, YELLOW),
        ("Out of Stock", out, RED),
    ]

    for i, (label, val, color) in enumerate(stat_cards):
        c = tk.Frame(stats_row, bg=CARD, padx=16, pady=10, highlightthickness=1, highlightbackground=BORDER)
        c.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="ew")
        stats_row.columnconfigure(i, weight=1)
        tk.Frame(c, bg=color, height=2).pack(fill="x", pady=(0, 8))
        tk.Label(c, text=str(val), font=("Segoe UI", 18, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(c, text=label, font=FONT_SMALL, bg=CARD, fg=color).pack(anchor="w")

    # toolbar search and filters
    toolbar = tk.Frame(content, bg=BG)
    toolbar.pack(fill="x", pady=(0, 10))

    search_frame = tk.Frame(toolbar, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    search_frame.pack(side="left")

    tk.Label(search_frame, text="🔍", bg=CARD, fg=TEXT3, font=("Segoe UI", 12)).pack(side="left", padx=(8, 2))

    search_entry = tk.Entry(
        search_frame, width=24, font=FONT_INPUT,
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

    # filter options
    cat_var = tk.StringVar(value="All Categories")
    cats = ["All Categories"] + get_category_names()

    cat_combo = ttk.Combobox(toolbar, textvariable=cat_var, values=cats, state="readonly", width=16, font=FONT_INPUT)
    cat_combo.pack(side="left", padx=10, ipady=4)
    cat_combo.bind("<<ComboboxSelected>>", lambda e: refresh_table())

    stock_var = tk.StringVar(value="All Stock")
    stock_combo = ttk.Combobox(
        toolbar, textvariable=stock_var,
        values=["All Stock", "In Stock", "Low Stock", "Out of Stock"],
        state="readonly", width=14, font=FONT_INPUT
    )
    stock_combo.pack(side="left", ipady=4)
    stock_combo.bind("<<ComboboxSelected>>", lambda e: refresh_table())

    # table button actions
    def edit_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to edit.")
            return
        product_id = table.item(selected[0], "values")[0]
        open_product_form(root, current_user, go_home, product_id)

    def delete_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to delete.")
            return
        vals = table.item(selected[0], "values")
        product_id = vals[0]
        name = vals[1]
        confirm = messagebox.askyesno(
            "Delete Product",
            f"Delete '{name}' (ID: {product_id})?\n\nThis cannot be undone."
        )
        if confirm:
            delete_product(product_id)
            refresh_table()
            messagebox.showinfo("Deleted", f"'{name}' has been deleted.")

    if can_edit(current_user):
        action_group = tk.Frame(toolbar, bg=BG)
        action_group.pack(side="right")

        tk.Button(
            action_group, text="＋  Add Product", font=FONT_BUTTON,
            bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0,
            padx=16, pady=6,
            command=lambda: open_product_form(root, current_user, go_home, None)
        ).pack(side="left")

        tk.Button(action_group, text="✏  Edit Selected", command=edit_selected, padx=14, pady=6, **BTN_SECONDARY).pack(side="left", padx=(10, 0))
        tk.Button(action_group, text="🗑  Delete Selected", command=delete_selected, padx=14, pady=6, **BTN_DANGER).pack(side="left", padx=(10, 0))

    # product treeview table
    table_frame = tk.Frame(content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True)

    cols = ("ID", "Name", "Category", "Brand", "Barcode", "Buy Price", "Sell Price", "GST", "Qty", "Unit", "Status")
    table = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)

    widths = {
        "ID": 90,
        "Name": 200,
        "Category": 110,
        "Brand": 110,
        "Barcode": 120,
        "Buy Price": 90,
        "Sell Price": 90,
        "GST": 60,
        "Qty": 60,
        "Unit": 70,
        "Status": 100,
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

    # holds the currently filtered product rows for PDF export
    product_state = {"rows": [], "full": [], "label": "All Products"}

    def export_products_pdf():
        if not product_state["rows"]:
            messagebox.showwarning("No Data", "There are no products in this filter to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Product List as PDF",
            initialfile="Product_List.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not path:
            return
        try:
            generate_products_pdf(path, product_state["label"], product_state["rows"])
            messagebox.showinfo("PDF Saved", f"Product list saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not generate PDF:\n{e}")

    tk.Button(
        btn_row, text="🖨  Export PDF", font=FONT_SMALL, bg=PURPLE, fg=TEXT,
        relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
        command=export_products_pdf
    ).pack(side="right", padx=(0, 10))

    def export_products_csv():
        headers = ["Product ID", "Name", "Category", "Brand", "Barcode", "Purchase Price", "Selling Price",
                   "GST %", "Quantity", "Min Stock", "Unit", "Date Added"]
        rows = []
        for p in product_state["full"]:
            barcode = p[13] if len(p) > 13 and p[13] else ""
            gst_rate = p[12] if p[12] is not None else 18
            rows.append((p[0], p[1], p[2], p[3], barcode, p[4], p[5], gst_rate, p[6], p[7], p[8], p[11]))
        export_table(headers, rows, "Products.csv")

    # stock tools and the CSV export are for admin / manager only (the CSV has purchase prices)
    if can_edit(current_user):
        tk.Button(
            btn_row, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE,
            relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
            command=export_products_csv
        ).pack(side="right", padx=(0, 10))

        def adjust_selected():
            selected = table.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select a product first.")
                return
            product_id = table.item(selected[0], "values")[0]
            open_adjust_dialog(root, current_user, product_id, lambda: show_products(root, current_user, go_home))

        def history_selected():
            selected = table.selection()
            product_id = table.item(selected[0], "values")[0] if selected else None
            open_history_window(root, product_id)

        tk.Button(btn_row, text="±  Adjust Stock", command=adjust_selected, padx=14, pady=5, **BTN_SECONDARY).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="📋  Stock History", command=history_selected, padx=14, pady=5, **BTN_SECONDARY).pack(side="left")

    # only admin / manager can open the edit form by double click
    if can_edit(current_user):
        table.bind("<Double-1>", lambda e: edit_selected())

    # refresh table contents
    def refresh_table():
        keyword = search_entry.get()
        if keyword == SEARCH_HINT:
            keyword = ""

        if keyword:
            products = search_products(keyword)
        else:
            products = load_products()

        cat = cat_var.get()
        if cat != "All Categories":
            products = [p for p in products if p[2] == cat]

        stock = stock_var.get()
        if stock == "In Stock":
            products = [p for p in products if p[6] > 0]
        elif stock == "Low Stock":
            low_ids = {p[0] for p in get_low_stock_products()}
            products = [p for p in products if p[0] in low_ids]
        elif stock == "Out of Stock":
            products = [p for p in products if p[6] <= 0]

        for row in table.get_children():
            table.delete(row)

        for p in products:
            qty = p[6]
            min_qty = p[7]
            gst_rate = p[12] if p[12] is not None else 18

            if qty <= 0:
                status = "Out of Stock"
                tag = "out"
            elif qty <= min_qty:
                status = "Low Stock"
                tag = "low"
            else:
                status = "In Stock"
                tag = "in"

            barcode = p[13] if len(p) > 13 and p[13] else ""

            table.insert("", "end", tags=(tag,), values=(
                p[0], p[1], p[2], p[3], barcode,
                f"₹{p[4]:.2f}", f"₹{p[5]:.2f}", f"{gst_rate:g}%", qty, p[8], status
            ))

        table.tag_configure("in", foreground=GREEN)
        table.tag_configure("low", foreground=YELLOW)
        table.tag_configure("out", foreground=RED)

        count_label.config(text=f"{len(products)} product(s) found")

        # keep a simplified (name, category, price, qty) snapshot for the PDF export
        product_state["rows"] = [(p[1], p[2], p[5], p[6]) for p in products]
        product_state["full"] = products
        label_bits = []
        if cat != "All Categories":
            label_bits.append(cat)
        if stock != "All Stock":
            label_bits.append(stock)
        product_state["label"] = " · ".join(label_bits) if label_bits else "All Products"

    refresh_table()

# add/edit product form
def open_product_form(root, current_user, go_home, product_id=None):

    # cashiers must not be able to reach this form at all
    if not can_edit(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can add or edit products.")
        return

    is_edit = product_id is not None
    form_title = "✏  Edit Product" if is_edit else "➕  Add Product"

    for widget in root.winfo_children():
        widget.destroy()

    def go_back():
        show_products(root, current_user, go_home)

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "products", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, form_title, current_user)

    content = make_scrollable(right, BG)

    # form layout
    card = tk.Frame(content, bg=CARD, padx=30, pady=24, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="x", padx=30, pady=20)

    tk.Label(card, text=form_title, font=FONT_HEADING, bg=CARD, fg=TEXT).grid(
        row=0, column=0, columnspan=4, sticky="w", pady=(0, 20)
    )

    def make_field(parent, label, row, col, width=22, colspan=1):
        tk.Label(parent, text=label, font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(
            row=row, column=col, sticky="w",
            padx=(0 if col == 0 else 20, 0), pady=(10, 2)
        )
        entry = tk.Entry(parent, width=width, font=FONT_INPUT)
        style_entry(entry)
        entry.grid(row=row + 1, column=col, columnspan=colspan, sticky="ew", padx=(0 if col == 0 else 20, 0), ipady=5)
        return entry

    id_entry = make_field(card, "Product ID *", 1, 0)
    name_entry = make_field(card, "Product Name *", 1, 2)

    cat_label = tk.Label(card, text="Category *", font=FONT_SMALL, bg=CARD, fg=TEXT3)
    cat_label.grid(row=3, column=0, sticky="w", pady=(10, 2))

    cat_var = tk.StringVar()
    cat_combo = ttk.Combobox(card, textvariable=cat_var, values=get_category_names(), state="readonly", width=20, font=FONT_INPUT)
    cat_combo.grid(row=4, column=0, sticky="ew", ipady=4)

    brand_entry = make_field(card, "Brand", 3, 2)
    buy_entry = make_field(card, "Purchase Price ₹ *", 5, 0)
    sell_entry = make_field(card, "Selling Price ₹ *", 5, 2)
    qty_entry = make_field(card, "Quantity *", 7, 0)
    min_entry = make_field(card, "Min Stock Level", 7, 2)
    if not is_edit:
        min_entry.insert(0, get_setting("default_min_stock", "5"))

    tk.Label(card, text="Unit", font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(row=9, column=0, sticky="w", pady=(10, 2))

    unit_var = tk.StringVar(value="Piece")
    unit_combo = ttk.Combobox(
        card, textvariable=unit_var,
        values=["Piece", "Kg", "Gram", "Litre", "ML", "Packet", "Bottle", "Box", "Dozen"],
        state="readonly", width=20, font=FONT_INPUT
    )
    unit_combo.grid(row=10, column=0, sticky="ew", ipady=4)

    gst_entry = make_field(card, "GST %", 9, 2)
    gst_entry.insert(0, "18")

    barcode_entry = make_field(card, "Barcode (optional)", 11, 0)

    # product image
    image_path_var = tk.StringVar()

    tk.Label(card, text="Product Image", font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(
        row=13, column=0, sticky="w", pady=(10, 2)
    )

    img_frame = tk.Frame(card, bg=CARD)
    img_frame.grid(row=14, column=0, sticky="ew")

    img_entry = tk.Entry(img_frame, textvariable=image_path_var, width=16, font=FONT_INPUT, state="readonly", readonlybackground=BG)
    style_entry(img_entry)
    img_entry.pack(side="left", ipady=5)

    preview_label = tk.Label(card, text="No image", font=FONT_SMALL, bg=CARD, fg=TEXT_DIM, width=12, height=5)
    preview_label.grid(row=13, column=2, rowspan=2, sticky="w", padx=(20, 0))

    def show_preview():
        name = image_path_var.get().strip()
        full_path = os.path.join(IMAGE_DIR, name)

        if PIL_AVAILABLE and name and os.path.exists(full_path):
            try:
                picture = Image.open(full_path)
                picture.thumbnail((90, 90))
                photo = ImageTk.PhotoImage(picture)
                preview_label.config(image=photo, text="", width=90, height=90)
                preview_label.image = photo
                return
            except OSError:
                pass

        preview_label.config(image="", text="No image", width=12, height=5)
        preview_label.image = None

    def browse_image():
        path = filedialog.askopenfilename(
            title="Select Product Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif")]
        )
        if not path:
            return

        try:
            os.makedirs(IMAGE_DIR, exist_ok=True)
            name = os.path.basename(path)
            target = os.path.join(IMAGE_DIR, name)
            base, ext = os.path.splitext(name)
            count = 1

            # same name but a different picture? give it a new name instead of overwriting
            while os.path.exists(target) and not filecmp.cmp(path, target, shallow=False):
                name = f"{base}_{count}{ext}"
                target = os.path.join(IMAGE_DIR, name)
                count += 1

            if not os.path.exists(target):
                shutil.copy2(path, target)
        except OSError as e:
            messagebox.showerror("Image Error", f"Could not copy the image:\n{e}")
            return

        image_path_var.set(name)
        show_preview()

    tk.Button(
        img_frame, text="Browse", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE,
        relief="flat", cursor="hand2", bd=0, padx=8, pady=5, command=browse_image
    ).pack(side="left", padx=6)

    tk.Label(card, text="Description", font=FONT_SMALL, bg=CARD, fg=TEXT3).grid(
        row=15, column=0, columnspan=4, sticky="w", pady=(14, 2)
    )

    desc_box = tk.Text(
        card, width=60, height=3, font=FONT_INPUT, bg=BG, fg=TEXT,
        insertbackground=PURPLE_LIGHT, relief="flat", highlightthickness=1, highlightbackground=BORDER
    )
    desc_box.grid(row=16, column=0, columnspan=4, sticky="ew", ipady=4)

    card.columnconfigure(0, weight=1)
    card.columnconfigure(2, weight=1)

    # populate fields for edit
    if is_edit:
        product = get_product(product_id)
        if product:
            id_entry.insert(0, product[0])
            id_entry.config(state="disabled")
            name_entry.insert(0, product[1] or "")
            cat_var.set(product[2] or "")
            brand_entry.insert(0, product[3] or "")
            buy_entry.insert(0, product[4])
            sell_entry.insert(0, product[5])
            qty_entry.insert(0, product[6])
            min_entry.insert(0, product[7])
            unit_var.set(product[8] or "Piece")
            desc_box.insert("1.0", product[9] or "")
            image_path_var.set(product[10] or "")
            if len(product) > 13 and product[13]:
                barcode_entry.insert(0, product[13])

            gst_entry.delete(0, tk.END)
            gst_entry.insert(0, f"{product[12]:g}" if product[12] is not None else "18")

            show_preview()

    error_label = tk.Label(content, text="", font=FONT_SMALL, bg=BG, fg=RED)
    error_label.pack(pady=(0, 4))

    # save or update product data
    def save():
        pid = product_id if is_edit else id_entry.get().strip()
        name = name_entry.get().strip()
        cat = cat_var.get()
        brand = brand_entry.get().strip()
        buy = buy_entry.get().strip()
        sell = sell_entry.get().strip()
        qty = qty_entry.get().strip()
        minst = min_entry.get().strip()
        gst = gst_entry.get().strip()
        barcode = barcode_entry.get().strip()
        unit = unit_var.get()
        desc = desc_box.get("1.0", tk.END).strip()
        img = image_path_var.get().strip()

        if not pid or not name or not cat:
            error_label.config(text="⚠  Product ID, Name and Category are required.")
            return

        try:
            buy_value = float(buy)
            sell_value = float(sell)
            qty_value = int(qty)
            min_value = int(minst) if minst else 0
            gst_value = float(gst) if gst else 18
        except ValueError:
            error_label.config(text="⚠  Price, Quantity and GST must be valid numbers.")
            return

        # written like this so a nan value fails too
        if not (buy_value >= 0 and sell_value >= 0 and qty_value >= 0 and min_value >= 0):
            error_label.config(text="⚠  Prices and quantities cannot be negative.")
            return

        if not (0 <= gst_value <= 100):
            error_label.config(text="⚠  GST must be between 0 and 100.")
            return

        if barcode and barcode_in_use(barcode, pid if is_edit else None):
            error_label.config(text="⚠  This barcode already belongs to another product.")
            return

        if is_edit:
            update_product(pid, name, cat, brand, buy_value, sell_value, qty_value, min_value, unit, desc, img, gst_value, barcode, current_user["username"])
            messagebox.showinfo("Updated", f"'{name}' updated successfully!")
        else:
            try:
                save_product(pid, name, cat, brand, buy_value, sell_value, qty_value, min_value, unit, desc, img, gst_value, barcode, current_user["username"])
                messagebox.showinfo("Saved", f"'{name}' added successfully!")
            except Exception as e:
                if "UNIQUE" in str(e):
                    error_label.config(text="⚠  Product ID already exists. Use a different ID.")
                    return
                else:
                    error_label.config(text=f"⚠  Error: {e}")
                    return

        go_back()

    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(pady=10)

    tk.Button(
        btn_row,
        text="💾  Save Product" if not is_edit else "💾  Update Product",
        padx=20, pady=8,
        command=save,
        **BTN_PRIMARY
    ).pack(side="left", padx=(0, 12))

    tk.Button(
        btn_row, text="← Back", padx=20, pady=8, command=go_back, **BTN_SECONDARY
    ).pack(side="left")
