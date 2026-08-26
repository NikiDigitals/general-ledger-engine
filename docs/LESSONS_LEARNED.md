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

##Python##

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
