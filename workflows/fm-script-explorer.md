# Script Explorer

Internal workflow for deep-dive analysis of every FileMaker script from `ddr/specs/05_scripts.json`. Input mode: `count`, `all`, or `reports`; for example, `count=5`.

You are documenting FileMaker scripts from a DDR export. Use the input mode selected by the main skill. Process scripts starting from where the CSVs left off, then stop.

**This is careful documentation work, not a fast lookup.** Your job is to use *your own intelligence* on every script. For each script, you read every step yourself, build a mental model of what the script does, and only then write the row. Do not skim. Do not pattern-match step names into a list. Do not infer purpose from the script name. Python is for moving data around (extracting JSON, writing CSV) — it is not allowed to write the `type`, `purpose`, or `result` fields. Those are always written by you, the model, after reading the steps.

You are writing a **high-level summary**, not a translation of the FM steps into English prose. A dev who needs the step-level detail can open `ddr/specs/05_scripts.json` and read it. The CSV exists to give a fast scannable understanding of *what kind of script this is*, *why it exists*, and *what changes when it runs* — so you can find the right scripts to study, group them by intent, and plan the migration.

If the user gives you a large batch (e.g. 100) and you find yourself wanting to speed up — slow down instead. Quality per script matters more than throughput.

---

## Output Structure

```
migration/fm-scripts-explorer/
  ├── *.csv                      ← one CSV per FM script group
  └── reports/
      ├── summary.md             ← high-level narrative overview
      ├── tier1-critical.md      ← all tier1-critical scripts by module
      ├── data-writes.md         ← all data-write scripts by module
      ├── batch-integration-import.md
      ├── triggers-dispatchers-validation.md
      └── out-of-scope-audit.md
```

## CSV Format

Each file has a header:

```
index,group,script_name,module,type,purpose,result,logic_tier
```

- `index` — 0-based position in `ddr/specs/05_scripts.json`
- `group` — FM script group/folder path (from the JSON)
- `script_name` — FM script name (from the JSON)
- `module` — functional business domain this script belongs to (see Module Classification below)
- `type` — short tag for the kind of script (controlled vocabulary below)
- `purpose` — one sentence on *why this script exists* in business terms
- `result` — one sentence on *what changes for the user or the data* when it runs
- `logic_tier` — `none` | `read-only` | `tier2` | `tier1-critical`

## Module Classification

Modules represent the functional business domains of the application. Derive them dynamically:

1. **If `migration/00_app_summary.md` exists** — read the Feature Map section. The functional domains listed there are your module vocabulary. Map each script to the domain that best matches its tables, fields, and logic.

2. **If no app summary exists** — derive modules from script group paths and the tables each script targets. Group similar scripts into domains using table names and script behavior as signals. Use short, lowercase, hyphenated names (e.g., `invoicing`, `user-management`, `reporting`).

3. **Universal modules** (always available regardless of application):
   - `infrastructure` — startup, session, configuration, post-migration utilities, developer tools
   - `deprecated` — scripts explicitly marked for deletion or superseded by newer versions
   - `out-of-scope` — scripts belonging to features excluded from the migration scope (confirm by reading steps and checking discovery answers if available)
   - `unknown` — cannot confidently classify; needs human review

Use the group name and script name as initial signals, but always read the steps before deciding. Scripts are sometimes miscategorized in their FM groups.

---

## Step 1 — Check Progress

```bash
python3 -c "
import os, json, glob, csv

out_dir = 'migration/fm-scripts-explorer'
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

with open('ddr/specs/05_scripts.json') as f:
    total = len(json.load(f))

print(done, next_idx, total)
"
```

This gives you `DONE NEXT_IDX TOTAL`.

**Interpreting the input mode:**
- If blank or not a number → default batch size = 1
- If a positive integer → batch size = that number
- If `"all"` → batch size = TOTAL - DONE
- If `"reports"` → skip to Step 4 (Report Generation)

If DONE >= TOTAL and the input mode is not `"reports"`, skip to Step 4 automatically.

---

## Step 2 — Process the Batch

For each script from index NEXT_IDX to NEXT_IDX+BATCH-1, do all of A through G **per script** before moving on to the next. Do not batch-extract many scripts at once and skim them — extract one, read it, classify it, write the row, then go to the next.

### A. Extract the script

```bash
python3 -c "
import json, sys
with open('ddr/specs/05_scripts.json') as f:
    scripts = json.load(f)
idx = int(sys.argv[1])
if idx >= len(scripts):
    print('DONE')
else:
    print(json.dumps(scripts[idx], indent=2))
" INDEX
```

### B. Read EVERY step

You — the model — must read every step in the script's `steps` array. Not the first three. Not just the named step types. Every step, including its `params`. Comment-only steps can be ignored, but every other active step gets your attention.

Fields in each step:
- `name` — the FM step type (e.g. "Set Variable", "Perform Script", "If", etc.)
- `params` — the step's arguments (variable names, field names, calculations, script references, layouts, etc.) — these are where the actual logic lives
- `enable` — "True" or "False"; disabled steps are dead code, ignore them

### C. Build a mental model — answer these before writing

Before writing the row, you must be able to answer:

1. **Parameter signature** — what does the script receive? Look for `Set Variable` steps at the top reading from `Get(ScriptParameter)` or splitting `$prm`. Arguments, not work.
2. **Tables and fields written** — every `Set Field`, `Replace Field Contents`, `New Record/Request`, `Delete Record/Request` on a real table.
3. **Scripts called** — every `Perform Script` and the parameter passed.
4. **Find/loop logic** — what record set does the script operate on? What does each iteration do?
5. **External effects** — `Insert from URL` (API call), `Open URL`, `Send Mail`, file exports, window open/close.
6. **The big question:** *"What kind of script is this, why does it exist, and what is different in the user's view or the data after it runs?"*

If you cannot answer #6 in plain English, you have not read the script carefully enough. Re-read it.

### D. Writing type / purpose / result

You are writing **three short fields**, not a translation of the script. Aim for the level a teammate would describe it to you in conversation: "Oh, that's a UI dispatcher — it handles the notification card open/dismiss flows. After it runs, the card is open and the visible notifications are marked read."

#### `type` — controlled vocabulary

Pick the dominant intent. If a script is mixed (e.g. a dispatcher that also writes data), pick the tag that best captures *why a developer would reach for this script*.

| tag | meaning |
|-----|---------|
| `ui dispatcher` | branches on a `$function`/`$mode`-style argument to drive multiple UI actions; the branches are the point of the script |
| `data write` | creates, updates, or deletes records — the script exists to change persistent data |
| `batch job` | loops over a found set or list, applying an operation to each item |
| `integration` | outbound call to an external system (`Insert from URL`, `Send Mail`, `Open URL`, file export to a watched folder) |
| `import` | inbound load — parses external data and writes records |
| `report` | produces output for a user (PDF, print, export, summary screen) |
| `navigation` | layout/window switching to set up a screen — no business logic |
| `utility` | small reusable helper called by other scripts; no clear standalone business purpose |
| `trigger handler` | invoked by a layout/field/script trigger event (look for triggering context clues) |
| `validation` | checks state and raises errors or warnings; no writes |
| `setup` | initializes globals, session state, or UI state (no record writes) |
| `dispatcher` | branches on a parameter to call other scripts (router) |

If none of these fit, invent a short tag (1–2 words, lowercase, no punctuation) — but try the list first.

#### `purpose` — one sentence, business-level

State *why this script exists* in terms a non-FM-developer would understand. Skip the FM mechanics. Examples:

- **good:** `Open the notifications panel for a specific user and program`
- **good:** `Generic search-filter handler shared across embedded portal widgets`
- **good:** `Mark a speaker as removed from a program assignment`
- **bad:** `Sets variables and navigates to a layout` (mechanics, not purpose)
- **bad:** `Handles dashboard notifications` (just restates the script name)

#### `result` — one sentence, observable outcome

State *what is different* after the script runs — for the user, the data, or the outside world. Examples:

- **good:** `Notifications window opens scoped to one user and program; all displayed notifications are marked read`
- **good:** `A named portal is filtered, cleared, or relaunched depending on the function argument`
- **bad:** `Variables are set` (no observable outcome)
- **bad:** `Navigates to a layout` (no outcome)

If the script's only observable effect is showing a dialog, opening a window, or otherwise UI-only, say so plainly: `A confirmation dialog is shown` or `An empty record-entry card is opened`.

If the active steps are all comments or boilerplate with no real logic, set `type = utility`, `purpose = No meaningful logic — comments and boilerplate only.`, `result = (none)`, `logic_tier = none`.

### E. Classify

**module** — see Module Classification section above. Use group path and script name as signals, but read the steps before deciding.

**logic_tier:**
- `none` — navigation, UI setup, empty, or commented-out only
- `read-only` — reads/filters/displays data, no record writes
- `tier2` — writes data but standard CRUD; no special rules
- `tier1-critical` — financial calculations, multi-step transactions, complex conditionals, data integrity rules — anything that would be wrong to reimplement without fully understanding

### F. Self-check before writing the row

Re-read your draft. Reject and rewrite if any of these are true:

- `type` is not from the controlled vocabulary and isn't a clearly better short tag.
- `purpose` describes mechanics ("sets fields", "navigates", "commits") instead of why the script exists.
- `purpose` just restates the script name.
- `result` describes a step rather than an observable outcome.
- `purpose` or `result` exceeds ~25 words. Tighten it.
- `type` and `purpose` contradict each other (e.g. `type=data write` but `purpose` describes opening a UI window).

Only after the self-check passes do you write the row.

### G. Write the row

Determine the output filename from the group name:

```bash
python3 -c "
import re, sys
group = sys.argv[1]
filename = re.sub(r'[\s/\\\\]+', '_', group).lower().strip('_')
print(filename + '.csv')
" 'GROUP'
```

If the file does not yet exist, create it with the header first:

```bash
python3 -c "
import os, sys
path = sys.argv[1]
if not os.path.exists(path):
    with open(path, 'w') as f:
        f.write('index,group,script_name,module,type,purpose,result,logic_tier\n')
" 'migration/fm-scripts-explorer/FILENAME'
```

Append the row using Python (handles quoting and commas correctly):

```bash
python3 -c "
import csv, sys
fields = sys.argv[1:]
with open(fields[0], 'a', newline='') as f:
    csv.writer(f).writerow(fields[1:])
" 'migration/fm-scripts-explorer/FILENAME' 'INDEX' 'GROUP' 'SCRIPT_NAME' 'MODULE' 'TYPE' 'PURPOSE' 'RESULT' 'LOGIC_TIER'
```

---

## Step 3 — Progress Report

Keep terminal output minimal — the user reads the CSVs directly. Output only:

```
Processed N scripts (DONE_NOW/TOTAL). Files updated: file1.csv, file2.csv
```

If all scripts are now complete (DONE_NOW >= TOTAL), proceed immediately to Step 4.

---

## Step 4 — Report Generation

Generate six report documents that synthesize the CSV data into actionable migration intelligence. These reports are the primary deliverable — the CSVs are the data layer; the reports are the analysis layer.

Create `migration/fm-scripts-explorer/reports/` if it doesn't exist.

Before generating, load all CSVs into memory using Python:

```bash
python3 -c "
import os, csv, json, glob

out_dir = 'migration/fm-scripts-explorer'
all_scripts = []
for f in sorted(glob.glob(os.path.join(out_dir, '*.csv'))):
    with open(f, newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row['_source_csv'] = os.path.basename(f)
            all_scripts.append(row)

# Print summary stats for report planning
from collections import Counter
tiers = Counter(s['logic_tier'] for s in all_scripts)
types = Counter(s['type'] for s in all_scripts)
modules = Counter(s['module'] for s in all_scripts)

print(f'Total scripts: {len(all_scripts)}')
print(f'Tiers: {dict(tiers)}')
print(f'Types: {dict(types)}')
print(f'Modules: {dict(modules)}')
print('---')

# Group by category for report planning
tier1 = [s for s in all_scripts if s['logic_tier'] == 'tier1-critical']
writes = [s for s in all_scripts if s['type'] == 'data write']
batch = [s for s in all_scripts if s['type'] in ('batch job', 'integration', 'import')]
triggers = [s for s in all_scripts if s['type'] in ('trigger handler', 'dispatcher', 'ui dispatcher', 'validation')]
excluded = [s for s in all_scripts if s['module'] in ('out-of-scope', 'deprecated')]

# Count active vs excluded
active = [s for s in all_scripts if s['module'] not in ('out-of-scope', 'deprecated')]
print(f'Active: {len(active)}, Excluded: {len(excluded)}')
print(f'Tier1: {len(tier1)}, Data writes: {len(writes)}, Batch/integ/import: {len(batch)}')
print(f'Triggers/dispatchers/validation: {len(triggers)}')
"
```

Use these counts to plan, then generate each report. **You — the model — write the analysis.** Python extracts and groups the CSV data; you interpret it and write the narrative.

### 4A. Summary Report (`reports/summary.md`)

This is the most important report. A reader should be able to understand the entire script landscape from this document alone.

**Structure:**

```markdown
# Script Explorer Summary

## Overview
- Total scripts analyzed, active vs. excluded counts
- Module breakdown table (module | active | deprecated | out-of-scope)
- Type distribution table (type | count)
- Tier distribution table (tier | count)

## Application Architecture (as revealed by scripts)
What does the script landscape tell you about how this application works?
Describe the architectural patterns: how data flows, how users interact,
what the backbone operations are. This is YOUR analysis, not a list.

## Module-by-Module Analysis
For each module (sorted by script count, descending):
- What this module does (2-3 sentences)
- Key scripts and their roles
- Patterns: CRUD, batch processing, integrations, event handling
- Migration notes: what's straightforward vs. what needs careful attention

## Backbone Scripts
Identify the 5-10 most architecturally important scripts — the ones that,
if they broke, would bring down major workflows. Explain why each matters.

## Hardest to Migrate
Scripts or patterns that will require the most careful translation:
- Complex multi-table transactions
- Custom algorithms or business rules
- Integration points with external systems
- Scripts with high calculation density

## Hidden Requirements
Business rules or behaviors that only become visible by reading the script
logic — things not obvious from the data model or UI alone.

## Statistics
Full count tables for reference.
```

### 4B. Tier 1 Critical Catalog (`reports/tier1-critical.md`)

**Structure:**

```markdown
# Tier 1 Critical Scripts

> Scripts containing financial calculations, multi-step transactions,
> complex conditionals, or data integrity rules that would be wrong
> to reimplement without full understanding.

Total: N scripts (N active, N deprecated)

## [Module Name] (N scripts)

Brief context for what this module's critical scripts handle.

| Source CSV | Index | Script Name | Type | Purpose | Result |
|------------|-------|-------------|------|---------|--------|
| ... | ... | ... | ... | ... | ... |

[Repeat for each module containing tier1 scripts]
```

### 4C. Data Writes Catalog (`reports/data-writes.md`)

**Structure:**

```markdown
# Data Write Scripts

> Scripts that create, update, or delete records — the persistent
> data mutation layer of the application.

Total: N scripts (N active, N deprecated)

## [Module Name] (N scripts)

Brief context for this module's data operations.

| Source CSV | Index | Script Name | Logic Tier | Purpose | Result |
|------------|-------|-------------|------------|---------|--------|
| ... | ... | ... | ... | ... | ... |

[Repeat for each module]
```

### 4D. Batch, Integration & Import Catalog (`reports/batch-integration-import.md`)

**Structure:**

```markdown
# Batch Jobs, Integrations & Imports

> Scripts that process sets of records, communicate with external
> systems, or ingest data from outside sources.

Total: N scripts — N batch jobs, N integrations, N imports

## Batch Jobs (N scripts)

### [Module Name] (N)
| Source CSV | Index | Script Name | Logic Tier | Purpose | Result |
| ... |

## Integrations (N scripts)

### [Module Name] (N)
| ... |

## Imports (N scripts)

### [Module Name] (N)
| ... |
```

### 4E. Triggers, Dispatchers & Validation (`reports/triggers-dispatchers-validation.md`)

**Structure:**

```markdown
# Trigger Handlers, Dispatchers & Validation

> Event-driven scripts: layout/field triggers, parameter-based
> routers, and state-checking guards.

Total: N scripts — N trigger handlers, N dispatchers,
N UI dispatchers, N validation

## Trigger Handlers (N scripts)

### [Module Name] (N)
| Source CSV | Index | Script Name | Logic Tier | Purpose | Result |
| ... |

## Dispatchers (N scripts)
[same structure]

## UI Dispatchers (N scripts)
[same structure]

## Validation (N scripts)
[same structure]
```

### 4F. Out-of-Scope & Deprecated Audit (`reports/out-of-scope-audit.md`)

**Structure:**

```markdown
# Out-of-Scope & Deprecated Scripts

> Scripts excluded from migration: features dropped from scope,
> superseded versions, and dead code.

Total: N scripts — N out-of-scope, N deprecated

## Out-of-Scope Scripts (N)

Organized by source CSV file. For each file:

### [csv_filename] (N scripts)

Why these are out-of-scope (infer from module, group, and purpose).

| Script Name | Type | Logic Tier | Purpose |
| ... |

## Deprecated Scripts (N)

### [csv_filename] (N scripts)
| Script Name | Type | Logic Tier | Purpose | Why Deprecated |
| ... |

## Potentially Misclassified

Any scripts where the out-of-scope or deprecated classification
seems uncertain. Flag for human review.
```

### Report Quality Standards

For all reports:
- **Write analysis, not data dumps.** The tables are supporting evidence; your narrative is the value.
- **Cross-reference modules.** When scripts in one module call scripts in another, note the dependency.
- **Flag migration risks.** Any script that will be hard to translate gets a brief note on why.
- **Be specific.** "Complex business logic" is useless. "Three-way payment split with currency conversion and rounding reconciliation" is actionable.
- **Keep it scannable.** Use tables for lists, prose for analysis. A reader should find what they need in under 30 seconds.

### Step 5 — Final Output

After generating all reports, output:

```
Reports generated in migration/fm-scripts-explorer/reports/:
  summary.md             — Application script landscape overview
  tier1-critical.md      — N tier1-critical scripts by module
  data-writes.md         — N data-write scripts by module
  batch-integration-import.md — N batch/integration/import scripts
  triggers-dispatchers-validation.md — N event-driven scripts
  out-of-scope-audit.md  — N excluded scripts with audit trail
```
