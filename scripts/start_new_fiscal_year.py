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
# Rather than asking the user to type in a year (error-prone: wrong
# year, or the same year run twice), the script finds the highest
# fiscal_year already present and adds 1. This is a deliberately
# manual, user-triggered script — but the year itself is never typed
# in by hand.

cursor.execute("SELECT MAX(fiscal_year) FROM fiscal_calendar")
current_max_year = cursor.fetchone()[0]
next_year = current_max_year + 1

# --- Safety check: refuse to duplicate an existing fiscal year ---
# fiscal_calendar has a composite PRIMARY KEY (fiscal_year, fiscal_period),
# so inserting an existing year would fail anyway — but with a cryptic
# SQLite error. This check fails early with a clear, human-readable
# message instead.

cursor.execute("SELECT COUNT(*) FROM fiscal_calendar WHERE fiscal_year = ?", (next_year,))
already_exists = cursor.fetchone()[0]

if already_exists > 0:
    raise ValueError(f"Fiscal year {next_year} already exists in fiscal_calendar. Aborting to avoid duplicate rows.")

# --- Insert all 12 periods for the new fiscal year ---
# calendar.monthrange() returns the correct number of days for each
# month in the given year, including leap-year February — no manual
# if/elif needed, unlike an earlier, hardcoded version of this logic.

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