# UI Evidence and Target Specification

## Evidence boundary

| Source | Hash/reference | Coverage | Missing |
|---|---|---|---|
| `04_layouts.json` |  | layout/field/portal/button inventory | bounds, static labels, tabs, triggers, control bindings, stable object ids |
| Raw layout XML/object map |  |  |  |
| Screenshots/recordings |  |  |  |
| Script Explorer |  | actions/effects |  |
| Hide/CF explorers |  | visibility/style | unattributed count |
| Discovery/design decisions |  |  |  |

Overall readiness: <!-- inventory-only / behavior-ready / implementation-ready -->

Do not claim implementation-ready while a required screen lacks labels/hierarchy/controls/actions/triggers/authorization/states or has unresolved unattributed rules.

## Source screen inventory

| Source file/layout id/name | TO → base table | Purpose/view | Fields/portals/buttons | Raw/screenshot evidence | Hide/CF attribution | Readiness | Disposition |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  | keep/merge/retire/unresolved |

## Stable object map

| Source file/layout id | Object key/status | Type/container path/bounds | Label/control/value list | Action/trigger | Hide/CF ids | Target component | Evidence |
|---|---|---|---|---|---|---|---|
|  | stable / derived / unattributed |  |  |  |  |  |  |

Never join rules to controls by array order. Keep unnamed/unattributed rules in the unresolved table.

## Navigation and workflows

| User workflow | Entry/route | Steps and states | Server operations | Role/record/field access | Source trace | Acceptance evidence |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

A trigger may invoke a server-owned domain operation. Client visibility and route guards never replace operation/data authorization.

## Target page specifications

### <!-- Page / route -->

- Readiness: <!-- inventory-only / behavior-ready / implementation-ready / blocked -->
- Use case and users: <!-- -->
- Source layouts/objects/scripts: <!-- stable ids -->
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

| Object/component | Condition | Visual payload/visibility | Server rule cross-reference | Attribution/evidence |
|---|---|---|---|---|
|  |  |  |  |  |

Preserve distinct `format_css` variants even when formulas match.

## Design system and responsive decisions

| Decision | Value | Source fact or product decision | Acceptance check |
|---|---|---|---|
| Typography/color/spacing |  |  |  |
| Breakpoints/input devices |  |  |  |
| Data-density/table behavior |  |  |  |
| Modal/tab/navigation behavior |  |  |  |
| Print/PDF behavior |  |  |  |
| Accessibility target |  |  |  |

## Unattributed and missing evidence

| Layout/rule/object | Missing evidence | Implementation risk | Required raw/screenshot/manual action | Owner/status |
|---|---|---|---|---|
|  |  |  |  |  |

## Verification

- [ ] Parsed layout counts reconcile to provenance/topology.
- [ ] Critical raw object types/bounds/labels/tabs/triggers/value-list bindings were measured.
- [ ] Every in-scope source layout has a target disposition.
- [ ] Every in-scope target page has an evidence readiness level.
- [ ] Unattributed hide/CF rules are unresolved rather than guessed.
- [ ] Server authorization negative tests exist for hidden/restricted operations and fields.
- [ ] Critical workflows were walked against the current app/screenshots/recordings.
