# Conditional Formatting Explorer

Internal workflow for analyzing every conditional formatting rule extracted from a FileMaker DDR export. Input mode: `count`, `all`, or `reports`; for example, `count=10`.

You are classifying every conditional formatting rule extracted from a FileMaker DDR export. Use the input mode selected by the main skill. Process rules starting from where the CSVs left off, then stop.

**This is careful classification work, not a fast lookup.** Your job is to read each formula yourself, understand what business condition it detects and what visual change it triggers, and classify it. Do not pattern-match formula fragments. Do not infer category from object name alone. Python is for moving data and tracking progress — it never writes the `category`, `meaning`, or `migration_note` fields. Those are always written by you after reading the formula.

Nothing is dismissed. Every rule gets a row. Cosmetic rules are documented in a dedicated catalog, not dropped. Ambiguous rules are flagged for human review.

---

## Output Structure

```
migration/fm-cf-explorer/
  ├── [layout_name].csv          ← one CSV per layout that has CF rules
  └── reports/
      ├── summary.md             ← narrative overview + flagged items
      ├── business-logic-catalog.md  ← all signal rules with migration mapping
      └── noise-catalog.md       ← all cosmetic/deprecated rules documented
```

---

## Step 1 — Check Progress

```bash
python3 -c "
import os, json, glob, csv

out_dir = 'migration/fm-cf-explorer'
os.makedirs(out_dir, exist_ok=True)

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

with open('ddr/specs/09_conditional_formatting.json') as f:
    total = len(json.load(f))

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

Before processing the batch, extract all formulas already classified in existing CSVs so duplicates can be identified quickly:

```bash
python3 -c "
import glob, csv, json

seen = {}  # formula_text -> {index, category, meaning, migration_note}
for f in sorted(glob.glob('migration/fm-cf-explorer/*.csv')):
    with open(f, newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            formula = row.get('formula', '').strip()
            dup = row.get('duplicate_of', '').strip()
            if formula and not dup and formula not in seen:
                seen[formula] = {
                    'index': row.get('index'),
                    'category': row.get('category'),
                    'meaning': row.get('meaning'),
                    'migration_note': row.get('migration_note'),
                }

print(json.dumps(seen))
"
```

Hold this map in context. For each rule in the batch, check if its `formula` already appears in this map before doing a full analysis.

---

## Step 3 — Process the Batch

For each rule from index NEXT_IDX to NEXT_IDX + BATCH - 1, do all of A through F before moving to the next.

### A. Extract the rule

```bash
python3 -c "
import json, sys
with open('ddr/specs/09_conditional_formatting.json') as f:
    rules = json.load(f)
idx = int(sys.argv[1])
if idx >= len(rules):
    print('DONE')
else:
    print(json.dumps(rules[idx], indent=2))
" INDEX
```

### B. Check for duplicate

If the formula text exactly matches an entry in the duplicate index from Step 2:
- Set `duplicate_of` = the original index
- Copy `category`, `meaning`, `migration_note` from the original
- Set `flag` = `clear`
- Skip to Step F (write the row immediately — no further analysis needed)

### C. Read the formula

You — the model — must read the full formula text. Consider:

1. **What data does it reference?** — which tables, fields, global variables (`$$var`, `$var`), or FM functions
2. **What condition does it detect?** — a threshold crossed, a state matched, a flag set, a role checked
3. **What visual change does it trigger?** — `format_actions` tells you: fill color, text color, bold, italic, etc.
4. **Is this a business condition or a display convention?** — see category vocabulary below
5. **What is the migration equivalent?** — a CSS class binding, a computed property, a status badge variant

If the formula references a field or table that appears to be missing (`<Table Missing>`, `<Field Missing>` markers or names that don't match any table in the spec), classify as `deprecated`.

### D. Classify

**`category`** — pick one:

| Category | What it means |
|---|---|
| `authorization` | Role or privilege check (`$$USER_privgroup`, privilege set name) |
| `data-state` | Visual indicator of a data condition (budget vs. paid, status match) |
| `urgency` | Time-based threshold (countdown < 9, due date passed) |
| `workflow-status` | Multi-state pipeline indicator (status = "Booked", "Cancelled") |
| `validation` | Missing or invalid data highlight (`IsEmpty`, cost = 0) |
| `change-tracking` | Audit or history indicator (has-changed flags, diff fields) |
| `financial` | Money, pricing, or budget comparison |
| `cosmetic` | No business logic: alternating rows, alphabetical color-coding, decorative |
| `deprecated` | References missing tables, fields, or out-of-scope layouts |

**`noise_signal`:**
- `signal` — encodes a business rule a developer needs to reimplement
- `noise` — purely decorative; implement as standard styling, no business logic needed

**`flag`:**
- `clear` — classification is confident
- `needs-review` — formula is ambiguous, references are unclear, or category conflicts with the object name or layout context

**`meaning`** — one sentence: what business condition does this formula detect? State the condition in business terms, not FM mechanics.
- Good: `"Highlights budget line when total cost exceeds approved amount"`
- Bad: `"Checks if Budget::total is greater than Budget::paid"`

**`migration_note`** — one sentence: how to implement this in the new system.
- Good: `"Bind CSS class 'text-red-600 font-semibold' when cost > approved_budget on the record"`
- Bad: `"Implement in frontend"`

### E. Self-check before writing

Reject and rewrite if any of these are true:
- `category` is not from the controlled vocabulary without a clearly better short tag
- `meaning` describes FM mechanics instead of the business condition
- `migration_note` is generic ("implement in frontend", "use a CSS class")
- `noise_signal = signal` but `migration_note` says nothing actionable
- `flag = needs-review` without a clear reason in the `meaning` field noting what's ambiguous

### F. Write the row

Determine the output filename from the layout name:

```bash
python3 -c "
import re, sys
layout = sys.argv[1]
filename = re.sub(r'[\s/\\\\]+', '_', layout).lower().strip('_')
print(filename + '.csv')
" 'LAYOUT_NAME'
```

Create the file with header if it doesn't exist:

```bash
python3 -c "
import os, sys
path = sys.argv[1]
if not os.path.exists(path):
    with open(path, 'w') as f:
        f.write('index,layout,object_name,object_type,formula,format_actions,category,noise_signal,duplicate_of,flag,meaning,migration_note\n')
" 'migration/fm-cf-explorer/FILENAME'
```

Append the row:

```bash
python3 -c "
import csv, sys
fields = sys.argv[1:]
with open(fields[0], 'a', newline='') as f:
    csv.writer(f).writerow(fields[1:])
" 'migration/fm-cf-explorer/FILENAME' 'INDEX' 'LAYOUT' 'OBJECT_NAME' 'OBJECT_TYPE' 'FORMULA' 'FORMAT_ACTIONS' 'CATEGORY' 'NOISE_SIGNAL' 'DUPLICATE_OF' 'FLAG' 'MEANING' 'MIGRATION_NOTE'
```

---

## Step 3 — Progress Report

Output only:
```
Processed N rules (DONE_NOW/TOTAL). Files updated: file1.csv, file2.csv
```

If all rules are now complete (DONE_NOW >= TOTAL), proceed immediately to Step 4.

---

## Step 4 — Report Generation

Load all CSVs and compute statistics:

```bash
python3 -c "
import os, csv, json, glob
from collections import Counter

out_dir = 'migration/fm-cf-explorer'
all_rules = []
for f in sorted(glob.glob(os.path.join(out_dir, '*.csv'))):
    with open(f, newline='') as fh:
        for row in csv.DictReader(fh):
            row['_source_csv'] = os.path.basename(f)
            all_rules.append(row)

categories = Counter(r['category'] for r in all_rules)
noise_signal = Counter(r['noise_signal'] for r in all_rules)
flags = Counter(r['flag'] for r in all_rules)
layouts = Counter(r['layout'] for r in all_rules)
duplicates = sum(1 for r in all_rules if r.get('duplicate_of', '').strip())
unique = len(all_rules) - duplicates

signal_rules = [r for r in all_rules if r['noise_signal'] == 'signal' and not r.get('duplicate_of', '').strip()]
noise_rules = [r for r in all_rules if r['noise_signal'] == 'noise']
flagged = [r for r in all_rules if r['flag'] == 'needs-review']

print(f'Total rules: {len(all_rules)}')
print(f'Unique formulas: {unique}, Duplicates: {duplicates}')
print(f'Signal (business logic): {noise_signal[\"signal\"]}')
print(f'Noise (cosmetic): {noise_signal[\"noise\"]}')
print(f'Needs review: {flags[\"needs-review\"]}')
print(f'Categories: {dict(categories)}')
print(f'Top layouts by rule count: {layouts.most_common(10)}')
print(f'Signal rules: {len(signal_rules)}')
"
```

Generate three reports in `migration/fm-cf-explorer/reports/`:

### 4A. Summary (`reports/summary.md`)

```markdown
# Conditional Formatting Analysis

## Overview
- Total rules: N across N layouts
- Unique formulas: N (N duplicates across layouts)
- Business logic (signal): N rules — N% of unique formulas
- Cosmetic (noise): N rules — N%
- Deprecated/broken: N rules
- Flagged for review: N rules

## Business Logic Domains
For each signal category (sorted by rule count):
### [Category Name]
- What business condition it encodes (2-3 sentences)
- Tables and fields involved
- Session variables referenced ($$var)
- Migration approach: [CSS class binding / computed property / status badge variant / etc.]

## Migration Mapping
| FM Pattern | Visual Effect | Modern Implementation |
|---|---|---|
| [formula pattern] | [e.g., red fill] | [e.g., :class binding on is_overdue computed] |

## Flagged for Review
Rules the model could not classify confidently. Each needs a human decision before implementation.

| Layout | Object | Formula | Why Flagged |
|---|---|---|---|
| ... | ... | ... | ... |

## Top Layouts by Rule Count
Table: layout, signal count, noise count, flagged count.
```

### 4B. Business Logic Catalog (`reports/business-logic-catalog.md`)

Every unique signal rule (not cosmetic, not a duplicate), organized by category:

```markdown
# Conditional Formatting — Business Logic Catalog

## [Category] (N unique formulas)

Brief description of what this category encodes for migration.

| Index | Formula | Format Actions | Layouts Applied | Occurrences | Meaning | Migration Note |
|---|---|---|---|---|---|---|
```

### 4C. Noise Catalog (`reports/noise-catalog.md`)

Every cosmetic and deprecated rule, documented:

```markdown
# Conditional Formatting — Noise Catalog

> Cosmetic and deprecated rules. Not required for migration logic, but documented
> here so nothing is silently dropped. Review the Deprecated section — some entries
> may indicate removed features that need a migration decision.

## Cosmetic Rules (N)
Rules with no business logic: alternating rows, alphabetical highlights, decorative formatting.

| Index | Layout | Object | Formula | Format Actions | Notes |

## Deprecated Rules (N)
Rules referencing missing tables or fields.

| Index | Layout | Object | Formula | Missing Reference | Notes |
```

---

### Report Quality Standards

- **Write analysis, not data dumps.** Tables are evidence; your narrative is the value.
- **Name the business domains.** "Financial threshold" is useless. "Budget overrun indicator on line items when actual > approved" is actionable.
- **Flagged items get a reason.** Every needs-review row in the summary must explain specifically what is ambiguous — not just "unclear."
- **Migration notes are specific.** Name the CSS class, computed property pattern, or component behavior. Never say "implement in frontend."

### Step 5 — Final Output

```
Reports generated in migration/fm-cf-explorer/reports/:
  summary.md                  — N rules, N signal, N noise, N flagged
  business-logic-catalog.md   — N unique business logic formulas by category
  noise-catalog.md            — N cosmetic + N deprecated rules documented
```
