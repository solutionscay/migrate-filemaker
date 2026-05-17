# migrate-filemaker

A Claude Code skill that guides a full migration from FileMaker Pro to an open-source stack. Point it at a FileMaker Database Design Report (DDR) XML export and it will parse the DDR, discover your requirements through conversation, recommend a tech stack, and generate a detailed rebuild plan complete with SQL schema, API design, UI spec, and business logic mapping.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI, desktop app, or IDE extension)
- Python 3.6+
- A FileMaker DDR XML export (generated from FileMaker Pro via File > Save a Copy as XML)

## Installation

Clone or copy this repository into your Claude Code skills directory:

```bash
# Personal skills directory (available in all projects)
git clone https://github.com/solutionscay/migrate-filemaker.git ~/.claude/skills/migrate-filemaker

# Or project-local (available only in that project)
git clone https://github.com/solutionscay/migrate-filemaker.git .claude/skills/migrate-filemaker
```

## Usage

In Claude Code, invoke the skill with the path to your DDR export:

```
/migrate-filemaker path/to/your/DDR.xml
```

You can also pass a directory containing multiple DDR XML files (for multi-file FileMaker solutions):

```
/migrate-filemaker path/to/ddr-exports/
```

The skill runs interactively — it will ask you questions about your goals, users, constraints, and preferences before generating the migration plan.

## What It Does

The migration runs in four phases, each producing checkpoint files so work can be paused and resumed:

### Phase 1: Parse & Understand

Runs the built-in DDR parser to extract structured JSON specs from the XML, then analyzes the solution to produce an application summary covering:

- Data model (tables, fields, relationships)
- Feature map (scripts grouped by domain)
- UI inventory (layouts, portals, buttons)
- Security model (privilege sets, accounts)
- Red flags (container fields, globals-heavy state, complex calculations)
- Specialized business logic detection

### Phase 2: Discovery

An interactive conversation (not a survey dump) that explores:

- Migration goals and scope
- Users and scale requirements
- UI style preferences and design references
- Technical preferences and team skills
- Timeline and budget constraints
- Data migration and integration needs
- Specialized business logic details

### Phase 3: Recommend

Produces a tech stack recommendation covering database, backend, frontend, auth, deployment, and architecture pattern — with primary and alternative choices, scored against your specific needs.

### Phase 4: Plan

Generates the full set of migration artifacts:

| File | Contents |
|------|----------|
| `03_migration_plan.md` | Phased build plan with effort estimates and risk register |
| `04_database_schema.sql` | Complete database DDL |
| `05_api_design.md` | RESTful + custom endpoints grouped by domain |
| `06_ui_spec.md` | Page inventory, component mapping, form specs |
| `07_business_logic.md` | Script categorization and logic translation |
| `08_auth_roles.md` | Role definitions and access control model |

## Deep Exploration (Optional)

For complex solutions (50+ scripts, heavy conditional formatting, many calculated fields), the skill includes specialized explorers that can be run between Phase 1 and Phase 2:

- **Script Explorer** — classifies every script by type, logic tier, and migration target
- **Conditional Formatting Explorer** — extracts business rules encoded in formatting formulas
- **Hide-Object-When Explorer** — uncovers authorization models and state machines hidden in visibility rules
- **Calculated Fields Explorer** — catalogs domain-specific calculations
- **Custom Functions Explorer** — documents the shared logic layer

## Output Structure

All generated files are written to a `migration/` directory in your working directory:

```
migration/
  00_app_summary.md
  01_discovery_answers.md
  02_recommendations.md
  03_migration_plan.md
  04_database_schema.sql
  05_api_design.md
  06_ui_spec.md
  07_business_logic.md
  08_auth_roles.md
```

Explorer outputs (if run) go into their own subdirectories:

```
migration/fm-scripts-explorer/
migration/fm-cf-explorer/
migration/fm-hide-explorer/
migration/fm-calc-explorer/
migration/fm-func-explorer/
```

## How to Generate a DDR Export

In FileMaker Pro:

1. Open your solution file
2. Go to **File > Save a Copy as XML**
3. Choose **Database Design Report** as the format
4. Save to a directory

For multi-file solutions, export each file's DDR into the same directory — the parser auto-detects and merges them.

## License

MIT
