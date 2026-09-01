# start_new_fiscal_year.py — Explained

A small, standalone, deliberately **manual** script: adding a new fiscal
year is a conscious decision a controller makes, not something that should
happen automatically in the background. Run it once, at the point you
actually want a new year available: `py .\start_new_fiscal_year.py` (from
inside `scripts/`).

---

## The full script

```python
import sqlite3
import os
import calendar

# Locate the database relative to this script's own folder, not the
# working directory it happens to be launched from — same pattern as
# generate_data.py.

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "database", "erp_demo.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- Determine the next fiscal year automatically ---

cursor.execute("SELECT MAX(fiscal_year) FROM fiscal_calendar")
current_max_year = cursor.fetchone()[0]
next_year = current_max_year + 1

# --- Safety check: refuse to duplicate an existing fiscal year ---

cursor.execute("SELECT COUNT(*) FROM fiscal_calendar WHERE fiscal_year = ?", (next_year,))
already_exists = cursor.fetchone()[0]

if already_exists > 0:
    raise ValueError(f"Fiscal year {next_year} already exists in fiscal_calendar. Aborting to avoid duplicate rows.")

# --- Insert all 12 periods for the new fiscal year ---

period_names = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]

for month in range(1, 13):
    period_name = period_names[month - 1]
    _, days_in_month = calendar.monthrange(next_year, month)
    start_date = f"{next_year}-{month:02d}-01"
    end_date = f"{next_year}-{month:02d}-{days_in_month:02d}"

    cursor.execute("""
        INSERT INTO fiscal_calendar (fiscal_year, fiscal_period, period_name, start_date, end_date)
        VALUES (?, ?, ?, ?, ?)
    """, (next_year, month, period_name, start_date, end_date))

# commit() writes the changes to disk — without it, they'd only exist
# in this script's memory and never actually reach the .db file.

conn.commit()
conn.close()

print(f"Fiscal year {next_year} added: 12 periods inserted into fiscal_calendar.")
```

---

## Concepts

- **`SELECT MAX(fiscal_year) FROM fiscal_calendar`** — instead of asking
  the person running the script to type in which year to add (error-prone:
  they could type the wrong year, or accidentally run it twice for the
  same year), the script determines the correct next year itself by
  finding the current highest year and adding 1. The script is still
  manually *triggered* — nothing runs automatically — but the year number
  itself is never typed by hand.

- **The safety check before inserting anything** — `fiscal_calendar`'s
  composite primary key `(fiscal_year, fiscal_period)` would already
  reject a duplicate year with a database error, but that error would be
  a fairly cryptic SQLite constraint message. Checking explicitly first
  with `SELECT COUNT(*) ... WHERE fiscal_year = ?` and raising a clear
  `ValueError` with a specific, human-readable message is better —
  whoever runs this script (very possibly a future version of the person
  who wrote it, months later, having forgotten the details) gets told
  exactly what went wrong and why, instead of having to decode a database
  error.

- **`raise ValueError(...)`** — a new concept: this stops the script
  immediately and prints the given message as an error, rather than
  letting execution continue (which could otherwise crash later, deeper
  in the script, with a much less clear error).

- **`calendar.monthrange(next_year, month)`** — see
  `data_generator_python_explained.md` section 4 for the full explanation;
  used identically here to correctly handle February in leap years without
  manual date-length logic.

---

## Why this is a separate script, not a function inside generate_data.py

`generate_data.py` is a full rebuild: it drops and recreates every table
from scratch, which is exactly what you want when setting up or resetting
the demo, but never what you want when the real, ongoing database already
has months of genuine transactions in it. `start_new_fiscal_year.py`
touches only `fiscal_calendar`, and only ever *adds* rows — it never drops
or rebuilds anything, making it safe to run against a database that
already contains real data worth keeping.

## What's next

This script only extends `fiscal_calendar` itself. No other table
automatically "knows" a new year exists until transactions are actually
posted into it — `journal_entry.fiscal_year`, `budget_line.fiscal_year`,
and `close_checklist.fiscal_year` are all populated per-transaction or
per-budget-line as those get created, not pre-filled for a whole year in
advance.
