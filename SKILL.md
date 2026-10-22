---
name: migrate-filemaker
description: Turn a FileMaker Database Design Report (DDR XML) into a complete migration plan - schema, business logic, authorization, API, UI, data migration and cutover. Use when given FileMaker DDR XML, or asked to analyze, document, or plan the rebuild of a FileMaker solution.
---

# FileMaker Migration Planner

Take the DDR apart into every object, read every object, and write the migration plan from what the objects say.

## Rules

1. Record what the FileMaker solution does, as written, with the object file as evidence. Do not judge whether its logic is correct. That is not the job.
2. Label each statement in an artifact as fact (from an object file), inference, product decision, or unavailable. Never invent behavior the DDR does not show.
3. Raw DDR XML is client data. Keep it out of version control. Never copy credentials into any artifact; the tools redact the ones they find.

## Paths

```bash
SKILL_DIR="/path/to/migrate-filemaker"
RAW_DIR="/path/to/ddr-export"        # the DDR XML files, plus Summary.xml when present
OUT_DIR="/path/to/migration"         # everything this skill writes
```

## Step 1: Extract everything

```bash
python3 "$SKILL_DIR/scripts/explode_ddr.py" "$RAW_DIR" "$OUT_DIR/objects"
python3 "$SKILL_DIR/scripts/parse_ddr.py"   "$RAW_DIR" "$OUT_DIR/specs"
```

- `objects/<file>/<kind>/<id>-<name>.txt` is one text file per object: scripts as numbered steps, tables with every field option, layouts as their object tree (labels, tooltips, triggers, buttons, hide rules, conditional formats, portal filters), table occurrences with their relationships, value lists, custom functions, custom menus, accounts, privilege sets, data sources, file options.
- Every calculation shows its text and a `refs:` line with the fields (`TO::field#id`) and custom functions it uses.
- `objects/index.tsv` lists every object: file, kind, id, name, folder, path, hash, lines.
- `specs/*.json` holds the same solution as structured JSON for counting and joining.
- If either command reports an error, stop and fix the extraction first.

The object files are the reading surface. Find usage with `grep -rl 'Invoices::total#' "$OUT_DIR/objects"`, then read the hits in full.

## Step 2: Inventory

Write `00_app_summary.md` from [templates/00_app_summary.md](templates/00_app_summary.md). Count every kind in `objects/index.tsv`. List the files, how they reference each other, and any unresolved references the parser printed.

## Step 3: Read every object

Go through every object kind and classify each object. Write one CSV row per object. Use `scripts/catalog_contract.py` to prove that every object has exactly one row (see [reference/explorer-contract.md](reference/explorer-contract.md)).

- Scripts: [workflows/fm-script-explorer.md](workflows/fm-script-explorer.md)
- Calculated fields, auto-enter and validation: [workflows/fm-calc-explorer.md](workflows/fm-calc-explorer.md)
- Custom functions: [workflows/fm-func-explorer.md](workflows/fm-func-explorer.md)
- Conditional formatting: [workflows/fm-cf-explorer.md](workflows/fm-cf-explorer.md)
- Hide rules: [workflows/fm-hide-explorer.md](workflows/fm-hide-explorer.md)
- Layouts and UI: [workflows/fm-ui-spec.md](workflows/fm-ui-spec.md)
- Tables and relationships: [workflows/fm-schema-builder.md](workflows/fm-schema-builder.md)

Large solutions have thousands of objects. Split each kind into batches, run batches in parallel, and merge the rows by object id.

## Step 4: Discovery questions

Write `01_discovery_answers.md` from [templates/01_discovery_answers.md](templates/01_discovery_answers.md). Ask only what the objects cannot tell: goals, scope, users, identity provider, data volume, integrations, and which behaviors to keep, change, or drop. With no one to answer, list the questions and continue.

## Step 5: Write the migration plan

Write each artifact from its template, citing object files as evidence:

| Artifact | Template | Reference |
|---|---|---|
| `02_recommendations.md` | [templates/02_recommendations.md](templates/02_recommendations.md) | [reference/tech-stack-decision-matrix.md](reference/tech-stack-decision-matrix.md) |
| `03_migration_plan.md` | [templates/03_migration_plan.md](templates/03_migration_plan.md) | |
| `04_database_schema.sql` | [templates/04_database_schema.sql](templates/04_database_schema.sql) | [reference/schema-translation-guide.md](reference/schema-translation-guide.md) |
| `05_api_design.md` | [templates/05_api_design.md](templates/05_api_design.md) | |
| `06_ui_spec.md` | [templates/06_ui_spec.md](templates/06_ui_spec.md) | |
| `07_business_logic.md` | [templates/07_business_logic.md](templates/07_business_logic.md) | [reference/script-translation-patterns.md](reference/script-translation-patterns.md), [reference/business-logic-detection.md](reference/business-logic-detection.md) |
| `08_auth_roles.md` | [templates/08_auth_roles.md](templates/08_auth_roles.md) | |

Without discovery answers or a chosen stack, write the artifacts anyway and mark each product decision open.

For FileMaker behavior, see [reference/filemaker-concepts.md](reference/filemaker-concepts.md). For the DDR format, see [reference/ddr-xml-reference.md](reference/ddr-xml-reference.md).

## Done when

- Every object kind in `objects/index.tsv` has its classification CSV, and `catalog_contract.py verify` passes for each.
- Every artifact in Step 5 exists, cites object files, and lists its open decisions.
- No artifact contains a credential.
