# Discovery Record

## Evidence basis

| Verified artifact | Hash/status | What it establishes |
|---|---|---|
| App summary |  |  |
| Explorer catalogs/reports |  |  |
| Screenshots/raw/manual exports |  |  |

Use these labels throughout: `source fact`, `stakeholder statement`, `inference`, `product decision`, `unavailable`, and `conflict`.

## Goals and scope

| Question | Answer | Label | Consequence / open issue |
|---|---|---|---|
| Migration driver and success measure |  |  |  |
| In-scope offices/files/workflows |  |  |  |
| Explicitly retire/simplify/preserve |  |  |  |
| Deadline/budget/parallel operation |  |  |  |
| Rollback and acceptable outage/data loss |  |  |  |

## Users, identity, and authorization

| Question | Answer | Label | Consequence / open issue |
|---|---|---|---|
| Current/projected users and concurrency |  |  |  |
| Identity provider and MFA |  |  |  |
| Account invite/reset/mapping plan |  |  | DDR has no password/hash |
| Disabled accounts and service principals |  |  |  |
| Role/capability ownership and approvers |  |  |  |
| Record/field/operation exceptions |  |  |  |
| API/export/admin access channels |  |  |  |

Do not replace measured privilege rules with stakeholder memory. Record conflicts for reconciliation.

## Workflows and business invariants

| Domain/workflow | Current purpose | Must preserve/change | Failure/exception behavior | Source identities | Decision owner |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Ask about tier1 scripts, calculations, custom functions, validation, value lists, conditional formatting, hide rules, and security predicates—not only scripts.

## Data migration

| Topic | Answer/decision | Evidence needed |
|---|---|---|
| Source record/container volumes |  | profile/export |
| Candidate keys/duplicates/orphans |  | column profiles |
| Historical/audit retention |  | policy/source |
| Source timezone and DST policy |  | office/server records |
| Empty/null/encoding/decimal handling |  | profiles/fixtures |
| Calculated/summary value treatment |  | rule decision |
| Rejected-row correction ownership |  | runbook |
| Parallel-write reconciliation |  | cutover design |

## UI and access patterns

| Topic | Answer | Evidence/status |
|---|---|---|
| Desktop/mobile/tablet/offline |  |  |
| Most-used and highest-risk screens |  | screenshots/recordings |
| Data density/navigation preferences |  |  |
| Accessibility requirements |  |  |
| Print/report/device workflows |  |  |
| Current pain points worth redesigning |  |  |

List each supplied screenshot/recording and the layouts/workflows it proves. Missing visual evidence keeps those screens inventory-only or behavior-ready.

## Existing technology and operations

| Topic | Answer/fact | Hard constraint? | Evidence |
|---|---|---|---|
| Existing repository stack |  |  | manifest/config |
| Team languages/frameworks |  |  |  |
| Hosting/network/data residency |  |  |  |
| CI/CD, observability, backup/restore |  |  |  |
| Security/compliance requirements |  |  |  |
| Native/offline/real-time clients |  |  |  |

## Integrations and reports

| Integration/report | Direction | Contract/data | Auth/secrets owner | Retry/audit | Must preserve? |
|---|---|---|---|---|---|
|  | inbound/outbound/bidirectional |  |  |  |  |

`Insert from URL` is outbound evidence. Do not call it an inbound webhook without separate proof.

## Conflicts and open decisions

| ID | Source evidence | Stakeholder statement | Risk | Required resolution | Owner |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Approved requirements

| Requirement | Acceptance evidence | Priority | Owner |
|---|---|---|---|
|  |  |  |  |

Do not move a conflict or inference into this table until it is resolved/approved.
