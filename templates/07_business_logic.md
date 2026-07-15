# Business-Logic Recovery and Target Contract

## Evidence and coverage

| Logic-bearing catalog | Hash/count | Explorer/report | Disposition coverage | Unresolved |
|---|---|---|---|---|
| Scripts (`05_scripts.json`, including root and `step_text`/comments) |  |  |  |  |
| Calculated fields (`01_tables.json`) |  |  |  |  |
| Custom functions (`08_custom_functions.json`) |  |  |  |  |
| Field validation/auto-enter (parsed + raw/manual) |  |  |  |  |
| Value lists (`06_value_lists.json`) |  |  |  |  |
| Conditional formatting (`09...`) |  |  |  |  |
| Hide-object rules (`10...`) |  |  |  |  |
| Security predicates/restrictions (`07_security.json`) |  |  |  |  |

Every source identity must map to a target rule/operation/presentation behavior, an approved retirement, a duplicate/contextual occurrence retained elsewhere, or `unresolved`. A script-only document is incomplete.

## Domain invariants and operations

| Domain/rule id | Plain-language invariant | Preconditions/inputs | Reads | Writes/found-set scope | Error/exception behavior | Source identities | Confidence/open question |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Target ownership

| Rule/operation | Server-domain/query/job/adapter/client | Interface | Transaction/concurrency | Authorization | Audit | Semantic tests |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Persistent invariants remain server-owned even when a FileMaker layout/field trigger invokes them. UI validation/visibility can mirror server behavior but cannot be the only enforcement point.

## Script dispositions

| Source identity | Group/name | Effects and evidence | Target owner/operation | Keep/replace/retire/unresolved | Dependencies/tests |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Do not retire navigation/startup/trigger-named scripts until field writes, authorization decisions, session initialization, calls, and external effects are traced.

## Calculations and custom functions

| Source identity | Context/dependencies | Meaning | Target implementation/signature | Coercion/null/timezone rules | Fixtures |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Exact formula duplicates retain separate context. A custom function is domain logic only when its body/call sites prove that classification.

## Validation and reference values

| Source rule/value list | Timing/override/stored-display semantics | Target DB/API/UI enforcement | Deliberate strengthening/change | Tests |
|---|---|---|---|---|
|  |  |  |  |  |

## Presentation and workflow signals

| CF/hide source ids | Condition | Presentation variants/object attribution | Domain/security cross-reference | Target behavior |
|---|---|---|---|---|
|  |  |  |  |  |

Conditional formatting and hide rules can reveal states/exceptions; they do not grant server access. Preserve every CSS/context variant and label unattributed objects.

## Bulk and integration safety

| Source operation | Reconstructed scope/direction | Credential handling | Retry/idempotency | Target contract | Failure tests |
|---|---|---|---|---|---|
|  |  | managed-secret reference only |  |  |  |

Never translate `Replace Field Contents` to an unqualified update. `Insert from URL` is outbound unless separate receiver evidence exists.

## Ambiguities and conflicts

| ID | Source behavior | Stakeholder description | Conflict/missing evidence | Risk | Required decision/proof |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Completion gate

- [ ] Provenance and every explorer exact-set verifier pass.
- [ ] Every logic-bearing catalog row has a disposition.
- [ ] Tier1/high-risk rules were checked against raw XML or the running source app.
- [ ] Found-set, null/empty, boundary, unauthorized, error, and retry fixtures exist where applicable.
- [ ] No credential literal appears in this document.
