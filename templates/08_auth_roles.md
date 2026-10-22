# Identity and Authorization Contract

## Authority and evidence

| Source | Count | Authority/use | Gaps |
|---|---|---|---|
| `accounts`, `privilege-sets` object files |  | Primary identity/authorization catalog | Password hashes absent |
| Record/field/layout privileges in privilege-set files |  | Primary enforcement evidence |  |
| Script/value-list privileges in privilege-set files |  | Operation/lookup evidence |  |
| `extended-privileges` object files |  | Access-channel evidence |  |
| Layout explorer (hide and format rules) |  | Secondary UI/exception evidence |  |
| Menu explorer (removed or gated commands) |  | Secondary UI evidence |  |
| Discovery/IdP policy |  | Target product decision |  |

Never use hide-object formulas as a replacement for the privilege catalog. Never infer an ownership column/predicate from a role name; cite the exact source predicate and target schema field.

## Identity provisioning

| Source account/category | Status/auth type | Target identity/IdP mapping | Invite/reset/cutover | Role assignment owner | Audit/exception |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

The DDR contains no password or hash. Define reset/invite or IdP mapping, disabled-account preservation, duplicate identity handling, service principals, break-glass accounts, MFA, and deprovisioning. Do not promise password migration.

## Roles and capabilities

| Source privilege set/rule | Target role/capability | Permission boundary | Explicit denies | Source evidence | Approval owner |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Default deny. A target role may combine/decompose source privilege sets only as an explicit, reviewed decision.

## Entity operation matrix

| Entity/domain | Role/capability | Create | View/query | Edit | Delete | Bulk/export/admin | Enforcement owner |
|---|---|---|---|---|---|---|---|
|  |  | deny/allow/conditional |  |  |  |  |  |

## Record-level policies

| Policy id | Entity/operation | Exact source predicate | Target predicate and fields | Null/edge semantics | Enforcement owner | Tests |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Verify every referenced target column exists and represents the same concept. Record ownership/source-account mappings explicitly; do not substitute an `assigned_to`-style field without evidence.

## Field-level policies

| Entity/field | Role/capability | Read | Create/write | Update | Redaction/omission behavior | Source restriction | Tests |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

Apply restrictions before serialization and mutation, not only in forms.

## Operation, script, and value-list access

| Target operation/lookup | Source script/value-list evidence | Allowed capabilities | Record/field dependency | Deny behavior | Tests |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Route/layout and access-channel matrix

| Route/page/channel | Source layout/extended privilege | Allowed capabilities | Underlying operations/data rules | Direct-access test |
|---|---|---|---|---|
|  |  |  |  |  |

Route guards and hidden navigation supplement the underlying operation/row/field policies. Take extended privileges from the `extended-privileges` object files.

## UI visibility and exceptions

| Layout file | Object key | Condition | Related server policy | Target UI behavior | Unresolved risk |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

An absent/hidden control does not authorize or deny the operation by itself.

## Session and global state

| FM global/`$$` value | Observed initialization/read/write | Target scope | Trusted for authorization? | Server recomputation/validation |
|---|---|---|---|---|
|  |  | per-session/per-request/durable preference/config | no unless independently proven |  |

Hosted FileMaker globals default to per-client/session scope. Client/session claims must not become authoritative without server validation.

## Service principals and integrations

| Principal/integration | Direction | Allowed operations/data | Credential owner/rotation | Network/access channel | Audit/tests |
|---|---|---|---|---|---|
|  |  |  | managed secret reference |  |  |

## Negative authorization tests

| Test id | Identity/role | Attempt | Expected denial/filter/redaction | Layer exercised | Evidence |
|---|---|---|---|---|---|
|  |  | forbidden create/read/update/delete/field/operation/channel |  |  |  |

Include direct API/server calls that bypass the UI, cross-record ownership attempts, restricted-field projection/mutation, disabled accounts, role changes, service principals, bulk/export, and access-channel tests.

## Open decisions and unavailable evidence

| ID | Missing/conflicting evidence | Security impact | Required proof/owner | Status |
|---|---|---|---|---|
|  |  |  |  |  |

## Completion gate

- [ ] Every privilege-set dimension maps to target enforcement.
- [ ] Every extended privilege has a target access channel or a retirement decision.
- [ ] Every entity operation defaults deny and has conditional rules where needed.
- [ ] Every field restriction is enforced before read/write serialization.
- [ ] Every record predicate references real target columns with equivalent meaning.
- [ ] Hide/CF rules are secondary UI evidence only.
- [ ] Identity provisioning covers resets/IdP, disabled users, and service principals.
- [ ] Negative tests pass through non-UI entry points.
- [ ] No credential literal appears in this document.
