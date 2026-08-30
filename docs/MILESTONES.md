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

## Backend API (Node/Express)

*(No milestones yet.)*

## Frontend (React)

*(No milestones yet.)*

## Deployment (Azure)

*(No milestones yet.)*

## Portfolio site write-up

*(No milestones yet.)*

<!--
Upcoming milestones, to be added once reached:

10. Python data generator scaled up: known gaps fixed (COGS/inventory
    reduction, opening capital entry) and fixed test dataset replaced
    with hundreds of randomised transactions across multiple months
11. Backend API (Node/Express) built, first endpoint live
12. Frontend (React) connected to the backend, first invoice created via the UI
13. Fully running locally: backend + frontend + database together
14. Deployed on Azure, publicly reachable
15. Portfolio site write-up published
-->
