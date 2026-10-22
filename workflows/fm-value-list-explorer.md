# Value-List Explorer

Kinds: `value-lists`. One CSV row per value-list file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md).

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind value-lists --output "$OUT_DIR/explorers/value-lists/catalog.json"
```

## Read

- `Source value=`: `Custom` (the values follow under `CustomValues`), `Field` (values come from `PrimaryField` and an optional `SecondaryField` for display), or `External` (a list in another file).
- `ShowRelated` and its table occurrence: the list shows only related records.
- Sort and show options on each field.
- Where it is used: `grep -rlF '<name>' "$OBJECTS"`, then keep the hits that use the list (layout `ValueList:` lines, validation, script steps, `ValueListItems` calculations).

## Record

```text
source_id,source_hash,kind,file,id,name,source,values,stored_display,related_to,used_by,target,open_question
```

- `source`: `custom`, `field`, `external`.
- `values`: for `custom`, the count and the values when they name a domain state (status, type); else the `TO::field#id` the values come from.
- `stored_display`: the stored field and the displayed field when they differ, else `same`.
- `related_to`: the table occurrence for a related-only list, else empty.
- `used_by`: object file paths, one per line, or `none found`.
- `target`: `enum`, `reference-table`, `lookup-query`, `ui-only`, `drop-candidate`, `unresolved`.

## Feeds

`04_database_schema.sql` (domains and reference tables), `07_business_logic.md` (validation and reference values), `06_ui_spec.md` (controls).
