import sqlite3
import datetime
import os
from security import hash_password, verify_password, is_hashed

# keep the database next to the code so it doesn't matter where the app is started from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "phantommart.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# connect to database
connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# adds a column to an old database if it isn't there yet
def add_column_if_missing(table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        connection.commit()

# users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id   TEXT PRIMARY KEY,
    username  TEXT UNIQUE,
    password  TEXT,
    role      TEXT,
    last_login TEXT)""")
connection.commit()

# insert default users (passwords are stored hashed)
cursor.execute("SELECT COUNT(*) FROM users")
if cursor.fetchone()[0] == 0:
    default_users = [
        ("U001", "admin", hash_password("admin123"), "Admin", ""),
        ("U002", "cashier", hash_password("cash123"), "Cashier", ""),
        ("U003", "manager", hash_password("mgr123"), "Manager", ""),
    ]
    cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", default_users)
    connection.commit()

# older databases have plain text passwords, hash them once
cursor.execute("SELECT user_id, password FROM users")
for user_id, old_password in cursor.fetchall():
    if not is_hashed(old_password):
        cursor.execute("UPDATE users SET password = ? WHERE user_id = ?", (hash_password(old_password or ""), user_id))
connection.commit()

# login functions
def check_login(username, password):
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and verify_password(password, user[2]):
        return user
    return None

def update_last_login(username):
    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    cursor.execute("UPDATE users SET last_login = ? WHERE username = ?", (now, username))
    connection.commit()

def get_last_login(username):
    cursor.execute("SELECT last_login FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    if result:
        return result[0] or ""
    return ""

# settings table, a tiny key / value store
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
)""")
connection.commit()

def get_setting(key, default=""):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else default

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    connection.commit()

# categories table
cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    category_id   TEXT PRIMARY KEY,
    category_name TEXT UNIQUE
)""")
connection.commit()

# insert default categories
cursor.execute("SELECT COUNT(*) FROM categories")
if cursor.fetchone()[0] == 0:
    defaults = [
        ("CAT001", "Dairy"),
        ("CAT002", "Beverages"),
        ("CAT003", "Snacks"),
        ("CAT004", "Grocery"),
        ("CAT005", "Personal Care"),
        ("CAT006", "Household"),
    ]
    cursor.executemany("INSERT INTO categories VALUES (?, ?)", defaults)
    connection.commit()

def load_categories():
    cursor.execute("SELECT * FROM categories ORDER BY rowid")
    return cursor.fetchall()

def get_category_names():
    cursor.execute("SELECT category_name FROM categories ORDER BY category_name")
    rows = cursor.fetchall()
    names = []
    for r in rows:
        names.append(r[0])
    return names

# every category together with how many products use it
def get_categories_with_count():
    cursor.execute("""
        SELECT c.category_id, c.category_name, COUNT(p.product_id)
        FROM categories c
        LEFT JOIN products p ON p.category = c.category_name
        GROUP BY c.category_id, c.category_name
        ORDER BY c.rowid
    """)
    return cursor.fetchall()

def save_category(category_id, category_name):
    cursor.execute("INSERT INTO categories VALUES (?, ?)", (category_id, category_name))
    connection.commit()

# products store the category name, so the products have to be renamed too
def update_category(category_id, new_name):
    cursor.execute("SELECT category_name FROM categories WHERE category_id = ?", (category_id,))
    row = cursor.fetchone()
    if row is None:
        return
    old_name = row[0]

    try:
        cursor.execute("UPDATE categories SET category_name = ? WHERE category_id = ?", (new_name, category_id))
        cursor.execute("UPDATE products SET category = ? WHERE category = ?", (new_name, old_name))
        connection.commit()
    except Exception:
        connection.rollback()
        raise

def delete_category(category_id):
    cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
    connection.commit()

# products table
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT,
    category        TEXT,
    brand           TEXT,
    purchase_price  REAL,
    selling_price   REAL,
    quantity        INTEGER,
    min_stock       INTEGER,
    unit            TEXT,
    description     TEXT,
    image_path      TEXT,
    date_added      TEXT
)""")
connection.commit()

# gst percentage for each product (old products get 18)
add_column_if_missing("products", "gst_rate", "REAL DEFAULT 18")

# barcode printed on the pack, scanners type this number
add_column_if_missing("products", "barcode", "TEXT")

# every change to a product's stock is written here
cursor.execute("""
CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   TEXT,
    product_name TEXT,
    change_qty   INTEGER,
    qty_after    INTEGER,
    reason       TEXT,
    reference    TEXT,
    user_name    TEXT,
    created_at   TEXT
)""")
connection.commit()

# adds one row to the log, the caller commits (so it is saved together with the stock change)
def log_stock_movement(product_id, product_name, change_qty, qty_after, reason, reference="", user_name=""):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT INTO stock_movements
           (product_id, product_name, change_qty, qty_after, reason, reference, user_name, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_id, product_name, change_qty, qty_after, reason, reference, user_name, now)
    )

# newest first, leave product_id empty to get every product
def get_stock_movements(product_id=None, limit=1000):
    sql = """SELECT created_at, product_id, product_name, change_qty, qty_after,
                    reason, reference, user_name FROM stock_movements"""
    params = []
    if product_id:
        sql += " WHERE product_id = ?"
        params.append(product_id)
    sql += " ORDER BY movement_id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(sql, params)
    return cursor.fetchall()

# add or remove stock by hand (received from supplier, damaged, stock count...)
def adjust_stock(product_id, change, reason, user_name="", note=""):
    cursor.execute("SELECT product_name, quantity FROM products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError("This product no longer exists.")

    new_qty = row[1] + change
    if new_qty < 0:
        raise ValueError(f"Stock can't go below zero (current stock is {row[1]}).")

    try:
        cursor.execute("UPDATE products SET quantity = ? WHERE product_id = ?", (new_qty, product_id))
        log_stock_movement(product_id, row[0], change, new_qty, reason, note, user_name)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return new_qty

def save_product(product_id, product_name, category, brand,
                 purchase_price, selling_price, quantity,
                 min_stock, unit, description, image_path, gst_rate=18,
                 barcode="", user_name=""):

    date_added = datetime.datetime.now().strftime("%d %b %Y")
    try:
        cursor.execute(
            """INSERT INTO products
               (product_id, product_name, category, brand, purchase_price, selling_price,
                quantity, min_stock, unit, description, image_path, date_added, gst_rate, barcode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product_id, product_name, category, brand,
                float(purchase_price), float(selling_price),
                int(quantity), int(min_stock), unit,
                description, image_path, date_added, float(gst_rate), barcode or None
            )
        )
        if int(quantity) > 0:
            log_stock_movement(product_id, product_name, int(quantity), int(quantity), "Opening stock", "", user_name)
        connection.commit()
    except Exception:
        connection.rollback()
        raise

def load_products():
    cursor.execute("SELECT * FROM products ORDER BY rowid")
    return cursor.fetchall()

def search_products(keyword):
    search_term = "%" + keyword + "%"
    cursor.execute(
        """SELECT * FROM products WHERE product_name LIKE ? OR product_id LIKE ?
           OR category LIKE ? OR brand LIKE ? OR barcode LIKE ?""",
        (search_term, search_term, search_term, search_term, search_term)
    )
    return cursor.fetchall()

def get_product(product_id):
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    return cursor.fetchone()

# used by the barcode scanner, a product id typed in works too
def get_product_by_barcode(code):
    cursor.execute("SELECT * FROM products WHERE barcode = ?", (code,))
    product = cursor.fetchone()
    if product is None:
        product = get_product(code)
    return product

def barcode_in_use(barcode, exclude_product_id=None):
    cursor.execute("SELECT product_id FROM products WHERE barcode = ?", (barcode,))
    row = cursor.fetchone()
    return row is not None and row[0] != exclude_product_id

def update_product(product_id, product_name, category, brand,
                   purchase_price, selling_price, quantity,
                   min_stock, unit, description, image_path, gst_rate=18,
                   barcode="", user_name=""):

    cursor.execute("SELECT quantity FROM products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    old_qty = row[0] if row else int(quantity)

    try:
        cursor.execute("""
            UPDATE products SET
                product_name   = ?,
                category       = ?,
                brand          = ?,
                purchase_price = ?,
                selling_price  = ?,
                quantity       = ?,
                min_stock      = ?,
                unit           = ?,
                description    = ?,
                image_path     = ?,
                gst_rate       = ?,
                barcode        = ?
            WHERE product_id = ?
        """, (
            product_name, category, brand,
            float(purchase_price), float(selling_price),
            int(quantity), int(min_stock), unit,
            description, image_path, float(gst_rate), barcode or None, product_id
        ))

        # if the quantity was changed in the edit form, keep a record of it
        if int(quantity) != old_qty:
            log_stock_movement(
                product_id, product_name, int(quantity) - old_qty, int(quantity),
                "Manual adjustment", "Product edit form", user_name
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

def delete_product(product_id):
    cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    connection.commit()

# id, name, price, stock, unit, min stock
def get_all_products_for_billing():
    cursor.execute("SELECT product_id, product_name, selling_price, quantity, unit, min_stock FROM products ORDER BY rowid")
    return cursor.fetchall()

def get_low_stock_products():
    cursor.execute("SELECT * FROM products WHERE quantity > 0 AND quantity <= min_stock")
    return cursor.fetchall()

def get_out_of_stock_products():
    cursor.execute("SELECT * FROM products WHERE quantity <= 0")
    return cursor.fetchall()

def get_product_count():
    cursor.execute("SELECT COUNT(*) FROM products")
    return cursor.fetchone()[0]

# customers table
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    customer_name TEXT,
    phone         TEXT,
    email         TEXT,
    address       TEXT
)""")
connection.commit()

def save_customer(customer_id, customer_name, phone, email, address):
    cursor.execute("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", (customer_id, customer_name, phone, email, address))
    connection.commit()

def load_customers():
    cursor.execute("SELECT * FROM customers ORDER BY rowid")
    return cursor.fetchall()

def search_customers(keyword):
    search_term = "%" + keyword + "%"
    cursor.execute(
        "SELECT * FROM customers WHERE customer_name LIKE ? OR customer_id LIKE ? OR phone LIKE ?",
        (search_term, search_term, search_term)
    )
    return cursor.fetchall()

def get_customer(customer_id):
    cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
    return cursor.fetchone()

def update_customer(customer_id, customer_name, phone, email, address):
    cursor.execute("""
        UPDATE customers SET
            customer_name = ?,
            phone         = ?,
            email         = ?,
            address       = ?
        WHERE customer_id = ?
    """, (customer_name, phone, email, address, customer_id))
    connection.commit()

def delete_customer(customer_id):
    cursor.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
    connection.commit()

def get_all_customers_for_billing():
    cursor.execute("SELECT customer_id, customer_name FROM customers ORDER BY customer_name")
    return cursor.fetchall()

def get_customer_count():
    cursor.execute("SELECT COUNT(*) FROM customers")
    return cursor.fetchone()[0]

# sales table
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    sale_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_number    TEXT,
    customer_id    TEXT,
    customer_name  TEXT,
    subtotal       REAL,
    discount       REAL,
    gst            REAL,
    grand_total    REAL,
    payment_method TEXT,
    payment_detail TEXT,
    cashier_name   TEXT,
    sale_date      TEXT,
    sale_time      TEXT
)""")
connection.commit()

add_column_if_missing("sales", "payment_detail", "TEXT")

# sale_date is for showing on screen, sale_date_iso (2026-10-03) is for filtering and sorting
add_column_if_missing("sales", "sale_date_iso", "TEXT")

cursor.execute("SELECT sale_id, sale_date FROM sales WHERE sale_date_iso IS NULL OR sale_date_iso = ''")
for old_id, old_date in cursor.fetchall():
    try:
        iso = datetime.datetime.strptime(old_date, "%d %b %Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        continue
    cursor.execute("UPDATE sales SET sale_date_iso = ? WHERE sale_id = ?", (iso, old_id))
connection.commit()

# sale items table
cursor.execute("""
CREATE TABLE IF NOT EXISTS sale_items (
    item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id      INTEGER,
    product_id   TEXT,
    product_name TEXT,
    quantity     INTEGER,
    unit_price   REAL,
    item_total   REAL
)""")
connection.commit()

# a bill can be paid with more than one method (cash + UPI...), one row per payment
cursor.execute("""
CREATE TABLE IF NOT EXISTS sale_payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id    INTEGER,
    method     TEXT,
    amount     REAL,
    detail     TEXT
)""")
connection.commit()

# older bills only have one payment, copy it over so every bill has at least one row
cursor.execute("""
    INSERT INTO sale_payments (sale_id, method, amount, detail)
    SELECT sale_id, payment_method, grand_total, payment_detail FROM sales
    WHERE sale_id NOT IN (SELECT DISTINCT sale_id FROM sale_payments)
""")
connection.commit()

# saves the bill, its items and the stock change in one go
# if anything fails (like not enough stock) nothing is saved
def save_sale(bill_number, customer_id, customer_name,
              subtotal, discount, gst, grand_total,
              payment_method, cashier_name, cart_items,
              payment_detail="", payments=None):

    # payments = list of (method, amount, detail), leave it out for a single payment
    if payments is None:
        payments = [(payment_method, grand_total, payment_detail)]

    now = datetime.datetime.now()
    date = now.strftime("%d %b %Y")
    date_iso = now.strftime("%Y-%m-%d")
    time = now.strftime("%I:%M %p")

    try:
        # the payments have to cover the bill exactly
        paid_total = round(sum(p[1] for p in payments), 2)
        if abs(paid_total - round(grand_total, 2)) > 0.01:
            raise ValueError(f"The payments add up to {paid_total:.2f} but the bill total is {grand_total:.2f}.")

        # make sure every item is still in stock
        stock_before = {}
        for item in cart_items:
            cursor.execute("SELECT quantity FROM products WHERE product_id = ?", (item["id"],))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"'{item['name']}' no longer exists in the product list.")
            if row[0] < item["qty"]:
                raise ValueError(f"Only {row[0]} unit(s) of '{item['name']}' left in stock.")
            stock_before[item["id"]] = row[0]

        cursor.execute("""
            INSERT INTO sales
            (bill_number, customer_id, customer_name, subtotal,
             discount, gst, grand_total, payment_method, payment_detail,
             cashier_name, sale_date, sale_date_iso, sale_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bill_number, customer_id, customer_name,
            subtotal, discount, gst, grand_total,
            payment_method, payment_detail, cashier_name, date, date_iso, time
        ))
        sale_id = cursor.lastrowid

        for method, amount, detail in payments:
            cursor.execute(
                "INSERT INTO sale_payments (sale_id, method, amount, detail) VALUES (?, ?, ?, ?)",
                (sale_id, method, amount, detail)
            )

        for item in cart_items:
            item_total = item["price"] * item["qty"]
            cursor.execute("""
                INSERT INTO sale_items
                (sale_id, product_id, product_name, quantity, unit_price, item_total)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sale_id, item["id"], item["name"],
                item["qty"], item["price"], item_total
            ))
            cursor.execute(
                "UPDATE products SET quantity = quantity - ? WHERE product_id = ?",
                (item["qty"], item["id"])
            )
            log_stock_movement(
                item["id"], item["name"], -item["qty"],
                stock_before[item["id"]] - item["qty"],
                "Sale", bill_number, cashier_name
            )

        connection.commit()
        return sale_id

    except Exception:
        connection.rollback()
        raise

def get_today_sales():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COALESCE(SUM(grand_total), 0) FROM sales WHERE sale_date_iso = ?", (today,))
    return cursor.fetchone()[0]

def get_today_bill_count():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM sales WHERE sale_date_iso = ?", (today,))
    return cursor.fetchone()[0]

def get_recent_sales(limit=5):
    cursor.execute(
        "SELECT bill_number, customer_name, grand_total, sale_time FROM sales ORDER BY sale_id DESC LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()

# sales for the report page, dates are in 2026-10-03 format
# leave both dates empty to get everything
def get_sales_report(start_date=None, end_date=None):
    sql = """
        SELECT bill_number, customer_name, sale_date, sale_time,
               subtotal, discount, gst, grand_total,
               payment_method, cashier_name
        FROM sales
    """
    params = ()
    if start_date and end_date:
        sql += " WHERE sale_date_iso BETWEEN ? AND ?"
        params = (start_date, end_date)
    sql += " ORDER BY sale_id DESC"

    cursor.execute(sql, params)
    return cursor.fetchall()

def get_sale_by_bill(bill_number):
    cursor.execute("""
        SELECT sale_id, bill_number, customer_id, customer_name,
               subtotal, discount, gst, grand_total,
               payment_method, payment_detail, cashier_name,
               sale_date, sale_time
        FROM sales
        WHERE bill_number = ?
    """, (bill_number,))
    return cursor.fetchone()

def get_sale_payments(sale_id):
    cursor.execute(
        "SELECT method, amount, detail FROM sale_payments WHERE sale_id = ? ORDER BY payment_id",
        (sale_id,)
    )
    return cursor.fetchall()

def get_sale_items(sale_id):
    cursor.execute("""
        SELECT product_id, product_name, quantity, unit_price, item_total
        FROM sale_items
        WHERE sale_id = ?
        ORDER BY item_id
    """, (sale_id,))
    return cursor.fetchall()

# sqlite never reuses an AUTOINCREMENT id, so a bill number can't repeat
# even if an old sale is deleted
def get_next_bill_number():
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'sales'")
    row = cursor.fetchone()
    last_id = row[0] if row else 0
    return f"PM-{str(last_id + 1).zfill(4)}"

# suppliers table
cursor.execute("""
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id    TEXT PRIMARY KEY,
    supplier_name  TEXT,
    contact_person TEXT,
    phone          TEXT,
    email          TEXT,
    gst_number     TEXT,
    address        TEXT,
    city           TEXT,
    state          TEXT
)""")
connection.commit()

# what we already owed this supplier before we started using the app
add_column_if_missing("suppliers", "opening_balance", "REAL DEFAULT 0")

def save_supplier(supplier_id, supplier_name, contact_person,
                  phone, email, gst_number, address, city, state, opening_balance=0):
    cursor.execute(
        """INSERT INTO suppliers
           (supplier_id, supplier_name, contact_person, phone, email, gst_number,
            address, city, state, opening_balance)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (supplier_id, supplier_name, contact_person, phone, email, gst_number,
         address, city, state, float(opening_balance or 0))
    )
    connection.commit()

def load_suppliers():
    cursor.execute("SELECT * FROM suppliers ORDER BY rowid")
    return cursor.fetchall()

def search_suppliers(keyword):
    search_term = "%" + keyword + "%"
    cursor.execute(
        "SELECT * FROM suppliers WHERE supplier_name LIKE ? OR supplier_id LIKE ? OR phone LIKE ? OR city LIKE ?",
        (search_term, search_term, search_term, search_term)
    )
    return cursor.fetchall()

def get_supplier(supplier_id):
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    return cursor.fetchone()

def update_supplier(supplier_id, supplier_name, contact_person,
                    phone, email, gst_number, address, city, state, opening_balance=0):
    cursor.execute("""
        UPDATE suppliers SET
            supplier_name  = ?,
            contact_person = ?,
            phone          = ?,
            email          = ?,
            gst_number     = ?,
            address        = ?,
            city           = ?,
            state          = ?,
            opening_balance = ?
        WHERE supplier_id = ?
    """, (
        supplier_name, contact_person, phone, email,
        gst_number, address, city, state, float(opening_balance or 0), supplier_id
    ))
    connection.commit()

def delete_supplier(supplier_id):
    cursor.execute("DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    connection.commit()

def get_supplier_count():
    cursor.execute("SELECT COUNT(*) FROM suppliers")
    return cursor.fetchone()[0]

# ------------------------------------------------------------------
# purchase orders and supplier payments
# ------------------------------------------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number      TEXT UNIQUE,
    supplier_id    TEXT,
    supplier_name  TEXT,
    status         TEXT,
    order_date     TEXT,
    order_date_iso TEXT,
    expected_date  TEXT,
    received_date  TEXT,
    notes          TEXT,
    total          REAL,
    created_by     TEXT
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS po_items (
    item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id        INTEGER,
    product_id   TEXT,
    product_name TEXT,
    quantity     INTEGER,
    unit_cost    REAL,
    received_qty INTEGER DEFAULT 0
)""")

# one row every time goods arrive, this is what the supplier balance is built from
cursor.execute("""
CREATE TABLE IF NOT EXISTS po_receipts (
    receipt_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id       INTEGER,
    received_at TEXT,
    amount      REAL,
    received_by TEXT
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS supplier_payments (
    payment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id TEXT,
    po_id       INTEGER,
    amount      REAL,
    method      TEXT,
    reference   TEXT,
    note        TEXT,
    paid_at     TEXT,
    created_by  TEXT
)""")
connection.commit()

def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# PO-0001, PO-0002... (an AUTOINCREMENT id is never reused, so a number can't repeat)
def get_next_po_number():
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'purchase_orders'")
    row = cursor.fetchone()
    last_id = row[0] if row else 0
    return f"PO-{str(last_id + 1).zfill(4)}"

# items = list of dicts {"id", "name", "qty", "cost"}, gives back the total
def check_po_items(items):
    if not items:
        raise ValueError("Add at least one product to the order.")

    total = 0
    for item in items:
        if int(item["qty"]) <= 0:
            raise ValueError(f"Quantity for '{item['name']}' must be more than 0.")
        cost = float(item["cost"])
        if not (cost >= 0) or cost == float("inf"):
            raise ValueError(f"The cost for '{item['name']}' is not valid.")
        cursor.execute("SELECT 1 FROM products WHERE product_id = ?", (item["id"],))
        if cursor.fetchone() is None:
            raise ValueError(f"'{item['name']}' no longer exists in the product list.")
        total += int(item["qty"]) * cost
    return round(total, 2)

def save_po_lines(po_id, items):
    cursor.execute("DELETE FROM po_items WHERE po_id = ?", (po_id,))
    for item in items:
        cursor.execute(
            """INSERT INTO po_items (po_id, product_id, product_name, quantity, unit_cost, received_qty)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (po_id, item["id"], item["name"], int(item["qty"]), float(item["cost"]))
        )

def create_purchase_order(supplier_id, expected_date, notes, items, user_name, status="Draft"):
    supplier = get_supplier(supplier_id)
    if supplier is None:
        raise ValueError("Please choose a supplier.")
    if status not in ("Draft", "Ordered"):
        raise ValueError("A new order can only be a Draft or Ordered.")

    try:
        total = check_po_items(items)
        now = datetime.datetime.now()
        cursor.execute(
            """INSERT INTO purchase_orders
               (po_number, supplier_id, supplier_name, status, order_date, order_date_iso,
                expected_date, notes, total, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (get_next_po_number(), supplier_id, supplier[1], status,
             now.strftime("%d %b %Y"), now.strftime("%Y-%m-%d"),
             expected_date, notes, total, user_name)
        )
        po_id = cursor.lastrowid
        save_po_lines(po_id, items)
        connection.commit()
        return po_id
    except Exception:
        connection.rollback()
        raise

# only a draft can be edited
def update_purchase_order(po_id, supplier_id, expected_date, notes, items, status="Draft"):
    order = get_purchase_order(po_id)
    if order is None:
        raise ValueError("This order no longer exists.")
    if order[4] != "Draft":
        raise ValueError("Only a Draft order can be edited.")
    supplier = get_supplier(supplier_id)
    if supplier is None:
        raise ValueError("Please choose a supplier.")
    if status not in ("Draft", "Ordered"):
        raise ValueError("An edited order can only be a Draft or Ordered.")

    try:
        total = check_po_items(items)
        cursor.execute(
            """UPDATE purchase_orders SET supplier_id = ?, supplier_name = ?, status = ?,
               expected_date = ?, notes = ?, total = ? WHERE po_id = ?""",
            (supplier_id, supplier[1], status, expected_date, notes, total, po_id)
        )
        save_po_lines(po_id, items)
        connection.commit()
    except Exception:
        connection.rollback()
        raise

# which status changes are allowed
PO_STATUS_CHANGES = {
    "Draft": ("Ordered", "Cancelled"),
    "Ordered": ("Cancelled",),
}

def set_po_status(po_id, new_status):
    order = get_purchase_order(po_id)
    if order is None:
        raise ValueError("This order no longer exists.")
    if new_status not in PO_STATUS_CHANGES.get(order[4], ()):
        if order[4] == "Partially Received" and new_status == "Cancelled":
            raise ValueError("Stock from this order was already received, so it can't be cancelled.")
        raise ValueError(f"A {order[4]} order can't be changed to {new_status}.")

    cursor.execute("UPDATE purchase_orders SET status = ? WHERE po_id = ?", (new_status, po_id))
    connection.commit()

# header: po_id, po_number, supplier_id, supplier_name, status, order_date,
#         expected_date, received_date, notes, total, created_by
def get_purchase_order(po_id):
    cursor.execute(
        """SELECT po_id, po_number, supplier_id, supplier_name, status, order_date,
                  expected_date, received_date, notes, total, created_by
           FROM purchase_orders WHERE po_id = ?""",
        (po_id,)
    )
    return cursor.fetchone()

# item_id, product_id, product_name, quantity, unit_cost, received_qty
def get_po_items(po_id):
    cursor.execute(
        """SELECT item_id, product_id, product_name, quantity, unit_cost, received_qty
           FROM po_items WHERE po_id = ? ORDER BY item_id""",
        (po_id,)
    )
    return cursor.fetchall()

# po_id, po_number, supplier, order_date, expected, status, item count, total, received value, paid, due
def get_purchase_orders(status=None, keyword=""):
    sql = """
        SELECT p.po_id, p.po_number, p.supplier_name, p.order_date, p.expected_date, p.status,
               (SELECT COUNT(*) FROM po_items i WHERE i.po_id = p.po_id),
               p.total,
               (SELECT COALESCE(SUM(i.received_qty * i.unit_cost), 0) FROM po_items i WHERE i.po_id = p.po_id),
               (SELECT COALESCE(SUM(s.amount), 0) FROM supplier_payments s WHERE s.po_id = p.po_id)
        FROM purchase_orders p
        WHERE 1 = 1
    """
    params = []
    if status:
        sql += " AND p.status = ?"
        params.append(status)
    if keyword:
        sql += " AND (p.po_number LIKE ? OR p.supplier_name LIKE ?)"
        params += ["%" + keyword + "%", "%" + keyword + "%"]
    sql += " ORDER BY p.po_id DESC"

    cursor.execute(sql, params)
    rows = []
    for r in cursor.fetchall():
        received_value = round(r[8], 2)
        paid = round(r[9], 2)
        rows.append(r[:8] + (received_value, paid, round(received_value - paid, 2)))
    return rows

# received = {item_id: quantity arriving now}
# adds the stock, writes the stock log and the receipt in one go
def receive_po_items(po_id, received, user_name="", update_prices=False):
    order = get_purchase_order(po_id)
    if order is None:
        raise ValueError("This order no longer exists.")
    if order[4] not in ("Ordered", "Partially Received"):
        raise ValueError(f"Stock can't be received on a {order[4]} order. Mark it as Ordered first.")

    try:
        receipt_value = 0
        any_received = False

        for item_id, product_id, product_name, quantity, unit_cost, received_qty in get_po_items(po_id):
            arriving = int(received.get(item_id, 0))
            if arriving < 0:
                raise ValueError("Quantities can't be negative.")
            if arriving == 0:
                continue
            if arriving > quantity - received_qty:
                raise ValueError(f"Only {quantity - received_qty} more of '{product_name}' are still expected.")

            cursor.execute("SELECT quantity FROM products WHERE product_id = ?", (product_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"'{product_name}' no longer exists in the product list.")
            new_qty = row[0] + arriving

            cursor.execute("UPDATE products SET quantity = ? WHERE product_id = ?", (new_qty, product_id))
            cursor.execute("UPDATE po_items SET received_qty = received_qty + ? WHERE item_id = ?", (arriving, item_id))
            if update_prices:
                cursor.execute("UPDATE products SET purchase_price = ? WHERE product_id = ?", (unit_cost, product_id))

            log_stock_movement(product_id, product_name, arriving, new_qty,
                               "Received from supplier", order[1], user_name)
            receipt_value += arriving * unit_cost
            any_received = True

        if not any_received:
            raise ValueError("Enter how many items arrived.")

        cursor.execute("SELECT COUNT(*) FROM po_items WHERE po_id = ? AND received_qty < quantity", (po_id,))
        still_open = cursor.fetchone()[0]
        new_status = "Partially Received" if still_open else "Received"

        cursor.execute(
            "INSERT INTO po_receipts (po_id, received_at, amount, received_by) VALUES (?, ?, ?, ?)",
            (po_id, now_text(), round(receipt_value, 2), user_name)
        )
        cursor.execute(
            "UPDATE purchase_orders SET status = ?, received_date = ? WHERE po_id = ?",
            (new_status, datetime.datetime.now().strftime("%d %b %Y"), po_id)
        )
        connection.commit()
        return new_status
    except Exception:
        connection.rollback()
        raise

# ---- what we owe the suppliers ----
# balance = opening balance + goods received - payments made
def get_supplier_balance(supplier_id):
    supplier = get_supplier(supplier_id)
    if supplier is None:
        return 0

    opening = (supplier[9] if len(supplier) > 9 else 0) or 0

    cursor.execute(
        """SELECT COALESCE(SUM(r.amount), 0) FROM po_receipts r
           JOIN purchase_orders p ON p.po_id = r.po_id WHERE p.supplier_id = ?""",
        (supplier_id,)
    )
    received = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM supplier_payments WHERE supplier_id = ?", (supplier_id,))
    paid = cursor.fetchone()[0]

    return round(opening + received - paid, 2)

def get_all_supplier_balances():
    cursor.execute("SELECT supplier_id FROM suppliers")
    ids = [r[0] for r in cursor.fetchall()]
    return {sid: get_supplier_balance(sid) for sid in ids}

# what is still unpaid on one order (goods received minus payments made against it)
def get_po_due(po_id):
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM po_receipts WHERE po_id = ?", (po_id,))
    received = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM supplier_payments WHERE po_id = ?", (po_id,))
    paid = cursor.fetchone()[0]
    return round(received - paid, 2)

def record_supplier_payment(supplier_id, amount, method, reference="", note="", user_name="", po_id=None):
    if get_supplier(supplier_id) is None:
        raise ValueError("This supplier no longer exists.")

    amount = round(float(amount), 2)
    if not (amount > 0) or amount == float("inf"):
        raise ValueError("The amount must be more than 0.")

    if po_id:
        order = get_purchase_order(po_id)
        if order is None or order[2] != supplier_id:
            raise ValueError("This order does not belong to the supplier.")
        due = get_po_due(po_id)
        if amount > due + 0.005:
            raise ValueError(f"This is more than what is due on {order[1]} (₹{due:.2f}).")

    balance = get_supplier_balance(supplier_id)
    if amount > balance + 0.005:
        raise ValueError(f"This is more than the balance owed to the supplier (₹{balance:.2f}).")

    cursor.execute(
        """INSERT INTO supplier_payments
           (supplier_id, po_id, amount, method, reference, note, paid_at, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (supplier_id, po_id, amount, method, reference, note, now_text(), user_name)
    )
    connection.commit()
    return cursor.lastrowid

# paid_at, method, reference, note, amount, po_number (or "")
def get_po_payments(po_id):
    cursor.execute(
        """SELECT paid_at, method, reference, note, amount FROM supplier_payments
           WHERE po_id = ? ORDER BY payment_id""",
        (po_id,)
    )
    return cursor.fetchall()

# statement for one supplier: (time, description, owed more, paid, running balance)
def get_supplier_ledger(supplier_id):
    supplier = get_supplier(supplier_id)
    if supplier is None:
        return []

    entries = []
    opening = (supplier[9] if len(supplier) > 9 else 0) or 0
    if opening:
        entries.append(("0000", "Opening balance", opening, 0))

    cursor.execute(
        """SELECT r.received_at, p.po_number, r.amount FROM po_receipts r
           JOIN purchase_orders p ON p.po_id = r.po_id WHERE p.supplier_id = ?""",
        (supplier_id,)
    )
    for received_at, po_number, amount in cursor.fetchall():
        entries.append((received_at, f"Goods received — {po_number}", amount, 0))

    cursor.execute(
        """SELECT s.paid_at, s.method, s.reference, p.po_number, s.amount
           FROM supplier_payments s LEFT JOIN purchase_orders p ON p.po_id = s.po_id
           WHERE s.supplier_id = ?""",
        (supplier_id,)
    )
    for paid_at, method, reference, po_number, amount in cursor.fetchall():
        label = f"Payment — {method}"
        if po_number:
            label += f" ({po_number})"
        if reference:
            label += f" ref {reference}"
        entries.append((paid_at, label, 0, amount))

    entries.sort(key=lambda e: e[0])

    ledger = []
    balance = 0
    for when, label, owed, paid in entries:
        balance = round(balance + owed - paid, 2)
        ledger.append((when, label, owed, paid, balance))
    return ledger

# a supplier with orders or payments must not be deleted
def supplier_has_history(supplier_id):
    cursor.execute("SELECT COUNT(*) FROM purchase_orders WHERE supplier_id = ?", (supplier_id,))
    orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM supplier_payments WHERE supplier_id = ?", (supplier_id,))
    payments = cursor.fetchone()[0]
    return orders + payments > 0

# backup and restore
def create_backup(prefix="phantommart"):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = os.path.join(BACKUP_DIR, f"{prefix}_{stamp}.db")

    connection.commit()
    copy = sqlite3.connect(path)
    try:
        connection.backup(copy)
    finally:
        copy.close()
    return path

def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")]
    files.sort(reverse=True)
    return [os.path.join(BACKUP_DIR, f) for f in files]

# makes sure a file really is a Phantom Mart database before we restore it
def check_backup_file(path):
    try:
        test = sqlite3.connect(path)
        try:
            if test.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False, "This file is damaged."
            tables = {r[0] for r in test.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            test.close()
    except sqlite3.DatabaseError:
        return False, "This is not a valid database file."

    for needed in ("users", "products", "sales"):
        if needed not in tables:
            return False, "This does not look like a Phantom Mart backup."
    return True, ""

# replaces everything in the live database with the backup
# a safety copy of the current data is made first
def restore_backup(path):
    ok, message = check_backup_file(path)
    if not ok:
        raise ValueError(message)

    safety_copy = create_backup("before_restore")

    source = sqlite3.connect(path)
    try:
        source.backup(connection)
    finally:
        source.close()
    return safety_copy
