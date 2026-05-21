---
name: migrate-filemaker
description: >
  Guide a full migration from FileMaker Pro to an open-source stack. Includes a built-in DDR
  parser that extracts structured specs from FileMaker Database Design Report XML exports.
  Parses the DDR, discovers requirements, recommends a tech stack, and generates a detailed
  rebuild plan with SQL schema and API design. Use when the user provides a FileMaker DDR XML
  export or directory, asks to migrate a FileMaker app, requests FileMaker-to-SQL/API/UI
  planning, or wants modernization recommendations for a FileMaker solution.
argument-hint: [path-to-ddr-xml-or-directory]
---

# FileMaker Migration Planner

Orchestrate a complete migration from a FileMaker Pro solution to a modern open-source stack. This skill runs in four phases, each producing a checkpoint file so work can be resumed across sessions.

This skill targets Claude Code and assumes Claude Code interactive question tools are available.

**Reference documents** (consult these during analysis):
- [FileMaker Concepts → Modern Equivalents](reference/filemaker-concepts.md)
- [Schema Translation Guide](reference/schema-translation-guide.md)
- [Script Translation Patterns](reference/script-translation-patterns.md)
- [Tech Stack Decision Matrix](reference/tech-stack-decision-matrix.md)
- [DDR XML Structure Reference](reference/ddr-xml-reference.md)

**Output templates** (use these structures for all generated documents):
- [templates/00_app_summary.md](templates/00_app_summary.md)
- [templates/01_discovery_answers.md](templates/01_discovery_answers.md)
- [templates/02_recommendations.md](templates/02_recommendations.md)
- [templates/03_migration_plan.md](templates/03_migration_plan.md)
- [templates/04_database_schema.sql](templates/04_database_schema.sql)
- [templates/05_api_design.md](templates/05_api_design.md)
- [templates/06_ui_spec.md](templates/06_ui_spec.md)
- [templates/07_business_logic.md](templates/07_business_logic.md)
- [templates/08_auth_roles.md](templates/08_auth_roles.md)

---

## Before Starting: Check for Previous Progress

Before running any phase, check which checkpoint files and explorer directories already exist:

```
migration/
  00_app_summary.md          ← Phase 1 output
  fm-scripts-explorer/       ← Phase 1.5 output (Script Explorer)
  fm-cf-explorer/            ← Phase 1.5 output (CF Explorer)
  fm-hide-explorer/          ← Phase 1.5 output (Hide-Object-When Explorer)
  fm-calc-explorer/          ← Phase 1.5 output (Calculated Fields Explorer)
  fm-func-explorer/          ← Phase 1.5 output (Custom Functions Explorer)
  01_discovery_answers.md    ← Phase 2 output
  02_recommendations.md      ← Phase 3 output
  03_migration_plan.md       ← Phase 4 output
  04_database_schema.sql     ← Phase 4 output
  05_api_design.md           ← Phase 4 output
  06_ui_spec.md              ← Phase 4 output
  07_business_logic.md       ← Phase 4 output
  08_auth_roles.md           ← Phase 4 output
```

If `00_app_summary.md` exists but `01_discovery_answers.md` does not, Phase 1.5 (Deep Exploration) is the next step — not Phase 2. Check which explorer directories already exist and run only the missing ones before proceeding to discovery.

If a phase's output file exists, ask:
> "Phase N (description) appears complete — I found `migration/NN_filename.md`. Would you like to review it, redo it, or continue to Phase N+1?"

**Redo cascading:** If the user chooses to redo a phase, warn them before proceeding:
> "Redoing Phase N will make the outputs from Phase N+1 onward stale — they were generated from the previous answers. I'll redo this phase, then list which downstream files still exist so you can decide whether to regenerate them."

After redoing, check which downstream checkpoint files still exist and ask: "These files reflect the old answers — would you like to regenerate them now, or review them first?"

Resume from the earliest incomplete phase.

---

## Phase 1: Parse & Understand

### Step 1.1: Run the DDR Parser

First, verify Python is available:

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null
```

If neither command succeeds, stop and tell the user:
> "The DDR parser requires Python (3.6+). Please install Python and try again — on macOS: `brew install python3`, on Ubuntu/Debian: `sudo apt install python3`."

Run the built-in DDR parser to extract specs from the DDR XML. Always pass `ddr/specs` as the output directory so downstream steps find the files in the expected location. The parser auto-detects multi-file solutions — if the directory contains multiple `FMPReport type="Report"` XMLs, all are parsed and merged:

```bash
python3 ~/.claude/skills/migrate-filemaker/scripts/parse_ddr.py "$ARGUMENTS" ddr/specs
```

If the script is not at the personal skills path, try the project-local path:

```bash
python3 .claude/skills/migrate-filemaker/scripts/parse_ddr.py "$ARGUMENTS" ddr/specs
```

If neither path contains the parser, stop and tell the user:
> "The DDR parser script could not be found. Expected locations: `~/.claude/skills/migrate-filemaker/scripts/parse_ddr.py` or `.claude/skills/migrate-filemaker/scripts/parse_ddr.py`. Please ensure the migrate-filemaker skill is installed correctly and try again."

If `ddr/specs/` already exists with all 11 JSON files (including `00_topology.json`, `09_conditional_formatting.json`, and `10_hide_object_when.json`), skip parsing and use the existing specs. Confirm with the user: "Found existing specs — using those. Re-run the parser if you want fresh extraction."

### Step 1.2: Verify Extraction Quality

Verify the parser output before proceeding:
1. **Topology** (`00_topology.json`): Confirm file count matches expectations. For multi-file solutions, verify cross-file references are resolved (check `unresolved_references` is empty or only has expected missing files)
2. Tables have fields properly separated into `fields`, `calculated`, `summary`, `globals`
3. Table occurrences all have a non-null `base_table`. For multi-file solutions, TOs with `external_file_reference` should have `resolved_source_file`
4. Relationships have join predicates with both left and right field names
5. Major layouts have populated fields/portals/buttons arrays
6. Scripts have parsed steps with params (not just step names). Cross-file script calls should have `external_file` in params
7. Value lists have their entries or source fields
8. Custom functions have calculation text

If any check fails, report the issue and ask whether to continue or fix first.

### Step 1.3: Analyze & Produce App Summary

Read all spec files (01 through 08, plus 09 and 10 if they contain data) and produce `migration/00_app_summary.md` using the template structure. The analysis must include:

**Application Profile:**
- Derive the app name from the DDR filename or table naming patterns
- For multi-file solutions: note the file structure (e.g., "UI + Data separation file") and which tables belong to which file
- Infer the domain/purpose from table names, field names, and script names
- Calculate a complexity score using these thresholds:
  - **Simple:** <5 real tables, <10 scripts, <5 layouts
  - **Medium:** 5–15 real tables, 10–50 scripts, 5–20 layouts
  - **Complex:** 15–30 real tables, 50–150 scripts, 20–50 layouts
  - **Enterprise:** >30 real tables, >150 scripts, >50 layouts
- Count "real tables" as those with at least one schema field (not globals-only tables)

**Data Model Summary:**
- List each real table with its schema field count, calculated field count, and record count
- Identify the core entity tables vs. junction/lookup tables
- Note any tables that are globals-only (app-state tables, not real data)
- Summarize relationship graph: key joins, one-to-many patterns, self-joins

**Feature Map:**
- Group scripts by their `group` path to identify functional domains
- Map each domain to likely application features (e.g., "Invoice Scripts" → invoicing)
- Note scripts that are clearly UI-only (navigation, dialog) vs. business logic
- Identify any script patterns suggesting integrations (email, export, API calls)

**UI Summary:**
- Count layouts by table assignment
- Identify list/detail layout pairs
- Note layouts with portals (master-detail patterns)
- Flag layouts with many buttons (complex user workflows)

**Security Model:**
- List privilege sets and their access levels
- Note any extended privileges
- Count active vs. inactive accounts

**Red Flags** (items that will need special attention during migration):
- Complex unstored calculations that reference related data
- Heavy use of global fields for state management
- Container fields (file storage)
- Cross-file script calls (scripts calling into other FM files — tightly coupled multi-file logic)
- Unresolved external file references (DDR missing for a referenced file)
- Heavy conditional formatting / hide-object-when rules (check `09_conditional_formatting.json` and `10_hide_object_when.json` counts) — these often encode authorization models, workflow state machines, and business rules invisible in the data model. If counts are significant (>100 rules), recommend running the Conditional Formatting and Hide-Object-When Explorer workflows for deep analysis.

**Specialized Business Logic Detection:**

Scan scripts for domain-specific logic that can't be inferred from the app type. See [reference/business-logic-detection.md](reference/business-logic-detection.md) for detection signals, plumbing filters, and the required output format. Present findings as a "Specialized Business Logic" section in the app summary, or note none found.

Present the summary to the user before proceeding.

---

## Phase 1.5: Deep Exploration (Required Gate)

**Do not start Phase 2 until all applicable explorers are complete.**

Run all explorers that have data. This is not optional — the explorers extract the information that makes Phase 2 discovery meaningful and Phase 4 planning precise. Script categories, the auth model, business logic thresholds, and custom function translations are all in hand before you ask the user a single question. There is no downside to running them.

Each explorer is incremental — run a batch at a time (`count` to see what's there, `all` to process everything, `reports` to generate reports from completed CSVs). All items get a documented row. Nothing is silently dropped.

Check which explorers apply based on the Phase 1 summary, then run each one:

---

### Script Explorer — Always Run
Read [workflows/fm-script-explorer.md](workflows/fm-script-explorer.md) and follow its methodology. Produces per-folder CSV catalogs + six reports in `migration/fm-scripts-explorer/`. Every migration has scripts. Run this first — the script categorization feeds directly into Phase 4 business logic mapping.

---

### Conditional Formatting Explorer — Run If Any CF Rules Found
Read [workflows/fm-cf-explorer.md](workflows/fm-cf-explorer.md) and follow its methodology. Produces per-layout CSV catalogs + three reports in `migration/fm-cf-explorer/`. CF formulas encode financial thresholds, status pipelines, and authorization states that are invisible in the data model. Skip only if Phase 1 found zero CF rules.

---

### Hide-Object-When Explorer — Run If Any Rules Found
Read [workflows/fm-hide-explorer.md](workflows/fm-hide-explorer.md) and follow its methodology. Produces per-layout CSV catalogs + four reports in `migration/fm-hide-explorer/`. These rules frequently encode the full authorization model and workflow state machines. Skip only if Phase 1 found zero hide-object-when rules.

---

### Calculated Fields Explorer — Run If Any Calculated Fields Found
Read [workflows/fm-calc-explorer.md](workflows/fm-calc-explorer.md) and follow its methodology. Produces per-table CSV catalogs + three reports in `migration/fm-calc-explorer/`. Skip only if all tables have zero calculated fields.

---

### Custom Functions Explorer — Run If Any Custom Functions Found
Read [workflows/fm-func-explorer.md](workflows/fm-func-explorer.md) and follow its methodology. Produces a single CSV + three reports in `migration/fm-func-explorer/`. Custom functions are the shared logic layer called from scripts, calculated fields, and layout formulas. Skip only if the solution has zero custom functions.

---

When all applicable explorers are complete, present a brief summary to the user:

> "Deep exploration complete. Here's what the explorers found:
> - Scripts: [N scripts across N groups — key findings]
> - Conditional formatting: [N rules — notable patterns]
> - Hide-object-when: [N rules — auth model notes]
> - Calculated fields: [N fields — business logic detected]
> - Custom functions: [N functions — shared logic]
>
> Ready to start Phase 2 discovery."

If the user closed the session after Phase 1 and is resuming, check which explorer output directories already exist (`migration/fm-scripts-explorer/`, `migration/fm-cf-explorer/`, etc.) and skip completed explorers. Only run what's missing.

---

## Phase 2: Discovery

This phase is interactive. Ask questions in small conversational groups (2–3 questions at a time), not as a survey dump. Adapt follow-up groups based on earlier answers. Skip questions that become irrelevant.

Use the AskUserQuestion tool for each group with appropriate options. Allow "You decide" / "No preference" as valid answers.

### Group 1 — Goals & Scope

Ask about:
1. **Migration driver:** What's motivating the move away from FileMaker? (Licensing costs, scalability limits, web/mobile access, team growth, vendor lock-in, other)
2. **Rebuild scope:** Full rebuild of all features, or partial? Any features to drop or simplify?
3. **Priority:** What's the single most important thing the new system must do well?

### Group 2 — Users & Scale

Ask about:
1. **Current users:** How many concurrent users today? Expected growth?
2. **Access patterns:** Desktop only, or also mobile/tablet? Need offline capability?
3. **User roles:** How many distinct roles/permission levels? (Reference the privilege sets found in Phase 1)

### Group 3 — UI Style & Design

Ask about:
1. **Screenshots of current FM app:** Ask the user to provide screenshots of their current FileMaker layouts — especially the most-used screens. Use the Read tool to view any provided image files. Note what works and what doesn't about the current UI from the user's perspective.
2. **Desired UI style:** What visual direction do they want? Options:
   - **Clean & minimal** — lots of whitespace, simple forms, modern SaaS look
   - **Data-dense & dashboard-heavy** — tables, charts, dense information display
   - **Match current FM look** — keep it familiar, minimize user retraining
   - **Something different entirely** — ask them to describe or provide references
3. **Reference apps or sites:** Ask for screenshots or links to any apps, websites, or products whose look and feel they admire. These become the design north star for the frontend build.

Record which screenshots were provided and note key observations: layout density, color usage, navigation patterns, form complexity. These feed directly into the Frontend and CSS/Component Library recommendations in Phase 3 and the UI Spec in Phase 4.

### Group 4 — Technical Preferences

Ask about:
1. **Coding mode:** Who is primarily writing this — AI-generated (vibe-coded), human developers, or a hybrid?
2. **Stack preferences:** Any hard requirements? (e.g., must use PostgreSQL, specific cloud provider, Docker required)
3. **Deployment target:** Cloud (which provider?), on-premise, or hybrid?
4. **Separate frontend need:** Is there a specific reason you'd need a separate frontend app — such as a native mobile app, offline access, or real-time collaborative editing? (Most internal tools and B2B apps don't need one.)

**Based on the coding mode answer, branch here:**

**If AI / vibe-coded:**
> "AI-generated code works best with full-stack MVC frameworks — Django, Laravel, and Rails. These have one obvious way to do everything: one ORM, one migration tool, one auth library. AI-generated React code almost universally misuses state management and data fetching in ways that appear to work in development but fail under real conditions. We'll use an MVC framework. The only remaining question is which language fits your team."
Skip to the language sub-question in the decision matrix. Do not ask about separate frontend preference unless real-time collab or native mobile came up in Groups 1–3.

**If human / hybrid:**
> "What language does your team primarily write in?"

Then use the WebSearch tool to pull current, real-world data before recommending anything. Search for:
- `"[language] web framework 2025 most popular production"`
- `"[framework A] vs [framework B] 2025"`
- Stack Overflow Developer Survey current year results for that language's top frameworks
- GitHub star history and recent commit activity for the top 2–3 candidates

Present the search findings to the user in plain language — community size, production adoption, recent momentum, any notable concerns — and let them weigh in before you make a recommendation. The goal is that they feel like they researched this, not that they accepted your default.

### Group 5 — Constraints

Ask about:
1. **Timeline:** When do you need this running? Is there a hard deadline?
2. **Budget:** Any budget constraints for hosting/infrastructure?
3. **Parallel operation:** Will the FM system run alongside the new one during transition?

*Skip Group 5 if the user indicated in Group 1 that this is exploratory / no timeline pressure.*

### Group 6 — Data & Integrations

Ask about:
1. **Data migration:** Need to migrate existing records? How many records in the largest table? (Reference record counts from Phase 1)
2. **External integrations:** Any connections to external systems (email, payment, other databases, APIs)?
3. **Reporting:** Any critical reports that must be replicated?

*Skip if Phase 1 shows a simple app with <1000 total records and no integration scripts.*

### Group 7 — Specialized Business Logic

*Only ask this group if Phase 1 detected specialized business logic scripts.*

Present the flagged script groups from the App Summary and ask about each domain:

> "I found [N] areas with specialized business logic that can't be inferred from the app type:
>
> 1. **[Domain]** — [brief description from Phase 1 detection]
> 2. **[Domain]** — [brief description]
> ...
>
> For each of these, can you describe the business rules? Specifically:
> - What is this logic supposed to accomplish?
> - Are the rules fixed, or do they change (e.g., pricing tiers updated annually)?
> - Must the rules be preserved exactly, or is this an opportunity to simplify?"

After discussing the flagged scripts, ask:

> "Are there any other scripts or business rules in the system that are critical to how your business operates — things that wouldn't be obvious from the data model? For example, custom calculations, compliance rules, or specialized workflows that took significant effort to build."

Record the answers with enough detail to drive the Phase 4 business logic mapping — capture the *why* behind the logic, not just the *what*.

*Skip if Phase 1 found no specialized business logic AND the app complexity is Simple or Medium.*

### Save Discovery Results

Write all answers to `migration/01_discovery_answers.md` using the template structure. Include the raw answers and any inferences drawn from the conversation.

---

## Phase 3: Recommend

Analyze the specs (Phase 1) and discovery answers (Phase 2) together. Consult the [Tech Stack Decision Matrix](reference/tech-stack-decision-matrix.md) for scoring guidance.

Produce `migration/02_recommendations.md` using the template structure:

### 3.1: Tech Stack Selection

The default is a **full-stack MVC monolith** (Django, Laravel, or Rails). These frameworks cover database, ORM, auth, admin, migrations, email, background jobs, and server-rendered UI in a single package — 2–3 decisions before writing features, not 12–15. This is the right default for almost every FileMaker migration: internal tools, B2B SaaS, single-team applications.

Only recommend a separate frontend (React, Vue, Svelte) if discovery answers document a specific need: native mobile app, offline-first PWA, real-time collaborative editing, or a team already deeply invested in a JS framework. "It's what everyone uses" is not a reason.

For each layer, recommend a **primary** choice and one **alternative**, with reasoning:

- **Database:** PostgreSQL vs. MySQL vs. SQLite — based on complexity, scale, feature needs. PostgreSQL is the default.
- **Full-Stack Framework:** Django (Python), Laravel (PHP), or Rails (Ruby) — match team language. Django if no preference. If a separate frontend is genuinely justified, recommend an MVC API backend + frontend framework combination and document what justified the split.
- **Interactivity layer:** For MVC monoliths — HTMX/Alpine.js (Django/Laravel) or Hotwire (Rails). Only recommend a full JS framework if the separate frontend case is met.
- **Authentication:** Based on the FM security model and deployment context. Default to framework built-in auth.
- **Deployment:** Based on budget, scale, team ops experience. PaaS (Railway, Render) is the default.

### 3.2: Architecture Pattern

Choose one with justification:
- **Monolith:** Simple apps, small teams, fast to build
- **Modular Monolith:** Medium complexity, clear domain boundaries, easy to split later
- **Microservices:** Only if genuinely needed (high scale, multiple teams, independent deployment)

Default recommendation should be **modular monolith** for most FileMaker migrations — they are typically single-team applications with clear domain boundaries.

### 3.3: Migration Strategy

Recommend one:
- **Phased:** Build core features first, migrate data, add remaining features iteratively. Lower risk. Preferred for most FM migrations.
- **Big Bang:** Build everything, switch over at once. Only for very simple apps or hard deadlines.

### 3.4: Feature Priority

Order the functional domains identified in Phase 1 by migration priority:
1. Core data management (CRUD for main entities)
2. Business logic (scripts that enforce rules)
3. Reporting and views
4. User management and auth
5. Integrations
6. Nice-to-have features

### Present & Adjust

Present the full recommendation document to the user. Ask:
> "Do these recommendations look right? Anything you'd like me to adjust before I generate the detailed migration plan?"

Incorporate any feedback before proceeding to Phase 4.

---

## Phase 4: Plan

Generate the detailed rebuild artifacts. Consult the reference documents for translation patterns:
- [Schema Translation Guide](reference/schema-translation-guide.md) for data types and patterns
- [Script Translation Patterns](reference/script-translation-patterns.md) for business logic mapping
- [FileMaker Concepts](reference/filemaker-concepts.md) for concept mapping

### Before Generating: Confirm the Plan

Before writing any file, confirm with the user what Phase 4 will produce:

> "I'm ready to generate the Phase 4 artifacts:
>
> - `03_migration_plan.md` — phased build plan with effort estimates and risk register
> - `04_database_schema.sql` — schema builder (confirms decisions with you before writing)
> - `05_api_design.md` — RESTful endpoints plus custom business logic endpoints
> - `06_ui_spec.md` — UI spec builder (full page inventory, component mapping, form specs)
> - `07_business_logic.md` — script categorization and specialized logic translation
> - `08_auth_roles.md` — privilege set mapping and access control model
>
> Shall I proceed?"

Incorporate any feedback, then proceed.

### 4.1: Migration Plan (`migration/03_migration_plan.md`)

Using the template, produce:
- **Phase breakdown** with clear milestones and dependencies
- **Effort estimates** per phase (relative sizing: S/M/L/XL, not hours)
- **Risk register** with mitigations
- **Data migration plan** (if applicable): extraction approach, transformation rules, validation strategy
- **Testing strategy** per phase
- **Rollback plan** if the new system has issues

### 4.2: Database Schema (`migration/04_database_schema.sql`)

Read [workflows/fm-schema-builder.md](workflows/fm-schema-builder.md) and follow its methodology to generate the database schema. It reads `ddr/specs/` and the tech stack choice from `migration/02_recommendations.md`, presents all key schema decisions for user confirmation, and writes `migration/04_database_schema.sql`.

See [workflows/fm-schema-builder.md](workflows/fm-schema-builder.md) for the full generation methodology.

### 4.3: API Design (`migration/05_api_design.md`)

Using the template, produce:
- **RESTful endpoints** for each real table (standard CRUD)
- **Custom endpoints** derived from business-logic scripts
- **Authentication endpoints** based on the security model
- **Batch/import endpoints** if data migration is needed
- Group endpoints by domain (matching the feature map from Phase 1)

### 4.4: Business Logic Mapping (`migration/07_business_logic.md`)

**If Script Explorer was run** (`migration/fm-scripts-explorer/` exists): read the CSV catalogs and reports — especially `reports/summary.md`, `reports/tier1-critical.md`, and `reports/data-writes.md`. Use the per-script classifications (type, logic_tier) to drive categorization instead of re-analyzing raw scripts. The explorer's module assignments, backbone script identification, and "hardest to migrate" analysis should directly inform this document.

Using [templates/07_business_logic.md](templates/07_business_logic.md), produce `migration/07_business_logic.md` with two sections:

**Section 1 — Script Categorization**

Categorize every script (or script group) as one of:
- **Drop:** Navigation-only scripts, UI helpers that the new framework handles
- **API Endpoint:** Scripts that perform data operations triggered by user action
- **Service Function:** Background logic, validation rules, calculations
- **UI Handler:** Client-side logic (form validation, conditional visibility)

Present as a table grouped by domain: `Script Group | Script Name | Category | Notes`.

**Section 2 — Specialized Logic Detail**

For each specialized business logic domain flagged in Phase 1 and explored in Phase 2 Group 7:

1. **Document the business rules** in plain language using the user's descriptions from Discovery
2. **Trace the script logic** — walk through the actual parsed steps and calculations to produce pseudocode or a logic flowchart that captures the algorithm
3. **Map custom functions** used by these scripts — include the function's calculation text and translate it to a modern equivalent (e.g., a utility function signature with documented inputs/outputs)
4. **Specify the implementation target** — where this logic lives in the new system (database function, service layer function, API middleware, etc.) with enough detail that a developer can implement it without referencing the original FileMaker scripts
5. **Flag any ambiguity** — if the parsed script logic doesn't fully match the user's description from Discovery, or if calculations are too opaque to confidently translate, note it as requiring manual verification during implementation

### 4.5: Auth & Roles Mapping (`migration/08_auth_roles.md`)

**If Hide-Object-When Explorer was run** (`migration/fm-hide-explorer/` exists): read `reports/summary.md` and `reports/auth-model.md`. These contain the full authorization model extracted from hide-object-when formulas — often more complete than the privilege set catalog alone, because FM developers frequently implement fine-grained access control through hide conditions rather than privilege sets.

Using [templates/08_auth_roles.md](templates/08_auth_roles.md), produce `migration/08_auth_roles.md` with:
- **Role definitions** — each FM privilege set mapped to a named role with its permission boundaries
- **Record-level access** — row-level security rules or middleware checks derived from FM record access privileges
- **Route/page permissions** — FM layout access restrictions mapped to route guards
- **Authorization layer map** — if the Hide-Object-When Explorer identified multiple authorization layers (role checks, permission flags, record sensitivity, SQL-based checks), document each layer explicitly and map it to its modern equivalent (middleware, store guard, component-level conditional, database RLS policy)
- **Session variables** — any `$$` globals used as permission state, with their modern equivalents (session store, JWT claims, server-side session)
- **Open questions** — any privilege rules that are ambiguous or require business clarification before implementation

### 4.6: UI Spec (`migration/06_ui_spec.md`)

Read [workflows/fm-ui-spec.md](workflows/fm-ui-spec.md) and follow its methodology to generate the frontend specification. It reads the discovery answers, layout specs, and Hide-Object-When / Conditional Formatting Explorer reports (if run), then writes `migration/06_ui_spec.md` — a complete page inventory, component mapping, form specs, and responsive requirements.

See [workflows/fm-ui-spec.md](workflows/fm-ui-spec.md) for the full specification methodology.

### Present Final Deliverables

Summarize what was generated and where to find each file:

```
migration/
  00_app_summary.md        ← Application analysis
  01_discovery_answers.md  ← Requirements gathered
  02_recommendations.md    ← Tech stack & architecture
  03_migration_plan.md     ← Phased rebuild plan
  04_database_schema.sql   ← Database DDL
  05_api_design.md         ← API endpoint design
  06_ui_spec.md            ← Frontend UI specification
  07_business_logic.md     ← Script categorization & specialized logic
  08_auth_roles.md         ← Role definitions & access control model
```

Suggest next steps:
1. Review all documents with the team
2. Set up the development environment with the recommended stack
3. Begin Phase 1 of the migration plan (core data model + CRUD)
