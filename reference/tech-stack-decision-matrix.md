# Tech-Stack Decision Matrix

Choose a replacement architecture from project constraints and verified requirements. Framework popularity, AI coding mode, or a preference for fewer packages cannot override an established repository, security model, offline need, integration boundary, or team ownership model.

## Start with constraints

Record these before scoring candidates:

- established repository/runtime/database/API/UI stack and cost of changing it;
- team languages, operational experience, staffing, and maintenance horizon;
- web, native, mobile, offline, accessibility, and real-time requirements;
- deployment/network/data-residency/backup/observability constraints;
- user/concurrency/data volume and workload shape;
- identity provider and authorization complexity at operation, row, and field level;
- integrations, background jobs, reporting, file storage, and audit/compliance needs;
- deadline, budget, parallel FileMaker operation, and cutover strategy.

Honor hard constraints. A greenfield preference is not permission to replace a working project stack.

## Architecture candidates

| Candidate | Fits when | Risks to evaluate |
|---|---|---|
| Server-rendered monolith | Primarily web forms/reports, one team, modest interactivity, framework expertise | Rich-client/offline needs, authorization gaps hidden behind built-in auth, long-running work. |
| Full-stack TypeScript application | Existing TypeScript stack, rich interactions, shared types, server functions/API | Client/server boundary, data-fetching discipline, bundle/runtime complexity, authorization ownership. |
| API plus separate web/mobile clients | Multiple clients, native/offline requirement, independent lifecycle | More contracts/deployments, duplicated validation, auth/token complexity, versioning. |
| Modular monolith | Clear domains, one deployment/team, need internal boundaries | Boundary enforcement and transaction ownership. |
| Services | Independent teams/scaling/deployment or hard integration boundaries | Distributed transactions, observability, operational cost, duplicated data/contracts. Do not choose for aesthetic modularity. |

React, server-rendered MVC, and other UI approaches are implementation choices to evaluate, not quality proxies. AI assistance does not make one architecture universally safe; deterministic tests, types, linting, code review, and clear boundaries matter in every stack.

## Database scoring

Evaluate candidates on:

- transactions, constraints, JSON/full-text/geospatial needs;
- row-level security and authorization ownership;
- concurrency and connection model;
- backup/restore/PITR and operational support;
- migration tooling and team expertise;
- reporting/query complexity and extensions;
- deployment/data-residency constraints.

PostgreSQL is a strong default for complex relational migrations, not an automatic conclusion. SQLite can fit single-node/edge/small deployments with compatible write concurrency. MySQL/MariaDB can fit established operational environments. Score the actual target versions and hosting model.

## Authentication is not authorization

Framework/provider authentication can establish identity and session handling. It does not automatically implement FileMaker's:

- privilege-set capabilities;
- record predicates;
- field read/write restrictions;
- layout/route access;
- script/operation access;
- value-list access;
- extended privilege/access-channel rules;
- UI exceptions.

Score authentication integration and authorization expressiveness separately. Require default-deny server enforcement and negative tests regardless of framework.

## API and rendering style

Choose from use cases:

- server functions/actions for a single co-deployed web client;
- GraphQL for client-driven typed graphs when complexity and tooling justify it;
- REST for resource/operation contracts and broad integration compatibility;
- event/queue interfaces for asynchronous boundaries;
- direct server rendering for request/response workflows.

Do not require a REST artifact when the selected architecture exposes no separate REST API. Do not create generic CRUD endpoints for every base table. Derive operations from workflows and authorization.

## Weighted decision record

Use weights agreed with the user/team. Example structure:

| Criterion | Weight | Candidate A | Candidate B | Evidence/assumption |
|---|---:|---:|---:|---|
| Existing-stack fit |  |  |  |  |
| Authorization coverage |  |  |  |  |
| Delivery/team fit |  |  |  |  |
| UI/offline/client needs |  |  |  |  |
| Operations/deployment |  |  |  |  |
| Data/reporting fit |  |  |  |  |
| Ecosystem/maintenance risk |  |  |  |  |
| Total | 100 |  |  |  |

Label scores based on stakeholder preference, repository facts, measured requirements, or external evidence. Run a small spike for a high-impact unknown instead of manufacturing precision.

## Current external evidence

Software versions, maintenance activity, hosting prices, security support, and ecosystem adoption change. When they affect the decision:

1. search using the current year/date rather than a hardcoded year;
2. prefer official release/support/security documentation and primary surveys;
3. record access date and target version;
4. distinguish measured facts from inference;
5. avoid celebrity-company anecdotes as proof of fit.

## Recommendation format

For the primary and one viable alternative, report:

- architecture and component choices;
- constraints satisfied and tradeoffs accepted;
- authorization implementation approach;
- integration/background/file/reporting approach;
- deployment/backup/observability ownership;
- migration compatibility with the existing repo;
- risks, spike results, and reversal cost;
- why the alternative lost under the agreed weights.

Revisit the choice if discovery uncovers a hard constraint. Do not force a prior default through contradictory evidence.
