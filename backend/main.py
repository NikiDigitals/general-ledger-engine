from fastapi import FastAPI
import sqlite3
import os

app = FastAPI()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "database", "erp_demo.db")

@app.get("/api/accounts")
def get_accounts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM chart_of_accounts").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/journal-entry-columns")
def get_journal_entry_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    rows = cursor.execute("PRAGMA table_info(journal_entry)").fetchall()
    conn.close()
    return rows

@app.get("/api/fiscal-years")
def get_fiscal_years():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT DISTINCT fiscal_year FROM fiscal_calendar ORDER BY fiscal_year").fetchall()
    conn.close()
    return rows

@app.get("/api/account-balances")
def account_balances():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT coa.account_code, coa.account_name,
               SUM(jel.debit_amount) as total_debit,
               SUM(jel.credit_amount) as total_credit
        FROM journal_entry_line jel
        JOIN chart_of_accounts coa ON coa.account_id = jel.account_id
        GROUP BY coa.account_id
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]