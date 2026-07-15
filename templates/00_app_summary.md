# Application Summary

## Evidence status

| Item | Value |
|---|---|
| Implementation/source set | <!-- ids/names --> |
| Raw manifest hash/status | <!-- verified / failed --> |
| Parser hash | <!-- sha256 --> |
| Spec hashes | <!-- _provenance.json reference --> |
| Parser regression suite | <!-- command/result/date --> |
| Raw/manual evidence used | <!-- paths/descriptions; no secret values --> |
| Unavailable evidence | <!-- e.g. extended privileges, UI geometry --> |

Do not continue this summary when provenance fails.

## Application profile

| Attribute | Measured value | Evidence / confidence |
|---|---|---|
| Name and purpose |  |  |
| Source FileMaker files |  |  |
| Base tables / table occurrences |  |  |
| Relationship definitions / predicates |  |  |
| Layouts |  |  |
| Script definitions / root scripts |  |  |
| Value lists |  |  |
| Privilege sets / accounts |  |  |
| Custom functions |  |  |
| Conditional-formatting rules |  |  |
| Hide-object rules |  |  |

List unresolved external files/calls and explain whether each is expected.

## Source-catalog coverage

| Catalog | Count | Explorer/status | Important omissions or caveats |
|---|---:|---|---|
| Tables: regular/calculated/summary/global fields |  |  |  |
| Table occurrences |  |  |  |
| Relationships and predicates |  |  |  |
| Layout inventory |  |  | Current JSON is not a complete UI spec |
| Scripts |  |  | Include root group, `step_text`, comments |
| Value lists |  |  |  |
| Security |  |  | Extended privileges not currently emitted |
| Custom functions |  |  |  |
| Conditional formatting |  |  | Preserve `format_css` variants |
| Hide-object-when |  |  | Note unattributed objects |

## Data model

| Source file | Base table | Records | Regular | Calculated | Summary | Globals | Binary | Candidate role | Key status |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
|  |  |  |  |  |  |  |  |  | <!-- proven/profile-needed/unresolved --> |

### Relationship semantics

| Relationship | Left occurrence → base | Operator/predicates | Right occurrence → base | Likely use | Resolution status |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Do not call an equality relationship a foreign key until referenced uniqueness and identity semantics are proven.

### Globals, containers, time, and validation

- Globals by observed/session/config preference purpose: <!-- counts and unknowns -->
- `Binary` fields and storage/export evidence: <!-- count/plan-needed -->
- Date/Time/TimeStamp source timezone evidence: <!-- value or unresolved -->
- Parsed validation coverage versus raw/manual catalog: <!-- measured -->

## Functional and logic map

| Domain | Source identities/groups | Reads/writes | Specialized rules | Confidence / open questions |
|---|---|---|---|---|
|  |  |  |  |  |

Report `ExecuteSQL()` calculation uses separately from `Execute SQL` ODBC steps. Do not exclude navigation/startup/trigger-named scripts before tracing effects.

## UI evidence boundary

| Evidence | Coverage | Missing |
|---|---|---|
| Parsed layout inventory |  | bounds, static text, tabs, triggers, controls, stable object ids as applicable |
| Raw layout XML review |  |  |
| Screenshots/recordings |  |  |
| Hide/CF attribution |  |  |

Classify the current deliverable as `inventory-only`, `behavior-ready`, or `implementation-ready`, with justification.

## Security model

| Dimension | Measured source rules | Source | Interpretation status |
|---|---:|---|---|
| Accounts and provisioning |  | `07_security.json` | Password/hash unavailable in DDR |
| Privilege sets |  | `07_security.json` |  |
| Table/record privileges |  | `07_security.json` |  |
| Field restrictions |  | `07_security.json` |  |
| Layout privileges |  | `07_security.json` |  |
| Script/value-list privileges |  | security/raw |  |
| Extended privileges/access channels |  | raw/manual or unavailable |  |
| Hide/format UI exceptions |  | 09/10 explorers | Secondary UI evidence only |

Do not infer access level from privilege-set names alone.

## Risks and open decisions

| Risk/decision | Evidence | Impact | Owner / next proof |
|---|---|---|---|
|  |  |  |  |

## Raw semantic spot checks

Record at least one checked example for calculations with field operands, root scripts, populated `step_text`/comments, CF payload, and security predicates/grants. Describe locations and results without exposing secrets.
