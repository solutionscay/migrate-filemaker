# FileMaker Script Explorer

Recover the behavior of every script without trusting names, folders, array positions, or populated parameter dictionaries.

Read [../reference/explorer-contract.md](../reference/explorer-contract.md) and [../reference/script-translation-patterns.md](../reference/script-translation-patterns.md) first.

## Inputs and outputs

```bash
SPEC_FILE="$SPECS_DIR/05_scripts.json"
EXPLORER_DIR="$ANALYSIS_DIR/explorers/scripts"
CATALOG="$EXPLORER_DIR/source_catalog.json"
CSV_ROOT="$EXPLORER_DIR/catalogs"
REPORT_DIR="$EXPLORER_DIR/reports"
```

Create the frozen identity catalog:

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --kind scripts --spec "$SPEC_FILE" --output "$CATALOG"
```

The empty/root group is `_root.csv`; do not normalize it to `.csv`. Use each catalog entry's `output_file` exactly. Do not glob the explorer root: classification CSVs live only under `catalogs/`.

## Classification record

Write one row per `source_id` with Python's `csv` module:

```text
source_id,source_hash,index,source_file,catalog_id,group,script_name,module,type,effect_owner,logic_tier,purpose,result,evidence,uncertainty
```

- `catalog_id` is the DDR script definition id.
- `type` is one of `navigation`, `read/query`, `data mutation`, `validation`, `integration`, `printing/export`, `orchestration`, `utility`, or `unknown`.
- `effect_owner` is one of `server-domain`, `server-query`, `client-presentation`, `background-job`, `external-adapter`, `drop-candidate`, or `unresolved`.
- `logic_tier` is `tier1` for domain-specific/invariant logic, `tier2` for standard but persistent data behavior, `tier3` for presentation/navigation only, or `unknown`.
- `evidence` names the steps/calculations/comments that support the classification.
- `uncertainty` records missing context or an empty string; never hide ambiguity in a confident category.

Keep the full script content in `05_scripts.json`; do not copy credential-bearing literals into reports.

## Per-script review

For each unclassified catalog identity:

1. Locate the source item by the frozen catalog `index`, then verify its `source_file`, `id`, and `source_hash` before reading it.
2. Read every active step (`enable != "False"`). Record disabled steps separately when they explain intent.
3. Read both structured `params` and `step_text` for every active step. An empty `params` object does not mean the step has no semantics.
4. Read populated comments. Comments are source evidence; they may explain find criteria, return contracts, exception cases, or abandoned behavior.
5. Trace found-set construction, loops, variables, script parameters/results, transactions, error handling, called scripts, external effects, and field writes.
6. Search calculation and step text for `ExecuteSQL (` as a FileMaker calculation function. Keep it distinct from the `Execute SQL` ODBC script step.
7. Determine effects before using the script name or folder as a hint. `Open*`, `Go To*`, `Close*`, and trigger-invoked scripts may enforce authorization or persistent state.
8. Classify the enforcement owner by effect. A layout/field trigger that changes durable business state still requires server-side domain enforcement.
9. Record a row immediately, preserving the catalog identity and item hash.

Do not hard-filter "plumbing" before scoring. Navigation-like names are weak evidence only. Do not classify `Replace Field Contents` until the current found set and its predicate are reconstructed.

## Cross-script tracing

After individual classification:

- Resolve `Perform Script` calls by source file and definition id/name; label unresolved external calls.
- Identify strongly connected call groups and dispatcher parameter contracts.
- Trace each tier1 write back through its callers and forward to affected fields/tables.
- Record whether transaction and error-handling behavior spans called scripts.
- Identify UI entry points, but do not move domain invariants to the client.

## Required reports

Generate reports only after the coverage verifier passes:

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" verify \
  --catalog "$CATALOG" --csv-root "$CSV_ROOT"
```

Write:

- `summary.md`: totals by source file, group, type, effect owner, and logic tier; unresolved count.
- `tier1-critical.md`: full evidence and call traces for domain-specific logic.
- `data-writes.md`: every durable field/table effect and its found-set/record scope.
- `integrations.md`: direction, endpoint/system, authentication evidence status, retry/error behavior, and redaction note.
- `call-graph.md`: resolved and unresolved calls, dispatchers, recursion, and shared subroutines.
- `triggers-dispatchers-validation.md`: invocation event separated from enforcement owner.
- `coverage.md`: spec hash, source count, exact-set verifier result, and raw XML spot checks.

## Semantic spot checks

Before accepting reports:

- Compare root-script totals to `00_topology.json` per-file script counts and inspect root definitions in raw XML.
- Check scripts with empty `params` but non-empty `step_text`.
- Check populated comment steps in each major domain.
- Check every `Replace Field Contents`, credential-redacted integration, account-management script, and authorization/router script.
- Recompute at least one tier1 conclusion directly from raw XML.

Counts prove coverage only. The spot checks prove that the workflow read the source semantics it claims to interpret.
