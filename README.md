# migrate-filemaker

An evidence-first coding-agent skill for recovering FileMaker behavior from Database Design Report XML and planning a verifiable rebuild.

It includes a standard-library Python parser, provenance and explorer-coverage gates, FileMaker semantic references, workflow guides, and migration artifact templates.

## Requirements

- A coding agent that supports project/personal skills
- Python 3
- The complete FileMaker DDR XML export set, including `Summary.xml` when available

Raw DDR XML can contain sensitive logic or credential literals. Keep it out of version control and do not paste secrets into generated documents.

## Install

Clone or vendor this directory into the skill location supported by your coding agent. Invoke it as `$migrate-filemaker` where supported, or ask the agent to load `SKILL.md` from this directory.

## Process

1. **Prove inputs**: run the parser regression suite, parse all DDR report files, and bind raw XML, parser, topology, and JSON specs with `_provenance.json`.
2. **Inventory and explore**: analyze every populated source catalog. Explorer state uses stable source identities and exact-set reconciliation, not array positions or directory existence.
3. **Discover decisions**: ask for business, identity, UI, data, integration, and operational context that the artifacts cannot establish.
4. **Design contracts**: produce evidence-linked schema, server/API, UI, business-logic, authorization, migration, and cutover artifacts.
5. **Audit completion**: trace high-risk conclusions back to raw XML/screenshots, run negative authorization tests, and validate migrated values beyond row counts.

The workflow does not guarantee that parsed layout JSON is a complete UI specification, that every FileMaker relationship is a foreign key, or that a generated document is correct because it is well formed. Missing semantics remain explicit blockers or product decisions.

## Configure paths

The skill does not assume `ddr/specs` or `migration/`. Set paths once for the repository:

```bash
SKILL_DIR="/path/to/migrate-filemaker"
RAW_DIR="/path/to/implementation/raw"
SPECS_DIR="/path/to/implementation/specs"
ANALYSIS_DIR="/path/to/implementation/analysis"
CORE_DIR="/path/to/canonical/core"
```

See `SKILL.md` for the complete process.

## Verify this package

```bash
python3 -m unittest discover -s tests
```

The suite is standard-library-only. It guards parser semantic fixtures, provenance invalidation, stable explorer identities, root-script coverage, exact-set classification checks, and high-risk guidance contracts.

## Resources

- `scripts/parse_ddr.py`: DDR parser with extraction self-check and credential-literal redaction
- `scripts/provenance.py`: raw/parser/spec/topology provenance create/verify gate
- `scripts/catalog_contract.py`: stable explorer source snapshots and exact-set coverage verifier
- `reference/`: FileMaker/XML/translation methodology
- `workflows/`: script, calculation, function, formatting, hide, schema, and UI workflows
- `templates/`: evidence-bounded migration artifacts

## License

MIT
