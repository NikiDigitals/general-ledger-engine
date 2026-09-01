# Database Instructions (SQL)

Complete reference of the SQLite database built so far for the Finance ERP
project. Every statement below has been typed, tested, and verified working
in DB Browser for SQLite. Running this file top to bottom (in the Execute
SQL tab) rebuilds the entire database from scratch.

> Note: `journal_entry` below includes `fiscal_year`, `fiscal_period`, and
> `reverses_journal_entry_id` directly in the original `CREATE TABLE`.
> Historically `fiscal_year`/`fiscal_period` were added later via
> `ALTER TABLE` once `v_budget_vs_actual` needed them, and
> `reverses_journal_entry_id` was added later still via `ALTER TABLE` to
> support reversal postings — see `LESSONS_LEARNED.md`. This file shows
> the clean, corrected version so it can be run in one pass without those
> extra steps.
>
> Note: `ar_invoice` below includes `'Written Off'` in the `status` CHECK
> constraint directly in the original `CREATE TABLE`. Historically this
> required rebuilding the table from scratch, since SQLite does not allow
> a CHECK constraint to be altered directly — see `LESSONS_LEARNED.md`.
>
> Note: `v_ar_ageing` and `v_ap_ageing` below use `julianday('now')` as the
> reference date, not a fixed date. An earlier version used a hardcoded
> `'2025-12-15'` for reproducible demo screenshots — correct for a
> single-year demo, but wrong for genuine ongoing use, where "today"
> must always mean today. See `DECISIONS.md`.

---

## 1. Chart of Accounts

```sql
CREATE TABLE chart_of_accounts (
    account_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    account_code   TEXT NOT NULL UNIQUE,
    account_name   TEXT NOT NULL,
    account_type   TEXT NOT NULL CHECK (account_type IN ('Asset','Liability','Equity','Revenue','Expense')),
    normal_balance TEXT NOT NULL CHECK (normal_balance IN ('Debit','Credit'))
);
```

**Sample data (9 accounts used throughout testing):**
```sql
INSERT INTO chart_of_accounts (account_code, account_name, account_type, normal_balance) VALUES
('1000', 'Cash and Cash Equivalents', 'Asset',     'Debit'),
('1100', 'Accounts Receivable',       'Asset',     'Debit'),
('1200', 'Inventory',                 'Asset',     'Debit'),
('2000', 'Accounts Payable',          'Liability', 'Credit'),
('3000', 'Common Stock',              'Equity',    'Credit'),
('4000', 'Sales Revenue',             'Revenue',   'Credit'),
('4100', 'Sales Discounts',           'Revenue',   'Debit'),
('5000', 'Cost of Goods Sold',        'Expense',   'Debit'),
('5100', 'Bad Debt Expense',          'Expense',   'Debit');
```

`Sales Discounts` is a **contra-revenue** account: it sits under the
Revenue category (hence the `4100` code, right after `4000`), but carries
`Debit` as its normal balance — the opposite of a typical Revenue account.
This keeps the value of discounts given visible on its own line, rather
than letting it silently reduce the `Sales Revenue` figure directly.

---

## 2. General Ledger — journal_entry + journal_entry_line

This is the core of the entire system: every financial fact is recorded
here, and the CHECK constraint on `journal_entry_line` makes an unbalanced
posting impossible.

```sql
CREATE TABLE journal_entry (
    journal_entry_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date                 DATE NOT NULL,
    fiscal_year                INTEGER NOT NULL DEFAULT 2025,
    fiscal_period               INTEGER NOT NULL DEFAULT 1,
    source_module               TEXT NOT NULL CHECK (source_module IN ('O2C', 'P2P', 'R2R', 'Manual')),
    description                 TEXT,
    reverses_journal_entry_id   INTEGER REFERENCES journal_entry(journal_entry_id)
);

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
);
```

**Verifying the balance guarantee (optional but recommended once):**
```sql
-- This should succeed:
INSERT INTO journal_entry (entry_date, source_module, description)
VALUES ('2025-01-15', 'Manual', 'Test entry');

INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (1, 1, 100, 0);
INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (1, 5, 0, 100);  -- adjust account_id if it doesn't match Common Stock in your data

-- This should FAIL with "CHECK constraint failed":
INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (1, 1, 50, 50);
```

---

## 3. Fiscal Calendar

Composite primary key example — a period is only unique by year + period
number together.

```sql
CREATE TABLE fiscal_calendar (
    fiscal_year    INTEGER NOT NULL,
    fiscal_period  INTEGER NOT NULL CHECK (fiscal_period BETWEEN 1 AND 12),
    period_name    TEXT NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    period_status  TEXT NOT NULL DEFAULT 'Open' CHECK (period_status IN ('Open', 'Closed')),
    PRIMARY KEY (fiscal_year, fiscal_period)
);
```

```sql
INSERT INTO fiscal_calendar (fiscal_year, fiscal_period, period_name, start_date, end_date)
VALUES
(2025, 1, 'January', '2025-01-01', '2025-01-31'),
(2026, 1, 'January', '2026-01-01', '2026-01-31');
```

> Note: the composite primary key `(fiscal_year, fiscal_period)` was
> designed from the start to support multiple years without any schema
> change — confirmed in practice when 2026 was added to the live database
> as a plain `INSERT`, no `ALTER TABLE` required. Each additional year
> needs its own 12 rows (one per month); see `LESSONS_LEARNED.md` for why
> this repetitive step is a deliberately manual, user-triggered action
> (`start_new_fiscal_year.py`) rather than an automatic background
> process.

---

## 4. Customer

```sql
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
);
```

```sql
INSERT INTO customer (customer_code, customer_name, country, ar_account_id)
VALUES ('CUST-001', 'Noordzee Logistics BV', 'NL', 2);
```

---

## 5. Product

Three foreign keys to `chart_of_accounts` — one each for revenue, cost of
goods sold, and inventory.

```sql
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
);
```

```sql
INSERT INTO product (sku, product_name, category, unit_cost, unit_price, revenue_account_id, cogs_account_id, inventory_account_id)
VALUES ('SKU-1001', 'Industriele Pomp Type A', 'Machines', 420, 780, 4, 7, 3);
-- adjust account_id numbers to match your chart_of_accounts row order
```

---

## 6. Sales Order + Sales Order Line (Order-to-Cash)

```sql
CREATE TABLE sales_order (
    sales_order_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number    TEXT NOT NULL UNIQUE,
    customer_id     INTEGER NOT NULL,
    order_date      DATE NOT NULL,
    status          TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Fulfilled', 'Invoiced', 'Cancelled')),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE sales_order_line (
    line_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_order_id   INTEGER NOT NULL,
    product_id       INTEGER NOT NULL,
    quantity         NUMERIC NOT NULL,
    unit_price       NUMERIC NOT NULL,
    FOREIGN KEY (sales_order_id) REFERENCES sales_order(sales_order_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
);
```

```sql
INSERT INTO sales_order (order_number, customer_id, order_date, status)
VALUES ('SO-2025-0001', 1, '2025-01-20', 'Open');

INSERT INTO sales_order_line (sales_order_id, product_id, quantity, unit_price)
VALUES (1, 1, 3, 780);
```

---

## 7. AR Invoice

First table linked back to `journal_entry` — `journal_entry_id` is
nullable because the invoice row must exist before the posting is created.

```sql
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
);
```

**Full worked example — invoice + posting (Dr AR / Cr Revenue):**
```sql
INSERT INTO ar_invoice (invoice_number, customer_id, sales_order_id, invoice_date, due_date, invoice_amount, status)
VALUES ('ARINV-2025-0001', 1, 1, '2025-01-20', '2025-02-19', 2340, 'Open');

INSERT INTO journal_entry (entry_date, source_module, description)
VALUES ('2025-01-20', 'O2C', 'AR invoice ARINV-2025-0001');
-- note the new journal_entry_id from the row above, then:

INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (2, 2, 2340, 0);   -- Dr Accounts Receivable
INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (2, 6, 0, 2340);   -- Cr Sales Revenue

UPDATE ar_invoice SET journal_entry_id = 2 WHERE invoice_number = 'ARINV-2025-0001';
```

---

## 8. Cash Receipt

```sql
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
);
```

**Full worked example — receipt + posting (Dr Cash / Cr AR):**
```sql
INSERT INTO cash_receipt (receipt_number, customer_id, ar_invoice_id, receipt_date, amount, payment_method)
VALUES ('CR-2025-0001', 1, 1, '2025-02-10', 2340, 'Bank Transfer');

INSERT INTO journal_entry (entry_date, source_module, description)
VALUES ('2025-02-10', 'O2C', 'Cash receipt CR-2025-0001');
-- note the new journal_entry_id, then:

INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (3, 1, 2340, 0);   -- Dr Cash
INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (3, 2, 0, 2340);   -- Cr Accounts Receivable

UPDATE cash_receipt SET journal_entry_id = 3 WHERE receipt_number = 'CR-2025-0001';
UPDATE ar_invoice SET amount_paid = 2340, status = 'Paid' WHERE invoice_number = 'ARINV-2025-0001';
```

**O2C cycle complete: customer → order → invoice → payment, fully reflected in the GL.**

---

## 9. Vendor (Procure-to-Pay begins — mirror of Customer)

```sql
CREATE TABLE vendor (
    vendor_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_code         TEXT NOT NULL UNIQUE,
    vendor_name         TEXT NOT NULL,
    country             TEXT,
    payment_terms_days  INTEGER DEFAULT 30,
    ap_account_id       INTEGER,
    is_active           INTEGER DEFAULT 1,
    FOREIGN KEY (ap_account_id) REFERENCES chart_of_accounts(account_id)
);
```

```sql
INSERT INTO vendor (vendor_code, vendor_name, country, ap_account_id)
VALUES ('VEND-001', 'Staal & Zonen Grondstoffen', 'NL', 4);
```

---

## 10. Purchase Order + Purchase Order Line

```sql
CREATE TABLE purchase_order (
    purchase_order_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number          TEXT NOT NULL UNIQUE,
    vendor_id          INTEGER NOT NULL,
    order_date         DATE NOT NULL,
    status             TEXT DEFAULT 'Open' CHECK (status IN ('Open', 'Received', 'Invoiced', 'Cancelled')),
    FOREIGN KEY (vendor_id) REFERENCES vendor(vendor_id)
);

CREATE TABLE purchase_order_line (
    line_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id  INTEGER NOT NULL,
    product_id         INTEGER,
    description        TEXT,
    quantity           NUMERIC NOT NULL,
    unit_cost          NUMERIC NOT NULL,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_order(purchase_order_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
);
```

```sql
INSERT INTO purchase_order (po_number, vendor_id, order_date, status)
VALUES ('PO-2025-0001', 1, '2025-01-15', 'Open');

INSERT INTO purchase_order_line (purchase_order_id, product_id, description, quantity, unit_cost)
VALUES (1, NULL, 'Onderhoud machinepark', 1, 4500);
```

---

## 11. AP Invoice

```sql
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
);
```

**Full worked example — invoice + posting (Dr Expense / Cr AP):**
```sql
INSERT INTO ap_invoice (invoice_number, vendor_id, purchase_order_id, invoice_date, due_date, invoice_amount, status)
VALUES ('APINV-2025-0001', 1, 1, '2025-01-16', '2025-02-15', 4500, 'Open');

INSERT INTO journal_entry (entry_date, source_module, description)
VALUES ('2025-01-16', 'P2P', 'AP invoice APINV-2025-0001');
-- note the new journal_entry_id, then:

INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (4, 7, 4500, 0);   -- Dr Cost of Goods Sold (temporary expense account)
INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (4, 4, 0, 4500);   -- Cr Accounts Payable

UPDATE ap_invoice SET journal_entry_id = 4 WHERE invoice_number = 'APINV-2025-0001';
```

---

## 12. Vendor Payment

```sql
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
);
```

**Full worked example — payment + posting (Dr AP / Cr Cash):**
```sql
INSERT INTO vendor_payment (payment_number, vendor_id, ap_invoice_id, payment_date, amount, payment_method)
VALUES ('VP-2025-0001', 1, 1, '2025-02-05', 4500, 'Bank Transfer');

INSERT INTO journal_entry (entry_date, source_module, description)
VALUES ('2025-02-05', 'P2P', 'Vendor payment VP-2025-0001');
-- note the new journal_entry_id, then:

INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (5, 4, 4500, 0);   -- Dr Accounts Payable
INSERT INTO journal_entry_line (journal_entry_id, account_id, debit_amount, credit_amount)
VALUES (5, 1, 0, 4500);   -- Cr Cash

UPDATE vendor_payment SET journal_entry_id = 5 WHERE payment_number = 'VP-2025-0001';
UPDATE ap_invoice SET amount_paid = 4500, status = 'Paid' WHERE invoice_number = 'APINV-2025-0001';
```

**P2P cycle complete: vendor → purchase order → invoice → payment, fully reflected in the GL.**

---

## 13. Close Checklist (Record-to-Report)

Composite foreign key example — references both columns of
`fiscal_calendar`'s composite primary key at once.

```sql
CREATE TABLE close_checklist (
    checklist_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year   INTEGER NOT NULL,
    fiscal_period INTEGER NOT NULL,
    task_name     TEXT NOT NULL,
    task_owner    TEXT,
    status        TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Complete')),
    completed_at  TEXT,
    FOREIGN KEY (fiscal_year, fiscal_period) REFERENCES fiscal_calendar(fiscal_year, fiscal_period)
);
```

```sql
INSERT INTO close_checklist (fiscal_year, fiscal_period, task_name, task_owner, status)
VALUES
(2025, 1, 'Bank reconciliation',   'Controller', 'Complete'),
(2025, 1, 'AR sub-ledger review',  'AR Lead',    'Complete'),
(2025, 1, 'AP sub-ledger review',  'AP Lead',    'Pending'),
(2025, 1, 'Trial balance review',  'Controller', 'In Progress');
```

---

## 14. Budget Line

```sql
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
);
```

```sql
INSERT INTO budget_line (fiscal_year, fiscal_period, account_id, budgeted_amount)
VALUES
(2025, 1, 6, 2000),  -- Sales Revenue budget
(2025, 1, 7, 4000);  -- Cost of Goods Sold budget
```

---

## 15. Reporting Views

All six views built so far. They read exclusively from `journal_entry_line`
and the sub-ledger tables, so they always stay consistent with the GL.

### v_trial_balance
```sql
CREATE VIEW v_trial_balance AS
SELECT
    coa.account_code,
    coa.account_name,
    coa.normal_balance,
    CASE
        WHEN coa.normal_balance = 'Debit' THEN SUM(jel.debit_amount) - SUM(jel.credit_amount)
        ELSE SUM(jel.credit_amount) - SUM(jel.debit_amount)
    END AS balance
FROM journal_entry_line jel
JOIN chart_of_accounts coa ON coa.account_id = jel.account_id
GROUP BY coa.account_code, coa.account_name, coa.normal_balance;
```

### v_ar_ageing
```sql
CREATE VIEW v_ar_ageing AS
SELECT
    ai.invoice_number,
    c.customer_name,
    ai.due_date,
    ai.invoice_amount - ai.amount_paid AS open_amount,
    CAST(julianday('now') - julianday(ai.due_date) AS INTEGER) AS days_past_due,
    CASE
        WHEN julianday('now') - julianday(ai.due_date) <= 0 THEN 'Not Due'
        WHEN julianday('now') - julianday(ai.due_date) <= 30 THEN '1-30 days'
        WHEN julianday('now') - julianday(ai.due_date) <= 60 THEN '31-60 days'
        WHEN julianday('now') - julianday(ai.due_date) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END AS ageing_bucket
FROM ar_invoice ai
JOIN customer c ON c.customer_id = ai.customer_id
WHERE ai.status NOT IN ('Paid', 'Written Off');
```

### v_ap_ageing
```sql
CREATE VIEW v_ap_ageing AS
SELECT
    ai.invoice_number,
    c.vendor_name,
    ai.due_date,
    ai.invoice_amount - ai.amount_paid AS open_amount,
    CAST(julianday('now') - julianday(ai.due_date) AS INTEGER) AS days_past_due,
    CASE
        WHEN julianday('now') - julianday(ai.due_date) <= 0 THEN 'Not Due'
        WHEN julianday('now') - julianday(ai.due_date) <= 30 THEN '1-30 days'
        WHEN julianday('now') - julianday(ai.due_date) <= 60 THEN '31-60 days'
        WHEN julianday('now') - julianday(ai.due_date) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END AS ageing_bucket
FROM ap_invoice ai
JOIN vendor c ON c.vendor_id = ai.vendor_id
WHERE ai.status != 'Paid';
```

### v_income_statement
```sql
CREATE VIEW v_income_statement AS
SELECT
    SUM(CASE WHEN coa.account_type = 'Revenue' THEN jel.credit_amount - jel.debit_amount ELSE 0 END) AS total_revenue,
    SUM(CASE WHEN coa.account_type = 'Expense' THEN jel.debit_amount - jel.credit_amount ELSE 0 END) AS total_expenses,
    SUM(CASE WHEN coa.account_type = 'Revenue' THEN jel.credit_amount - jel.debit_amount ELSE 0 END)
    - SUM(CASE WHEN coa.account_type = 'Expense' THEN jel.debit_amount - jel.credit_amount ELSE 0 END) AS net_income
FROM journal_entry_line jel
JOIN chart_of_accounts coa ON coa.account_id = jel.account_id;
```

### v_close_status
```sql
CREATE VIEW v_close_status AS
SELECT
    fiscal_year,
    fiscal_period,
    COUNT(*) AS total_tasks,
    SUM(CASE WHEN status = 'Complete' THEN 1 ELSE 0 END) AS completed_tasks,
    ROUND(100.0 * SUM(CASE WHEN status = 'Complete' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_complete
FROM close_checklist
GROUP BY fiscal_year, fiscal_period;
```

### v_budget_vs_actual
```sql
CREATE VIEW v_budget_vs_actual AS
SELECT
    bl.fiscal_year,
    bl.fiscal_period,
    coa.account_code,
    coa.account_name,
    bl.budgeted_amount,
    COALESCE((
        SELECT SUM(CASE WHEN coa.account_type = 'Revenue' THEN jel.credit_amount - jel.debit_amount
                         ELSE jel.debit_amount - jel.credit_amount END)
        FROM journal_entry_line jel
        JOIN journal_entry je ON je.journal_entry_id = jel.journal_entry_id
        WHERE jel.account_id = bl.account_id
          AND je.fiscal_year = bl.fiscal_year
          AND je.fiscal_period = bl.fiscal_period
    ), 0) AS actual_amount
FROM budget_line bl
JOIN chart_of_accounts coa ON coa.account_id = bl.account_id;
```

**Testing any view:**
```sql
SELECT * FROM v_trial_balance;
SELECT * FROM v_ar_ageing;
SELECT * FROM v_ap_ageing;
SELECT * FROM v_income_statement;
SELECT * FROM v_close_status;
SELECT * FROM v_budget_vs_actual;
```

---

## 16. Starting a new fiscal year

`fiscal_calendar`'s composite primary key (`fiscal_year`, `fiscal_period`)
supports multiple years without any schema change — adding a year is
purely a matter of inserting 12 more rows. This is done via a small,
deliberately **manual, user-triggered** script
(`scripts/start_new_fiscal_year.py`), not an automatic background
process — a fiscal year-end is a conscious, controlled event in real
accounting, not something that should happen silently. See that script's
own explained documentation and `docs/DECISIONS.md` for the reasoning.

```sql
-- What the script does, expressed as plain SQL (illustrative — the real
-- script determines the next year automatically instead of hardcoding it):
INSERT INTO fiscal_calendar (fiscal_year, fiscal_period, period_name, start_date, end_date)
VALUES
(2027, 1, 'January', '2027-01-01', '2027-01-31'),
(2027, 2, 'February', '2027-02-01', '2027-02-28');
-- ... one row per month, 12 total
```

---

## After running this file

Remember to click **Write Changes** in DB Browser to persist everything to
disk — none of the above is permanent until you do.

## What's next

The data above is minimal, hand-typed test data — enough to prove every
constraint and view works correctly. `scripts/generate_data.py` builds
this same schema (plus the reversal/write-off/multi-year support noted
above) and seeds it with 232+ realistic, randomised transactions in a
single run — see `scripts/data_generator_python_explained.md`.
