# Hide-Object-When Explorer

Internal workflow for analyzing every hide-object-when rule extracted from a FileMaker DDR export. Input mode: `count`, `all`, or `reports`; for example, `count=10`.

You are classifying every hide-object-when rule extracted from a FileMaker DDR export. Use the input mode selected by the main skill. Process rules starting from where the CSVs left off, then stop.

**This is careful classification work, not a fast lookup.** Hide-object-when formulas frequently encode the application's entire authorization model, workflow state machines, and progressive disclosure logic — business logic that is invisible in the data model and scripts. Your job is to read each formula yourself, understand what it controls and why, and classify it precisely. Do not pattern-match formula fragments. Do not infer category from object name alone.

Nothing is dismissed. Every rule gets a row. Constant formulas (`1`, `True`) are documented in the noise catalog — some are intentional reserved space; some are accidentally hidden features. Ambiguous rules are flagged for human review. Python is for moving data — it never writes classification fields.

---

## Output Structure

```
migration/fm-hide-explorer/
  ├── [layout_name].csv          ← one CSV per layout that has hide rules
  └── reports/
      ├── summary.md             ← narrative overview + authorization model + flagged items
      ├── auth-model.md          ← all authorization rules by layer
      ├── state-rules.md         ← workflow and session-state rules
      └── noise-catalog.md       ← constant, deprecated, and platform-only rules documented
```

---

## Step 1 — Check Progress

```bash
python3 -c "
import os, json, glob, csv

out_dir = 'migration/fm-hide-explorer'
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

with open('ddr/specs/10_hide_object_when.json') as f:
    total = len(json.load(f))

print(done, next_idx, total)
"
```

**Interpreting the input mode:**
- Blank or not a number → default batch size = 1
- Positive integer → batch size = that number
- `"all"` → batch size = TOTAL - DONE
- `"reports"` → skip to Step 4

If DONE >= TOTAL and the input mode is not `"reports"`, skip to Step 4 automatically.

---

## Step 2 — Build Duplicate Index

Before processing the batch, extract all formulas already classified in existing CSVs:

```bash
python3 -c "
import glob, csv, json

seen = {}
for f in sorted(glob.glob('migration/fm-hide-explorer/*.csv')):
    with open(f, newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            formula = row.get('formula', '').strip()
            dup = row.get('duplicate_of', '').strip()
            if formula and not dup and formula not in seen:
                seen[formula] = {
                    'index': row.get('index'),
                    'category': row.get('category'),
                    'auth_layer': row.get('auth_layer'),
                    'meaning': row.get('meaning'),
                    'migration_target': row.get('migration_target'),
                }

print(json.dumps(seen))
"
```

Hold this map in context. For each rule in the batch, check if its formula exactly matches an entry before doing full analysis.

---

## Step 3 — Process the Batch

For each rule from index NEXT_IDX to NEXT_IDX + BATCH - 1, do all of A through F before moving to the next.

### A. Extract the rule

```bash
python3 -c "
import json, sys
with open('ddr/specs/10_hide_object_when.json') as f:
    rules = json.load(f)
idx = int(sys.argv[1])
if idx >= len(rules):
    print('DONE')
else:
    print(json.dumps(rules[idx], indent=2))
" INDEX
```

### B. Check for duplicate

If the formula text exactly matches an entry in the duplicate index:
- Set `duplicate_of` = the original index
- Copy `category`, `auth_layer`, `meaning`, `migration_target` from the original
- Set `flag` = `clear`
- Skip to Step F immediately

### C. Read the formula

You — the model — must read the full formula text. Consider:

1. **What data does it reference?** — tables, fields, global variables (`$$var`), FM functions like `Get(AccountPrivilegeSetName)`, `Get(SystemPlatform)`
2. **What condition hides the object?** — the formula evaluates to true (non-zero) when the object is hidden
3. **What kind of control is this?** — role check, permission flag, workflow gate, platform branch, constant, or dead code
4. **Who can see this object?** — for authorization rules, infer which roles or conditions make the formula false (showing the object)
5. **What does the object name suggest about its function?** — object names like `btn_approve`, `portal_sensitive_data`, `nav_admin` give context

**Authorization layer recognition** — FM developers stack these in order of increasing granularity:
- **Layer 1 — Role check:** `$$USER_privgroup`, `Get(AccountPrivilegeSetName)` against privilege set names
- **Layer 2 — Menu/context:** `$$USER_menuset`, user context variables
- **Layer 3 — Permission flag:** `$$SENSITIVEDATA_*`, `$$CANVIEW_*`, `$$PERMISSION_*` loaded from a database at login
- **Layer 4 — Record-level sensitivity:** per-record flag field (e.g., `Contacts::IsConfidential = 1`)
- **Layer 5 — Activity/category-level:** `ExecuteSQL` or aggregate checks against activity categories or line items

If the formula references fields or tables that appear to be missing, classify as `deprecated`.

### D. Classify

**`category`** — pick one:

| Category | What it means |
|---|---|
| `authorization` | Role or privilege-based visibility — who can see this |
| `permission-flag` | Granular database-stored permission loaded into a session variable |
| `record-sensitivity` | Per-record confidential or restricted flag |
| `session-state` | Progressive disclosure driven by what data has been loaded (`data01 = ""`) |
| `workflow-state` | Object visible only during a specific workflow stage |
| `ui-context` | Mode, view, or tab dependent — no auth logic |
| `platform` | Desktop vs. mobile vs. WebDirect (`Get(SystemPlatform)`) |
| `deprecated` | References missing tables, deleted fields, or out-of-scope features |
| `constant` | Formula is always true (`1`, `True`) or always false (`0`) — permanently hidden or always visible |

**`auth_layer`** — for `authorization` and `permission-flag` categories only:
- `1` through `5` based on the layer description above
- Leave blank for all other categories

**`flag`:**
- `clear` — classification is confident
- `needs-review` — formula is ambiguous, references are contradictory, or the object context conflicts with the formula logic

**`meaning`** — one sentence: what business condition controls this object's visibility?
- Good: `"Hidden from all users except those with Full Access privilege set"`
- Good: `"Visible only after the voucher has been marked sent by the workflow"`
- Bad: `"Checks $$USER_privgroup variable"`

**`migration_target`** — one sentence: how to implement this in the new system.
- `route-guard` — server-side or router-level check before the page loads
- `store-permission` — permission flag loaded into the auth store at login, checked via computed prop
- `component-prop` — passed as a `:visible` or `v-if` prop to the component
- `reactive-state` — reactive store state drives conditional rendering
- `state-machine` — XState or store enum drives which UI elements are visible
- `dead-code` — constant or deprecated, no migration needed (document reason)

### E. Self-check before writing

Reject and rewrite if:
- `category` is not from the controlled vocabulary without a clearly better tag
- `auth_layer` is set for a non-authorization category
- `meaning` describes FM mechanics instead of the visibility condition in business terms
- `migration_target` is vague ("implement in frontend", "use v-if")
- `flag = needs-review` without a clear reason embedded in the meaning

### F. Write the row

Determine output filename from layout name:

```bash
python3 -c "
import re, sys
layout = sys.argv[1]
filename = re.sub(r'[\s/\\\\]+', '_', layout).lower().strip('_')
print(filename + '.csv')
" 'LAYOUT_NAME'
```

Create with header if the file doesn't exist:

```bash
python3 -c "
import os, sys
path = sys.argv[1]
if not os.path.exists(path):
    with open(path, 'w') as f:
        f.write('index,layout,object_name,object_type,formula,category,auth_layer,duplicate_of,flag,meaning,migration_target\n')
" 'migration/fm-hide-explorer/FILENAME'
```

Append the row:

```bash
python3 -c "
import csv, sys
fields = sys.argv[1:]
with open(fields[0], 'a', newline='') as f:
    csv.writer(f).writerow(fields[1:])
" 'migration/fm-hide-explorer/FILENAME' 'INDEX' 'LAYOUT' 'OBJECT_NAME' 'OBJECT_TYPE' 'FORMULA' 'CATEGORY' 'AUTH_LAYER' 'DUPLICATE_OF' 'FLAG' 'MEANING' 'MIGRATION_TARGET'
```

---

## Step 3 — Progress Report

Output only:
```
Processed N rules (DONE_NOW/TOTAL). Files updated: file1.csv, file2.csv
```

If all rules complete, proceed immediately to Step 4.

---

## Step 4 — Report Generation

Load all CSVs and compute statistics:

```bash
python3 -c "
import os, csv, json, glob
from collections import Counter

out_dir = 'migration/fm-hide-explorer'
all_rules = []
for f in sorted(glob.glob(os.path.join(out_dir, '*.csv'))):
    with open(f, newline='') as fh:
        for row in csv.DictReader(fh):
            row['_source_csv'] = os.path.basename(f)
            all_rules.append(row)

categories = Counter(r['category'] for r in all_rules)
auth_layers = Counter(r['auth_layer'] for r in all_rules if r.get('auth_layer'))
flags = Counter(r['flag'] for r in all_rules)
layouts = Counter(r['layout'] for r in all_rules)
duplicates = sum(1 for r in all_rules if r.get('duplicate_of', '').strip())
unique = len(all_rules) - duplicates

auth_rules = [r for r in all_rules if r['category'] in ('authorization', 'permission-flag', 'record-sensitivity') and not r.get('duplicate_of', '').strip()]
state_rules = [r for r in all_rules if r['category'] in ('session-state', 'workflow-state', 'ui-context') and not r.get('duplicate_of', '').strip()]
noise_rules = [r for r in all_rules if r['category'] in ('constant', 'deprecated', 'platform')]
flagged = [r for r in all_rules if r['flag'] == 'needs-review']

print(f'Total rules: {len(all_rules)}')
print(f'Unique formulas: {unique}, Duplicates: {duplicates}')
print(f'Authorization rules: {len(auth_rules)}')
print(f'State/workflow rules: {len(state_rules)}')
print(f'Noise rules: {len(noise_rules)}')
print(f'Needs review: {len(flagged)}')
print(f'Auth layers found: {dict(auth_layers)}')
print(f'Categories: {dict(categories)}')
"
```

Generate four reports in `migration/fm-hide-explorer/reports/`:

### 4A. Summary (`reports/summary.md`)

```markdown
# Hide-Object-When Analysis

## Overview
- Total rules: N across N layouts
- Unique formulas: N (N duplicates)
- Authorization rules: N — N%
- State/workflow rules: N — N%
- Noise (constant, deprecated, platform): N — N%
- Flagged for review: N

## Authorization Model

Document the complete access control model found in the formulas, layer by layer:

### Layer N: [Layer Name]
- **Mechanism:** how the check works
- **Rule count:** N unique formulas
- **Variables/fields involved:** list of $$vars, field names
- **Roles/values:** privilege set names, permission flag names, record flag values

## State Machines & Workflows
For each identified workflow:
### [Workflow Name]
- States and transitions encoded in formulas
- Session variable driving the state
- UI elements controlled by each state

## Flagged for Review
| Layout | Object | Formula | Why Flagged |
|---|---|---|---|

## Top Layouts by Rule Count
Table: layout, auth count, state count, noise count, flagged count.
```

### 4B. Auth Model (`reports/auth-model.md`)

Every unique authorization, permission-flag, and record-sensitivity rule:

```markdown
# Authorization Rules

> The complete access control model derived from hide-object-when formulas.
> Organized by authorization layer.

## Layer N: [Layer Name] (N unique formulas)

Context for what this layer controls.

| Index | Formula | Auth Layer | Layouts | Occurrences | Meaning | Migration Target |
|---|---|---|---|---|---|---|
```

### 4C. State Rules (`reports/state-rules.md`)

Every unique session-state, workflow-state, and ui-context rule:

```markdown
# State & Workflow Rules

> Rules that control visibility based on application state, workflow position,
> or UI context. These encode the application's progressive disclosure and
> workflow state machines.

## Session State (N unique formulas)
| Index | Formula | Layouts | Occurrences | Meaning | Migration Target |

## Workflow State (N unique formulas)
| Index | Formula | Layouts | Occurrences | Meaning | Migration Target |

## UI Context (N unique formulas)
| Index | Formula | Layouts | Occurrences | Meaning | Migration Target |
```

### 4D. Noise Catalog (`reports/noise-catalog.md`)

Every constant, deprecated, and platform rule — documented, not dismissed:

```markdown
# Noise Catalog

> Rules not required for migration logic. Documented so nothing is silently dropped.
> Review the Constant section carefully — some permanently-hidden objects may be
> disabled features that need a migration decision, not dead code.

## Constant Rules (N) — Always Hidden or Always Visible
| Index | Layout | Object | Formula | Notes |

## Deprecated Rules (N) — References Missing Elements
| Index | Layout | Object | Formula | Missing Reference | Notes |

## Platform Rules (N) — Desktop/Mobile/WebDirect Branches
| Index | Layout | Object | Formula | Platform Target | Notes |
```

---

### Report Quality Standards

- **Name the authorization layers explicitly.** If you find role checks, permission flags, record sensitivity, and SQL-based checks, that is a 4-layer auth model. Document each layer by name.
- **Track session variables.** Build a complete inventory of every `$$variable` found — use count, what layer it serves, what it contains.
- **Constant rules get notes.** A formula of `1` on an object named `portal_legacy_billing` is not obviously dead code — note the object name and let a human decide.
- **Flagged items explain the ambiguity specifically.** "Formula references both role and a record flag — unclear which takes precedence" is actionable. "Unclear" is not.

### Step 5 — Final Output

```
Reports generated in migration/fm-hide-explorer/reports/:
  summary.md           — N rules, N-layer auth model, N state machines, N flagged
  auth-model.md        — N authorization formulas by layer
  state-rules.md       — N state/workflow formulas by category
  noise-catalog.md     — N constant + N deprecated + N platform rules documented
```
