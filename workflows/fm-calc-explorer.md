# Calculated Fields Explorer

Internal workflow for analyzing every calculated field extracted from a FileMaker DDR export. Input mode: `count`, `all`, or `reports`; for example, `count=10`. Tables with no calculated fields are skipped.

You are classifying every calculated field extracted from a FileMaker DDR export. Use the input mode selected by the main skill. Process fields starting from where the CSVs left off, then stop.

**This is careful classification work, not a fast lookup.** Calculated fields are often dismissed as "display logic" — but they frequently encode eligibility rules, financial derivations, status computations, and business invariants that must be faithfully reimplemented in the new system. Your job is to read each formula, understand what it computes and why it exists, and classify it precisely.

Nothing is dismissed. Every calculated field gets a row. Display-only and deprecated fields are documented in a dedicated catalog. Ambiguous fields are flagged for human review. Tables with no calculated fields are skipped entirely. Python is for moving data — it never writes classification fields.

---

## Output Structure

```
migration/fm-calc-explorer/
  ├── [table_name].csv           ← one CSV per table that has calculated fields
  └── reports/
      ├── summary.md             ← narrative overview + flagged items
      ├── business-logic-fields.md   ← tier2/tier1 fields with translation guidance
      └── migration-targets.md   ← all fields organized by migration target
```

---

## Step 1 — Build Flat Index and Check Progress

Calculated fields are nested inside table objects in `01_tables.json`. Flatten them into a single indexed list for consistent progress tracking:

```bash
python3 -c "
import os, json, glob, csv

out_dir = 'migration/fm-calc-explorer'
os.makedirs(out_dir, exist_ok=True)

# Build flat index
with open('ddr/specs/01_tables.json') as f:
    tables = json.load(f)

flat = []
for table in tables:
    calcs = table.get('calculated', [])
    if calcs:
        for field in calcs:
            flat.append({'table': table['name'], 'field': field})

# Check progress
done_indices = set()
for f in glob.glob(os.path.join(out_dir, '*.csv')):
    with open(f, newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                done_indices.add(int(row['index']))
            except (KeyError, ValueError):
                pass

done = len(done_indices)
next_idx = max(done_indices) + 1 if done_indices else 0
total = len(flat)

print(done, next_idx, total)
"
```

This gives `DONE NEXT_IDX TOTAL`.

**Interpreting the input mode:**
- Blank or not a number → default batch size = 1
- Positive integer → batch size = that number
- `"all"` → batch size = TOTAL - DONE
- `"reports"` → skip to Step 4

If DONE >= TOTAL and the input mode is not `"reports"`, skip to Step 4 automatically.

---

## Step 2 — Build Duplicate Index

Extract all formulas already classified in existing CSVs:

```bash
python3 -c "
import glob, csv, json

seen = {}
for f in sorted(glob.glob('migration/fm-calc-explorer/*.csv')):
    with open(f, newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            formula = row.get('formula', '').strip()
            dup = row.get('duplicate_of', '').strip()
            if formula and not dup and formula not in seen:
                seen[formula] = {
                    'index': row.get('index'),
                    'category': row.get('category'),
                    'logic_tier': row.get('logic_tier'),
                    'meaning': row.get('meaning'),
                    'migration_target': row.get('migration_target'),
                }

print(json.dumps(seen))
"
```

Hold this map in context. For each field in the batch, check if its formula exactly matches an entry before doing full analysis.

---

## Step 3 — Process the Batch

For each field from index NEXT_IDX to NEXT_IDX + BATCH - 1, do all of A through F before moving to the next.

### A. Extract the field

```bash
python3 -c "
import json, sys

with open('ddr/specs/01_tables.json') as f:
    tables = json.load(f)

flat = []
for table in tables:
    for field in table.get('calculated', []):
        flat.append({'table': table['name'], 'field': field})

idx = int(sys.argv[1])
if idx >= len(flat):
    print('DONE')
else:
    print(json.dumps(flat[idx], indent=2))
" INDEX
```

### B. Check for duplicate

If the formula text exactly matches an entry in the duplicate index:
- Set `duplicate_of` = the original index
- Copy `category`, `logic_tier`, `meaning`, `migration_target` from the original
- Set `flag` = `clear`
- Skip to Step F immediately

### C. Read the formula

You — the model — must read the full formula text and consider:

1. **What does this field compute?** — what is the result in business terms?
2. **What data does it reference?** — fields from related tables, global variables, FM functions, custom functions
3. **Is this a display transformation or a business rule?** — formatting a name for display is different from computing an approval status
4. **Is this formula used as a source for other things?** — calculated fields are often the inputs to other calculations, scripts, value lists, or conditional rules
5. **Does it reference a custom function?** — if so, that function name is a signal about the domain (e.g., `CalcDiscount`, `IsEligible`, `PriceAfterTier`)
6. **What happens if it's wrong?** — a wrong display-name calculation is cosmetic; a wrong financial calculation has real consequences

If the formula references fields or tables that appear to be missing, classify as `deprecated`.

### D. Classify

**`category`** — pick one:

| Category | What it means |
|---|---|
| `display-only` | Formats data for presentation (concatenates name, formats currency/date, builds labels) — no business decision embedded |
| `business-rule` | Computes an eligibility status, approval condition, classification, or domain decision |
| `financial` | Computes a monetary value, cost, fee, balance, or financial metric |
| `aggregate` | Sums, counts, averages, or otherwise aggregates related records |
| `lookup` | Pulls a value from a related record (effectively a join) |
| `audit-derived` | Derives a timestamp, modifier name, or change-tracking value |
| `deprecated` | References missing tables, deleted fields, or removed features |

**`logic_tier`** — mirrors the script explorer scale:
- `none` — display-only formatting with no decision logic
- `read-only` — derives or looks up a value, no decision
- `tier2` — encodes a classification or conditional logic; standard enough to reimplement from the formula alone
- `tier1-critical` — financial computation, multi-step derivation, eligibility decision, or any formula where a wrong implementation has real consequences

**`return_type`** — the FM return type if discernible from the formula or field definition: `text` / `number` / `date` / `boolean` / `timestamp`

**`flag`:**
- `clear` — classification is confident
- `needs-review` — formula is ambiguous, references are unclear, logic tier is hard to determine without domain context, or the field name contradicts what the formula computes

**`meaning`** — one sentence: what does this calculated field represent in business terms?
- Good: `"Computes total cost of all line items plus any applicable surcharges"`
- Good: `"Returns true when the record is past its due date and no payment has been received"`
- Bad: `"Sums the related fields and applies a calculation"`

**`migration_target`** — where does this field live in the new system?
- `db-generated-column` — simple arithmetic on columns within the same row (e.g., `quantity * unit_price`) → SQL `GENERATED ALWAYS AS`
- `sql-view` — aggregates or joins that span tables → implement as a database view or materialized view
- `service-layer` — complex conditional logic, multi-step derivation, or custom function dependency → backend service method
- `frontend-computed` — display-only transformation (name formatting, label building, currency display) → computed property or filter in the frontend
- `drop` — deprecated or redundant; document why

### E. Self-check before writing

Reject and rewrite if:
- `category` is not from the controlled vocabulary without a clearly better tag
- `logic_tier = tier1-critical` but `migration_target = frontend-computed` (frontend shouldn't own critical business logic)
- `meaning` describes what the formula does mechanically instead of what it represents
- `migration_target` is vague ("implement in application")
- `flag = needs-review` without a clear reason in the meaning field

### F. Write the row

Determine output filename from the table name:

```bash
python3 -c "
import re, sys
table = sys.argv[1]
filename = re.sub(r'[\s/\\\\]+', '_', table).lower().strip('_')
print(filename + '.csv')
" 'TABLE_NAME'
```

Create with header if the file doesn't exist:

```bash
python3 -c "
import os, sys
path = sys.argv[1]
if not os.path.exists(path):
    with open(path, 'w') as f:
        f.write('index,table,field_name,formula,return_type,category,logic_tier,duplicate_of,flag,meaning,migration_target\n')
" 'migration/fm-calc-explorer/FILENAME'
```

Append the row:

```bash
python3 -c "
import csv, sys
fields = sys.argv[1:]
with open(fields[0], 'a', newline='') as f:
    csv.writer(f).writerow(fields[1:])
" 'migration/fm-calc-explorer/FILENAME' 'INDEX' 'TABLE' 'FIELD_NAME' 'FORMULA' 'RETURN_TYPE' 'CATEGORY' 'LOGIC_TIER' 'DUPLICATE_OF' 'FLAG' 'MEANING' 'MIGRATION_TARGET'
```

---

## Step 3 — Progress Report

Output only:
```
Processed N fields (DONE_NOW/TOTAL). Files updated: file1.csv, file2.csv
```

If all fields complete, proceed immediately to Step 4.

---

## Step 4 — Report Generation

Load all CSVs and compute statistics:

```bash
python3 -c "
import os, csv, json, glob
from collections import Counter

out_dir = 'migration/fm-calc-explorer'
all_fields = []
for f in sorted(glob.glob(os.path.join(out_dir, '*.csv'))):
    with open(f, newline='') as fh:
        for row in csv.DictReader(fh):
            row['_source_csv'] = os.path.basename(f)
            all_fields.append(row)

categories = Counter(r['category'] for r in all_fields)
tiers = Counter(r['logic_tier'] for r in all_fields)
targets = Counter(r['migration_target'] for r in all_fields)
flags = Counter(r['flag'] for r in all_fields)
tables = Counter(r['table'] for r in all_fields)
duplicates = sum(1 for r in all_fields if r.get('duplicate_of', '').strip())
unique = len(all_fields) - duplicates

critical = [r for r in all_fields if r['logic_tier'] == 'tier1-critical' and not r.get('duplicate_of','').strip()]
business = [r for r in all_fields if r['category'] in ('business-rule', 'financial') and not r.get('duplicate_of','').strip()]
flagged = [r for r in all_fields if r['flag'] == 'needs-review']

print(f'Total fields: {len(all_fields)}')
print(f'Unique formulas: {unique}, Duplicates: {duplicates}')
print(f'Categories: {dict(categories)}')
print(f'Logic tiers: {dict(tiers)}')
print(f'Migration targets: {dict(targets)}')
print(f'Tier1-critical: {len(critical)}')
print(f'Business rule + financial: {len(business)}')
print(f'Needs review: {len(flagged)}')
print(f'Tables with calculated fields: {len(tables)}')
"
```

Generate three reports in `migration/fm-calc-explorer/reports/`:

### 4A. Summary (`reports/summary.md`)

```markdown
# Calculated Fields Analysis

## Overview
- Total calculated fields: N across N tables
- Unique formulas: N (N duplicates)
- Tier1-critical: N — require careful translation
- Business rule / financial: N — encode domain decisions
- Display-only: N — safe to implement as frontend computed
- Deprecated: N — document and confirm disposal
- Flagged for review: N

## Key Findings
[2-4 sentences on the most important things the calculated fields reveal about the application's business logic]

## Tables with Most Business Logic
Table: table name, business-rule count, tier1 count, flagged count.

## Migration Complexity by Target
| Target | Count | Notes |
|---|---|---|
| db-generated-column | N | Simple — add GENERATED AS clause |
| sql-view | N | Moderate — design views for each aggregate |
| service-layer | N | High — requires careful implementation |
| frontend-computed | N | Low — computed property or filter |
| drop | N | Verify each before removing |

## Flagged for Review
| Table | Field | Formula | Why Flagged |
|---|---|---|---|
```

### 4B. Business Logic Fields (`reports/business-logic-fields.md`)

Every tier2 and tier1-critical field, with translation guidance:

```markdown
# Business Logic Calculated Fields

> Fields that encode domain decisions, financial computations, or eligibility rules.
> These are the calculated fields that require careful translation — not just a
> computed property, but verified business logic.

## Tier 1 Critical (N fields)

| Table | Field | Formula | Return Type | Meaning | Migration Target |
|---|---|---|---|---|---|

## Tier 2 (N fields)

| Table | Field | Formula | Return Type | Meaning | Migration Target |
|---|---|---|---|---|---|
```

### 4C. Migration Targets (`reports/migration-targets.md`)

All fields organized by where they land in the new system:

```markdown
# Migration Targets

> Every calculated field organized by implementation location.
> Use this to plan the development work for each layer of the new system.

## Database Generated Columns (N fields)
Fields safe to implement as SQL GENERATED ALWAYS AS expressions.
| Table | Field | Formula | Proposed SQL Expression |

## SQL Views / Aggregates (N fields)
Fields requiring joins or aggregations across tables.
| Table | Field | Formula | Proposed View/Query |

## Service Layer (N fields)
Fields with complex logic that belongs in backend code.
| Table | Field | Formula | Meaning | Notes |

## Frontend Computed (N fields)
Display-only fields safe to implement as computed properties or filters.
| Table | Field | Formula | Meaning |

## Drop (N fields)
Deprecated or redundant fields.
| Table | Field | Formula | Reason |
```

---

### Report Quality Standards

- **Tier1-critical fields get specific translation guidance** — not just "implement in service layer" but a sketch of what the service method needs to do.
- **Aggregate fields name their query** — "SUM of line_items.amount WHERE status != 'cancelled'" is actionable. "Aggregate" is not.
- **Custom function references are noted** — if a formula calls a custom function, note the function name so it can be cross-referenced with the fm-func-explorer output.
- **Flagged items explain the ambiguity specifically.**

### Step 5 — Final Output

```
Reports generated in migration/fm-calc-explorer/reports/:
  summary.md                  — N fields, N tier1-critical, N flagged
  business-logic-fields.md    — N business-rule/financial fields with translation
  migration-targets.md        — All N fields by implementation location
```
