# Phantom·Mart — Supermarket POS & Store Management

A desktop point-of-sale app for a supermarket or grocery shop. It handles billing, stock,
purchasing from suppliers, customers and loyalty points, and sales reports.

It is written in **Python + Tkinter + SQLite**. There is no server and no internet needed.
Everything is stored in one file, `phantommart.db`, that sits next to the code.

---

## 1. Quick start (Windows)

1. Install **Python 3.10 or newer** from python.org. Tick *"Add Python to PATH"* during setup.
2. Put all the project files in one folder.
3. Open **Command Prompt in that folder** and install the packages:

   ```
   pip install -r requirements.txt
   ```

   (`requirements.txt` lists the packages in the table below.)

   | Package | Needed for | If it is missing |
   |---|---|---|
   | `pillow` | logo and product pictures | the app will not start |
   | `reportlab` | PDF bills and reports | the app will not start |
   | `qrcode` | the UPI QR code at billing | a warning shows instead of the QR |
   | `matplotlib` | dashboard charts | a text summary shows instead of charts |
   | `openpyxl` | Excel (.xlsx) export | CSV export still works |

4. Start the app:

   ```
   python main.py
   ```

On the very first start the app creates `phantommart.db` by itself, with the three default
users and six starter categories. You do not need a database file to begin.

> **Important:** `pip` and the Python that runs the app must be the **same Python**.
> If you have more than one Python installed (for example 3.12 and 3.14), install the
> packages for the one you actually use, e.g. `py -3.14 -m pip install matplotlib`.
> See *Troubleshooting* below.

---

## 2. The database files (`sample_data/` folder)

The app works with a single file called **`phantommart.db`**, placed in the same folder as
`main.py`. Two ready-made files are provided in `sample_data/`:

| File | What it is | Use it for |
|---|---|---|
| `phantommart_demo.db` | A full demo shop: 36 products, 10 customers, 4 suppliers, **about 1,150 bills over 90 days**, purchase orders, supplier payments and loyalty points | Trying the app, seeing charts and reports with real-looking numbers, training staff |

### The easy way: one command

```
python sample_data\load_demo.py            (loads the demo shop, so you can see sample data in the app)
python sample_data\load_demo.py --empty    (goes back to a clean, empty database)
```

If you already have a `phantommart.db`, it asks first and saves a copy in `backups/` before
replacing anything. Then start the app with `python main.py`.

### Or do it by hand

1. **Close the app.**
2. **Back up your current `phantommart.db`** if you have one. Copying a file over it replaces
   everything.
3. Copy the file you want into the project folder (next to `main.py`) and **rename it to
   `phantommart.db`**.
4. Start the app.

### About the demo data

- Everything in it is **made up**: names, phone numbers, GST numbers and barcodes (the
  barcodes start with `8909999`). Brands are invented.
- The data is realistic and consistent: stock matches the stock log, every bill adds up, and
  supplier balances reconcile.
- Dates end on the day the file was made. If the dashboard shows ₹0 for today or the chart
  ends in a drop, bring the dates up to today:

  ```
  python sample_data\refresh_demo_dates.py
  ```

  This moves every date forward so the newest bills are dated today. It only works on the
  demo database (it refuses anything else), so real shop data is never touched.
- **Do not use the demo database for your real shop.** Start from `phantommart_empty.db`.

---

## 3. Logins

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Manager | `manager` | `mgr123` |
| Cashier | `cashier` | `cash123` |

On the login screen, pick the matching role button, then type the username and password.

**Change these passwords before real use.** Passwords are stored hashed (PBKDF2), but these
defaults are public. There is no change-password screen yet. Until there is, open Command
Prompt in the project folder and run:

```
python -c "import database as db, security as s; db.cursor.execute('UPDATE users SET password = ? WHERE username = ?', (s.hash_password('YourNewPassword'), 'admin')); db.connection.commit(); print('done')"
```

Replace `YourNewPassword` and `admin` as needed (do it for `manager` and `cashier` too).
Close the app first.

---

## 4. Who can do what

| | Admin | Manager | Cashier |
|---|:--:|:--:|:--:|
| Billing, customer lookup, barcode scanning | ✅ | ✅ | ✅ |
| View products, categories, suppliers (no costs or balances) | ✅ | ✅ | ✅ |
| View a customer's purchase history | ✅ | ✅ | ✅ |
| Add / edit / delete products, customers, suppliers | ✅ | ✅ | ❌ |
| Adjust stock, stock history, CSV/Excel export | ✅ | ✅ | ❌ |
| Purchase orders, supplier payments, supplier ledgers | ✅ | ✅ | ❌ |
| Adjust loyalty points | ✅ | ✅ | ❌ |
| Sales report, dashboard charts | ✅ | ✅ | ❌ |
| Settings, backup and restore | ✅ | ❌ | ❌ |

The roles are defined in `security.py`.

---

## 5. What the app does

**Billing**
- Search and pick products, double-click to add, or **scan a barcode** (scan + Enter adds one item;
  typing a product ID also works).
- Quantity buttons that respect stock, a typed discount, and **GST per item** using each product's own rate.
- Payment methods: **Cash** (with change calculator), **UPI** (scannable QR), **Card**, **Net Banking**,
  **Wallet**, and **Split** (several methods on one bill).
- **Loyalty points:** a registered customer can spend points as a discount (the **Max** button helps),
  and the screen shows how many points the bill will earn.
- After the sale: a **PDF bill**, a **thermal receipt**, or skip.
- Each sale is saved in one step: the bill, items, payments, stock change, stock log and points.
  If anything fails, nothing is saved.

**Products & stock**
- Name, category, brand, purchase and selling price, GST %, quantity, minimum stock, unit, barcode,
  description and picture.
- Rows are coloured for in stock, low stock and out of stock, and the dashboard lists the alerts.
- **± Adjust Stock** (received, damaged, expired, count correction) and **📋 Stock History**, a full
  audit log of every stock change with who did it and when.

**Suppliers & purchasing**
- Supplier details, GST number and an **opening balance** (what you owed before using the app).
- **Purchase orders:** Draft → Ordered → Partially Received → Received (or Cancelled).
  Receiving stock adds it to your inventory and writes the stock log with the PO number. Partial
  deliveries are supported.
- **Supplier payments** (against an order or on account) and a **ledger** per supplier that always shows
  the running balance owed. Overpaying is refused.

**Customers & loyalty**
- Customer list, **purchase history** (lifetime spent, number of bills, average bill, bills with their
  items) and a points log.
- Default: 1 point for every ₹100 spent, and 1 point = ₹1 off. Change this in **Settings**.

**Reports & analytics**
- **Sales report:** filter by All Time, Today, This Month or a custom date range. Double-click a bill to see it,
  reprint the PDF or open its thermal receipt.
- **Dashboard charts:** daily sales over 7, 30 or 90 days, and the top 5 products by units or revenue.
- Export to **PDF**, **CSV** or **Excel**.

**Data safety**
- **Backup and restore** from the Settings page (Admin only).
- Passwords are hashed and SQL is parameterised. Role checks apply on every page and form.

---

## 6. Setting it up for your shop

| What | Where |
|---|---|
| Shop name, address, phone, GSTIN (shown on PDF bills and receipts) | the first lines of `pdf_export.py` |
| Your UPI ID (used in the QR code) | `SHOP_UPI_ID` at the top of `billing.py` |
| Logo | replace `logo.png` (keep the same name) |
| GST % | on each product (default 18) |
| Default minimum stock, loyalty rates | **Settings** page in the app |

Quick order flow for new stock: **Purchase Orders → New** (pick supplier and products) → **Save & Mark
Ordered** → when it arrives, select it and **Receive Stock** → later, **Pay Supplier**.

---

## 7. Backup and restore

- **Create a backup:** Settings → **Create Backup Now**. It saves a timestamped file in the `backups/` folder.
  It is safe to do while the app is running.
- **Restore:** Settings → **Restore From File**. It checks the file is a real Phantom·Mart database, makes a
  safety copy of your current data first, replaces everything, and then **closes the app**. Just open it again.
- Also copy the `backups/` folder somewhere else (a USB drive or cloud folder) now and then. A backup on the
  same computer will not help if the computer fails.

---

## 8. Troubleshooting

**The dashboard says "Charts need matplotlib…" even though I installed it**
You have more than one Python, and `pip` installed matplotlib into a different one than the one running the app.
The message on the dashboard shows the exact command for the right Python, with a **Copy** button. Run it in
Command Prompt. Or run the app with the Python that already has it (`python main.py`).

**The UPI QR code is missing, or Excel export only offers CSV**
Install `qrcode` or `openpyxl` for the same Python (see above).

**The ₹ sign shows as "Rs." in PDFs**
No suitable font was found. On Windows, Segoe UI or Arial is used automatically. You can also put
`DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` in a folder named `fonts` next to `pdf_export.py`.

**Thermal receipt printing**
Choose *Thermal Receipt* after a sale, pick 80mm or 58mm, and either save a `.txt` or a raw ESC/POS `.prn` file.
To print the `.prn` file on Windows, share the printer, then run:
`copy /b receipt.prn \\localhost\YourPrinterShareName`.
Basic thermal printers cannot print Tamil or other non-English text; those characters print as `?`.

**Barcode scanner**
Scanners act like a keyboard that types the code and presses Enter. At Billing, the cursor starts in the
**Scan** box. Put a barcode on each product in the product form.

**"I forgot the admin password"**
Use the reset command in section 3.

**Buttons at the bottom of a page look cut off**
Update to the latest files; the button row is now always reserved first on every list page.

**The app does not start: "No module named …"**
Install the missing package with `pip install <name>` for the Python you use. On Linux you may also need
`sudo apt install python3-tk`.

---

## 9. Files

| File | What it does |
|---|---|
| `main.py` | login screen and app start |
| `dashboard.py` | sidebar, top bar, dashboard |
| `billing.py` | the billing screen |
| `products.py` | products list and form |
| `categories.py` | categories |
| `customers.py`, `customer_history.py` | customers, purchase history, points |
| `suppliers.py`, `supplier_money.py` | suppliers, payments, ledgers |
| `purchases.py` | purchase orders |
| `stock.py` | stock adjustments and stock history |
| `reports.py` | sales report |
| `charts.py` | dashboard charts |
| `settings.py` | settings, backup and restore |
| `database.py` | the database: tables and all queries |
| `security.py` | password hashing and role rules |
| `navigation.py` | opens pages |
| `styles.py` | colours, fonts, theme |
| `pdf_export.py` | PDF bills, reports, product list |
| `thermal.py`, `receipt_ui.py` | thermal receipts and the print choice |
| `export_tools.py` | CSV / Excel export |
| `logo.png` | your logo |
| `sample_data/` | demo and empty databases, and the date refresh script |

Created automatically while you use the app: `phantommart.db`, `backups/`, `product_images/`.

### Database tables

`users`, `settings`, `categories`, `products`, `customers`, `suppliers` · `sales`, `sale_items`,
`sale_payments` · `stock_movements` · `loyalty_points` · `purchase_orders`, `po_items`,
`po_receipts`, `supplier_payments`.

---

## 10. Known limitations

- No change-password or user-management screen yet (use the reset command above).
- No returns or refunds: a sale cannot be reversed, and returned goods cannot go back into stock.
- No profit report, and no payment-mode totals (a split bill shows as "Split").
- One computer only: a single local database file, with no syncing between several terminals.
  Do not open the app twice on the same database.
- Tested on Python 3.12 on Linux (headless). Not yet tested with a real thermal printer or a real
  barcode scanner.

---

## 11. Putting it on GitHub

**Upload:** all the `.py` files, `logo.png`, `README.md`, `requirements.txt`, `.gitignore`, and the whole
`sample_data/` folder (the demo data is made up, so it is safe to share).

**Never upload:** your own `phantommart.db` (real customers, sales and password hashes), the `backups/`
folder or `product_images/`. The included `.gitignore` keeps these out automatically when you use Git.

Anyone who downloads the project can then run `pip install -r requirements.txt`, then
`python sample_data/load_demo.py`, then `python main.py` and see the sample shop straight away.
