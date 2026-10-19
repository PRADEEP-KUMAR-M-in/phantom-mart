import tkinter as tk
import datetime
from styles import *
from navigation import go_to
from security import can_edit, can_view_reports, can_manage_system
from database import (
    get_today_sales, get_today_bill_count,
    get_product_count, get_customer_count,
    get_low_stock_products, get_out_of_stock_products,
    get_recent_sales
)

# make sidebar
def make_sidebar(parent, root, current_user, active_page, go_home):

    sidebar = tk.Frame(parent, bg=BG2, width=200)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # logo header
    logo_frame = tk.Frame(sidebar, bg=BG2)
    logo_frame.pack(fill="x", padx=14, pady=(14, 10))

    tk.Label(logo_frame, text="🛒", font=("Segoe UI", 22), bg=BG2, fg=TEXT).pack(anchor="w")
    tk.Label(logo_frame, text="PHANTOM·MART", font=("Segoe UI", 11, "bold"), bg=BG2, fg=PURPLE_LIGHT).pack(anchor="w")
    tk.Label(logo_frame, text="POS System", font=FONT_SMALL, bg=BG2, fg=TEXT_DIM).pack(anchor="w")

    tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", pady=8)

    def nav_section(label):
        tk.Label(sidebar, text=label, font=("Segoe UI", 9, "bold"), bg=BG2, fg=TEXT_DIM).pack(anchor="w", padx=14, pady=(10, 2))

    def nav_btn(label, emoji, page_key):
        is_active = (page_key == active_page)
        frame = tk.Frame(sidebar, bg=PURPLE_BG if is_active else BG2, cursor="hand2")
        frame.pack(fill="x")

        highlight = tk.Frame(frame, bg=PURPLE_LIGHT if is_active else BG2, width=3)
        highlight.pack(side="left", fill="y")

        lbl = tk.Label(frame, text=f"  {emoji}  {label}", font=FONT_BODY, bg=PURPLE_BG if is_active else BG2, fg=PURPLE_PALE if is_active else TEXT3, anchor="w")
        lbl.pack(side="left", fill="x", expand=True, pady=8)

        def open_page(e):
            go_to(page_key, root, current_user, go_home)

        frame.bind("<Button-1>", open_page)
        lbl.bind("<Button-1>", open_page)
        highlight.bind("<Button-1>", open_page)

        def on_enter(e):
            if not is_active:
                frame.config(bg=CARD)
                lbl.config(bg=CARD)
                highlight.config(bg=CARD)

        def on_leave(e):
            if not is_active:
                frame.config(bg=BG2)
                lbl.config(bg=BG2)
                highlight.config(bg=BG2)

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

    nav_section("MAIN")
    nav_btn("Dashboard", "🏠", "dashboard")
    nav_btn("Products", "📦", "products")
    nav_btn("Customers", "👥", "customers")
    nav_btn("Billing", "🧾", "billing")

    nav_section("MANAGE")
    nav_btn("Categories", "🏷️", "categories")
    nav_btn("Suppliers", "🚚", "suppliers")

    # purchase orders show what we pay suppliers, so cashiers don't see them
    if can_edit(current_user):
        nav_btn("Purchase Orders", "📋", "purchases")

    # cashiers don't see the sales report
    if can_view_reports(current_user):
        nav_section("REPORTS")
        nav_btn("Sales Report", "📊", "reports")

    # settings (backup / restore) is for the admin only
    if can_manage_system(current_user):
        nav_section("SYSTEM")
        nav_btn("Settings", "⚙️", "settings")

    tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", side="bottom", pady=0)

    user_frame = tk.Frame(sidebar, bg=BG2)
    user_frame.pack(side="bottom", fill="x", padx=14, pady=12)

    tk.Label(user_frame, text=current_user["username"].capitalize(), font=("Segoe UI", 11, "bold"), bg=BG2, fg=TEXT2).pack(anchor="w")
    tk.Label(user_frame, text=current_user["role"], font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(anchor="w")

    return sidebar

# make topbar
def make_topbar(parent, page_title, current_user):

    topbar = tk.Frame(parent, bg=BG2, height=52)
    topbar.pack(fill="x")
    topbar.pack_propagate(False)

    tk.Label(topbar, text=page_title, font=("Segoe UI", 14, "bold"), bg=BG2, fg=TEXT).pack(side="left", padx=20)

    clock_label = tk.Label(topbar, text="", font=FONT_SMALL, bg=CARD, fg=PURPLE_LIGHT, padx=12, pady=4)
    clock_label.pack(side="right", padx=16, pady=10)

    tk.Label(topbar, text=f"👤  {current_user['username']}  ({current_user['role']})", font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(side="right", padx=10)

    clock_job = {"id": None}

    def update_clock():
        now = datetime.datetime.now()
        clock_label.config(text=now.strftime("🕐  %I:%M:%S %p  |  %d %b %Y"))
        clock_job["id"] = clock_label.after(1000, update_clock)

    # stop the timer when the page is closed, otherwise it keeps running on a dead label
    def stop_clock(event):
        if event.widget is clock_label and clock_job["id"]:
            clock_label.after_cancel(clock_job["id"])
            clock_job["id"] = None

    clock_label.bind("<Destroy>", stop_clock)
    update_clock()

    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    return topbar

# main dashboard
def show_dashboard(root, current_user, go_to_login):

    for w in root.winfo_children():
        w.destroy()

    def go_home():
        show_dashboard(root, current_user, go_to_login)

    def open_page(page):
        go_to(page, root, current_user, go_home)

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    make_sidebar(page, root, current_user, "dashboard", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "🏠  Dashboard", current_user)

    content = make_scrollable(right, BG)

    # welcome msg
    welcome = tk.Frame(content, bg=CARD, padx=20, pady=16, highlightthickness=1, highlightbackground=BORDER)
    welcome.pack(fill="x", padx=20, pady=(18, 0))

    tk.Label(welcome, text=f"Welcome back, {current_user['username'].capitalize()} 👋", font=("Segoe UI", 14, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
    tk.Label(welcome, text="Here is what is happening in your store today.", font=FONT_BODY, bg=CARD, fg=TEXT3).pack(anchor="w", pady=(2, 0))

    if current_user.get("last_login"):
        tk.Label(welcome, text=f"Last login: {current_user['last_login']}", font=FONT_SMALL, bg=CARD, fg=TEXT_DIM).pack(anchor="w", pady=(2, 0))

    # stat boxes
    stats_frame = tk.Frame(content, bg=BG)
    stats_frame.pack(fill="x", padx=20, pady=(14, 0))

    today_sales = get_today_sales()
    today_bills = get_today_bill_count()
    total_prods = get_product_count()
    total_custs = get_customer_count()
    low_stock = len(get_low_stock_products())
    out_of_stock = len(get_out_of_stock_products())

    stat_data = [
        ("Today's Sales", f"₹{today_sales:,.0f}", f"{today_bills} bills today", PURPLE_LIGHT, PURPLE_BG),
        ("Total Products", str(total_prods), "In your inventory", TEAL, "#0d1f2d"),
        ("Total Customers", str(total_custs), "Registered customers", GREEN, GREEN_BG),
        ("Stock Alerts", str(low_stock + out_of_stock), f"{out_of_stock} out of stock", RED, RED_BG),
    ]

    for i, (label, value, sub, color, bg_color) in enumerate(stat_data):
        card = tk.Frame(stats_frame, bg=CARD, padx=18, pady=16, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="nsew")
        stats_frame.columnconfigure(i, weight=1)

        tk.Frame(card, bg=color, height=2).pack(fill="x", pady=(0, 10))
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")
        tk.Label(card, text=value, font=("Segoe UI", 22, "bold"), bg=CARD, fg=TEXT).pack(anchor="w", pady=(4, 2))
        tk.Label(card, text=sub, font=FONT_SMALL, bg=CARD, fg=color).pack(anchor="w")

    # recent sales + stock alerts
    mid = tk.Frame(content, bg=BG)
    mid.pack(fill="x", padx=20, pady=14)
    mid.columnconfigure(0, weight=1)
    mid.columnconfigure(1, weight=1)

    sales_panel = tk.Frame(mid, bg=CARD, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER)
    sales_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

    tk.Label(sales_panel, text="🕐  Recent Sales", font=FONT_SUB, bg=CARD, fg=TEXT2).pack(anchor="w", pady=(0, 10))

    recent = get_recent_sales(5)

    if not recent:
        tk.Label(sales_panel, text="No sales yet.", font=FONT_SMALL, bg=CARD, fg=TEXT_DIM).pack(anchor="w")
    else:
        for bill_no, cust_name, total, sale_time in recent:
            row = tk.Frame(sales_panel, bg=CARD)
            row.pack(fill="x", pady=4)

            tk.Label(row, text=bill_no, font=FONT_SMALL, bg=CARD, fg=PURPLE_LIGHT).pack(side="left")
            tk.Label(row, text=cust_name, font=FONT_SMALL, bg=CARD, fg=TEXT).pack(side="left", padx=10)
            tk.Label(row, text=f"₹{total:,.0f}", font=("Segoe UI", 11, "bold"), bg=CARD, fg=GREEN).pack(side="right")
            tk.Label(row, text=sale_time, font=FONT_SMALL, bg=CARD, fg=TEXT_DIM).pack(side="right", padx=10)

            tk.Frame(sales_panel, bg=BORDER, height=1).pack(fill="x", pady=2)

    stock_panel = tk.Frame(mid, bg=CARD, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER)
    stock_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    tk.Label(stock_panel, text="⚠️  Stock Alerts", font=FONT_SUB, bg=CARD, fg=TEXT2).pack(anchor="w", pady=(0, 10))

    out = get_out_of_stock_products()
    low = get_low_stock_products()
    alerts = out + low

    if not alerts:
        tk.Label(stock_panel, text="All products are well stocked! ✅", font=FONT_SMALL, bg=CARD, fg=GREEN).pack(anchor="w")
    else:
        for prod in alerts[:6]:
            row = tk.Frame(stock_panel, bg=CARD)
            row.pack(fill="x", pady=4)

            tk.Label(row, text=prod[1], font=FONT_SMALL, bg=CARD, fg=TEXT).pack(side="left")

            qty = prod[6]
            is_out = (qty <= 0)

            badge = tk.Label(
                row,
                text="Out of stock" if is_out else f"{qty} left",
                font=FONT_SMALL,
                bg=RED_BG if is_out else YELLOW_BG,
                fg=RED if is_out else YELLOW,
                padx=8,
                pady=2
            )
            badge.pack(side="right")

            tk.Frame(stock_panel, bg=BORDER, height=1).pack(fill="x", pady=2)

    # quick buttons
    tk.Label(content, text="Quick Actions", font=FONT_SUB, bg=BG, fg=TEXT2).pack(anchor="w", padx=20, pady=(0, 8))

    quick_frame = tk.Frame(content, bg=BG)
    quick_frame.pack(fill="x", padx=20, pady=(0, 20))

    quick_buttons = [
        ("🧾  New Bill", PURPLE_BG, PURPLE, "billing"),
        ("📦  Add Product", "#0d1f2d", TEAL, "products"),
        ("👥  Add Customer", GREEN_BG, GREEN, "customers"),
    ]

    # only admin and manager get the report shortcut
    if can_view_reports(current_user):
        quick_buttons.append(("📊  Sales Report", YELLOW_BG, YELLOW, "reports"))

    for i, (text, bg_color, fg_color, target) in enumerate(quick_buttons):
        tk.Button(
            quick_frame, text=text, font=FONT_BUTTON, bg=bg_color, fg=fg_color,
            relief="flat", cursor="hand2", bd=0, padx=20, pady=14, width=16,
            command=lambda p=target: open_page(p)
        ).grid(row=0, column=i, padx=(0 if i == 0 else 10, 0))

    # logout
    tk.Button(content, text="🚪  Logout", font=FONT_BUTTON, bg=RED_BG, fg=RED, relief="flat", cursor="hand2", bd=0, padx=20, pady=10, command=go_to_login).pack(anchor="e", padx=20, pady=(0, 20))
