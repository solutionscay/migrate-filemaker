# Server Operation / API Design

Choose the interface style here (server functions/actions, GraphQL, REST, events, or a combination) and record it as a product decision; `02_recommendations.md` is written later and confirms or changes it. Do not create CRUD endpoints for every FileMaker base table.

## Evidence and boundary

| Item | Value |
|---|---|
| Explorer CSVs used |  |
| Selected interface style and reason |  |
| Consumers/clients/integrations |  |
| Authentication mechanism |  |
| Authorization design reference | `08_auth_roles.md` |
| Unavailable/open contracts |  |

## Use-case operation catalog

| Domain/use case | Operation | Consumer | Input | Output | Object files | Transaction/effects | Authorization policy | Idempotency/errors |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

Expose only use cases that a consumer needs. Internal/audit/join/config/security tables remain unexposed unless a proven administrative operation requires them.

## Query/read contracts

| Query | Fields/projection | Filters/sort/page | Record policy | Field restrictions | Source found-set/report semantics | Limits |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Apply record predicates and field restrictions before serialization. Never fetch all rows/fields and rely on the client to hide them.

## Mutation/command contracts

| Command | Preconditions | Allowed fields | Persistent invariant owner | Atomic writes | Audit | Forbidden cases/tests |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Bulk operations must include an explicit authorized predicate or record-id set. A FileMaker `Replace Field Contents` translation without proven found-set scope is unresolved and must not be exposed.

## Identity and account operations

| Operation | Provider/owner | Flow | Authorization | Audit/negative tests |
|---|---|---|---|---|
| Invite/reset/map user |  |  |  |  |
| Activate/disable account |  |  |  |  |
| Assign/revoke roles |  |  |  |  |
| Provision/rotate service principal |  |  |  |  |

The DDR contains no password or password hash. Include a local password-change operation only when discovery selected local credential ownership; otherwise use the IdP's supported reset/invite flow.

## Authorization matrix

| Operation/query | Policy ids (`08`) | Access channel | Deny behavior |
|---|---|---|---|
|  |  |  |  |

`08_auth_roles.md` defines each role, record predicate and field rule. Cite its policy ids here.

Default deny. Route/operation checks, row filters, field restrictions, and UI visibility are separate layers.

## External integrations

| Integration | Direction | Trigger/operation | Contract | Credential reference | Retry/idempotency | Audit/reconciliation |
|---|---|---|---|---|---|---|
|  | inbound / outbound / bidirectional |  |  | managed secret only |  |  |

- FileMaker `Insert from URL` proves an outbound request, not an inbound webhook.
- An inbound webhook requires separate provider/receiver evidence, signature verification, replay protection, and idempotency.
- Do not copy credential literals from DDR scripts/calculations.
- Client-side mail (`Send Mail` via the e-mail client) and embedded web viewers are integrations too. A web viewer URL that carries a key moves that key to the server.

## Background jobs

| Job id | Source (script, schedule, robot queue) | Trigger and frequency | Operation (OP- id) | Idempotency/retry | Run-as principal (08) | Evidence |
|---|---|---|---|---|---|---|
| JOB-01 |  |  |  |  |  | `objects/<file>/scripts/...` |

The DDR has no server schedules. A script that names a schedule, runs as a server account, or reads a robot queue table is a job candidate; mark its frequency `unavailable` until discovery confirms it.

## Confirmations

A FileMaker "show dialog, then continue" step is a business rule when it guards a write. Model it as a two-step command (the server returns the warning; the client resends with a confirmation flag) and cite the 07 rule.

## Errors, concurrency, and observability

| Concern | Contract |
|---|---|
| Validation/domain errors | <!-- stable codes + user-safe messages --> |
| Authentication/authorization denial | <!-- non-leaking behavior --> |
| Conflict/locking/retry |  |
| Partial external failure/compensation |  |
| Idempotency |  |
| Rate/size/pagination limits |  |
| Audit actor/reason/correlation |  |
| Sensitive-field logging/redaction |  |

## Traceability and tests

For each operation, link its object files and semantic fixtures. Require:

- happy-path and boundary behavior;
- forbidden role/record/field/operation tests;
- found-set/bulk-scope tests;
- transaction rollback and retry/idempotency tests;
- outbound/inbound integration contract tests;
- response projection tests preventing restricted-field leakage.

## Unresolved operations

| Source behavior | Missing evidence | Risk | Required proof/owner |
|---|---|---|---|
|  |  |  |  |
