# UI Spec Builder

Internal workflow for generating a complete frontend UI specification from a FileMaker DDR export and migration discovery answers. Writes `migration/06_ui_spec.md`.

You are generating a complete frontend UI specification for a FileMaker migration. Your job is to map every FileMaker layout to a modern page, translate FM UI elements to modern component equivalents, incorporate the user's design direction from discovery, and surface the business logic embedded in conditional visibility and formatting rules.

**This spec is what a frontend developer builds from.** It must be complete enough that a developer can implement every screen without referencing any other document. Do not skim the form specs or component mapping — the detail here is the value.

---

## Step 1 — Check Prerequisites

Verify required inputs exist:

```bash
ls migration/01_discovery_answers.md migration/00_app_summary.md ddr/specs/04_layouts.json 2>/dev/null
```

Check for optional inputs:

```bash
ls migration/fm-hide-explorer/reports/summary.md 2>/dev/null && echo "Hide-object explorer: available" || echo "Hide-object explorer: not run"
ls migration/fm-cf-explorer/reports/summary.md 2>/dev/null && echo "Conditional formatting explorer: available" || echo "Conditional formatting explorer: not run"
ls migration/fm-scripts-explorer/reports/summary.md 2>/dev/null && echo "Script explorer: available" || echo "Script explorer: not run"
```

If `migration/01_discovery_answers.md` is missing, stop:
> "Discovery answers not found. Complete Phase 2 first — the UI spec depends on the user's design direction from discovery."

If `ddr/specs/04_layouts.json` is missing, stop:
> "Layout specs not found. Run the DDR parser first with `/migrate-filemaker <path-to-ddr>`."

Note which optional inputs are available — Hide-Object-When and Conditional Formatting Explorer reports significantly enrich conditional visibility, auth, and visual-state sections.

---

## Step 2 — Profile the Layouts

Extract a layout inventory:

```bash
python3 -c "
import json
from collections import Counter

with open('ddr/specs/04_layouts.json') as f:
    layouts = json.load(f)

print(f'Total layouts: {len(layouts)}')

by_table = Counter(l.get('table', 'unknown') for l in layouts)
print('Layouts by table:')
for table, count in by_table.most_common():
    print(f'  {table}: {count}')

print('Layouts with portals/tabs:')
for l in layouts:
    portals = l.get('portals', [])
    tabs = l.get('tab_controls', [])
    buttons = l.get('buttons', [])
    if portals or tabs:
        print(f\"  {l['name']}: {len(portals)} portals, {len(tabs)} tab controls, {len(buttons)} buttons\")
"
```

Then read:
- `migration/01_discovery_answers.md` — focus on Group 2 (access patterns) and Group 3 (UI style, screenshots, reference apps)
- `migration/00_app_summary.md` — feature map, script navigation patterns, UI summary
- `migration/fm-hide-explorer/reports/` — if available: `summary.md`, `auth-model.md`, `state-rules.md`
- `migration/fm-cf-explorer/reports/` — if available: `summary.md`, `business-logic-catalog.md`
- `migration/fm-scripts-explorer/reports/summary.md` — if available: navigation patterns, UI dispatchers

---

## Step 3 — Generate the UI Spec

Use [templates/06_ui_spec.md](../templates/06_ui_spec.md) as the structural scaffold. Consult [reference/filemaker-concepts.md](../reference/filemaker-concepts.md) for FM-to-modern UI element mapping.

### 3A. Design Direction

Summarize:
- **Target style** from the user's Discovery Group 3 answer (clean/minimal, data-dense, match FM look, or custom)
- **Current FM app observations** from any screenshots the user provided — layout density, color usage, navigation patterns, what works and what the user wants changed
- **Reference apps** the user cited with a note on what to emulate from each
- **Design tokens** derived from the style direction: border radius, density, color palette, typography

### 3B. Navigation Structure

Derive the navigation structure from:
- FM layouts used as navigation hubs (home screens, menu layouts)
- Groups of "Go To Layout" scripts — these reveal the app's information architecture
- The feature map domains from Phase 1

Draw the proposed nav structure as an ASCII tree. Note explicitly how FM's button-driven navigation maps to a sidebar or top-nav with standard route links.

### 3C. Page Inventory

Map every user-facing FM layout to a modern route and component:

| FM Layout | Route | Component | Type | Description |
|---|---|---|---|---|

Types: `List` / `Form` / `Dashboard` / `Report` / `Modal` / `Settings`

**Pages to drop:** FM layouts with no modern equivalent (dedicated print layouts, developer tools, pure navigation hubs that become sidebar links). Explain the reason for each.

### 3D. Component Mapping

Map FM UI elements to modern equivalents. Start from the standard mapping in `reference/filemaker-concepts.md`, then add application-specific behavior notes:

| FM Element | Modern Equivalent | Behavior Notes |
|---|---|---|

For complex components, provide full detail:

**Portals** — for each portal on a significant layout:
- Source table and fields
- Column list with data types
- Which columns are editable inline
- Inline calculations (e.g., line total = qty × unit_price)
- Add/remove row behavior, sort behavior
- Proposed component: editable data table, read-only sub-table, or collapsible list

**Tab Controls** — for each multi-tab layout:
- Tab names and content summary
- Any conditional tab visibility (if Hide-Object-When Explorer found hide rules on tabs, reference them here)

**Pop-overs and Slide Controls** — map to popover/dropdown, modal dialog, or multi-step wizard as appropriate

### 3E. Conditional Visibility

**If Hide-Object-When Explorer was run**, read `migration/fm-hide-explorer/reports/summary.md` and `migration/fm-hide-explorer/reports/state-rules.md`. Map each category to its modern implementation pattern:

| FM Hide Category | Modern Pattern | Implementation |
|---|---|---|
| Role check (`$$USER_privgroup`) | Route guard + `v-if` | Auth middleware checks `user.role` |
| Permission flag (`$$SENSITIVEDATA_*`) | Permission store + conditional | `v-if="can('view:sensitive')"` |
| Record-level flag | Component prop | `:visible="!record.isConfidential \|\| canViewConfidential"` |
| Session state (`data01 = ""`) | Reactive store | Store getter + `v-if` |
| Workflow state (`$$status = "sent"`) | State machine | XState enum or store enum |

For each named object with a hide rule, note which component receives a conditional prop and what condition drives it.

**If Hide-Object-When Explorer was NOT run**, flag the layouts with the most buttons and portals from the profile above as the highest-risk screens for hidden conditional logic. Recommend running the internal [fm-hide-explorer workflow](fm-hide-explorer.md) before implementation if the app has more than ~50 layouts.

### 3F. Conditional Formatting

**If Conditional Formatting Explorer was run**, read `migration/fm-cf-explorer/reports/summary.md` and `migration/fm-cf-explorer/reports/business-logic-catalog.md`. Map business-logic formatting rules to CSS class bindings or computed styles:

| FM Formula | Visual Effect | Modern Implementation |
|---|---|---|
| [formula] | [e.g., red fill when overdue] | `:class="{ 'text-red-600': isOverdue }"` |

Exclude cosmetic/noise rules (alternating row colors, alphabetical highlights) — implement those as standard table styling.

### 3G. Form Specs

For every data-entry layout, produce a complete field-by-field table. Do not skip fields.

**[Form Name] — [Route] — [Component]**

| Field Label | FM Field | Input Type | Validation | Conditional | Notes |
|---|---|---|---|---|---|

Input types: `text` / `email` / `number` / `date` / `time` / `select` / `multi-select` / `checkbox` / `radio` / `textarea` / `readonly` / `file-upload`

Validation: `required` / `email` / `min:N` / `max:N` / `pattern:regex` / `[custom]`

Conditional: "Show only if [condition]" — cross-reference Hide-Object-When Explorer rules where applicable.

Notes: calculated fields (readonly, value derived), value list sources, currency formatting, placeholder text.

### 3H. Responsive Requirements

Based on Discovery Group 2 (access patterns, mobile/offline needs):

| Device | Required | Priority | Notes |
|---|---|---|---|
| Desktop (1280px+) | [Yes/No] | [Primary/Secondary/Tertiary] | [Notes] |
| Tablet (768–1279px) | [Yes/No] | [...] | [...] |
| Mobile (<768px) | [Yes/No] | [...] | [...] |

State the responsive strategy (desktop-first vs. mobile-first). Note any mobile-specific requirements from discovery (large touch targets, offline capability, field use context).

---

## Step 4 — Write the File

Write the complete spec to `migration/06_ui_spec.md`.

After writing:
> "UI spec written to `migration/06_ui_spec.md`. [N] pages documented, [N] portals detailed, [N] form specs. [If Hide-Object-When Explorer was not run and the app has >50 layouts:] Consider running the internal hide-object explorer workflow before implementation — hide-object-when rules frequently encode the authorization model and will be needed to complete the conditional visibility section."
