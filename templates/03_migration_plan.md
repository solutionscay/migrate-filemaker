# Migration Plan

## Scope and evidence baseline

| Item | Value/status |
|---|---|
| Source implementations/files |  |
| DDR export and `objects/index.tsv` |  |
| In-scope workflows/data/history |  |
| Target stack/architecture decision |  |
| Parallel-operation/cutover model |  |
| Unavailable evidence/open decisions |  |

A new DDR export needs a new explode and new catalogs. `catalog_contract.py verify` fails on a catalog made from the old one.

## Release increments

Define increments around usable, authorized workflows—not generic CRUD layers.

| Increment | User/business outcome | Object files | Schema/operations/UI | Authorization | Dependencies | Size | Exit evidence | Rollback |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  | S/M/L/XL |  |  |

Each increment must implement its server-side invariants and negative authorization tests before exposing the workflow.

Say whether increments go live one at a time or only set build order. When modules share core tables (cases, people) and nothing writes back to FileMaker, a split go-live means two systems of record; state the choice and its D- id. A policy that spans increments is owned by the first increment that needs it and retested by the later ones.

## Foundation gates

- [ ] Repository/runtime versions and CI quality gates are reproducible.
- [ ] Database schema decisions resolve source keys, TO aliases, compound relationships, validation changes, containers, and timezone policy.
- [ ] Identity provisioning and default-deny authorization skeleton exist before user data operations.
- [ ] Audit actor/time/reason and sensitive logging/redaction rules are defined.
- [ ] Backup, restore, observability, secret management, and environment promotion are tested.
- [ ] Source-to-target traceability identifiers are retained.

## Rules and policies by increment

| Increment | Business rule ids (`07`) | Authorization policy ids (`08`) | Discovery answers (`D-`) |
|---|---|---|---|
|  |  |  |  |

`07_business_logic.md` defines each rule and `08_auth_roles.md` defines each policy. Cite their ids here; do not restate them. Every tier1 rule and every policy lands in exactly one increment.

## UI implementation

| Screen/flow | Evidence readiness | Data/operations | States/errors/accessibility | Source trace | Acceptance test |
|---|---|---|---|---|---|
|  | inventory-only / behavior-ready / implementation-ready |  |  |  |  |

Do not schedule inventory-only screens as implementation-complete. Get screenshots or run an explicit product-design task first.

## Integration and reporting plan

| Boundary/report | Direction | Contract | Auth/secrets | Retry/idempotency/audit | Reconciliation test |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Keep outbound `Insert from URL` replacements separate from inbound webhook endpoints.

## Data migration runbook

### Extract and stage

- [ ] Freeze/version each source export with hashes, counts, encoding, timezone, and export criteria.
- [ ] Export stable source identifiers and relationship keys.
- [ ] Inventory container files with size/content hash and missing/corrupt status.
- [ ] Redact/separate secrets; never commit raw credential-bearing exports.
- [ ] Record rejected source rows without silently dropping them.

### Transform and load

| Source field/table | Target | Transformation/decision | Null/empty/timezone/encoding rule | Reject handling | Reversible mapping |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

- Load in dependency-aware stages while preserving compound/source identifiers.
- Reconcile parallel writes or enforce an explicit freeze window.
- Make reruns idempotent and record batch/version lineage.

Load order: list foreign-key cycles and how the load breaks them (load without the constraint, then add it). Seed every number counter (serials, case or invoice numbers) from the source maximum at cutover.

### Validation matrix

| Check | Source baseline | Target result | Tolerance | Status/evidence |
|---|---|---|---|---|
| Row count by defined export scope |  |  | exact/explained |  |
| Per-column null/distinct/min/max/length/domain |  |  |  |  |
| Stable-value hashes/canonical checksums |  |  |  |  |
| Candidate-key duplicates and relationship orphans |  |  |  |  |
| Containers: count/bytes/content hashes |  |  |  |  |
| Encoding/decimal/timezone/DST edge cases |  |  |  |  |
| Ownership/authorization attributes |  |  |  |  |
| Business totals/calculated invariants |  |  |  |  |
| Rejected/changed rows with reasons |  |  |  |  |
| Target constraint/negative cases |  |  |  |  |

Random samples of migrated rows supplement this matrix; they never replace it.

## Test strategy

- Semantic fixtures for tier1 rules, built from the object files and non-secret sample data.
- Unit tests for calculations/domain transitions and FileMaker coercion edge cases.
- Integration tests for transactions, found-set bulk operations, retries, and external adapters.
- Authorization tests for every forbidden create/read/update/delete/field/operation path.
- UI workflow/accessibility tests only at the evidence readiness claimed.
- Migration rehearsal on production-shaped data with restore and rerun tests.
- Parallel-run business reconciliation before cutover.

## Cutover and rollback

| Decision/check | Owner | Deadline | Evidence |
|---|---|---|---|
| Final source freeze or delta strategy |  |  |  |
| Account invitation/IdP mapping |  |  |  |
| Final migration validation sign-off |  |  |  |
| Monitoring/support/training |  |  |  |
| Rollback trigger and decision authority |  |  |  |
| Target-to-FileMaker write-back capability/limit |  |  |  |

Document the point after which rollback requires data reconciliation rather than a DNS switch.

## Risk and decision register

| ID | Risk/open decision | Evidence | Likelihood/impact | Mitigation/proof | Owner/status |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Completion gate

- [ ] `catalog_contract.py verify` passes for every explorer.
- [ ] Every logic-bearing catalog has a disposition.
- [ ] Every source security dimension has an enforcement owner and negative test.
- [ ] Every relationship predicate and target key is resolved or explicitly open.
- [ ] Data validation exceeds counts/samples and all rejects are accounted for.
- [ ] No credential literal appears in committed artifacts.
- [ ] Rollback, restore, and cutover rehearsal evidence is recorded.
