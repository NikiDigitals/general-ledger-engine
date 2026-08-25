# Decisions

**SQLite instead of PostgreSQL during the build phase**
No server required, less friction while learning the fundamentals without
connection configuration. The schema is later portable 1-to-1 to
PostgreSQL (same DDL structure, different syntax details).

**journal_entry_id optional (nullable) on ar_invoice/cash_receipt/ap_invoice/vendor_payment**
Avoids a chicken-and-egg problem: the invoice/payment row must exist first
before the corresponding posting can be created. The link is established
afterwards via an `UPDATE`, rather than being mandatory upfront. Applied
consistently across both O2C and P2P.

**Balance enforced with a database CHECK, not application logic**
`CHECK ((debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0))` on
`journal_entry_line`. This means no future application (or manual insert)
can ever write an unbalanced posting — the guarantee sits at the deepest
level, independent of how careful the application code happens to be.

**English accounting terminology (Debit/Credit, Cancelled) instead of Dutch**
Aligns with the standard language used in accounting software, code, and
APIs — avoiding a future mismatch between database values and application
code. Extended to all project documentation as a fixed rule: conversation
in Dutch, all docs/code/comments in English.

**Price captured on the order line, not only on the product**
`sales_order_line.unit_price` exists alongside `product.unit_price` so that
a historical order remains correct even if a product's standard price
changes later.

**fiscal_year/fiscal_period added to journal_entry via ALTER TABLE, not a rebuild**
When `v_budget_vs_actual` needed to filter postings by period, the columns
didn't exist yet on the original `journal_entry` table. Rather than
dropping and recreating the table (and re-entering all existing data), the
columns were added retroactively with `ALTER TABLE ... ADD COLUMN`, then
backfilled using `strftime()` on the existing `entry_date` values. Reflects
a normal part of schema evolution — a design only fully reveals its
requirements once enough of the system is built. Future from-scratch
rebuilds (e.g. the Python generator) will include these columns in the
original `CREATE TABLE` directly.

**Documentation split into separate files per concern, not one combined log**
`ARCHITECTURE.md`, `MILESTONES.md`, `DECISIONS.md`, and
`LESSONS_LEARNED.md` are kept separate rather than merged into a single
devlog, so each can be scanned independently depending on what a reader
(or future self) is looking for.

**Milestones tracked at the level of working functionality, not individual build steps**
A milestone is only logged once a complete, testable capability exists
(e.g. "the entire O2C cycle works end-to-end"), not each time a single
table is created. Keeps the milestone log meaningful rather than a long,
low-value list of build steps.

**MIT license for the public repository**
Permissive, widely recognised, and appropriate for a portfolio project
intended to be freely viewable and reusable by others.

**erp_demo.db committed to the repository, not gitignored**
Chosen so visitors can inspect the actual database immediately without
first running any scripts. Documented as a reversible choice in
`.gitignore` should a future preference be to keep only the generation
scripts under version control.

**Azure for deployment (instead of Vercel/Railway/other platforms)**
Account already exists, so fewer new platforms to learn. App Service
(backend) + Static Web Apps (frontend), both with a free tier — suitable
for a portfolio demo without monthly costs.
