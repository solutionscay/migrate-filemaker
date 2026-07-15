# FileMaker Concepts and Migration Semantics

Use modern equivalents as design candidates, not mechanical translations. Verify the source behavior and record every intentional semantic change.

## Data and graph

| FileMaker construct | Target candidates | Required checks |
|---|---|---|
| Base table | Database table | Preserve source identity and fields; decide normalization separately. |
| Table occurrence | SQL/query alias and context | Resolve occurrence to base table/source file. A relationship side name is often an alias, not a table. |
| Regular field | Column | Preserve type/coercion, auto-enter, validation, repetitions, indexing, and privileges. |
| Stored calculation | Authored/stored derived value | A generated column is only one candidate; target restrictions may require application logic or a trigger. |
| Unstored calculation | Query/view/application computation | Preserve relationship, layout, found-set, privilege, locale, and session context. |
| Summary field | Aggregate/report query | Meaning may depend on found set, sort parts, and layout context; it is not automatically a global `GROUP BY`. |
| Repeating field | Ordered child rows or, deliberately, an array | Determine each repetition's meaning and every script/layout dependency before normalizing. |
| Container / JSON `Binary` | Object storage plus metadata, or database blob | Inventory embedded/external storage, repetitions, filenames, access control, integrity, and migration failures. A URL column alone is not a migration plan. |
| Relationship | Join/query rule; sometimes a foreign key | Resolve table occurrences, preserve every predicate/operator, and prove referenced uniqueness before adding a constraint. |
| Allow creation of related records | Contextual create workflow | This is UI/graph behavior, not cascade insert semantics. Specify authorization and defaults. |
| Delete related records | Candidate ownership/cascade rule | Confirm actual ownership, orphan data, and desired target behavior before `ON DELETE CASCADE`. |

## Globals and session state

A hosted FileMaker global field is maintained independently for each client/session. Default its target to per-session or per-request state. A file's hosted initial value and initialization scripts may still act like a default.

Classify each global by observed reads/writes and initialization:

- per-session filter/navigation state;
- per-session authorization/UI state (never authoritative by itself);
- temporary calculation/scripting state;
- user preference that should become durable per-user data;
- genuinely shared configuration, proven by usage and administration workflow.

Do not map a global to a process-wide variable, environment variable, or shared cache key merely because it has one value in the DDR.

## Layouts and UI

| FileMaker construct | Target candidate | Caveat |
|---|---|---|
| Layout | Page, report, print view, modal, or utility context | Not every layout is a route; several may represent one workflow. |
| Portal | Related collection/editor | Preserve relationship context, sort/filter, create/delete permission, and row actions. |
| Value list binding | Select/radio/lookup | Preserve stored vs displayed values, dynamic source, sorting, and access. |
| Button | UI invocation | Trace its script/action; persistent rules remain server-owned. |
| Script trigger | Invocation event | Classify by effects. A trigger can invoke server domain logic, client presentation, or both. |
| Conditional formatting | Presentation rule/domain signal | Preserve CSS/style variant and context; it is not authorization. |
| Hide object when | UI visibility/affordance | Reconcile protected operations to server authorization. Unnamed rules need raw object attribution. |

The current parsed layout contract omits object bounds, static text, tab membership, triggers, control/value-list bindings, and stable keys for many hide/format rules. Require raw XML/screenshots before calling a UI specification implementation-ready.

## Scripts and found sets

FileMaker scripts execute in context: current file/window/layout/table occurrence, current record, found set, sort order, mode, session globals, account/privilege set, and error state. Preserve or deliberately replace that context.

- Navigation steps may establish the table occurrence needed by later reads/writes.
- Find steps create or modify a found set that scopes later loops, exports, and `Replace Field Contents`.
- `Commit Records/Requests`, error capture, and called scripts affect transaction/error semantics.
- `ExecuteSQL()` is a calculation function over FileMaker data. `Execute SQL` is an ODBC script step. Treat them separately.
- `Insert from URL` is an outbound client request, not an inbound webhook receiver.

## Validation and auto-enter

FileMaker validation can vary by timing, validate-if-modified behavior, user override privilege, custom message, calculation, range, value list, data type, and uniqueness/not-empty options. Auto-enter behavior can be creation-only, replace-existing, contextual, or user-overridable.

Therefore:

- `Not empty` is not automatically equivalent to unconditional SQL `NOT NULL`.
- `Unique` is not automatically equivalent to an immediate database `UNIQUE` constraint.
- auto-enter serial/calculation is not automatically a primary key/default/generated column.

Profile existing data and record a product decision before strengthening these rules in the database. Preserve user-facing validation messages and API enforcement where required.

## Identity and security

| FileMaker construct | Target concern |
|---|---|
| Account | Identity to provision/map; the DDR exposes no password/hash to migrate. |
| Privilege set | Role/capability bundle, not necessarily one target role without decomposition. |
| Record access predicate | Server row policy/service authorization. |
| Field restriction | Read/write projection and mutation authorization. |
| Layout access | Route/page access plus underlying operation/data checks. |
| Script/value-list access | Operation/capability and lookup-data authorization. |
| Extended privilege | Access channel/capability; current parsed specs do not emit this catalog. |
| External authentication | IdP/account mapping, invitation/reset, service principals, disabled accounts, and cutover. |

Start with `07_security.json`, then supplement it with raw/manual extended privileges and UI hide/format evidence. Deny by default and test forbidden reads and writes. A hidden button is not a security boundary.

## Time semantics

FileMaker Date, Time, and TimeStamp values do not carry an embedded timezone. Establish the source office/server timezone, DST ambiguity/nonexistence policy, historical changes, and whether a value represents a local civil time or an instant before choosing `TIMESTAMP`, `TIMESTAMPTZ`, or an application type. Test boundary dates during migration.
