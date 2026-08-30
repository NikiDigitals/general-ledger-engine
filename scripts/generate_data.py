import sqlite3

DB_PATH = "../database/erp_demo.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

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

customer_names = [
    "Noordzee Logistics BV",
    "Delta Retail Group",
    "Amstel Bouwmaterialen",
    "Rijnland Foods NV",
    "Veldkamp Technics"
]

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

products = [
    ("Top", 5.00 , 9.99), 
    ("T-shirt", 10.00 , 14.99),
    ("Hoodie", 15.00, 24.99),
    ("Cardigan", 17.50, 29.99),
    ("Pullover" , 17.50, 29.99) 
]

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


# Create 5 sales orders, each with 1 line
customer_ids = [1, 2, 3, 4, 5]
product_prices = {1: 9.99, 2: 14.99, 3: 24.99, 4: 29.99, 5: 29.99}  # product_id: unit_price

for i in range(1, 6):
    order_number = f"SO-2025-{i:04d}"
    customer_id = customer_ids[i - 1]
    product_id = i  # simple mapping for now: order 1 -> product 1, etc.

    cursor.execute("""
        INSERT INTO sales_order (order_number, customer_id, order_date, status)
        VALUES (?, ?, ?, ?)
    """, (order_number, customer_id, "2025-01-20", "Open"))

    new_order_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO sales_order_line (sales_order_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?)
    """, (new_order_id, product_id, 2, product_prices[product_id]))

print("5 sales orders with lines inserted.")

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

# Turn each sales order into an invoice
sales_order_ids = [1, 2, 3, 4, 5]
customer_ids = [1, 2, 3, 4, 5]
invoice_amounts = [19.98, 29.98, 49.98, 59.98, 59.98]  # quantity 2 x unit_price, per order

for i in range(1, 6):
    invoice_number = f"ARINV-2025-{i:04d}"
    amount = invoice_amounts[i - 1]
     # Step 1: create the invoice row (no journal_entry_id yet)
    cursor.execute("""
        INSERT INTO ar_invoice (invoice_number, customer_id, sales_order_id, invoice_date, due_date, invoice_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (invoice_number, customer_ids[i - 1], sales_order_ids[i - 1], "2025-01-20", "2025-02-19", amount, "Open"))

    new_invoice_id = cursor.lastrowid

    # Step 2: create the journal entry header
    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, ("2025-01-20", 2025, 1, "O2C", f"AR invoice {invoice_number}"))

    new_je_id = cursor.lastrowid

    # Step 3: create the two balanced lines (Dr Accounts Receivable / Cr Sales Revenue)
    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 2, amount, 0))  # account_id 2 = Accounts Receivable

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 6, 0, amount))  # account_id 6 = Sales Revenue

    # Step 3b: create the matching COGS entry (Dr COGS / Cr Inventory)
    cogs_amount = amount * 0.5  # simple assumption: cost is 50% of sale price

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 7, cogs_amount, 0))  # account_id 7 = Cost of Goods Sold

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 3, 0, cogs_amount))  # account_id 3 = Inventory

    # Step 4: link the invoice back to its journal entry
    cursor.execute("""
        UPDATE ar_invoice SET journal_entry_id = ? WHERE ar_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print("5 AR invoices created, each with a balanced GL posting.")

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

# Register a cash receipt for each invoice, generating the matching GL posting
for i in range(1, 6):
    receipt_number = f"CR-2025-{i:04d}"
    customer_id = i
    ar_invoice_id = i
    amount = invoice_amounts[i - 1]

    print(f"--- Processing receipt {i} ---")

    # Step 1: create the cash_receipt row (no journal_entry_id yet)
    cursor.execute("""
        INSERT INTO cash_receipt (receipt_number, customer_id, ar_invoice_id, receipt_date, amount, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (receipt_number, customer_id, ar_invoice_id, "2025-02-10", amount, "Bank Transfer"))

    new_receipt_id = cursor.lastrowid
    print(f"Created cash receipt with id {new_receipt_id}")

    # Step 2: create the journal entry header for this receipt
    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, ("2025-02-10", 2025, 2, "O2C", f"Cash receipt {receipt_number}"))

    new_je_id = cursor.lastrowid
    print(f"Created journal entry with id {new_je_id}")

    # Step 3: create the two balanced lines (Dr Cash / Cr Accounts Receivable)
    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 1, amount, 0))  # account_id 1 = Cash

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 2, 0, amount))  # account_id 2 = Accounts Receivable

    print("Journal entry lines created.")

    # Step 4: link the receipt back to its journal entry
    cursor.execute("""
        UPDATE cash_receipt SET journal_entry_id = ? WHERE cash_receipt_id = ?
    """, (new_je_id, new_receipt_id))

    # Step 5: mark the invoice as paid now that the receipt is posted
    cursor.execute("""
        UPDATE ar_invoice SET amount_paid = ?, status = ? WHERE ar_invoice_id = ?
    """, (amount, "Paid", ar_invoice_id))

    print(f"Receipt {i} linked and invoice {ar_invoice_id} marked as paid.")

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

vendor_names = [
    "Staal & Zonen Grondstoffen",
    "EuroPack Verpakkingsmaterialen",
    "TechParts Wholesale",
    "GreenPower Energie BV",
    "OfficeMax Kantoorartikelen"
]

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

# Create 5 purchase orders, each with 1 line (buying stock from a vendor)
vendor_ids = [1, 2, 3, 4, 5]
purchase_costs = [5.00, 10.00, 15.00, 17.50, 17.50]  # matches unit_cost per product

for i in range(1, 6):
    po_number = f"PO-2025-{i:04d}"
    vendor_id = vendor_ids[i - 1]
    product_id = i
    cost = purchase_costs[i - 1]

    cursor.execute("""
        INSERT INTO purchase_order (po_number, vendor_id, order_date, status)
        VALUES (?, ?, ?, ?)
    """, (po_number, vendor_id, "2025-01-10", "Open"))

    new_po_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO purchase_order_line (purchase_order_id, product_id, description, quantity, unit_cost)
        VALUES (?, ?, ?, ?, ?)
    """, (new_po_id, product_id, None, 10, cost))

print("5 purchase orders with lines inserted.")

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

purchase_order_ids = [1, 2, 3, 4, 5]
ap_invoice_amounts = [50.00, 100.00, 150.00, 175.00, 175.00]  # 10 units x unit_cost, per PO

for i in range(1, 6):
    invoice_number = f"APINV-2025-{i:04d}"
    amount = ap_invoice_amounts[i - 1]

    # Step 1: create the invoice row (no journal_entry_id yet)
    cursor.execute("""
        INSERT INTO ap_invoice (invoice_number, vendor_id, purchase_order_id, invoice_date, due_date, invoice_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (invoice_number, vendor_ids[i - 1], purchase_order_ids[i - 1], "2025-01-16", "2025-02-15", amount, "Open"))

    new_invoice_id = cursor.lastrowid

    # Step 2: create the journal entry header
    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, ("2025-01-16", 2025, 1, "P2P", f"AP invoice {invoice_number}"))

    new_je_id = cursor.lastrowid

    # Step 3: create the two balanced lines (Dr Inventory / Cr Accounts Payable)
    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 3, amount, 0))  # account_id 3 = Inventory

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 4, 0, amount))  # account_id 4 = Accounts Payable

    # Step 4: link the invoice back to its journal entry
    cursor.execute("""
        UPDATE ap_invoice SET journal_entry_id = ? WHERE ap_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print("5 AP invoices created, each with a balanced GL posting.")

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

# Register a vendor payment for each AP invoice
for i in range(1, 6):
    payment_number = f"VP-2025-{i:04d}"
    vendor_id = i
    ap_invoice_id = i
    amount = ap_invoice_amounts[i - 1]

    # Step 1: create the vendor_payment row (no journal_entry_id yet)
    cursor.execute("""
        INSERT INTO vendor_payment (payment_number, vendor_id, ap_invoice_id, payment_date, amount, payment_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (payment_number, vendor_id, ap_invoice_id, "2025-02-05", amount, "Bank Transfer"))

    new_payment_id = cursor.lastrowid

    # Step 2: create the journal entry header
    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, ("2025-02-05", 2025, 2, "P2P", f"Vendor payment {payment_number}"))

    new_je_id = cursor.lastrowid

    # Step 3: create the two balanced lines (Dr Accounts Payable / Cr Cash)
    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 4, amount, 0))  # account_id 4 = Accounts Payable

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 1, 0, amount))  # account_id 1 = Cash

    # Step 4: link the payment back to its journal entry
    cursor.execute("""
        UPDATE vendor_payment SET journal_entry_id = ? WHERE vendor_payment_id = ?
    """, (new_je_id, new_payment_id))

    # Step 5: mark the invoice as paid now that the payment is posted
    cursor.execute("""
        UPDATE ap_invoice SET amount_paid = ?, status = ? WHERE ap_invoice_id = ?
    """, (amount, "Paid", ap_invoice_id))

print("5 vendor payments created, each linked and invoice marked as paid.")

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