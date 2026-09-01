# Milestones

## Database schema

1. **Database foundation built**: chart of accounts, general ledger
   (`journal_entry` + `journal_entry_line`) with database-enforced
   double-entry bookkeeping — no posting can ever be written unbalanced.
   **[SQLite/DDL]**

2. **Order-to-Cash fully working**: customer → order → invoice → payment,
   including the associated GL postings, manually tested end-to-end and
   verified that debit always equals credit. **[SQLite/DDL + DML]**

3. **Procure-to-Pay fully working**: vendor → purchase order → invoice →
   payment, mirror image of O2C, end-to-end tested with correct GL
   postings. **[SQLite/DDL + DML]**

4. **Full database schema completed**: all 17 tables in place (O2C, P2P,
   R2R), including close checklist and budget tracking support.
   **[SQLite/DDL]**

## Reporting views

5. **First reporting view built**: `v_trial_balance`, combining JOIN,
   GROUP BY, SUM, and CASE WHEN to correctly normalise Debit vs Credit
   balances per account — reusable via a single SELECT. **[SQL/DDL+DQL]**

6. **Reporting layer expanded**: v_ar_aging and v_ap_aging views built,
   introducing date arithmetic (julianday) and multi-branch CASE WHEN for
   ageing buckets. **[SQL/DDL+DQL]**

7. **Full reporting layer completed**: six views covering trial balance,
   AR/AP ageing, income statement, close status, and budget vs actual —
   including a correlated subquery and an ALTER TABLE schema fix along the
   way. **[SQL/DDL+DQL]**

## Python data generator

8. **Python connected to the database**: verified the sqlite3 module can
   read from erp_demo.db directly. **[Python]**

9. **Python data generator complete (structure)**: all 17 tables — O2C,
   P2P, and R2R (close_checklist, budget_line) — rebuilt via Python in a
   single script run. Existing SQL views (v_trial_balance, v_ar_aging,
   v_close_status, v_budget_vs_actual, etc.) verified to still work
   correctly against the Python-rebuilt data. Both known gaps identified
   after initial automation — no opening capital entry, no COGS/Inventory
   reduction on sale — have since been resolved: an opening capital entry
   (Dr Cash / Cr Common Stock) now funds the business before any other
   transaction, and every AR invoice now also posts a matching
   Dr COGS / Cr Inventory line. The trial balance reflects a realistic,
   funded position with no outstanding known gaps. **[Python]**

10. **Sales orders and AR invoices scaled up with controlled randomness**:
    customers (5→20) and products (5→15) expanded with randomised
    name-combinations and cost-based pricing; sales orders scaled up 30x
    (5→150), spread across the full year via a custom random_date_2025()
    function. ~83% invoiced (124 of 150), ~74% of those paid (92 of 124),
    leaving 32 open invoices for realistic AR ageing. Introduced
    random.random() threshold checks, `continue` to skip loop iterations,
    and building/reusing a list (ar_invoice_ids) across two separate
    generation steps. **[Python]**

11. **Full data generator scaled up — O2C and P2P**: purchase orders,
    vendors, AP invoices, and vendor payments scaled up to match the O2C
    approach (12 vendors, 100 purchase orders, ~82% invoiced, ~73% of
    those paid). Combined with the O2C scale-up, the generator now
    produces 232+ transactions with realistic open/paid ratios across
    both cycles, all still perfectly balanced. The data generator is now
    feature-complete for a realistic single-year demo dataset. **[Python]**

## Backend API (Python/FastAPI)

12. **Node.js backend initialised (superseded)**: Express and
    better-sqlite3 installed, first successful database read from
    JavaScript (`test-connection.js`) confirming the same data accessible
    from Python and SQL is reachable via Node. **[Node.js]**

13. **First working Node/Express API endpoint (superseded)**: a running
    Express server exposed `GET /api/accounts`, returning live data from
    erp_demo.db as JSON — the first time this project's data was reachable
    over HTTP instead of only through a database browser or script.
    Repository hygiene fixed in the same session: project-wide
    `.gitignore` added and `node_modules` removed from version control.
    **[Node.js/Express]**

14. **Backend migrated to Python/FastAPI**: the Node/Express work above
    was deliberately superseded, not deleted — preserved as
    `backend-node-exploration/` to align backend skills with a larger,
    related project's tech stack. First FastAPI endpoint
    (`GET /api/accounts`) live within `backend/`, including FastAPI's
    auto-generated interactive docs at `/docs`, confirming the migration
    works and exposes richer built-in tooling than the Express
    equivalent. **[Python/FastAPI]**

15. **Schema extended for reversals, write-offs, and multi-year support —
    verified live via the API**: `journal_entry.reverses_journal_entry_id`
    added (nullable, self-referencing FK, enabling correction entries
    without ever editing/deleting an original posting), `'Written Off'`
    added to `ar_invoice.status` CHECK, `Bad Debt Expense` and
    `Sales Discounts` (a deliberate Debit-normal contra-revenue account)
    added to `chart_of_accounts`, and `fiscal_calendar` extended to cover
    2025–2026. On the Python side, `generate_data.py` now drives every
    date and identifier from a single `CURRENT_YEAR` constant instead of
    hardcoding the year, uses `calendar.monthrange()` for leap-year-safe
    month lengths, and a new, deliberately manual
    `scripts/start_new_fiscal_year.py` script adds future years on
    request. `v_ar_aging`/`v_ap_aging` switched from a fixed reference
    date to `julianday('now')`. All of it confirmed live through the
    FastAPI backend (`PRAGMA table_info`, a distinct-fiscal-years query)
    rather than only in DB Browser. **[SQLite/Python/FastAPI]**

16. **Silent account_id drift found and fixed**: three hardcoded
    account_id references in generate_data.py, left pointing at the old
    chart-of-accounts ordering after two new accounts were inserted
    mid-list, corrected and verified live via /api/account-balances —
    Cost of Goods Sold now carries its expected balance, Sales Discounts
    and Bad Debt Expense correctly carry none. **[Python/FastAPI]**

## Frontend (React)

*(No milestones yet.)*

## Deployment (Azure)

*(No milestones yet.)*

## Portfolio site write-up

*(No milestones yet.)*

<!--
Upcoming milestones, to be added once reached:

16. Full CRUD API: customers, vendors, invoices, reporting views, with
    accounting-standard soft-delete on chart_of_accounts
17. Application-layer routes that create a reversal, a write-off, and a
    discount, using the schema support already in place
18. Frontend (React) connected to the backend, first invoice created via the UI
19. Fully running locally: backend + frontend + database together
20. Deployed on Azure, publicly reachable
21. Portfolio site write-up published
-->
