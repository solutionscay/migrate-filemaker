# File Explorer

Kinds: `file`, `data-sources`, `auth-files`, `base-directories`, and any kind in `objects/index.tsv` that no other explorer names. One CSV row per object file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md).

```bash
cut -f2 "$OBJECTS/index.tsv" | sort | uniq -c        # list every kind; add the unclaimed ones below
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot --objects "$OBJECTS" \
  --kind file --kind data-sources --kind auth-files --kind base-directories \
  --output "$OUT_DIR/explorers/file/catalog.json"
```

## Read

- `file` (one per FileMaker file): `OnOpen` options (minimum version, sign-in options), `WindowTriggers` (`OnFirstWindowOpen`, `OnLastWindowClose` and other file triggers with their scripts), `DefaultCustomMenuSet`, encryption.
- `data-sources`: each `FileReference` (another FileMaker file, by `pathList`) or ODBC source. These are the links between files. Match a path to a file in the index by the rules in [../reference/ddr-xml-reference.md](../reference/ddr-xml-reference.md) ("Cross-file resolution", steps 1 to 3). A path that names no file in the index is an unresolved reference.
- `auth-files`: which other files may open this one (`Outbound`/`Inbound` authorizations). The entries are file names, not data sources; match them to the index by file name, and mark a name with no file in the index as `unresolved` (a file outside this DDR set).
- `base-directories`: where containers stored externally live.
- Any other kind: read it as the same plain object tree.

## Record

```text
source_id,source_hash,kind,file,id,name,meaning,settings,references,target,open_question
```

- `meaning`: what the object does, in one or two sentences.
- `settings`: options that change behavior, one per line (`OnFirstWindowOpen -> script 1`, `encryption on`, `minimum version 12`).
- `references`: object file paths or other FileMaker files it points to, one per line. Mark a data source that resolves to no file in the index as `unresolved`.
- `target`: `startup-logic`, `integration`, `container-storage`, `deployment-setting`, `drop-candidate`, `unresolved`.

## Feeds

`00_app_summary.md` (files and how they reference each other), `07_business_logic.md` (startup and close scripts), `03_migration_plan.md` (containers, deployment).
