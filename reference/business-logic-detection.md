# Specialized Business-Logic Detection

Use these signals to decide which objects need the closest reading. They are features, not conclusions: read every script before calling it plumbing, and take meaning from its full steps, calculations, comments, callers and field effects.

## Detection signals

1. **Durable writes and invariants**: field changes, record creation/deletion, account changes, or validation that affect persistent state. Resolve table occurrences to base tables and reconstruct record/found-set scope.
2. **ExecuteSQL calculation calls**: `grep -rl 'fn:ExecuteSQL' "$OBJECTS"` finds every calculation that calls it. This is a FileMaker calculation function. Keep it distinct from the `Execute SQL` ODBC script step.
3. **Multi-entity orchestration**: writes to several base tables, compound transaction/error handling, or dependencies across called scripts.
4. **Branching/calculation complexity**: nested `Case`/`If`, domain thresholds, date windows, rounding/allocation, state transitions, or dense computed writes.
5. **Custom-function calls**: `grep -rl 'cf:<name>' "$OBJECTS"` finds the callers; read the function's object file and each caller. A custom function may be a generic utility; its existence alone is not a domain signal.
6. **Authorization and routing decisions**: privilege-set checks, account/role state, record ownership predicates, field/layout access, and scripts that select a destination based on access.
7. **External effects**: outbound HTTP/email/export/import, ODBC, filesystem/plugin activity, or calls to missing FileMaker files.
8. **Developer evidence**: comment steps, field `Comment` lines, and comments inside calculations that describe exceptions, compliance, calculation intent, or return contracts.

## Name/folder hints

Names such as Navigation, Utility, Startup, Trigger, Open, Close, Go To, Show, Hide, or Refresh reduce confidence only after effects are traced. They are never exclusion filters. Dispatchers and trigger handlers can be the entry point to critical server-owned logic.

## Output

Group the candidates by functional domain and report:

```text
Domain | Script identity | Evidence (object file) | Durable effects | Calls/dependencies | Confidence | Open questions
```

If no object shows specialized logic, say: `No specialized business logic was found in the explored objects.` Also state explorer coverage and unresolved references. Never conclude that all behavior is reproducible from the data model merely because the detector found no candidates.
