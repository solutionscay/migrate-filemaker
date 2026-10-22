# Custom-Menu Explorer

Kinds: `custom-menus`, `custom-menu-sets`. One CSV row per object file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md).

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot --objects "$OBJECTS" \
  --kind custom-menus --kind custom-menu-sets --output "$OUT_DIR/explorers/menus/catalog.json"
```

## Read

- A custom-menu file: `Options` (modes and platforms), the menu's `Install` condition, `BaseMenu`, then each `MenuItem` with its `Command`, its `Install` condition, any override action (a script or step) and its shortcut.
- A menu-set file: the menus it holds.
- Where a set is installed: the `file` options object (`DefaultCustomMenuSet`), layout files (`CustomMenuSet`), and `Install Menu Set` script steps.

## Record

Custom menus:

```text
source_id,source_hash,kind,file,id,name,install_when,items,removed,overrides,open_question
```

- `install_when`: the meaning of the menu's install condition, or `always`.
- `items`: the number of menu items.
- `removed`: standard commands this menu leaves out or installs only on a condition, one per line with the condition. A removed `Delete Record` is behavior the target must decide on. The DDR lists only the items a menu keeps, not the standard menu it replaces. Name a removed command only when the menu's `BaseMenu` is a standard menu whose items you can list (Records: New, Duplicate, Delete Record, Delete Found/All, Replace Field Contents); else write `unresolved` and ask.
- `overrides`: one line per item whose action is replaced: `<command> | <script id or step> | <what it does>`.

Menu sets:

```text
source_id,source_hash,kind,file,id,name,menus,installed_by,target,open_question
```

- `installed_by`: object file paths, one per line, or `none found`.
- `target`: `ui-actions`, `role-gated-actions`, `drop-candidate`, `unresolved`.

## Feeds

`06_ui_spec.md` (navigation and actions), `08_auth_roles.md` (actions removed for some users), `07_business_logic.md` (overridden commands that run scripts).
