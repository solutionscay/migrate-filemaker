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
- `TitleCalc`, `LabelCalc`, `PlaceholderText`, `AccTitle`: other display calculations. They have no column of their own: a `LabelCalc` is the label of its button or button-bar segment, a `TitleCalc` is the title of its popover. Web viewer calculations (`ExternalObj`) go in `buttons` only when they run a step; else in `open_question` if they matter.
- Ownership is by indentation only. A `HideCondition` can come after an object's nested children; it still belongs to the object at its indentation.
- `context`: the `Table` line names only the occurrence. Take the base table from `objects/<file>/table-occurrences/<id>-<TO>.txt`, and name its file when it is another file.
- Who opens the layout: `grep -rlE 'Layout id=<id> name=' "$OBJECTS/<file>"` (scripts, buttons, triggers). Only grep the layout's own file, or hits with the same id in the other file are false. Ignore hits in `privilege-sets/` (they list every layout) and in disabled (`//`) script steps. A script can also go to a layout by calculated name; "none found" is then not proof of a dead layout. Put "no reference found" in `open_question`, not in `target`.
- Trigger scripts: read the script's header comments and enough steps to say what it does in one phrase. Do not classify it; the script explorer does that. A trigger's parameter sits under its `Script` line.

Count what the row must cover before you write it (the `Item` count includes every `Item` line; subtract any that are not under `ConditionalFormatting`):

```bash
grep -oE '^\s*(HideCondition|Item|Trigger|ButtonObj|GroupButtonObj|PopoverButtonObj|ToolTip|PortalObj)\b' "$OBJECTS/<path>" \
  | sed 's/^ *//' | sort | uniq -c
```

## Record

```text
source_id,source_hash,kind,file,id,name,purpose,context,hide_rules,conditional_formats,triggers,buttons,tooltips,portals,value_lists,target,open_question
```

- `purpose`: `form`, `list`, `report-print`, `dialog`, `navigation`, `dashboard`, `utility`, `developer`. A home or splash screen is `navigation`; a raw field dump in a data file is `developer`. The DDR has no layout parts or view type, so `form` against `list` comes from the objects (a portal-free body of one record's fields is `form`).
- `context`: `<TO> (base <table>, <file>)`.
- `hide_rules`: one line per `HideCondition`: `key <n> <object> | hidden when <meaning>`.
- `conditional_formats`: one line per `Item`: `key <n> <object> | when <meaning> | <effect>`. `<effect>` is `style` (color, weight, size), `hide`, `disabled`, or `none` (the item has no `Format:` line). `hide` covers the hiding tricks: font size of 400pt or more, and text color with alpha 0. An icon color with alpha 0 is `hide` only when it is the whole format on a button with no text; next to other style changes, or on a text or field object, it is `style`. A format that greys out a button with text is `disabled`. White text is `hide` only when the object's fill is known to be white; the DDR often does not show the fill, so write `style (white text)` and ask. An empty condition never fires; write `when (empty condition)`.
- `triggers`: one line per `Trigger`: `key <n> or layout | <event> | <script id and name> | <what the script does>`, then `| param <meaning>` when the trigger passes a parameter. Name the object as the hide and format lines do. A trigger whose script is `id=0 ref=none` is `| no script`.
- `buttons`: one line per button object: `key <n> <label> | <step or script id> | <parameter meaning>`. Take `<label>` from the object's text, `LabelCalc`, tooltip or object name, in that order, else `(icon)`; for a `GroupButtonObj`, look at its child objects too. Any button (`ButtonObj` or `GroupButtonObj`) with no `Step` is `key <n> <label> | no step`. A `PopoverButtonObj` is `key <n> <label> | opens popover "<title>"` (`""` when its `TitleCalc` is empty).
- `tooltips`: one line per `ToolTip`: `key <n> | <text or meaning>`. Flatten line breaks to spaces.
- `portals`: one line per `PortalObj`: `key <n> | <TO> | sort | filter meaning or none`. A `FilterCalc enable=False` is `filter off (<meaning>)`.
- `value_lists`: the value lists the fields use, one per line.
- `target`: `page`, `merge`, `modal`, `report`, `print`, `script-context`, `drop-candidate`, `unresolved`. `script-context` is a layout that only scripts, imports, exports or the Data API use as context; no user sees it. `report` is an on-screen summary; `print` is a page layout for paper or PDF (letters and legal forms are `print`); `merge` is a layout that the target folds into another screen.

Repeated identical objects (record-slider segments, calendar day buttons, nav-header groups) may share one line: `keys <k1>,<k2>,... (×<count>) <label> | ...`, or `keys <a>..<b>` only when every key in the range belongs to the group. A part that differs per object is written as a placeholder (`GOTO <n>`). One object with many identical format `Item`s may share a line the same way. The `<count>` adds to the line count. When a name or label contains `|`, put it in double quotes.

The line count in each list column (with `×<count>` lines counted as `<count>`) must equal its count in the census. A hide rule or conditional format controls what the user sees. It does not grant access; `08_auth_roles.md` takes access from privilege sets.

## Feeds

`06_ui_spec.md` (screens, objects, conditional presentation), `07_business_logic.md` (presentation and workflow signals), `08_auth_roles.md` (UI visibility).
