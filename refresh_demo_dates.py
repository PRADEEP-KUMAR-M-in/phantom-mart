# Moves all the dates in the DEMO database forward so the newest day is today.
# Run it whenever the demo looks old (dashboard shows 0 sales for today, the chart ends in a drop).
#
#   python sample_data/refresh_demo_dates.py                      (uses ../phantommart.db)
#   python sample_data/refresh_demo_dates.py path/to/phantommart.db
#
# It only works on the demo database (it has a "demo_data" marker), so your real shop data is safe.

import os
import sqlite3
import sys
import datetime

# the three date styles used in the database
def shift_iso(text, shift):                    # 2026-10-08
    return (datetime.date.fromisoformat(text) + shift).isoformat() if text else text

def shift_stamp(text, shift):                  # 2026-10-08 14:30:05
    if not text:
        return text
    return (datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S") + shift).strftime("%Y-%m-%d %H:%M:%S")

def shift_text(text, shift):                   # 08 Oct 2026
    if not text:
        return text
    return (datetime.datetime.strptime(text, "%d %b %Y") + shift).strftime("%d %b %Y")

# table, key column, [(column, function), ...]
PLAN = [
    ("sales",             "sale_id",     [("sale_date", shift_text), ("sale_date_iso", shift_iso)]),
    ("products",          "product_id",  [("date_added", shift_text)]),
    ("stock_movements",   "movement_id", [("created_at", shift_stamp)]),
    ("loyalty_points",    "log_id",      [("created_at", shift_stamp)]),
    ("purchase_orders",   "po_id",       [("order_date", shift_text), ("order_date_iso", shift_iso),
                                          ("expected_date", shift_text), ("received_date", shift_text)]),
    ("po_receipts",       "receipt_id",  [("received_at", shift_stamp)]),
    ("supplier_payments", "payment_id",  [("paid_at", shift_stamp)]),
]

# gives back a message to show; raises SystemExit-style problems as ValueError
def refresh_dates(path):
    if not os.path.exists(path):
        raise ValueError(f"Database not found: {path}")

    db = sqlite3.connect(path)
    try:
        has_settings = db.execute("SELECT 1 FROM sqlite_master WHERE name = 'settings'").fetchone()
        marker = db.execute("SELECT value FROM settings WHERE key = 'demo_data'").fetchone() if has_settings else None
        if not marker:
            raise ValueError("This is not the demo database, so nothing was changed.\n"
                             "(Only phantommart_demo.db can be re-dated, your real data is never touched.)")

        newest = db.execute("SELECT MAX(sale_date_iso) FROM sales").fetchone()[0]
        if not newest:
            raise ValueError("The database has no sales to re-date.")

        today = datetime.date.today()
        days = (today - datetime.date.fromisoformat(newest)).days
        if days == 0:
            return "Dates are already up to date (newest sale is today). Nothing to do."

        shift = datetime.timedelta(days=days)
        try:
            for table, key, columns in PLAN:
                names = ", ".join(name for name, _ in columns)
                for row in db.execute(f"SELECT {key}, {names} FROM {table}").fetchall():
                    new_values = [fn(value, shift) for (name, fn), value in zip(columns, row[1:])]
                    sets = ", ".join(f"{name} = ?" for name, _ in columns)
                    db.execute(f"UPDATE {table} SET {sets} WHERE {key} = ?", new_values + [row[0]])
            db.commit()
        except Exception as error:
            db.rollback()
            raise ValueError(f"Something went wrong, nothing was changed.\n{error}")

        return f"Done. Moved every date forward by {days} day(s). The newest sales are now dated {today.strftime('%d %b %Y')}."
    finally:
        db.close()

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "phantommart.db")
    try:
        print(refresh_dates(target))
    except ValueError as problem:
        sys.exit(str(problem))
