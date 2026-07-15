# FileMaker Schema Builder

Build a reversible target schema from source keys and relationship predicates. Do not invent `id` columns or foreign keys before the source key model is proven.

Read [../reference/schema-translation-guide.md](../reference/schema-translation-guide.md) and [../reference/filemaker-concepts.md](../reference/filemaker-concepts.md) first.

## Required inputs

- `$SPECS_DIR/_provenance.json` (must verify)
- `01_tables.json`
- `02_table_occurrences.json`
- `03_relationships.json`
- `05_scripts.json` for finds, sorts, writes, and found-set behavior
- `06_value_lists.json`
- raw validation/auto-enter metadata or a manual schema export when the parsed field record lacks it
- source data profiles for candidate-key uniqueness, nulls, duplicates, orphans, ranges, and encodings
- discovery decisions for timezone, containers, retention, and identifiers

Run provenance verification before analysis. If source data is unavailable, produce a schema decision register with unresolved keys; do not emit executable foreign keys on guesses.

## Step 1: Inventory observed tokens

Read JSON structurally and print the distinct values of:

- field `data_type` and `field_type`;
- relationship predicate `operator`;
- validation keys actually present;
- table-occurrence resolution status.

Fail on unknown enum values. The current parser contract uses:

- `data_type == "Binary"` for FileMaker container data;
- `data_type == "TimeStamp"` for timestamps;
- relationship operators such as `Equal`, `NotEqual`, `GreaterThan`, `LessThan`, and `CartesianProduct`.

Do not test `field_type == "Container"` or `operator == "="`; those literals do not describe the emitted JSON contract.

## Step 2: Build the table-occurrence map

Resolve every relationship side through `02_table_occurrences.json` using source-file context, occurrence id/name, `base_table`, `base_table_id`, and `resolved_source_file`.

For every predicate, retain:

```text
relationship_id,source_file,left_to,left_base,left_field,operator,right_to,right_base,right_field,predicate_position
```

Preserve all predicates in a compound relationship and preserve non-equality/cartesian semantics. Do not turn every relationship into a foreign key.

Stop executable DDL generation when a referenced occurrence/base table or field cannot be resolved. Record the unresolved edge and required evidence.

## Step 3: Classify keys from evidence

For each base table:

1. Inventory authored identifiers, auto-enter serial/UUID/calculation behavior, unique/not-empty settings, and relationship use.
2. Profile actual records for nulls and duplicates. A field named `ID`, a serial auto-enter option, or use in a relationship is not proof of uniqueness.
3. Identify composite candidate keys where relationships use multiple predicates.
4. Decide which source identifiers remain public/business keys.
5. Add a surrogate target key only when explicitly chosen. Record source-to-target mapping, backfill, uniqueness, cutover, and rollback behavior.
6. Never add a second `id` column that collides case-insensitively with an existing authored field.

A foreign key may reference only an evidenced primary/unique key with compatible types. When a FileMaker relationship expresses filtering rather than identity, model it as a query/domain rule instead.

## Step 4: Map fields without strengthening semantics silently

Record for every field:

```text
source_file,table_id,field_id,source_name,source_category,source_data_type,target_name,target_type,null_policy,default_policy,validation_policy,decision,evidence
```

- Preserve regular, calculated, summary, and global categories.
- Handle `Binary` fields through a documented object-storage/blob decision; do not silently replace bytes with a URL without a file-migration plan.
- Decide source timezone and DST ambiguity policy before converting `TimeStamp` values to timezone-aware instants.
- Treat FileMaker validation timing, validate-if-modified behavior, user override, and custom messages separately from database constraints.
- Add `NOT NULL`, `UNIQUE`, range, enum, or length constraints only after profiling and an explicit decision that the target should enforce stricter invariant semantics.
- Port calculated fields to generated columns only when the target database permits the expression and dependencies; otherwise choose query/application/trigger/materialized behavior explicitly.
- Analyze globals as per-session state by default; promote to shared configuration only when use and initialization prove that intent.
- Normalize repeating fields with an order-preserving child model only after determining every repetition's meaning and script/layout dependencies.

## Step 5: Design referential behavior

For each proven foreign key, record:

- source relationship and all predicates;
- target unique key evidence;
- nullability and orphan profile;
- FileMaker create/delete-related-record behavior;
- proposed `ON UPDATE`/`ON DELETE` action;
- migration ordering and rejected-row treatment.

Do not default to `CASCADE`. FileMaker graph relationships do not by themselves establish ownership or delete semantics.

## Step 6: Design indexes from workloads

Create indexes for proven constraints and measured access paths:

- primary/unique constraints;
- foreign-key checks and common joins;
- high-value finds, sorts, reports, and authorization predicates;
- partial/expression/full-text indexes when the target workload supports them.

Do not index every field named in a script. Record the query pattern and expected selectivity; validate with target query plans after data load.

## Decision gate before SQL

Present a table of all unresolved or product-changing decisions:

- source and target keys;
- compound/non-equality relationships;
- stricter constraints;
- calculated/summary fields;
- globals;
- containers;
- timestamp timezone/DST policy;
- repeating fields;
- delete/update behavior;
- naming collisions and reserved words.

Obtain user/stakeholder confirmation for product decisions. Resolve factual questions from source artifacts rather than asking users to guess.

## Generate and verify DDL

Use [../templates/04_database_schema.sql](../templates/04_database_schema.sql). Include a traceability comment for each table, key, relationship-derived constraint, and intentional deviation.

Verification must include:

1. Parse/apply the DDL in a disposable instance of the selected database.
2. Confirm every source field has a disposition and no target column name collides.
3. Confirm every relationship predicate has a disposition: foreign key, query rule, domain rule, cartesian UI relation, or unresolved.
4. Load representative profiled data and check constraint rejects explicitly.
5. Test timezone boundaries, containers, composite keys, orphans, and duplicate legacy identifiers.
6. Compare business totals and stable-value hashes, not only table/row counts.

Report unresolved items next to the DDL. A syntactically valid schema is not complete while key evidence or relationship resolution is missing.
