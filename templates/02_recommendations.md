# Technology and Architecture Recommendation

## Decision basis

| Constraint/requirement | Weight / hard gate | Evidence | Primary fit | Alternative fit |
|---|---|---|---|---|
| Existing repository compatibility |  |  |  |  |
| Team/delivery fit |  |  |  |  |
| Authorization coverage |  |  |  |  |
| Client/offline/accessibility needs |  |  |  |  |
| Data/reporting/integration needs |  |  |  |  |
| Deployment/operations/compliance |  |  |  |  |
| Reversal/migration cost |  |  |  |  |

Record product preferences separately from repository facts and current external evidence.

## Recommendation

| Layer | Primary | Alternative | Evidence-based rationale / tradeoff |
|---|---|---|---|
| Architecture/deployment unit |  |  |  |
| Runtime/framework |  |  |  |
| UI/rendering/client |  |  |  |
| Database/data access |  |  |  |
| API/server-operation style |  |  |  |
| Background jobs/events |  |  |  |
| File/container storage |  |  |  |
| Authentication/identity provider |  |  |  |
| Authorization enforcement |  |  |  |
| Testing/observability/deployment |  |  |  |

Do not claim built-in authentication implements FileMaker authorization. Explain operation, row, field, route/layout, script/value-list, access-channel, service-principal, and UI enforcement separately.

## Existing-stack decision

- Established stack: <!-- measured from repo -->
- Keep/change decision: <!-- explicit -->
- Evidence requiring change, if any: <!-- hard constraint -->
- Migration/reversal cost: <!-- concrete -->

## Authorization architecture

| Source dimension | Target owner/mechanism | Default deny | Negative-test strategy |
|---|---|---|---|
| Roles/capabilities |  |  |  |
| Record predicates |  |  |  |
| Field read/write |  |  |  |
| Operations/scripts/value lists |  |  |  |
| Routes/layouts |  |  |  |
| Extended privileges/access channels |  |  |  |
| UI visibility |  |  | Secondary only |

## Interface style

State why the selected system uses server actions/functions, GraphQL, REST, events, or a combination. Derive interfaces from use cases; do not promise generic CRUD for each base table.

## Migration strategy

| Increment | User/business outcome | Source scope | Dependencies | Exit evidence | Rollback boundary |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Do not defer authorization or core invariants until after generic data entry is exposed.

## Current external evidence

| Claim affecting choice | Primary source/version | Access date | Fact or inference |
|---|---|---|---|
|  |  |  |  |

Use current-year/current-version sources. Avoid popularity anecdotes as proof of suitability.

## Risks, spikes, and decisions

| Risk/unknown | Impact | Proof/spike | Owner | Decision deadline |
|---|---|---|---|---|
|  |  |  |  |  |

## Rejected alternative

Explain why the viable alternative lost under the stated constraints, what would reverse the decision, and which tradeoff the primary accepts.
