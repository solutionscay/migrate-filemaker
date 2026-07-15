# FileMaker UI Evidence and Specification Workflow

The current `04_layouts.json` supports a layout inventory, not an implementation-complete screen specification. Produce only the level of detail supported by raw layout evidence, screenshots, and stakeholder confirmation.

## Inputs

- verified `04_layouts.json`;
- `05_scripts.json` and Script Explorer reports;
- `06_value_lists.json`;
- Conditional Formatting and Hide-Object Explorer reports with attribution status;
- raw DDR layout XML for object identity, bounds, controls, tabs, triggers, labels, and style data;
- current screenshots or recordings for visual hierarchy and interaction behavior;
- discovery decisions for target devices, accessibility, and workflows.

If raw XML/screenshots are unavailable, use [../templates/06_ui_spec.md](../templates/06_ui_spec.md) in `inventory-only` mode and list missing evidence. Do not fill absent properties with conventional guesses.

## Step 1: Record the extraction boundary

Before describing screens, inventory which properties are present in parsed JSON and which require another source. Check rather than assume:

| Property | Parsed JSON | Required fallback |
|---|---|---|
| Layout id/name/table occurrence/width | Usually present | Raw XML for confirmation |
| Field/portal/button inventories | Partial | Raw XML and screenshot |
| Object bounds/order | Not in current contract | Raw XML |
| Static labels/text | Not in current contract | Raw XML/screenshot |
| Input control and value-list binding | Not in current contract | Raw XML |
| Tab/panel membership | Not in current contract | Raw XML/screenshot |
| Layout/object triggers | Not in current contract | Raw XML/script trace |
| Stable object key for hide/CF attribution | Not in current contract | Raw XML extraction |
| Responsive intent/accessibility | Not represented by DDR | Product decision/testing |

State observed counts and `not measured` where no census was run.

## Step 2: Build a stable raw object inventory

For every implementation-critical layout, extract or manually record:

```text
source_file,layout_id,layout_name,object_key,object_type,parent/container_path,bounds,label,field_or_portal,control_type,value_list,button_action,trigger,hide_rule_ids,cf_rule_ids
```

Use raw XML ids/object keys when emitted. If no stable key exists, combine source file, layout id, object type, bounds, and container path, then label the identity `derived` and verify it against a screenshot. Never join hide/CF rules to an object by array position.

Record unnamed/unattributed hide and CF rules separately until this mapping is proven.

## Step 3: Inventory screens and workflows

For each layout:

- distinguish operational screens from print/report/utility layouts;
- resolve the layout's table occurrence to a base table;
- trace buttons and triggers to scripts and classify the invoked effects;
- record found-set/list/detail/portal behavior;
- record current labels, controls, value lists, tabs, dialogs, and validation feedback from raw/screenshot evidence;
- record role/state visibility as UI behavior and cross-reference server authorization requirements;
- record unresolved objects and missing screenshots.

A trigger that changes durable state invokes a server-owned operation; do not specify it as client-only logic.

## Step 4: Design the target experience

Separate source behavior from target product decisions. For each target page or flow, specify:

- route and use case;
- authorized operations and data fields;
- data loading, pagination, filtering, and sort behavior;
- forms, exact validation owner, value sources, error and empty states;
- persistent business operations called by UI events;
- component visibility as defense in depth;
- responsive behavior for named breakpoints/devices;
- keyboard, focus, labels, contrast, screen-reader, and destructive-action requirements;
- source layout/object/script traceability.

Do not promise pixel equivalence unless screenshots/bounds/styles were captured and the user requested it.

## Step 5: Completeness gate

For every target screen, use one status:

- `implementation-ready`: labels, geometry/hierarchy, controls, actions, triggers, data, authorization, and states are evidenced or explicitly decided;
- `behavior-ready`: workflow and operations are specified but visual/layout details remain a design task;
- `inventory-only`: parsed catalogs identify the layout and objects but cannot support implementation;
- `blocked`: a critical behavior or security rule is unresolved.

An overall UI spec may be called implementation-ready only when every in-scope screen is implementation-ready and all unattributed hide/CF rules have a disposition.

## Verification

- Compare object totals and types to raw XML per source file/layout.
- Walk every critical workflow against the current app or a recording.
- Test all roles and negative authorization paths through the server, not only hidden controls.
- Verify value-list bindings, tab membership, trigger actions, print behavior, and destructive confirmations.
- Record screenshot/raw XML references without copying sensitive data.
