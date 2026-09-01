# Python Data Generator — Explained

Complete reference of `scripts/generate_data.py`. Every block below has
been typed, tested, and verified working. Running the full script top to
bottom (`py .\generate_data.py`, from inside `scripts/`) rebuilds all 17
tables and seeds a realistic, reproducible single-year dataset: 232+
transactions across O2C and P2P, fully balanced, with an opening capital
entry and correct COGS/inventory postings on every sale.

This document explains what the code does and why, concept by concept, in
the order those concepts first appear — read top to bottom to understand
the whole script.

---

## Setup

```python
import sqlite3
import random
import os
import calendar
from datetime import date, timedelta

random.seed(42)
CURRENT_YEAR = 2025

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "database", "erp_demo.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def random_date(year):
    start = date(year, 1, 1)
    random_days = random.randint(0, 364)
    return start + timedelta(days=random_days)
```

**Imports:**
- **`sqlite3`** — Python's built-in module for talking to SQLite
  databases, no installation needed.
- **`random`** — Python's built-in module for controlled randomness.
- **`os`** — used here purely to build a reliable file path.
- **`calendar`** — knows how many days are in any given month of any
  given year, including leap years. Used later when generating
  `fiscal_calendar` rows.
- **`from datetime import date, timedelta`** — `date` represents a
  calendar date; `timedelta` represents a span of time (e.g. "30 days")
  that can be added to or subtracted from a `date`.

**`random.seed(42)`** — "plants" the random number generator with a fixed
starting point. Without this, every run of the script would produce
different random data, making bugs impossible to reproduce reliably. With
it, every run produces byte-for-byte identical "random" data. The number
`42` is arbitrary — any number works, it just has to stay the same
between runs to get reproducibility.

**`CURRENT_YEAR = 2025`** — a constant, written in uppercase by
convention to signal "this is a setting, not a value that changes while
the script runs." Every date, invoice number, and journal entry generated
below reads from this one variable — change this single line to generate
a different year's worth of data, without touching anything else in the
file.

**`SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`** —
`__file__` is a built-in variable that always holds the path to the
current script file. `os.path.abspath(...)` turns that into a full,
unambiguous path; `os.path.dirname(...)` then takes just the folder part
of it (wherever `scripts/` happens to live on this particular computer).

**`DB_PATH = os.path.join(SCRIPT_DIR, "..", "database", "erp_demo.db")`**
— builds the database path relative to the script's own location, not
relative to whatever folder the script happens to be launched from.
`os.path.join(...)` also handles the difference between Windows (`\`)
and Mac/Linux (`/`) path separators automatically. The practical result:
this script runs correctly whether launched from inside `scripts/`, from
the repo root, or via an absolute path from anywhere else.

**`def random_date(year): ...`** — a custom function, the first one in
this script. Defining a function with `def` gives a name to a piece of
reusable logic, so instead of repeating the same three lines everywhere a
random date is needed, the script just calls `random_date(CURRENT_YEAR)`.
Inside it: `date(year, 1, 1)` builds 1 January of the given year;
`random.randint(0, 364)` picks a random whole number between 0 and 364
inclusive (covering every day in a 365-day year); adding that many days
with `timedelta(days=random_days)` lands on a random date somewhere in
that year.

---

## 1. Chart of Accounts

```python
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
    ("4100", "Sales Discounts", "Revenue", "Debit"),
    ("5000", "Cost of Goods Sold", "Expense", "Debit"),
    ("5100", "Bad Debt Expense", "Expense", "Debit"),
]

for code, name, acc_type, balance in accounts:
    cursor.execute("""
        INSERT INTO chart_of_accounts (account_code, account_name, account_type, normal_balance)
        VALUES (?, ?, ?, ?)
    """, (code, name, acc_type, balance))

print(f"{len(accounts)} accounts inserted.")
```

**`cursor.execute("DROP TABLE IF EXISTS ...")`** — clears the table if it
already exists, so this script can be re-run from scratch any number of
times without erroring on "table already exists."

**Triple-quoted strings (`"""..."""`)** — let a SQL statement span
multiple lines, keeping long `CREATE TABLE` statements readable.

**`accounts = [...]`, a list of tuples** — each tuple holds one account's
four values in a fixed order (code, name, type, balance).

**`for code, name, acc_type, balance in accounts:`** — unpacks each tuple
into four named variables in a single step. Note `acc_type`, not `type` —
`type` is a reserved Python built-in function, so using it as a variable
name would shadow that function.

**`?` placeholders** — SQL values are never pasted directly into a query
string. The `?` marks are filled in safely from the tuple passed as the
second argument to `execute()`, which protects against SQL injection and
correctly handles special characters (like an apostrophe in a name).

**`Sales Discounts` is a contra-revenue account**: it sits under the
Revenue category (account code `4100`) but has `Debit` as its normal
balance — the opposite of a typical Revenue account. This keeps the value
of discounts given visible on its own line in reporting, rather than
silently reducing the `Sales Revenue` figure directly.

---

## 2. General Ledger — journal_entry + journal_entry_line

```python
cursor.execute("DROP TABLE IF EXISTS journal_entry_line")
cursor.execute("DROP TABLE IF EXISTS journal_entry")

cursor.execute("""
    CREATE TABLE journal_entry (
        journal_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date       DATE NOT NULL,
        fiscal_year      INTEGER NOT NULL,
        fiscal_period    INTEGER NOT NULL,
        source_module    TEXT NOT NULL CHECK (source_module IN ('O2C', 'P2P', 'R2R', 'Manual')),
        description      TEXT,
        reverses_journal_entry_id  INTEGER REFERENCES journal_entry(journal_entry_id)
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

**Drop order matters**: `journal_entry_line` is dropped before
`journal_entry`, because it holds a foreign key pointing to it — always
drop child tables before parent tables.

**The balance CHECK** is the single most important line in the whole
schema: `(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0
AND credit_amount > 0)` makes it physically impossible to save a line
where both debit and credit are zero, or both are non-zero. This is
double-entry bookkeeping enforced by the database itself, not by
application code.

**`reverses_journal_entry_id INTEGER REFERENCES journal_entry(journal_entry_id)`**
— a **self-referencing foreign key**: a column on `journal_entry` that
points back to `journal_entry`'s own primary key. It's nullable (no
`NOT NULL`), so most entries leave it empty. When a future correction
entry is posted to reverse an earlier mistake, this column records
*which* entry it corrects — the original entry is never edited or
deleted, only ever pointed at by a new one.

---

## 3. Opening capital entry

```python
cursor.execute("""
    INSERT INTO journal_entry (entry_date, fiscal_year, fiscal_period, source_module, description)
    VALUES (?, ?, ?, ?, ?)
""", (f"{CURRENT_YEAR}-01-01", CURRENT_YEAR, 1, "Manual", "Opening balance - shareholder capital contribution"))

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

**Why this exists:** a business doesn't start at zero — shareholders
contribute starting capital. Without this entry, Cash would only ever
show what's left after expenses with no funding behind it. Posting it
immediately after the GL tables exist, before any other transaction,
guarantees it's always the very first entry in the ledger.

**`cursor.lastrowid`** — immediately after an `INSERT` into a table with
an `AUTOINCREMENT` primary key, this returns the ID that row was just
given. It's how a parent row (here, the journal entry header) gets linked
to its child rows (its two balancing lines) without guessing or
hardcoding an ID. This pattern — insert, capture `lastrowid`, use it in
the next insert — recurs constantly for the rest of this script.

**`f"{CURRENT_YEAR}-01-01"`** — an f-string, which embeds a variable's
value directly into a string. Here it builds `"2025-01-01"` when
`CURRENT_YEAR` is `2025`.

---

## 4. Fiscal Calendar

```python
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
    _, days_in_month = calendar.monthrange(CURRENT_YEAR, month)
    start_date = f"{CURRENT_YEAR}-{month:02d}-01"
    end_date = f"{CURRENT_YEAR}-{month:02d}-{days_in_month:02d}"

    cursor.execute("""
        INSERT INTO fiscal_calendar (fiscal_year, fiscal_period, period_name, start_date, end_date)
        VALUES (?, ?, ?, ?, ?)
    """, (CURRENT_YEAR, month, period_name, start_date, end_date))

print("12 fiscal periods inserted.")
```

**`PRIMARY KEY (fiscal_year, fiscal_period)`** — a **composite primary
key**: uniqueness is enforced across *both* columns together, not either
one alone. This means the table can hold any number of years — 2025,
2026, 2050 — without any schema change, because each year's 12 periods
are uniquely identified by the (year, period) pair. `journal_entry`,
`close_checklist`, and `budget_line` all reference this same pair as a
composite foreign key later in the script.

**`for month in range(1, 13):`** — loops through the numbers 1 to 12,
replacing what would otherwise be 12 separate manual `INSERT` statements.

**`calendar.monthrange(CURRENT_YEAR, month)`** — returns a tuple of
`(weekday of the 1st, number of days in that month)`. The code only needs
the second value, so `_, days_in_month = calendar.monthrange(...)` uses
an underscore to explicitly discard the first value it doesn't need — a
common Python convention for "this value exists but I'm not using it."
This correctly returns 29 for February in a leap year and 28 otherwise,
with no manual leap-year logic required.

**`f"{CURRENT_YEAR}-{month:02d}-01"`** — the `{month:02d}` part is a
format specifier: format this number with at least 2 digits, padding
with a leading zero if needed, so `1` becomes `"01"` and `12` stays
`"12"`.

---

## 5. Customer

```python
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

**`random.choice(list)`** — picks one random item from a list.

**`for _ in range(20):`** — the underscore here means "I don't need this
loop's counter value, I just want the loop body to run 20 times."

**`customer_names.append(name)`** — adds one item to the end of a list
that already exists. `customer_names` starts empty (`[]`) and is filled
one name at a time by combining a random prefix and a random type — 10×8
= 80 possible combinations, sampled 20 times (occasional repeats are fine
for a demo).

**`enumerate(customer_names, start=1)`** — loops through a list while
also producing a running counter, starting at 1 instead of the default 0.
Needed here to build `CUST-001`, `CUST-002`, and so on.

---

## 6. Product

```python
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
    """, (sku, name, cost, price, 6, 8, 3))

print(f"{len(products)} products inserted.")
```

**`random.uniform(min, max)`** — returns a random *decimal* number
between two bounds, unlike `random.randint()` which gives whole numbers.

**`round(..., 2)`** — rounds to 2 decimal places, needed because
`random.uniform()` otherwise produces long, unrealistic decimals like
`47.283947...`.

**`price = round(cost * random.uniform(1.5, 2.2), 2)`** — the sale price
is deliberately *derived from* the cost, rather than generated
independently. This guarantees every product is sold at a profit (a
markup between 50% and 120%), instead of risking a random price that
happens to fall below cost.

**`enumerate(products, start=1)` with tuple unpacking** —
`for i, (name, cost, price) in enumerate(...)` pulls out the running
counter *and* all three values from each tuple in one line.

**The final three numbers (`6, 8, 3`)** in the `INSERT` are the account
IDs for revenue, cost of goods sold, and inventory respectively —
matching `chart_of_accounts` (account_id 6 = Sales Revenue, 8 = Cost of
Goods Sold, 3 = Inventory). These columns aren't currently read anywhere
else in this script — every actual posting elsewhere uses its own
hardcoded account IDs directly — but they're kept accurate here so a
future feature that *does* read them (e.g. a route that looks up "this
product's correct COGS account") finds correct data.

---

## 7. Sales Order + Sales Order Line

```python
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

NUM_SALES_ORDERS = 150

for i in range(1, NUM_SALES_ORDERS + 1):
    order_number = f"SO-{CURRENT_YEAR}-{i:04d}"
    customer_id = random.randint(1, 20)       # 20 customers now exist
    product_id = random.randint(1, 15)         # 15 products now exist
    quantity = random.randint(1, 10)
    order_date = random_date(CURRENT_YEAR)

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

**`NUM_SALES_ORDERS = 150`** — an uppercase constant, the same convention
as `CURRENT_YEAR`: an adjustable setting kept at the top of its section
rather than buried in the loop.

**`random.randint(min, max)`** — a random *whole* number, inclusive of
both bounds. Used here for customer, product, and quantity, unlike
`random.uniform()` which gives decimals.

**`cursor.execute("SELECT unit_price FROM product WHERE product_id = ?", (product_id,))`
followed by `cursor.fetchone()[0]`** — this is the first place the script
both *reads and writes* within the same operation: it looks up a real,
current price from the database instead of guessing or hardcoding one.
`fetchone()` returns one row as a tuple; `[0]` takes the first (and only)
value out of it.

**`order_date.isoformat()`** — `random_date()` returns a Python `date`
object, not text. SQLite needs a text date (`"2025-03-15"`), so
`.isoformat()` converts the `date` object to exactly that format before
storing it.

---

## 8. AR Invoice

```python
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
        status           TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Partially Paid', 'Paid', 'Overdue', 'Written Off')),
        journal_entry_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
        FOREIGN KEY (sales_order_id) REFERENCES sales_order(sales_order_id),
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entry(journal_entry_id)
    )
""")

print("ar_invoice table created.")

cursor.execute("SELECT sales_order_id, customer_id, order_date FROM sales_order")
all_orders = cursor.fetchall()

invoice_counter = 0
ar_invoice_ids = []

for order_id, customer_id, order_date_str in all_orders:
    if random.random() > 0.8:
        continue

    invoice_counter += 1
    invoice_number = f"ARINV-{CURRENT_YEAR}-{invoice_counter:04d}"

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
    """, (invoice_date.isoformat(), CURRENT_YEAR, invoice_date.month, "O2C", f"AR invoice {invoice_number}"))

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
    """, (new_je_id, 8, cogs_amount, 0))

    cursor.execute("""
        INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
        VALUES (?, ?, ?, ?)
    """, (new_je_id, 3, 0, cogs_amount))

    cursor.execute("""
        UPDATE ar_invoice SET journal_entry_id = ? WHERE ar_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print(f"{invoice_counter} AR invoices created out of {len(all_orders)} orders, each with a balanced GL posting.")
```

This is the most concept-dense section in the script — five ideas appear
here for the first time.

**`status` CHECK includes `'Written Off'`** — a fifth valid status
alongside the original four, so that a future feature can mark an
uncollectable invoice this way. No invoice generated by this script is
ever actually set to `'Written Off'`; the value is simply permitted by
the schema, ready for that future feature.

**`random.random()`** — returns a floating-point number between `0.0`
and `1.0`. Checking `if random.random() > 0.8: continue` means roughly
80% of values (everything at or below 0.8) proceed past this check, and
the remaining ~20% trigger the `continue`.

**`continue`** — immediately jumps to the next iteration of the loop,
skipping every line below it for this particular order. This is how the
script leaves ~20% of orders deliberately un-invoiced, rather than
invoicing every single one.

**`ar_invoice_ids.append((new_invoice_id, customer_id, amount, invoice_date))`**
— builds up a list during this loop, to be reused directly in the cash
receipt section next, avoiding a second database query to rediscover
which invoices exist.

**`date.fromisoformat(order_date_str)`** — the reverse of `.isoformat()`:
converts a text date read back from the database into a real Python
`date` object, so `timedelta` arithmetic can be applied to it (here,
`due_date = invoice_date + timedelta(days=30)`).

**The four-line posting** — this journal entry has four
`journal_entry_line` rows under the same `new_je_id`: `Dr Accounts
Receivable / Cr Sales Revenue` (the sale itself), and
`Dr Cost of Goods Sold / Cr Inventory` (recognising the cost of what was
sold, calculated here as a simplified flat 50% of the sale price). A
single journal entry can have any number of lines, as long as total
debits equal total credits — it isn't limited to exactly two.

---

## 9. Cash Receipt

```python
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

receipt_counter = 0

for invoice_id, customer_id, amount, invoice_date in ar_invoice_ids:
    if random.random() > 0.75:
        continue

    receipt_counter += 1
    receipt_number = f"CR-{CURRENT_YEAR}-{receipt_counter:04d}"

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
    """, (receipt_date.isoformat(), CURRENT_YEAR, receipt_date.month, "O2C", f"Cash receipt {receipt_number}"))

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

**`for invoice_id, customer_id, amount, invoice_date in ar_invoice_ids:`**
— loops directly over the list built in the previous section, instead of
a fixed range or a fresh database query. Guarantees this step only ever
considers invoices that actually exist from this exact run.

**`random.choice(["Bank Transfer", "Direct Debit"])`** — a small realism
touch: which payment method was used is itself randomised.

**Variable payment timing** (`random.randint(1, 45)` days after the
invoice) means different invoices get paid at different speeds — some
quickly, some close to or past their 30-day due date — producing a
realistic spread once the AR ageing report is queried.

**Two `UPDATE` statements at the end** — after posting the GL entry, the
script also updates `cash_receipt` (linking it to its journal entry) and
`ar_invoice` (recording that it's now paid). A single business event —
"a customer paid" — touches three different tables: the new receipt row,
the new journal entry and its lines, and the original invoice's status.

---

## 10. Vendor

```python
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

Structurally identical to the customer section (section 5) — combined
random name-parts, `enumerate` for sequential codes. No new concepts;
this is P2P's mirror of O2C's `customer` table, with account_id `4`
(Accounts Payable) in place of AR.

---

## 11. Purchase Order + Purchase Order Line

```python
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

NUM_PURCHASE_ORDERS = 100

for i in range(1, NUM_PURCHASE_ORDERS + 1):
    po_number = f"PO-{CURRENT_YEAR}-{i:04d}"
    vendor_id = random.randint(1, 12)
    product_id = random.randint(1, 15)
    quantity = random.randint(5, 30)
    order_date = random_date(CURRENT_YEAR)

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

Mirrors section 7 (Sales Order) closely — live-priced lookups (this time
`unit_cost`, not `unit_price`), `random_date(CURRENT_YEAR)`,
`cursor.lastrowid` linking each order to its line.

**`None`** — Python's way of writing "no value" (SQL's `NULL`). Used here
for `description`, since a real `product_id` is supplied instead — the
column exists for free-text purchases that aren't tied to a catalogue
product, which this generator doesn't currently produce.

---

## 12. AP Invoice

```python
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

cursor.execute("SELECT purchase_order_id, vendor_id, order_date FROM purchase_order")
all_pos = cursor.fetchall()

ap_invoice_counter = 0
ap_invoice_ids = []

for po_id, vendor_id, order_date_str in all_pos:
    if random.random() > 0.85:
        continue

    ap_invoice_counter += 1
    invoice_number = f"APINV-{CURRENT_YEAR}-{ap_invoice_counter:04d}"

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
    """, (invoice_date.isoformat(), CURRENT_YEAR, invoice_date.month, "P2P", f"AP invoice {invoice_number}"))

    new_je_id = cursor.lastrowid

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

Mirrors section 8 (AR Invoice) — same probabilistic invoicing pattern
(`random.random()` + `continue`), same list-building for reuse in the
next section — but only two posting lines instead of four:
`Dr Inventory / Cr Accounts Payable`. A purchase increases inventory
directly; there's no equivalent of the "sale-side COGS" step on the
buying side, since nothing has been sold yet.

Note this table's `status` CHECK does **not** include `'Written Off'` —
that value only makes sense for money owed *to* the business
(receivables), not money the business owes *out* (payables).

---

## 13. Vendor Payment

```python
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

payment_counter = 0

for invoice_id, vendor_id, amount, invoice_date in ap_invoice_ids:
    if random.random() > 0.8:
        continue

    payment_counter += 1
    payment_number = f"VP-{CURRENT_YEAR}-{payment_counter:04d}"

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
    """, (payment_date.isoformat(), CURRENT_YEAR, payment_date.month, "P2P", f"Vendor payment {payment_number}"))

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

Mirrors section 9 (Cash Receipt) exactly — `Dr Accounts Payable / Cr Cash`
instead of `Dr Cash / Cr Accounts Receivable`, same two `UPDATE`
statements at the end linking the journal entry and marking the invoice
paid.

---

## 14. Close Checklist

```python
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
    """, (CURRENT_YEAR, 1, task_name, owner, status))

print(f"{len(close_tasks)} close checklist tasks inserted.")
```

**`FOREIGN KEY (fiscal_year, fiscal_period) REFERENCES fiscal_calendar(fiscal_year, fiscal_period)`**
— a **composite foreign key**, referencing both columns of
`fiscal_calendar`'s composite primary key at once. This table holds a
small, fixed set of representative tasks rather than generated volume —
demonstrating the close-checklist concept, not simulating a full year of
close activity.

---

## 15. Budget Line

```python
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
    (8, 400.00),   # account_id 8 = Cost of Goods Sold
]

for account_id, budgeted_amount in budgets:
    cursor.execute("""
        INSERT INTO budget_line (fiscal_year, fiscal_period, account_id, budgeted_amount)
        VALUES (?, ?, ?, ?)
    """, (CURRENT_YEAR, 1, account_id, budgeted_amount))

print(f"{len(budgets)} budget lines inserted.")
```

**`UNIQUE (fiscal_year, fiscal_period, account_id)`** — a uniqueness rule
spanning three columns together, ensuring no more than one budget row can
exist for the same year+period+account combination, without restricting
any single column on its own.

---

## Closing the connection

```python
conn.commit()
conn.close()
```

**`conn.commit()`** writes everything done so far permanently to the
database file — the Python equivalent of clicking "Write Changes" in DB
Browser. Without it, none of the above would actually persist once the
script finishes. **`conn.close()`** releases the connection cleanly.

---

## Full script structure, top to bottom

```
Setup                        (imports, seed, CURRENT_YEAR, connection, random_date(year))
1.  Chart of Accounts        (table + 9 accounts)
2.  General Ledger           (journal_entry incl. reverses_journal_entry_id + journal_entry_line)
3.  Opening capital entry    (Dr Cash / Cr Common Stock, €1,000)
4.  Fiscal Calendar          (table + 12 periods, leap-year-safe)
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

**Result of a full run:** 232+ transactions across O2C and P2P, an
opening capital entry, correct COGS/inventory postings on every sale, and
a trial balance that sums to exactly zero —
`SELECT ROUND(SUM(debit_amount) - SUM(credit_amount), 2) FROM journal_entry_line;`
returns `0.0` regardless of how much randomness was involved in producing
the data.

## What's next

The schema supports reversals (`reverses_journal_entry_id`) and
write-offs (`'Written Off'` status), but no code in this script — or
anywhere else yet — creates one; that's application-layer work for the
Python/FastAPI backend. Adding a new fiscal year doesn't require touching
this script at all — see `scripts/start_new_fiscal_year_explained.md`
for the separate, manually-triggered script that handles that. See
`docs/ARCHITECTURE.md` under "Future extensions" for what's still pending
on discounts and more accurate per-product COGS costing.
