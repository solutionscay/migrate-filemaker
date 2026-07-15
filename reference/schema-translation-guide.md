# Schema Translation Guide

Use this guide to make evidenced mapping decisions. Do not generate a target schema by mechanically renaming fields or adding surrogate keys.

## Source tokens and target candidates

FileMaker's UI terminology and the current parsed JSON tokens differ:

| FileMaker UI type | Parsed `data_type` | PostgreSQL candidate | Decision required |
|---|---|---|---|
| Text | `Text` | `TEXT`, constrained `VARCHAR`, enum/reference table | Length, collation, case/accent search, empty vs null, value-list semantics. |
| Number | `Number` | `INTEGER`, `BIGINT`, `NUMERIC(p,s)`, `DOUBLE PRECISION` | Decimal precision, rounding, scientific values, identifiers stored as numbers. |
| Date | `Date` | `DATE` | Invalid/empty legacy values and calendar assumptions. |
| Time | `Time` | `TIME` or duration representation | Time-of-day versus elapsed duration. |
| Timestamp | `TimeStamp` | `TIMESTAMP` or `TIMESTAMPTZ` | Source timezone, DST policy, and local-civil-time versus instant meaning. |
| Container | `Binary` | Object/blob reference plus metadata, or `BYTEA` | Embedded/external storage, repetitions, filenames, access, integrity, and transfer. |

Inspect actual distinct tokens and fail on unknown values. `field_type` describes Normal/Calculated/Summary, not Container.

For MySQL/SQLite or another target, choose semantically equivalent types after the same decisions; do not copy a PostgreSQL mapping blindly.

## Time conversion

FileMaker timestamps contain no embedded timezone. Before using `TIMESTAMPTZ`:

1. identify the server/office timezone for each source;
2. determine whether the value represents a local civil time or an instant;
3. define ambiguous/nonexistent DST handling and historical timezone changes;
4. profile values around boundaries;
5. write round-trip fixtures.

Store timezone metadata separately when the originating zone matters. Use timezone-naive target values deliberately for civil-time concepts such as an office opening time.

## Keys and identifiers

Do not infer a primary key from the name `ID`, auto-enter serial behavior, or relationship participation.

For each candidate key, collect:

- source file/table/field ids and types;
- auto-enter and modification behavior;
- uniqueness/not-empty settings with timing/override semantics;
- actual null/duplicate profile;
- incoming/outgoing relationship predicates;
- external/public uses and leading-zero/case behavior.

Preserve authored business/legacy identifiers. Add a surrogate `IDENTITY`/UUID only as an explicit design decision with a reversible source-to-target mapping. A target foreign key may reference only a proven unique key of compatible type. Preserve composite keys when they express real identity.

## Table occurrences and relationships

Resolve each relationship side through `02_table_occurrences.json`; an occurrence name is an alias and may point to an external file's base table.

The parser emits operator tokens such as `Equal`, `NotEqual`, `GreaterThan`, `LessThan`, and `CartesianProduct`, not SQL punctuation. Preserve every predicate and its order.

- `Equal` can support a foreign key only when the referenced side is proven unique and the relationship expresses identity rather than filtering.
- Multiple equality predicates may form a composite join/foreign key.
- Inequality and cartesian relationships become query/domain/UI-context rules, not foreign keys.
- "Allow creation" is contextual create behavior, not database cascade insert.
- "Delete related" is evidence to investigate, not automatic approval for `ON DELETE CASCADE`.

Record a disposition for every relationship predicate and every unresolved occurrence.

## Calculated and summary fields

Classify each authored calculation by storage/context and dependencies:

- row-local deterministic derived value;
- related/context-dependent lookup;
- aggregate/found-set/layout summary;
- validation or auto-enter behavior;
- display/serialization helper;
- persistent domain rule.

Target candidates include application computation, query/view, materialized view, database trigger, ordinary stored column maintained by a service, or generated column. PostgreSQL generated expressions have restrictions and are not a generic translation for related-table, aggregate, volatile, or context-dependent FileMaker calculations.

Summary fields often depend on found set, sort order, and layout parts. Prove their reporting semantics before replacing them with a generic aggregate.

## Validation and constraints

FileMaker validation may be conditional by timing, validate-if-modified state, override privilege, custom message, range, member-of-list, calculation, type, uniqueness, or non-empty setting. The current parsed field records may expose only a subset.

Treat SQL constraints as target product invariants:

1. extract the complete rule or label it unavailable;
2. profile existing violations;
3. decide whether the target deliberately strengthens behavior;
4. define import cleanup/rejection;
5. reproduce user-facing/API error behavior;
6. add negative tests.

Do not automatically map FileMaker `Not empty` to unconditional `NOT NULL` or `Unique` to immediate `UNIQUE`.

## Auto-enter, lookups, and audit fields

Capture creation-only versus replace-existing behavior, user override, dependency context, and modification conditions.

- Creation/modification timestamps and accounts may map to database/application audit columns only after actor/time semantics are proven.
- Looked-up values may intentionally preserve a historical snapshot; replacing them with a live join can change history.
- Auto-enter calculations may require service logic rather than a SQL default.
- Serial values may be public identifiers without being the desired target primary key.

## Globals, repetitions, and containers

- Hosted globals default to per-session state. Classify each by reads/writes and initialization before promoting it to shared config or durable user preferences.
- Repeating fields usually become ordered child rows, but preserve repetition number and all script/layout behavior. Arrays are a deliberate alternative, not a default shortcut.
- Container migration requires a manifest, content hash, filename/MIME metadata, authorization, missing/corrupt-file handling, object-store key strategy, and source-to-target reconciliation.

## Naming and traceability

Choose a consistent target naming convention, but keep a mapping table containing source file/table/field ids and original names. Detect case-insensitive collisions, reserved words, punctuation-only differences, and multiple table occurrences before emitting DDL.

Every target column and constraint must cite one of:

- direct source evidence;
- profiled data evidence;
- stakeholder-approved product decision;
- target-platform requirement.

## Data-load verification

Row counts are necessary but insufficient. Verify:

- per-column null/distinct/min/max/length/domain profiles;
- stable-value hashes where ordering/canonicalization are defined;
- duplicate keys and orphan references;
- rejected/changed rows with reasons;
- container counts and content hashes;
- timezone/encoding/decimal edge cases;
- calculated/business totals and ownership rules;
- forbidden values and constraint behavior.
