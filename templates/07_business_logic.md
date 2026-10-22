# Business-Logic Recovery and Target Contract

## Evidence and coverage

| Logic | Object kind | Explorer | Count | Disposition coverage | Unresolved |
|---|---|---|---:|---|---|
| Scripts | `scripts` | script |  |  |  |
| Calculated fields | `tables` | table |  |  |  |
| Field validation/auto-enter | `tables` | table |  |  |  |
| Custom functions | `custom-functions` | function |  |  |  |
| Value lists | `value-lists` | value list |  |  |  |
| Conditional formatting | `layouts` | layout |  |  |  |
| Hide-object rules | `layouts` | layout |  |  |  |
| Triggers and buttons | `layouts` | layout |  |  |  |
| Custom menu overrides | `custom-menus` | menu |  |  |  |
| File triggers | `file` | file |  |  |  |
| Security predicates/restrictions | `privilege-sets` | security |  |  |  |

Every source identity (an object file, or a field or layout rule inside it) must map to a target rule/operation/presentation behavior, an approved retirement, a duplicate/contextual occurrence retained elsewhere, or `unresolved`. A script-only document is incomplete.

## Domain invariants and operations

| Domain/rule id | Plain-language invariant | Preconditions/inputs | Reads | Writes/found-set scope | Error/exception behavior | Object files | Open question |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Target ownership

| Rule/operation | Server-domain/query/job/adapter/client | Interface | Transaction/concurrency | Authorization | Audit | Semantic tests |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Persistent invariants remain server-owned even when a FileMaker layout/field trigger invokes them. UI validation/visibility can mirror server behavior but cannot be the only enforcement point.

## Script dispositions

| Object file | Folder/name | Effects and evidence | Target owner/operation | Keep/replace/retire/unresolved | Dependencies/tests |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Do not retire navigation/startup/trigger-named scripts until field writes, authorization decisions, session initialization, calls, and external effects are traced.

## Calculations and custom functions

| Object file and field id | Context/dependencies | Meaning | Target implementation/signature | Coercion/null/timezone rules | Fixtures |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Exact formula duplicates retain separate context. A custom function is domain logic only when its body/call sites prove that classification.

## Validation and reference values

| Source rule/value list | Timing/override/stored-display semantics | Target DB/API/UI enforcement | Deliberate strengthening/change | Tests |
|---|---|---|---|---|
|  |  |  |  |  |

## Presentation and workflow signals

| Layout file and object key | Condition | Effect (style or hide) | Domain/security cross-reference | Target behavior |
|---|---|---|---|---|
|  |  |  |  |  |

Conditional formatting and hide rules can reveal states and exceptions; they do not grant server access. Keep every distinct `Format:` and layout context.

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

- [ ] `catalog_contract.py verify` passes for every explorer.
- [ ] Every logic-bearing catalog row has a disposition.
- [ ] Every tier1 rule cites its object file and step number or field id.
- [ ] Found-set, null/empty, boundary, unauthorized, error, and retry fixtures exist where applicable.
- [ ] No credential literal appears in this document.
