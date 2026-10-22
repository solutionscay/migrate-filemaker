# UI Evidence and Target Specification

## Evidence

| Source | Coverage | Missing |
|---|---|---|
| Layout object files (`objects/<file>/layouts/`) | objects, keys, bounds, labels, fields, value lists, tabs, popovers, portals, buttons, triggers, hide rules, conditional formats, tooltips | theme styling, how the screen looks |
| Layout explorer CSVs |  |  |
| Script explorer CSVs | what buttons and triggers do |  |
| Menu explorer CSVs | menu commands and overrides |  |
| Screenshots/recordings |  |  |
| Discovery/design decisions |  |  |

Overall readiness: <!-- inventory-only / behavior-ready / implementation-ready -->

Do not claim implementation-ready while a required screen lacks labels/hierarchy/controls/actions/triggers/authorization/states.

Give each target page a `UI-<nn>` id. Put the full layout inventory and per-object maps in `06_ui_spec_appendix.md`, generated from the layout catalog; this file keeps the main screens.

## Source screen inventory

| Layout file | TO → base table | Purpose | Fields/portals/buttons | Hide/CF rules | Screenshot | Readiness | Disposition |
|---|---|---|---|---|---|---|---|
| `objects/<file>/layouts/<id>-<name>.txt` |  |  |  |  |  |  | keep/merge/retire/unresolved |

## Object map

| Layout file | Object key | Type/bounds/panel | Label/control/value list | Action/trigger | Hide/CF rule | Target component |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Identify each object by its layout file and `key`.

Several layouts often show one record in different views (a detail screen per workflow stage). Map them to one target page with views, and list every source layout under it. Note navigation that a script builds from a computed layout name; the layout catalog cannot see it.

## Navigation and workflows

| User workflow | Entry/route | Steps and states | Server operations | Role/record/field access | Source trace | Acceptance evidence |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

A trigger may invoke a server-owned domain operation. Client visibility and route guards never replace operation/data authorization.

## Target page specifications

### <!-- Page / route -->

- Readiness: <!-- inventory-only / behavior-ready / implementation-ready / blocked -->
- Use case and users: <!-- -->
- Source layouts/objects/scripts: <!-- object files and object keys -->
- Data queries and authorized projection: <!-- -->
- Commands and persistent invariant owner: <!-- -->
- Hierarchy/layout/breakpoints: <!-- evidenced or explicit design decision -->
- States: loading / empty / populated / validation / forbidden / error / conflict / offline (if applicable)
- Keyboard/focus/labels/screen reader/contrast requirements: <!-- -->
- Destructive action confirmation/recovery: <!-- -->

#### Fields and controls

| Label | Data field | Control | Stored/display values | Required/validation owner | Read/write rule | Source evidence |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

#### Collections/portals

| Collection | Relationship/query | Columns/actions | Sort/filter/page | Create/delete rule | Empty/error behavior | Source evidence |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

#### Conditional presentation

| Object key/component | Condition | Effect (style or hide) | Server rule cross-reference | Evidence |
|---|---|---|---|---|
|  |  |  |  |  |

Keep each distinct `Format:` even when conditions match.

## Design system and responsive decisions

| Decision | Value | Source fact or product decision | Acceptance check |
|---|---|---|---|
| Typography/color/spacing |  |  |  |
| Breakpoints/input devices |  |  |  |
| Data-density/table behavior |  |  |  |
| Modal/tab/navigation behavior |  |  |  |
| Print/PDF behavior |  |  |  |
| Accessibility target |  |  |  |

## Missing evidence

| Layout/object | Missing evidence | Implementation risk | Required screenshot/decision | Owner/status |
|---|---|---|---|---|
|  |  |  |  |  |

## Verification

- [ ] Every in-scope layout file has a target disposition.
- [ ] Every in-scope target page has an evidence readiness level.
- [ ] Every hide rule, conditional format, trigger and button in the layout explorer has a target behavior.
- [ ] Server authorization negative tests exist for hidden/restricted operations and fields.
- [ ] Critical workflows were walked against the current app/screenshots/recordings, or this item is marked blocked with its D- id when none exist.
