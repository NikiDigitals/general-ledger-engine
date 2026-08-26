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

**Status: core structure complete; scale-up in progress.**

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
rather than fixed immediately, a deliberate choice to keep the current
milestone scoped to "the structure works" before layering in the missing
posting types.

**Key realisation:** a for-loop turns a dozen error-prone manual steps
into one correct one, but it also means a booking mistake — like a
missing posting type — now repeats consistently instead of varying by
accident. Reporting caught the gap immediately precisely because every
record was generated the same, deliberate way. The distinction that
crystallised here: "the books balance" is a guarantee the database
enforces on every single posting; "the books are complete" depends on
whether every transaction type the business actually needs has been
implemented yet. The first was true from the start. The second isn't,
yet — and now there's a written, specific list of what's missing instead
of a vague sense that something might be.

_(To be continued: adding the missing COGS/inventory and opening capital
postings, then scaling the fixed 5-record dataset up to hundreds of
transactions spread across multiple months using controlled randomness.)_

---

## 4. Backend API (Node/Express)

**Status: not started.**

_(This section will describe how the database gets exposed over HTTP —
the first time the project becomes something other than a local database
file. Expect topics like REST route design, how the balance guarantee
gets enforced in application code as a second line of defence, and the
first moment a request from outside SQLite successfully posts a
transaction.)_

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
