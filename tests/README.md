# Parser regression tests

```
python3 -m unittest discover -s tests -v      # or: python3 tests/test_parse_ddr.py
```

Stdlib only. `parse_ddr.py` has no dependencies and must keep none.

- `fixtures/mini_ddr.xml` — a hand-authored FMPReport, UTF-16 LE, ~370 lines.
- `test_parse_ddr.py` — runs the real parser over it and asserts the output exactly.

---

## Why this exists: `verify()` is not enough

`parse_ddr.py` reconciles its emitted counts against the raw XML on every run.
That check is worth keeping, and it is genuinely load-bearing — it catches a
dropped script, an empty catalog, a whole file that failed to open.

**It cannot catch the worst defect this parser ever shipped.**

`get_calculation` deleted every field reference from every calculation. It turned

```
Get ( AccountName ) ≠ Case_Notes::log_created_account
```

into

```
Get ( AccountName ) ≠
```

Same number of calculations in. Same number out. **Every count reconciles.** The
output is well-formed, parseable, and syntactically plausible — and it means
something entirely different. It destroyed 9,148 field references across 6,229
calculations in the gold DDR alone. Downstream, it produced a `drop`
recommendation on `Line_Items::Allocations` (the report itself called the field
"critical for restitution accounting" in the same row), and it inverted the
reading of the single largest authorization rule: a row-level author-ownership
check was documented as a hardcoded username.

The symptom was observed four separate times, by four separate artifacts, and
written off each time as `"stripped by DDR"` — an unfixable upstream export
limitation. It was never FileMaker's fault. It was one `join` on the wrong
attribute, and it survived for months because nothing compared a **value** to
ground truth.

A count check answers *"how many?"*. Corruption of this class needs *"what,
exactly?"*. That is the only question this suite asks.

### The deeper root cause

None of the eight defects came from sloppy coding. Every one traces to a line in
`reference/ddr-xml-reference.md` that described an XML shape FileMaker does not
emit. **The parser was written against the doc, not against the XML.** Five
sections have since been corrected against real output; the rest has never been
validated. So this fixture is not derived from the reference doc either — every
shape in it was lifted from real gold DDR output
(`ddr/implementations/phase1/rcda-gold-2026-05-21_1658/raw/`, FileMaker 22.0.6),
and that is a rule for anyone extending it. **If you add an element here, copy it
out of real XML. Do not copy it out of the reference doc, and do not invent it.**

---

## What each fixture element guards

| Fixture element | Guards | The bug it replays |
|---|---|---|
| `Field ID` → `AutoEnter/Calculation` with **direct text** | D1 | `<Calculation>` holds the formula as direct text. It has **no `<Text>` child** — 0 of 36,051 gold calcs had one, so the branch reading `Calculation/Text` was dead code and 100% of calcs took the lossy path. |
| `Field Restitution_Owed_Display` → **single FieldRef chunk** | D1 / audit §4.1 | Whole formula rendered to whitespace → `get_calculation` returned `None` → field looked **formula-less**. ~1,947 calcs vanished this way. Source of the 8 false `drop` recommendations. Verbatim shape of the real gold field. |
| `Object Button` → `HideCondition` with a `Table::field` operand | D1 / audit §4.2 | The exact `Get ( AccountName ) ≠` truncation, which occurred in 44 places and was documented as "hardcoded user-specific access (name stripped by DDR)". It is the opposite: hide unless *you wrote this note*. |
| `Object stale_banner` → `DisplayCalculation`, FieldRef chunk with nested `<Field table= name=/>` and empty `.text` | D1 | The chunk-walker fallback — where the operand deletion lived. Also guards the **whitespace rule**: a FieldRef chunk's own text/tail is pretty-printing, not formula (without the guard, 53% of recovered refs come back wrapped in indentation). |
| `PrivilegeSet Manager` → `View value="Limited"` + `Calculation` | D1 + D4 | Row-level security predicates need *both* fixes to come out intact. This is the authorization model. |
| `Script Open` at **ScriptCatalog root** | D2 | Descending only into `<Group>` dropped 1,860 of 17,870 scripts (10.41%) repo-wide — with their bodies. Root is exactly where FileMaker developers put startup, login, routing and case-closure logic. |
| `Script` inside `Group Modules/Grand Jury` | D2 | The group path must keep working. The one-line fix must not regress it. |
| `Script name="-"` at root **and** in a group | separators | Double-mishandled: dropped at root (with the real scripts), kept in groups (91 junk rows in gold's shipped list). Both must go. |
| `Layout name="-"` | separators | Layouts have always filtered these. Scripts now match. |
| `ConditionalFormatting` → `Item` / `op` / `Format` sibling / `Styles/LocalCSS` | D3 | **Four things wrong at once**: `Condition` is nested under `<Item>` (non-recursive `findall` → `[]` every time), the attribute is `op` not `type`, `Format` is Condition's *sibling*, and the payload is `LocalCSS` text not child tag names. Result: all 13 offices shipped a **2-byte** `09_conditional_formatting.json`; 34,318 rules never extracted. |
| `PrivilegeSet` → `Records value="Custom"` / `TableList/BaseTable` / `FieldAccess/FieldList/Field@accessRestriction` | D4 | The parser looked for `RecordAccessPrivileges` / `LayoutAccessPrivileges` / `ScriptAccessPrivileges` / `ExtendedPrivileges`. **None of those tags exist.** Every privilege set emitted as bare `{id, name}`, discarding 5,268 field-level entries and 18 row-level predicates in gold's Schema alone — so the RBAC design got built from hide formulas instead. |
| Two files' worth of access under one privilege-set name (via `access_by_file`) | D4 (8th defect) | `merge_security` deduped by name and kept the first occurrence. Files sort UI-first and the UI file carries only a coarse grant, so dedup discarded the recovered model. |
| `ButtonObj` with a nested `Step` | D6 | Only `GroupButtonObj` was handled. 1,617 Step-bearing `ButtonObj` ignored in gold; 24,018 across the swept offices. |
| `GroupButtonObj` whose `Step` is **one level deeper** | D6 | `el.find("Step")` sees direct children only. 1,140 of gold's 5,256 `GroupButtonObj` are containers. Together: 872 of 1,536 button actions lost (56.8%), and 112 layouts reported `buttons:[]` while genuinely having buttons. |
| `Step` with `StepText` | D7 | The structured params are an allow-list of ~10 child tags out of ~102 that occur, so **62% of emitted steps had no `params` key at all** — dialog text, find queries, sort orders and return values all gone. `StepText` is FileMaker's own faithful rendering and was never read, though the same parser already read it for buttons. |
| `Field name="===Keys==="` | D8 | Separator fields are inert and correctly skipped. |
| C0 control char + unparseable file (injected by the test, not in the fixture) | D5 | `except Exception: continue` swallowed a single malformed byte and dropped a whole DDR file — 90% of an office's scripts — with no warning and exit 0. |

Also asserted: `verify()` reconciles against the fixture, and `_count_catalog`
does not inflate the script count by counting `<Script>` **references** inside
steps and buttons (the fixture contains 3 such references; a naive `iter()`
would count them and report 5 instead of 2).

---

## Two things to know before you edit this

**1. One shape in the fixture is not observed in gold.** The `stale_banner`
hide condition has an empty `<Calculation />` next to a populated
`<DisplayCalculation>`. In real gold, **100% of `DisplayCalculation` parents also
carry `<Calculation>` direct text** (measured: every one, across both raw files),
which means the chunk-walker fallback is unreachable against this DDR version.
That fallback is still live code, it is still the forward-compatibility path for
a DDR version that shapes things differently, and it is precisely where the D1
operand deletion lived. It is exercised here deliberately. Everything *inside*
that element — the chunk types, the nested `<Field table= id= name=/>`, the
indentation — is verbatim gold. Only the empty `<Calculation />` sibling is
constructed.

**2. One assertion pins a defect on purpose.** `_MANAGER_ACCESS["layouts"]` has
no `items` key, and the test asserts that. This is **not** the parser being
right. The parser reads `Layouts/LayoutList/LayoutAccess`, but FileMaker emits:

```xml
<Layouts value="Custom" allowCreation="False">
  <LayoutList>
    <Layout id="1" name="Intakes">
      <LayoutAccess value="NoAccess"/>
      <DataAccess value="NoAccess"/>
    </Layout>
```

`LayoutAccess` is a **child of `Layout`** carrying `value=`, not a sibling
carrying `name=`. So `findall("LayoutList/LayoutAccess")` returns `[]` and every
per-layout grant is dropped — 236 of them in gold's `RCDA_Schema`. This is the
D4 fix's residual: the audit flagged the D4 patch as "written but not executed",
and this is the part that did not survive contact with the XML.

The fixture encodes the **real** shape. The assertion encodes **current
behavior**, so the defect is visible in the test rather than silent in the
output. When the parser is fixed, this assertion is *supposed* to fail — update
it to the recovered `items`, don't delete it.
