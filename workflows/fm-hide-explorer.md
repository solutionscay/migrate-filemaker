# FileMaker Hide-Object-When Explorer

Recover UI visibility conditions without mistaking them for the server authorization model or attaching an unnamed rule to a guessed control.

Read [../reference/explorer-contract.md](../reference/explorer-contract.md) first.

## Freeze the source

```bash
SPEC_FILE="$SPECS_DIR/10_hide_object_when.json"
EXPLORER_DIR="$ANALYSIS_DIR/explorers/hide-rules"
CATALOG="$EXPLORER_DIR/source_catalog.json"
CSV_ROOT="$EXPLORER_DIR/catalogs"
REPORT_DIR="$EXPLORER_DIR/reports"

python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --kind hide-rules --spec "$SPEC_FILE" --output "$CATALOG"
```

## Classification record

```text
source_id,source_hash,index,source_file,layout,object_name,object_type,attribution,category,security_relation,dependencies,meaning,migration_target,uncertainty
```

- `attribution` is `named-context-only`, `stable-object`, or `unattributed`. With the current emitted schema, most records cannot qualify as `stable-object` because no object key/bounds/container path is present.
- `security_relation` is `none`, `ui-affordance`, `security-exception`, or `unresolved`. It never means the rule itself grants access.

## Review method

For each rule:

1. Verify the frozen identity and hash.
2. Read the full formula and layout context.
3. If `object_name` is empty, mark the rule `unattributed`. Do not infer a button, field, tab, or action from nearby array order.
4. Resolve fields, globals, custom functions, privilege-set names, SQL/calculation checks, and workflow-state values.
5. Explain when the object is hidden and, separately, the possible domain/UI reason.
6. Cross-reference `07_security.json` for any role, record, field, or layout access implication. Security remains authoritative even when the hide formula is more fine-grained visually.
7. Assign server enforcement only when a protected operation/data rule is independently supported. Component visibility is defense in depth, not authorization.
8. Record uncertainty when the exact object/action is unavailable.

## Repeated formulas

Retain every row. The same expression can hide different controls on different layouts and therefore have different user-facing consequences.

- Group formulas for analysis only.
- Preserve source file, layout, object attribution, and proposed target for every occurrence.
- Never inherit a migration target from the first exact-formula match.

## Completion and reports

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

Write:

- `summary.md`: totals by source/layout/category and attribution status.
- `workflow-visibility.md`: state-dependent UI behavior, with unknown targets called out.
- `authorization-ui.md`: UI affordances/exceptions reconciled to privilege catalog evidence.
- `unattributed.md`: every rule that needs raw object extraction or screenshot/manual mapping.
- `formula-families.md`: repeated conditions with every distinct context retained.
- `coverage.md`: source hash, exact-set result, and raw XML spot checks.

Do not call this a "complete access-control model." A complete authorization deliverable must begin with accounts and privilege sets, then cover table/record/field/layout/script/value-list/access-channel enforcement and only then add hide rules as UI evidence.
