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

## Backend API (Node/Express)

12. **Node.js backend initialised**: Express and better-sqlite3 installed,
    first successful database read from JavaScript (`test-connection.js`)
    confirming the same data accessible from Python and SQL is reachable
    via Node — the foundation for the REST API. **[Node.js]**

13. **First working API endpoint**: a running Express server exposes
    `GET /api/accounts`, returning live data from erp_demo.db as JSON —
    the first time this project's data is reachable over HTTP instead of
    only through a database browser or script. Repository hygiene fixed
    in the same session: project-wide `.gitignore` added and
    `node_modules` removed from version control. **[Node.js/Express]**

## Frontend (React)

*(No milestones yet.)*

## Deployment (Azure)

*(No milestones yet.)*

## Portfolio site write-up

*(No milestones yet.)*

<!--
Upcoming milestones, to be added once reached:

14. Full CRUD API: customers, vendors, invoices, reporting views, with
    accounting-standard soft-delete on chart_of_accounts
15. Frontend (React) connected to the backend, first invoice created via the UI
16. Fully running locally: backend + frontend + database together
17. Deployed on Azure, publicly reachable
18. Portfolio site write-up published
-->
