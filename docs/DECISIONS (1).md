# Decisions

**SQLite instead of PostgreSQL during the build phase**
No server required, less friction while learning the fundamentals without
connection configuration. The schema is later portable 1-to-1 to
PostgreSQL (same DDL structure, different syntax details).

**journal_entry_id optional (nullable) on ar_invoice/cash_receipt**
Avoids a chicken-and-egg problem: the invoice row must exist first before
the corresponding posting can be created. The link is established
afterwards via an `UPDATE`, rather than being mandatory upfront.

**Balance enforced with a database CHECK, not application logic**
`CHECK ((debit > 0 AND credit = 0) OR (debit = 0 AND credit > 0))` on
`journal_entry_line`. This means no future application (or manual insert)
can ever write an unbalanced posting — the guarantee sits at the deepest
level, independent of how careful the application code happens to be.

**English accounting terminology (Debit/Credit, Cancelled) instead of Dutch**
Aligns with the standard language used in accounting software, code, and
APIs — avoiding a future mismatch between database values and application
code.

**Price captured on the order line, not only on the product**
`sales_order_line.unit_price` exists alongside `product.unit_price` so that
a historical order remains correct even if a product's standard price
changes later.

**Azure for deployment (instead of Vercel/Railway/other platforms)**
Account already exists, so fewer new platforms to learn. App Service
(backend) + Static Web Apps (frontend), both with a free tier — suitable
for a portfolio demo without monthly costs.
