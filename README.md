# migrate-filemaker

![migrate-filemaker: from a FileMaker DDR to a verified, documented rebuild plan](assets/banner.png)

A coding-agent skill for FileMaker rebuilds. It reads a FileMaker Database Design Report (DDR) as XML and produces a rebuild plan. Each conclusion in the plan links back to the XML.

## Requirements

- A coding agent that supports skills (Claude Code, Codex, or similar)
- Python 3, standard library only
- The full DDR XML export: one file per FileMaker file, plus `Summary.xml` when you have it

Raw DDR XML can contain credentials and client logic. Keep it out of version control.

## Install

Clone this directory into your agent's skills folder. Invoke it as `$migrate-filemaker`, or tell the agent to load `SKILL.md`.

## Process

1. Extract: write one text file per FileMaker object (script, table, layout, privilege set, menu and the rest), plus an index of all of them.
2. Explore: read every object file and classify it in one CSV row. A coverage check proves that each object is classified exactly once.
3. Discover: ask the owner what the XML cannot tell you: business rules, users, integrations, operations.
4. Design: write the schema, API, UI, business logic, authorization, data migration, and cutover plan.
5. Plan: write the migration plan, citing object files as evidence.

`SKILL.md` has the full process.

## Scripts

```bash
python3 scripts/explode_ddr.py RAW_DIR OBJECTS_DIR       # DDR XML -> one text file per object
python3 scripts/catalog_contract.py {snapshot,verify} ... # explorer coverage check
python3 scripts/parse_ddr.py RAW_DIR [SPECS_DIR]        # DDR XML -> JSON specs (not used by the steps)
python3 scripts/provenance.py {create,verify} ...       # bind raw XML, parser and specs
```

Both extractors handle multi-file solutions and redact credentials they find in the XML.

## Layout

- `scripts/`: extractors, provenance, and coverage tools
- `workflows/`: one guide per explorer: what to read, what to record
- `reference/`: DDR XML format, FileMaker concepts, translation patterns
- `templates/`: the migration documents the process fills in

## Tests

```bash
python3 -m unittest discover -s tests
```

## License

MIT
