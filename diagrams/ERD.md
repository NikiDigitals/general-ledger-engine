# Entity Relationship Diagram

```mermaid
erDiagram
    CHART_OF_ACCOUNTS {
        int account_id PK
        text account_code
        text account_name
        text account_type
        text normal_balance
    }

    JOURNAL_ENTRY {
        int journal_entry_id PK
        date entry_date
        int fiscal_year
        int fiscal_period
        text source_module
        text description
        int reverses_journal_entry_id FK
    }

    JOURNAL_ENTRY_LINE {
        int line_id PK
        int journal_entry_id FK
        int account_id FK
        numeric debit_amount
        numeric credit_amount
    }

    FISCAL_CALENDAR {
        int fiscal_year PK
        int fiscal_period PK
        text period_name
        date start_date
        date end_date
        text period_status
    }

    CUSTOMER {
        int customer_id PK
        text customer_code
        text customer_name
        text country
        numeric credit_limit
        int payment_terms_days
        int ar_account_id FK
        int is_active
    }

    PRODUCT {
        int product_id PK
        text sku
        text product_name
        text category
        numeric unit_cost
        numeric unit_price
        int revenue_account_id FK
        int cogs_account_id FK
        int inventory_account_id FK
    }

    SALES_ORDER {
        int sales_order_id PK
        text order_number
        int customer_id FK
        date order_date
        text status
    }

    SALES_ORDER_LINE {
        int line_id PK
        int sales_order_id FK
        int product_id FK
        numeric quantity
        numeric unit_price
    }

    AR_INVOICE {
        int ar_invoice_id PK
        text invoice_number
        int customer_id FK
        int sales_order_id FK
        date invoice_date
        date due_date
        numeric invoice_amount
        numeric amount_paid
        text status
        int journal_entry_id FK
    }

    CASH_RECEIPT {
        int cash_receipt_id PK
        text receipt_number
        int customer_id FK
        int ar_invoice_id FK
        date receipt_date
        numeric amount
        text payment_method
        int journal_entry_id FK
    }

    VENDOR {
        int vendor_id PK
        text vendor_code
        text vendor_name
        text country
        int payment_terms_days
        int ap_account_id FK
        int is_active
    }

    PURCHASE_ORDER {
        int purchase_order_id PK
        text po_number
        int vendor_id FK
        date order_date
        text status
    }

    PURCHASE_ORDER_LINE {
        int line_id PK
        int purchase_order_id FK
        int product_id FK
        text description
        numeric quantity
        numeric unit_cost
    }

    AP_INVOICE {
        int ap_invoice_id PK
        text invoice_number
        int vendor_id FK
        int purchase_order_id FK
        date invoice_date
        date due_date
        numeric invoice_amount
        numeric amount_paid
        text status
        int journal_entry_id FK
    }

    VENDOR_PAYMENT {
        int vendor_payment_id PK
        text payment_number
        int vendor_id FK
        int ap_invoice_id FK
        date payment_date
        numeric amount
        text payment_method
        int journal_entry_id FK
    }

    CLOSE_CHECKLIST {
        int checklist_id PK
        int fiscal_year FK
        int fiscal_period FK
        text task_name
        text task_owner
        text status
        text completed_at
    }

    BUDGET_LINE {
        int budget_id PK
        int fiscal_year FK
        int fiscal_period FK
        int account_id FK
        numeric budgeted_amount
        text notes
    }

    %% --- General Ledger core ---
    JOURNAL_ENTRY ||--o{ JOURNAL_ENTRY_LINE : contains
    CHART_OF_ACCOUNTS ||--o{ JOURNAL_ENTRY_LINE : "posted to"
    FISCAL_CALENDAR ||--o{ JOURNAL_ENTRY : "defines period"
    JOURNAL_ENTRY ||--o| JOURNAL_ENTRY : "reverses (self-referencing)"

    %% --- Order-to-Cash ---
    CUSTOMER ||--o{ SALES_ORDER : places
    CUSTOMER ||--o{ AR_INVOICE : "billed to"
    CUSTOMER ||--o{ CASH_RECEIPT : "pays as"
    CHART_OF_ACCOUNTS ||--o{ CUSTOMER : "AR account"
    SALES_ORDER ||--o{ SALES_ORDER_LINE : contains
    PRODUCT ||--o{ SALES_ORDER_LINE : "ordered as"
    SALES_ORDER ||--o| AR_INVOICE : "invoiced as"
    AR_INVOICE ||--o{ CASH_RECEIPT : "settled by"
    JOURNAL_ENTRY ||--o| AR_INVOICE : generates
    JOURNAL_ENTRY ||--o| CASH_RECEIPT : generates

    %% --- Procure-to-Pay ---
    VENDOR ||--o{ PURCHASE_ORDER : receives
    VENDOR ||--o{ AP_INVOICE : "bills to"
    VENDOR ||--o{ VENDOR_PAYMENT : "paid as"
    CHART_OF_ACCOUNTS ||--o{ VENDOR : "AP account"
    PURCHASE_ORDER ||--o{ PURCHASE_ORDER_LINE : contains
    PRODUCT ||--o{ PURCHASE_ORDER_LINE : "ordered as"
    PURCHASE_ORDER ||--o| AP_INVOICE : "invoiced as"
    AP_INVOICE ||--o{ VENDOR_PAYMENT : "settled by"
    JOURNAL_ENTRY ||--o| AP_INVOICE : generates
    JOURNAL_ENTRY ||--o| VENDOR_PAYMENT : generates

    %% --- Product to accounts ---
    CHART_OF_ACCOUNTS ||--o{ PRODUCT : "revenue account"
    CHART_OF_ACCOUNTS ||--o{ PRODUCT : "COGS account"
    CHART_OF_ACCOUNTS ||--o{ PRODUCT : "inventory account"

    %% --- Record-to-Report ---
    FISCAL_CALENDAR ||--o{ CLOSE_CHECKLIST : "defines period"
    FISCAL_CALENDAR ||--o{ BUDGET_LINE : "defines period"
    CHART_OF_ACCOUNTS ||--o{ BUDGET_LINE : "budgeted for"
```

## How to read this

- **PK** = Primary Key, **FK** = Foreign Key
- `||--o{` means "exactly one, to zero-or-many" — e.g. one `CUSTOMER` can
  place zero or many `SALES_ORDER` rows, but every `SALES_ORDER` belongs to
  exactly one `CUSTOMER`.
- `||--o|` means "exactly one, to zero-or-one" — e.g. a `SALES_ORDER` is
  invoiced at most once (into a single `AR_INVOICE`), but not every order
  has to be invoiced yet.
- The `JOURNAL_ENTRY ||--o| JOURNAL_ENTRY : "reverses (self-referencing)"`
  line is a **self-referencing relationship**: a table pointing back to
  its own primary key. It represents `reverses_journal_entry_id` — an
  optional link from a correction entry to the original entry it
  corrects. No entry currently uses this in the seeded demo data; the
  schema is ready for it, but no application logic creates a reversal
  yet.

## Design principle visible in this diagram

Notice that `JOURNAL_ENTRY` sits at the centre, connected to every
transactional table (`AR_INVOICE`, `CASH_RECEIPT`, `AP_INVOICE`,
`VENDOR_PAYMENT`) and now also to itself. This reflects the core
architecture decision: the General Ledger is the single source of truth,
every financial event in any sub-ledger produces a posting there, and any
future correction to that posting is itself a new, traceable posting —
never a silent edit or deletion of the original.

## What's not shown

`chart_of_accounts` gained two additional *rows* (`Sales Discounts`,
`Bad Debt Expense`) as part of the same schema extension that added
`reverses_journal_entry_id` — this diagram shows table *structure*, not
data, so those new accounts don't appear here; see
`scripts/rebuild_database_sql.md` section 1 for the full account list.

## How to preview this before committing

Paste the code block above (without the outer ` ```mermaid ` fence) into
the [Mermaid Live Editor](https://mermaid.live) to see the rendered
diagram instantly. Once this file is committed to GitHub, it renders
automatically wherever it's linked or viewed — no extra tool needed.
