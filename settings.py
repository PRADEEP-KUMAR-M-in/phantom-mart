import os
import tkinter as tk
from tkinter import messagebox, filedialog
from styles import *
from security import can_manage_system
from database import (
    create_backup, list_backups, restore_backup, check_backup_file,
    BACKUP_DIR, get_setting, set_setting
)

# turns "100" into 100.0, gives back None for anything that isn't a normal number >= 0
def read_rupees(text):
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value >= 0 and value != float("inf") else None

# settings page, admin only
def show_settings(root, current_user, go_home):

    if not can_manage_system(current_user):
        messagebox.showwarning("Not Allowed", "Only Admin can open the settings page.")
        return

    for widget in root.winfo_children():
        widget.destroy()

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "settings", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "⚙️  Settings", current_user)

    content = make_scrollable(right, BG)

    def make_card(title, subtitle):
        card = tk.Frame(content, bg=CARD, padx=24, pady=20, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(card, text=title, font=FONT_HEADING, bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(card, text=subtitle, font=FONT_SMALL, bg=CARD, fg=TEXT3, justify="left").pack(anchor="w", pady=(2, 12))
        return card

    # ---- stock alerts
    stock_card = make_card("📦  Stock Alerts", "New products start with this minimum stock level. You can still change it for each product.")

    row = tk.Frame(stock_card, bg=CARD)
    row.pack(anchor="w")

    tk.Label(row, text="Default minimum stock:", font=FONT_BODY, bg=CARD, fg=TEXT2).pack(side="left")
    threshold_entry = tk.Entry(row, width=6, font=FONT_INPUT)
    style_entry(threshold_entry)
    threshold_entry.insert(0, get_setting("default_min_stock", "5"))
    threshold_entry.pack(side="left", padx=10, ipady=4)

    threshold_msg = tk.Label(stock_card, text="", font=FONT_SMALL, bg=CARD, fg=RED)
    threshold_msg.pack(anchor="w", pady=(6, 0))

    def save_threshold():
        text = threshold_entry.get().strip()
        if not text.isdigit():
            threshold_msg.config(text="⚠  Enter a whole number (0 or more).", fg=RED)
            return
        set_setting("default_min_stock", int(text))
        threshold_msg.config(text="✅  Saved.", fg=GREEN)

    tk.Button(row, text="💾  Save", padx=14, pady=5, command=save_threshold, **BTN_PRIMARY).pack(side="left")

    # ---- loyalty points
    loyalty_card = make_card(
        "⭐  Loyalty Points",
        "Registered customers earn points on every bill and can spend them as a discount.\n"
        "Put 0 in a box to switch that part off."
    )

    earn_row = tk.Frame(loyalty_card, bg=CARD)
    earn_row.pack(anchor="w", pady=3)
    tk.Label(earn_row, text="Customer earns 1 point for every  ₹", font=FONT_BODY, bg=CARD, fg=TEXT2).pack(side="left")
    earn_entry = tk.Entry(earn_row, width=8, font=FONT_INPUT)
    style_entry(earn_entry)
    earn_entry.insert(0, get_setting("loyalty_earn_per", "100"))
    earn_entry.pack(side="left", padx=8, ipady=4)
    tk.Label(earn_row, text="spent", font=FONT_BODY, bg=CARD, fg=TEXT2).pack(side="left")

    value_row = tk.Frame(loyalty_card, bg=CARD)
    value_row.pack(anchor="w", pady=3)
    tk.Label(value_row, text="1 point is worth  ₹", font=FONT_BODY, bg=CARD, fg=TEXT2).pack(side="left")
    value_entry = tk.Entry(value_row, width=8, font=FONT_INPUT)
    style_entry(value_entry)
    value_entry.insert(0, get_setting("loyalty_point_value", "1"))
    value_entry.pack(side="left", padx=8, ipady=4)
    tk.Label(value_row, text="off the bill", font=FONT_BODY, bg=CARD, fg=TEXT2).pack(side="left")

    loyalty_msg = tk.Label(loyalty_card, text="", font=FONT_SMALL, bg=CARD, fg=RED)
    loyalty_msg.pack(anchor="w", pady=(6, 0))

    def save_loyalty():
        earn = read_rupees(earn_entry.get().strip())
        value = read_rupees(value_entry.get().strip())
        if earn is None or value is None:
            loyalty_msg.config(text="⚠  Use numbers only (0 or more).", fg=RED)
            return
        set_setting("loyalty_earn_per", f"{earn:g}")
        set_setting("loyalty_point_value", f"{value:g}")
        loyalty_msg.config(text="✅  Saved. New bills use these values.", fg=GREEN)

    tk.Button(loyalty_card, text="💾  Save", padx=14, pady=5, command=save_loyalty, **BTN_PRIMARY).pack(anchor="w", pady=(8, 0))

    # ---- backup and restore
    backup_card = make_card(
        "💾  Backup & Restore",
        "A backup is a full copy of your database (products, customers, sales, users).\n"
        f"Backups are saved in:  {BACKUP_DIR}"
    )

    backup_list = tk.Label(backup_card, text="", font=FONT_SMALL, bg=CARD, fg=TEXT3, justify="left")

    def refresh_backup_list():
        files = list_backups()
        if not files:
            backup_list.config(text="No backups yet.")
        else:
            names = [os.path.basename(f) for f in files[:5]]
            more = f"\n...and {len(files) - 5} more" if len(files) > 5 else ""
            backup_list.config(text="Latest backups:\n" + "\n".join(names) + more)

    def make_backup():
        try:
            path = create_backup()
        except Exception as e:
            messagebox.showerror("Backup Error", f"Could not create the backup:\n{e}")
            return
        messagebox.showinfo("Backup Created", f"Backup saved to:\n{path}")
        refresh_backup_list()

    def do_restore():
        path = filedialog.askopenfilename(
            title="Choose a backup file",
            initialdir=BACKUP_DIR if os.path.isdir(BACKUP_DIR) else None,
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )
        if not path:
            return

        ok, message = check_backup_file(path)
        if not ok:
            messagebox.showerror("Cannot Restore", message)
            return

        confirm = messagebox.askyesno(
            "Restore Backup",
            "This replaces ALL current data with the data from:\n"
            f"{os.path.basename(path)}\n\n"
            "A safety copy of your current data is made first.\n"
            "The app will close afterwards, so just open it again.\n\nContinue?"
        )
        if not confirm:
            return

        try:
            safety = restore_backup(path)
        except Exception as e:
            messagebox.showerror("Restore Error", f"Could not restore the backup:\n{e}")
            return

        messagebox.showinfo(
            "Restore Complete",
            f"Data restored.\nYour previous data was saved as:\n{os.path.basename(safety)}\n\n"
            "The app will close now. Please open it again."
        )
        root.destroy()

    btn_row = tk.Frame(backup_card, bg=CARD)
    btn_row.pack(anchor="w", pady=(0, 10))

    tk.Button(btn_row, text="💾  Create Backup Now", padx=16, pady=7, command=make_backup, **BTN_PRIMARY).pack(side="left", padx=(0, 10))
    tk.Button(btn_row, text="♻  Restore From File...", padx=16, pady=7, command=do_restore, **BTN_DANGER).pack(side="left")

    backup_list.pack(anchor="w")
    refresh_backup_list()
