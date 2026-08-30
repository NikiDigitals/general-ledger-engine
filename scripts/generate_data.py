import sqlite3
import random
from datetime import date, timedelta

random.seed(42)

DB_PATH = "../database/erp_demo.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def random_date_2025():
    start = date(2025, 1, 1)
    random_days = random.randint(0, 364)
    return start + timedelta(days=random_days)

# --- Chart of Accounts ---
cursor.execute("DROP TABLE IF EXISTS chart_of_accounts")

cursor.execute("""
    CREATE TABLE chart_of_accounts (
        account_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        account_code   TEXT NOT NULL UNIQUE,
        account_name   TEXT NOT NULL,
        account_type   TEXT NOT NULL CHECK (account_type IN ('Asset','Liability','Equity','Revenue','Expense')),
        normal_balance TEXT NOT NULL CHECK (normal_balance IN ('Debit','Credit'))
    )
""")
print("chart_of_accounts table created.")

accounts = [
    ("1000", "Cash and Cash Equivalents", "Asset", "Debit"),
    ("1100", "Accounts Receivable", "Asset", "Debit"),
    ("1200", "Inventory", "Asset", "Debit"),
    ("2000", "Accounts Payable", "Liability", "Credit"),
    ("3000", "Common Stock", "Equity", "Credit"),
    ("4000", "Sales Revenue", "Revenue", "Credit"),
    ("5000", "Cost of Goods Sold", "Expense", "Debit"),
]

for code, name, acc_type, balance in accounts:
    cursor.execute("""
        INSERT INTO chart_of_accounts (account_code, account_name, account_type, normal_balance)
        VALUES (?, ?, ?, ?)
    """, (code, name, acc_type, balance))

print(f"{len(accounts)} accounts inserted.")

# --- General Ledger ---
cursor.execute("DROP TABLE IF EXISTS journal_entry_line")
cursor.execute("DROP TABLE IF EXISTS journal_entry")

cursor.execute("""
    CREATE TABLE journal_entry (
        journal_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date       DATE NOT NULL,
        fiscal_year      INTEGER NOT NULL,
        fiscal_period    INTEGER NOT NULL,
        source_module    TEXT NOT NULL CHECK (source_module IN ('O2C', 'P2P', 'R2R', 'Manual')),
        description      TEXT
    )
""")

cursor.execute("""
    CREATE TABLE journal_entry_line (
        line_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        journal_entry_id  INTEGER NOT NULL,
        account_id        INTEGER NOT NULL,
        debit_amount      NUMERIC NOT NULL DEFAULT 0,
        credit_amount     NUMERIC NOT NULL DEFAULT 0,
        CHECK (
            (debit_amount > 0 AND credit_amount = 0)
            OR
            (debit_amount = 0 AND credit_amount > 0)
        ),
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entry(journal_entry_id),
        FOREIGN KEY (account_id) REFERENCES chart_of_accounts(account_id)
    )
""")

print("journal_entry and journal_entry_line tables created.")

# --- Opening capital entry ---
# A business doesn't start at zero — shareholders contribute starting capital.
# This must be posted before any other transaction, so Cash doesn't drift
# negative purely because expenses were recorded before any funding was.
cursor.execute("""
    INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
    VALUES (?, ?, ?, ?, ?)
""", ("2025-01-01", 2025, 1, "Manual", "Opening balance - shareholder capital contribution"))

opening_je_id = cursor.lastrowid

cursor.execute("""
    INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
    VALUES (?, ?, ?, ?)
""", (opening_je_id, 1, 1000.00, 0))  # account_id 1 = Cash

cursor.execute("""
    INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
    VALUES (?, ?, ?, ?)
""", (opening_je_id, 5, 0, 1000.00))  # account_id 5 = Common Stock

print("Opening capital entry created.")


# --- Fiscal Calendar ---
cursor.execute("DROP TABLE IF EXISTS fiscal_calendar")

cursor.execute("""
    CREATE TABLE fiscal_calendar (
        fiscal_year    INTEGER NOT NULL,
        fiscal_period  INTEGER NOT NULL CHECK (fiscal_period BETWEEN 1 AND 12),
        period_name    TEXT NOT NULL,
        start_date     DATE NOT NULL,
        end_date       DATE NOT NULL,
        period_status  TEXT NOT NULL DEFAULT 'Open' CHECK (period_status IN ('Open', 'Closed')),
        PRIMARY KEY (fiscal_year, fiscal_period)
    )
""")

print("fiscal_calendar table created.")

# Genereer alle 12 maanden voor fiscal year 2025
period_names = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]

for month in range(1, 13):
    period_name = period_names[month - 1]
    start_date = f"2025-{month:02d}-01"
    if month == 2:
        end_date = "2025-02-28"
    elif month in [4, 6, 9, 11]:
        end_date = f"2025-{month:02d}-30"
    else:
        end_date = f"2025-{month:02d}-31"

    cursor.execute("""
        INSERT INTO fiscal_calendar (fiscal_year, fiscal_period, period_name, start_date, end_date)
        VALUES (?, ?, ?, ?, ?)
    """, (2025, month, period_name, start_date, end_date))

print("12 fiscal periods inserted.")

# --- Customer ---
cursor.execute("DROP TABLE IF EXISTS customer")

cursor.execute("""
    CREATE TABLE customer (
        customer_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_code       TEXT NOT NULL UNIQUE,
        customer_name       TEXT NOT NULL,
        country             TEXT,
        credit_limit        NUMERIC DEFAULT 0,
        payment_terms_days  INTEGER DEFAULT 30,
        ar_account_id       INTEGER,
        is_active           INTEGER DEFAULT 1,
        FOREIGN KEY (ar_account_id) REFERENCES chart_of_accounts(account_id)
    )
""")

print("customer table created.")

company_prefixes = ["Noordzee", "Delta", "Amstel", "Rijnland", "Veldkamp", "Zuiderzee", "Hollandia", "Maasstad", "Vecht", "Wester"]
company_types = ["Logistics BV", "Retail Group", "Bouwmaterialen", "Foods NV", "Technics", "Handel BV", "Import/Export", "Diensten BV"]

customer_names = []
for _ in range(20):
    name = f"{random.choice(company_prefixes)} {random.choice(company_types)}"
    customer_names.append(name)

for i, name in enumerate(customer_names, start=1):
    customer_code = f"CUST-{i:03d}"
    cursor.execute("""
        INSERT INTO customer (customer_code, customer_name, country, ar_account_id)
        VALUES (?, ?, 'NL', 2)
    """, (customer_code, name))

print(f"{len(customer_names)} customers inserted.")


#---Product---#
cursor.execute("DROP TABLE IF EXISTS product")

cursor.execute("""
CREATE TABLE product(
    product_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sku                   TEXT NOT NULL UNIQUE,
    product_name          TEXT NOT NULL,
    category              TEXT,
    unit_cost             NUMERIC NOT NULL,
    unit_price            NUMERIC NOT NULL,
    revenue_account_id    INTEGER,
    cogs_account_id       INTEGER,
    inventory_account_id  INTEGER,
    FOREIGN KEY (revenue_account_id) REFERENCES chart_of_accounts(account_id),
    FOREIGN KEY (cogs_account_id) REFERENCES chart_of_accounts(account_id),
    FOREIGN KEY (inventory_account_id) REFERENCES chart_of_accounts(account_id)
)
""")
print("product table created.")

product_types = ["Pomp", "Motor", "Sensor", "Frame", "Cilinder", "Ventiel", "Filter", "Aandrijfunit", "Besturingsunit", "Lagerset"]
product_variants = ["Type A", "Compact", "Pro", "Heavy Duty", "Standaard", "Industrieel"]

products = []
for _ in range(15):
    name = f"{random.choice(product_types)} {random.choice(product_variants)}"
    cost = round(random.uniform(10, 200), 2)
    price = round(cost * random.uniform(1.5, 2.2), 2)  # sell at 50-120% markup over cost
    products.append((name, cost, price))

for i, (name, cost, price) in enumerate(products, start=1):
    sku = f"SKU-{1000 +i}"
    cursor.execute("""
        INSERT INTO product (sku, product_name, unit_cost, unit_price,  revenue_account_id, cogs_account_id, inventory_account_id)
       VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sku, name, cost, price, 2, 7, 3))

print(f"{len(products)} products inserted.")

# --- Sales Order + Sales Order Line ---
cursor.execute("DROP TABLE IF EXISTS sales_order_line")
cursor.execute("DROP TABLE IF EXISTS sales_order")

cursor.execute("""
    CREATE TABLE sales_order (
        sales_order_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number    TEXT NOT NULL UNIQUE,
        customer_id     INTEGER NOT NULL,
        order_date      DATE NOT NULL,
        status          TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Fulfilled', 'Invoiced', 'Cancelled')),
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    )
""")

cursor.execute("""
    CREATE TABLE sales_order_line (
        line_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        sales_order_id   INTEGER NOT NULL,
        product_id       INTEGER NOT NULL,
        quantity         NUMERIC NOT NULL,
        unit_price       NUMERIC NOT NULL,
        FOREIGN KEY (sales_order_id) REFERENCES sales_order(sales_order_id),
        FOREIGN KEY (product_id) REFERENCES product(product_id)
    )
""")

print("sales_order and sales_order_line tables created.")

# Create 150 sales orders, each with 1 line, spread across the year
NUM_SALES_ORDERS = 150

for i in range(1, NUM_SALES_ORDERS + 1):
    order_number = f"SO-2025-{i:04d}"
    customer_id = random.randint(1, 20)       # 20 customers now exist
    product_id = random.randint(1, 15)         # 15 products now exist
    quantity = random.randint(1, 10)
    order_date = random_date_2025()

    # Look up this product's actual price, instead of guessing
    cursor.execute("SELECT unit_price FROM product WHERE product_id = ?", (product_id,))
    unit_price = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO sales_order (order_number, customer_id, order_date, status)
        VALUES (?, ?, ?, ?)
    """, (order_number, customer_id, order_date.isoformat(), "Open"))

    new_order_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO sales_order_line (sales_order_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?)
    """, (new_order_id, product_id, quantity, unit_price))

print(f"{NUM_SALES_ORDERS} sales orders with lines inserted.")

# --- AR Invoice ---
cursor.execute("DROP TABLE IF EXISTS ar_invoice")

cursor.execute("""
    CREATE TABLE ar_invoice (
        ar_invoice_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number   TEXT NOT NULL UNIQUE,
        customer_id      INTEGER NOT NULL,
        sales_order_id   INTEGER,
        invoice_date     DATE NOT NULL,
        due_date         DATE NOT NULL,
        invoice_amount   NUMERIC NOT NULL,
        amount_paid      NUMERIC DEFAULT 0,
        status           TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Partially Paid', 'Paid', 'Overdue')),
        journal_entry_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
        FOREIGN KEY (sales_order_id) REFERENCES sales_order(sales_order_id),
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entry(journal_entry_id)
    )
""")

print("ar_invoice table created.")

# Invoice roughly 80% of sales orders, leaving the rest as "Open" orders
cursor.execute("SELECT sales_order_id, customer_id, order_date FROM sales_order")
all_orders = cursor.fetchall()

invoice_counter = 0
ar_invoice_ids = []  # keep track of which invoices exist, for the receipt step next

for order_id, customer_id, order_date_str in all_orders:
    if random.random() > 0.8:
        continue  # skip this order — leave it un-invoiced

    invoice_counter += 1
    invoice_number = f"ARINV-2025-{invoice_counter:04d}"

    # Get the order's line amount (quantity x unit_price)
    cursor.execute("""
        SELECT quantity, unit_price FROM sales_order_line WHERE sales_order_id = ?
    """, (order_id,))
    quantity, unit_price = cursor.fetchone()
    amount = round(quantity * unit_price, 2)

    invoice_date = date.fromisoformat(order_date_str)
    due_date = invoice_date + timedelta(days=30)

    cursor.execute("""
        INSERT INTO ar_invoice (invoice_number, customer_id, sales_order_id, invoice_date, due_date, invoice_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (invoice_number, customer_id, order_id, invoice_date.isoformat(), due_date.isoformat(), amount, "Open"))

    new_invoice_id = cursor.lastrowid
    ar_invoice_ids.append((new_invoice_id, customer_id, amount, invoice_date))

    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, (invoice_date.isoformat(), 2025, invoice_date.month, "O2C", f"AR invoice {invoice_number}"))

    new_je_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 2, amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 6, 0, amount))

    cogs_amount = round(amount * 0.5, 2)

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 7, cogs_amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 3, 0, cogs_amount))

    cursor.execute("""
        UPDATE ar_invoice SET journal_entry_id = ? WHERE ar_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print(f"{invoice_counter} AR invoices created out of {len(all_orders)} orders, each with a balanced GL posting.")

# --- Cash Receipt ---
cursor.execute("DROP TABLE IF EXISTS cash_receipt")

cursor.execute("""
    CREATE TABLE cash_receipt (
        cash_receipt_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_number   TEXT NOT NULL UNIQUE,
        customer_id      INTEGER NOT NULL,
        ar_invoice_id    INTEGER NOT NULL,
        receipt_date     DATE NOT NULL,
        amount           NUMERIC NOT NULL,
        payment_method   TEXT,
        journal_entry_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
        FOREIGN KEY (ar_invoice_id) REFERENCES ar_invoice(ar_invoice_id),
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entry(journal_entry_id)
    )
""")
print("cash_receipt table created.")

# Register a receipt for roughly 75% of invoices, leaving the rest open (for AR ageing)
receipt_counter = 0

for invoice_id, customer_id, amount, invoice_date in ar_invoice_ids:
    if random.random() > 0.75:
        continue  # leave this invoice unpaid

    receipt_counter += 1
    receipt_number = f"CR-2025-{receipt_counter:04d}"

    # Payment happens sometime between the invoice date and 45 days later
    days_to_pay = random.randint(1, 45)
    receipt_date = invoice_date + timedelta(days=days_to_pay)

    cursor.execute("""
        INSERT INTO cash_receipt (receipt_number, customer_id, ar_invoice_id, receipt_date, amount, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (receipt_number, customer_id, invoice_id, receipt_date.isoformat(), amount, random.choice(["Bank Transfer", "Direct Debit"])))

    new_receipt_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, (receipt_date.isoformat(), 2025, receipt_date.month, "O2C", f"Cash receipt {receipt_number}"))

    new_je_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 1, amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 2, 0, amount))

    cursor.execute("""
        UPDATE cash_receipt SET journal_entry_id = ? WHERE cash_receipt_id = ?
    """, (new_je_id, new_receipt_id))

    cursor.execute("""
        UPDATE ar_invoice SET amount_paid = ?, status = ? WHERE ar_invoice_id = ?
    """, (amount, "Paid", invoice_id))

print(f"{receipt_counter} cash receipts created out of {len(ar_invoice_ids)} invoices.")
print("O2C cycle scaled up: orders, invoices, and receipts now generated with controlled randomness.")



# --- Vendor ---
cursor.execute("DROP TABLE IF EXISTS vendor")

cursor.execute("""
    CREATE TABLE vendor (
        vendor_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_code         TEXT NOT NULL UNIQUE,
        vendor_name         TEXT NOT NULL,
        country             TEXT,
        payment_terms_days  INTEGER DEFAULT 30,
        ap_account_id       INTEGER,
        is_active           INTEGER DEFAULT 1,
        FOREIGN KEY (ap_account_id) REFERENCES chart_of_accounts(account_id)
    )
""")
print("vendor table created.")

vendor_prefixes = ["Staal & Zonen", "EuroPack", "TechParts", "GreenPower", "OfficeMax", "Industria", "Metaalunie", "Connectix", "Bouwgroep", "Precisie", "DataCore", "CleanPro"]
vendor_types = ["Grondstoffen", "Wholesale", "Diensten BV", "Toeleveranciers", "Services", "Onderhoud BV"]

vendor_names = []
for _ in range(12):
    name = f"{random.choice(vendor_prefixes)} {random.choice(vendor_types)}"
    vendor_names.append(name)


for i, name in enumerate(vendor_names, start=1):
    vendor_code = f"VEND-{i:03d}"
    cursor.execute("""
        INSERT INTO vendor (vendor_code, vendor_name, country, ap_account_id)
        VALUES (?, ?, 'NL', 4)
    """, (vendor_code, name))

print(f"{len(vendor_names)} vendors inserted.")

# --- Purchase Order + Purchase Order Line ---
cursor.execute("DROP TABLE IF EXISTS purchase_order_line")
cursor.execute("DROP TABLE IF EXISTS purchase_order")

cursor.execute("""
    CREATE TABLE purchase_order (
        purchase_order_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number          TEXT NOT NULL UNIQUE,
        vendor_id          INTEGER NOT NULL,
        order_date         DATE NOT NULL,
        status             TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Received', 'Invoiced', 'Cancelled')),
        FOREIGN KEY (vendor_id) REFERENCES vendor(vendor_id)
    )
""")

cursor.execute("""
    CREATE TABLE purchase_order_line (
        line_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_order_id  INTEGER NOT NULL,
        product_id         INTEGER,
        description        TEXT,
        quantity           NUMERIC NOT NULL,
        unit_cost          NUMERIC NOT NULL,
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_order(purchase_order_id),
        FOREIGN KEY (product_id) REFERENCES product(product_id)
    )
""")
print("purchase_order and purchase_order_line tables created.")

# Create 100 purchase orders, each with 1 line, spread across the year
NUM_PURCHASE_ORDERS = 100

for i in range(1, NUM_PURCHASE_ORDERS + 1):
    po_number = f"PO-2025-{i:04d}"
    vendor_id = random.randint(1, 12)      # 12 vendors now exist
    product_id = random.randint(1, 15)      # 15 products now exist
    quantity = random.randint(5, 30)
    order_date = random_date_2025()

    # Look up this product's actual cost, instead of guessing
    cursor.execute("SELECT unit_cost FROM product WHERE product_id = ?", (product_id,))
    unit_cost = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO purchase_order (po_number, vendor_id, order_date, status)
        VALUES (?, ?, ?, ?)
    """, (po_number, vendor_id, order_date.isoformat(), "Open"))

    new_po_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO purchase_order_line (purchase_order_id, product_id, description, quantity, unit_cost)
        VALUES (?, ?, ?, ?, ?)
    """, (new_po_id, product_id, None, quantity, unit_cost))

print(f"{NUM_PURCHASE_ORDERS} purchase orders with lines inserted.")

# --- AP Invoice ---
cursor.execute("DROP TABLE IF EXISTS ap_invoice")

cursor.execute("""
    CREATE TABLE ap_invoice (
        ap_invoice_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number    TEXT NOT NULL UNIQUE,
        vendor_id         INTEGER NOT NULL,
        purchase_order_id INTEGER,
        invoice_date      DATE NOT NULL,
        due_date          DATE NOT NULL,
        invoice_amount    NUMERIC NOT NULL,
        amount_paid       NUMERIC DEFAULT 0,
        status            TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Partially Paid', 'Paid', 'Overdue')),
        journal_entry_id  INTEGER,
        FOREIGN KEY (vendor_id) REFERENCES vendor(vendor_id),
        FOREIGN KEY (purchase_order_id) REFERENCES purchase_order(purchase_order_id),
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entry(journal_entry_id)
    )
""")
print("ap_invoice table created.")

# Invoice roughly 85% of purchase orders, leaving the rest as "Open"
cursor.execute("SELECT purchase_order_id, vendor_id, order_date FROM purchase_order")
all_pos = cursor.fetchall()

ap_invoice_counter = 0
ap_invoice_ids = []  # keep track of which invoices exist, for the payment step next

for po_id, vendor_id, order_date_str in all_pos:
    if random.random() > 0.85:
        continue  # skip this PO — leave it un-invoiced

    ap_invoice_counter += 1
    invoice_number = f"APINV-2025-{ap_invoice_counter:04d}"

    # Get the PO's line amount (quantity x unit_cost)
    cursor.execute("""
        SELECT quantity, unit_cost FROM purchase_order_line WHERE purchase_order_id = ?
    """, (po_id,))
    quantity, unit_cost = cursor.fetchone()
    amount = round(quantity * unit_cost, 2)

    invoice_date = date.fromisoformat(order_date_str)
    due_date = invoice_date + timedelta(days=30)

    cursor.execute("""
        INSERT INTO ap_invoice (invoice_number, vendor_id, purchase_order_id, invoice_date, due_date, invoice_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (invoice_number, vendor_id, po_id, invoice_date.isoformat(), due_date.isoformat(), amount, "Open"))

    new_invoice_id = cursor.lastrowid
    ap_invoice_ids.append((new_invoice_id, vendor_id, amount, invoice_date))

    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, (invoice_date.isoformat(), 2025, invoice_date.month, "P2P", f"AP invoice {invoice_number}"))

    new_je_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 3, amount, 0))  # account_id 3 = Inventory

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 4, 0, amount))  # account_id 4 = Accounts Payable

    cursor.execute("""
        UPDATE ap_invoice SET journal_entry_id = ? WHERE ap_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print(f"{ap_invoice_counter} AP invoices created out of {len(all_pos)} purchase orders, each with a balanced GL posting.")

# --- Vendor Payment ---
cursor.execute("DROP TABLE IF EXISTS vendor_payment")

cursor.execute("""
    CREATE TABLE vendor_payment (
        vendor_payment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_number     TEXT NOT NULL UNIQUE,
        vendor_id          INTEGER NOT NULL,
        ap_invoice_id      INTEGER NOT NULL,
        payment_date       DATE NOT NULL,
        amount             NUMERIC NOT NULL,
        payment_method     TEXT,
        journal_entry_id   INTEGER,
        FOREIGN KEY (vendor_id) REFERENCES vendor(vendor_id),
        FOREIGN KEY (ap_invoice_id) REFERENCES ap_invoice(ap_invoice_id),
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entry(journal_entry_id)
    )
""")
print("vendor_payment table created.")

# Register a payment for roughly 80% of AP invoices, leaving the rest open (for AP ageing)
payment_counter = 0

for invoice_id, vendor_id, amount, invoice_date in ap_invoice_ids:
    if random.random() > 0.8:
        continue  # leave this invoice unpaid

    payment_counter += 1
    payment_number = f"VP-2025-{payment_counter:04d}"

    # Payment happens sometime between the invoice date and 40 days later
    days_to_pay = random.randint(1, 40)
    payment_date = invoice_date + timedelta(days=days_to_pay)

    cursor.execute("""
        INSERT INTO vendor_payment (payment_number, vendor_id, ap_invoice_id, payment_date, amount, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (payment_number, vendor_id, invoice_id, payment_date.isoformat(), amount, "Bank Transfer"))

    new_payment_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, (payment_date.isoformat(), 2025, payment_date.month, "P2P", f"Vendor payment {payment_number}"))

    new_je_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 4, amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 1, 0, amount))

    cursor.execute("""
        UPDATE vendor_payment SET journal_entry_id = ? WHERE vendor_payment_id = ?
    """, (new_je_id, new_payment_id))

    cursor.execute("""
        UPDATE ap_invoice SET amount_paid = ?, status = ? WHERE ap_invoice_id = ?
    """, (amount, "Paid", invoice_id))

print(f"{payment_counter} vendor payments created out of {len(ap_invoice_ids)} invoices.")
print("P2P cycle scaled up: purchase orders, invoices, and payments now generated with controlled randomness.")




# --- Close Checklist ---
cursor.execute("DROP TABLE IF EXISTS close_checklist")

cursor.execute("""
    CREATE TABLE close_checklist (
        checklist_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        fiscal_year    INTEGER NOT NULL,
        fiscal_period  INTEGER NOT NULL,
        task_name      TEXT NOT NULL,
        task_owner     TEXT,
        status         TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Complete')),
        completed_at   TEXT,
        FOREIGN KEY (fiscal_year, fiscal_period) REFERENCES fiscal_calendar(fiscal_year, fiscal_period)
    )
""")
print("close_checklist table created.")

close_tasks = [
    ("Bank reconciliation", "Controller", "Complete"),
    ("AR sub-ledger review", "AR Lead", "Complete"),
    ("AP sub-ledger review", "AP Lead", "Pending"),
    ("Trial balance review", "Controller", "In Progress"),
]

for task_name, owner, status in close_tasks:
    cursor.execute("""
        INSERT INTO close_checklist (fiscal_year, fiscal_period, task_name, task_owner, status)
        VALUES (?, ?, ?, ?, ?)
    """, (2025, 1, task_name, owner, status))

print(f"{len(close_tasks)} close checklist tasks inserted.")

# --- Budget Line ---
cursor.execute("DROP TABLE IF EXISTS budget_line")

cursor.execute("""
    CREATE TABLE budget_line (
        budget_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        fiscal_year      INTEGER NOT NULL,
        fiscal_period    INTEGER NOT NULL,
        account_id       INTEGER NOT NULL,
        budgeted_amount  NUMERIC NOT NULL,
        notes            TEXT,
        UNIQUE (fiscal_year, fiscal_period, account_id),
        FOREIGN KEY (fiscal_year, fiscal_period) REFERENCES fiscal_calendar(fiscal_year, fiscal_period),
        FOREIGN KEY (account_id) REFERENCES chart_of_accounts(account_id)
    )
""")
print("budget_line table created.")

budgets = [
    (6, 200.00),   # account_id 6 = Sales Revenue
    (7, 400.00),   # account_id 7 = Cost of Goods Sold
]

for account_id, budgeted_amount in budgets:
    cursor.execute("""
        INSERT INTO budget_line (fiscal_year, fiscal_period, account_id, budgeted_amount)
        VALUES (?, ?, ?, ?)
    """, (2025, 1, account_id, budgeted_amount))

print(f"{len(budgets)} budget lines inserted.")

conn.commit()
conn.close()