import tkinter as tk
from tkinter import ttk, messagebox
from styles import *
from security import can_edit
from database import (
    save_category, update_category, delete_category,
    get_categories_with_count
)

SEARCH_HINT = "Search categories..."

# main categories page
def show_categories(root, current_user, go_home):

    for widget in root.winfo_children():
        widget.destroy()

    page = tk.Frame(root, bg=BG)
    page.pack(fill="both", expand=True)

    from dashboard import make_sidebar, make_topbar
    make_sidebar(page, root, current_user, "categories", go_home)

    right = tk.Frame(page, bg=BG)
    right.pack(side="right", fill="both", expand=True)

    make_topbar(right, "🏷️  Categories", current_user)

    content = tk.Frame(right, bg=BG)
    content.pack(fill="both", expand=True, padx=20, pady=16)

    # layout columns
    left_col = tk.Frame(content, bg=BG, width=320)
    left_col.pack(side="left", fill="y", padx=(0, 16))
    left_col.pack_propagate(False)

    right_col = tk.Frame(content, bg=BG)
    right_col.pack(side="right", fill="both", expand=True)

    # left add/edit form
    form_card = tk.Frame(left_col, bg=CARD, padx=20, pady=20, highlightthickness=1, highlightbackground=BORDER)
    form_card.pack(fill="x")

    form_title = tk.Label(form_card, text="➕  Add Category", font=FONT_HEADING, bg=CARD, fg=TEXT)
    form_title.pack(anchor="w", pady=(0, 16))

    tk.Label(form_card, text="CATEGORY ID", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")

    id_entry = tk.Entry(form_card, width=28, font=FONT_INPUT)
    style_entry(id_entry)
    id_entry.pack(fill="x", ipady=6, pady=(4, 12))

    tk.Label(form_card, text="CATEGORY NAME", font=("Segoe UI", 9, "bold"), bg=CARD, fg=TEXT3).pack(anchor="w")

    name_entry = tk.Entry(form_card, width=28, font=FONT_INPUT)
    style_entry(name_entry)
    name_entry.pack(fill="x", ipady=6, pady=(4, 16))

    error_label = tk.Label(form_card, text="", font=FONT_SMALL, bg=CARD, fg=RED)
    error_label.pack(anchor="w")

    editing_id = {"value": None}

    def reset_form():
        editing_id["value"] = None
        id_entry.config(state="normal")
        id_entry.delete(0, tk.END)
        name_entry.delete(0, tk.END)
        form_title.config(text="➕  Add Category")
        save_btn.config(text="💾  Save Category")
        error_label.config(text="")

    def save_or_update():
        cid = id_entry.get().strip()
        name = name_entry.get().strip()

        if not cid or not name:
            error_label.config(text="⚠  Both fields are required.")
            return

        try:
            if editing_id["value"]:
                update_category(editing_id["value"], name)
                messagebox.showinfo("Updated", f"Category '{name}' updated!")
            else:
                save_category(cid, name)
                messagebox.showinfo("Saved", f"Category '{name}' added!")
        except Exception as e:
            if "UNIQUE" in str(e):
                error_label.config(text="⚠  ID or name already exists.")
            else:
                error_label.config(text=f"⚠  Error: {e}")
            return

        reset_form()
        refresh_table()

    save_btn = tk.Button(
        form_card, text="💾  Save Category", padx=14, pady=8,
        command=save_or_update, **BTN_PRIMARY
    )
    save_btn.pack(fill="x", pady=(8, 4))

    tk.Button(
        form_card, text="✕  Cancel / Clear", padx=14, pady=8,
        command=reset_form, **BTN_SECONDARY
    ).pack(fill="x")

    if not can_edit(current_user):
        id_entry.config(state="disabled")
        name_entry.config(state="disabled")
        save_btn.config(state="disabled")

    # total stats card
    stats_card = tk.Frame(left_col, bg=CARD, padx=20, pady=16, highlightthickness=1, highlightbackground=BORDER)
    stats_card.pack(fill="x", pady=(14, 0))

    tk.Frame(stats_card, bg=PURPLE_LIGHT, height=2).pack(fill="x", pady=(0, 10))

    total_cats_lbl = tk.Label(stats_card, text="0", font=("Segoe UI", 22, "bold"), bg=CARD, fg=TEXT)
    total_cats_lbl.pack(anchor="w")

    tk.Label(stats_card, text="Total Categories", font=FONT_SMALL, bg=CARD, fg=PURPLE_LIGHT).pack(anchor="w")

    # right table section
    search_frame = tk.Frame(right_col, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    search_frame.pack(fill="x", pady=(0, 10))

    tk.Label(search_frame, text="🔍", bg=CARD, fg=TEXT3, font=("Segoe UI", 12)).pack(side="left", padx=(8, 2))

    search_entry = tk.Entry(search_frame, width=30, font=FONT_INPUT, bg=CARD, fg=TEXT_DIM, insertbackground=PURPLE_LIGHT, relief="flat", bd=0)
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

    # categories table
    table_frame = tk.Frame(right_col, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
    table_frame.pack(fill="both", expand=True)

    cols = ("ID", "Category Name", "Products", "Action")
    table = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)

    table.heading("ID", text="Category ID")
    table.heading("Category Name", text="Category Name")
    table.heading("Products", text="No. of Products")
    table.heading("Action", text="")

    table.column("ID", width=120, anchor="center")
    table.column("Category Name", width=220, anchor="w")
    table.column("Products", width=130, anchor="center")
    table.column("Action", width=80, anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    table.pack(fill="both", expand=True)

    # bottom actions
    btn_row = tk.Frame(right_col, bg=BG)
    btn_row.pack(fill="x", pady=10)

    def edit_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a category to edit.")
            return
        vals = table.item(selected[0], "values")
        cat_id = vals[0]
        cat_name = vals[1]

        editing_id["value"] = cat_id
        id_entry.config(state="normal")
        id_entry.delete(0, tk.END)
        id_entry.insert(0, cat_id)
        id_entry.config(state="disabled")

        name_entry.delete(0, tk.END)
        name_entry.insert(0, cat_name)

        form_title.config(text="✏  Edit Category")
        save_btn.config(text="💾  Update Category")
        error_label.config(text="")

    def delete_selected():
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a category to delete.")
            return
        vals = table.item(selected[0], "values")
        cat_id = vals[0]
        cat_name = vals[1]
        count = int(vals[2])

        if count > 0:
            messagebox.showerror(
                "Cannot Delete",
                f"'{cat_name}' has {count} product(s) linked to it.\n"
                "Reassign those products first before deleting."
            )
            return

        if messagebox.askyesno("Delete Category", f"Delete '{cat_name}'?\nThis cannot be undone."):
            delete_category(cat_id)
            reset_form()
            refresh_table()
            messagebox.showinfo("Deleted", f"'{cat_name}' deleted successfully!")

    if can_edit(current_user):
        tk.Button(btn_row, text="✏  Edit", command=edit_selected, padx=14, pady=6, **BTN_SECONDARY).pack(side="left", padx=(0, 10))
        tk.Button(btn_row, text="🗑  Delete", command=delete_selected, padx=14, pady=6, **BTN_DANGER).pack(side="left")
        table.bind("<Double-1>", lambda e: edit_selected())

    count_label = tk.Label(btn_row, text="", font=FONT_SMALL, bg=BG, fg=TEXT3)
    count_label.pack(side="right")

    # refresh table data
    def refresh_table():
        keyword = search_entry.get()
        if keyword == SEARCH_HINT:
            keyword = ""

        all_cats = get_categories_with_count()
        shown = all_cats

        if keyword:
            shown = [
                c for c in all_cats
                if keyword.lower() in c[1].lower() or keyword.lower() in c[0].lower()
            ]

        for row in table.get_children():
            table.delete(row)

        for cat in shown:
            table.insert("", "end", values=(cat[0], cat[1], cat[2], "Edit →"))

        total_cats_lbl.config(text=str(len(all_cats)))
        count_label.config(text=f"{len(shown)} category(s)")

    refresh_table()
