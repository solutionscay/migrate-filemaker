-- FileMaker migration target schema
-- Written from the table, graph and value-list explorer CSVs.
--
-- Evidence:
--   source implementation(s): <ids>
--   objects: <path to objects/index.tsv>
--   source data profile: <artifact/hash>
--   target database/version: <database/version>
--   timezone/DST decision: <decision id>
--   unresolved blockers: <none or list>
--
-- Tables, columns and keys the objects prove are executable. A constraint that
-- rests on an unresolved key, relationship side, validation change or source
-- field stays commented out, with the decision id it waits on. Do not invent an
-- `id SERIAL PRIMARY KEY`, foreign key to `parent(id)`, or unconditional SQL
-- constraint merely to make the DDL complete.
--
-- Multi-tenant default (when discovery keeps one): a `tenant_id` column on every
-- entity table, part of each unique constraint, cited to its D- id.

BEGIN;

-- ---------------------------------------------------------------------------
-- Source-to-target mapping register
-- ---------------------------------------------------------------------------
-- Keep the full register in `04_database_schema_appendix.md`: one row per base
-- table, field, relationship and value list, generated from the catalogs.
-- Every target object below cites its object file and field id, or an
-- approved product-decision id.
--
-- object file | field id | source_name | target_object | disposition
-- <...>

-- ---------------------------------------------------------------------------
-- Domains/reference values (only when value-list semantics and governance prove it)
-- Many small custom lists may share one `value_list_items (list, value, sort)`
-- table instead of one table or enum each. A multikey field (a return-separated
-- list of keys) becomes a join table.
-- ---------------------------------------------------------------------------

-- Example shape; replace/remove based on evidence:
-- CREATE TABLE <reference_table> (
--   <source_or_surrogate_key> <type> PRIMARY KEY,
--   <stored_value> TEXT NOT NULL,
--   <display_value> TEXT NOT NULL,
--   <sort_order> INTEGER NOT NULL,
--   <active> BOOLEAN NOT NULL DEFAULT TRUE,
--   CONSTRAINT <proved_uniqueness> UNIQUE (<columns>)
-- );

-- ---------------------------------------------------------------------------
-- Base tables
-- ---------------------------------------------------------------------------

-- For each table document:
--   Source: objects/<file>/tables/<id>-<name>.txt
--   Source key evidence/profile: <artifact/result>
--   Surrogate-key decision (if any): <decision id and reversible mapping>
--   Validation changes: <decision ids>
--   Calculated/global/repeating/container dispositions: <references>
--
-- CREATE TABLE <target_table> (
--   <preserved_source_key> <compatible_type> NOT NULL,
--   <ordinary_field> <type>,
--   <binary_object_key> TEXT, -- only with container manifest/storage design
--   <local_civil_timestamp> TIMESTAMP, -- or TIMESTAMPTZ per explicit policy
--   CONSTRAINT <pk_name> PRIMARY KEY (<proved_key_columns>),
--   CONSTRAINT <constraint_name> <approved/profiled target invariant>
-- );

-- ---------------------------------------------------------------------------
-- Relationship-derived constraints
-- ---------------------------------------------------------------------------

-- Add an FK only when the source TOs resolve, all source predicates are retained,
-- the referenced target columns have proven uniqueness, types are compatible,
-- and update/delete behavior is explicitly decided.
--
-- Source relationship: objects/<file>/relationships/<id>-<name>.txt
-- Predicates: <left TO/base/field> Equal <right TO/base/field> [AND ...]
-- Uniqueness/orphan evidence: <profile artifact>
-- Ownership/delete decision: <decision id>
-- ALTER TABLE <child>
--   ADD CONSTRAINT <fk_name>
--   FOREIGN KEY (<child_columns>)
--   REFERENCES <parent> (<proved_unique_columns>)
--   ON UPDATE <decision>
--   ON DELETE <decision>;
--
-- Record NotEqual/GreaterThan/LessThan/CartesianProduct relationships in the
-- appendix's relationship register (they become queries or 07 rules); do not
-- force them into FKs.

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Cite a constraint or measured query/authorization workload for each index.
-- CREATE INDEX <name> ON <table> (<columns>); -- evidence: <query/profile>

-- ---------------------------------------------------------------------------
-- Views/generated values/triggers
-- ---------------------------------------------------------------------------

-- Cite the table object file and field id, the full dependency list, target-platform
-- restrictions, and semantic fixtures. Generated columns are not allowed for
-- related/aggregate/context-dependent expressions unsupported by the target.

-- ---------------------------------------------------------------------------
-- Authorization (when database policies are selected)
-- ---------------------------------------------------------------------------

-- Policies supplement the complete authorization design. Include default-deny,
-- operation/row/field behavior, service roles, and negative tests. UI hide rules
-- are never the policy source of truth.

COMMIT;

-- Verification evidence required before promotion:
-- [ ] DDL applied in a disposable instance of the exact target version.
-- [ ] Every source field and relationship predicate has a disposition.
-- [ ] Candidate keys were profiled; duplicates/orphans are accounted for.
-- [ ] Constraint strengthening is approved and tested against source data.
-- [ ] Timezone/DST, decimal, encoding, container, and composite-key fixtures pass.
-- [ ] Business totals and stable-value hashes reconcile after a rehearsal load.
