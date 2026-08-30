# General Ledger Engine

A general ledger from start to end built from scratch, covering Order-to-Cash,
Procure-to-Pay, and Record-to-Report, with double-entry bookkeeping
enforced at the database level. No posting can ever be unbalanced.

This is a learning-by-building project: every table, view, and later every
line of application code is written from first principles, with each
design decision and mistake documented along the way.

## Current status

The database layer is complete: 17 tables covering the full O2C, P2P, and
R2R cycles, all built in SQLite. Six reporting views are in place (trial
balance, AR/AP ageing, income statement, close status, budget vs actual).
The Python data generator is now feature-complete: it rebuilds the entire
schema from scratch and seeds a realistic single-year demo dataset —
20 customers, 15 products, 12 vendors, 150 sales orders and 100 purchase
orders spread across the full year, with realistic invoiced/paid ratios
(leaving open invoices for AR/AP ageing) — all through controlled
randomness (`random.seed(42)`, so every run produces the same dataset).
See [`docs/MILESTONES.md`](docs/MILESTONES.md) for the up-to-date
progress log, or [`docs/JOURNAL.md`](docs/JOURNAL.md) for the full story
behind each phase.

**Not yet built:** the backend API, the frontend, and deployment. See the
roadmap below.

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
├── database/
│   └── erp_demo.db                          # The SQLite database itself
├── scripts/
│   ├── rebuild_database_sql.md              # Every CREATE TABLE / VIEW statement, runnable top to bottom
│   ├── generate_data.py                     # Python data generator (feature-complete)
│   └── data_generator_python_explained.md   # The same script, section by section, with commentary
├── diagrams/
│   └── ERD.md                               # Entity-relationship diagram (Mermaid)
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

Three resources, kept in sync with each other:

- **SQL, step by step**: [`scripts/rebuild_database_sql.md`](scripts/rebuild_database_sql.md)
  — open it, copy each SQL block in order into DB Browser for SQLite's
  Execute SQL tab (or any SQLite client), and run top to bottom. Produces
  a small, fixed test dataset — useful for understanding the schema
  without any randomness involved.
- **Python, one command**: `scripts/generate_data.py` — rebuilds all 17
  tables and seeds a full, realistic single-year dataset with a single
  run (232+ transactions across O2C and P2P, an opening capital entry,
  and COGS/inventory postings on every sale). Reproducible: the same seed
  produces the same dataset every time.
- **Python, explained**: [`scripts/data_generator_python_explained.md`](scripts/data_generator_python_explained.md)
  — the same script broken into sections, with commentary on every new
  Python concept as it's introduced (loops, `enumerate`, tuple unpacking,
  dictionaries, `cursor.lastrowid`, parameterised queries, the `random`
  module, and date arithmetic).

> **Path note:** `generate_data.py` locates the database relative to its
> own file location (via Python's `__file__`), not relative to whatever
> folder you happen to run it from — so it works correctly whether it's
> launched from inside `scripts/`, from the repo root, or via an absolute
> path. The one assumption that remains is that `scripts/` and
> `database/` stay siblings (next to each other), which is already the
> repo's fixed folder structure.

## Roadmap

- [x] Database schema (17 tables, O2C + P2P + R2R)
- [x] Reporting views (trial balance, ageing, income statement, budget vs actual)
- [x] Python data generator — feature-complete realistic single-year dataset
- [ ] Backend API (Node/Express)
- [ ] Frontend (React)
- [ ] Deployment (Azure)
- [ ] Portfolio site write-up

## License

MIT — see [`LICENSE`](LICENSE).
