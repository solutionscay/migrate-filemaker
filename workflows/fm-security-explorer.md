# Security Explorer

Kinds: `privilege-sets`, `accounts`, `extended-privileges`. One CSV row per object file. Follow [../reference/explorer-contract.md](../reference/explorer-contract.md).

```bash
python3 "$SKILL_DIR/scripts/catalog_contract.py" snapshot --objects "$OBJECTS" \
  --kind privilege-sets --kind accounts --kind extended-privileges \
  --output "$OUT_DIR/explorers/security/catalog.json"
```

## Read

- A privilege-set file: the `PrivilegeSet` line (menu access, export, print, manage accounts, override validation, idle disconnect), then `Records`, `Layouts`, `ValueLists` and `Scripts`. With `value=Custom`, each `BaseTable` lists `Create`, `View`, `Edit`, `Delete` (with a `Calculation` when access is limited to some records) and `FieldAccess` (with per-field restrictions).
- An account file: privilege set, status, `managedBy` (FileMaker or an external provider), password flags. The DDR has no password or hash.
- An extended-privilege file: the keyword (`fmapp`, `fmwebdirect`, `fmrest`, `fmxml`, `fmphp`, `fmodbc`, `fmextscriptaccess`, `fmurlscript`, or a custom one) and the privilege sets that hold it.
- Scripts that check access: `grep -rlE 'PrivilegeSetName|AccountName|AccountPrivilegeSetName|AccountExtendedPrivileges' "$OBJECTS"`.

## Record

Privilege sets:

```text
source_id,source_hash,kind,file,id,name,records,record_rules,field_rules,layouts,value_lists,scripts,flags,extended,target_role,open_question
```

- `records`: `all`, `custom`, `view-only`, `none`.
- `record_rules`: one line per table with custom access: `<table> | C/V/E/D | <meaning of each limiting calculation>`.
- `field_rules`: one line per restricted field: `<table>::<field> | view-only or none`.
- `layouts`, `value_lists`, `scripts`: `all`, `custom`, `view-only`, `none`; for `custom`, one line per item that differs from the default.
- `flags`: the `PrivilegeSet` line options that are on, one per line.
- `extended`: keywords this set holds.
- `target_role`: the proposed target role or capability, or `unresolved`.

Accounts:

```text
source_id,source_hash,kind,file,id,name,privilege_set,status,auth,category,target_identity,open_question
```

- `auth`: `filemaker`, `external-group`, `oauth`, `other`.
- `category`: `person`, `shared`, `service`, `guest`, `admin`.

Extended privileges:

```text
source_id,source_hash,kind,file,id,name,channel,privilege_sets,target,open_question
```

- `channel`: `desktop`, `web`, `rest-api`, `xml-api`, `php-api`, `odbc`, `script-access`, `url-script`, `custom`.
- `target`: `keep`, `replace`, `retire`, `unresolved`.

## Feeds

`08_auth_roles.md` (identity, roles, record and field policies, access channels), `05_api_design.md` (authorization matrix).
