# Lessons Learned

**"Smart quotes" (‘ ’) instead of straight quotes (')**
Caused by typing text in an app with autocorrect enabled (Word, Notes).
SQL only recognises straight quotes (`'`) as the string delimiter. →
Always type SQL directly in the SQL editor, never draft it in a word
processor first.

**UNIQUE is case-sensitive in SQLite**
`'CUST-001'` and `'Cust-001'` were treated as two different, and therefore
both permitted, values — the `UNIQUE` constraint blocked nothing. Lesson:
case-insensitive uniqueness must be requested explicitly with
`COLLATE NOCASE`; it does not happen automatically.

**FOREIGN KEY belongs on its own line, not inside a column definition**
Repeatedly wrote `FOREIGN KEY` inside a column line by mistake instead of
as a separate line after all columns, using the syntax
`FOREIGN KEY (local_column) REFERENCES other_table(column_there)`.

**Counting brackets and commas**
The most common syntax error was a missing closing bracket at the end of a
`CREATE TABLE` statement, or a trailing comma after the last column/line.
Lesson: after typing a table, explicitly count opening and closing
brackets, and check that the final line before `)` has no comma.

**AUTOINCREMENT requires PRIMARY KEY**
Cannot be used on its own as a standalone keyword in SQLite — always
`INTEGER PRIMARY KEY AUTOINCREMENT` together, never `INTEGER AUTOINCREMENT`
without `PRIMARY KEY`.

**`==` vs `=`, and `=>`/`=<` vs `>=`/`<=`**
Comparison operators from programming languages (JavaScript/Python) are
not all valid in SQL. SQL uses a single `=` for equality, and `>=`/`<=`
(not reversed) for greater-than-or-equal/less-than-or-equal. For ranges,
`BETWEEN x AND y` is more readable than two separate comparisons.

**Copying a previous table as a starting point is error-prone**
When adapting a copied `CREATE TABLE` (e.g. `ar_invoice` → `cash_receipt`),
mistakes from the previous table easily carry over (wrong data type, wrong
constraint left in place). Lesson: re-read every column line as if seeing
it for the first time, rather than assuming a copied line is already
correct.

**Tracking milestones too granularly loses the overview**
Logging every individually created table as its own milestone produces a
long, low-value list. Better: a milestone is a complete, working piece of
functionality (e.g. "the entire O2C cycle works end-to-end"), not an
individual build step.

**A missing journal entry line is invisible until you build reporting**
A cash receipt's posting header existed, but its two lines were never
inserted. The gap stayed unnoticed until the trial balance query surfaced
an account with only a debit side and no matching credit — proof that
reporting queries double as a data-integrity check.

**A view can reference columns that don't exist yet in an earlier design**
`journal_entry` was originally built without `fiscal_year`/`fiscal_period`
columns. A later view (`v_budget_vs_actual`) assumed they existed, causing
a "no such column" error. Fixed retroactively with `ALTER TABLE ADD COLUMN`
plus a `strftime()`-based UPDATE to backfill existing rows. Lesson: as a
schema grows, earlier tables sometimes need columns that only become
necessary once a later feature is designed — this is normal, not a sign of
bad initial design.

## Python

**Windows redirects `python` to the Microsoft Store by default**
Even with Python properly installed, typing `python` in PowerShell can
trigger a fake "not found, install from Store" message due to Windows'
App Execution Aliases feature. The Python Launcher (`py`) bypasses this
and works directly — use `py` instead of `python` for all commands in this
project on Windows.

**Every tuple in a list needs its own complete set of parentheses**
When building a list of tuples like `[("Top", 5.00, 9.99), ("T-shirt", ...)]`,
each individual item must be fully wrapped in its own `(...)` — a common
mistake is to open the first tuple correctly but drop the opening
parenthesis on subsequent lines, leaving a stray closing bracket with
nothing to match.

**A column name must sit inside the same parentheses as the others**
`INSERT INTO product (sku, product_name, ...)` — every column being
inserted belongs inside one shared set of parentheses. Writing
`INSERT INTO product sku, (product_name, ...)` separates one column out,
which SQL cannot parse correctly.

**Python uses indentation, not brackets, to define code blocks**
Unlike SQL (where `()` define scope) or many other languages (where `{}`
do), Python determines what belongs inside a loop or function purely by
how far a line is indented. A single misaligned line — even by one space —
causes an `IndentationError`. This becomes especially easy to trigger when
manually adding lines to an existing loop, since every new line must match
the exact indentation of its neighbours.

**A "balanced" trial balance doesn't mean every account balance is meaningful yet**
After rebuilding O2C and P2P via Python, `v_trial_balance` showed AR and
AP correctly netting to zero (proof those two cycles close properly), but
Inventory showed a positive balance and Cash was negative. Neither was a
bug: the Python generator's O2C postings only recorded Dr AR / Cr Revenue
and never reduced Inventory or booked COGS on the sale side (unlike the
original hand-written SQL version, which did), and no opening capital
injection (Dr Cash / Cr Common Stock) was ever posted. Every individual
posting was still perfectly balanced — the CHECK constraint guarantees
that — but the *overall* picture across accounts only makes full business
sense once every intended posting type actually exists. Lesson: "the
books balance" and "the books are complete" are two different claims: the
first is guaranteed by the database, the second depends on whether every
transaction type the business model needs has actually been implemented.

**A fixed random seed makes "random" reproducible**
`random.seed(42)`, set once at the very top of the script before anything
else runs, guarantees the exact same sequence of "random" values on every
run. Without it, a bug that shows up once could vanish on the next run
simply because different random values happened to be drawn — making it
impossible to reliably reproduce or verify a fix. The seed value itself
is arbitrary; what matters is setting one at all.

**Scaling up one step of a pipeline can silently break the next step**
After rewriting the sales-order generation loop to use randomised data
instead of a fixed 5-item list, the very next section (`ar_invoice`)
crashed with `NameError: name 'invoice_amounts' is not defined` — that
variable only existed in the old, fixed-list version, and the invoice
section still expected it. The same happened again one step later with
`vendor_ids`. Lesson: when scaling up or rewriting one stage of a
multi-stage script, check every later stage that reads variables the
rewritten stage used to produce — the error often won't appear until
Python actually reaches that later code.

**`random.random() > threshold` combined with `continue` is a clean way to skip items probabilistically**
To leave ~20% of sales orders un-invoiced (so AR ageing has real open
items to report on), each order is checked with
`if random.random() > 0.8: continue` — `random.random()` returns a value
between 0.0 and 1.0, so roughly 80% of values fall at or below 0.8 and
proceed, while the rest skip immediately to the next loop iteration.
`continue` (rather than wrapping the rest of the loop body in an `if`)
keeps the "normal path" code unindented and easy to read.

**Building a list during one loop, then reusing it in the next, avoids a redundant query**
While generating AR invoices, each new invoice's ID, customer, amount, and
date were appended to a plain Python list (`ar_invoice_ids`). The next
step (generating cash receipts) then looped directly over that list
instead of running a fresh `SELECT` to rediscover which invoices exist —
simpler, and guarantees the two steps stay perfectly in sync with exactly
the invoices just created in this run.

**`date.fromisoformat()` and `.isoformat()` are inverses**
SQLite stores dates as plain text (e.g. `"2025-03-15"`). To do arithmetic
on a date read back from the database (like adding a payment delay with
`timedelta`), it first needs converting from that text into a real
`date` object with `date.fromisoformat(text)`; the reverse,
`some_date.isoformat()`, converts a `date` object back into the exact
text format SQLite expects for storage.

**A relative path assumes a specific working directory — `__file__` doesn't**
`DB_PATH = "../database/erp_demo.db"` only resolves correctly if the
script happens to be launched from inside `scripts/`. That's an easy
assumption to get wrong, especially for anyone else cloning the repo and
running the script from a different folder. Building the path from the
script's own location instead —
`os.path.dirname(os.path.abspath(__file__))` joined with the relative
folders — makes the script work correctly no matter which directory it's
launched from, while still avoiding a machine-specific hardcoded absolute
path.

## Node.js / Express

**Express routes need a leading `/`**
`app.get("api/accounts", ...)` does not register as a valid route path —
it must be `app.get("/api/accounts", ...)`. Without the leading slash,
Express does not treat the string as a proper path, and a request to
that endpoint fails.

**Template literals need backticks, not quotes**
`` `text ${variable}` `` only interpolates the variable when wrapped in
backticks. The same string wrapped in single or double quotes —
`'text ${variable}'` — is treated as plain text, and prints the literal
characters `${variable}` instead of its value. Backticks and quotes look
similar at a glance, especially on a US keyboard where backtick sits
top-left near Escape, but they are not interchangeable in JavaScript.

**A server is a fundamentally different kind of program from a script**
Every Python and SQL script in this project so far runs once, does
something, and exits. `app.listen(PORT, ...)` never returns — the process
stays alive indefinitely, waiting for incoming requests, until manually
stopped (Ctrl+C). This is the core mechanical difference between "a
script that talks to a database" and "a backend."

**No `.gitignore` from the start meant `node_modules` got committed**
The project had gone all the way from database schema through the Python
generator without ever needing a `.gitignore`, since none of those layers
produced generated, regenerable folders. The moment `npm install`
introduced `node_modules` (hundreds of files, fully reproducible from
`package.json` alone), the absence of a `.gitignore` meant all of it got
committed to GitHub. Fixed with a project-wide `.gitignore` plus
`git rm -r --cached node_modules` to remove it from tracking without
touching the files on disk. Lesson: add a `.gitignore` at the very start
of a repository, before the first tool that generates a regenerable
folder is introduced, rather than retrofitting one after the fact.
