# FileMaker DDR XML Structure Reference

This document describes the exact XML paths and structure of a FileMaker Pro Database Design Report (DDR) export. Use this when the parser script encounters an unfamiliar DDR version or when you need to manually inspect/extend the extraction.

## File Identification

A DDR export produces multiple XML files. Target the one with:
- Root element: `<FMPReport type="Report">`
- Encoding: UTF-16 LE (BOM bytes `FF FE`)
- It will be the largest XML file in the export

The Summary file (`type="Summary"`) is just an index. The `<FMSaveAsXML>` file is a raw structure dump — less organized, skip it.

## Top-Level Structure

```
<FMPReport type="Report" version="...">
  <File name="..." path="...">
    <BaseTableCatalog>
    <BaseDirectoryCatalog>
    <RelationshipGraph>
    <LayoutCatalog>
    <ValueListCatalog>
    <ScriptCatalog>
    <AccountCatalog>
    <PrivilegesCatalog>
    <ExtendedPrivilegeCatalog>
    <AuthFileCatalog>
    <CustomFunctionCatalog>
    <ExternalDataSourcesCatalog>
    <CustomMenuSetCatalog>
    <CustomMenuCatalog>
    <Options>
    <ThemeCatalog>
  </File>
</FMPReport>
```

## Critical Rule: Schema vs. Non-Schema Fields

FileMaker conflates stored data with runtime constructs. Always separate:

| FileMaker concept | `fieldType` attribute | `<Storage global="...">` | Output category |
|---|---|---|---|
| Normal field | `Normal` | `False` | `fields` (real schema) |
| Calculated field | `Calculated` | any | `calculated` |
| Summary field | `Summary` | any | `summary` |
| Global field | any | `True` | `globals` |

A table with only globals and no schema fields is NOT a real database table.

## Calculation Text Extraction

> **This section previously documented a shape that does not exist, and every
> tool written against it silently corrupted its output. Verified against
> FileMaker 22 DDR exports: 36,051 `<Calculation>` elements, 0 with a `<Text>`
> child.**

Two elements carry formula text, and they are **not** two interchangeable versions:

- **`<Calculation>`** holds the formula as **direct text**:
  ```xml
  <Calculation>not Investigation_boolean and not isAdmin_Private</Calculation>
  ```
  Read `calc.text`. Do **not** look for a `<Text>` child — measured 0/36,051.
- **`<DisplayCalculation>`** is a *chunked rendering* of the same formula, for display:
  ```xml
  <DisplayCalculation>
    <Chunk type="FunctionRef">Get</Chunk>
    <Chunk type="NoRef"> ( </Chunk>
    <Chunk type="FunctionRef">AccountName</Chunk>
    <Chunk type="NoRef"> ) ≠ </Chunk>
    <Chunk type="FieldRef"><Field table="Case_Notes" id="4" name="log_created_account"/></Chunk>
  </DisplayCalculation>
  ```

Chunk `type` determines where the payload lives:

| `type` | Payload | Notes |
|---|---|---|
| `NoRef` | `.text` | operators, punctuation, literals. Carries authored whitespace. |
| `FunctionRef` | `.text` | function names |
| `CustomFunctionRef` | `.text` | custom function names |
| `FieldRef` | **nested `<Field table= name=/>`** | **`.text` is empty** |

**The trap:** `"".join(c.text or "" for c in chunks)` looks correct and is
catastrophic. It deletes every field operand while keeping operators and string
literals, producing a syntactically plausible formula that is semantically
wrong — `Get ( AccountName ) ≠` instead of
`Get ( AccountName ) ≠ Case_Notes::log_created_account`. Nothing downstream can
detect this, because the output is still well-formed. Worse: when a formula is a
*single* FieldRef chunk it renders to the empty string, so the field appears to
have **no formula at all**.

**Extract `<Calculation>`'s direct text.** If you must walk chunks, resolve
`FieldRef` children to `table::name` rather than dropping them. Applies to: field
calculations, auto-enter calculations, script step calculations, custom
functions, conditional formatting, hide conditions, and privilege-set row-level
security predicates.

## Tables and Fields

Path: `File > BaseTableCatalog > BaseTable`

```xml
<BaseTable id="135" records="0" name="Contacts">
  <FieldCatalog>
    <Field id="12" dataType="Number" fieldType="Normal" name="_zkp_Contact_id">
      <Comment/>
      <AutoEnter allowEditing="True" value="CreationName" constant="False" ...>
        <Serial increment="1" nextValue="430" generate="OnCreation"/>
        <Calculation>
          <Text>...formula...</Text>
        </Calculation>
        <ConstantData/>
      </AutoEnter>
      <Validation message="False" ... type="OnlyDuringDataEntry">
        <NotEmpty value="False"/>
        <Unique value="False"/>
        <Existing value="False"/>
        <StrictValidation value="False"/>
      </Validation>
      <Storage index="All" indexLanguage="English" global="False" maxRepetition="1"/>
    </Field>
  </FieldCatalog>
</BaseTable>
```

### Field attributes
- `dataType`: Text, Number, Date, Time, Timestamp, Container
- `fieldType`: Normal, Calculated, Summary

### AutoEnter
- `value` attribute: CreationName, CreationDate, CreationTime, ModificationName, ModificationDate, ModificationTime
- `<Serial>`: auto-increment with `nextValue`, `increment`, `generate` (OnCreation/OnCommit)
- `<Calculation><Text>`: auto-enter calculation formula

### Storage
- `global="True"`: app-level variable, not per-record
- `index`: None, Minimal, All
- `maxRepetition`: repeating field count (>1 is FileMaker-specific)

### Separator fields
Fields named `===Something===` are visual grouping markers in FileMaker's field list. They are not real fields — skip them.

## Table Occurrences

Path: `File > RelationshipGraph > TableList > Table`

DDR versions vary in how they store the base table reference:

**Attribute form (v19+)** — base table info is on the `Table` element itself:
```xml
<Table id="1065097" color="#FF6666" baseTableId="135" baseTable="Contacts" name="Contacts_01"/>
```

**Child element form (older versions):**
```xml
<Table id="1065097" name="Contacts_01">
  <BaseTable id="135" name="Contacts"/>
</Table>
```

The parser checks the `baseTable` attribute first, then falls back to the child element. Multiple occurrences can reference the same base table. This is how FileMaker creates different "contexts" for the same data in the relationship graph.

### Cross-file table occurrences

In multi-file solutions, a table occurrence can reference a base table in a different `.fmp12` file. This is indicated by a `<FileReference>` child element:

```xml
<Table id="1065097" name="DataFile_Contacts" baseTable="Contacts" baseTableId="135">
  <FileReference id="2" name="DataFile"/>
</Table>
```

The `FileReference` `name` attribute is the symbolic name of the external file (as defined in the External Data Sources). The parser records this as `external_file_reference` and attempts to resolve it to a known parsed file via the EDS map.

## Relationships

Path: `File > RelationshipGraph > RelationshipList > Relationship`

```xml
<Relationship id="3">
  <LeftTable id="..." name="Contacts"/>
  <RightTable id="..." name="Sales"/>
  <JoinPredicateList>
    <JoinPredicate type="Equal">
      <LeftField>
        <Field id="..." name="_zkp_Contact_id"/>
      </LeftField>
      <RightField>
        <Field id="..." name="_zfk_Contact_id"/>
      </RightField>
    </JoinPredicate>
  </JoinPredicateList>
  <LeftOptions deleteRelated="False" createRelated="False">
    <SortList/>
  </LeftOptions>
  <RightOptions deleteRelated="False" createRelated="True">
    <SortList>
      <Sort type="Ascending">
        <Field name="..."/>
      </Sort>
    </SortList>
  </RightOptions>
</Relationship>
```

**Important**: Left/Right table names are **occurrence names**, not base table names. Resolve to base tables using the occurrence mapping.

## Layouts (Screens)

Path: `File > LayoutCatalog > Layout`

Layouts named `-` are visual separators — skip them.

### Field objects
```xml
<Object type="Field" key="..." ...>
  <FieldObj numOfReps="1" ...>
    <Name>TableOccurrence::FieldName</Name>
    <DDRInfo>
      <Field name="FieldName" id="..." table="TableOccurrence"/>
    </DDRInfo>
  </FieldObj>
</Object>
```

Prefer `DDRInfo > Field` (structured). Fall back to `Name` text (format: `Table::Field`).

### Portal objects
```xml
<Object type="Portal" ...>
  <PortalObj ...>
    <TableAliasKey>RelatedTableOccurrence</TableAliasKey>
    <FieldList>
      <Field table="..." id="..." name="..."/>
      <Field table="..." id="..." name="..."/>
    </FieldList>
  </PortalObj>
</Object>
```

### Button actions

Buttons come in **four** flavours. Handling only `GroupButtonObj` misses the
majority of real bindings — measured on one solution: 872 of 1,536 distinct
button actions lost (57%), and 112 layouts reporting no buttons while genuinely
having them.

| Element | Notes |
|---|---|
| `ButtonObj` | Plain button. **The most common carrier of real actions.** |
| `GroupButtonObj` | Often a *container*: its `<Step>` may be nested a level deeper, not a direct child. |
| `PopoverButtonObj` | Popover trigger; can hold several steps. |
| `ButtonBarObj` | Segmented bar; multiple steps. |

```xml
<Object type="GroupButton" ...>
  <GroupButtonObj numOfObjs="...">
    <Step enable="True" id="1" name="Perform Script">
      <StepText>Perform Script [ "ScriptName" ]</StepText>
      <Script id="..." name="ScriptName"/>
    </Step>
    ...child objects...
  </GroupButtonObj>
</Object>
```

Search **nested** `<Step>` elements (`el.iter("Step")`) across all four tags, not
just direct children. Dedup on `(action, script)` — keying on script name alone
collapses distinct scriptless buttons together.

### Conditional Formatting

Layout objects can have conditional formatting rules that change visual appearance based on a formula:

> **Corrected against real DDR output.** The shape below was previously
> documented without the `<Item>` wrapper, with `Format` inside `Condition`, and
> with a `type` attribute. All three are wrong, and `findall` is non-recursive —
> so a parser written to the old shape extracted **exactly zero rules from every
> file** while emitting a well-formed empty list.

```xml
<Object type="Field" name="budget_total" ...>
  <FieldObj ...>...</FieldObj>
  <ConditionalFormatting>
    <Item id="0" flags="5">
      <Condition op="0">
        <Calculation>Budget::total &gt; Budget::paid</Calculation>
        <DisplayCalculation>...</DisplayCalculation>
      </Condition>
      <Format>
        <Styles>
          <LocalCSS>background-color: rgba(100%,0%,0%,1); -fm-strikethrough: true;</LocalCSS>
        </Styles>
      </Format>
    </Item>
  </ConditionalFormatting>
</Object>
```

- Every `<Condition>` is wrapped in an **`<Item>`**. Iterate `ConditionalFormatting > Item > Condition`.
- The attribute is **`op`**, not `type`.
- **`<Format>` is a sibling of `<Condition>`**, both under `<Item>` — not a child of Condition.
- Formatting is **CSS** at `Format > Styles > LocalCSS`, not discrete `FillColor` / `TextColor` elements.
- `Item@flags` (observed `3`, `5`) encodes rule state.
- Formula lives in `<Calculation>` — see "Calculation Text Extraction".
- Business logic is frequently embedded here: financial thresholds, status pipelines, urgency countdowns.

### Hide Object When

Any layout object can have a visibility condition — a formula that hides the object when true:

```xml
<Object type="Field" name="price_column" ...>
  <FieldObj ...>...</FieldObj>
  <HideCondition>
    <Calculation>
      <Text>$$USER_privgroup ≠ "[Full Access]"</Text>
    </Calculation>
  </HideCondition>
</Object>
```

- Single formula per object (no multiple conditions)
- When formula evaluates to true (non-zero), the object is hidden
- Heavily used for: role-based access control, progressive disclosure, workflow state machines, platform detection
- Authorization logic is frequently implemented here rather than in privilege sets

**Migration importance:** These formulas often encode the application's entire authorization model and workflow state machines — business logic invisible in the data model and scripts.

### Object types reference
| Type | What it is | Extract? |
|---|---|---|
| `Field` | Data field on layout | Yes |
| `Portal` | Related records list | Yes |
| `GroupButton` | Button or button group (contains Step for actions) | Yes (Step only) |
| `TabControl` / `TabPanel` | Tab interface | Yes (panel names) |
| `Text` | Static label | Optional |
| `Graphic` | Image/icon | No |
| `Rect`, `Line`, `Oval` | Decorative shapes | No |

## Scripts

Path: `File > ScriptCatalog > {Group | Script}` — groups can nest, **and scripts
also appear at the root of `ScriptCatalog`, outside any group.**

> **Do not treat `Group` as a mandatory path segment.** Descending only into
> groups silently drops every ungrouped script. Measured across 13 real
> solutions: **1,860 of 17,870 script definitions (10.4%) lost** — and the
> ungrouped tier is exactly where developers put startup, login, routing and
> cross-cutting trigger logic (`Open`, `Set User Information at Login`,
> `Go To Layout By Account`, `Set is_Closed from ...`). The `LayoutCatalog`
> has the same dual shape; handle both identically.

```xml
<Group name="Sales" ...>
  <Script id="14" name="AddSaleProduct" ...>
    <StepList>
      <Step id="141" name="Set Variable" enable="True">
        <Name>$variable</Name>
        <Calculation>
          <Text>...expression...</Text>
        </Calculation>
      </Step>
      <Step id="1" name="Perform Script" enable="True">
        <Script id="..." name="OtherScript"/>
      </Step>
      <Step id="6" name="Go to Layout" enable="True">
        <Layout name="LayoutName"/>
      </Step>
    </StepList>
  </Script>
</Group>
```

### Key step elements
- `<Script name="...">`: called script (Perform Script step)
- `<Layout name="...">`: target layout (Go to Layout step)
- `<Field>` / `<FieldRef>`: target field (Set Field step)
- `<Calculation><Text>`: expression/formula
- `<Name>`: variable name (Set Variable step)
- `<CurrentScript value="Pause|Resume|Exit">`: flow control

### Cross-file script calls

Perform Script steps can call scripts in other files. This is indicated by a `<FileReference>` child element on the `<Step>`:

```xml
<Step id="1" name="Perform Script" enable="True">
  <Script id="14" name="ProcessRecord"/>
  <FileReference id="2" name="DataFile"/>
</Step>
```

The parser records the `FileReference` name as `external_file` in the step's `params`.

## Value Lists

Path: `File > ValueListCatalog > ValueList`

### Custom values
```xml
<ValueList id="5" name="PaymentTypes">
  <Source value="Custom"/>
  <CustomValues>
    <Text>Visa
MC
AMEX
Cash
Check</Text>
  </CustomValues>
</ValueList>
```

### Field-based values
```xml
<ValueList id="3" name="Sale_Products">
  <Source value="Field"/>
  <PrimaryField show="False" sort="False">
    <Field table="Products" id="7" name="_zkp_Product_id"/>
  </PrimaryField>
  <SecondaryField show="True" sort="True">
    <Field table="Products" id="25" name="Product"/>
  </SecondaryField>
  <ShowRelated value="False"/>
</ValueList>
```

When `ShowRelated value="True"`, the list filters to records related through a specific table occurrence.

## Security

### Accounts
Path: `File > AccountCatalog > Account`
Attributes: `name`, `status` (Active/Inactive), `privilegeSet`, `emptyPassword`

### Privilege Sets
Path: `File > PrivilegesCatalog > PrivilegeSet`

> **Corrected.** The four element names previously documented here —
> `RecordAccessPrivileges`, `LayoutAccessPrivileges`, `ScriptAccessPrivileges`,
> `ExtendedPrivileges` — **do not exist in FileMaker DDR output.** A parser
> written to them emits every privilege set as bare `{id, name}` and drops the
> authorization model entirely: 5,240 field-level rules and 18 row-level
> security predicates lost in a single solution, with no error.

Real children: **`Records`**, **`Layouts`**, **`Scripts`**, **`ValueLists`**.

```xml
<PrivilegeSet id="5" name="Manager" menu="All" printing="True" exporting="True"
              idleDisconnect="True" manageAccounts="False" allowModifyPassword="True"
              overrideValidationWarning="True" comment="">
  <Records value="Custom">
    <TableList>
      <BaseTable id="129" name="Intakes" comment="">
        <Create value="True"/>
        <Delete value="False"/>
        <View value="Limited">
          <Calculation>not Investigation_boolean and not isAdmin_Private</Calculation>
          <DisplayCalculation>...</DisplayCalculation>
        </View>
        <Edit value="Limited">...</Edit>
        <FieldAccess value="Limited">
          <FieldList>
            <Field id="1" name="ID" accessRestriction="Modifiable"/>
          </FieldList>
        </FieldAccess>
      </BaseTable>
    </TableList>
  </Records>
  <Layouts value="Modifiable" allowCreation="True">
    <LayoutList><LayoutAccess name="..." value="..."><DataAccess value="..."/></LayoutAccess></LayoutList>
  </Layouts>
  <Scripts value="ExecutableOnly" allowCreation="False"/>
  <ValueLists value="Modifiable" allowCreation="True"/>
</PrivilegeSet>
```

Key points:

- `Records@value` is a coarse grant (`ViewOnly`, `CreateEdit`, `CreateEditDelete`,
  `Custom`). Only **`Custom`** carries a `TableList`.
- **`value="Limited"` on View/Edit/Create/Delete means a `<Calculation>` child holds a
  row-level security predicate.** This *is* the authorization model — extract it.
- `FieldAccess > FieldList > Field@accessRestriction` gives field-level rules.
- **Multi-file solutions:** privilege-set *names* are synced across files, but their
  *contents* are not. The UI file typically holds a coarse grant while the data file
  holds the `Custom` model. Deduping by name and keeping the first occurrence
  discards the real rules — files usually sort UI-first. Merge per-file, or prefer
  the definition that enumerates tables.

## Custom Functions

Path: `File > CustomFunctionCatalog > CustomFunction`
Attributes: `name`, `parameters` (semicolon-separated)
Contains calculation via `<Calculation><Text>` or `<DisplayCalculation><Chunk>` (see "Calculation Text Extraction" above).

## External Data Sources

Path: `File > ExternalDataSourcesCatalog`

This catalog lists references to other files or databases that the current FM file can access. It is the key to understanding multi-file solution topology.

### FileReference entries (other FileMaker files)

```xml
<ExternalDataSourcesCatalog>
  <FileReference id="2" name="DataFile">
    <PathList>
      <Path>file:DataFile</Path>
      <Path>file:/Volumes/Server/DataFile.fmp12</Path>
    </PathList>
  </FileReference>
</ExternalDataSourcesCatalog>
```

- `name`: The symbolic name used elsewhere in the DDR (in table occurrences and script steps) to reference this file
- `id`: Internal FM identifier
- `PathList > Path`: Ordered list of file paths FM tries when opening the reference. May include `file:`, `fmnet:/`, or absolute paths.

### OdbcDataSource entries (external non-FM databases)

```xml
<ExternalDataSourcesCatalog>
  <OdbcDataSource id="5" name="ProductionDB" DSN="ProductionDSN"/>
</ExternalDataSourcesCatalog>
```

ODBC sources indicate the FM solution connects to an external SQL database. These are recorded in the topology for manual investigation during migration.

### Cross-file resolution

The parser uses External Data Source names to resolve cross-file references:
1. Table occurrences with `<FileReference>` child → `external_file_reference` field
2. Perform Script steps with `<FileReference>` child → `external_file` param
3. The merger maps symbolic names to actual parsed files via name matching

## FileMaker Naming Conventions (informational)

Common prefixes used by FileMaker developers:
- `_zkp_` — primary key
- `_zkf_` / `_zfk_` — foreign key
- `_zhc_` — housekeeping/audit fields
- `_zg_` — global field
- `_c_` — calculation
- `_s_` — summary
- `===Name===` — visual separator (not a real field)

These are conventions, not enforced by FileMaker. The target system should use its own naming standards.
