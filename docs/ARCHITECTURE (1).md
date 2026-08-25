# Architecture

## Database layer (SQLite, via DB Browser for SQLite)

- One central General Ledger (`journal_entry` + `journal_entry_line`) as the
  single source of truth for all financial facts.
- Sub-ledger tables (`customer`, `sales_order`, `ar_invoice`,
  `cash_receipt`, and the P2P counterparts still to come) reference
  `journal_entry` via an optional `journal_entry_id` foreign key.
- Double-entry bookkeeping is enforced at database level via a CHECK
  constraint on `journal_entry_line`: every line must have exactly one of
  debit/credit greater than 0, never both or neither.
- Every account (`chart_of_accounts`) has a `normal_balance` (Debit/Credit)
  that determines how that account behaves in reporting.
- Composite primary key (`fiscal_year` + `fiscal_period`) on
  `fiscal_calendar` to tie postings to periods.

## Process structure

- **O2C (Order-to-Cash)** — complete:
  `customer` → `product` → `sales_order` → `sales_order_line` →
  `ar_invoice` → `cash_receipt`, each linked to the GL.
- **P2P (Procure-to-Pay)** — in progress, mirror image of O2C:
  `vendor` → `purchase_order` → `purchase_order_line` → `ap_invoice` →
  `vendor_payment`.
- **R2R (Record-to-Report)** — still to be built:
  `close_checklist`, `budget_line`.

## Why this design?

The core guarantee of this system is that the books **always** balance,
regardless of whatever application ends up running on top of it. By
enforcing double-entry at the database level (not in application code), no
future bug, script, or ad-hoc SQL statement can ever write an unbalanced
posting — the database simply refuses it.

## Still to be built

- P2P tables (vendor, purchase_order, ap_invoice, vendor_payment)
- R2R tables (close_checklist, budget_line)
- Reporting views (trial balance, AR/AP ageing, income statement)
- Backend (Node/Express) to drive this database via a REST API
- Frontend (React) for data entry
- Deployment on Azure (App Service + Static Web Apps)
