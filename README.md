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
A Python data generator now rebuilds the entire schema and a small test
dataset programmatically in a single run — the next step is scaling that
up to hundreds of realistic, randomised transactions across multiple
months. See [`docs/MILESTONES.md`](docs/MILESTONES.md) for the up-to-date
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
│   └── erp_demo.db                # The SQLite database itself
├── scripts/
│   ├── Database-SQL.md            # Every CREATE TABLE / VIEW statement, runnable top to bottom
│   └── generate_data.py           # Python data generator (structure complete, scale-up in progress)
├── diagrams/
│   └── ERD.md                     # Entity-relationship diagram (Mermaid)
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

Two ways to rebuild the database, kept in sync with each other:

- **SQL, step by step**: [`scripts/Database-SQL.md`](scripts/Database-SQL.md)
  — open it, copy each SQL block in order into DB Browser for SQLite's
  Execute SQL tab (or any SQLite client), and run top to bottom.
- **Python, one command**: `scripts/generate_data.py` — rebuilds all 17
  tables (O2C, P2P, R2R) and seeds a small hand-picked test dataset in a
  single run. Known gaps (no COGS/inventory reduction on sale, no opening
  capital entry) are tracked as TODOs in the script itself, to be resolved
  as part of the upcoming scale-up to realistic, randomised transaction
  volume.

## Roadmap

- [x] Database schema (17 tables, O2C + P2P + R2R)
- [x] Reporting views (trial balance, ageing, income statement, budget vs actual)
- [ ] Python data generator — structure complete; realistic multi-month volume via randomisation still pending
- [ ] Backend API (Node/Express)
- [ ] Frontend (React)
- [ ] Deployment (Azure)
- [ ] Portfolio site write-up

## License

MIT — see [`LICENSE`](LICENSE).
