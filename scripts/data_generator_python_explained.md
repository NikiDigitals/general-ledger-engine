# Python Data Generator

Complete reference of `scripts/generate_data.py`, built up table by table.
Every block below has been typed, tested, and verified working. Running
the full script top to bottom (`py .\generate_data.py`, from inside
`scripts/`) rebuilds all 17 tables and seeds a small, fixed test dataset
covering the full O2C and P2P cycles.

> **Known, deliberately deferred gaps** (see `docs/ARCHITECTURE.md` and
> `docs/LESSONS_LEARNED.md`): no `Dr COGS / Cr Inventory` posting on the
> sale side, and no opening capital entry. Every individual posting below
> is still perfectly balanced — these gaps affect the aggregate picture
> across accounts, not any single transaction's correctness.

---

## Setup

```python
import sqlite3

# TODO: add COGS/Inventory reduction on sale (Dr COGS / Cr Inventory per invoice)
# TODO: add an opening capital entry (Dr Cash / Cr Common Stock) so Cash doesn't start negative

DB_PATH = "../database/erp_demo.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
```

**What this does:** `sqlite3` is Python's built-in module for talking to
SQLite databases — no installation needed. `conn` is the connection to the
database file; `cursor` is the tool used to actually run SQL commands
against it, similar in role to the SQL editor in DB Browser.

`DB_PATH` is a **relative path** — `../database/erp_demo.db` means "go up
one folder from wherever this script is run, then into `database/`". This
only works correctly if the script is run from inside the `scripts/`
folder.

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

**Concepts introduced:**
- **`DROP TABLE IF EXISTS`** — clears the table if it already exists, so
  the script can be re-run from scratch any number of times without
  erroring on "table already exists".
- **`"""..."""` (triple-quoted strings)** — lets a SQL statement span
  multiple lines, which keeps long `CREATE TABLE` statements readable.
- **A list of tuples** — `accounts` holds one tuple per account, each with
  4 values in a fixed order.
- **`for code, name, acc_type, balance in accounts:`** — unpacks each
  tuple into four named variables in one step. `acc_type` (not `type`) is
  used deliberately, since `type` is a reserved Python built-in function.
- **`?` placeholders** — never build SQL by pasting values directly into a
  string. The `?` marks are filled in safely from the tuple passed as the
  second argument to `execute()`, which also protects against SQL
  injection and handles special characters (like an apostrophe in a name)
  correctly.

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

**Concepts introduced:**
- **Drop order matters**: `journal_entry_line` is dropped *before*
  `journal_entry`, because it holds a foreign key pointing to it. Always
  drop child tables before parent tables.
- **`fiscal_year`/`fiscal_period` included directly** in the original
  `CREATE TABLE` — a deliberate correction versus the earlier hand-written
  SQL version, where these columns were bolted on later with `ALTER
  TABLE` once `v_budget_vs_actual` needed them.

---

## 3. Fiscal Calendar

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

**Concepts introduced:**
- **`range(1, 13)`** — generates the numbers 1 through 12. The first real
  loop over numbers instead of a fixed list, replacing 12 manual `INSERT`
  statements with one correct block of logic.
- **`f"2025-{month:02d}-01"` (f-strings)** — embeds a variable directly
  into a string. `{month:02d}` means "format this number as at least 2
  digits, padded with a leading zero" — so `1` becomes `01`, `12` stays
  `12`.
- **`if / elif / else`** — chooses the correct `end_date` depending on
  which month it is (28, 30, or 31 days).

---

## 4. Customer

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
```

**Concepts introduced:**
- **`enumerate(customer_names, start=1)`** — loops through a list while
  also producing a running counter (`i`), starting at 1 instead of the
  default 0. Needed here to build `CUST-001`, `CUST-002`, etc.
- **`len(customer_names)`** — counts how many items are in a list, used
  here just to make the final print message accurate without hardcoding a
  number.

---

## 5. Product

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

products = [
    ("Top", 5.00, 9.99),
    ("T-shirt", 10.00, 14.99),
    ("Hoodie", 15.00, 24.99),
    ("Cardigan", 17.50, 29.99),
    ("Pullover", 17.50, 29.99)
]

for i, (name, cost, price) in enumerate(products, start=1):
    sku = f"SKU-{1000 + i}"
    cursor.execute("""
        INSERT INTO product (sku, product_name, unit_cost, unit_price, revenue_account_id, cogs_account_id, inventory_account_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sku, name, cost, price, 2, 7, 3))

print(f"{len(products)} products inserted.")
```

**Concepts introduced:**
- **`enumerate(products, start=1)` with tuple unpacking** —
  `for i, (name, cost, price) in enumerate(...)` pulls out the running
  counter *and* all three values from each tuple in a single line.
- Every tuple in the list needs its **own complete set of parentheses** —
  a common mistake is dropping the opening `(` on later lines while
  keeping the closing `)`.

---

## 6. Sales Order + Sales Order Line

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
```

**Concepts introduced — the most important one in this whole script:**
- **`cursor.lastrowid`** — immediately after an `INSERT` into a table with
  an `AUTOINCREMENT` primary key, this returns the ID that row was just
  given. It's how a script (or, later, a backend API) links a parent row
  to the child rows it's about to create, without having to guess or
  hardcode an ID.
- **A `dict` (dictionary)** — `product_prices` maps a product_id to its
  price using `{key: value}` pairs, retrieved with `product_prices[1]`.
  Different from a list, which is indexed by position (0, 1, 2...); a dict
  is indexed by whatever key you choose.
- **A nested pattern**: for every order created in the loop, its line is
  created *immediately after*, using the `new_order_id` just captured.
  This exact "create parent → capture ID → create child" pattern repeats
  in every section below.

---

## 7. AR Invoice — the first automated GL posting

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

# Turn each sales order into an invoice
sales_order_ids = [1, 2, 3, 4, 5]
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

    # Step 4: link the invoice back to its journal entry
    cursor.execute("""
        UPDATE ar_invoice SET journal_entry_id = ? WHERE ar_invoice_id = ?
    """, (new_je_id, new_invoice_id))

print("5 AR invoices created, each with a balanced GL posting.")
```

**Why this section matters most:** this is the first place the script
does something a real application would also need to do — take one user
action (raise an invoice) and automatically generate a correct, balanced
GL posting behind the scenes, with no manual SQL involved. The 4-step
pattern here (create row → capture ID → post journal entry → link back)
is exactly what the future backend API will do on each HTTP request,
just triggered by a loop instead of a click.

**Account IDs used** (`2` for Accounts Receivable, `6` for Sales Revenue)
depend on the order accounts were inserted via *this* script — always
verify against `chart_of_accounts` before trusting a hardcoded number.

---

## 8. Cash Receipt

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

print("O2C cycle complete: 5 invoices raised, posted, and paid.")
```

**Concepts introduced:**
- **5 steps instead of 4** — this is the first loop that both creates a
  new posting *and* updates an existing row (`ar_invoice`) as a
  consequence. This exact shape — post a transaction, then update
  something else it affects — recurs constantly in real financial
  systems.
- **Indentation discipline**: every line inside this `for` loop must be
  indented identically. Python uses indentation (not brackets, as SQL
  does with `()`) to define what belongs inside a loop — a single
  misaligned line causes an `IndentationError`, especially when adding new
  lines by hand into an existing loop.

---

## 9. Vendor (Procure-to-Pay begins)

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
```

No new concepts here — a direct mirror of the `customer` section, with
`ap_account_id` (4 = Accounts Payable) in place of `ar_account_id`.

---

## 10. Purchase Order + Purchase Order Line

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
```

**Concept introduced:** `None` — Python's way of writing "no value"/SQL
`NULL`. Used here for `description`, since a `product_id` is supplied
instead (the column exists for free-text purchases that aren't tied to a
catalogue product).

---

## 11. AP Invoice

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
```

Direct mirror of the AR invoice section — same 4-step pattern, opposite
side of the transaction (Dr Inventory / Cr Accounts Payable instead of
Dr Accounts Receivable / Cr Sales Revenue).

---

## 12. Vendor Payment

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
print("P2P cycle complete: 5 invoices raised, posted, and paid.")
```

Mirror of the cash receipt section — same 5-step pattern, opposite
direction (Dr Accounts Payable / Cr Cash instead of Dr Cash / Cr Accounts
Receivable).

---

## 13. Close Checklist

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

**Concept introduced:** a **composite foreign key** —
`FOREIGN KEY (fiscal_year, fiscal_period) REFERENCES fiscal_calendar(fiscal_year, fiscal_period)`
references *two* columns at once, because `fiscal_calendar`'s primary key
is itself a combination of both.

---

## 14. Budget Line

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

**Concept introduced:** `UNIQUE` across **three columns together** —
ensures no more than one budget row can exist for the same
year+period+account combination, without restricting any single column on
its own.

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
1.  Chart of Accounts        (table + 7 accounts)
2.  General Ledger           (journal_entry + journal_entry_line)
3.  Fiscal Calendar          (table + 12 periods, via loop)
4.  Customer                 (table + 5 customers, via loop)
5.  Product                  (table + 5 products, via loop)
6.  Sales Order + Line       (table + 5 orders/lines, via loop + lastrowid)
7.  AR Invoice               (table + 5 invoices + automated GL postings)
8.  Cash Receipt             (table + 5 receipts + GL postings + invoice updates)
9.  Vendor                   (table + 5 vendors, via loop)
10. Purchase Order + Line    (table + 5 POs/lines, via loop + lastrowid)
11. AP Invoice               (table + 5 invoices + automated GL postings)
12. Vendor Payment           (table + 5 payments + GL postings + invoice updates)
13. Close Checklist          (table + 4 tasks)
14. Budget Line              (table + 2 budgets)
conn.commit() / conn.close()
```

## What's next

This script currently seeds a small, fixed dataset (5 records per core
entity) — enough to prove every table, constraint, and posting pattern
works correctly, matching what was first verified by hand in
`scripts/Database-SQL.md`. The next phase replaces these fixed lists with
Python's `random` module to generate hundreds of transactions spread
across multiple months, alongside fixing the two known gaps noted at the
top of this document (COGS/inventory reduction on sale, opening capital
entry).
