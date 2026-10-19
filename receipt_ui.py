import tkinter as tk
from tkinter import messagebox, filedialog
from styles import *
from thermal import PAPER_WIDTHS, build_receipt_lines, lines_to_text, lines_to_escpos

def center_popup(root, popup, width, height):
    popup.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - width) // 2
    y = root.winfo_rooty() + (root.winfo_height() - height) // 2
    popup.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    # grab_set fails if the window isn't on screen yet, so wait for it first
    try:
        popup.wait_visibility()
        popup.grab_set()
    except tk.TclError:
        pass

# small popup that asks how the bill should be printed
# gives back "pdf", "thermal" or None (skip)
def ask_print_choice(root):
    result = {"value": None}

    popup = tk.Toplevel(root)
    popup.title("Print Bill")
    popup.configure(bg=BG)
    popup.transient(root)
    popup.resizable(False, False)
    center_popup(root, popup, 360, 250)

    card = tk.Frame(popup, bg=CARD, padx=22, pady=20, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="both", expand=True, padx=14, pady=14)

    tk.Label(card, text="🖨  Print this bill?", font=FONT_HEADING, bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 14))

    def choose(value):
        result["value"] = value
        popup.destroy()

    tk.Button(card, text="📄  PDF Bill", padx=14, pady=8, command=lambda: choose("pdf"), **BTN_PRIMARY).pack(fill="x", pady=3)
    tk.Button(card, text="🧾  Thermal Receipt", padx=14, pady=8, command=lambda: choose("thermal"), **BTN_SECONDARY).pack(fill="x", pady=3)
    tk.Button(card, text="Skip", padx=14, pady=6, command=lambda: choose(None), **BTN_SECONDARY).pack(fill="x", pady=(3, 0))

    popup.protocol("WM_DELETE_WINDOW", lambda: choose(None))
    root.wait_window(popup)
    return result["value"]

# preview of the thermal receipt with save / copy buttons
# wait=True keeps the code stopped until the window is closed
def open_receipt_preview(root, data, wait=False):
    popup = tk.Toplevel(root)
    popup.title(f"Thermal Receipt — {data['bill_number']}")
    popup.configure(bg=BG)
    popup.transient(root)
    center_popup(root, popup, 560, 700)

    top = tk.Frame(popup, bg=BG)
    top.pack(fill="x", padx=16, pady=(14, 8))

    tk.Label(top, text="🧾  Thermal Receipt", font=FONT_HEADING, bg=BG, fg=TEXT).pack(side="left")

    paper_var = tk.StringVar(value="80mm")

    # buttons first, packed at the bottom, so they never get pushed out of view
    bottom = tk.Frame(popup, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    tip = tk.Label(
        popup,
        text="Tip: the .prn file is raw printer data. On Windows you can send it with:\n"
             "copy /b receipt.prn \\\\localhost\\YourPrinterShareName",
        font=("Segoe UI", 9), bg=BG, fg=TEXT_DIM, justify="left"
    )
    tip.pack(side="bottom", anchor="w", padx=16, pady=(0, 8))

    text_frame = tk.Frame(popup, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    text_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    receipt_box = tk.Text(
        text_frame, font=("Courier New", 10), bg="#f5f5f5", fg="#111111",
        relief="flat", wrap="none", padx=10, pady=10
    )
    receipt_box.pack(fill="both", expand=True)

    def current_lines():
        return build_receipt_lines(data, PAPER_WIDTHS[paper_var.get()])

    def show_receipt():
        receipt_box.config(state="normal", width=PAPER_WIDTHS[paper_var.get()] + 2)
        receipt_box.delete("1.0", tk.END)
        receipt_box.insert("1.0", lines_to_text(current_lines()))
        receipt_box.config(state="disabled")

    for label in PAPER_WIDTHS:
        tk.Radiobutton(
            top, text=label, variable=paper_var, value=label, command=show_receipt,
            font=FONT_BODY, bg=BG, fg=TEXT, selectcolor=BG2, activebackground=BG,
            activeforeground=TEXT, bd=0, highlightthickness=0
        ).pack(side="right", padx=(8, 0))
    tk.Label(top, text="Paper:", font=FONT_SMALL, bg=BG, fg=TEXT3).pack(side="right")

    def save_text():
        path = filedialog.asksaveasfilename(
            title="Save Receipt as Text", initialfile=f"{data['bill_number']}_receipt.txt",
            defaultextension=".txt", filetypes=[("Text files", "*.txt")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(lines_to_text(current_lines()) + "\n")
        except OSError as e:
            messagebox.showerror("Save Error", f"Could not save the file:\n{e}")
            return
        messagebox.showinfo("Saved", f"Receipt saved to:\n{path}")

    def save_escpos():
        path = filedialog.asksaveasfilename(
            title="Save ESC/POS Receipt", initialfile=f"{data['bill_number']}_receipt.prn",
            defaultextension=".prn", filetypes=[("Printer files", "*.prn")]
        )
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(lines_to_escpos(current_lines()))
        except OSError as e:
            messagebox.showerror("Save Error", f"Could not save the file:\n{e}")
            return
        messagebox.showinfo("Saved", f"ESC/POS file saved to:\n{path}")

    def copy_text():
        popup.clipboard_clear()
        popup.clipboard_append(lines_to_text(current_lines()))
        messagebox.showinfo("Copied", "Receipt text copied to the clipboard.")

    tk.Button(bottom, text="💾  Save .txt", font=FONT_SMALL, padx=10, pady=6, command=save_text, bg=PURPLE, fg=TEXT, relief="flat", cursor="hand2", bd=0).pack(side="left", padx=(0, 8))
    tk.Button(bottom, text="🖨  Save ESC/POS (.prn)", font=FONT_SMALL, padx=10, pady=6, command=save_escpos, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0).pack(side="left", padx=(0, 8))
    tk.Button(bottom, text="📋  Copy", font=FONT_SMALL, padx=10, pady=6, command=copy_text, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0).pack(side="left")
    tk.Button(bottom, text="Close", font=FONT_BUTTON, padx=14, pady=6, command=popup.destroy, bg=PURPLE_BG, fg=PURPLE_PALE, relief="flat", cursor="hand2", bd=0).pack(side="right")

    show_receipt()

    if wait:
        root.wait_window(popup)
