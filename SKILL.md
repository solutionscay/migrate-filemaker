---
name: migrate-filemaker
description: Turn a FileMaker Database Design Report (DDR XML) into a complete migration plan - schema, business logic, authorization, API, UI, data migration and cutover. Use when given FileMaker DDR XML, or asked to analyze, document, or plan the rebuild of a FileMaker solution.
---

# FileMaker Migration Planner

Take the DDR apart into every object, read every object, and write the migration plan from what the objects say.

## Rules

1. Record what the FileMaker solution does, as written, with the object file as evidence. Do not judge whether its logic is correct. That is not the job.
2. Label each statement in an artifact as fact (from an object file), inference, product decision, or unavailable. Never invent behavior the DDR does not show.
3. Raw DDR XML is client data. Keep it out of version control.

## Paths

```bash
SKILL_DIR="/path/to/migrate-filemaker"
RAW_DIR="/path/to/ddr-export"        # the DDR XML files, plus Summary.xml when present
OUT_DIR="/path/to/migration"         # everything this skill writes
```

## Step 1: Extract everything

```bash
python3 "$SKILL_DIR/scripts/explode_ddr.py" "$RAW_DIR" "$OUT_DIR/objects"
```

- `objects/<file>/<kind>/<id>-<name>.txt` is one text file per object: scripts as numbered steps, tables with every field option, layouts as their object tree (labels, tooltips, triggers, buttons, hide rules, conditional formats, portal filters), table occurrences with their relationships, value lists, custom functions, custom menus, accounts, privilege sets, data sources, file options.
- Every calculation shows its text and a `refs:` line with the fields (`TO::field#id`) and custom functions it uses.
- `objects/index.tsv` lists every object: file, kind, id, name, folder, path, hash, lines.
- `objects/LEGEND.md` explains the markers and every code that appears in the object files. Read it once before Step 3.
- `objects/unresolved.tsv` lists every reference whose target is deleted (`ref=none`, `ref=missing`) or in a file that was not exported (`ref=external`).
- The run stops with an error if any calculation or attribute check fails. Fix the extraction before going on.
- Object files carry every value exactly as the DDR has it.

The object files are the reading surface. Find usage with `grep -rl 'Invoices::total#' "$OUT_DIR/objects"`, then read the hits in full.

## Step 2: Inventory

Write `00_app_summary.md` from [templates/00_app_summary.md](templates/00_app_summary.md). Count every kind in `objects/index.tsv`. List the files and how they reference each other (their `data-sources` objects).

## Step 3: Read every object

Every row of `objects/index.tsv` is read in full and gets one CSV row. Each explorer snapshots its kinds with `scripts/catalog_contract.py`, and `verify` proves that every object has exactly one row (see [reference/explorer-contract.md](reference/explorer-contract.md)).

- Scripts: [workflows/fm-script-explorer.md](workflows/fm-script-explorer.md)
- Custom functions: [workflows/fm-func-explorer.md](workflows/fm-func-explorer.md)
- Tables, with calculated fields, auto-enter and validation: [workflows/fm-table-explorer.md](workflows/fm-table-explorer.md)
- Layouts, with hide rules, conditional formats, triggers, buttons, tooltips and portal filters: [workflows/fm-layout-explorer.md](workflows/fm-layout-explorer.md)
- Table occurrences and relationships: [workflows/fm-graph-explorer.md](workflows/fm-graph-explorer.md)
- Privilege sets, accounts and extended privileges: [workflows/fm-security-explorer.md](workflows/fm-security-explorer.md)
- Value lists: [workflows/fm-value-list-explorer.md](workflows/fm-value-list-explorer.md)
- Custom menus and menu sets: [workflows/fm-menu-explorer.md](workflows/fm-menu-explorer.md)
- File options, data sources, and every other kind: [workflows/fm-file-explorer.md](workflows/fm-file-explorer.md)

Large solutions have thousands of objects and hundreds of thousands of lines. The catalog splits each kind into batches of at most 50 objects or 6000 lines (one CSV each). Give each agent whole batches and run them in parallel:

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" assign --agents 20 --output "$OUT_DIR/explorers/assignments" \
  --catalog "$OUT_DIR/explorers/layouts/catalog.json" --catalog ...
```

- `assign` packs whole batches into agents of near-equal lines; one TSV per agent. About 20,000 object lines is a fair share for one agent: on a 4,500-object solution that took 22 agents of 4 to 10 minutes each. Pack one explorer per agent where you can, so each agent reads one workflow.
- Each agent proves its own share with `verify --catalog ... --csv-root ... --assignment <its tsv>` before it reports.
- An agent may use a helper script to pre-fill mechanical columns (counts, callers, census lines). It still reads each object and writes the meaning, purpose and target columns itself.
- Ask each agent to report skill problems it hit. Fix the workflow before the next run, not during one: a changed object file changes its hash and voids its row.

## Step 4: Discovery questions

Write `01_discovery_answers.md` from [templates/01_discovery_answers.md](templates/01_discovery_answers.md). Ask only what the objects cannot tell: goals, scope, users, identity provider, data volume, integrations, and which behaviors to keep, change, or drop. With no one to answer, list the questions and continue.

Start with the questions the catalogs raise. Collect every `open_question`, every `drop-candidate` and `unresolved` target, every `callers`, `used_by` or `installed_by` of `none found`, every graph `use` of `unused`, and every row of `objects/unresolved.tsv`. A large solution raises thousands of these signals. Group them into questions that one answer settles ("are the 284 layouts with no caller still used?"), and keep the full list as `01_discovery_signals.tsv`. Rank the questions by what the answer changes in the plan. Do not cap the list; the owner answers from the top and can stop at any point.

Give every answer an ID (`D-01`, `D-02`, ...). When an answer is "I don't know", record the default you assume, who can decide, and which increment waits on it.

## Step 5: Write the migration plan

Write each artifact from its template, citing object files as evidence. Cite an object file as `objects/<path>`, where `<path>` is its `path` in `objects/index.tsv`.

| Artifact | Template | Reference |
|---|---|---|
| `04_database_schema.sql` | [templates/04_database_schema.sql](templates/04_database_schema.sql) | [reference/schema-translation-guide.md](reference/schema-translation-guide.md) |
| `07_business_logic.md` | [templates/07_business_logic.md](templates/07_business_logic.md) | [reference/script-translation-patterns.md](reference/script-translation-patterns.md), [reference/business-logic-detection.md](reference/business-logic-detection.md) |
| `08_auth_roles.md` | [templates/08_auth_roles.md](templates/08_auth_roles.md) | |
| `05_api_design.md` | [templates/05_api_design.md](templates/05_api_design.md) | |
| `06_ui_spec.md` | [templates/06_ui_spec.md](templates/06_ui_spec.md) | |
| `02_recommendations.md` | [templates/02_recommendations.md](templates/02_recommendations.md) | [reference/tech-stack-decision-matrix.md](reference/tech-stack-decision-matrix.md) |
| `03_migration_plan.md` | [templates/03_migration_plan.md](templates/03_migration_plan.md) | |

Write them in this order. Each one builds on the ones above it. `07` owns the business rules and `08` owns the authorization policies; the other artifacts cite their rule and policy ids and do not restate them. Where a decision rests on a discovery answer, cite its `D-` id.

Some links point forward: `07` names the policy that guards each operation, and `04` and `05` make stack choices that `02` confirms. Write each artifact with the ids it can know, then make one reconcile pass after `03`: fill forward ids, and make every cited id, table and column exist in the artifact that owns it.

Shared conventions, so artifacts written by different agents line up:

- Target tables and columns: snake_case of the FileMaker name. Split at each lower-to-upper change and at each letter-digit change, and keep a run of capitals together (`FileMaker_AccountName` -> `file_maker_account_name`, `Invoice_Lines` -> `invoice_lines`, `SKU_Code` -> `sku_code`).
- Ids: rules `BR-<DOMAIN>-<nn>` and operations `OP-<DOMAIN>-<nn>` (07), roles `ROLE-<NAME>` and policies `AP-<nn>` (08), screens `UI-<nn>` (06), background jobs `JOB-<nn>` and integrations `EXT-<nn>` (05), increments `I<n>` (03), open decisions `OD-<artifact>-<nn>`, tests `T-<artifact>-<nn>`. Pick the domain list once and give it to every writer.
- A large inventory (every field, layout, script or table-by-role cell) goes in `<artifact>_appendix.md` (or `.csv`), generated from the catalogs. The template's tables then hold the important rows and point to the appendix.

Without discovery answers or a chosen stack, write the artifacts anyway and mark each product decision open.

For FileMaker behavior, see [reference/filemaker-concepts.md](reference/filemaker-concepts.md). For the DDR format, see [reference/ddr-xml-reference.md](reference/ddr-xml-reference.md).

## Step 6: Audit the plan against the objects

Before you call the plan done, check that it rests on what the objects say, not on what the catalogs guessed.

- Re-read the object file behind each tier1 rule in `07_business_logic.md`. Fix the plan where the rule is wrong, keep the rule's id, and mark the fix. Use a reader who did not write `07`: on a 1,200-script solution an author who had read every tier1 object still had 17% of rules wrong, and only a second reader caught them.
- List what the plan still does not understand: unanswered questions, `unresolved` targets, and rows of `objects/unresolved.tsv`. Name the part of the plan each gap affects.

Write the result to `09_audit.md`. The operator decides which gaps matter. A gap the operator accepts stays listed and does not block the plan.

## Done when

- Every kind in `objects/index.tsv` is in one explorer's catalog, and `catalog_contract.py verify` passes for every explorer.
- Every artifact in Step 5 exists, cites object files, and lists its open decisions.
- `09_audit.md` lists every gap and the part of the plan it affects.
