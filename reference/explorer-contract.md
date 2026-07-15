# Explorer State and Coverage Contract

Use this contract for scripts, calculated fields, custom functions, conditional formatting, and hide-object rules.

## Why the contract exists

Array indexes are display positions, not identities. Parser repairs, insertions, removals, merge-order changes, and separator filtering can move an item while leaving a valid-looking CSV row at the old index. Never resume or join by `index`.

## Required paths

Set these per run:

```bash
SPEC_FILE="$SPECS_DIR/05_scripts.json"       # choose the explorer's source
EXPLORER_DIR="$ANALYSIS_DIR/explorers/scripts"
CATALOG="$EXPLORER_DIR/source_catalog.json"
CSV_ROOT="$EXPLORER_DIR/catalogs"
```

Keep reports outside `CSV_ROOT` so report-support CSVs cannot be mistaken for classifications.

## Snapshot the exact source

Create a source catalog before classification:

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --kind scripts --spec "$SPEC_FILE" --output "$CATALOG"
```

Choose one observed kind: `scripts`, `calculations`, `functions`, `conditional-formatting`, or `hide-rules`.

The catalog records:

- the complete spec hash;
- one stable `source_id` per source item;
- a `source_hash` of that item's full parsed content;
- the original index for lookup only;
- a collision-resistant output filename.

For the root script group, the output filename is explicitly `_root.csv`. Other group/layout/table names include a hash suffix so normalized-name collisions do not merge unrelated sources.

If `snapshot` reports that the source changed, stop. Archive or delete the stale classification directory, recreate the catalog with `--force`, and reclassify. Do not carry rows forward by index. A manual carry-forward is allowed only after matching `source_id` and verifying `source_hash`; record that operation.

## Required CSV columns

Every classification CSV must include:

```text
source_id,source_hash,index,...human classification columns...
```

Copy these three values from `source_catalog.json`. Use `index` only to locate the frozen source item. Do not compute the next item as `max(index) + 1`; select catalog entries whose `source_id` is absent from the CSV set.

Do not serialize formulas or step content into shell commands. Read JSON structurally and write CSV with Python's `csv` module so newlines and quotes remain valid.

## Completion gate

Before producing any report, run:

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

The command fails on:

- a missing source item;
- an unknown/stale source item;
- a duplicate source identity;
- a changed item hash;
- a CSV without the identity columns.

Reports may claim complete coverage only after this exact-set check passes. A directory, row count, largest index, or `DONE == TOTAL` is not sufficient.

## Semantic review gate

Exact-set coverage still cannot prove a correct interpretation. For each report:

1. Reopen the full source object for every high-risk classification.
2. Read all semantic fallbacks (`step_text`, full calculation text, CSS payload, object attribution status).
3. Compare at least one representative and every alarming outlier to raw XML or another primary artifact.
4. Mark uncertain targets or meanings as `unresolved`; never fill a required cell with a guess.
5. Preserve presentation variants and context even when formulas are identical.
