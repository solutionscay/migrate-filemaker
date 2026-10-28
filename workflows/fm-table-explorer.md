# Table Explorer

Kinds: `tables`. One CSV row per table file. The row records every field that has logic: calculated and summary fields, auto-enter and validation. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md); read [../reference/schema-translation-guide.md](../reference/schema-translation-guide.md) for target choices.

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind tables --output "$OUT_DIR/explorers/tables/catalog.json"
```

## Read

Each `Field` block shows `dataType` (`Text`, `Number`, `Date`, `Time`, `TimeStamp`, `Binary` for containers), `fieldType` (`Normal`, `Calculated`, `Summary`) and its options:

- `Calculation` with its `refs:` line: the formula of a calculated field, an auto-enter calculation or a validation calculation, by where it sits.
- `SummaryField` and `SummaryInfo`: the summarized field, the operation, and the sort-group behavior.
- `AutoEnter`: `Serial`, creation/modification values, `ConstantData`, `Calculation`, `Lookup`, `alwaysEvaluate`, and `allowEditing` (whether the user can change the value).
- `Validation`: `type` (when it runs), `StrictValidation` (no user override), `NotEmpty`, `Unique`, `Existing`, `StrictDataType`, `MaxDataLength`, range, value list, calculation, and `ErrorMessage`.
- `Storage`: `global=True`, `maxRepetition`, `storeCalculationResults`, indexing.
- `Comment`: the developer's note on the field.
- `Validation alwaysValidateCalculation=True` with no `Calculation` block, or an `ErrorMessage` with no rule, validates nothing; it is not logic.
- `overwriteExistingValue=True`: the auto-enter replaces a value already in the field. `alwaysEvaluate=True`: an unstored-style recalculation on every change of a referenced field, even for a stored result.
- A field can have `calculation=True` or `fieldType=Calculated` and no `Calculation` block: the DDR omits the formula (the object file says `(no formula in DDR)`). Tag it as usual and put `formula not in DDR` in the meaning.
- A formula that is only a comment (`// ... //`, or `1 // old formula`) returns empty or a constant. Say so in the meaning.
- Treat a value as secret only where that matters to the plan: the target must keep it out of code (an integration's login or signing key). A value that only looks like one (a JSON key, a status word, a field name) is ordinary logic. Write `secret` in `open_question` for a field that holds such a value.

Find who uses a field with `grep -rl '<Table>::<field>#<id>' "$OBJECTS"` when its meaning depends on its callers. A table occurrence name can differ from the base table name; the `table-occurrences` files map one to the other.

## Record

```text
source_id,source_hash,kind,file,id,name,role,fields,regular,calculated,summary,global,container,repeating,keys,logic,logic_count,target,open_question
```

- `role`: `entity`, `join`, `lookup`, `log-audit`, `settings-globals`, `interface-resources`, `staging`, `utility`. `staging` is an import, queue or report work table. A table that links two entities is `join` even when it copies attributes from them.
- `fields` … `repeating`: counts from the file. `regular` counts `Normal` fields that are not global.
- `keys`: candidate key fields, one per line, with the evidence the file shows (serial, UUID calculation, unique validation, use as the parent side of an `Equal` relationship predicate). A field used only for sort, inequality or a self-join range is not key evidence. Neither are globals, constant fields (a calc or auto-enter of `1`, used for all-records joins), scratch fields and boolean flags. A field on the child side of a relationship is a foreign key: list it once as `FK -> <table>::<field>`, not as a candidate key. A name such as `ID` alone is not evidence.
- `logic`: one line per field with logic: `<id> <name> | <logic> | <meaning>`. `<logic>` is one or more of `calc-stored`, `calc-unstored`, `summary`, `auto-serial`, `auto-calc`, `auto-lookup`, `auto-created`, `auto-modified`, `auto-data`, `validate-calc`, `validate-rule`, separated by `, `. `validate-rule` covers any validation option (`NotEmpty`, `Unique`, `Existing`, range, value list, `StrictDataType`, `MaxDataLength`, or `StrictValidation` alone); add `(always)` when `type=Always`. `<meaning>` says what the formula or rule does in plain words. A global with no other logic is not listed; it is counted in `global`. A calculated field with global storage counts in both `calculated` and `global` and is listed.
- `logic_count`: the number of lines in `logic`. It must equal the number of fields with one of those options.
- The DDR does not show whether serial numbering is on. Tag `auto-serial` and do not add a per-row question; Step 4 asks it once for the solution.
- `target`: `table`, `merge`, `view-or-query`, `config`, `session-state`, `drop-candidate`, `unresolved`.

## Feeds

`04_database_schema.sql` (tables, keys, constraints), `07_business_logic.md` (calculations, validation, auto-enter), `00_app_summary.md` (data model).
