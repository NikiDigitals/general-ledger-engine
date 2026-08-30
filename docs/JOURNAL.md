# Build Journal

Narrative log of the project, organised by roadmap phase rather than by
session. Where `MILESTONES.md` states _what_ was completed, this journal
tells the story of _how_ it happened: the reasoning, the mistakes, the
moments something clicked. Each section is updated as that phase
progresses, so a phase may span several sessions before its story is
complete.

---

## 1. Database schema (17 tables, O2C + P2P + R2R)

**Status: complete.**

The project started with a single question: what's the simplest table
needed before anything else can exist? The answer was `chart_of_accounts`.
Every other table eventually points back to it, directly or indirectly.

From there, the build followed the natural dependency order: the chart of
accounts, then the General Ledger core (`journal_entry` and
`journal_entry_line`), then the fiscal calendar, then the full
Order-to-Cash chain (customer, product, sales order, AR invoice, cash
receipt), then its mirror image, Procure-to-Pay (vendor, purchase order,
AP invoice, vendor payment), and finally the Record-to-Report support
tables (close checklist, budget line).

By the end, both cycles had been walked through by hand. A real order,
turned into a real invoice, turned into a real posting, turned into a real
payment. Every step verified against the database rather than assumed
correct. Along the way came a string of very typical early-SQL mistakes:
smart quotes instead of straight quotes, `FOREIGN KEY` written inside a
column definition instead of as its own line, mismatched brackets, a
case-sensitivity surprise on a `UNIQUE` constraint. None of these were
conceptual failures. They were precision failures, and fixing each one
built the habit of reading a `CREATE TABLE` statement line by line rather
than skimming it.

**Key realisation:** double-entry bookkeeping stops being an abstract
accounting rule once you've watched a database physically refuse to save
an unbalanced entry. The CHECK constraint on `journal_entry_line` did more
to explain _why_ debits must equal credits than any textbook definition
could.

---

## 2. Reporting views (trial balance, ageing, income statement, budget vs actual)

**Status: complete.**

Six views were built in sequence, each introducing one new SQL concept on
top of the last: `v_trial_balance` (JOIN, GROUP BY, SUM, and a CASE WHEN
to correctly normalise Debit vs Credit balances), `v_ar_aging` and
`v_ap_aging` (date arithmetic with `julianday()` and a multi-branch CASE
WHEN for ageing buckets), `v_income_statement` (conditional aggregation
without a GROUP BY, to produce a single summary row), `v_close_status`
(COUNT and a 1-or-0 SUM pattern for percentage calculations), and finally
`v_budget_vs_actual`. This was the most complex one of the six, requiring
a correlated subquery to compare each budget line against its matching
actual postings.

That last view also exposed a design gap: `journal_entry` had never been
given `fiscal_year`/`fiscal_period` columns, because the original design
only anticipated filtering by `entry_date`. Rather than a sign of bad
planning, this was a natural consequence of not yet knowing what later
reporting would need. The columns were added retroactively with `ALTER
TABLE`, then backfilled from existing dates using `strftime()`.

The trial balance view earned its keep almost immediately: it surfaced a
real data bug. A missing pair of journal entry lines from an earlier
manual entry, that would otherwise have gone unnoticed. That single
moment was probably the clearest demonstration of _why_ reporting and
database constraints matter, not just how to write them.

**Key realisation:** a view can be syntactically perfect and still be
substantively wrong if it queries the wrong table or omits a filter. SQL
checks your grammar, never your intent. Building `v_ap_aging` by adapting
a copy of `v_ar_aging` and forgetting to change `FROM ar_invoice` to `FROM
ap_invoice` proved that directly.

---

## 3. Python data generator (realistic multi-month transaction volume)

**Status: complete.**

The move from typing SQL by hand to writing Python that generates the
schema and data programmatically marked the first real step toward a
repeatable, one-command rebuild instead of a manually maintained database.

The rebuild also became an opportunity to fix the `fiscal_year`/
`fiscal_period` gap properly: instead of the `ALTER TABLE` patch used
during manual SQL work, the Python version includes those columns
directly in the original `CREATE TABLE journal_entry` statement — the kind
of small correction that only becomes obvious once you're rebuilding
something from scratch a second time.

The build proceeded table by table, in the same dependency order as the
original SQL work: chart of accounts, General Ledger, a full 12-month
fiscal calendar (generated with a single `for` loop instead of twelve
manual inserts), customers, and products. Parameterised queries (`?`
placeholders instead of building SQL strings by hand) were established as
a non-negotiable habit from the very first `INSERT`.

The Order-to-Cash chain came next, and this is where the generator earned
its keep: `cursor.lastrowid` was introduced to capture a newly created
row's ID for use in its child rows (an order's ID for its lines, an
invoice's ID for its posting), first walked through by hand for a single
record, then generalised into a full loop that creates five orders, turns
each into an invoice with a balanced GL posting, and registers a matching
cash receipt that closes it out — the first time this project generated
GL-correct transactions without a single manual `INSERT`.

Procure-to-Pay followed as a near-literal mirror of O2C — vendor, purchase
order, AP invoice, vendor payment — and went noticeably faster, since the
pattern was already familiar. One `IndentationError` came up while adding
new lines inside an existing loop and was self-diagnosed and fixed before
asking for help, a good sign the underlying pattern had actually sunk in
rather than just being copied. The two Record-to-Report support tables,
`close_checklist` and `budget_line`, closed out all 17 tables — the first
time the full schema existed entirely as Python-generated code.

Running `v_trial_balance` against the freshly generated data produced a
useful surprise: Accounts Receivable and Accounts Payable both netted
correctly to zero, proving both cycles close properly, but Inventory sat
at a positive balance and Cash was negative. Neither was a bug — every
individual posting was still perfectly balanced — but it revealed that the
generator, unlike the original hand-written SQL version, never posted a
COGS/inventory reduction on the sale side and never recorded an opening
capital injection. Both gaps were logged as TODOs directly in the script
rather than fixed immediately, a deliberate choice to keep that milestone
scoped to "the structure works" before layering in the missing posting
types.

Both TODOs were resolved next. An opening capital entry
(`Dr Cash / Cr Common Stock`) was added right after the GL tables are
created, funding the business before any other transaction is posted.
Every AR invoice's posting loop gained a second pair of lines
(`Dr COGS / Cr Inventory`, using a simplified flat percentage of sale
price), so a sale now correctly reduces Inventory instead of leaving it
to only ever grow via purchases. Re-running the trial balance afterwards
showed exactly the expected shift: Common Stock appeared with the funded
amount, Cash moved from negative to a realistic positive balance, and the
whole ledger still balanced to zero.

With both gaps closed, the scale-up itself began — this is where
`random` entered the project for the first time. `random.seed(42)` was
set immediately, before anything else, to guarantee the same "random"
dataset every run: a deliberate choice to keep debugging and screenshots
reproducible rather than chasing a moving target. Customers and products
were the first to scale, generated by randomly combining name-parts
(prefix + type) instead of hand-typing each one — 5 customers became 20,
5 products became 15, with product prices now derived from a randomised
markup over cost so no product is ever priced below what it cost to make.

Sales orders were the real test: 150 orders, each assigned a random
customer, product, quantity, and order date via a purpose-built
`random_date_2025()` helper function — the first custom function written
in this project, and the first use of `timedelta` for date arithmetic.
Rather than guessing prices, each order now looks its product's real
price up live from the database with a `SELECT` inside the generation
loop — the first time the script both read and wrote within the same
operation, mirroring what a real application does constantly.

Turning orders into invoices, and invoices into receipts, needed a
different shape of loop: instead of a fixed count, the script now queries
every existing sales order, and for each one uses `random.random()`
against a threshold (roughly 80%) with `continue` to skip the rest —
deliberately leaving a portion of orders un-invoiced, and a portion of
invoices unpaid, so the resulting dataset would have genuinely open items
for AR ageing to report on, not just paid-in-full records. A list built
during the invoicing step (`ar_invoice_ids`) was carried over and reused
in the receipts step immediately after, avoiding a second, redundant
database query to re-discover which invoices exist.

This is also where a pair of very informative `NameError` crashes showed
up — `invoice_amounts` and `vendor_ids` no longer existed once their
sections were rewritten, because the *next* section down still referenced
the old, fixed-list approach. Both were fixed the same way: recognising
that scaling up one step of a pipeline breaks whichever step downstream
still assumes the old shape of the data, and updating that step to match
before moving on.

Procure-to-Pay was scaled up as a direct mirror of this pattern —
12 vendors, 100 purchase orders, the same live-price-lookup and
random-date approach, then AP invoices and vendor payments using the same
random-threshold-with-`continue` technique. By the end, the generator
produced 232+ transactions across both cycles (150 sales orders / 124
invoiced / 92 paid; 100 purchase orders / 82 invoiced / 60 paid), and a
final balance check — `SUM(debit) - SUM(credit)` across the entire
`journal_entry_line` table — still returned exactly zero.

**Key realisation:** a for-loop turns a dozen error-prone manual steps
into one correct one, but it also means a booking mistake — like a
missing posting type — now repeats consistently instead of varying by
accident. Reporting caught the gap immediately precisely because every
record was generated the same, deliberate way. The distinction that
crystallised here: "the books balance" is a guarantee the database
enforces on every single posting; "the books are complete" depends on
whether every transaction type the business actually needs has been
implemented yet. Both are now true — and the reproducible seed means that
claim can be checked again at any time by simply re-running the script
and reading the same balance check.

---

## 4. Backend API (Node/Express)

**Status: in progress.**

This phase opened with a first, deliberate installation: Node.js itself,
followed by `npm init` to create the project and `npm install express` /
`npm install better-sqlite3` to bring in a web framework and a database
driver. A short side-by-side comparison with the Python data generator
made the parallels immediately visible — `sqlite3.connect()` and
`Database()`, `cursor.execute()` and `db.prepare()`, `cursor.fetchall()`
and `.all()` — different syntax, the same underlying idea, which made a
first test script (`test-connection.js`) fast to write and understand: it
read the same chart of accounts already familiar from every other layer
of this project, just from a third language now.

The real shift came with `server.js`. Unlike every Python or SQL script
so far — which runs once, does something, and stops — a server is built
to keep running indefinitely, listening for requests rather than
executing top to bottom once. `app.get("/api/accounts", ...)` defined the
first *route*: a standing instruction for what to do whenever a request
arrives at that specific address. A couple of small, very typical
first-server mistakes came up along the way — a missing leading `/` in
the route path, and using single quotes instead of backticks around a
template string with `${PORT}` inside it — both fixed by reading the
error output and the code side by side rather than guessing.

Starting the server and opening `http://localhost:4000/api/accounts` in
a browser produced the same seven accounts already seen dozens of times
via DB Browser, Python, and raw SQL — but this time retrieved over an
actual HTTP request, the same mechanism a real frontend (or anyone else
on the internet, once deployed) will use. That moment marked the first
time this project's data became reachable by something other than a
script or tool running directly on the same machine.

The session closed with a repository-hygiene fix: the project had never
had a `.gitignore`, so `node_modules` — hundreds of files, all of them
regenerable with a single `npm install` — had been committed to GitHub
along with the real backend code. A project-wide `.gitignore` was added
covering Node, Python, editor, and OS clutter, and `node_modules` was
removed from Git's tracking with `git rm -r --cached`, without touching
the actual files on disk.

Two decisions were made explicit before writing any further routes:
first, that the eventual application will use one schema and one
codebase for both a portfolio demo (pre-seeded `erp_demo.db`) and genuine
personal use (a second, empty database file), switched via an
environment variable rather than separate "modes" in the code; second,
and more fundamentally, that wherever a technical shortcut and an
accounting standard conflict for the rest of this project, the accounting
standard wins — starting with `chart_of_accounts`, which will support
soft-delete for any account already used in a posting, never a hard
delete that could orphan historical entries.

**Key realisation:** a server is a genuinely different kind of program
from anything built so far in this project — not "a script that talks to
a database," but "a standing service that waits to be asked something."
Everything from the database schema through the Python generator existed
to be *run*; the backend exists to *stay running*. That distinction is
also why the very first successful browser request felt disproportionately
significant for how small the endpoint actually was: it was the first
time the project's data left the boundary of "something explored on this
one machine" and became reachable the way real applications are reached.

_(To be continued: routes for customers, vendors, orders, invoices, and
reporting views; full CRUD with the accounting-standard soft-delete rule
in place; and — eventually — the balance guarantee enforced again at the
application layer as a second line of defence alongside the database
CHECK constraint.)_

---

## 5. Frontend (React)

**Status: not started.**

_(This section will cover the first UI screens, the jump
to a working interface, and the point where the
project stops being something only explorable via a database browser or
API client.)_

---

## 6. Deployment (Azure)

**Status: not started.**

_(This section will document getting the backend onto Azure App Service
and the frontend onto Azure Static Web Apps — the first time the project
is reachable by anyone other than its author.)_

---

## 7. Portfolio site write-up

**Status: not started.**

_(This section will describe turning the finished project into a
portfolio piece: what got highlighted, what got left out, and how the
story of building it from scratch was told to an audience that never saw
any of the mistakes along the way.)_
