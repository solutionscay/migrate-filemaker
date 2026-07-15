# Server Operation / API Design

Use this artifact for the interface style selected in recommendations: server functions/actions, GraphQL, REST, events, or a combination. Do not create CRUD endpoints for every FileMaker base table.

## Evidence and boundary

| Item | Value |
|---|---|
| Source/spec/explorer hashes |  |
| Selected interface style and reason |  |
| Consumers/clients/integrations |  |
| Authentication mechanism |  |
| Authorization design reference | `08_auth_roles.md` |
| Unavailable/open contracts |  |

## Use-case operation catalog

| Domain/use case | Operation | Consumer | Input | Output | Source scripts/rules | Transaction/effects | Authorization policy | Idempotency/errors |
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

| Operation/query | Role/capability | Record predicate | Field read/write projection | Access channel | Deny behavior/test |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Default deny. Route/operation checks, row filters, field restrictions, and UI visibility are separate layers.

## External integrations

| Integration | Direction | Trigger/operation | Contract | Credential reference | Retry/idempotency | Audit/reconciliation |
|---|---|---|---|---|---|---|
|  | inbound / outbound / bidirectional |  |  | managed secret only |  |  |

- FileMaker `Insert from URL` proves an outbound request, not an inbound webhook.
- An inbound webhook requires separate provider/receiver evidence, signature verification, replay protection, and idempotency.
- Do not copy credential literals from DDR scripts/calculations.

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

For each operation, link source identities and semantic fixtures. Require:

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
