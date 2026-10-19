import csv
from tkinter import messagebox, filedialog

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# Excel treats text that starts with = or @ as a formula, so we put a ' in front of it
def safe_cell(value):
    if isinstance(value, str) and value:
        first = value[0]
        if first in "=@" or (first in "+-" and not value[1:2].isdigit()):
            return "'" + value
    return value

# headers = list of column names, rows = list of tuples / lists
def export_table(headers, rows, default_name):
    if not rows:
        messagebox.showwarning("No Data", "There is nothing to export.")
        return

    file_types = [("CSV file", "*.csv")]
    if EXCEL_AVAILABLE:
        file_types.append(("Excel file", "*.xlsx"))

    path = filedialog.asksaveasfilename(
        title="Export Table",
        initialfile=default_name,
        defaultextension=".csv",
        filetypes=file_types
    )
    if not path:
        return

    clean_rows = [[safe_cell(cell) for cell in row] for row in rows]

    try:
        if path.lower().endswith(".xlsx"):
            if not EXCEL_AVAILABLE:
                messagebox.showerror("Export Error", "Excel export needs the 'openpyxl' package.\nInstall it, or save as CSV instead.")
                return
            book = openpyxl.Workbook()
            sheet = book.active
            sheet.append(list(headers))
            for row in clean_rows:
                sheet.append(row)
            book.save(path)
        else:
            # utf-8-sig so Excel shows the ₹ sign and other symbols correctly
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(clean_rows)
    except OSError as e:
        messagebox.showerror("Export Error", f"Could not save the file:\n{e}")
        return

    messagebox.showinfo("Exported", f"{len(rows)} row(s) saved to:\n{path}")
