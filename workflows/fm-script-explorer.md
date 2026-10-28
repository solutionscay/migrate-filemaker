# Script Explorer

Kinds: `scripts`. One CSV row per script file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md); read [../reference/script-translation-patterns.md](../reference/script-translation-patterns.md) for step meanings.

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind scripts --output "$OUT_DIR/explorers/scripts/catalog.json"
```

## Read

- Every numbered step. A `//` after the number marks a disabled step. Comment steps (`#`) are the developer's own notes; record what they say when it explains intent.
- The indented option lines under a step: called script ids, file references, find requests, sort keys, import maps, and the `refs:` of each calculation.
- The callers. Grep for `Script id=<id> name=` in the same file (script steps, buttons, triggers, menus, file options). A call from the other file carries `in=<file>`; grep that file for `Script id=<id> name=.* in=<this file slug>`. A plain `Script id=<id>` grep across both files gives false hits. A call through a data source whose path the DDR cannot resolve (a `$$variable` path) prints `ref=external` and no `in=`; find it by the quoted script name on `Script id=... ref=external` lines and check the data source on the lines above it. These lines are also in `objects/unresolved.tsv`.
- Callers the DDR cannot show: the Scripts menu (`includeInMenu=True` in the header), FileMaker Server schedules (not in the DDR), `Perform Script` by calculated name, script names stored as data or passed as text (robot or queue tables, `Create Triggered Actions ( ... "script name" ... )`), plugin callbacks (for example MBS `Twain.SetNotificationScript`), web viewer `FileMaker.PerformScript`, and `Install OnTimer Script` targets. Grep the quoted script name to find the text-based ones; drop hits on `Script id=` lines, which are structured calls (already found above, or to another script of the same name). A caller found by name is `<path> (by name, step N)`; a caller only in steps that never run is `<path> (dead code)`. When none is found, write `none found` and add the reason that may apply: `none found (in Scripts menu)`, `none found (name suggests server schedule)`, `none found (may be called by name)`.
- Plugin calls hide inside calculations: `MBS (`, other plugin prefixes, and `<Function Missing>` (a plugin function the DDR could not resolve because the plugin was not installed when the DDR was made).
- Script ids repeat across files (script 123 can exist in both). Key any helper by file and id.
- Steps after an unconditional `Exit Script` or `Halt Script` never run; steps after a `Halt Script` inside an `If` run only when the condition is false. Record them in `open_question`, not in `writes` or `calls`.

## Record

```text
source_id,source_hash,kind,file,id,name,type,owner,tier,purpose,reads,writes,calls,callers,external,open_question
```

- `type`: `navigation`, `find-query`, `data-change`, `validation`, `integration`, `print-export`, `orchestration`, `session-setup`, `security`, `utility`, `empty`.
- `owner`: `server-domain`, `server-query`, `client-ui`, `background-job`, `external-adapter`, `drop-candidate`, `unresolved`. Choose by effect, not by name or folder. A trigger script that writes durable data is `server-domain`. Report and print scripts are `server-query`. Use `drop-candidate` only for a script with no effect the target needs (developer tests, one-time legacy imports, comment-only README scripts, and vendored module code that no live script calls); say the effect owner it would have in `purpose`. Vendored code that live scripts call (for example fmLog from a sync job) keeps its effect owner.
- `tier`: `tier1` domain rule, `tier2` standard persistent data behavior, `tier3` presentation or navigation only. A find that encodes a business definition (what counts as pending, which cases a report omits) is `tier1`. Developer, test and dead scripts are `tier3`.
- `purpose`: one or two sentences, in plain words, of what the script does.
- `reads`, `writes`: one `TO::field#id` per line. For a write, add the step number and the record scope: `current record`, `found set from step N`, `new record`, `related via <TO>` (a write through a relationship; it can create the related record), `portal row`, `other window`, or `by name` (`Set Field By Name`, `GetField`, `Evaluate`: the target is computed at run time; quote the expression). Scopes also include `found set on entry` (a loop over the records found before the script started) and `record found in step N`. A global field write is `global` (one value per session, no record). Record deletes go in `writes` as `delete: <TO> (<Delete Record|Delete All Records|Delete Portal Row> step N, <scope>)`. `Show Custom Dialog` input fields and `Insert Calculated Result` into the active field are writes. A `Set Field` on a non-global field in find mode is a find criterion: put it under `reads` as `TO::field#id (find criterion step N)`. Find requests, sort keys and import match keys carry field ids in their option lines; use them when the step has `Restore state=True`. With `Restore state=False` FileMaker does not use the saved ones (see LEGEND); do not list them. Summarize an export or import map over 20 fields as `<count> fields (step N)`. Fields inside `ExecuteSQL` text have no `refs:`; list them as `TO::field (ExecuteSQL step N)`.
- `calls`: one called script per line (`file/scripts/<id>` and the step number). Mark calls to other files with the data-source name.
- `callers`: one object file path per line, or `none found`.
- `external`: `Insert from URL`, `Send Mail`, export, import, `Save Records as PDF`, `Perform Script on Server`, ODBC, `ExecuteSQL`, `Open URL`, web viewer (`Set Web Viewer`, `Perform JavaScript in Web Viewer`), plugin calls (`MBS (`, `<Function Missing>`) or file-system steps, one per line, with the step number. Ignore matches inside `/* */` or `//` comments in a calculation. Disabled steps are not listed.
- Treat a value as secret only where that matters to the plan: the target must keep it out of code (an integration's login or signing key). A value that only looks like one (a JSON key, a status word, a field name) is ordinary logic. Write `secret` in `open_question` for a step that sets or sends such a value, with the step number.

Write `none` in a list cell that has nothing in it.

## Feeds

`07_business_logic.md` (script dispositions, domain operations), `05_api_design.md` (operations and integrations), `03_migration_plan.md` (increments).
