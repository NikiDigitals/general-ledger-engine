import sqlite3

conn = sqlite3.connect("../database/erp_demo.db")
cursor = conn.cursor()

cursor.execute("SELECT account_code, account_name FROM chart_of_accounts")
results = cursor.fetchall()

for row in results:
    print(row)

conn.close()