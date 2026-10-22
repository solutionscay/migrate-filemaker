# Relationship-Graph Explorer

Kinds: `table-occurrences`, `relationships`. One CSV row per object file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md); read [../reference/schema-translation-guide.md](../reference/schema-translation-guide.md) for keys and foreign keys.

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot --objects "$OBJECTS" \
  --kind table-occurrences --kind relationships --output "$OUT_DIR/explorers/graph/catalog.json"
```

## Read

- A table-occurrence file: the `Table` line (`baseTable`, `baseTableId`, and the data source when the base table is in another file), then every relationship that touches it.
- A relationship file: `LeftTable` and `RightTable` with `cascadeCreate`, `cascadeDelete` and `SortList`, then each `JoinPredicate` with its `type` (`Equal`, `NotEqual`, `GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `CartesianProduct`) and fields.
- For an occurrence on another file, open that file's `data-sources` object to see which file it points to. The base table id belongs to that file.
- Where an occurrence is used: `grep -rlE '(table|name)=<TO>( |$)|<TO>::' "$OBJECTS/<file>"` (layouts, portals, scripts, calculations, value lists).

## Record

Table occurrences:

```text
source_id,source_hash,kind,file,id,name,base_table,data_source,use,used_by,open_question
```

- `base_table`: the base table's object file path, or `unresolved`.
- `data_source`: the data-source name for an occurrence on another file, else empty.
- `use`: `layout-context`, `portal`, `lookup`, `filter`, `script-context`, `value-list`, `unused`. One or more, one per line.
- `used_by`: object file paths, one per line, or `none found`.

Relationships:

```text
source_id,source_hash,kind,file,id,name,predicates,cascade_create,cascade_delete,sort,meaning,fk_candidate,open_question
```

- `predicates`: one line per `JoinPredicate`, in order: `LeftTO::field#id <type> RightTO::field#id`.
- `cascade_create`, `cascade_delete`: the side where it is `True`, or `none`.
- `meaning`: `identity` (a parent-child key match), `filter` (extra predicates or inequality), `cartesian`, `self-join`, `global-match` (a global field on one side).
- `fk_candidate`: `yes`, `no`, or `needs-profile` (equality on a key whose uniqueness the DDR cannot show).

## Feeds

`04_database_schema.sql` (foreign keys and query rules), `00_app_summary.md` (relationship semantics), `06_ui_spec.md` (portal context).
