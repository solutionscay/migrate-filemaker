# Application Summary

Cite evidence as object file paths: `objects/<file>/<kind>/<id>-<name>.txt`.

## Source

| Item | Value |
|---|---|
| DDR export (folder, date, FileMaker version) |  |
| Object files (`objects/index.tsv` rows) |  |
| Extraction errors | <!-- none, or what explode_ddr.py reported --> |

## Application profile

| Attribute | Value | Evidence |
|---|---|---|
| Name and purpose |  |  |
| FileMaker files |  |  |
| Tables / table occurrences / relationships |  |  |
| Layouts |  |  |
| Scripts |  |  |
| Custom functions |  |  |
| Value lists |  |  |
| Privilege sets / accounts / extended privileges |  |  |
| Custom menus / menu sets |  |  |

Take each count from `cut -f1,2 objects/index.tsv | sort | uniq -c`.

## Files and references

| File | References these files (data sources) | Unresolved data sources | Evidence |
|---|---|---|---|
|  |  |  | `objects/<file>/data-sources/...` |

## Explorer coverage

| Explorer | Kinds | Objects | `catalog_contract.py verify` |
|---|---|---:|---|
| Scripts | scripts |  |  |
| Custom functions | custom-functions |  |  |
| Tables | tables |  |  |
| Layouts | layouts |  |  |
| Graph | table-occurrences, relationships |  |  |
| Security | privilege-sets, accounts, extended-privileges |  |  |
| Value lists | value-lists |  |  |
| Menus | custom-menus, custom-menu-sets |  |  |
| File | file, data-sources, auth-files, base-directories, other kinds |  |  |

Every kind in `objects/index.tsv` appears in one row.

## Data model

| File | Base table | Role | Regular | Calculated | Summary | Globals | Containers | Key status | Evidence |
|---|---|---|---:|---:|---:|---:|---:|---|---|
|  |  |  |  |  |  |  |  | <!-- shown / needs-profile / unresolved --> | `objects/<file>/tables/...` |

### Relationship semantics

| Relationship | Left occurrence → base | Predicates | Right occurrence → base | Meaning | Evidence |
|---|---|---|---|---|---|
|  |  |  |  |  | `objects/<file>/relationships/...` |

Do not call an equality relationship a foreign key until the referenced key is shown to be unique.

### Globals, containers, time, and validation

- Globals by purpose (session filter, UI state, preference, shared config): <!-- counts -->
- Container fields and where they store data: <!-- count, base-directories -->
- Source timezone for Date/Time/TimeStamp values: <!-- value or unresolved -->
- Fields with validation or auto-enter: <!-- count from the table explorer -->

## Functional and logic map

| Domain | Objects (scripts, fields, functions, layouts) | Reads/writes | Specialized rules | Open questions |
|---|---|---|---|---|
|  |  |  |  |  |

Report `ExecuteSQL()` calculation uses separately from `Execute SQL` ODBC steps. Do not exclude navigation/startup/trigger-named scripts before tracing effects.

## Security model

| Dimension | Count | Evidence | Notes |
|---|---:|---|---|
| Accounts and provisioning |  | `objects/<file>/accounts/...` | The DDR has no passwords or hashes |
| Privilege sets |  | `objects/<file>/privilege-sets/...` |  |
| Record-level rules |  |  |  |
| Field restrictions |  |  |  |
| Layout / script / value-list access |  |  |  |
| Extended privileges (access channels) |  | `objects/<file>/extended-privileges/...` |  |
| Hide and conditional-format rules |  | layout explorer | UI evidence only |

Do not infer access level from privilege-set names alone.

## Open decisions

| Decision | Evidence | Impact | Owner |
|---|---|---|---|
|  |  |  |  |
