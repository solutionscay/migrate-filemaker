# FileMaker Custom-Function Explorer

Classify every custom function from its body and call sites. Do not assume custom functions are domain logic; many are generic text, JSON, date, or UI utilities.

Read [../reference/explorer-contract.md](../reference/explorer-contract.md) first.

## Freeze the source

```bash
SPEC_FILE="$SPECS_DIR/08_custom_functions.json"
EXPLORER_DIR="$ANALYSIS_DIR/explorers/functions"
CATALOG="$EXPLORER_DIR/source_catalog.json"
CSV_ROOT="$EXPLORER_DIR/catalogs"
REPORT_DIR="$EXPLORER_DIR/reports"

python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --kind functions --spec "$SPEC_FILE" --output "$CATALOG"
```

All rows may share the catalog-provided custom-functions CSV, but every `source_id` must remain distinct.

## Classification record

```text
source_id,source_hash,index,source_file,catalog_id,name,parameters,visible,category,logic_tier,purity,dependencies,call_sites,meaning,migration_target,modern_signature,uncertainty
```

Suggested categories are `domain rule`, `text`, `date/time`, `number`, `list`, `JSON/XML`, `encoding`, `UI`, `integration`, `compatibility`, `utility`, and `unknown`. Assign `tier1` only when the body or verified call sites establish specialized business behavior.

## Review method

For each function:

1. Verify its source identity and hash.
2. Read the full calculation body and declared parameters.
3. Trace calls to other custom functions, fields/globals, context-dependent FileMaker functions, and recursive self-calls.
4. Search structurally through calculated fields, script `params`, script `step_text`, conditional-formatting formulas, and hide formulas for call sites. Avoid regexing serialized JSON.
5. Determine whether the function is pure, context-dependent, stateful, or unresolved.
6. Infer domain meaning only from the body and call sites. A name or the fact that it is custom is not sufficient.
7. Propose a modern signature only after documenting FileMaker coercion, null/empty behavior, locale, timezone, and error behavior that callers rely on.
8. Record uncertainty rather than inventing a contract.

Do not discard unused functions automatically. Label them `no observed call site in extracted catalogs`; external plugins, missing files, or dynamic evaluation may still call them.

## Completion and reports

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

Write:

- `summary.md`: totals by category/tier/purity and unresolved/unused status.
- `domain-functions.md`: proven business functions with callers, tests, and target ownership.
- `utility-porting.md`: reusable utilities, compatibility requirements, and library-replacement candidates.
- `dependency-map.md`: function call graph, recursion, cycles, and context dependencies.
- `coverage.md`: spec hash, exact-set result, and raw XML spot checks.

Spot-check raw XML for a nested/custom-function-heavy body and any body whose parsed calculation is unexpectedly empty. For every ported tier1 function, create input/output fixtures from non-secret representative cases before implementation.
