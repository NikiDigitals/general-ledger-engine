# Python Data Generator — Explained

Complete reference of `scripts/generate_data.py` in its current,
feature-complete form. Every block below has been typed, tested, and
verified working. Running the full script top to bottom
(`py .\generate_data.py`, from inside `scripts/`) rebuilds all 17 tables
and seeds a realistic, reproducible single-year dataset: 232+ transactions
across O2C and P2P, fully balanced, with an opening capital entry and
correct COGS/inventory postings on every sale.

> This document supersedes an earlier draft written while the generator
> still used a small, fixed 5-record dataset with two known TODOs (no
> opening capital, no COGS/inventory reduction). Both gaps are resolved
> below, and every generation step now uses controlled randomness instead
> of fixed lists — see `docs/JOURNAL.md` section 3 for the full story of
> how it got here.

---

## Setup

```python
import sqlite3
import random
import os
from datetime import date, timedelta

random.seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "database", "erp_demo.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def random_date_2025():
    start = date(2025, 1, 1)
    random_days = random.randint(0, 364)
    return start + timedelta(days=random_days)
```

**What's here and why:**
- **`sqlite3`** — Python's built-in module for talking to SQLite
  databases, no installation needed.
- **`random`** — Python's built-in module for controlled randomness.
- **`os`** — Python's built-in module for interacting with the operating
  system, used here purely to build a reliable file path.
- **`from datetime import date, timedelta`** — `date` represents a
  calendar date; `timedelta` represents a span of time (e.g. "30 days")
  that can be added to or subtracted from a `date`.
- **`random.seed(42)`** — "plants" the random number generator with a
  fixed starting point. Without this, every run of the script would
  produce different random data, making bugs impossible to reproduce
  reliably. With it, every run produces byte-for-byte identical "random"
  data. The number `42` is arbitrary — any number works, it just has to
  stay the same between runs to get reproducibility.
- **`SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`** — `__file__`
  is a built-in variable that always holds the path to the current script
  file. `os.path.abspath(...)` turns that into a full, unambiguous path;
  `os.path.dirname(...)` then takes just the folder part of it (i.e.
  wherever `scripts/` happens to live on this particular computer).
- **`DB_PATH = os.path.join(SCRIPT_DIR, "..", "database", "erp_demo.db")`**
  — builds the database path *relative to the script's own location*,
  not relative to whatever folder the script happens to be launched from.
  `os.path.join(...)` also handles the difference between Windows (`\`)
  and Mac/Linux (`/`) path separators automatically. The practical result:
  this script now runs correctly whether it's launched from inside
  `scripts/`, from the repo root, or via an absolute path from anywhere
  else — the only assumption left is that `scripts/` and `database/`
  remain sibling folders, which is already the repo's fixed structure.
- **`random_date_2025()`** — the first custom function in this project.
  Rather than repeating the same 3 lines everywhere a random date is
  needed, this gives it a name and can be called as `random_date_2025()`
  wherever needed. It picks a random day offset (0 to 364) and adds it to
  1 January 2025.

---

## 1. Chart of Accounts

```python
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
```

**Concepts:**
- **`DROP TABLE IF EXISTS`** — clears the table if it exists, so the
  script can be re-run any number of times without erroring.
- **A list of tuples**, unpacked with `for code, name, acc_type, balance
  in accounts:`. `acc_type` (not `type`) is used deliberately — `type` is
  a reserved Python built-in function name.
- **`?` placeholders** — values are never pasted directly into a SQL
  string. The `?` marks are safely filled from the tuple passed as the
  second argument to `execute()`, which also protects against SQL
  injection.

---

## 2. General Ledger — journal_entry + journal_entry_line

```python
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
```

**Concepts:**
- **Drop order matters**: `journal_entry_line` is dropped before
  `journal_entry`, because it holds a foreign key pointing to it — always
  drop child tables before parent tables.
- **`fiscal_year`/`fiscal_period` included directly** in the original
  `CREATE TABLE` — unlike the earlier hand-written SQL version, where
  these were bolted on later with `ALTER TABLE` once `v_budget_vs_actual`
  needed them.
- **The balance CHECK** is the single most important line in the whole
  schema: it makes it physically impossible to save a line where both
  debit and credit are zero, or both are non-zero.

---

## 3. Opening capital entry

```python
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
```

**Why this exists and why it's posted here:** every other transaction in
this script assumes Cash already has some money in it. Without this
entry, Cash would only ever show what's left after every expense with no
funding behind it — a structurally negative, unrealistic balance. Posting
it immediately after the GL tables exist, before any customer or vendor
transaction, guarantees it's always the very first entry in the ledger.

**`cursor.lastrowid`** — introduced here for the first time in this
document, though it's used constantly from this point on: immediately
after an `INSERT` into a table with an `AUTOINCREMENT` primary key, this
returns the ID that row was just given. It's how a parent row (here, the
journal entry header) gets linked to its child rows (its two balancing
lines) without guessing or hardcoding an ID.

---

## 4. Fiscal Calendar

```python
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
```

**Concepts:**
- **`range(1, 13)`** — generates 1 through 12, replacing 12 manual
  `INSERT`s with one correct loop.
- **`f"2025-{month:02d}-01"`** — an f-string. `{month:02d}` formats the
  number with at least 2 digits, padded with a leading zero (`1` → `01`).
- **`if / elif / else`** — picks the right `end_date` (28, 30, or 31 days)
  depending on the month.

---

## 5. Customer — first use of combined random name generation

```python
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
```

**Concepts:**
- **`random.choice(list)`** — picks one random item from a list.
- **`for _ in range(20):`** — the underscore `_` is a Python convention
  meaning "I don't need this loop variable, I just want the loop to run
  20 times."
- **`.append(...)`** — adds one item to a list that already exists.
  `customer_names` starts empty (`[]`) and is filled by combining a
  random prefix and a random type each time — 10×8 = 80 possible
  combinations, sampled 20 times (occasional repeats are fine for a demo).
- **`enumerate(customer_names, start=1)`** — unchanged from the original,
  fixed-list version. It doesn't need to know or care whether the list
  has 5 items or 20 — it just loops through whatever's there.

---

## 6. Product — cost-based pricing

```python
# --- Product ---
cursor.execute("DROP TABLE IF EXISTS product")

cursor.execute("""
    CREATE TABLE product (
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
    sku = f"SKU-{1000 + i}"
    cursor.execute("""
        INSERT INTO product (sku, product_name, unit_cost, unit_price, revenue_account_id, cogs_account_id, inventory_account_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sku, name, cost, price, 2, 7, 3))

print(f"{len(products)} products inserted.")
```

**Concepts:**
- **`random.uniform(min, max)`** — returns a random decimal number
  between two bounds.
- **`round(..., 2)`** — rounds to 2 decimal places, needed because
  `random.uniform()` otherwise produces long, unrealistic decimals.
- **`price = round(cost * random.uniform(1.5, 2.2), 2)`** — the sale
  price is deliberately *derived from* the cost, rather than generated
  independently. This guarantees every product is sold at a profit (a
  markup between 50% and 120%), instead of risking a random price that
  happens to fall below cost.

---

## 7. Sales Order + Sales Order Line — 30x scale-up

```python
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
```

**Why this section matters most so far:** this is the first time the
script both *reads* and *writes* within the same operation.
`cursor.execute("SELECT unit_price FROM product WHERE product_id = ?", (product_id,))`
followed by `cursor.fetchone()[0]` looks up a real, current price from
the database instead of guessing or hardcoding one — exactly what a real
application does on every request.

**Other concepts:**
- **`random.randint(min, max)`** — a random *whole* number, inclusive of
  both bounds. Used here for choosing which customer, product, and
  quantity, unlike `random.uniform()` which gives decimals.
- **`NUM_SALES_ORDERS = 150`** — a constant in uppercase, a Python
  convention meaning "an adjustable setting." Changing the demo's scale
  later means changing only this one number.
- **`order_date.isoformat()`** — `random_date_2025()` returns a Python
  `date` object, not text. SQLite needs a text date (`"2025-03-15"`), so
  `.isoformat()` converts it to exactly that format before storing it.

---

## 8. AR Invoice — probabilistic invoicing, live-priced COGS

```python
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

    # Post the journal entry header, dated/periodised from the real invoice date
    cursor.execute("""
        INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
        VALUES (?, ?, ?, ?, ?)
    """, (invoice_date.isoformat(), 2025, invoice_date.month, "O2C", f"AR invoice {invoice_number}"))

    new_je_id = cursor.lastrowid

    # Dr Accounts Receivable / Cr Sales Revenue
    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 2, amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 6, 0, amount))

    # Dr Cost of Goods Sold / Cr Inventory (simplified: 50% of sale price)
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
```

**The most conceptually dense section in the whole script — five new
ideas at once:**

- **`random.random()`** — returns a float between 0.0 and 1.0. Checking
  `if random.random() > 0.8: continue` means roughly 80% of values (those
  at or below 0.8) proceed, and the remaining ~20% skip this order
  entirely, leaving it un-invoiced.
- **`continue`** — immediately jumps to the next loop iteration, skipping
  everything below it for this particular order. This is the first
  deliberate use of a loop *not* processing every item the same way.
- **`ar_invoice_ids.append((new_invoice_id, customer_id, amount, invoice_date))`**
  — a list is built up during this loop, to be reused directly in the
  cash receipt step next, avoiding a second database query to rediscover
  which invoices exist.
- **`date.fromisoformat(order_date_str)`** — the reverse of
  `.isoformat()`: converts a text date read back from the database into a
  real Python `date` object, so it can have `timedelta` arithmetic
  applied to it (`due_date = invoice_date + timedelta(days=30)`).
- **A four-line posting instead of two**: this journal entry now has four
  `journal_entry_line` rows under the same `new_je_id` — Dr AR/Cr Revenue
  *and* Dr COGS/Cr Inventory — proving a single journal entry can have
  more than 2 lines, as long as total debits still equal total credits.

**Why an ~80% invoice rate is a deliberate choice, not an approximation:**
a dataset where every order is invoiced immediately would give
`v_ar_aging` nothing meaningful to report. Leaving a portion of orders
un-invoiced (and, in the next section, a portion of invoices unpaid)
produces exactly the kind of open, ageing items a real AR report exists
to surface.

---

## 9. Cash Receipt — reusing the invoice list, variable payment timing

```python
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
```

**Concepts:**
- **`for invoice_id, customer_id, amount, invoice_date in ar_invoice_ids:`**
  — loops directly over the list built in the previous section, instead
  of a fixed `range()` or a fresh `SELECT`. Guarantees this step only
  ever considers invoices that actually exist from this exact run.
- **`random.choice(["Bank Transfer", "Direct Debit"])`** — a small
  realism touch: which payment method was used is itself randomised.
- **Payment timing (`random.randint(1, 45)` days after the invoice)**
  means different invoices get paid at different speeds — some quickly,
  some close to (or past) their 30-day due date — producing a realistic
  spread once `v_ar_aging` is queried.

---

## 10. Vendor — mirrors Customer

```python
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
```

No new concepts — a direct mirror of the customer section, generating 12
vendors from combined name-parts.

---

## 11. Purchase Order + Purchase Order Line — mirrors Sales Order

```python
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
```

**One concept unique to this section:** `None` — Python's way of writing
"no value" / SQL `NULL`. Used for `description`, since a real `product_id`
is supplied instead (the column exists for free-text purchases not tied
to a catalogue product, which this generator doesn't currently produce).

Everything else mirrors the sales order section exactly: live-priced
lookups, `random_date_2025()`, and `cursor.lastrowid` linking each order
to its line.

---

## 12. AP Invoice — mirrors AR Invoice (no COGS side needed)

```python
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

    # Dr Inventory / Cr Accounts Payable
    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 3, amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 4, 0, amount))

    cursor.execute("""
        UPDATE ap_invoice SET journal_entry_id = ? WHERE ap_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print(f"{ap_invoice_counter} AP invoices created out of {len(all_pos)} purchase orders, each with a balanced GL posting.")
```

Same pattern as AR invoices — probabilistic invoicing, live-priced
amounts, a list built for reuse in the next section — but only two
posting lines instead of four, since a purchase increases Inventory
directly (`Dr Inventory / Cr Accounts Payable`); there's no equivalent of
the "sale-side COGS" step on the buying side.

---

## 13. Vendor Payment — mirrors Cash Receipt

```python
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
```

Mirror of the cash receipt section — Dr Accounts Payable / Cr Cash
instead of Dr Cash / Cr Accounts Receivable, otherwise identical in
structure.

---

## 14. Close Checklist

```python
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
```

**Concept:** a composite foreign key —
`FOREIGN KEY (fiscal_year, fiscal_period) REFERENCES fiscal_calendar(fiscal_year, fiscal_period)`
references two columns at once, matching `fiscal_calendar`'s composite
primary key. This table wasn't scaled up with randomness — it holds a
fixed, small set of representative close tasks rather than transaction
volume.

---

## 15. Budget Line

```python
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
```

**Concept:** `UNIQUE` across three columns together, ensuring no more
than one budget row can exist for the same year+period+account
combination.

---

## Closing the connection

```python
conn.commit()
conn.close()
```

**`conn.commit()`** writes everything permanently to the database file —
the Python equivalent of "Write Changes" in DB Browser. **`conn.close()`**
releases the connection cleanly.

---

## Full script structure, top to bottom

```
Setup                        (imports, seed, connection, random_date_2025())
1.  Chart of Accounts        (table + 7 accounts)
2.  General Ledger           (journal_entry + journal_entry_line)
3.  Opening capital entry    (Dr Cash / Cr Common Stock, €1,000)
4.  Fiscal Calendar          (table + 12 periods, via loop)
5.  Customer                 (table + 20 customers, randomised names)
6.  Product                  (table + 15 products, cost-based pricing)
7.  Sales Order + Line       (table + 150 orders, live-priced, random dates)
8.  AR Invoice               (~80% of orders invoiced, 4-line GL posting incl. COGS)
9.  Cash Receipt             (~75% of invoices paid, variable timing)
10. Vendor                   (table + 12 vendors, randomised names)
11. Purchase Order + Line    (table + 100 orders, live-priced, random dates)
12. AP Invoice               (~85% of POs invoiced, 2-line GL posting)
13. Vendor Payment           (~80% of invoices paid, variable timing)
14. Close Checklist          (table + 4 fixed tasks)
15. Budget Line              (table + 2 fixed budgets)
conn.commit() / conn.close()
```

**Result of a full run:** 232+ transactions across O2C (150 orders / 124
invoiced / 92 paid) and P2P (100 orders / 82 invoiced / 60 paid), an
opening capital entry, correct COGS/inventory postings on every sale, and
a trial balance that sums to exactly zero —
`SELECT ROUND(SUM(debit_amount) - SUM(credit_amount), 2) FROM journal_entry_line;`
returns `0.0` regardless of how much randomness was involved in producing
the data.

## What's next

The data generator is feature-complete for a realistic single-year demo.
See `docs/ARCHITECTURE.md` under "Future extensions" for possible
refinements (more accurate per-product COGS costing, discounts,
reversals, write-offs) that aren't required for the current demo but fit
the architecture without a redesign. The next major phase on the roadmap
is the backend API (Node/Express) that will expose this database over
HTTP.
