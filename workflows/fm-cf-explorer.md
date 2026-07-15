# FileMaker Conditional-Formatting Explorer

Recover both halves of every rule: the condition and the visual payload. Identical formulas do not imply identical presentation.

Read [../reference/explorer-contract.md](../reference/explorer-contract.md) first.

## Freeze the source

```bash
SPEC_FILE="$SPECS_DIR/09_conditional_formatting.json"
EXPLORER_DIR="$ANALYSIS_DIR/explorers/conditional-formatting"
CATALOG="$EXPLORER_DIR/source_catalog.json"
CSV_ROOT="$EXPLORER_DIR/catalogs"
REPORT_DIR="$EXPLORER_DIR/reports"

python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --kind conditional-formatting --spec "$SPEC_FILE" --output "$CATALOG"
```

The emitted schema uses `format_css`, not `format_actions`. Treat unknown `condition_type` or `flags` values as a contract failure to investigate, not as an empty/default rule.

## Classification record

```text
source_id,source_hash,index,source_file,layout,object_name,object_type,attribution,condition_type,flags,formula_hash,format_hash,category,meaning,visual_effect,migration_target,uncertainty
```

Do not copy credential-like literals from formulas. Hashes in the CSV are traceability aids; interpret the full source values in memory.

## Review method

For each rule:

1. Verify its frozen identity and item hash.
2. Read the full `formula`, `condition_type`, `flags`, and `format_css` values.
3. Record `attribution=unattributed` when the current spec cannot identify the exact layout object. A layout/name/type tuple is context, not guaranteed stable object identity.
4. Explain the condition independently from the rendering effect.
5. Resolve globals, fields, privilege checks, custom functions, and table-occurrence references using their catalogs.
6. Decide whether the rule is presentation-only, communicates a domain state, signals validation, or reflects authorization UI. It never grants server authorization.
7. Retain layout/object context and every presentation payload.
8. Mark missing object identity or unexplained CSS as uncertainty.

## Shared formulas and variants

Never deduplicate on formula alone.

- Retain every source rule as a classified row.
- A presentation-equivalent group requires equality of `formula`, `condition_type`, `flags`, and `format_css`.
- A formula family may share a plain-language condition while retaining all distinct CSS variants and contexts.
- Do not copy the first rule's migration note or visual description to another payload.

## Completion and reports

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

Write:

- `summary.md`: counts by source/layout/category and attributed/unattributed status.
- `condition-families.md`: shared logical conditions with every distinct presentation variant.
- `domain-signals.md`: validation/status/threshold meaning and target design ownership.
- `authorization-ui.md`: UI visibility/emphasis evidence cross-referenced to, but never replacing, `07_security.json`.
- `coverage.md`: source hash, exact-set result, enum inventory, and raw XML spot checks.

Compare raw XML for at least one rule per observed condition type/flags combination and every surprising empty payload. Confirm the XML's `Item` wrapper and CSS payload are represented before trusting a zero or novel enum count.
