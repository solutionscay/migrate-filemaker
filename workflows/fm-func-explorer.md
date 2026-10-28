# Custom-Function Explorer

Kinds: `custom-functions`. One CSV row per function file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md).

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind custom-functions --output "$OUT_DIR/explorers/functions/catalog.json"
```

## Read

- The `CustomFunction` line (parameters, `visible`) and the full calculation body, including commented-out parts.
- The `refs:` line: other custom functions (`cf:`), fields and context functions such as `fn:Get`.
- The callers: `grep -rl 'cf:<name>' "$OBJECTS/<file-dir>"`. A custom function belongs to its own file; a hit in another file is a same-named function there. Callers can be fields, scripts, layouts, menus or other functions. A `cf:` hit can be a parameter of the same name in another function (the DDR types it as a function); check the caller's parameter list before you count it.

## Record

```text
source_id,source_hash,kind,file,id,name,category,context,tier,parameters,calls,callers,meaning,target_signature,open_question
```

- `category`: `domain-rule`, `text`, `date-time`, `number`, `list`, `json-xml`, `encoding`, `ui`, `integration`, `utility`.
- `context`: `pure` (depends only on its parameters), `context-dependent` (reads fields, `Get()` values, globals or variables), `recursive`. One value: a function that calls itself is `recursive` even when it also reads context; say what context it reads in `meaning`.
- A function byte-identical to one in the other file keeps its own row; name the twin in `open_question` so the plan writes it once.
- Treat a value as secret only where that matters to the plan: the target must keep it out of code (an integration's login or signing key). A value that only looks like one (a JSON key, a status word, a field name) is ordinary logic. Write `secret` in `open_question` for a function that returns or holds such a value.
- `tier`: `tier1` only when the body or its callers show specific business behavior; else `tier2` or `tier3`.
- `calls`: custom functions it calls, one per line.
- `callers`: one object file path per line, or `none found`. An unused function keeps its row.
- `meaning`: what it returns, in plain words, including empty-input and coercion behavior the body shows.
- `target_signature`: a typed signature for the target language, or `unresolved`.

## Feeds

`07_business_logic.md` (calculations and custom functions).
