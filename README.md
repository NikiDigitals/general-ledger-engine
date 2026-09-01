# General Ledger Engine

A general ledger from start to end built from scratch, covering Order-to-Cash,
Procure-to-Pay, and Record-to-Report, with double-entry bookkeeping
enforced at the database level. No posting can ever be unbalanced.

This is a learning-by-building project: every table, view, and later every
line of application code is written from first principles, with each
design decision and mistake documented along the way.

## Current status

The database layer is complete: 17 tables covering the full O2C, P2P, and
R2R cycles, all built in SQLite, now extended to support reversals
(`journal_entry.reverses_journal_entry_id`), invoice write-offs
(`ar_invoice.status`), discount postings (`Sales Discounts` and
`Bad Debt Expense` accounts), and multiple fiscal years
(`fiscal_calendar` currently covers 2025–2026, extendable on demand via
`scripts/start_new_fiscal_year.py`). Six reporting views are in place
(trial balance, AR/AP ageing — now measured against the real current
date, not a fixed one — income statement, close status, budget vs
actual). The Python data generator is feature-complete and
year-independent, seeding a realistic dataset of 232+ transactions driven
entirely by a single `CURRENT_YEAR` setting.

A Python/FastAPI backend is under active development, exposing the
database over HTTP. An earlier Node.js/Express version is preserved in
`backend-node-exploration/` — see
[`docs/DECISIONS.md`](docs/DECISIONS.md) for why the project moved to
Python/FastAPI. See [`docs/MILESTONES.md`](docs/MILESTONES.md) for the
up-to-date progress log, or [`docs/JOURNAL.md`](docs/JOURNAL.md) for the
full story behind each phase.

**Not yet built:** the React frontend and deployment. See the roadmap
below.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — design overview and reporting layer
- [Build Journal](docs/JOURNAL.md) — the story of how this was built, phase by phase
- [Milestones](docs/MILESTONES.md) — progress log, one entry per completed capability
- [Decisions](docs/DECISIONS.md) — why things were built the way they were
- [Lessons Learned](docs/LESSONS_LEARNED.md) — mistakes made and what they taught
- [ERD](diagrams/ERD.md) — entity-relationship diagram (Mermaid)

## Repository structure

```
.
├── .gitignore
├── LICENSE
├── database/
│   └── erp_demo.db                            # The SQLite database itself
├── scripts/
│   ├── rebuild_database_sql.md                # Every CREATE TABLE / VIEW statement, runnable top to bottom
│   ├── generate_data.py                       # Python data generator (feature-complete, year-independent)
│   ├── data_generator_python_explained.md     # The same script, section by section, with commentary
│   ├── start_new_fiscal_year.py               # Manual, user-triggered script to add a new fiscal year
│   └── start_new_fiscal_year_explained.md     # That script, explained section by section
├── backend-node-exploration/                  # Superseded Node.js/Express attempt, kept for the record
├── backend/                                   # Active Python/FastAPI backend (in progress)
├── diagrams/
│   └── ERD.md                                 # Entity-relationship diagram (Mermaid)
└── docs/
    ├── ARCHITECTURE.md            # Design overview
    ├── JOURNAL.md                 # Narrative build log, by roadmap phase
    ├── MILESTONES.md              # Progress log, one entry per completed capability
    ├── DECISIONS.md               # Why things were built the way they were
    └── LESSONS_LEARNED.md         # Mistakes made and what they taught
```

## Design principle

The General Ledger (`journal_entry` + `journal_entry_line`) is the single
source of truth. Every sub-ledger transaction — an invoice, a receipt, a
payment — generates a posting there, and a CHECK constraint makes it
physically impossible to write an unbalanced entry (debit must equal
credit, enforced by the database, not by application code).

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design
rationale, and [`diagrams/ERD.md`](diagrams/ERD.md) for the table
relationships.

## Rebuilding the database from scratch

Four resources, kept in sync with each other:

- **SQL, step by step**: [`scripts/rebuild_database_sql.md`](scripts/rebuild_database_sql.md)
  — open it, copy each SQL block in order into DB Browser for SQLite's
  Execute SQL tab (or any SQLite client), and run top to bottom. Produces
  a small, fixed test dataset — useful for understanding the schema
  without any randomness involved.
- **Python, one command**: `scripts/generate_data.py` — rebuilds all 17
  tables and seeds a full, realistic single-year dataset with a single
  run (232+ transactions across O2C and P2P, an opening capital entry,
  and COGS/inventory postings on every sale). Reproducible: the same seed
  produces the same dataset every time. Year-independent — change the
  `CURRENT_YEAR` constant at the top of the script to generate a
  different year.
- **Python, explained**: [`scripts/data_generator_python_explained.md`](scripts/data_generator_python_explained.md)
  — the same script broken into sections, with commentary on every new
  Python concept as it's introduced (loops, `enumerate`, tuple unpacking,
  dictionaries, `cursor.lastrowid`, parameterised queries, the `random`
  module, date arithmetic, and leap-year-safe month handling via
  `calendar.monthrange`).
- **Adding a new fiscal year**: `scripts/start_new_fiscal_year.py` —
  a small, deliberately manual script that extends `fiscal_calendar` by
  one more year without touching or resetting any existing data. See
  [`scripts/start_new_fiscal_year_explained.md`](scripts/start_new_fiscal_year_explained.md).

> **Path note:** both `generate_data.py` and `start_new_fiscal_year.py`
> locate the database relative to their own file location (via Python's
> `__file__`), not relative to whatever folder you happen to run them
> from — so they work correctly whether launched from inside `scripts/`,
> from the repo root, or via an absolute path. The one assumption that
> remains is that `scripts/` and `database/` stay siblings (next to each
> other), which is already the repo's fixed folder structure.

## Running the backend API

```bash
cd backend
py -m pip install fastapi uvicorn
py -m uvicorn main:app --reload
```

The server starts on `http://127.0.0.1:8000`. Currently exposes:

- `GET /api/accounts` — the full chart of accounts, as JSON

FastAPI also auto-generates interactive API docs — once the server is
running, visit `http://127.0.0.1:8000/docs` to see and try every endpoint
directly in the browser.

> An earlier Node.js/Express version of this backend is preserved in
> `backend-node-exploration/` — see [`docs/DECISIONS.md`](docs/DECISIONS.md)
> for why the project moved to Python/FastAPI.

More routes (customers, vendors, invoices, reporting views, reversals,
write-offs, discounts, and full create/update/delete operations) are
being added incrementally — see [`docs/JOURNAL.md`](docs/JOURNAL.md)
section 4 for progress.

## Roadmap

- [x] Database schema (17 tables, O2C + P2P + R2R), extended for
      reversals, write-offs, discounts, and multi-year support
- [x] Reporting views (trial balance, ageing measured against the live
      current date, income statement, budget vs actual)
- [x] Python data generator — feature-complete, year-independent
      realistic dataset
- [ ] Backend API (Python/FastAPI) — in progress
- [ ] Frontend (React)
- [ ] Deployment (Azure)
- [ ] Portfolio site write-up

## License

MIT — see [`LICENSE`](LICENSE).
