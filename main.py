import os
import tkinter as tk

from styles import *
from database import check_login, update_last_login, get_last_login
from PIL import Image, ImageTk

# the logo sits next to this file, so it works from any folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

main = tk.Tk()
setup_theme()

try:
    icon = tk.PhotoImage(file=LOGO_PATH)
    main.iconphoto(True, icon)
except tk.TclError:
    pass  # no logo file, the app still works without the icon

main.title("Phantom·Mart — POS System")
main.config(bg=BG)
main.resizable(True, True)

try:
    main.state("zoomed")
except tk.TclError:
    main.attributes("-zoomed", True)  # linux

current_user = {
    "username": "",
    "role": "",
    "last_login": ""
}

def clear():
    for w in main.winfo_children():
        w.destroy()

def go_to_dashboard():
    from dashboard import show_dashboard
    show_dashboard(main, current_user, go_to_login)

def go_to_login():
    clear()
    show_login()

def show_login():
    clear()

    outer = tk.Frame(main, bg=BG)
    outer.place(relx=0, rely=0, relwidth=1, relheight=1)

    left = tk.Frame(outer, bg=BG2, width=600)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    left_inner = tk.Frame(left, bg=BG2)
    left_inner.place(relx=0.78, rely=0.5, anchor="center")

    try:
        logo = Image.open(LOGO_PATH)
        logo = logo.resize((140, 140))
        logo_img = ImageTk.PhotoImage(logo)

        logo_label = tk.Label(left_inner, image=logo_img, bg=BG2)
        logo_label.image = logo_img
        logo_label.pack()
    except OSError:
        tk.Label(left_inner, text="🛒", font=("Segoe UI", 60), bg=BG2, fg=TEXT).pack()

    tk.Label(left_inner, text="PHANTOM·MART", font=("Segoe UI", 22, "bold"), bg=BG2, fg=PURPLE_LIGHT).pack(pady=(10, 0))
    tk.Label(left_inner, text="POS · Management System", font=FONT_SMALL, bg=BG2, fg=TEXT3).pack(pady=(4, 0))

    tk.Frame(left_inner, bg=BORDER, height=1, width=260).pack(pady=28)

    tk.Label(left_inner, text="Manage your store smarter.", font=FONT_BODY, bg=BG2, fg=TEXT3).pack()
    tk.Label(left_inner, text="Fast · Accurate · Phantom", font=FONT_SMALL, bg=BG2, fg=TEXT_DIM).pack(pady=6)

    right = tk.Frame(outer, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    center = tk.Frame(right, bg=BG)
    center.place(relx=0.57, rely=0.5, anchor="center")

    card = tk.Frame(center, bg=CARD, padx=40, pady=40, highlightthickness=1, highlightbackground=BORDER)
    card.pack()

    tk.Label(card, text="Welcome Back", font=FONT_HEADING, bg=CARD, fg=TEXT).pack(pady=(0, 4))
    tk.Label(card, text="Sign in to your account", font=FONT_SMALL, bg=CARD, fg=TEXT3).pack(pady=(0, 20))

    tk.Label(card, text="LOGIN AS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")

    selected_role = tk.StringVar(value="Admin")
    role_frame = tk.Frame(card, bg=CARD)
    role_frame.pack(fill="x", pady=(6, 18))

    role_buttons = {}
    for i, role_name in enumerate(["Admin", "Cashier", "Manager"]):
        btn = tk.Button(role_frame, text=role_name, font=FONT_SMALL, width=10, relief="flat", cursor="hand2", bd=0, highlightthickness=1)
        btn.grid(row=0, column=i, padx=4)
        role_buttons[role_name] = btn

    def select_role(r):
        selected_role.set(r)
        for name, btn in role_buttons.items():
            if name == r:
                btn.config(bg=PURPLE_BG, fg=PURPLE_PALE, highlightbackground=PURPLE_LIGHT)
            else:
                btn.config(bg=BG, fg=TEXT3, highlightbackground=BORDER)

    for role_name, btn in role_buttons.items():
        btn.config(command=lambda r=role_name: select_role(r))

    select_role("Admin")

    tk.Label(card, text="USERNAME", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")
    username_entry = tk.Entry(card, width=32, font=FONT_INPUT)
    style_entry(username_entry)
    username_entry.pack(pady=(6, 14), ipady=6)

    tk.Label(card, text="PASSWORD", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")

    pw_frame = tk.Frame(card, bg=CARD)
    pw_frame.pack(fill="x", pady=(6, 6))

    password_entry = tk.Entry(pw_frame, font=FONT_INPUT, show="*", width=27)
    style_entry(password_entry)
    password_entry.pack(side="left", ipady=6)

    show_pw = tk.BooleanVar(value=False)

    def toggle_password():
        if show_pw.get():
            password_entry.config(show="*")
            eye_btn.config(text="👁")
        else:
            password_entry.config(show="")
            eye_btn.config(text="🙈")
        show_pw.set(not show_pw.get())

    eye_btn = tk.Button(pw_frame, text="👁", font=("Segoe UI", 12), bg=CARD, fg=TEXT3, relief="flat", cursor="hand2", bd=0, command=toggle_password)
    eye_btn.pack(side="left", padx=6)

    error_label = tk.Label(card, text="", font=FONT_SMALL, bg=CARD, fg=RED)
    error_label.pack(pady=(6, 0))

    def do_login():
        u = username_entry.get().strip()
        p = password_entry.get().strip()
        r = selected_role.get()

        if not u or not p:
            error_label.config(text="Please enter username and password.")
            return

        user = check_login(u, p)

        if user is None:
            error_label.config(text="❌  Wrong username or password.")
            password_entry.delete(0, tk.END)
            password_entry.focus()
            return

        if user[3] != r:
            error_label.config(text=f"❌  This account is not a {r}.")
            return

        # grab the previous login time before we overwrite it, the dashboard shows it
        previous_login = get_last_login(u)
        update_last_login(u)

        current_user["username"] = user[1]
        current_user["role"] = user[3]
        current_user["last_login"] = previous_login
        go_to_dashboard()

    login_btn = tk.Button(card, text="Enter Phantom Mart", width=30, pady=8, command=do_login, **BTN_PRIMARY)
    login_btn.pack(pady=(16, 10))

    username_entry.bind("<Return>", lambda e: password_entry.focus())
    password_entry.bind("<Return>", lambda e: do_login())
    username_entry.focus()

show_login()
main.mainloop()
