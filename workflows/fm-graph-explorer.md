# Relationship-Graph Explorer

Kinds: `table-occurrences`, `relationships`. One CSV row per object file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md); read [../reference/schema-translation-guide.md](../reference/schema-translation-guide.md) for keys and foreign keys.

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot --objects "$OBJECTS" \
  --kind table-occurrences --kind relationships --output "$OUT_DIR/explorers/graph/catalog.json"
```

## Read

- A table-occurrence file: the `Table` line (`baseTable`, `baseTableId`), a `FileReference` line under it when the base table is in another file, then every relationship that touches it.
- A relationship file: `LeftTable` and `RightTable` with `cascadeCreate`, `cascadeDelete` and `SortList`, then each `JoinPredicate` with its `type` (`Equal`, `NotEqual`, `GreaterThan`, `GreaterThanOrEqualTo`, `LessThan`, `LessThanOrEqualTo`, `CartesianProduct`) and fields.
- For an occurrence on another file, open that file's `data-sources` object to see which file it points to. The base table id belongs to that file.
- Where an occurrence is used: `grep -rlE 'table="?<TO>"?( |$)|(^|[^A-Za-z0-9_])<TO>::' "$OBJECTS/<file-dir>"` (layouts, portals, scripts, calculations, value lists, privilege sets). Quote the name when it has spaces or ends in a space (`table="Supervisors_All "`). `name=<TO>` also matches layouts and scripts of the same name; drop those hits. Occurrences named only inside `ExecuteSQL` text (`FROM`/`JOIN`) need a grep on the quoted name; drop hits in field comments and `/* */` comments. Disabled script steps count as a use; say so in `used_by`.

## Record

Table occurrences:

```text
source_id,source_hash,kind,file,id,name,base_table,data_source,use,used_by,open_question
```

- `base_table`: the base table's object file path, or `unresolved`.
- `data_source`: the data-source name for an occurrence on another file, else empty.
- `use`: `layout-context`, `portal`, `lookup`, `filter`, `script-context`, `value-list`, `calculation`, `security`, `menu`, `unused`. One or more, one per line. `lookup`: a related field shown on a layout outside a portal, or used by a field auto-enter lookup. `filter`: named in a portal `FilterCalc`. `calculation`: named in any calculation that is not a portal filter: a field calculation or its `table=` context, a custom function, `ExecuteSQL` text, or a layout hide rule, conditional format, tooltip or button parameter. `security`: named in a privilege set. `unused` only when `used_by` is `none found`.
- `used_by`: object file paths, one per line, or `none found`.

Relationships:

```text
source_id,source_hash,kind,file,id,name,predicates,cascade_create,cascade_delete,sort,meaning,fk_candidate,open_question
```

- `predicates`: one line per `JoinPredicate`, in order: `LeftTO::field#id <type> RightTO::field#id`. Put a TO name that contains a space in double quotes (`"Defense Attorney"::ID#1`).
- `cascade_create`, `cascade_delete`: `left`, `right`, `both`, or `none` (the side where it is `True`).
- `sort`: `left|right (<TO>): <TO>::field#id ascending|descending`, one per line, or `none`.
- `meaning`: one value, the first that fits in this order: `cartesian` (a `CartesianProduct` predicate), `constant` (both sides are fixed values: a calc of `1`, an auto-enter `ConstantData`, or a literal auto-enter calc; it matches every record; with a fixed value on one side only, it is `filter`), `global-match` (a global field on one side), `self-join` (both sides on one base table), `filter` (extra predicates or inequality), `identity` (a parent-child key match).
- `fk_candidate`: `yes`, `no`, or `needs-profile`. `yes` needs one side shown unique: a `Unique` validation, a serial auto-enter, or an auto-enter `Get ( UUID )` that the user cannot edit. Only `identity` and single-predicate `self-join` rows can be `yes`; others are `no`. The DDR does not show whether serial numbering is on, so a serial alone gives `needs-profile`, not `yes`. Equality on a key whose uniqueness the DDR cannot show is `needs-profile`.

## Feeds

`04_database_schema.sql` (foreign keys and query rules), `00_app_summary.md` (relationship semantics), `06_ui_spec.md` (portal context).
