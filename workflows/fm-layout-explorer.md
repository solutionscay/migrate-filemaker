# Layout Explorer

Kinds: `layouts`. One CSV row per layout file. The row covers every object's hide rule, conditional format, trigger, button, tooltip and portal filter. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md).

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot \
  --objects "$OBJECTS" --kind layouts --output "$OUT_DIR/explorers/layouts/catalog.json"
```

## Read

The file is the layout's object tree. The `Layout` line gives width and options; `Table` gives the table occurrence it shows. Each `Object` line has a `type`, a `key` (the object's stable id on this layout) and `bounds` (top,left,bottom,right). Children are indented under it:

- `Text:` static label text. `FieldObj` with `Name: TO::field`, `ValueList:` and display type.
- `HideCondition` with its calculation: when the object is hidden.
- `ConditionalFormatting` with one `Item` per rule: `Condition` calculation and `Format:` CSS. A `font-size: 500pt` (or larger) format is how FileMaker developers hide an object.
- `ScriptTriggers` with one `Trigger event=` per trigger and the script it runs. Layout-level triggers sit directly under `Layout`.
- `ButtonObj`, `GroupButtonObj`, `PopoverButtonObj` with the `Step` they run (`StepText:`, script id, parameter calculation).
- `ToolTip` with its calculation.
- `PortalObj` with its table occurrence, sort, row count and `FilterCalc`.
- `TabControlObj`/`TabPanelObj`, `SlideControlObj`/`SlidePanelObj`, `PopoverObj`: panel membership is the indentation.
- `TitleCalc`, `LabelCalc`, `PlaceholderText`, `AccTitle`: other display calculations.

Count what the row must cover before you write it:

```bash
grep -oE '^\s*(HideCondition|Item|Trigger|ButtonObj|GroupButtonObj|PopoverButtonObj|ToolTip|PortalObj)\b' "$OBJECTS/<path>" \
  | sed 's/^ *//' | sort | uniq -c
```

## Record

```text
source_id,source_hash,kind,file,id,name,purpose,context,hide_rules,conditional_formats,triggers,buttons,tooltips,portals,value_lists,target,open_question
```

- `purpose`: `form`, `list`, `report-print`, `dialog`, `navigation`, `dashboard`, `utility`, `developer`.
- `context`: the table occurrence and its base table.
- `hide_rules`: one line per `HideCondition`: `key <n> <object> | hidden when <meaning>`.
- `conditional_formats`: one line per `Item`: `key <n> <object> | when <meaning> | <effect>`. `<effect>` is `style` (color, weight, size) or `hide` (500pt text and similar).
- `triggers`: one line per `Trigger`: `key <n> or layout | <event> | <script id and name> | <what the script does>`.
- `buttons`: one line per button object: `key <n> <label> | <step or script id> | <parameter meaning>`.
- `tooltips`: one line per `ToolTip`: `key <n> | <text or meaning>`.
- `portals`: one line per `PortalObj`: `key <n> | <TO> | sort | filter meaning or none`.
- `value_lists`: the value lists the fields use, one per line.
- `target`: `page`, `merge`, `modal`, `report`, `print`, `drop-candidate`, `unresolved`.

The line count in each list column must equal its count in the census. A hide rule or conditional format controls what the user sees. It does not grant access; `08_auth_roles.md` takes access from privilege sets.

## Feeds

`06_ui_spec.md` (screens, objects, conditional presentation), `07_business_logic.md` (presentation and workflow signals), `08_auth_roles.md` (UI visibility).
