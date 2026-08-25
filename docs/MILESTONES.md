# Milestones

## Database fundament completed

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

## Raportage views

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

## Data - Generator

8. **Python connected to the database**: verified the sqlite3 module can
   read from erp_demo.db directly. **[Python]**

9.**First data-generation loop**: fiscal_calendar rebuilt via Python,
replacing 12 manual INSERTs with a single for-loop and parameterised
queries (? placeholders). **[Python]**

## Backend (NODE/Express)

## Frontend (React)##

## Dashboiard - demo

## Github + deployment naar Azure

## Portfolio - website + GitBook##

<!--
Upcoming milestones, to be added once reached:

3. Procure-to-Pay fully working (mirror image of O2C)
4. Reporting layer: trial balance, AR/AP ageing as SQL views
5. Data generator script (Python) for realistic test data
6. Backend API (Node/Express) built, first endpoint live
7. Frontend (React) connected to the backend, first invoice created via the UI
8. R2R: close checklist + budget vs actual added
9. Fully running locally: backend + frontend + database together
10. Deployed on Azure, publicly reachable
-->
