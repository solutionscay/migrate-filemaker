# Script Translation Patterns

Translate complete FileMaker behavior, not isolated step names. A step's meaning depends on window/layout/table-occurrence context, current record, found set, mode, sort order, session globals, privilege set, variables, called scripts, and error state.

## Translation record

For each script or operation, capture:

```text
source identity | inputs/context | preconditions | reads | writes | found-set scope |
calls/external effects | transaction/error behavior | result | target owner | authorization | tests
```

Read both structured `params` and `step_text`; preserve populated comments as evidence.

## Data operations

| FileMaker step | Candidate target | Required semantic reconstruction |
|---|---|---|
| `Set Field` | Typed service mutation/form update | Current record/TO, calculation coercion, privileges, validation, and commit behavior. |
| `Set Field By Name` | Allowlisted dynamic mutation | Resolve/allowlist the target; never accept an arbitrary client column name. |
| `New Record/Request` | Create operation or a new find request | Mode determines whether this creates data or adds query criteria. |
| `Delete Record/Request` | Authorized delete | Current record, related-delete behavior, confirmation, audit, and ownership. |
| `Delete All Records` | Explicit administrative bulk delete | Prove table/found-set semantics and require narrow authorization, audit, dry-run/count, and recovery. Never infer `TRUNCATE`. |
| `Commit Records/Requests` | Transaction/save boundary | Include validations, triggers, conflict handling, and `Get(LastError)` behavior. |
| `Revert Record/Request` | Rollback/discard | Determine whether it reverts only the current record/request and what prior commits remain. |
| `Duplicate Record/Request` | Copy operation | Identify copied/auto-entered/related values and authorization. |
| `Replace Field Contents` | Scoped bulk update | It operates on the current found set. Reconstruct an explicit target predicate or list of record keys. Refuse translation when scope cannot be proven; never emit an unqualified `UPDATE`. |

## Find and record context

Treat the following as a state machine, not independent query snippets:

- `Enter Find Mode` begins request construction.
- `Set Field` in find mode adds criteria with FileMaker operators/coercion.
- `New Record/Request` in find mode adds an OR request.
- `Omit Record`, `Extend Found Set`, `Constrain Found Set`, and `Show Omitted Only` transform a set.
- `Perform Find` materializes the found set and error behavior.
- `Sort Records` changes order used by navigation, summaries, and reports.
- `Go to Record`, loops, exports, printing, and replacement operate on that set/order.
- `Show All Records` expands scope and is high risk before a bulk write/export.

Translate a found set into a parameterized predicate or an explicit server-side collection of authorized record identifiers. Preserve row authorization in addition to the legacy criteria.

## Control flow and calls

| FileMaker pattern | Target candidate | Caveat |
|---|---|---|
| `If` / `Else If` / `Else` | Conditional | Preserve FileMaker truthiness, empty/null, error, and type coercion where observable. |
| `Loop` / `Exit Loop If` | Loop, set-based query, or batch job | A set-based rewrite must preserve found-set membership, order, per-record error behavior, and side effects. |
| `Perform Script` | Function/service call | Preserve parameter/result, file context, call stack, and error propagation. |
| `Perform Script on Server` | Server operation/job | Determine session/context differences and whether the caller waits for a result. |
| `Exit Script` | Typed return | Preserve result encoding and caller expectations. |
| `Halt Script` | Abort the operation chain | It can stop more than a local helper; trace callers. |
| `$var` / `$$var` | Local / per-session state | Hosted globals and `$$` variables are not process-wide shared state by default. |

## UI and trigger behavior

Navigation, dialogs, focus, window management, and loading feedback may become client behavior. Classify the invoked effects first:

- A trigger that only formats or focuses may be client-owned.
- A trigger that validates a durable invariant or writes persistent state requires a server-owned operation; the client can invoke it but cannot be the only enforcement point.
- A navigation/router script can still contain authorization decisions or initialize session context.
- Button visibility and client validation supplement, not replace, server authorization and validation.

Do not label every script attached to `OnObjectEnter`, `OnObjectModify`, `OnRecordCommit`, or another trigger as a UI handler.

## Integrations

| FileMaker construct | Direction/target | Required checks |
|---|---|---|
| `Insert from URL` | Outbound HTTP/client request | URL/method/body/headers, redacted credentials, response parsing, timeout, TLS, retry/idempotency, and egress policy. It is not evidence of an inbound webhook. |
| `Open URL` | User navigation or outbound invocation | Determine whether a browser opens or an integration protocol is called. |
| `Send Mail` | Outbound email service/job | Recipients, templates, attachments, audit, retry, and failure handling. |
| Import/export | Inbound/outbound file pipeline | Found-set scope, field order, encoding, filenames, overwrite, scheduling, and rejected rows. |
| `ExecuteSQL()` | FileMaker calculation query | Parse calculation inputs and query semantics; parameterize the target equivalent. |
| `Execute SQL` | ODBC script step | Identify external DSN/database, SQL, bindings, transaction, and credentials. |
| Plugin/external script | Adapter or replacement workflow | Inventory availability, side effects, platform dependence, and missing code. |

Never print or copy credential literals from DDR calculations. Document only their source location and purpose, then replace them with managed secret references.

## Transactions, errors, and concurrency

`Set Error Capture`, `Open Transaction`, `Commit Transaction`, `Revert Transaction`, record commits, called scripts, and `Get(LastError)` collectively define failure behavior. Translate the complete boundary.

Specify:

- atomic records/tables and external effects;
- lock/conflict behavior and retry policy;
- partial progress and compensation;
- validation/error codes surfaced to callers;
- idempotency for retryable operations;
- audit actor/time/reason.

An example SQL transaction is not proof that a multi-script FileMaker sequence was atomic.

## Categorize by ownership, not invocation

- `server-domain`: persistent invariants, writes, validation, authorization, state transitions.
- `server-query`: authorized reads, finds, reports, aggregates.
- `background-job`: scheduled/long-running/retryable effects.
- `external-adapter`: HTTP/email/file/ODBC/plugin boundary.
- `client-presentation`: focus, display, local interaction with no trusted invariant.
- `drop-candidate`: behavior made obsolete by the target, after dependencies are traced.
- `unresolved`: insufficient context.

A user action may call a server-domain operation; that does not make the operation a generic CRUD endpoint. A drop candidate is not dropped until call sites and side effects prove it safe.

## Verification

For high-risk translations, create semantic fixtures covering normal, empty/null, boundary, unauthorized, duplicate, found-set, error, and retry cases. Compare results to the source application or raw authored logic. Counts and successful compilation cannot detect a changed predicate or deleted operand.
