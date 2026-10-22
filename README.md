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

1. Parse: convert the DDR XML into JSON specs, and record provenance so stale specs are caught.
2. Explore: classify every script, calculation, custom function, conditional format, and hide rule. A coverage check proves that each one is classified exactly once.
3. Discover: ask the owner what the XML cannot tell you: business rules, users, integrations, operations.
4. Design: write the schema, API, UI, business logic, authorization, data migration, and cutover plan.
5. Audit: check high-risk conclusions against the raw XML, test authorization, and compare migrated data values as well as row counts.

`SKILL.md` has the full process.

## Scripts

```bash
python3 scripts/parse_ddr.py RAW_DIR [SPECS_DIR]        # DDR XML -> JSON specs
python3 scripts/provenance.py {create,verify} ...       # bind raw XML, parser and specs
python3 scripts/catalog_contract.py {snapshot,verify} ... # explorer coverage check
```

The parser handles multi-file solutions. It resolves references between files through each external data source's path. It stops if two inputs have the same FileMaker file name. It redacts credentials it finds in the XML.

## Layout

- `scripts/`: parser, provenance, and coverage tools
- `workflows/`: step-by-step guides for each explorer, the schema, and the UI
- `reference/`: DDR XML format, FileMaker concepts, translation patterns
- `templates/`: the migration documents the process fills in

## Tests

```bash
python3 -m unittest discover -s tests
```

## License

MIT
