# FileMaker Calculated-Field Explorer

Classify every calculated field while preserving its table context, complete authored expression, storage behavior, and relationship dependencies.

Read [../reference/explorer-contract.md](../reference/explorer-contract.md) and [../reference/schema-translation-guide.md](../reference/schema-translation-guide.md) first.

## Freeze the source

```bash
SPEC_FILE="$SPECS_DIR/01_tables.json"
EXPLORER_DIR="$ANALYSIS_DIR/explorers/calculations"
CATALOG="$EXPLORER_DIR/source_catalog.json"
CSV_ROOT="$EXPLORER_DIR/catalogs"
REPORT_DIR="$EXPLORER_DIR/reports"

python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --kind calculations --spec "$SPEC_FILE" --output "$CATALOG"
```

Use the catalog's collision-resistant `output_file`; do not derive filenames from normalized table names yourself.

## Classification record

Write exactly one row per identity:

```text
source_id,source_hash,index,source_file,table_id,table,field_id,field_name,return_type,storage,category,logic_tier,dependencies,meaning,migration_target,uncertainty
```

Use categories `display`, `derived domain value`, `validation`, `key/relationship`, `aggregate`, `integration/serialization`, `utility`, or `unknown`. Use `tier1`, `tier2`, `tier3`, or `unknown` for logic tier.

## Review method

For each unclassified identity:

1. Verify the frozen identity and item hash.
2. Read the full calculation string structurally. Never regex serialized JSON or reconstruct a formula from tokens.
3. Record every local field, related table occurrence/field, custom function, global, and context-dependent function it uses.
4. Resolve related references through `02_table_occurrences.json`; do not treat a table-occurrence alias as a base table.
5. Determine stored/unstored behavior from source evidence. Mark it unavailable if the emitted spec lacks the needed storage metadata.
6. Separate the formula's current meaning from the proposed implementation. A SQL generated column is allowed only if the target database supports every expression/dependency and the value is row-local and immutable enough for that mechanism.
7. Record timezone assumptions for Date/Time/TimeStamp expressions. FileMaker timestamps contain no embedded timezone.
8. Record a row with evidence or an explicit uncertainty.

## Duplicate formulas

An exact formula match is a review aid, not a semantic identity. The same text can mean something different under another table context, relationship graph, return type, storage setting, or privilege rule.

- Retain every source row.
- Group exact formulas in reports only after comparing their complete context.
- Never copy `meaning`, `logic_tier`, or `migration_target` from the first matching formula without re-review.
- Constants and mirrored field definitions may legitimately repeat.

## Completion and reports

Run the exact-set gate:

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

Then write:

- `summary.md`: counts by source/table/category/tier, stored-status availability, and unresolved dependencies.
- `business-logic.md`: tier1 formulas with plain-language rules, inputs, outputs, and implementation owner.
- `dependency-map.md`: field/custom-function/global/TO dependencies and cycles.
- `duplicates.md`: repeated text with contextual comparison and no discarded rows.
- `coverage.md`: source hash, exact-set result, and raw XML spot checks.

Inspect in raw XML at least one formula containing field operands, one related-field reference, one custom-function call, and every alarming empty/constant result. A count match cannot detect deleted operands.
