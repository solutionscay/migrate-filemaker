# Script Explorer

Kinds: `scripts`. One CSV row per script file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md); read [../reference/script-translation-patterns.md](../reference/script-translation-patterns.md) for step meanings.

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind scripts --output "$OUT_DIR/explorers/scripts/catalog.json"
```

## Read

- Every numbered step. A `//` after the number marks a disabled step. Comment steps (`#`) are the developer's own notes; record what they say when it explains intent.
- The indented option lines under a step: called script ids, file references, find requests, sort keys, import maps, and the `refs:` of each calculation.
- The callers. Grep for `Script id=<id> name=` in the same file (script steps, buttons, triggers, menus, file options) and for the script name in other files that reference this one.

## Record

```text
source_id,source_hash,kind,file,id,name,type,owner,tier,purpose,reads,writes,calls,callers,external,open_question
```

- `type`: `navigation`, `find-query`, `data-change`, `validation`, `integration`, `print-export`, `orchestration`, `session-setup`, `security`, `utility`, `empty`.
- `owner`: `server-domain`, `server-query`, `client-ui`, `background-job`, `external-adapter`, `drop-candidate`, `unresolved`. Choose by effect, not by name or folder. A trigger script that writes durable data is `server-domain`.
- `tier`: `tier1` domain rule, `tier2` standard persistent data behavior, `tier3` presentation or navigation only.
- `purpose`: one or two sentences, in plain words, of what the script does.
- `reads`, `writes`: one `TO::field#id` per line. For a write, add the step number and the record scope (current record, found set from step N, new record).
- `calls`: one called script per line (`file/scripts/<id>` and the step number). Mark calls to other files with the data-source name.
- `callers`: one object file path per line, or `none found`.
- `external`: `Insert from URL`, `Send Mail`, export, import, ODBC, plugin or file-system steps, one per line, with the step number. Credentials are already redacted; do not restore them.

## Feeds

`07_business_logic.md` (script dispositions, domain operations), `05_api_design.md` (operations and integrations), `03_migration_plan.md` (increments).
