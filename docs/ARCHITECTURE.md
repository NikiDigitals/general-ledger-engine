# Architecture

## Database layer (SQLite, via DB Browser for SQLite)

- One central General Ledger (`journal_entry` + `journal_entry_line`) as the
  single source of truth for all financial facts.
- Sub-ledger tables (`customer`, `sales_order`, `ar_invoice`,
  `cash_receipt`, `vendor`, `purchase_order`, `ap_invoice`,
  `vendor_payment`) reference `journal_entry` via an optional
  `journal_entry_id` foreign key.
- Double-entry bookkeeping is enforced at database level via a CHECK
  constraint on `journal_entry_line`: every line must have exactly one of
  debit/credit greater than 0, never both or neither.
- Every account (`chart_of_accounts`) has a `normal_balance` (Debit/Credit)
  that determines how that account behaves in reporting.
- Composite primary key (`fiscal_year` + `fiscal_period`) on
  `fiscal_calendar` to tie postings to periods. `journal_entry`,
  `close_checklist`, and `budget_line` all reference this composite key.

## Process structure — all three cycles complete

- **O2C (Order-to-Cash)**:
  `customer` → `product` → `sales_order` → `sales_order_line` →
  `ar_invoice` → `cash_receipt`, each linked to the GL. Tested end-to-end:
  order → invoice → payment, with correct postings at every step.
- **P2P (Procure-to-Pay)**, mirror image of O2C:
  `vendor` → `purchase_order` → `purchase_order_line` → `ap_invoice` →
  `vendor_payment`. Tested end-to-end with the same rigor as O2C.
- **R2R (Record-to-Report)**:
  `close_checklist` (period-close task tracking, composite FK to
  `fiscal_calendar`) and `budget_line` (per-account monthly budgets,
  compared against actuals via a correlated subquery).

## Reporting layer — six views, all reading exclusively from the GL

- `v_trial_balance` — per-account balance, normalised for Debit/Credit
  accounts via `CASE WHEN normal_balance = ...`
- `v_ar_aging` / `v_ap_aging` — open invoices bucketed by days past due,
  using `julianday()` date arithmetic and a multi-branch `CASE WHEN`
- `v_income_statement` — revenue, expenses, and net income in a single row
- `v_close_status` — percentage of close-checklist tasks completed, per
  period
- `v_budget_vs_actual` — budgeted vs actual amount per account/period,
  using a correlated subquery against `journal_entry_line`

All views read only from `journal_entry_line` and the sub-ledger tables —
never from anywhere else — so reporting always stays consistent with
whatever is actually posted in the GL.

## Why this design?

The core guarantee of this system is that the books **always** balance,
regardless of whatever application ends up running on top of it. By
enforcing double-entry at the database level (not in application code), no
future bug, script, or ad-hoc SQL statement can ever write an unbalanced
posting — the database simply refuses it. This was verified directly: a
missing pair of `journal_entry_line` rows (from an early manual mistake)
was caught by the trial balance view itself, before it caused any further
harm — see `LESSONS_LEARNED.md`.

## Version control

The project is tracked in Git and hosted on GitHub
(`github.com/NikiDigitals/general-ledger-engine`), including the SQLite
database file itself, all documentation, and the ERD — so the full state
of the project at any point is reproducible from the repository alone.

## Still to be built

- Python data generator (realistic multi-month transaction volume,
  replacing the current small set of hand-typed test rows)
- Backend (Node/Express) to drive this database via a REST API
- Frontend (React) for data entry
- Deployment on Azure (App Service + Static Web Apps)
