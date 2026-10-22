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

Find who uses a field with `grep -rl '<Table>::<field>#<id>' "$OBJECTS"` when its meaning depends on its callers. A table occurrence name can differ from the base table name; the `table-occurrences` files map one to the other.

## Record

```text
source_id,source_hash,kind,file,id,name,role,fields,regular,calculated,summary,global,container,repeating,keys,logic,logic_count,target,open_question
```

- `role`: `entity`, `join`, `lookup`, `log-audit`, `settings-globals`, `interface-resources`, `utility`.
- `fields` … `repeating`: counts from the file. `regular` counts `Normal` fields that are not global.
- `keys`: candidate key fields, one per line, with the evidence the file shows (serial, UUID calculation, unique validation, use in relationships). A name such as `ID` alone is not evidence.
- `logic`: one line per field with logic: `<id> <name> | <logic> | <meaning>`. `<logic>` is one or more of `calc-stored`, `calc-unstored`, `summary`, `global`, `auto-serial`, `auto-calc`, `auto-lookup`, `auto-created`, `auto-modified`, `auto-data`, `validate-calc`, `validate-rule`. `<meaning>` says what the formula or rule does in plain words.
- `logic_count`: the number of lines in `logic`. It must equal the number of fields with one of those options.
- `target`: `table`, `merge`, `view-or-query`, `config`, `session-state`, `drop-candidate`, `unresolved`.

## Feeds

`04_database_schema.sql` (tables, keys, constraints), `07_business_logic.md` (calculations, validation, auto-enter), `00_app_summary.md` (data model).
