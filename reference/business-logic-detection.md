# Specialized Business Logic Detection

Use these signals to identify scripts containing domain-specific logic that can't be inferred from the app type and must be carefully migrated. Run this analysis after producing the standard App Summary sections; present findings as a dedicated "Specialized Business Logic" section.

## Detection Signals (in priority order)

1. **Custom function calls in script calculations** — Cross-reference `08_custom_functions.json` against script step calculations. If a script's Set Variable or Set Field steps reference custom functions by name, flag it. Custom functions are almost always purpose-built domain logic.
2. **ExecuteSQL steps** — Any script containing an ExecuteSQL step is doing hand-crafted data operations beyond standard FileMaker. Always flag.
3. **Multi-table writes** — If a script does Set Field against 3+ different base tables (resolve table occurrences to base tables), it's orchestrating a multi-entity transaction. Flag it.
4. **Calculation density** — If >40% of a script's steps are Set Variable/Set Field with non-trivial calculations (containing `+`, `-`, `*`, `/`, or functions like `Round`, `Case` with multiple branches, nested function calls), it's implementing an algorithm, not plumbing.

## Plumbing Filters (exclude before scoring)

- Script groups named: Navigation, Nav, UI, Utility, Debug, Startup, Triggers, or similar
- Script names matching: "Go To", "Navigate", "Open", "Close", "Toggle", "Show", "Hide", "Refresh"
- Scripts that are only Perform Script calls (dispatchers/routers)
- Scripts where all steps are navigation + one dialog

## Output Format

Group flagged scripts by functional domain (using script group paths and table targets) and present as:

> **Specialized Business Logic**
>
> Found N scripts across M functional areas that contain domain-specific logic requiring careful migration:
>
> 1. **[Domain name]** — N scripts, references custom functions `FuncA`, `FuncB`. [Brief description of what the logic appears to do based on function names, field targets, and calculation content.]
> 2. **[Domain name]** — N scripts with ExecuteSQL-based [operation]. Writes across tables: X, Y, Z.
> 3. ...
>
> These will be explored in detail during Discovery.

If no specialized business logic is detected, note: "No specialized business logic detected — all scripts appear to be standard app plumbing that can be recreated from the data model and app type."
