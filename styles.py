import tkinter as tk
from tkinter import ttk

# background colors
BG = "#0d0d14"
BG2 = "#0a0a12"
CARD = "#13131f"
CARD2 = "#16163a"
BORDER = "#1e1b4b"

# brand and accent colors
PURPLE = "#6d28d9"
PURPLE2 = "#4f46e5"
PURPLE_LIGHT = "#818cf8"
PURPLE_PALE = "#c4b5fd"
PURPLE_BG = "#1a1640"
PURPLE_DARK = "#312e60"

# status indicators
GREEN = "#34d399"
GREEN_BG = "#0d2218"
GREEN_BORDER = "#065f46"

YELLOW = "#fbbf24"
YELLOW_BG = "#2d1f00"

RED = "#f87171"
RED_BG = "#200d0d"
RED_BORDER = "#7f1d1d"

TEAL = "#38bdf8"

# text shades
TEXT = "#e2e8f0"
TEXT2 = "#a78bfa"
TEXT3 = "#6b6ba0"
TEXT_DIM = "#3f3f6e"

# font styles
FONT_TITLE = ("Segoe UI", 26, "bold")
FONT_HEADING = ("Segoe UI", 16, "bold")
FONT_SUB = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 11, "bold")
FONT_INPUT = ("Segoe UI", 11)

# button themes
BTN_PRIMARY = {
    "bg": PURPLE,
    "fg": TEXT,
    "font": FONT_BUTTON,
    "relief": "flat",
    "cursor": "hand2",
    "activebackground": PURPLE2,
    "activeforeground": TEXT,
    "bd": 0,
}

BTN_SECONDARY = {
    "bg": PURPLE_BG,
    "fg": PURPLE_PALE,
    "font": FONT_BUTTON,
    "relief": "flat",
    "cursor": "hand2",
    "activebackground": BORDER,
    "activeforeground": TEXT,
    "bd": 0,
}

BTN_DANGER = {
    "bg": RED_BG,
    "fg": RED,
    "font": FONT_BUTTON,
    "relief": "flat",
    "cursor": "hand2",
    "activebackground": "#3b1515",
    "activeforeground": RED,
    "bd": 0,
}

BTN_SUCCESS = {
    "bg": GREEN_BG,
    "fg": GREEN,
    "font": FONT_BUTTON,
    "relief": "flat",
    "cursor": "hand2",
    "activebackground": "#0d3325",
    "activeforeground": GREEN,
    "bd": 0,
}

# ttk theme - call this once when the app starts
def setup_theme():
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Treeview", background=CARD, foreground=TEXT2, rowheight=32,
        fieldbackground=CARD, bordercolor=BORDER, font=("Segoe UI", 10)
    )
    style.configure(
        "Treeview.Heading", background=BG, foreground=PURPLE_LIGHT,
        font=("Segoe UI", 10, "bold"), relief="flat"
    )
    style.map("Treeview", background=[("selected", PURPLE_BG)], foreground=[("selected", TEXT)])

    # tabs (customer history window)
    style.configure("TNotebook", background=BG, bordercolor=BORDER, borderwidth=0)
    style.configure(
        "TNotebook.Tab", background=CARD, foreground=TEXT3, padding=(14, 7),
        font=("Segoe UI", 10, "bold"), bordercolor=BORDER
    )
    style.map("TNotebook.Tab", background=[("selected", PURPLE_BG)], foreground=[("selected", PURPLE_PALE)])

    style.configure(
        "TCombobox", fieldbackground=BG, background=BG, foreground=TEXT2,
        arrowcolor=PURPLE_LIGHT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER
    )

    # a read-only dropdown ignores the colors above unless we map its state too
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG), ("disabled", CARD)],
        foreground=[("readonly", TEXT2), ("disabled", TEXT_DIM)],
        selectbackground=[("readonly", BG)],
        selectforeground=[("readonly", TEXT2)],
        background=[("readonly", BG), ("active", PURPLE_BG)],
    )

    # the list that opens under the dropdown is a plain tk Listbox
    root = style.master
    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", PURPLE_BG)
    root.option_add("*TCombobox*Listbox.selectForeground", PURPLE_PALE)

# style entry widgets
def style_entry(entry):
    entry.config(
        bg=BG,
        fg=TEXT,
        insertbackground=PURPLE_LIGHT,
        relief="flat",
        font=FONT_INPUT,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=PURPLE_LIGHT,
    )

# create scrollable panel container, returns the inner frame
def make_scrollable(parent, bg=None):
    bg = bg or BG

    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)

    inner = tk.Frame(canvas, bg=bg)
    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_inner_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(inner_id, width=event.width)

    inner.bind("<Configure>", on_inner_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    canvas.configure(yscrollcommand=vscroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    vscroll.pack(side="right", fill="y")

    # mouse wheel handling
    def _on_mousewheel(event):
        try:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            # canvas was destroyed while the wheel binding was still active
            pass

    def _bind_wheel(_):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

    def _unbind_wheel(_):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    canvas.bind("<Enter>", _bind_wheel)
    canvas.bind("<Leave>", _unbind_wheel)

    return inner

# style frame as card
def style_card(frame):
    frame.config(
        bg=CARD,
        highlightthickness=1,
        highlightbackground=BORDER,
    )
