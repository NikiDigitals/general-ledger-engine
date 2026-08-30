import Database from "better-sqlite3";

const db = new Database("../database/erp_demo.db");

const accounts = db
  .prepare("SELECT account_code, account_name FROM chart_of_accounts")
  .all();

console.log(accounts);

db.close();
