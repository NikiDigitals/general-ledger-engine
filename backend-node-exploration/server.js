// Express server exposing the ERP database over HTTP.
// This is the first REST API for the project — it reads directly from
// erp_demo.db using the same database that Python and SQL both use.

import express from "express";
import Database from "better-sqlite3";

const app = express();
const db = new Database("../database/erp_demo.db");
const PORT = 4000;

// GET /api/accounts — returns the full chart of accounts as JSON.
app.get("/api/accounts", (req, res) => {
  const accounts = db.prepare("SELECT * FROM chart_of_accounts").all();
  res.json(accounts);
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
