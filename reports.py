import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
from styles import *
from security import can_view_reports
from database import get_sales_report, get_sale_by_bill, get_sale_items, get_sale_payments
from pdf_export import generate_report_pdf, generate_bill_pdf
from export_tools import export_table
import receipt_ui

# "01 Jan 2025" -> "2025-01-01", gives back None if the text isn't a date
def date_to_iso(text):
    try:
        return datetime.datetime.strptime(text.strip(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None

# main sales reports page
def show_reports(root, current_user, go_home):

    # cashiers are not allowed to see sales totals
    if not can_view_reports(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin or Manager can open the sales report.")
        return

    for widget in root.winfo_children():
        widget.destroy()

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "reports", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "📊  Sales Report", current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=16)

    # date filters
    filter_frame = tk.Frame(content, bg=CARD, padx=16, pady=12, highlightthickness=1, highlightbackground=BORDER)
    filter_frame.pack(fill="x", pady=(0, 14))

    tk.Label(filter_frame, text="📅  Filter by Date", font=FONT_SUB, bg=CARD, fg=TEXT2).pack(side="left", padx=(0, 20))

    now = datetime.datetime.now()
    today = now.strftime("%d %b %Y")
    first_of_year = now.replace(month=1, day=1).strftime("%d %b %Y")

    filter_var = tk.StringVar(value="all")

    def set_filter(val):
        filter_var.set(val)
        refresh_report()
        for v, btn in filter_btns.items():
            if v == val:
                btn.config(bg=PURPLE_BG, fg=PURPLE_PALE, highlightbackground=PURPLE_LIGHT)
            else:
                btn.config(bg=BG, fg=TEXT3, highlightbackground=BORDER)

    filter_btns = {}

    for label, val in [("All Time", "all"), ("Today", "today"), ("This Month", "month")]:
        btn = tk.Button(
            filter_frame, text=label, font=FONT_SMALL,
            relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
            highlightthickness=1, command=lambda v=val: set_filter(v)
        )
        btn.pack(side="left", padx=4)
        filter_btns[val] = btn

    # custom date entry fields
    tk.Label(filter_frame, text="  From:", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(side="left", padx=(16, 4))
    from_entry = tk.Entry(filter_frame, width=12, font=FONT_INPUT)
    style_entry(from_entry)
    from_entry.pack(side="left", ipady=4)
    from_entry.insert(0, first_of_year)

    tk.Label(filter_frame, text="  To:", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(side="left", padx=(8, 4))
    to_entry = tk.Entry(filter_frame, width=12, font=FONT_INPUT)
    style_entry(to_entry)
    to_entry.pack(side="left", ipady=4)
    to_entry.insert(0, today)

    def apply_custom():
        start = date_to_iso(from_entry.get())
        end = date_to_iso(to_entry.get())

        if start is None or end is None:
            messagebox.showerror("Date Error", "Please enter dates in this format: 01 Jan 2025")
            return
        if start > end:
            messagebox.showerror("Date Error", "The 'From' date must come before the 'To' date.")
            return

        set_filter("custom")

    tk.Button(
        filter_frame, text="Apply", font=FONT_SMALL, bg=PURPLE, fg=TEXT,
        relief="flat", cursor="hand2", bd=0, padx=10, pady=5,
        command=apply_custom
    ).pack(side="left", padx=8)

    # summary metric cards
    stats_frame = tk.Frame(content, bg=BG)
    stats_frame.pack(fill="x", pady=(0, 14))

    def make_stat_card(parent, col, heading, color):
        card = tk.Frame(parent, bg=CARD, padx=16, pady=12, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=col, padx=(0 if col == 0 else 10, 0), sticky="ew")
        parent.columnconfigure(col, weight=1)
        tk.Frame(card, bg=color, height=2).pack(fill="x", pady=(0, 8))
        tk.Label(card, text=heading, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")
        val_lbl = tk.Label(card, text="—", font=("Segoe UI", 18, "bold"), bg=CARD, fg=TEXT)
        val_lbl.pack(anchor="w", pady=(4, 2))
        sub_lbl = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=color)
        sub_lbl.pack(anchor="w")
        return val_lbl, sub_lbl

    ts_val, ts_sub = make_stat_card(stats_frame, 0, "Total Sales", PURPLE_LIGHT)
    tb_val, tb_sub = make_stat_card(stats_frame, 1, "Total Bills", TEAL)
    td_val, td_sub = make_stat_card(stats_frame, 2, "Total Discount", YELLOW)
    av_val, av_sub = make_stat_card(stats_frame, 3, "Avg Bill Value", GREEN)

    # sales history table
    table_frame = tk.Frame(content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True)

    cols = ("Bill No", "Customer", "Date", "Time", "Subtotal", "Discount", "GST", "Grand Total", "Payment", "Cashier")
    table = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)

    widths = {
        "Bill No": 90, "Customer": 150, "Date": 100, "Time": 80,
        "Subtotal": 90, "Discount": 80, "GST": 70, "Grand Total": 100,
        "Payment": 90, "Cashier": 90,
    }

    for col in cols:
        table.heading(col, text=col)
        table.column(col, width=widths[col], anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
    table.configure(yscrollcommand=scrollbar.set, xscrollcommand=h_scroll.set)

    scrollbar.pack(side="right", fill="y")
    h_scroll.pack(side="bottom", fill="x")
    table.pack(fill="both", expand=True)

    # bill detail popup — shown on double-click, lets you reprint that bill as PDF
    def show_bill_detail(event=None):
        selected = table.selection()
        if not selected:
            return

        bill_no = table.item(selected[0], "values")[0]
        sale = get_sale_by_bill(bill_no)
        if not sale:
            messagebox.showerror("Not Found", f"Could not find bill {bill_no}.")
            return

        (sale_id, bill_number, customer_id, customer_name,
         subtotal, discount, gst, grand_total,
         payment_method, payment_detail, cashier_name,
         sale_date, sale_time) = sale

        items = get_sale_items(sale_id)
        payments = get_sale_payments(sale_id)

        popup = tk.Toplevel(root)
        popup.title(f"Bill Details — {bill_number}")
        popup.configure(bg=BG)
        popup.transient(root)
        popup.resizable(True, True)
        popup.minsize(560, 640)

        # size and center relative to the main window
        popup.update_idletasks()
        pw, ph = 600, 700
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()
        px = rx + (rw - pw) // 2
        py = ry + (rh - ph) // 2
        popup.geometry(f"{pw}x{ph}+{max(px,0)}+{max(py,0)}")

        # grab_set fails if the window isn't on screen yet, so wait for it first
        try:
            popup.wait_visibility()
            popup.grab_set()
        except tk.TclError:
            pass

        header = tk.Frame(popup, bg=CARD, padx=18, pady=14, highlightthickness=1, highlightbackground=BORDER)
        header.pack(fill="x", padx=16, pady=(16, 10))

        tk.Label(header, text=f"🧾  {bill_number}", font=("Segoe UI", 15, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(header, text=f"{sale_date}  ·  {sale_time}", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(2, 8))

        info_grid = tk.Frame(header, bg=CARD)
        info_grid.pack(fill="x")

        def info_row(label, value, row):
            tk.Label(info_grid, text=label, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).grid(row=row, column=0, sticky="w", pady=2)
            tk.Label(info_grid, text=value, font=FONT_SMALL, bg=CARD, fg=TEXT2).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)

        info_row("Customer:", customer_name, 0)
        info_row("Cashier:", cashier_name, 1)
        info_row("Payment:", f"{payment_method}" + (f"  ({payment_detail})" if payment_detail else ""), 2)

        # buttons and totals are packed to the bottom first so they never get pushed out of view
        btn_row = tk.Frame(popup, bg=BG)
        btn_row.pack(side="bottom", fill="x", padx=16, pady=(0, 16))

        totals_frame = tk.Frame(popup, bg=CARD, padx=16, pady=10, highlightthickness=1, highlightbackground=BORDER)
        totals_frame.pack(side="bottom", fill="x", padx=16, pady=(0, 10))

        def totals_row(label, value, bold=False, color=TEXT2):
            row = tk.Frame(totals_frame, bg=CARD)
            row.pack(fill="x", pady=1)
            f = ("Segoe UI", 11, "bold") if bold else FONT_SMALL
            tk.Label(row, text=label, font=f, bg=CARD, fg=TEXT3 if not bold else TEXT).pack(side="left")
            tk.Label(row, text=value, font=f, bg=CARD, fg=color).pack(side="right")

        totals_row("Subtotal", f"₹{subtotal:.2f}")
        if discount:
            totals_row("Discount", f"-₹{discount:.2f}")
        totals_row("GST", f"₹{gst:.2f}")
        totals_row("Grand Total", f"₹{grand_total:.2f}", bold=True, color=GREEN)

        # line items table fills whatever space is left
        items_frame = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        items_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        item_cols = ("Product", "Qty", "Unit Price", "Total")
        item_table = ttk.Treeview(items_frame, columns=item_cols, show="headings", height=8)
        item_widths = {"Product": 220, "Qty": 60, "Unit Price": 100, "Total": 100}
        for col in item_cols:
            item_table.heading(col, text=col)
            item_table.column(col, width=item_widths[col], anchor="center")

        item_scroll = ttk.Scrollbar(items_frame, orient="vertical", command=item_table.yview)
        item_table.configure(yscrollcommand=item_scroll.set)
        item_scroll.pack(side="right", fill="y")
        item_table.pack(fill="both", expand=True)

        cart_items = []
        for pid, name, qty, unit_price, item_total in items:
            item_table.insert("", "end", values=(name, qty, f"₹{unit_price:.2f}", f"₹{item_total:.2f}"))
            cart_items.append({"id": pid, "name": name, "price": unit_price, "qty": qty})

        def generate_pdf_for_bill():
            path = filedialog.asksaveasfilename(
                title="Save Bill as PDF",
                initialfile=f"{bill_number}.pdf",
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")]
            )
            if not path:
                return
            try:
                generate_bill_pdf(
                    path, bill_number, customer_name, payment_method,
                    payment_detail, cart_items, subtotal, discount,
                    gst, grand_total, cashier_name, sale_date, sale_time, payments
                )
                messagebox.showinfo("PDF Saved", f"Bill saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("PDF Error", f"Could not generate PDF:\n{e}")

        tk.Button(
            btn_row, text="🖨  Generate PDF", font=FONT_BUTTON, bg=PURPLE, fg=TEXT,
            relief="flat", cursor="hand2", bd=0, padx=16, pady=8,
            command=generate_pdf_for_bill
        ).pack(side="left")

        def show_thermal_receipt():
            receipt_ui.open_receipt_preview(root, {
                "bill_number": bill_number,
                "customer_name": customer_name,
                "date": sale_date,
                "time": sale_time,
                "cashier": cashier_name,
                "items": [(i["name"], i["qty"], i["price"]) for i in cart_items],
                "subtotal": subtotal,
                "discount": discount or 0,
                "gst": gst,
                "grand_total": grand_total,
                "payments": payments
            })

        tk.Button(
            btn_row, text="🧾  Thermal Receipt", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE,
            relief="flat", cursor="hand2", bd=0, padx=16, pady=8,
            command=show_thermal_receipt
        ).pack(side="left", padx=(10, 0))

        tk.Button(
            btn_row, text="Close", font=FONT_BUTTON, bg=PURPLE_BG, fg=PURPLE_PALE,
            relief="flat", cursor="hand2", bd=0, padx=16, pady=8,
            command=popup.destroy
        ).pack(side="right")

    table.bind("<Double-1>", show_bill_detail)

    bottom = tk.Frame(content, bg=BG)
    bottom.pack(fill="x", pady=8)

    count_label = tk.Label(bottom, text="", font=FONT_SMALL, bg=BG, fg=TEXT3)
    count_label.pack(side="left")

    tk.Label(bottom, text="💡  Double-click a row to view & print that bill", font=FONT_SMALL, bg=BG, fg=TEXT_DIM).pack(side="left", padx=(16, 0))

    # holds the currently filtered results so the PDF export matches the table
    report_state = {"sales": [], "label": "All Time", "total": 0, "discount": 0, "bills": 0, "avg": 0}

    def export_report_pdf():
        if not report_state["sales"]:
            messagebox.showwarning("No Data", "There are no sales in this filter to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Sales Report as PDF",
            initialfile="Sales_Report.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not path:
            return
        try:
            generate_report_pdf(
                path, report_state["label"], report_state["sales"],
                report_state["total"], report_state["discount"],
                report_state["bills"], report_state["avg"]
            )
            messagebox.showinfo("PDF Saved", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not generate PDF:\n{e}")

    tk.Button(
        bottom, text="🖨  Export PDF", font=FONT_SMALL, bg=PURPLE, fg=TEXT,
        relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
        command=export_report_pdf
    ).pack(side="right")

    tk.Button(
        bottom, text="⬇  Export CSV", font=FONT_SMALL, bg=PURPLE_BG, fg=PURPLE_PALE,
        relief="flat", cursor="hand2", bd=0, padx=12, pady=5,
        command=lambda: export_table(
            ["Bill No", "Customer", "Date", "Time", "Subtotal", "Discount", "GST",
             "Grand Total", "Payment", "Cashier"],
            report_state["sales"], "Sales_Report.csv"
        )
    ).pack(side="right", padx=(0, 10))

    # load and update table values
    def refresh_report():
        f = filter_var.get()
        today_date = datetime.datetime.now()

        if f == "today":
            day = today_date.strftime("%Y-%m-%d")
            sales = get_sales_report(day, day)
            label = "Today"

        elif f == "month":
            # ISO dates sort as text, so "-01" to "-31" covers the whole month
            month = today_date.strftime("%Y-%m")
            sales = get_sales_report(f"{month}-01", f"{month}-31")
            label = "This Month"

        elif f == "custom":
            sales = get_sales_report(date_to_iso(from_entry.get()), date_to_iso(to_entry.get()))
            label = f"{from_entry.get().strip()} to {to_entry.get().strip()}"

        else:
            sales = get_sales_report()
            label = "All Time"

        for row in table.get_children():
            table.delete(row)

        total_amount = 0
        total_discount = 0

        for s in sales:
            table.insert("", "end", values=(
                s[0], s[1], s[2], s[3],
                f"₹{s[4]:.2f}", f"₹{s[5]:.2f}", f"₹{s[6]:.2f}", f"₹{s[7]:.2f}",
                s[8], s[9]
            ))
            total_amount += s[7]
            total_discount += s[5]

        bill_count = len(sales)
        avg = total_amount / bill_count if bill_count else 0

        ts_val.config(text=f"₹{total_amount:,.2f}")
        ts_sub.config(text="total revenue")

        tb_val.config(text=str(bill_count))
        tb_sub.config(text="bills generated")

        td_val.config(text=f"₹{total_discount:,.2f}")
        td_sub.config(text="given to customers")

        av_val.config(text=f"₹{avg:,.2f}")
        av_sub.config(text="per bill")

        count_label.config(text=f"{bill_count} bill(s) found")

        report_state["sales"] = sales
        report_state["label"] = label
        report_state["total"] = total_amount
        report_state["discount"] = total_discount
        report_state["bills"] = bill_count
        report_state["avg"] = avg

    set_filter("all")
