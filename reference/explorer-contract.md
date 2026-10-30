# Explorer Contract

Every explorer works the same way. The unit of review is one object file. Every row of `objects/index.tsv` of the explorer's kinds is read in full and gets exactly one CSV row.

## Paths

```bash
OBJECTS="$OUT_DIR/objects"
EXPLORER_DIR="$OUT_DIR/explorers/<name>"    # for example explorers/scripts
CATALOG="$EXPLORER_DIR/catalog.json"
CSV_ROOT="$EXPLORER_DIR/csv"
```

Keep only classification CSVs under `CSV_ROOT`. Put notes and drafts elsewhere.

## Snapshot

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind scripts --output "$CATALOG"
```

Repeat `--kind` for an explorer that covers several kinds. A kind the solution does not have is noted and skipped. The catalog is a JSON object: `objects` (the objects folder path), `kinds`, `batch_size`, `batch_lines`, `count`, and `entries`, one entry per index row:

- `source_id`: the object file path relative to `objects/` (`<file>/<kind>/<id>-<name>.txt`).
- `source_hash`: the row's `sha256`.
- `file`, `kind`, `id`, `name`, `lines`: copied from the index.
- `output_file`: the CSV for this row, relative to `CSV_ROOT`. It is one batch of up to 50 objects (`--batch-size`) or 6000 object lines (`--batch-lines`) from one file, kind and folder. It starts with the kind, so CSVs land at `CSV_ROOT/<kind>/...`; that is intended.

A batch is the unit of parallel work. Give each agent whole batches. Two agents never write the same CSV.

If `snapshot` says the objects changed, move the old CSVs away, run it again with `--force`, and classify again. Do not carry rows forward.

## CSV rows

Every CSV starts with these columns, copied from the catalog entry:

```text
source_id,source_hash,kind,file,id,name,...explorer columns...
```

Write CSVs with Python's `csv` module so quotes and newlines stay valid. A list cell (one line per field, rule or button) holds one item per line inside the quoted cell; write `none` when it has no items. Inside a line, `|` separates parts; put a name or label that contains `|` in double quotes. Use the explorer's enums exactly. Write free-text cells in the user's language. Keep column names, enum values, `none` and `unresolved` in English, and copy `source_id`, `source_hash`, names and ids verbatim. When the object file does not show something, write `unresolved` and put the question in `open_question`. Never fill a cell with a guess.

## How to read an object

1. Open the object file and read every line. The header gives its kind, id, name, file, folder and source XML path.
2. Calculations show their full text after `|` and a `refs:` line with the fields (`TO::field#id`), custom functions (`cf:`) and FileMaker functions (`fn:`) they use.
3. Follow references with grep, then read the hits in full. `<file-dir>` is the file's folder under `objects/`: the first part of `source_id` (`Picker_Module.fmp12`), not the `file` column (`Picker Module.fmp12`), which can hold spaces and names no folder.

   ```bash
   grep -rl 'Invoices::total#' "$OBJECTS"                         # who uses a field
   grep -rl 'cf:TaxFor' "$OBJECTS/<file-dir>"                     # who calls a custom function in one file
   grep -rlE 'Script id=42 name=' "$OBJECTS/<file-dir>"           # who calls script 42 in one file
   ```

4. Cite evidence as an object file path, `objects/<file>/<kind>/<id>-<name>.txt`, plus a step number, field id or layout object key when that helps.

Record what the object does, as written. Do not judge whether the client's logic is correct.

## Completion gate

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

It fails on a missing object, an unknown object, a duplicate row, a changed hash, a row outside its `output_file`, a CSV without `source_id`/`source_hash`, and a catalog that no longer matches the current `index.tsv`. An artifact may say an explorer is complete only after this passes.
