# Custom Functions Explorer

Internal workflow for analyzing every custom function extracted from a FileMaker DDR export. Input mode: `count`, `all`, or `reports`; for example, `all`.

You are classifying every custom function extracted from a FileMaker DDR export. Use the input mode selected by the main skill. Process functions starting from where the CSV left off, then stop.

**This is the highest-stakes exploration in the migration.** Custom functions are the shared logic layer of a FileMaker solution — called from scripts, calculated fields, conditional formatting, and hide rules everywhere. A function named `PriceAfterDiscount` or `IsEligibleForApproval` is almost certainly a business rule that must be faithfully translated. A function named `PadLeft` or `TrimDate` is a utility helper. The difference matters enormously.

Your job is to read each function's full calculation text, understand what it computes, and produce a classification precise enough to drive translation. For business-critical functions, you also produce a proposed modern signature — the function's shape in the new system.

Nothing is dismissed. Utility functions are documented in a catalog. Deprecated functions are noted. Ambiguous functions are flagged for review. Python moves data — it never writes classification fields.

**On count:** FileMaker solutions rarely have more than 100 custom functions. All functions are written to a single `custom_functions.csv` unless the total exceeds 50, in which case split into alphabetical group files (`a_d.csv`, `e_k.csv`, etc.) to keep files manageable.

---

## Output Structure

```
migration/fm-func-explorer/
  ├── custom_functions.csv       ← single file if ≤ 50 functions
  │   OR [alpha_group].csv files ← split alphabetically if > 50
  └── reports/
      ├── summary.md             ← narrative overview + flagged items
      ├── critical-functions.md  ← business-rule and data-derivation functions with translation
      └── utility-catalog.md     ← utility and helper functions documented
```

---

## Step 1 — Check Progress and Determine File Strategy

```bash
python3 -c "
import os, json, glob, csv

out_dir = 'migration/fm-func-explorer'
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

with open('ddr/specs/08_custom_functions.json') as f:
    functions = json.load(f)
total = len(functions)

strategy = 'single' if total <= 50 else 'alpha'
print(done, next_idx, total, strategy)
"
```

This gives `DONE NEXT_IDX TOTAL STRATEGY`.
- `single` → use `custom_functions.csv`
- `alpha` → determine file from first letter of function name

**Interpreting the input mode:**
- Blank or not a number → default batch size = 1
- Positive integer → batch size = that number
- `"all"` → batch size = TOTAL - DONE
- `"reports"` → skip to Step 4

If DONE >= TOTAL and the input mode is not `"reports"`, skip to Step 4 automatically.

---

## Step 2 — Process the Batch

For each function from index NEXT_IDX to NEXT_IDX + BATCH - 1, do all of A through F before moving to the next.

### A. Extract the function

```bash
python3 -c "
import json, sys
with open('ddr/specs/08_custom_functions.json') as f:
    functions = json.load(f)
idx = int(sys.argv[1])
if idx >= len(functions):
    print('DONE')
else:
    print(json.dumps(functions[idx], indent=2))
" INDEX
```

### B. Read the full calculation

You — the model — must read the complete `calculation` text. Custom functions can be recursive, can call other custom functions, and can have complex conditional branching. Consider:

1. **What are the parameters?** — from the `parameters` field (semicolon-separated). What do they represent in business terms?
2. **What does the function compute?** — trace through the logic: what is the return value for different inputs?
3. **Does it call other custom functions?** — nested custom function calls indicate a library of shared logic; note the dependency
4. **Is it recursive?** — FM custom functions support recursion; if recursive, understand the base case and what the recursion accumulates
5. **What domain does it serve?** — the function name, parameters, and calculation body together tell you: pricing, validation, date math, string formatting, workflow, etc.
6. **Is `visible` = False?** — hidden functions were intentionally not exposed to users in the FM editor; this is a weak signal for internal/deprecated status, not a definitive one

### C. Classify

**`category`** — pick one:

| Category | What it means |
|---|---|
| `utility` | Generic helper with no domain knowledge: string manipulation, date math, number formatting, list operations |
| `business-rule` | Encodes a domain decision: eligibility check, approval condition, classification, discount rule |
| `financial` | Computes a monetary value, pricing tier, fee, tax, or financial metric |
| `data-derivation` | Derives a value from related data, aggregates, or cross-table lookups |
| `validation` | Checks whether a value or record state is valid; returns boolean or error message |
| `deprecated` | References missing fields/tables, marked hidden with no apparent callers, or clearly superseded |

**`logic_tier`:**
- `none` — pure utility with no domain knowledge (string pad, date difference, list filter)
- `tier2` — domain-aware but straightforward; can be reimplemented from the formula alone
- `tier1-critical` — financial computation, eligibility decision, multi-step algorithm, or recursive accumulation where a wrong implementation has real consequences

**`flag`:**
- `clear` — classification is confident
- `needs-review` — calculation is too opaque to classify confidently, references unknown custom functions, or the function name contradicts what the formula computes

**`meaning`** — one sentence: what does this function compute, in business terms?
- Good: `"Computes the discounted price for a line item based on quantity tier and customer category"`
- Good: `"Returns true when a speaker record meets all criteria for confirmation in the program"`
- Bad: `"Applies a Case statement to the input parameters"`

**`migration_target`** — where does this function live in the new system?
- `utility-module` — language-level helper (lodash-style, date-fns, custom util file); no business domain
- `service-method` — backend service method with domain logic; should be tested
- `db-function` — can be expressed as a PostgreSQL function or generated column expression
- `frontend-helper` — display-only transformation safe to implement as a filter or computed property
- `drop` — deprecated or superseded; verify before removing

**`modern_signature`** — proposed function signature in the new system. Write in TypeScript-style notation (readable regardless of the target language):
- `calculateLineTotal(quantity: number, unitPrice: number, discountRate: number): number`
- `isEligibleForApproval(record: SpeakerRecord, programStatus: string): boolean`
- `formatDisplayName(first: string, last: string, suffix: string): string`

For `drop` and `utility-module` (standard helpers), the signature can be: `[drop]` or `[use lodash/date-fns equivalent]`.

### D. Self-check before writing

Reject and rewrite if:
- `category` is not from the controlled vocabulary without a clearly better tag
- `logic_tier = tier1-critical` but `migration_target = frontend-helper` (frontend shouldn't own critical business logic)
- `meaning` describes the formula mechanics instead of what the function represents
- `modern_signature` is missing for any `business-rule`, `financial`, or `data-derivation` function
- `flag = needs-review` without a clear reason embedded in the meaning

### E. Write the row

Determine output filename:

```bash
python3 -c "
import sys
total = int(sys.argv[1])
strategy = sys.argv[2]
name = sys.argv[3].lower()

if strategy == 'single':
    print('custom_functions.csv')
else:
    # Alphabetical grouping
    c = name[0] if name else 'z'
    groups = [('a','d'), ('e','k'), ('l','p'), ('q','z')]
    for start, end in groups:
        if start <= c <= end:
            print(f'{start}_{end}.csv')
            break
    else:
        print('other.csv')
" TOTAL STRATEGY 'FUNCTION_NAME'
```

Create with header if the file doesn't exist:

```bash
python3 -c "
import os, sys
path = sys.argv[1]
if not os.path.exists(path):
    with open(path, 'w') as f:
        f.write('index,name,params,visible,category,logic_tier,flag,meaning,migration_target,modern_signature\n')
" 'migration/fm-func-explorer/FILENAME'
```

Append the row:

```bash
python3 -c "
import csv, sys
fields = sys.argv[1:]
with open(fields[0], 'a', newline='') as f:
    csv.writer(f).writerow(fields[1:])
" 'migration/fm-func-explorer/FILENAME' 'INDEX' 'NAME' 'PARAMS' 'VISIBLE' 'CATEGORY' 'LOGIC_TIER' 'FLAG' 'MEANING' 'MIGRATION_TARGET' 'MODERN_SIGNATURE'
```

---

## Step 3 — Progress Report

Output only:
```
Processed N functions (DONE_NOW/TOTAL). File(s) updated: file1.csv
```

If all functions complete, proceed immediately to Step 4.

---

## Step 4 — Report Generation

Load all CSVs and compute statistics:

```bash
python3 -c "
import os, csv, json, glob
from collections import Counter

out_dir = 'migration/fm-func-explorer'
all_funcs = []
for f in sorted(glob.glob(os.path.join(out_dir, '*.csv'))):
    with open(f, newline='') as fh:
        for row in csv.DictReader(fh):
            row['_source_csv'] = os.path.basename(f)
            all_funcs.append(row)

categories = Counter(r['category'] for r in all_funcs)
tiers = Counter(r['logic_tier'] for r in all_funcs)
targets = Counter(r['migration_target'] for r in all_funcs)
flags = Counter(r['flag'] for r in all_funcs)

critical = [r for r in all_funcs if r['logic_tier'] == 'tier1-critical']
business = [r for r in all_funcs if r['category'] in ('business-rule', 'financial', 'data-derivation')]
utilities = [r for r in all_funcs if r['category'] == 'utility']
flagged = [r for r in all_funcs if r['flag'] == 'needs-review']
hidden = [r for r in all_funcs if r.get('visible', 'True') == 'False']

print(f'Total functions: {len(all_funcs)}')
print(f'Tier1-critical: {len(critical)}')
print(f'Business logic (rule/financial/derivation): {len(business)}')
print(f'Utilities: {len(utilities)}')
print(f'Needs review: {len(flagged)}')
print(f'Hidden (visible=False): {len(hidden)}')
print(f'Categories: {dict(categories)}')
print(f'Tiers: {dict(tiers)}')
print(f'Migration targets: {dict(targets)}')
"
```

Generate three reports in `migration/fm-func-explorer/reports/`:

### 4A. Summary (`reports/summary.md`)

```markdown
# Custom Functions Analysis

## Overview
- Total custom functions: N
- Tier1-critical: N — require careful translation and testing
- Business logic (rule/financial/derivation): N
- Utilities: N — can use standard library equivalents
- Deprecated: N — verify before dropping
- Flagged for review: N
- Hidden (visible=False): N

## Application Logic Library
[3-5 sentences describing what this custom function library reveals about the application's
architecture. What business domains are represented? Is there a clear utility layer vs. domain
layer? Are there signs of technical debt (deprecated functions, duplicated logic)?]

## Function Dependencies
[If any functions call other custom functions, document the dependency graph here.
Recursive functions get special attention — list them and describe what they accumulate.]

## Migration Priority
Tier1-critical functions must be translated before any feature that uses them can be built.
[List the tier1-critical functions in suggested translation order, based on dependencies.]

## Flagged for Review
| Function | Params | Why Flagged |
|---|---|---|

## Hidden Functions
| Function | Params | Category | Notes |
|---|---|---|---|
```

### 4B. Critical Functions (`reports/critical-functions.md`)

Every business-rule, financial, and data-derivation function — with full translation guidance:

```markdown
# Critical Custom Functions

> Functions that encode domain decisions, financial logic, or complex derivations.
> These must be translated before any feature that depends on them can be built.
> Each entry includes the original calculation and a proposed modern equivalent.

## Tier 1 Critical (N functions)

### [Function Name]([params])
**Category:** [business-rule / financial / data-derivation]
**Migration target:** [service-method / db-function / etc.]
**Modern signature:** `[proposed signature]`

**Original calculation:**
```
[full FM calculation text]
```

**What it does:** [2-3 sentences explaining the business logic in plain terms]

**Translation notes:** [Specific guidance — edge cases, FM functions that need equivalents,
recursive logic to unroll, dependencies on other custom functions]

---

[Repeat for each critical function]

## Tier 2 (N functions)

[Same structure, slightly less detail — focus on signature and translation notes]
```

### 4C. Utility Catalog (`reports/utility-catalog.md`)

Every utility and helper function — documented for the team's reference:

```markdown
# Utility Functions Catalog

> Helper functions with no domain business logic. These can typically be replaced
> by standard library functions (lodash, date-fns, Python stdlib, etc.) or
> implemented as simple utility methods.

## [Category: String Utilities / Date Utilities / Math Utilities / List Utilities / Other]

| Index | Function | Params | Meaning | Migration Target | Modern Equivalent |
|---|---|---|---|---|---|

## Deprecated Functions (N)
| Index | Function | Params | Visible | Notes |
|---|---|---|---|---|
```

---

### Report Quality Standards

- **Critical functions get full calculation text in the report.** A developer translating `PriceAfterDiscount` needs to read the FM formula. Don't paraphrase; include it.
- **Recursive functions get unrolled.** Explain what the recursion accumulates and what the base case returns.
- **Dependencies are explicit.** If `CalculateFee` calls `GetTierRate` which calls `RoundCurrency`, that chain must be visible in the report.
- **Modern signatures are real.** The proposed signature should be something a developer could copy into a file and implement against. TypeScript notation is preferred regardless of target language.
- **Hidden functions get extra scrutiny.** `visible=False` can mean deprecated, internal, or intentionally hidden. Note the ambiguity and let a human decide.

### Step 5 — Final Output

```
Reports generated in migration/fm-func-explorer/reports/:
  summary.md              — N functions, N tier1-critical, N flagged
  critical-functions.md   — N business-critical functions with translation guidance
  utility-catalog.md      — N utility/helper functions + N deprecated documented
```
