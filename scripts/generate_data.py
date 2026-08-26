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

# Create 3 orders, each with 1-2 lines

cursor.execute("""
    INSERT INTO sales_order(order_number, customer_id, order_date, status)
    VALUES (?, ?, ?, ?)
""", ("SO-2025-0001", 1, "2025-01-20", "Open"))  

new_order_id = cursor.lastrowid  # the sales_order_id that was just assigned


cursor.execute("""
    INSERT INTO sales_order_line (sales_order_id, product_id, quantity, unit_price)
    VALUES (?, ?, ?, ?)
   """, (new_order_id, 1, 3, 9.99)) 

print("1 sales order with 1 line inserted")

conn.commit()
conn.close()

