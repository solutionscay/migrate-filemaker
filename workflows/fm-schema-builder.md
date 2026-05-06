# Schema Builder

Internal workflow for generating a production-ready SQL DDL schema from a FileMaker DDR spec export. Reads `ddr/specs/` tables, relationships, and value lists, then confirms key schema decisions before writing `migration/04_database_schema.sql`.

You are generating a production-ready database schema from a FileMaker DDR export. Your job is to read the extracted specs, understand the data model, present key decisions to the user for confirmation, and then write a clean, well-commented SQL DDL file.

**This is careful translation work.** The schema you produce is the foundation everything else is built on. Silent assumptions about naming, normalization, types, or dropped fields create debt that's hard to unwind later. Always present before you write.

---

## Step 1 — Check Prerequisites

Verify required inputs:

```bash
ls ddr/specs/01_tables.json ddr/specs/03_relationships.json ddr/specs/06_value_lists.json 2>/dev/null
```

```bash
ls migration/02_recommendations.md 2>/dev/null
```

If `ddr/specs/` is missing, stop:
> "ddr/specs/ not found. Run the DDR parser first with `/migrate-filemaker <path-to-ddr>`."

If `migration/02_recommendations.md` is missing, ask the user to confirm the target database (PostgreSQL, MySQL, or SQLite) before proceeding.

---

## Step 2 — Profile the Data Model

Extract a working profile of tables and relationships:

```bash
python3 -c "
import json
from collections import Counter

with open('ddr/specs/01_tables.json') as f:
    tables = json.load(f)

with open('ddr/specs/03_relationships.json') as f:
    rels = json.load(f)

with open('ddr/specs/06_value_lists.json') as f:
    vlists = json.load(f)

real_tables = [t for t in tables if t.get('fields')]
globals_only = [t for t in tables if not t.get('fields') and t.get('globals')]

repeating = []
containers = []
for t in real_tables:
    for f in t.get('fields', []):
        if f.get('repetitions', 1) > 1:
            repeating.append(f\"{t['name']}.{f['name']} ({f['repetitions']} reps)\")
        if f.get('field_type') == 'Container':
            containers.append(f\"{t['name']}.{f['name']}\")

print(f'Real tables: {len(real_tables)}')
for t in real_tables:
    print(f\"  {t['name']}: {len(t.get('fields', []))} schema fields, {len(t.get('calculated', []))} calculated, {len(t.get('globals', []))} globals\")
print(f'Globals-only tables: {len(globals_only)}')
for t in globals_only:
    print(f\"  {t['name']}: {len(t.get('globals', []))} globals\")
print(f'Relationships: {len(rels)}')
print(f'Value lists: {len(vlists)}')
print(f'Repeating fields: {len(repeating)}')
for r in repeating: print(f'  {r}')
print(f'Container fields: {len(containers)}')
for c in containers: print(f'  {c}')
"
```

Read `migration/02_recommendations.md` to confirm the target database and any architecture decisions that affect the schema.

Also read `migration/01_discovery_answers.md` if it exists — it may contain user guidance on globals classification or naming preferences from Discovery.

---

## Step 3 — Present Key Decisions and Wait for Confirmation

Before writing a single line of SQL, present the following to the user and wait for their response:

> "I'm ready to generate the database schema. Here's my plan — please confirm or redirect before I write the file.
>
> **Target database:** [PostgreSQL / MySQL / SQLite]
>
> **Tables to create ([N] total):**
> [List each real table with field count]
>
> **Tables to skip (globals-only):**
> [For each, propose a disposition:]
> - [TableName] — [N] globals → [proposed: app_settings rows / frontend session state / env variables]
>
> **Primary key strategy:** Serial integer (`id SERIAL PRIMARY KEY`). Say so if you need UUIDs — valid reasons: syncing across systems, external references, distributed writes.
>
> **Naming:** FM table names → lowercase `snake_case` plural. FM column names → lowercase `snake_case`. Prefixes like `tbl_`, `fk_`, `z_`, `_pk_` are stripped.
>
> **Repeating fields ([N] found):**
> [For each: proposed normalization as a child table, or separate columns if reps are few and semantically distinct]
>
> **Container fields ([N] found):**
> [List] → stored as `TEXT` (file path / URL). Binary data is not stored in the database.
>
> **Value lists — proposed strategy:**
> [For each: ENUM (short, stable), CHECK constraint (small, may evolve), or reference table (user-managed or long)]
>
> **Globals classification:**
> - Session/UI state (not in schema): [list] → frontend store / session
> - App settings (need a table): [list] → `app_settings` key-value table
>
> Anything to change before I generate?"

Incorporate all feedback, then proceed.

---

## Step 4 — Generate the SQL DDL

Consult [reference/schema-translation-guide.md](../reference/schema-translation-guide.md) for type mapping and naming rules.

Generate sections in this order:

### 4A. ENUM Types

For each value list classified as ENUM:
```sql
-- From value list: ValueListName
CREATE TYPE status_type AS ENUM ('Value1', 'Value2', ...);
```

### 4B. Reference Tables

For user-managed or long value lists:
```sql
-- From value list: ValueListName
CREATE TABLE statuses (
  id         SERIAL PRIMARY KEY,
  name       VARCHAR(100) NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL DEFAULT 0
);
```

### 4C. App Settings Table

If any globals were classified as app settings:
```sql
CREATE TABLE app_settings (
  key        VARCHAR(100) PRIMARY KEY,
  value      TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4D. Core Tables (dependency order — referenced tables first)

For each real table:
```sql
-- Source: FM table "OriginalTableName" (N records, N schema fields)
CREATE TABLE table_name (
  id         SERIAL PRIMARY KEY,
  -- columns from schema fields
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Type mapping rules:**
- FM Text → `TEXT` (or `VARCHAR(n)` if max-length validation existed)
- FM Number (integer/flag) → `INTEGER` or `BOOLEAN`
- FM Number (decimal/money) → `NUMERIC(p,s)`
- FM Date → `DATE`
- FM Time → `TIME`
- FM Timestamp → `TIMESTAMPTZ`
- FM Container → `TEXT` with comment: `-- file path reference; binary stored externally`
- Add `NOT NULL` for fields with "not empty" validation
- Add `UNIQUE` for fields with unique-value validation
- Add `CHECK (col IN (...))` for fields with range or value-list validation
- Add SQL comment for each calculated field: `-- Calculated: [original FM formula]`
- Add SQL comment for each summary field: `-- Summary: [e.g., SUM of line_items.amount]`
- Skip global fields entirely

### 4E. Foreign Keys

For each equi-join relationship (operator `=`):
```sql
-- Source: FM relationship "Description"
ALTER TABLE child_table
  ADD CONSTRAINT fk_child_table_parent_table
  FOREIGN KEY (column)
  REFERENCES parent_table(id)
  ON DELETE CASCADE;  -- SET NULL for optional relationships, RESTRICT if unsure
```

Skip inequality joins — they become WHERE clauses, not FK constraints.

### 4F. Indexes

```sql
-- FK indexes (required for every FK column)
CREATE INDEX idx_table_column ON table(column);

-- Unique indexes (fields with unique validation)
CREATE UNIQUE INDEX idx_table_column ON table(column);

-- Search indexes (fields used in FM find operations — check ddr/specs/05_scripts.json for Enter Find Mode steps)
CREATE INDEX idx_table_column ON table(column);
```

### 4G. Child Tables for Repeating Fields

For each repeating field normalized to a child table:
```sql
CREATE TABLE parent_child_items (
  id         SERIAL PRIMARY KEY,
  parent_id  INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE,
  value      [type],
  sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_parent_child_items_parent_id ON parent_child_items(parent_id);
```

### 4H. updated_at Trigger (PostgreSQL only)

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Repeat for each table:
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON table_name
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 4I. Notes Section

End the file with a comment block:

```sql
-- =============================================================================
-- NOTES
-- =============================================================================

-- Globals-only tables (not migrated as database tables):
-- - TableName: proposed disposition

-- Calculated fields (implement in application, not database):
-- - TableName.FieldName: original FM calculation

-- Summary fields (implement as SQL queries):
-- - TableName.FieldName: e.g., SUM of line_items.amount

-- Repeating fields (normalized to child tables):
-- - TableName.FieldName: child table created: child_table_name
```

---

## Step 5 — Write the File

Write the complete SQL to `migration/04_database_schema.sql`.

After writing:
> "Schema written to `migration/04_database_schema.sql`. [N] tables, [N] foreign keys, [N] indexes. Review before running — especially the globals disposition and any repeating-field normalizations, which may need adjustment once the team sees the generated child tables."
