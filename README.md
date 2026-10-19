# 🛒 PhantomMart - POS System

A modern Desktop Point of Sale (POS) system built using Python and Tkinter. PhantomMart helps small retail shops manage their inventory, handle customer billing, track suppliers, and export clean PDF receipts seamlessly.

---

## ✨ Features

- **Billing & Checkout:** Process transactions quickly with an intuitive shopping cart interface.
- **Inventory Management:** Track live stock levels, add/update products, and monitor supplier shipments.
- **Customer CRM:** Save customer profiles and log their transaction history.
- **Suppliers & Finances:** Maintain records of supplier accounts and payments.
- **PDF Export:** Generate professional, print-ready PDF invoices and reports automatically.
- **Responsive Theme:** Built with a custom widget style layer for a unified desktop experience.

---

## 📂 Repository Structure

```text
phantommart/
│
├── requirements.txt         # Project package dependencies
├── README.md                # System documentation
│
└── phantommart/             # Core Source Files
    ├── main.py              # Application entry point
    ├── billing.py           # Checkout & invoice calculations
    ├── categories.py        # Product categorization
    ├── customers.py         # Customer database management
    ├── dashboard.py         # Sales overview stats interface
    ├── database.py          # SQLite engine connections
    ├── export_tools.py      # General data export utilities
    ├── navigation.py        # App sidebar/menu router
    ├── pdf_export.py        # PDF invoice generation engine
    ├── products.py          # Item CRUD operations
    ├── purchases.py         # Restocking logs
    ├── receipt_ui.py        # In-app interactive receipt previews
    ├── reports.py           # Financial reporting views
    ├── security.py          # Authentication handlers
    ├── settings.py          # Application configuration UI
    ├── stock.py             # Inventory counts & alerts
    ├── styles.py            # Global colors and theme rules
    ├── suppliers.py         # Vendor management profiles
    ├── supplier_money.py    # Vendor payouts and statements ledger
    └── thermal.py           # Thermal printer strip generator format
```

---

## 🚀 Getting Started

### 📋 Prerequisites
Make sure you have **Python 3.10+** installed on your system. 

### 🔧 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com
   cd phantommart
   ```

2. **Set up a Virtual Environment (Recommended):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 🏃 Running the App
Execute the app by launching the central execution script:
```bash
python phantommart/main.py
```
*(The local SQLite database configuration will initialize automatically upon your first boot).*

---

## 🛠️ Built With

- **Python** - Core language
- **Tkinter** - Native Desktop GUI framework
- **SQLite** - Embedded local relational database
- **Pillow (PIL)** - Image and asset optimization
- **ReportLab / FPDF** - PDF dynamic generation tools

---

## 🔒 Security Note
This project utilizes a local database engine (`phantommart.db`). Please ensure that runtime database files are **excluded** from your commits via the provided `.gitignore` file to protect active customer and transactional records.
