# Specialized Business-Logic Detection

Use these signals to prioritize manual review. They are features, not proof: score every script before considering it plumbing, and confirm meaning from full steps, calculations, comments, call sites, and field effects.

## Detection signals

1. **Durable writes and invariants**: field changes, record creation/deletion, account changes, or validation that affect persistent state. Resolve table occurrences to base tables and reconstruct record/found-set scope.
2. **ExecuteSQL calculation calls**: search calculation values in structured `params` and `step_text` for `ExecuteSQL (`. This is a FileMaker calculation function. Keep it distinct from the `Execute SQL` ODBC script step.
3. **Multi-entity orchestration**: writes to several base tables, compound transaction/error handling, or dependencies across called scripts.
4. **Branching/calculation complexity**: nested `Case`/`If`, domain thresholds, date windows, rounding/allocation, state transitions, or dense computed writes.
5. **Custom-function calls**: cross-reference `08_custom_functions.json`, then inspect the function body and callers. A custom function may be a generic utility; its existence alone is not a domain signal.
6. **Authorization and routing decisions**: privilege-set checks, account/role state, record ownership predicates, field/layout access, and scripts that select a destination based on access.
7. **External effects**: outbound HTTP/email/export/import, ODBC, filesystem/plugin activity, or calls to missing FileMaker files.
8. **Developer evidence**: populated comments or `step_text` that describe exceptions, compliance, calculation intent, or return contracts.

## Name/folder hints

Names such as Navigation, Utility, Startup, Trigger, Open, Close, Go To, Show, Hide, or Refresh reduce confidence only after effects are traced. They are never exclusion filters. Dispatchers and trigger handlers can be the entry point to critical server-owned logic.

## Output

Group proven candidates by functional domain and report:

```text
Domain | Script identity | Evidence | Durable effects | Calls/dependencies | Confidence | Open questions
```

If no specialized logic is proven, say: `No specialized business logic was proven in the reviewed catalogs.` Also state coverage and unresolved/missing sources. Never conclude that all behavior is reproducible from the data model merely because the detector found no candidates.
