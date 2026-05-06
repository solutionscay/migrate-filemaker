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

FileMaker DDR versions differ in how they store calculation/formula text. There are two patterns:

- **`<Calculation><Text>...</Text></Calculation>`** — present in some DDR versions, but may be **empty** in v19+ exports.
- **`<DisplayCalculation><Chunk>text</Chunk><Chunk>text</Chunk>...</DisplayCalculation>`** — reliable fallback. Concatenate all `<Chunk>` children's text to reconstruct the formula.

Always try `Calculation > Text` first, then fall back to `DisplayCalculation > Chunk`. This applies to: field calculations, auto-enter calculations, script step calculations, and custom functions.

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
Buttons live inside `<GroupButtonObj>` elements (not `<Object type="Button">`):
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

### Conditional Formatting

Layout objects can have conditional formatting rules that change visual appearance based on a formula:

```xml
<Object type="Field" name="budget_total" ...>
  <FieldObj ...>...</FieldObj>
  <ConditionalFormatting>
    <Condition type="Formula">
      <Calculation>
        <Text>Budget::total &gt; Budget::paid</Text>
      </Calculation>
      <Format>
        <FillColor value="#FF0000"/>
        <TextColor value="#FFFFFF"/>
      </Format>
    </Condition>
    <Condition type="Formula">
      <Calculation>
        <Text>Budget::total = Budget::paid</Text>
      </Calculation>
      <Format>
        <FillColor value="#00FF00"/>
      </Format>
    </Condition>
  </ConditionalFormatting>
</Object>
```

- Multiple `<Condition>` elements per object (evaluated in order, first match wins)
- `<Format>` children vary: `FillColor`, `TextColor`, `FontStyle` (Bold/Italic), etc.
- Formula text uses the same calculation syntax as field calculations and scripts
- Business logic is frequently embedded here: financial thresholds, status pipelines, urgency countdowns

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

Path: `File > ScriptCatalog > Group > Script` (groups can nest)

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
Contains: `RecordAccessPrivileges > TableAccess` (CRUD per table), `LayoutAccessPrivileges`, `ScriptAccessPrivileges`, `ExtendedPrivileges`

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
