-- FileMaker migration target schema
-- Generated only after workflows/fm-schema-builder.md gates pass.
--
-- Evidence:
--   source implementation(s): <ids>
--   provenance/spec hashes: <hashes>
--   source data profile: <artifact/hash>
--   target database/version: <database/version>
--   timezone/DST decision: <decision id>
--   unresolved blockers: <none or list>
--
-- This file must remain non-executable while a key target, relationship side,
-- validation change, or required source field is unresolved. Do not invent an
-- `id SERIAL PRIMARY KEY`, foreign key to `parent(id)`, or unconditional SQL
-- constraint merely to make the DDL complete.

BEGIN;

-- ---------------------------------------------------------------------------
-- Source-to-target mapping register
-- ---------------------------------------------------------------------------
-- Maintain the full register in the companion schema decision artifact.
-- Every target object below cites source file/table/field ids or an approved
-- product-decision id.
--
-- source_file | table_id | field_id | source_name | target_object | disposition
-- <...>

-- ---------------------------------------------------------------------------
-- Domains/reference values (only when value-list semantics and governance prove it)
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
--   Source: <source_file>, table id <id>, name <name>
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
-- Source relationship: <source_file>/<relationship_id>
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
-- companion query/domain-rule register; do not force them into FKs.

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Cite a constraint or measured query/authorization workload for each index.
-- CREATE INDEX <name> ON <table> (<columns>); -- evidence: <query/profile>

-- ---------------------------------------------------------------------------
-- Views/generated values/triggers
-- ---------------------------------------------------------------------------

-- Cite calculation identity, complete dependency analysis, target-platform
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
