---
name: migrate-filemaker
description: Guide complete FileMaker Pro migrations from DDR XML to verified discovery, schema, authorization, business-logic, API, UI, and cutover artifacts. Use when analyzing FileMaker Database Design Report XML or parsed specs, comparing implementations, recovering scripts/calculations/layout/security semantics, recommending a replacement architecture, or planning and validating a FileMaker rebuild.
---

# FileMaker Migration Planner

Treat a FileMaker migration as source recovery, not document generation. A plausible artifact is not evidence. Preserve provenance, reconcile every derived catalog to its source, and mark unavailable semantics instead of inventing them.

## Set paths once

Infer these paths from the repository or ask when they cannot be discovered safely:

```bash
SKILL_DIR="/path/to/migrate-filemaker"
RAW_DIR="/path/to/implementation/raw"
SPECS_DIR="/path/to/implementation/specs"
ANALYSIS_DIR="/path/to/implementation/analysis"
CORE_DIR="/path/to/canonical/core"
```

Do not substitute hardcoded `ddr/specs` or `migration/` paths inside later steps. Keep implementation-specific evidence under its implementation directory. Put cross-implementation conclusions in an explicitly named comparison/canonical directory.

## Non-negotiable evidence rules

1. Treat raw DDR XML as immutable and sensitive. Never commit it or print credential literals.
2. Treat parsed JSON as trusted only when `_provenance.json` verifies the raw hashes, parser hash, spec hashes, topology declarations, and passing parser tests.
3. Stop on a failed extraction or provenance check. Do not ask whether to continue with corrupted inputs.
4. Treat counts as coverage evidence, not semantic evidence. Inspect representative source values and retain golden edge cases for calculations, steps, security predicates, and layout behavior.
5. Use stable source identities, never mutable array positions, for explorer state. Require exact identity-set equality before generating reports.
6. Use `07_security.json` as the primary authorization catalog. Hide-object rules are secondary UI/exception evidence and never grant server access.
7. Distinguish facts, inferences, product decisions, and unavailable evidence in every generated artifact.
8. Never claim an implementation-complete UI from the current layout JSON alone. Require raw-layout evidence and screenshots for labels, geometry, controls, tabs, triggers, and unnamed objects.

Read [reference/explorer-contract.md](reference/explorer-contract.md) before running an explorer. Read other resources only for the phase that needs them:

- DDR extraction: [reference/ddr-xml-reference.md](reference/ddr-xml-reference.md)
- FileMaker semantics: [reference/filemaker-concepts.md](reference/filemaker-concepts.md)
- Schema decisions: [reference/schema-translation-guide.md](reference/schema-translation-guide.md)
- Script behavior: [reference/script-translation-patterns.md](reference/script-translation-patterns.md)
- Logic detection: [reference/business-logic-detection.md](reference/business-logic-detection.md)
- Architecture selection: [reference/tech-stack-decision-matrix.md](reference/tech-stack-decision-matrix.md)

## Phase 0: Establish trustworthy inputs

Run the regression suite from the loaded skill directory:

```bash
cd "$SKILL_DIR"
python3 -m unittest discover -s tests
```

Then verify an existing extraction:

```bash
python3 "$SKILL_DIR/scripts/provenance.py" verify \
  "$RAW_DIR" "$SPECS_DIR" --parser "$SKILL_DIR/scripts/parse_ddr.py"
```

If verification fails or the manifest is missing, regenerate all specs from raw XML and create a new manifest. Do not merge new JSON with an older extraction.

```bash
rm -rf "$SPECS_DIR.new"
python3 "$SKILL_DIR/scripts/parse_ddr.py" "$RAW_DIR" "$SPECS_DIR.new"
python3 "$SKILL_DIR/scripts/provenance.py" create \
  "$RAW_DIR" "$SPECS_DIR.new" --parser "$SKILL_DIR/scripts/parse_ddr.py"
```

Inspect the new directory before replacing the old one. Preserve or archive old derived artifacts for comparison, but do not let explorers resume against changed specs.

Verify the extraction contract:

- All files `00_topology.json` through `10_hide_object_when.json` exist.
- Topology source identities match the supplied DDR set; unresolved references are enumerated and explained.
- Tables distinguish regular, calculated, summary, and global fields.
- Table occurrences resolve to base tables and source files where the DDR set permits.
- Every relationship predicate has both sides and an observed operator token.
- Layouts, scripts, value lists, security, custom functions, conditional formatting, and hide rules reconcile with the parser's self-check.
- Sample semantic fixtures include field operands in calculations, root scripts, populated `step_text`, conditional-formatting payloads, record/field/layout privileges, and redaction.

Current `07_security.json` does not contain FileMaker extended-privilege definitions. If they matter, inspect the raw `ExtendedPrivilege` catalog or obtain a manual export and label the result `raw/manual`; otherwise state `unavailable`, never `none`.

## Phase 1: Inventory and source coverage

Create the implementation app summary from [templates/00_app_summary.md](templates/00_app_summary.md). Read every spec catalog, including empty catalogs, and record its provenance hash/status.

Include:

- source-file topology and unresolved dependencies;
- base tables, table occurrences, relationship predicates, layouts, scripts, value lists, security, custom functions, conditional formatting, and hide rules;
- field categories and data types using the JSON tokens actually emitted;
- integration directions and script calls;
- known unavailable evidence, especially extended privileges and unextracted UI details;
- specialized logic candidates found with [reference/business-logic-detection.md](reference/business-logic-detection.md).

Do not infer authorization from role names or hide formulas. Do not infer keys from a field named `ID`. Do not describe a global as shared configuration without proving its use and initialization.

## Phase 1.5: Deep exploration

Run every explorer whose source catalog contains entries. An explorer directory is not a completion signal. Its source snapshot must match the current spec hash, and its CSVs must cover every `source_id` exactly once with the matching `source_hash`.

Use `scripts/catalog_contract.py` as specified in the shared explorer contract; do not recreate its identity or coverage logic ad hoc.

- Scripts: [workflows/fm-script-explorer.md](workflows/fm-script-explorer.md)
- Calculated fields: [workflows/fm-calc-explorer.md](workflows/fm-calc-explorer.md)
- Custom functions: [workflows/fm-func-explorer.md](workflows/fm-func-explorer.md)
- Conditional formatting: [workflows/fm-cf-explorer.md](workflows/fm-cf-explorer.md)
- Hide-object rules: [workflows/fm-hide-explorer.md](workflows/fm-hide-explorer.md)
- UI evidence: [workflows/fm-ui-spec.md](workflows/fm-ui-spec.md)
- Schema decisions: [workflows/fm-schema-builder.md](workflows/fm-schema-builder.md)

For scripts, read both structured `params` and `step_text` for every active step. Preserve populated comments as developer evidence. Classify persistent effects by where they must be enforced, not by whether a layout trigger invoked them.

For conditional formatting, separate shared conditions from presentation variants. For hide rules with no stable object attribution, label the target `unattributed`; do not guess.

## Phase 2: Discovery

Use [templates/01_discovery_answers.md](templates/01_discovery_answers.md). Ask only questions whose answers cannot be established from verified artifacts. Cover:

- migration goals, scope, deadlines, and parallel operation;
- current/future users and device/offline needs;
- identity provider, account provisioning, service accounts, and authorization expectations;
- active workflows, critical business invariants, exception handling, and reports;
- data volume, source timezone/DST policy, containers, and integrations;
- screenshots and UI behavior missing from the DDR;
- which legacy behaviors should be preserved, tightened, simplified, or retired.

When source evidence and a stakeholder description conflict, record both and open a decision. Do not silently choose one.

## Phase 3: Recommend

Use [templates/02_recommendations.md](templates/02_recommendations.md) and [reference/tech-stack-decision-matrix.md](reference/tech-stack-decision-matrix.md).

Honor an established repository stack unless discovery establishes a reason to change it. Choose architecture from constraints: team capability, offline/native clients, integration boundaries, authorization complexity, operational ownership, scale, and delivery risk. Separate authentication capability from authorization coverage.

When current ecosystem facts affect a recommendation, verify them against current primary sources using the current year. Label preference and inference separately from measured facts.

## Phase 4: Produce rebuild contracts

Generate the following from verified evidence and record each input hash:

1. `03_migration_plan.md` from [templates/03_migration_plan.md](templates/03_migration_plan.md)
2. `04_database_schema.sql` through [workflows/fm-schema-builder.md](workflows/fm-schema-builder.md)
3. `05_api_design.md` from [templates/05_api_design.md](templates/05_api_design.md)
4. `06_ui_spec.md` through [workflows/fm-ui-spec.md](workflows/fm-ui-spec.md)
5. `07_business_logic.md` from [templates/07_business_logic.md](templates/07_business_logic.md)
6. `08_auth_roles.md` from [templates/08_auth_roles.md](templates/08_auth_roles.md)

Apply these gates:

- **Schema:** preserve source keys until uniqueness and relationship evidence support a mapping. Resolve relationship sides through table occurrences. Preserve compound predicates. Add a surrogate key only as an explicit, reversible decision. Treat SQL constraints stricter than FileMaker validation as product decisions backed by profiling.
- **API:** derive operations from use cases and authorization rules, not one CRUD surface per table. Default deny at route, row, and field level. Distinguish outbound `Insert from URL` calls from inbound webhooks.
- **UI:** produce an evidence-bounded inventory unless screenshots/raw-layout analysis supply the missing presentation semantics. Never attach an unnamed hide rule to a guessed control.
- **Business logic:** reconcile scripts, calculations, custom functions, validations, value lists, conditional formatting, hide rules, and security predicates. A trigger can invoke server-owned domain logic.
- **Authorization:** reconcile account provisioning, privilege sets, table/record/field/layout/script/value-list access, access channels, service principals, route guards, and UI visibility. Deny by default and specify negative tests.
- **Data migration:** go beyond row counts and random samples. Require column profiles, stable-value hashes, duplicate/orphan checks, rejected-row accounting, business totals, encoding/timezone tests, and targeted edge cases.

## Phase 5: Completion audit

Before declaring the migration plan complete:

1. Re-run provenance verification.
2. Re-run each explorer's catalog coverage verifier.
3. Trace at least one high-risk conclusion in every logic/security/UI category back to raw XML or a screenshot, not only parsed JSON.
4. Verify every source catalog has a disposition in the business-logic coverage matrix.
5. Verify every source security dimension has an enforcement owner and negative test.
6. Verify every relationship target resolves to an evidenced unique key or is explicitly unresolved.
7. Verify generated artifacts contain no credential literals.
8. List unavailable evidence and open decisions honestly.

If any gate fails, the output is incomplete even when all expected files exist.
