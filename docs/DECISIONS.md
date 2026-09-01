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

**Fixed random seed (`random.seed(42)`) instead of true randomness**
Guarantees the generator produces an identical dataset on every run. This
makes bugs reproducible (a value that looks wrong stays the same wrong
value the next time the script runs, rather than shifting), keeps
screenshots and documentation examples permanently accurate, and makes it
possible to verify a fix by simply re-running the script and comparing
against a known-good prior result.

**Invoiced/paid ratios deliberately below 100% during scale-up**
Sales orders and purchase orders are invoiced at ~83%/82% respectively,
and of those, only ~74%/73% are paid — leaving a deliberate set of open
invoices in both AR and AP. A dataset where everything is paid instantly
would make `v_ar_aging`/`v_ap_aging` return nothing meaningful; the
thresholds were chosen specifically to leave a realistic number of open,
overdue items for those views to report on.

**COGS costing simplified to a flat 50% of sale price, not yet per-product**
The scale-up phase prioritised getting a complete, balanced transaction
cycle working across realistic volume over perfecting cost accuracy.
Every invoice now correctly reduces Inventory and books COGS, which
resolves the balance-completeness gap — the remaining refinement (using
each product's actual `unit_cost` instead of a flat assumption) is
tracked in `ARCHITECTURE.md` under Future Extensions rather than blocking
this phase.

**DB_PATH resolved relative to the script's own location, not the working directory**
An earlier version used a plain relative path (`"../database/erp_demo.db"`),
which only worked correctly if the script was launched from inside
`scripts/` — a fragile assumption for a portfolio repo that other people
will clone and run from whatever folder they happen to be in. Replaced
with `os.path.dirname(os.path.abspath(__file__))` to locate the script's
own folder first, then join `../database/erp_demo.db` onto that — making
the script work correctly regardless of the current working directory it's
launched from, while still avoiding any machine-specific hardcoded
absolute path. The only remaining assumption is that `scripts/` and
`database/` stay sibling folders, which is already the repo's fixed
structure.

**One application, one schema — demo and personal use differ only in starting data**
Rather than building separate "demo mode" and "production mode" logic
into the backend, the plan is a single application that works identically
against any database file. `erp_demo.db` starts pre-seeded with the full
232+ transaction dataset for portfolio visitors to explore and add to; a
second database file (to be created) starts with only the schema and
chart of accounts, empty otherwise, for genuine personal use. Which file
the backend talks to is selected via a `DB_PATH` environment variable, so
the application code itself never needs to know or care which one it's
connected to.

**Chart of accounts uses soft-delete (`is_active`), never a hard delete, once used**
Deleting an account that already appears in `journal_entry_line` would
break historical postings — they'd reference an account that no longer
exists. Following standard accounting-system practice, an account already
in use can only be deactivated (`is_active = 0`), preventing it from being
selected for new postings while leaving all historical entries intact. A
true hard delete is only permitted for an account that has never been
used in any posting. This is a general rule for the project going
forward: wherever a technical shortcut and an accounting standard
conflict, the accounting standard wins.

**Backend switched from Node.js/Express to Python/FastAPI mid-project**
The original Express implementation was working correctly (first
endpoint live, tested), but the decision was made to switch to
Python/FastAPI to align with the technology stack of a larger, related
personal project (LES), so backend skills built here transfer directly
rather than needing to be relearned in a different language later. The
superseded Node/Express code was renamed to `backend-node-exploration/`
rather than deleted — it remains a documented, visible record of a
deliberate technology choice, not a discarded false start.

**Fiscal year additions are a manual, user-triggered script, never automatic**
`scripts/start_new_fiscal_year.py` must be run explicitly by the person
maintaining the database; nothing in the application checks the current
date and silently creates a new year on its own. A fiscal year-end is a
conscious, controlled event in real accounting practice, and the schema's
composite primary key on `fiscal_calendar` already supports this without
any automatic mechanism being necessary.

**A single `CURRENT_YEAR` constant instead of hardcoding the year throughout**
`generate_data.py` originally had the literal year typed in dozens of
places (table names, invoice number formats, journal entry dates).
Replaced with one constant at the top of the script that everything else
reads from, and a `random_date(year)` function taking the year as a
parameter instead of having a specific year in its name. This is a
general pattern worth repeating in future projects: any value repeated
more than a couple of times in a script is a candidate for a single named
constant.

**Reporting views use `julianday('now')`, not a fixed reference date**
`v_ar_aging`/`v_ap_aging` originally used a hardcoded `'2025-12-15'` so
that demo screenshots and worked examples would always show the same,
reproducible ageing buckets regardless of when the query was actually
run. That was correct for a single-year, screenshot-driven demo, but
wrong for the database's intended ongoing personal use, where "how many
days overdue" must always be measured against the real, current date.
Switched to SQLite's built-in `'now'` keyword once genuine multi-year use
became the actual goal, not just a demo.
