import math
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from styles import *
from database import (
    get_all_products_for_billing, get_all_customers_for_billing,
    get_product, get_product_by_barcode, save_sale, get_next_bill_number,
    get_loyalty_settings, get_customer_points, get_sale_loyalty
)
from pdf_export import generate_bill_pdf
import receipt_ui

try:
    import qrcode
    from PIL import ImageTk
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

# change this to your real UPI id
SHOP_UPI_ID = "phantommart@upi"

# turns what the cashier typed into a number, anything weird becomes 0
def to_number(text):
    try:
        value = float(text)
    except ValueError:
        return 0
    if not math.isfinite(value):
        return 0
    return value

def show_billing(root, current_user, go_home):

    cart = []

    for widget in root.winfo_children():
        widget.destroy()

    # layout
    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar
    make_sidebar(page, root, current_user, "billing", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    # topbar
    topbar = tk.Frame(right, bg=BG2, height=52)
    topbar.pack(fill="x")
    topbar.pack_propagate(False)

    tk.Label(topbar, text="🧾  Sales Billing — POS", font=("Segoe UI", 14, "bold"), bg=BG2, fg=TEXT).pack(side="left", padx=20)

    bill_number = get_next_bill_number()

    tk.Label(topbar, text=f"Bill  {bill_number}", font=FONT_SMALL, bg=GREEN_BG, fg=GREEN, padx=12, pady=4).pack(side="right", padx=10, pady=12)
    tk.Label(topbar, text=f"👤  {current_user['username']}  ({current_user['role']})", font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(side="right", padx=10)

    tk.Frame(right, bg=BORDER, height=1).pack(fill="x")

    # main split body
    body = tk.Frame(right, bg=BG)
    body.pack(fill="both", expand=True)

    # left panel
    left = tk.Frame(body, bg=BG)
    left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=14)

    # customer select
    cust_frame = tk.Frame(left, bg=CARD, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
    cust_frame.pack(fill="x", pady=(0, 10))

    tk.Label(cust_frame, text="👤  CUSTOMER", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(0, 6))

    cust_row = tk.Frame(cust_frame, bg=CARD)
    cust_row.pack(fill="x")

    customer_list = get_all_customers_for_billing()
    cust_values = [f"{c[0]}  —  {c[1]}" for c in customer_list]
    cust_values.insert(0, "🚶  Walk-in Customer")

    cust_var = tk.StringVar(value="🚶  Walk-in Customer")
    cust_combo = ttk.Combobox(cust_row, textvariable=cust_var, values=cust_values, state="readonly", width=36, font=FONT_INPUT)
    cust_combo.pack(side="left")

    def get_current_customer():
        cust_raw = cust_var.get()
        if cust_raw.startswith("🚶"):
            return "WALKIN", "Walk-in Customer"
        return cust_raw.split("  —  ")[0].strip(), cust_raw.split("  —  ")[1].strip()

    # loyalty points: shown only when a registered customer is picked
    earn_per, point_value = get_loyalty_settings()
    loyalty_state = {"points": 0}

    loyalty_frame = tk.Frame(cust_frame, bg=CARD)

    loyalty_info = tk.Label(loyalty_frame, text="", font=FONT_SMALL, bg=CARD, fg=YELLOW)
    loyalty_info.pack(anchor="w")

    redeem_row = tk.Frame(loyalty_frame, bg=CARD)
    redeem_row.pack(fill="x", pady=(4, 0))

    tk.Label(redeem_row, text="Use points:", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(side="left")
    points_entry = tk.Entry(redeem_row, width=7, font=FONT_INPUT)
    style_entry(points_entry)
    points_entry.pack(side="left", padx=6, ipady=3)
    points_entry.bind("<KeyRelease>", lambda e: recalculate())

    tk.Button(
        redeem_row, text="Max", font=("Segoe UI", 9), bg=PURPLE_BG, fg=PURPLE_PALE,
        relief="flat", cursor="hand2", bd=0, padx=8, pady=2, command=lambda: use_max_points()
    ).pack(side="left")

    loyalty_earn = tk.Label(loyalty_frame, text="", font=("Segoe UI", 9), bg=CARD, fg=GREEN)
    loyalty_earn.pack(anchor="w", pady=(4, 0))

    # points can't be spent when 1 point is worth nothing
    if point_value <= 0:
        redeem_row.pack_forget()

    cust_combo.bind("<<ComboboxSelected>>", lambda e: on_customer_change())

    # product search
    prod_frame = tk.Frame(left, bg=CARD, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
    prod_frame.pack(fill="x", pady=(0, 10))

    tk.Label(prod_frame, text="📦  PRODUCTS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w", pady=(0, 8))

    # barcode scanners type the code and press Enter, so one Enter = one item in the cart
    scan_row = tk.Frame(prod_frame, bg=CARD)
    scan_row.pack(fill="x", pady=(0, 8))

    tk.Label(scan_row, text="📷  Scan:", font=FONT_BODY, bg=CARD, fg=TEXT3).pack(side="left", padx=(0, 6))

    scan_entry = tk.Entry(scan_row, width=22, font=FONT_INPUT)
    style_entry(scan_entry)
    scan_entry.pack(side="left", ipady=5)

    scan_hint = tk.Label(scan_row, text="Scan a barcode (or type a product ID) and press Enter", font=("Segoe UI", 9), bg=CARD, fg=TEXT_DIM)
    scan_hint.pack(side="left", padx=10)

    search_row = tk.Frame(prod_frame, bg=CARD)
    search_row.pack(fill="x", pady=(0, 8))

    search_frame = tk.Frame(search_row, bg=BG, highlightthickness=1, highlightbackground=BORDER)
    search_frame.pack(side="left")

    tk.Label(search_frame, text="🔍", bg=BG, fg=TEXT3, font=("Segoe UI", 12)).pack(side="left", padx=(6, 2))

    search_entry = tk.Entry(search_frame, width=26, font=FONT_INPUT, bg=BG, fg=TEXT, insertbackground=PURPLE_LIGHT, relief="flat", bd=0)
    search_entry.pack(side="left", ipady=6, padx=(0, 6))

    tk.Label(search_row, text="Qty:", font=FONT_BODY, bg=CARD, fg=TEXT3).pack(side="left", padx=(14, 4))

    qty_entry = tk.Entry(search_row, width=6, font=FONT_INPUT)
    style_entry(qty_entry)
    qty_entry.insert(0, "1")
    qty_entry.pack(side="left", ipady=5)

    add_btn = tk.Button(search_row, text="➕  Add", font=FONT_BUTTON, bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0, padx=12, pady=5)
    add_btn.pack(side="left", padx=10)

    # product picker table
    picker_frame = tk.Frame(left, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    picker_frame.pack(fill="both", expand=True)

    pick_cols = ("ID", "Product Name", "Price", "Qty")
    picker = ttk.Treeview(picker_frame, columns=pick_cols, show="headings", height=12)

    pick_widths = {"ID": 90, "Product Name": 240, "Price": 90, "Qty": 90}
    for col in pick_cols:
        picker.heading(col, text=col)
        picker.column(col, width=pick_widths[col], anchor="center")

    pick_scroll = ttk.Scrollbar(picker_frame, orient="vertical", command=picker.yview)
    picker.configure(yscrollcommand=pick_scroll.set)
    pick_scroll.pack(side="right", fill="y")
    picker.pack(fill="both", expand=True)

    all_products = get_all_products_for_billing()

    def refresh_picker(keyword=""):
        for row in picker.get_children():
            picker.delete(row)
        for p in all_products:
            if keyword and keyword.lower() not in p[1].lower() and keyword.lower() not in p[0].lower():
                continue
            # p = id, name, price, stock, unit, min stock
            if p[3] <= 0:
                tag = "out"
            elif p[3] <= p[5]:
                tag = "low"
            else:
                tag = ""
            picker.insert("", "end", tags=(tag,), values=(p[0], p[1], f"₹{p[2]:.2f}", p[3]))
        picker.tag_configure("out", foreground=RED)
        picker.tag_configure("low", foreground=YELLOW)

    refresh_picker()
    search_entry.bind("<KeyRelease>", lambda e: refresh_picker(search_entry.get()))

    # right cart panel
    right_panel = tk.Frame(body, bg=BG2, width=360)
    right_panel.pack(side="right", fill="y", padx=(0, 0))
    right_panel.pack_propagate(False)

    cart_header = tk.Frame(right_panel, bg=BG2)
    cart_header.pack(fill="x", padx=14, pady=(14, 6))

    tk.Label(cart_header, text="🛒  Cart", font=("Segoe UI", 13, "bold"), bg=BG2, fg=TEXT2).pack(side="left")

    cart_count_label = tk.Label(cart_header, text="0 items", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE, padx=8, pady=2)
    cart_count_label.pack(side="left", padx=8)

    tk.Button(cart_header, text="🗑  Clear", font=FONT_SMALL, bg=RED_BG, fg=RED, relief="flat", cursor="hand2", bd=0, padx=8, pady=3, command=lambda: clear_cart()).pack(side="right")

    tk.Frame(right_panel, bg=BORDER, height=1).pack(fill="x")

    # the footer has to be packed before the scrollable cart so it stays at the bottom
    cart_footer = tk.Frame(right_panel, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    cart_footer.pack(fill="x", side="bottom")

    cart_inner = make_scrollable(right_panel, BG2)

    def make_summary_row(parent, label, value_text, color=TEXT2):
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill="x", padx=14, pady=3)
        tk.Label(row, text=label, font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(side="left")
        lbl = tk.Label(row, text=value_text, font=FONT_SMALL, bg=BG2, fg=color)
        lbl.pack(side="right")
        return lbl

    tk.Frame(cart_footer, bg=BORDER, height=1).pack(fill="x")

    subtotal_lbl = make_summary_row(cart_footer, "Subtotal", "₹0")

    disc_row = tk.Frame(cart_footer, bg=BG2)
    disc_row.pack(fill="x", padx=14, pady=3)
    tk.Label(disc_row, text="Discount  (₹)", font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(side="left")
    disc_entry = tk.Entry(disc_row, width=8, font=FONT_INPUT)
    style_entry(disc_entry)
    disc_entry.insert(0, "0")
    disc_entry.pack(side="right", ipady=3)
    disc_entry.bind("<KeyRelease>", lambda e: recalculate())

    disc_hint = tk.Label(cart_footer, text="", font=("Segoe UI", 9), bg=BG2, fg=YELLOW, anchor="e")
    disc_hint.pack(fill="x", padx=14)

    points_used_lbl = tk.Label(cart_footer, text="", font=("Segoe UI", 9), bg=BG2, fg=GREEN, anchor="e")
    points_used_lbl.pack(fill="x", padx=14)

    gst_lbl = make_summary_row(cart_footer, "GST", "₹0")

    tk.Frame(cart_footer, bg=BORDER, height=1).pack(fill="x", pady=4)

    grand_row = tk.Frame(cart_footer, bg=BG2)
    grand_row.pack(fill="x", padx=14, pady=4)
    tk.Label(grand_row, text="Grand Total", font=("Segoe UI", 13, "bold"), bg=BG2, fg=TEXT).pack(side="left")
    grand_lbl = tk.Label(grand_row, text="₹0", font=("Segoe UI", 16, "bold"), bg=BG2, fg=GREEN)
    grand_lbl.pack(side="right")

    tk.Frame(cart_footer, bg=BORDER, height=1).pack(fill="x", pady=4)

    tk.Label(cart_footer, text="PAYMENT METHOD", font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT3).pack(anchor="w", padx=14, pady=(4, 6))

    pay_var = tk.StringVar(value="Cash")
    pay_methods = ["Cash", "UPI", "Card", "Net Banking", "Wallet", "Split"]
    # the methods that can be used as one part of a split payment
    split_choices = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]
    pay_row = tk.Frame(cart_footer, bg=BG2)
    pay_row.pack(fill="x", padx=14, pady=(0, 8))

    pay_buttons = {}

    # total = the bill amount the UPI / card payment was started for
    payment_state = {"confirmed": True, "detail": "", "total": 0.0}
    # split payment: one entry per method, each has an amount and a "received" tick
    split_lines = []
    split_widgets = {}
    cash_received_var = tk.StringVar()
    bank_var = tk.StringVar(value="State Bank of India")
    wallet_var = tk.StringVar(value="Paytm")
    cash_widgets = {}

    # the only place where the bill amounts are worked out
    # the typed discount and the loyalty points being used
    # together they can't take the bill below 0
    def discount_parts(subtotal):
        manual = min(max(to_number(disc_entry.get()), 0), subtotal)

        points = 0
        customer_id, _ = get_current_customer()
        if customer_id != "WALKIN" and point_value > 0:
            wanted = int(max(to_number(points_entry.get()), 0))
            room = int(math.floor(round(subtotal - manual, 2) / point_value + 1e-9))
            points = max(0, min(wanted, loyalty_state["points"], room))

        return manual, points, round(points * point_value, 2)

    def compute_totals():
        subtotal = sum(item["price"] * item["qty"] for item in cart)

        manual, points, points_value = discount_parts(subtotal)
        discount = round(manual + points_value, 2)

        # gst is worked out per item, each item has its own rate
        gst = 0
        for item in cart:
            line_total = item["price"] * item["qty"]
            share = line_total / subtotal if subtotal else 0
            taxable = line_total - discount * share
            gst += taxable * item["gst_rate"] / 100

        gst = round(gst, 2)
        grand = round(subtotal - discount + gst, 2)
        return subtotal, discount, gst, grand

    payment_detail_frame = tk.Frame(cart_footer, bg=BG2)
    payment_detail_frame.pack(fill="x", padx=14, pady=(0, 8))

    def refresh_cash_change():
        if "entry" not in cash_widgets:
            return
        _, _, _, grand = compute_totals()
        text = cash_widgets["entry"].get().strip()
        if not text:
            cash_widgets["label"].config(text="Enter amount received", fg=TEXT3)
            payment_state["confirmed"] = False
            payment_state["detail"] = ""
            return
        received = to_number(text)
        change = round(received - grand, 2)
        if change < 0:
            cash_widgets["label"].config(text=f"Short by ₹{abs(change):.2f}", fg=RED)
            payment_state["confirmed"] = False
            payment_state["detail"] = ""
        else:
            cash_widgets["label"].config(text=f"Change to return: ₹{change:.2f}", fg=GREEN)
            payment_state["confirmed"] = True
            payment_state["detail"] = f"Cash Received ₹{received:.2f}, Change ₹{change:.2f}"

    def split_paid_total():
        return sum(to_number(line["amount_var"].get()) for line in split_lines)

    def refresh_split_status():
        status = split_widgets.get("status")
        if status is None or not status.winfo_exists():
            return

        _, _, _, grand = compute_totals()
        remaining = round(grand - split_paid_total(), 2)

        if not split_lines:
            status.config(text="Add the payment methods below", fg=TEXT3)
        elif abs(remaining) < 0.005:
            status.config(text="✅  Fully paid", fg=GREEN)
        elif remaining > 0:
            status.config(text=f"Remaining: ₹{remaining:.2f}", fg=YELLOW)
        else:
            status.config(text=f"Over by ₹{abs(remaining):.2f}", fg=RED)

    def add_split_line():
        method = split_widgets["choice"].get()
        if any(line["method"] == method for line in split_lines):
            messagebox.showwarning("Already Added", f"{method} is already in the list.")
            return

        # the new line starts with whatever is still unpaid
        _, _, _, grand = compute_totals()
        remaining = round(grand - split_paid_total(), 2)

        split_lines.append({
            "method": method,
            "amount_var": tk.StringVar(value=f"{remaining:.2f}" if remaining > 0 else ""),
            "received_var": tk.BooleanVar(value=(method == "Cash"))
        })
        render_split_panel()

    def remove_split_line(line):
        split_lines.remove(line)
        render_split_panel()

    # puts the unpaid amount into this line
    def fill_rest(line):
        _, _, _, grand = compute_totals()
        others = sum(to_number(l["amount_var"].get()) for l in split_lines if l is not line)
        line["amount_var"].set(f"{max(round(grand - others, 2), 0):.2f}")
        line["received_var"].set(line["method"] == "Cash")
        refresh_split_status()

    def amount_changed(line):
        # a new amount has to be confirmed again
        line["received_var"].set(line["method"] == "Cash")
        refresh_split_status()

    def render_split_panel():
        for w in payment_detail_frame.winfo_children():
            w.destroy()
        split_widgets.clear()

        tk.Label(payment_detail_frame, text="SPLIT PAYMENT", font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT3).pack(anchor="w")

        for line in split_lines:
            row = tk.Frame(payment_detail_frame, bg=BG2)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=line["method"], font=FONT_SMALL, bg=BG2, fg=TEXT2, width=11, anchor="w").pack(side="left")

            entry = tk.Entry(row, textvariable=line["amount_var"], width=8, font=FONT_INPUT)
            style_entry(entry)
            entry.pack(side="left", ipady=3)
            entry.bind("<KeyRelease>", lambda e, l=line: amount_changed(l))

            tk.Button(row, text="Rest", font=("Segoe UI", 9), bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=5, command=lambda l=line: fill_rest(l)).pack(side="left", padx=4)

            if line["method"] != "Cash":
                tk.Checkbutton(
                    row, text="Received", variable=line["received_var"], font=("Segoe UI", 9),
                    bg=BG2, fg=TEXT3, selectcolor=BG, activebackground=BG2, activeforeground=TEXT,
                    bd=0, highlightthickness=0
                ).pack(side="left")

            tk.Button(row, text="✕", font=("Segoe UI", 9), bg=RED_BG, fg=RED, relief="flat", cursor="hand2", bd=0, padx=4, command=lambda l=line: remove_split_line(l)).pack(side="right")

        # add another method (only the ones not used yet)
        unused = [m for m in split_choices if all(line["method"] != m for line in split_lines)]
        if unused:
            add_row = tk.Frame(payment_detail_frame, bg=BG2)
            add_row.pack(fill="x", pady=(4, 2))

            choice_var = tk.StringVar(value=unused[0])
            ttk.Combobox(add_row, textvariable=choice_var, values=unused, state="readonly", width=12, font=FONT_SMALL).pack(side="left")
            tk.Button(add_row, text="➕  Add", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=8, pady=2, command=add_split_line).pack(side="left", padx=6)
            split_widgets["choice"] = choice_var

        status = tk.Label(payment_detail_frame, text="", font=FONT_SMALL, bg=BG2, fg=TEXT3)
        status.pack(anchor="w", pady=(4, 0))
        split_widgets["status"] = status
        refresh_split_status()

    # works out what to save for the payment and whether the bill can be generated yet
    # gives back a dict: ready, title, message, payments, method, detail
    def payment_summary():
        _, _, _, grand = compute_totals()
        method = pay_var.get()

        result = {"ready": False, "title": "", "message": "", "payments": [], "method": method, "detail": ""}

        if method == "Split":
            payments = []
            for line in split_lines:
                amount = round(to_number(line["amount_var"].get()), 2)
                if amount > 0:
                    payments.append((line["method"], amount, ""))

            if not payments:
                result["title"] = "Payment Required"
                result["message"] = "Add the payments for this bill first."
                return result

            result["payments"] = payments
            if len(payments) == 1:
                result["method"] = payments[0][0]
            else:
                result["method"] = "Split"
                result["detail"] = " + ".join(f"{m} ₹{a:.2f}" for m, a, _ in payments)

            paid = round(sum(p[1] for p in payments), 2)
            if abs(paid - grand) > 0.005:
                result["title"] = "Amounts Don't Match"
                result["message"] = f"The payments add up to ₹{paid:.2f} but the bill is ₹{grand:.2f}."
                return result

            waiting = [
                line["method"] for line in split_lines
                if round(to_number(line["amount_var"].get()), 2) > 0
                and line["method"] != "Cash" and not line["received_var"].get()
            ]
            if waiting:
                result["title"] = "Payment Not Confirmed"
                result["message"] = "Please tick 'Received' for: " + ", ".join(waiting)
                return result

            result["ready"] = True
            return result

        # single method
        result["payments"] = [(method, grand, payment_state["detail"])]
        result["detail"] = payment_state["detail"]

        if payment_state["confirmed"]:
            result["ready"] = True
        elif method == "Cash":
            result["title"] = "Amount Required"
            result["message"] = "Please enter a cash amount that covers the grand total."
        elif method == "UPI":
            result["title"] = "Payment Not Confirmed"
            result["message"] = "Please click 'Mark as Paid' once the UPI payment is received."
        elif method == "Card":
            result["title"] = "Payment Not Confirmed"
            result["message"] = "Please click 'Approved' once the card payment goes through."
        return result

    def render_payment_detail():
        for w in payment_detail_frame.winfo_children():
            w.destroy()
        cash_widgets.clear()

        method = pay_var.get()
        _, _, _, grand = compute_totals()
        payment_state["total"] = grand

        if method == "Cash":
            payment_state["confirmed"] = False
            payment_state["detail"] = ""

            tk.Label(payment_detail_frame, text="AMOUNT RECEIVED (₹)", font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT3).pack(anchor="w")

            row = tk.Frame(payment_detail_frame, bg=BG2)
            row.pack(fill="x", pady=(3, 0))

            entry = tk.Entry(row, textvariable=cash_received_var, width=10, font=FONT_INPUT)
            style_entry(entry)
            entry.pack(side="left", ipady=4)

            change_lbl = tk.Label(row, text="Enter amount received", font=FONT_SMALL, bg=BG2, fg=TEXT3)
            change_lbl.pack(side="left", padx=10)

            cash_widgets["entry"] = entry
            cash_widgets["label"] = change_lbl

            entry.bind("<KeyRelease>", lambda e: refresh_cash_change())
            refresh_cash_change()

        elif method == "UPI":
            payment_state["confirmed"] = False
            payment_state["detail"] = ""

            row = tk.Frame(payment_detail_frame, bg=BG2)
            row.pack(fill="x")

            if QRCODE_AVAILABLE:
                upi_string = f"upi://pay?pa={SHOP_UPI_ID}&pn=PhantomMart&am={grand:.2f}&cu=INR"
                qr_img = qrcode.make(upi_string).resize((100, 100))
                qr_photo = ImageTk.PhotoImage(qr_img)
                qr_label = tk.Label(row, image=qr_photo, bg=BG2)
                qr_label.image = qr_photo
                qr_label.pack(side="left", padx=(0, 12))
            else:
                tk.Label(row, text="⚠  Install the 'qrcode' package\nto show a scannable QR code.", font=FONT_SMALL, bg=BG2, fg=YELLOW, justify="left").pack(side="left", padx=(0, 12))

            right_col = tk.Frame(row, bg=BG2)
            right_col.pack(side="left", fill="y")

            tk.Label(right_col, text=f"Scan to pay ₹{grand:.2f}", font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(anchor="w")

            status_lbl = tk.Label(right_col, text="⏳  Waiting for payment...", font=FONT_SMALL, bg=BG2, fg=YELLOW)
            status_lbl.pack(anchor="w", pady=(4, 4))

            def mark_paid():
                payment_state["confirmed"] = True
                payment_state["detail"] = "UPI payment confirmed"
                status_lbl.config(text="✅  Payment confirmed", fg=GREEN)

            tk.Button(right_col, text="✅  Mark as Paid", font=FONT_SMALL, bg=GREEN_BG, fg=GREEN, relief="flat", cursor="hand2", bd=0, padx=8, pady=4, command=mark_paid).pack(anchor="w")

        elif method == "Card":
            payment_state["confirmed"] = False
            payment_state["detail"] = ""

            tk.Label(payment_detail_frame, text=f"💳  Charge ₹{grand:.2f} on the card terminal", font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(anchor="w")

            status_lbl = tk.Label(payment_detail_frame, text="⏳  Waiting for card...", font=FONT_SMALL, bg=BG2, fg=YELLOW)
            status_lbl.pack(anchor="w", pady=(4, 4))

            btn_row2 = tk.Frame(payment_detail_frame, bg=BG2)
            btn_row2.pack(anchor="w")

            def card_approved():
                payment_state["confirmed"] = True
                payment_state["detail"] = "Card payment approved"
                status_lbl.config(text="✅  Card approved", fg=GREEN)

            def card_declined():
                payment_state["confirmed"] = False
                payment_state["detail"] = ""
                status_lbl.config(text="❌  Card declined — try again", fg=RED)

            tk.Button(btn_row2, text="✅  Approved", font=FONT_SMALL, bg=GREEN_BG, fg=GREEN, relief="flat", cursor="hand2", bd=0, padx=8, pady=4, command=card_approved).pack(side="left", padx=(0, 6))
            tk.Button(btn_row2, text="❌  Declined", font=FONT_SMALL, bg=RED_BG, fg=RED, relief="flat", cursor="hand2", bd=0, padx=8, pady=4, command=card_declined).pack(side="left")

        elif method == "Net Banking":
            payment_state["confirmed"] = True

            tk.Label(payment_detail_frame, text="SELECT BANK", font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT3).pack(anchor="w")

            banks = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank", "Punjab National Bank", "Other"]
            bank_combo = ttk.Combobox(payment_detail_frame, textvariable=bank_var, values=banks, state="readonly", width=22, font=FONT_INPUT)
            bank_combo.pack(anchor="w", pady=(3, 0), ipady=3)

            def update_bank(e=None):
                payment_state["detail"] = f"Net Banking via {bank_var.get()}"
            bank_combo.bind("<<ComboboxSelected>>", update_bank)
            update_bank()

        elif method == "Wallet":
            payment_state["confirmed"] = True

            tk.Label(payment_detail_frame, text="SELECT WALLET", font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXT3).pack(anchor="w")

            wallets = ["Paytm", "PhonePe", "Amazon Pay", "Mobikwik", "Freecharge", "Other"]
            wallet_combo = ttk.Combobox(payment_detail_frame, textvariable=wallet_var, values=wallets, state="readonly", width=22, font=FONT_INPUT)
            wallet_combo.pack(anchor="w", pady=(3, 0), ipady=3)

            def update_wallet(e=None):
                payment_state["detail"] = f"Wallet — {wallet_var.get()}"
            wallet_combo.bind("<<ComboboxSelected>>", update_wallet)
            update_wallet()

        elif method == "Split":
            payment_state["confirmed"] = False
            payment_state["detail"] = ""
            render_split_panel()

    def select_payment(method):
        pay_var.set(method)
        for m, btn in pay_buttons.items():
            if m == method:
                btn.config(bg=PURPLE_BG, fg=PURPLE_PALE, highlightbackground=PURPLE_LIGHT)
            else:
                btn.config(bg=BG, fg=TEXT3, highlightbackground=BORDER)
        render_payment_detail()

    for i, method in enumerate(pay_methods):
        btn = tk.Button(
            pay_row, text=method, font=FONT_SMALL, relief="flat", cursor="hand2", bd=0,
            padx=6, pady=4, highlightthickness=1, command=lambda m=method: select_payment(m)
        )
        btn.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
        pay_buttons[method] = btn

    select_payment("Cash")

    btn_pair = tk.Frame(cart_footer, bg=BG2)
    btn_pair.pack(fill="x", padx=14, pady=(4, 14))

    generate_btn = tk.Button(
        btn_pair, text="✅  Generate Bill", font=("Segoe UI", 13, "bold"),
        bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0, pady=12,
        command=lambda: generate_bill()
    )
    generate_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

    print_btn = tk.Button(
        btn_pair, text="🖨", font=("Segoe UI", 13, "bold"), width=3,
        bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, pady=12,
        command=lambda: export_current_cart_pdf()
    )
    print_btn.pack(side="left")

    # PDF export helpers
    def export_bill_pdf(bill_no, customer_name, payment, detail, items,
                         subtotal, discount, gst, grand, cashier,
                         sale_date=None, sale_time=None, payments=None, loyalty=None):
        default_name = f"{bill_no}.pdf"
        path = filedialog.asksaveasfilename(
            title="Save Bill as PDF",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not path:
            return None
        try:
            generate_bill_pdf(
                path, bill_no, customer_name, payment, detail, items,
                subtotal, discount, gst, grand, cashier,
                sale_date, sale_time, payments, loyalty
            )
            messagebox.showinfo("PDF Saved", f"Bill saved to:\n{path}")
            return path
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not generate PDF:\n{e}")
            return None

    def export_current_cart_pdf():
        if not cart:
            messagebox.showwarning("Empty Cart", "Add products to the cart first.")
            return
        subtotal, discount, gst, grand = compute_totals()
        customer_id, customer_name = get_current_customer()
        plan = payment_summary()
        export_bill_pdf(
            bill_number, customer_name, plan["method"], plan["detail"], cart,
            subtotal, discount, gst, grand, current_user["username"],
            payments=plan["payments"]
        )

    def on_customer_change():
        customer_id, _ = get_current_customer()
        points_entry.delete(0, tk.END)

        if customer_id == "WALKIN" or (earn_per <= 0 and point_value <= 0):
            loyalty_state["points"] = 0
            loyalty_frame.pack_forget()
        else:
            loyalty_state["points"] = get_customer_points(customer_id)
            worth = f"   (1 point = ₹{point_value:g})" if point_value > 0 else ""
            loyalty_info.config(text=f"⭐  {loyalty_state['points']} points available{worth}")
            loyalty_frame.pack(fill="x", pady=(8, 0))
        recalculate()

    # fills in as many points as the customer has / the bill can take
    def use_max_points():
        subtotal = sum(item["price"] * item["qty"] for item in cart)
        manual = min(max(to_number(disc_entry.get()), 0), subtotal)
        room = int(math.floor(round(subtotal - manual, 2) / point_value + 1e-9)) if point_value > 0 else 0

        points_entry.delete(0, tk.END)
        points_entry.insert(0, str(max(0, min(loyalty_state["points"], room))))
        recalculate()

    # cart calculation & action helpers
    def recalculate():
        subtotal, discount, gst, grand = compute_totals()

        subtotal_lbl.config(text=f"₹{subtotal:.2f}")
        gst_lbl.config(text=f"₹{gst:.2f}")
        grand_lbl.config(text=f"₹{grand:.2f}")

        # let the cashier know if we had to change the discount they typed
        manual, points, points_value = discount_parts(subtotal)
        if to_number(disc_entry.get()) != manual:
            disc_hint.config(text=f"Discount adjusted to ₹{manual:.2f}")
        else:
            disc_hint.config(text="")

        if points:
            points_used_lbl.config(text=f"⭐  {points} points used  (−₹{points_value:.2f})")
        else:
            points_used_lbl.config(text="")

        if earn_per > 0 and get_current_customer()[0] != "WALKIN":
            loyalty_earn.config(text=f"Will earn {int(math.floor(grand / earn_per + 1e-9))} points on this bill")
        else:
            loyalty_earn.config(text="")

        method = pay_var.get()
        if method == "Cash":
            refresh_cash_change()
        elif method == "Split":
            refresh_split_status()
        elif method in ("UPI", "Card") and abs(grand - payment_state["total"]) > 0.001:
            # the amount changed after the payment was started, so start the payment again
            render_payment_detail()

    def render_cart():
        for widget in cart_inner.winfo_children():
            widget.destroy()

        if not cart:
            tk.Label(cart_inner, text="Cart is empty", font=FONT_BODY, bg=BG2, fg=TEXT_DIM, pady=30).pack()
            cart_count_label.config(text="0 items")
            recalculate()
            return

        cart_count_label.config(text=f"{len(cart)} item{'s' if len(cart)>1 else ''}")

        for item in cart:
            item_frame = tk.Frame(cart_inner, bg=CARD, padx=10, pady=8, highlightthickness=1, highlightbackground=BORDER)
            item_frame.pack(fill="x", padx=10, pady=4)

            top = tk.Frame(item_frame, bg=CARD)
            top.pack(fill="x")

            tk.Label(top, text=item["name"], font=("Segoe UI", 11, "bold"), bg=CARD, fg=TEXT, wraplength=200, justify="left").pack(side="left")
            tk.Button(top, text="✕", font=FONT_SMALL, bg=RED_BG, fg=RED, relief="flat", cursor="hand2", bd=0, padx=4, command=lambda i=item: remove_from_cart(i["id"])).pack(side="right")

            bot = tk.Frame(item_frame, bg=CARD)
            bot.pack(fill="x", pady=(6, 0))

            tk.Label(bot, text=f"₹{item['price']:.2f} each", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(side="left")

            ctrl = tk.Frame(bot, bg=CARD)
            ctrl.pack(side="right")

            tk.Button(ctrl, text="−", font=("Segoe UI", 12, "bold"), bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=6, pady=1, command=lambda i=item: change_qty(i["id"], -1)).pack(side="left")
            tk.Label(ctrl, text=str(item["qty"]), font=("Segoe UI", 12, "bold"), bg=CARD, fg=TEXT, width=3, anchor="center").pack(side="left")
            tk.Button(ctrl, text="+", font=("Segoe UI", 12, "bold"), bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0, padx=6, pady=1, command=lambda i=item: change_qty(i["id"], 1)).pack(side="left")

            item_total = item["price"] * item["qty"]
            tk.Label(bot, text=f"₹{item_total:.2f}", font=("Segoe UI", 12, "bold"), bg=CARD, fg=GREEN).pack(side="right", padx=10)

        recalculate()

    # puts a product in the cart, gives back (True, name) or (False, reason)
    # the caller decides how to show the reason (popup for clicks, a small message for scanning)
    def put_in_cart(product_id, qty):
        product = get_product(product_id)
        if not product:
            return False, "Product not found."

        stock = product[6]
        if stock <= 0:
            return False, f"'{product[1]}' is out of stock."

        # is it already in the cart?
        existing = None
        for item in cart:
            if item["id"] == product_id:
                existing = item
                break

        already_in_cart = existing["qty"] if existing else 0

        if already_in_cart + qty > stock:
            message = f"Only {stock} units available for '{product[1]}'."
            if already_in_cart:
                message += f" You already have {already_in_cart} in the cart."
            return False, message

        if existing:
            existing["qty"] += qty
        else:
            cart.append({
                "id": product_id,
                "name": product[1],
                "price": product[5],
                "qty": qty,
                "gst_rate": product[12] if product[12] is not None else 18
            })

        render_cart()
        return True, product[1]

    def add_to_cart():
        selected = picker.selection()
        if not selected:
            messagebox.showwarning("No Product", "Please select a product from the list.")
            return

        product_id = picker.item(selected[0], "values")[0]

        try:
            qty = int(qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Qty", "Please enter a valid quantity (1 or more).")
            return

        ok, message = put_in_cart(product_id, qty)
        if not ok:
            messagebox.showerror("Cannot Add", message)
            return

        qty_entry.delete(0, tk.END)
        qty_entry.insert(0, "1")

    def handle_scan(event=None):
        code = scan_entry.get().strip()
        scan_entry.delete(0, tk.END)
        if not code:
            return

        product = get_product_by_barcode(code)
        if not product:
            scan_hint.config(text=f"❌  Nothing found for '{code}'", fg=RED)
            return

        ok, message = put_in_cart(product[0], 1)
        if ok:
            scan_hint.config(text=f"✅  Added: {message}", fg=GREEN)
        else:
            scan_hint.config(text=f"⚠  {message}", fg=RED)

    scan_entry.bind("<Return>", handle_scan)

    add_btn.config(command=add_to_cart)
    picker.bind("<Double-1>", lambda e: add_to_cart())

    def change_qty(product_id, delta):
        for item in cart:
            if item["id"] == product_id:
                # the + button must not go above what we have in stock
                if delta > 0:
                    product = get_product(product_id)
                    in_stock = product[6] if product else 0
                    if item["qty"] + delta > in_stock:
                        messagebox.showerror("Not Enough Stock", f"Only {in_stock} units available for '{item['name']}'.")
                        return
                item["qty"] += delta
                if item["qty"] <= 0:
                    cart.remove(item)
                break
        render_cart()

    def remove_from_cart(product_id):
        cart[:] = [i for i in cart if i["id"] != product_id]
        render_cart()

    def clear_cart():
        if not cart:
            return
        if messagebox.askyesno("Clear Cart", "Remove all items from the cart?"):
            cart.clear()
            render_cart()

    def generate_bill():
        if not cart:
            messagebox.showwarning("Empty Cart", "Add products to the cart first.")
            return

        plan = payment_summary()
        if not plan["ready"]:
            messagebox.showwarning(plan["title"], plan["message"])
            return

        customer_id, customer_name = get_current_customer()
        subtotal, discount, gst, grand = compute_totals()
        points_used = discount_parts(subtotal)[1]
        payment = plan["method"]
        detail = plan["detail"]

        try:
            sale_id = save_sale(
                bill_number, customer_id, customer_name,
                subtotal, discount, gst, grand, payment,
                current_user["username"], cart, detail, plan["payments"], points_used
            )
        except ValueError as e:
            # most likely not enough stock, nothing was saved
            messagebox.showerror("Cannot Generate Bill", str(e))
            return
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not save the bill:\n{e}")
            return

        summary = f"Bill Number  :  {bill_number}\n"
        summary += f"Customer     :  {customer_name}\n"
        summary += f"Payment      :  {payment}\n"
        if detail:
            summary += f"               {detail}\n"
        summary += "─" * 34 + "\n"
        for item in cart:
            summary += f"{item['name'][:22]:<22}  x{item['qty']}  ₹{item['price']*item['qty']:.2f}\n"
        summary += "─" * 34 + "\n"
        summary += f"Subtotal     :  ₹{subtotal:.2f}\n"
        if discount > 0:
            summary += f"Discount     : -₹{discount:.2f}\n"
        summary += f"GST          :  ₹{gst:.2f}\n"
        summary += f"Grand Total  :  ₹{grand:.2f}\n"

        # points on this bill (only for registered customers)
        loyalty = None
        if customer_id != "WALKIN":
            earned, redeemed = get_sale_loyalty(sale_id)
            loyalty = {"earned": earned, "redeemed": redeemed, "balance": get_customer_points(customer_id)}
            if earned or redeemed:
                summary += f"Points       :  {redeemed} used, {earned} earned (balance {loyalty['balance']})\n"

        messagebox.showinfo("✅  Bill Generated!", summary)

        sold_items = [dict(i) for i in cart]
        now = datetime.datetime.now()
        sale_date = now.strftime("%d %b %Y")
        sale_time = now.strftime("%I:%M %p")

        choice = receipt_ui.ask_print_choice(root)

        if choice == "pdf":
            export_bill_pdf(
                bill_number, customer_name, payment, detail, sold_items,
                subtotal, discount, gst, grand, current_user["username"],
                sale_date, sale_time, plan["payments"], loyalty
            )
        elif choice == "thermal":
            receipt_ui.open_receipt_preview(root, {
                "bill_number": bill_number,
                "customer_name": customer_name,
                "date": sale_date,
                "time": sale_time,
                "cashier": current_user["username"],
                "items": [(i["name"], i["qty"], i["price"]) for i in sold_items],
                "subtotal": subtotal,
                "discount": discount,
                "gst": gst,
                "grand_total": grand,
                "payments": plan["payments"],
                "loyalty": loyalty
            }, wait=True)

        show_billing(root, current_user, go_home)

    render_cart()
    scan_entry.focus_set()
