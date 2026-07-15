"""
FileMaker DDR XML Parser
Extracts all components from one or more FileMaker Database Design Report (FMPReport XML)
files into clean JSON specs.

Usage:
    python parse_ddr.py <path_to_ddr_report.xml_or_directory> [output_dir]

    If output_dir is omitted, specs are written to a "specs" folder
    next to the input file (or directory).

    The input can be:
    - A single FMPReport type="Report" XML file (UTF-16 LE encoded)
    - A directory containing one or more Report XMLs (multi-file DDR)

    Multi-file solutions (e.g., UI file + data file) are auto-detected.
    All files are parsed and merged into unified specs with source_file
    annotations and cross-file reference resolution.
"""

import xml.etree.ElementTree as ET
import json
import os
import re
import sys


# FileMaker occasionally emits raw C0 control characters inside <Data> elements.
# They are invalid in XML 1.0 and expat rejects the whole file.
_C0_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


# ─── SECRET REDACTION ────────────────────────────────────────────────────────
#
# WHY THIS EXISTS. FileMaker solutions routinely hardcode credentials into script
# steps: SMTP passwords, S3 access keys, third-party API keys, and the passwords
# used by Create Account / Change Password steps. They are in the DDR because they
# are in the solution.
#
# The asymmetry that makes this the parser's problem: projects gitignore the raw
# DDR XML (it is huge, and it is full of this) but COMMIT the parsed specs. So the
# parser is the boundary between "secret stays on the analyst's disk" and "secret
# is in git history forever".
#
# This mattered silently for a while: the parser's own bugs were acting as an
# accidental redactor. Calculations came out with their operands deleted and
# StepText was never read, so most literals never reached the JSON. Fixing those
# bugs removed the accident. Hence a deliberate redactor.
#
# Deliberately conservative. It only fires on a quoted literal that FOLLOWS a
# credential-ish keyword, so it cannot touch:
#   - field references (Table::field) or variables ($x, $$y) -- they are unquoted
#   - a quoted string that merely CONTAINS such a word (Status = "Token")
# "secret" excludes "secretary" -- Secretary_global is a real field name in this
# domain and matching it was a false positive that badly inflated a first estimate.
_SECRET_KEYWORD = r"(?:password|passwd|pwd|api[ _]?key|access[ _]?key|secret(?!ary)|token|credential)"
_SECRET_RE = re.compile(
    r'(' + _SECRET_KEYWORD + r'[^"\n]{0,40}")([^"]{4,})(")',
    re.I,
)

REDACTION_PLACEHOLDER = "<REDACTED>"
_redaction_count = 0


_QUOTED_RE = re.compile(r'"([^"]{4,})"')
_SECRET_NAME_RE = re.compile(_SECRET_KEYWORD, re.I)


def redact_secrets(text):
    """Mask hardcoded credential literals, preserving the surrounding structure.

    Structure is kept deliberately: an analyst still needs to see THAT a step sets
    an SMTP password, and where, in order to plan the migration. They just do not
    need the value in git.
    """
    global _redaction_count
    if not text or '"' not in text:
        return text

    def sub(m):
        global _redaction_count
        _redaction_count += 1
        return m.group(1) + REDACTION_PLACEHOLDER + m.group(3)

    return _SECRET_RE.sub(sub, text)


def redact_all_literals(text):
    """Mask EVERY quoted literal in `text`.

    For when the surrounding context has already established that the payload is a
    secret, so the value carries no give-away keyword of its own -- e.g.
        Set Variable [ $password ; Value: "hunter2" ]
    where the <Value> element is just "hunter2". Keyword-adjacency cannot see that;
    the variable NAME is the only signal.
    """
    global _redaction_count
    if not text or '"' not in text:
        return text

    def sub(m):
        global _redaction_count
        _redaction_count += 1
        return f'"{REDACTION_PLACEHOLDER}"'

    return _QUOTED_RE.sub(sub, text)


def looks_like_secret_target(*names):
    """True if any of these variable/field names names a credential."""
    return any(n and _SECRET_NAME_RE.search(str(n)) for n in names)


def parse_xml(path):
    """Parse a DDR XML file, tolerating FileMaker's invalid control characters.

    Observed in the wild: 8 raw 0x1E (RECORD SEPARATOR) bytes inside a <Data>
    string. ET.parse raises "not well-formed (invalid token)" and, if the caller
    swallows it, the entire file vanishes from the extraction with no warning.
    """
    with open(path, encoding="utf-16") as fh:
        src = fh.read()
    cleaned, n = _C0_RE.subn("", src)
    if n:
        print(f"  WARNING: stripped {n} invalid control char(s) from {os.path.basename(path)}",
              file=sys.stderr)
    # Some exports carry a stray newline before the XML declaration, which expat
    # rejects with "XML or text declaration not at start of entity". Same class
    # of FileMaker malformation as the control chars above -- tolerate it, so the
    # warning channel stays meaningful rather than crying wolf on every run.
    cleaned = cleaned.lstrip("﻿ \t\r\n")
    return ET.ElementTree(ET.fromstring(cleaned))


# ─── HELPERS (module-level, take explicit params) ────────────────────────────

def get_calculation(parent):
    """Extract calculation text from a parent element.

    Verified against real DDR output (FileMaker 22, 36,051 <Calculation> elements):

    - <Calculation> holds the formula as DIRECT TEXT. It has no <Text> child --
      0 of 36,051 did. Any code looking for Calculation/Text is dead code.
    - <DisplayCalculation> is a chunked *rendering* of the same formula:
        <Chunk type="NoRef">        operators/punctuation, payload in .text
        <Chunk type="FunctionRef">  function names,        payload in .text
        <Chunk type="FieldRef">     payload is a NESTED <Field table= name=/>,
                                    and .text is EMPTY.
      So joining only .text silently deletes every field operand, leaving a
      syntactically plausible formula with its operands missing
      ("Get ( AccountName ) <>" instead of
       "Get ( AccountName ) <> Case_Notes::log_created_account").

    Prefer <Calculation>'s direct text; fall back to a chunk walker that
    resolves FieldRef children instead of dropping them.
    """
    calc = parent.find("Calculation")
    if calc is not None and calc.text and calc.text.strip():
        return calc.text.strip()

    dc = parent.find("DisplayCalculation")
    if dc is None:
        return None

    parts = []
    for chunk in dc.findall("Chunk"):
        is_fieldref = chunk.get("type") == "FieldRef"
        # NoRef chunks carry authored whitespace that is part of the formula.
        # A FieldRef's own whitespace is just pretty-printing around the child.
        if chunk.text and (chunk.text.strip() or not is_fieldref):
            parts.append(chunk.text)
        for child in chunk:
            if child.tag == "Field":
                table, name = child.get("table"), child.get("name")
                parts.append(f"{table}::{name}" if table else (name or ""))
            elif child.text:
                # Forward-compat: degrade rather than delete on unknown chunk shapes.
                parts.append(child.text)
            if child.tail and (child.tail.strip() or not is_fieldref):
                parts.append(child.tail)

    text = "".join(parts).strip()
    return text or None


def parse_field(field_el):
    f = {
        "id": field_el.get("id"),
        "name": field_el.get("name"),
        "data_type": field_el.get("dataType"),
        "field_type": field_el.get("fieldType"),
    }

    comment = field_el.find("Comment")
    if comment is not None and comment.text:
        f["comment"] = comment.text.strip()

    # Auto-enter
    ae = field_el.find("AutoEnter")
    if ae is not None:
        auto = {}
        if ae.get("value"):
            auto["value"] = ae.get("value")
        serial = ae.find("Serial")
        if serial is not None:
            auto["serial"] = {
                "next": serial.get("nextValue"),
                "increment": serial.get("increment"),
                "generate": serial.get("generate"),
            }
        ae_calc = get_calculation(ae)
        if ae_calc:
            auto["calculation"] = ae_calc
        if auto:
            f["auto_enter"] = auto

    # Field-level calculation (for Calculated / Summary fields)
    field_calc = get_calculation(field_el)
    if field_calc:
        f["calculation"] = field_calc

    # Validation
    val = field_el.find("Validation")
    if val is not None:
        rules = {}
        ne = val.find("NotEmpty")
        if ne is not None and ne.get("value") == "True":
            rules["not_empty"] = True
        uq = val.find("Unique")
        if uq is not None and uq.get("value") == "True":
            rules["unique"] = True
        if rules:
            f["validation"] = rules

    # Storage
    stor = field_el.find("Storage")
    if stor is not None:
        if stor.get("global") == "True":
            f["global"] = True
        if stor.get("index") and stor.get("index") != "None":
            f["index"] = stor.get("index")
        rep = stor.get("maxRepetition")
        if rep and rep != "1":
            f["repetitions"] = int(rep)

    return f


def extract_field_from_obj(obj):
    """Extract field reference from a layout Field object via DDRInfo or Name."""
    fo = obj.find("FieldObj")
    if fo is None:
        return None

    # Prefer DDRInfo (structured)
    ddr = fo.find("DDRInfo")
    if ddr is not None:
        field = ddr.find("Field")
        if field is not None:
            return {
                "table": field.get("table", ""),
                "field": field.get("name", ""),
            }

    # Fallback: Name element contains "Table::Field"
    name_el = fo.find("Name")
    if name_el is not None and name_el.text and "::" in name_el.text:
        parts = name_el.text.split("::", 1)
        return {"table": parts[0], "field": parts[1]}

    return None


def parse_script_steps(step_list):
    """Parse script steps into readable pseudocode."""
    steps = []
    if step_list is None:
        return steps

    for step in step_list.findall("Step"):
        s = {
            "id": step.get("id"),
            "name": step.get("name", ""),
            "enable": step.get("enable", "True"),
        }

        # StepText is FileMaker's own fully-rendered form of the step, e.g.
        #   Set Field [ INTAKES::is_Closed; 1 ]
        # The structured params below are an allow-list of ~10 child tags out of
        # ~102 that actually occur, so 62% of steps otherwise emit no params at
        # all -- losing dialog text, find queries, sort orders and return values.
        # Keep the faithful rendering alongside whatever we can structure.
        step_text = step.findtext("StepText")
        if step_text and step_text.strip():
            s["step_text"] = redact_secrets(step_text.strip())

        # Collect relevant parameters
        params = {}

        # Script reference (Perform Script)
        sr = step.find("Script")
        if sr is not None:
            params["script"] = sr.get("name", "")

        # FileReference in Perform Script steps (cross-file call)
        fr_ref = step.find("FileReference")
        if fr_ref is not None:
            params["external_file"] = fr_ref.get("name", "")

        # Layout reference
        lr = step.find("Layout")
        if lr is not None:
            params["layout"] = lr.get("name", "")

        # Field reference
        fr = step.find("Field")
        if fr is not None:
            table = fr.find("Table")
            field = fr.find("Field") if fr.find("Field") is not None else fr
            fname = field.get("name", "") if field is not None else ""
            tname = table.get("name", "") if table is not None else ""
            if fname:
                params["field"] = f"{tname}::{fname}" if tname else fname

        # Calculation
        step_calc = get_calculation(step)
        if step_calc:
            params["calculation"] = redact_secrets(step_calc)

        # Name (for variables etc.)
        name_el = step.find("Name")
        if name_el is not None and name_el.text:
            params["variable"] = name_el.text.strip()

        # Value/string
        val = step.find("Value")
        if val is not None:
            text = val.find("Text")
            if text is not None and text.text:
                params["value"] = redact_secrets(text.text.strip())

        # Boolean conditions
        for tag in ["Select", "Restore", "NoInteract"]:
            el = step.find(tag)
            if el is not None and el.get("state") == "True":
                params[tag.lower()] = True

        # A credential-ish TARGET means the payload is the secret even though the
        # payload itself carries no keyword:
        #     Set Variable [ $password ; Value: "hunter2" ]
        # Here <Value> is just "hunter2" -- keyword-adjacency cannot see it, and
        # the variable name is the only signal. Same for Set Field into a
        # Users::Password column.
        if looks_like_secret_target(params.get("variable"), params.get("field")):
            for key in ("value", "calculation"):
                if params.get(key):
                    params[key] = redact_all_literals(params[key])
            if s.get("step_text"):
                s["step_text"] = redact_all_literals(s["step_text"])

        if params:
            s["params"] = params

        steps.append(s)

    return steps


# ─── DDR DISCOVERY ───────────────────────────────────────────────────────────

def find_ddr_reports(path):
    """Given a file or directory, find all FMPReport type='Report' XMLs."""
    if os.path.isfile(path):
        return [path]

    if os.path.isdir(path):
        reports = []
        for f in os.listdir(path):
            if not f.lower().endswith(".xml"):
                continue
            full = os.path.join(path, f)
            try:
                tree = parse_xml(full)
                root = tree.getroot()
                if root.tag == "FMPReport" and root.get("type") == "Report":
                    reports.append(full)
            except Exception as exc:
                # NEVER swallow this silently. A single malformed byte used to
                # drop an entire DDR file (and 90% of an office's scripts) with
                # no warning and exit 0.
                print(f"  WARNING: could not parse {f}: {exc}", file=sys.stderr)
                continue

        if reports:
            return sorted(reports)

        # Fallback: return the largest XML if no Report found
        candidates = []
        for f in os.listdir(path):
            if f.lower().endswith(".xml"):
                full = os.path.join(path, f)
                candidates.append((os.path.getsize(full), full))
        candidates.sort(reverse=True)
        if candidates:
            return [candidates[0][1]]

    print(f"Error: Could not find any DDR Report XML in '{path}'")
    sys.exit(1)


# ─── WRITE HELPER ────────────────────────────────────────────────────────────

def write_json(output_dir, name, data):
    path = os.path.join(output_dir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  wrote {path} ({len(json.dumps(data))} chars)")


# ─── DDRFile CLASS ───────────────────────────────────────────────────────────

class DDRFile:
    """Encapsulates parsing of a single FMPReport XML file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)

        tree = parse_xml(filepath)
        root = tree.getroot()
        self.file_el = root.find("File")
        self.source_file = self.file_el.get("name", self.filename)

        # Parsed results
        self.tables = []
        self.table_occurrences = []
        self.relationships = []
        self.layouts = []
        self.scripts = []
        self.value_lists = []
        self.accounts = []
        self.privileges = []
        self.custom_functions = []
        self.external_data_sources = []
        self.conditional_formatting = []
        self.hide_conditions = []

    def parse_all(self):
        """Parse all catalogs from this file."""
        print(f"\nParsing file: {self.source_file} ({self.filepath})")
        self.tables = self._parse_tables()
        self.table_occurrences = self._parse_table_occurrences()
        self.relationships = self._parse_relationships()
        self.layouts = self._parse_layouts()
        self._extract_ui_logic()
        self.scripts = self._parse_scripts()
        self.value_lists = self._parse_value_lists()
        self.accounts, self.privileges = self._parse_accounts()
        self.custom_functions = self._parse_custom_functions()
        self.external_data_sources = self._parse_external_data_sources()
        self.verify()
        return self

    # ─── SELF-CHECK ─────────────────────────────────────────────────────

    def _count_catalog(self, catalog_tag, item_tag, skip_separators=False):
        """Count definitions in a catalog, descending only through Groups.

        Deliberately NOT ElementTree.iter(): a <Script> element also appears
        inside script steps and button definitions as a *reference*. Counting
        those would inflate the total ~6x and make this check useless.
        """
        catalog = self.file_el.find(catalog_tag)
        if catalog is None:
            return 0

        def walk(el):
            n = 0
            for child in el:
                if child.tag == item_tag:
                    if skip_separators and (child.get("name") or "").strip() == "-":
                        continue
                    n += 1
                elif child.tag == "Group":
                    n += walk(child)
            return n

        return walk(catalog)

    def _count_path(self, path):
        return len(self.file_el.findall(path)) if self.file_el is not None else 0

    def verify(self):
        """Reconcile emitted counts against the raw XML and warn on mismatch.

        Every silent-loss bug this parser has shipped produced *well-formed*
        output -- an empty list, a truncated formula, a plausible count -- so
        nothing downstream could detect it, and the losses were repeatedly
        misattributed to FileMaker's exporter instead. A structural traversal
        mistake is invisible without a ground-truth count to compare against.
        That is what this is for. Keep it honest: compare to the RAW XML, never
        to another parsed artifact.
        """
        checks = [
            ("tables", len(self.tables), self._count_catalog("BaseTableCatalog", "BaseTable")),
            ("table occurrences", len(self.table_occurrences),
             self._count_path("RelationshipGraph/TableList/Table")),
            ("relationships", len(self.relationships),
             self._count_path("RelationshipGraph/RelationshipList/Relationship")),
            ("layouts", len(self.layouts),
             self._count_catalog("LayoutCatalog", "Layout", skip_separators=True)),
            ("scripts", len(self.scripts),
             self._count_catalog("ScriptCatalog", "Script", skip_separators=True)),
            ("value lists", len(self.value_lists), self._count_path("ValueListCatalog/ValueList")),
            ("accounts", len(self.accounts), self._count_path("AccountCatalog/Account")),
            ("privilege sets", len(self.privileges),
             self._count_path("PrivilegesCatalog/PrivilegeSet")),
            ("custom functions", len(self.custom_functions),
             self._count_path("CustomFunctionCatalog/CustomFunction")),
        ]

        problems = [(what, got, raw) for what, got, raw in checks if got != raw]
        for what, got, raw in problems:
            print(f"  WARNING: {what}: emitted {got}, raw XML defines {raw} "
                  f"({raw - got:+d})", file=sys.stderr)

        # A catalog that exists in the XML but yields nothing is the exact
        # signature of a wrong tag name or a non-recursive findall.
        for what, count, present in (
            ("conditional formatting", len(self.conditional_formatting),
             self._count_path(".//ConditionalFormatting")),
            ("hide conditions", len(self.hide_conditions), self._count_path(".//HideCondition")),
        ):
            if present and not count:
                print(f"  WARNING: {what}: extracted 0 rules but the XML contains "
                      f"{present} blocks -- likely a wrong element name or a "
                      f"non-recursive lookup", file=sys.stderr)

        if not problems:
            print("  self-check: emitted counts reconcile with raw XML")
        return problems

    def _extract_ui_logic(self):
        """Extract conditional formatting and hide-object-when from parsed layouts."""
        for layout in self.layouts:
            layout_name = layout.get("name", "")
            for cf in layout.get("conditional_formatting", []):
                entry = dict(cf)
                entry["layout"] = layout_name
                self._inject_source(entry)
                self.conditional_formatting.append(entry)
            for hc in layout.get("hide_conditions", []):
                entry = dict(hc)
                entry["layout"] = layout_name
                self._inject_source(entry)
                self.hide_conditions.append(entry)

    def _inject_source(self, item):
        """Add source_file to a parsed item."""
        item["source_file"] = self.source_file
        return item

    # ─── TABLES & FIELDS ────────────────────────────────────────────────

    def _parse_tables(self):
        print("  Parsing tables & fields...")
        tables = []
        catalog = self.file_el.find("BaseTableCatalog")
        if catalog is None:
            return tables

        for bt in catalog.findall("BaseTable"):
            table = {
                "id": bt.get("id"),
                "name": bt.get("name"),
                "records": int(bt.get("records", 0)),
                "fields": [],
                "calculated": [],
                "summary": [],
                "globals": [],
            }
            fc = bt.find("FieldCatalog")
            if fc is not None:
                for field in fc.findall("Field"):
                    name = field.get("name", "")
                    if name.startswith("===") and name.endswith("==="):
                        continue

                    parsed = parse_field(field)
                    field_type = parsed.get("field_type", "")
                    is_global = parsed.get("global", False)

                    if is_global:
                        table["globals"].append(parsed)
                    elif field_type == "Summary":
                        table["summary"].append(parsed)
                    elif field_type == "Calculated":
                        table["calculated"].append(parsed)
                    else:
                        table["fields"].append(parsed)

            self._inject_source(table)
            tables.append(table)
        return tables

    # ─── TABLE OCCURRENCES ──────────────────────────────────────────────

    def _parse_table_occurrences(self):
        print("  Parsing table occurrences...")
        graph = self.file_el.find("RelationshipGraph")
        if graph is None:
            return []

        tl = graph.find("TableList")
        if tl is None:
            return []

        occurrences = []
        for to in tl.findall("Table"):
            occ = {
                "id": to.get("id"),
                "name": to.get("name"),
                "base_table": to.get("baseTable"),
                "base_table_id": to.get("baseTableId"),
            }
            # Fallback: some DDR versions use a child element
            if occ["base_table"] is None:
                bt = to.find("BaseTable")
                if bt is not None:
                    occ["base_table"] = bt.get("name")
                    occ["base_table_id"] = bt.get("id")

            # Check for external file reference (cross-file TO)
            file_ref = to.find("FileReference")
            if file_ref is not None:
                occ["external_file_reference"] = {
                    "name": file_ref.get("name", ""),
                    "id": file_ref.get("id", ""),
                }

            self._inject_source(occ)
            occurrences.append(occ)
        return occurrences

    # ─── RELATIONSHIPS ──────────────────────────────────────────────────

    def _parse_relationships(self):
        print("  Parsing relationships...")
        graph = self.file_el.find("RelationshipGraph")
        if graph is None:
            return []

        rl = graph.find("RelationshipList")
        if rl is None:
            return []

        relationships = []
        for rel in rl.findall("Relationship"):
            r = {"id": rel.get("id")}

            lt = rel.find("LeftTable")
            if lt is not None:
                r["left_table"] = lt.get("name")

            rt = rel.find("RightTable")
            if rt is not None:
                r["right_table"] = rt.get("name")

            jp = rel.find("JoinPredicateList")
            if jp is not None:
                predicates = []
                for pred in jp.findall("JoinPredicate"):
                    p = {"operator": pred.get("type", "equal")}
                    lf = pred.find("LeftField")
                    if lf is not None:
                        field = lf.find("Field")
                        if field is not None:
                            p["left_field"] = field.get("name")
                    rf = pred.find("RightField")
                    if rf is not None:
                        field = rf.find("Field")
                        if field is not None:
                            p["right_field"] = field.get("name")
                    predicates.append(p)
                r["predicates"] = predicates

            for side in ["Left", "Right"]:
                opts_el = rel.find(f"{side}Options")
                if opts_el is not None:
                    opts = {}
                    if opts_el.get("deleteRelated") == "True":
                        opts["delete_related"] = True
                    if opts_el.get("createRelated") == "True":
                        opts["allow_create"] = True
                    sort = opts_el.find("SortList")
                    if sort is not None and len(list(sort)):
                        sort_fields = []
                        for sf in sort.findall("Sort"):
                            field = sf.find("Field")
                            if field is not None:
                                sort_fields.append({
                                    "field": field.get("name"),
                                    "order": sf.get("type", "Ascending"),
                                })
                        if sort_fields:
                            opts["sort"] = sort_fields
                    if opts:
                        r[f"{side.lower()}_options"] = opts

            self._inject_source(r)
            relationships.append(r)
        return relationships

    # ─── LAYOUTS ────────────────────────────────────────────────────────

    def _parse_single_layout(self, layout_el, group_path=""):
        """Parse a single Layout element into a dict."""
        name = layout_el.get("name", "")
        if name == "-":
            return None

        l = {
            "id": layout_el.get("id"),
            "name": name,
            "width": layout_el.get("width"),
            "in_menu": layout_el.get("includeInMenu") == "True",
        }

        if group_path:
            l["group"] = group_path

        table = layout_el.find("Table")
        if table is not None:
            l["table"] = table.get("name")

        fields_shown = []
        portals = []
        buttons = []
        cond_formatting = []
        hide_conditions = []

        def walk(el):
            if el.tag == "Object":
                otype = el.get("type", "")
                obj_name = el.get("name", "")
                if otype == "Field":
                    fref = extract_field_from_obj(el)
                    if fref:
                        fields_shown.append(fref)
                elif otype == "Portal":
                    po = el.find("PortalObj")
                    if po is not None:
                        alias = po.find("TableAliasKey")
                        portal_table = alias.text.strip() if alias is not None and alias.text else ""
                        portal_fields = []
                        fl = po.find("FieldList")
                        if fl is not None:
                            for f in fl.findall("Field"):
                                portal_fields.append({
                                    "table": f.get("table", ""),
                                    "field": f.get("name", ""),
                                })
                        portals.append({"table": portal_table, "fields": portal_fields})

                # Conditional formatting — on any Object.
                # Real shape (100% consistent in FileMaker 22 DDR output):
                #   <ConditionalFormatting>
                #     <Item id flags>
                #       <Condition op="0"><Calculation>..</Calculation></Condition>
                #       <Format><Styles><LocalCSS>..</LocalCSS></Styles></Format>
                #     </Item>
                # Condition is nested under <Item> (findall is non-recursive, so
                # looking for it directly returned [] every time), the attribute
                # is `op` not `type`, and Format is Condition's SIBLING, not its
                # child. Getting all four wrong extracted exactly zero rules.
                cf_el = el.find("ConditionalFormatting")
                if cf_el is not None:
                    for item in cf_el.findall("Item"):
                        fmt = item.find("Format")
                        css = ""
                        if fmt is not None:
                            css = (fmt.findtext("Styles/LocalCSS") or "").strip()
                        for cond in item.findall("Condition"):
                            formula = get_calculation(cond)
                            if not formula:
                                continue
                            cond_formatting.append({
                                "object_name": obj_name or "",
                                "object_type": otype,
                                "condition_type": cond.get("op", ""),
                                "flags": item.get("flags", ""),
                                "formula": formula,
                                "format_css": css,
                            })

                # Hide Object When — on any Object
                hide_el = el.find("HideCondition")
                if hide_el is not None:
                    formula = get_calculation(hide_el)
                    if formula:
                        hide_conditions.append({
                            "object_name": obj_name or "",
                            "object_type": otype,
                            "formula": formula,
                        })

            # Buttons come in four flavours, not one. Handling only
            # GroupButtonObj -- and only its DIRECT Step child -- missed 57% of
            # button actions: plain ButtonObj carries the majority of real
            # bindings, GroupButtonObj is often a container whose Step sits a
            # level deeper, and PopoverButtonObj/ButtonBarObj were ignored
            # outright. Search nested Steps across all four.
            elif el.tag in ("GroupButtonObj", "ButtonObj", "PopoverButtonObj", "ButtonBarObj"):
                for step in el.iter("Step"):
                    action = step.get("name", "")
                    if not action:
                        continue
                    b = {"action": action, "button_type": el.tag}
                    script_ref = step.find("Script")
                    if script_ref is not None:
                        b["script"] = script_ref.get("name", "")
                    step_text = step.find("StepText")
                    if step_text is not None and step_text.text:
                        b["description"] = step_text.text.strip()
                    buttons.append(b)

            for c in el:
                walk(c)

        for child in layout_el:
            walk(child)

        # Deduplicate fields
        seen = set()
        unique_fields = []
        for f in fields_shown:
            key = f"{f['table']}::{f['field']}"
            if key not in seen:
                seen.add(key)
                unique_fields.append(f)

        # Deduplicate buttons on (action, script). Keying on script alone
        # collapses distinct actions that call no script -- and `.get("script",
        # default)` returns "" rather than the default when the key exists but
        # is empty, so scriptless buttons all collided on "".
        seen_btns = set()
        unique_buttons = []
        for b in buttons:
            key = (b.get("action", ""), b.get("script", ""))
            if key[0] and key not in seen_btns:
                seen_btns.add(key)
                unique_buttons.append(b)

        l["fields"] = unique_fields
        l["portals"] = portals
        l["buttons"] = unique_buttons
        l["conditional_formatting"] = cond_formatting
        l["hide_conditions"] = hide_conditions

        self._inject_source(l)
        return l

    def _parse_layouts(self):
        print("  Parsing layouts...")
        catalog = self.file_el.find("LayoutCatalog")
        if catalog is None:
            return []

        layouts = []

        def walk_group(group_el, path=""):
            group_name = group_el.get("name", "")
            current_path = f"{path}/{group_name}" if path else group_name

            for child in group_el:
                if child.tag == "Group":
                    walk_group(child, current_path)
                elif child.tag == "Layout":
                    parsed = self._parse_single_layout(child, current_path)
                    if parsed:
                        layouts.append(parsed)

        for child in catalog:
            if child.tag == "Group":
                walk_group(child)
            elif child.tag == "Layout":
                parsed = self._parse_single_layout(child)
                if parsed:
                    layouts.append(parsed)

        return layouts

    # ─── SCRIPTS ────────────────────────────────────────────────────────

    def _parse_scripts(self):
        print("  Parsing scripts...")
        catalog = self.file_el.find("ScriptCatalog")
        if catalog is None:
            return []

        scripts = []

        def parse_script(script_el, current_path):
            name = script_el.get("name", "")
            # "-" is a visual separator in the script menu, not a script.
            # _parse_layouts has always skipped these; scripts now match.
            if name.strip() == "-":
                return
            script = {
                "id": script_el.get("id"),
                "name": name,
                "group": current_path,
                "in_menu": script_el.get("includeInMenu") == "True",
            }
            sl = script_el.find("StepList")
            script["steps"] = parse_script_steps(sl)
            self._inject_source(script)
            scripts.append(script)

        def walk_group(group_el, path=""):
            group_name = group_el.get("name", "")
            current_path = f"{path}/{group_name}" if path else group_name

            for child in group_el:
                if child.tag == "Group":
                    walk_group(child, current_path)
                elif child.tag == "Script":
                    parse_script(child, current_path)

        # ScriptCatalog holds BOTH grouped scripts and scripts declared at its
        # root. Descending only into Groups (the original bug) silently dropped
        # every ungrouped script -- which is exactly where FileMaker developers
        # put startup, login, routing and cross-cutting trigger logic.
        # This mirrors _parse_layouts, which has always handled both.
        for child in catalog:
            if child.tag == "Group":
                walk_group(child)
            elif child.tag == "Script":
                parse_script(child, "")

        return scripts

    # ─── VALUE LISTS ────────────────────────────────────────────────────

    def _parse_value_lists(self):
        print("  Parsing value lists...")
        catalog = self.file_el.find("ValueListCatalog")
        if catalog is None:
            return []

        vlists = []
        for vl in catalog.findall("ValueList"):
            v = {
                "id": vl.get("id"),
                "name": vl.get("name"),
            }

            source = vl.find("Source")
            source_type = source.get("value", "") if source is not None else ""

            if source_type == "Custom":
                v["type"] = "custom"
                cv = vl.find("CustomValues")
                if cv is not None:
                    text_el = cv.find("Text")
                    if text_el is not None and text_el.text:
                        v["values"] = [line.strip() for line in text_el.text.strip().split("\n") if line.strip()]

            elif source_type == "Field":
                v["type"] = "field"
                pf = vl.find("PrimaryField")
                if pf is not None:
                    field = pf.find("Field")
                    if field is not None:
                        v["primary_table"] = field.get("table", "")
                        v["primary_field"] = field.get("name", "")
                        v["primary_show"] = pf.get("show", "")

                sf = vl.find("SecondaryField")
                if sf is not None:
                    field2 = sf.find("Field")
                    if field2 is not None:
                        v["secondary_table"] = field2.get("table", "")
                        v["secondary_field"] = field2.get("name", "")
                        v["secondary_show"] = sf.get("show", "")

                sr = vl.find("ShowRelated")
                if sr is not None and sr.get("value") == "True":
                    rel_table = sr.find("Table")
                    if rel_table is not None:
                        v["show_related_from"] = rel_table.get("name", "")

            self._inject_source(v)
            vlists.append(v)

        return vlists

    # ─── ACCOUNTS & PRIVILEGES ──────────────────────────────────────────

    def _parse_accounts(self):
        print("  Parsing accounts & privileges...")

        acatalog = self.file_el.find("AccountCatalog")
        accounts = []
        if acatalog is not None:
            for acc in acatalog.findall("Account"):
                a = {
                    "id": acc.get("id"),
                    "name": acc.get("name"),
                    "status": acc.get("status"),
                    "privilege_set": acc.get("privilegeSet"),
                    "empty_password": acc.get("emptyPassword"),
                }
                self._inject_source(a)
                accounts.append(a)

        pcatalog = self.file_el.find("PrivilegesCatalog")
        privileges = []
        if pcatalog is not None:
            for ps in pcatalog.findall("PrivilegeSet"):
                p = {
                    "id": ps.get("id"),
                    "name": ps.get("name"),
                }

                # The four tags this used to look for -- RecordAccessPrivileges,
                # LayoutAccessPrivileges, ScriptAccessPrivileges and
                # ExtendedPrivileges -- do not exist in FileMaker DDR output.
                # The real children are Records / Layouts / Scripts / ValueLists,
                # so every privilege set emitted as just {id, name}: no per-table
                # grants, no field-level restrictions, and no row-level security
                # predicates. Those predicates are the authorization model.
                for attr in ("menu", "printing", "exporting", "idleDisconnect",
                             "manageAccounts", "managedExtended", "allowModifyPassword",
                             "overrideValidationWarning", "comment"):
                    if ps.get(attr) is not None:
                        p[attr] = ps.get(attr)

                def _value(el, tag):
                    child = el.find(tag) if el is not None else None
                    return child.get("value", "") if child is not None else ""

                records = ps.find("Records")
                if records is not None:
                    rec = {"value": records.get("value", "")}
                    tables = []
                    for bt in records.findall("TableList/BaseTable"):
                        entry = {
                            "table": bt.get("name", ""),
                            "create": _value(bt, "Create"),
                            "view": _value(bt, "View"),
                            "edit": _value(bt, "Edit"),
                            "delete": _value(bt, "Delete"),
                            "field_access": _value(bt, "FieldAccess"),
                        }
                        # A "Limited" grant carries a calculation -- this is
                        # row-level security, and it is the whole ballgame.
                        for tag in ("View", "Edit", "Create", "Delete"):
                            calc = get_calculation(bt.find(tag)) if bt.find(tag) is not None else None
                            if calc:
                                entry[f"{tag.lower()}_calculation"] = calc
                        fields = [
                            {"field": f.get("name", ""),
                             "restriction": f.get("accessRestriction", "")}
                            for f in bt.findall("FieldAccess/FieldList/Field")
                        ]
                        if fields:
                            entry["fields"] = fields
                        tables.append(entry)
                    if tables:
                        rec["tables"] = tables
                    p["records"] = rec

                # Real shape (verified, gold Schema — 236 grants):
                #   <LayoutList>
                #     <Layout id="1" name="Intakes">      <- the NAME lives here
                #       <LayoutAccess value="NoAccess"/>  <- access is a CHILD
                #       <DataAccess   value="NoAccess"/>  <- and DataAccess is its SIBLING
                # Reading LayoutList/LayoutAccess directly finds nothing: same wrapper trap
                # as ConditionalFormatting's <Item>. It silently dropped all 236 grants.
                layouts = ps.find("Layouts")
                if layouts is not None:
                    lay = {
                        "value": layouts.get("value", ""),
                        "allow_creation": layouts.get("allowCreation", ""),
                    }
                    items = [
                        {"layout": el.get("name", ""),
                         "id": el.get("id", ""),
                         "access": _value(el, "LayoutAccess"),
                         "data_access": _value(el, "DataAccess")}
                        for el in layouts.findall("LayoutList/Layout")
                    ]
                    if items:
                        lay["items"] = items
                    p["layouts"] = lay

                # Scripts / ValueLists carry only a coarse grant here. Measured across all
                # 13 offices: Scripts is ExecutableOnly/Modifiable/NoAccess (199 sets) and
                # ValueLists is Modifiable/ViewOnly/NoAccess (199 sets). NEITHER is ever
                # "Custom", so no per-item list is ever emitted and its shape is unobserved.
                # Deliberately not guessing at one -- encoding an unverified shape is the
                # exact mistake that produced every defect this parser was audited for.
                # If a future export shows Custom here, verify the real nesting against the
                # XML first (Layouts above is the likely template: List > Item > Access).
                for tag, key in (("Scripts", "scripts"), ("ValueLists", "value_lists")):
                    el = ps.find(tag)
                    if el is not None:
                        p[key] = {
                            "value": el.get("value", ""),
                            "allow_creation": el.get("allowCreation", ""),
                        }

                self._inject_source(p)
                privileges.append(p)

        return accounts, privileges

    # ─── CUSTOM FUNCTIONS ───────────────────────────────────────────────

    def _parse_custom_functions(self):
        print("  Parsing custom functions...")
        catalog = self.file_el.find("CustomFunctionCatalog")
        if catalog is None:
            return []

        functions = []
        for cf in catalog.findall("CustomFunction"):
            func = {
                "id": cf.get("id"),
                "name": cf.get("name"),
                "parameters": cf.get("parameters", ""),
                "visible": cf.get("visible", "True"),
            }
            cf_calc = get_calculation(cf)
            if cf_calc:
                func["calculation"] = cf_calc
            self._inject_source(func)
            functions.append(func)

        return functions

    # ─── EXTERNAL DATA SOURCES ──────────────────────────────────────────

    def _parse_external_data_sources(self):
        print("  Parsing external data sources...")
        catalog = self.file_el.find("ExternalDataSourcesCatalog")
        if catalog is None:
            return []

        sources = []

        # FileReference entries — other FileMaker files
        for fr in catalog.findall("FileReference"):
            entry = {
                "type": "filemaker",
                "id": fr.get("id", ""),
                "name": fr.get("name", ""),
            }
            path_list = fr.find("PathList")
            if path_list is not None:
                paths = []
                for p in path_list.findall("Path"):
                    if p.text:
                        paths.append(p.text.strip())
                if paths:
                    entry["paths"] = paths
            self._inject_source(entry)
            sources.append(entry)

        # OdbcDataSource entries — external non-FM databases
        for odbc in catalog.findall("OdbcDataSource"):
            entry = {
                "type": "odbc",
                "id": odbc.get("id", ""),
                "name": odbc.get("name", ""),
                "dsn": odbc.get("DSN", ""),
            }
            self._inject_source(entry)
            sources.append(entry)

        return sources


# ─── DDRMerger CLASS ─────────────────────────────────────────────────────────

class DDRMerger:
    """Merges parsed data from multiple DDRFile objects into unified specs."""

    def __init__(self, ddr_files):
        self.files = ddr_files
        self.multi_file = len(ddr_files) > 1

        # Build EDS map: symbolic name → source file name that defines it
        # Used to resolve external file references
        self._eds_map = self._build_eds_map()

    def _build_eds_map(self):
        """Map external data source names to actual parsed file names."""
        eds_map = {}
        known_files = {f.source_file for f in self.files}

        for ddr in self.files:
            for eds in ddr.external_data_sources:
                if eds["type"] == "filemaker":
                    eds_name = eds["name"]
                    # Try to match to a known parsed file
                    if eds_name in known_files:
                        eds_map[(ddr.source_file, eds_name)] = eds_name
                    else:
                        # Try matching without extension
                        for kf in known_files:
                            kf_base = os.path.splitext(kf)[0]
                            if eds_name == kf_base or eds_name.lower() == kf_base.lower():
                                eds_map[(ddr.source_file, eds_name)] = kf
                                break
        return eds_map

    def _resolve_external_ref(self, source_file, ref_name):
        """Try to resolve an external file reference name to a known file."""
        known_files = {f.source_file for f in self.files}

        # Direct match
        if ref_name in known_files:
            return ref_name

        # Via EDS map
        resolved = self._eds_map.get((source_file, ref_name))
        if resolved:
            return resolved

        # Case-insensitive / extensionless match
        for kf in known_files:
            kf_base = os.path.splitext(kf)[0]
            if ref_name == kf_base or ref_name.lower() == kf_base.lower():
                return kf

        return None  # Unresolved

    def merge_topology(self):
        """Produce the 00_topology.json with file inventory and cross-file refs."""
        files_info = []
        cross_file_tos = []
        cross_file_scripts = []
        unresolved_refs = []

        known_files = {f.source_file for f in self.files}

        for ddr in self.files:
            info = {
                "name": ddr.source_file,
                "filepath": ddr.filepath,
                "base_tables": [t["name"] for t in ddr.tables],
                "counts": {
                    "tables": len(ddr.tables),
                    "table_occurrences": len(ddr.table_occurrences),
                    "relationships": len(ddr.relationships),
                    "layouts": len(ddr.layouts),
                    "scripts": len(ddr.scripts),
                    "value_lists": len(ddr.value_lists),
                    "custom_functions": len(ddr.custom_functions),
                    "conditional_formatting": len(ddr.conditional_formatting),
                    "hide_conditions": len(ddr.hide_conditions),
                },
                "external_data_sources": ddr.external_data_sources,
            }
            files_info.append(info)

            # Track cross-file TOs
            for to in ddr.table_occurrences:
                if "external_file_reference" in to:
                    ref_name = to["external_file_reference"]["name"]
                    resolved = self._resolve_external_ref(ddr.source_file, ref_name)
                    entry = {
                        "from_file": ddr.source_file,
                        "to_name": to["name"],
                        "base_table": to.get("base_table"),
                        "external_ref": ref_name,
                        "resolved_to": resolved,
                    }
                    cross_file_tos.append(entry)
                    if resolved is None:
                        unresolved_refs.append({
                            "type": "table_occurrence",
                            "from_file": ddr.source_file,
                            "reference": ref_name,
                            "context": f"TO '{to['name']}' references file '{ref_name}'",
                        })

            # Track cross-file script calls
            for script in ddr.scripts:
                for step in script.get("steps", []):
                    params = step.get("params", {})
                    if "external_file" in params:
                        ext_file = params["external_file"]
                        resolved = self._resolve_external_ref(ddr.source_file, ext_file)
                        entry = {
                            "from_file": ddr.source_file,
                            "script": script["name"],
                            "step": step.get("name"),
                            "calls_script": params.get("script", ""),
                            "external_ref": ext_file,
                            "resolved_to": resolved,
                        }
                        cross_file_scripts.append(entry)
                        if resolved is None:
                            unresolved_refs.append({
                                "type": "script_call",
                                "from_file": ddr.source_file,
                                "reference": ext_file,
                                "context": f"Script '{script['name']}' calls script in file '{ext_file}'",
                            })

            # Check EDS references to files not in our set
            for eds in ddr.external_data_sources:
                if eds["type"] == "filemaker":
                    eds_name = eds["name"]
                    resolved = self._resolve_external_ref(ddr.source_file, eds_name)
                    if resolved is None and eds_name not in known_files:
                        unresolved_refs.append({
                            "type": "external_data_source",
                            "from_file": ddr.source_file,
                            "reference": eds_name,
                            "context": f"External data source '{eds_name}' — DDR not found",
                        })

        topology = {
            "multi_file": self.multi_file,
            "file_count": len(self.files),
            "files": files_info,
            "cross_file_references": {
                "table_occurrences": cross_file_tos,
                "script_calls": cross_file_scripts,
            },
            "unresolved_references": unresolved_refs,
        }

        if unresolved_refs:
            print(f"\n  WARNING: {len(unresolved_refs)} unresolved cross-file reference(s):")
            for ref in unresolved_refs:
                print(f"    - {ref['context']}")

        return topology

    def merge_tables(self):
        """Concatenate tables from all files (no dedup — different files = different tables)."""
        merged = []
        for ddr in self.files:
            merged.extend(ddr.tables)
        return merged

    def merge_table_occurrences(self):
        """Concatenate TOs from all files, resolving external file references."""
        merged = []
        for ddr in self.files:
            for to in ddr.table_occurrences:
                if "external_file_reference" in to:
                    ref_name = to["external_file_reference"]["name"]
                    resolved = self._resolve_external_ref(ddr.source_file, ref_name)
                    if resolved:
                        to["resolved_source_file"] = resolved
                merged.append(to)
        return merged

    def merge_relationships(self):
        merged = []
        for ddr in self.files:
            merged.extend(ddr.relationships)
        return merged

    def merge_layouts(self):
        merged = []
        for ddr in self.files:
            for layout in ddr.layouts:
                out = {k: v for k, v in layout.items()
                       if k not in ("conditional_formatting", "hide_conditions")}
                merged.append(out)
        return merged

    def merge_scripts(self):
        merged = []
        for ddr in self.files:
            merged.extend(ddr.scripts)
        return merged

    def merge_value_lists(self):
        merged = []
        for ddr in self.files:
            merged.extend(ddr.value_lists)
        return merged

    # Access blocks are per-file: in a multi-file solution the UI file and the
    # data file each define their own rules under the SAME privilege-set name.
    _ACCESS_KEYS = ("records", "layouts", "scripts", "value_lists")

    def merge_security(self):
        """Merge accounts and privilege sets.

        FileMaker syncs privilege-set NAMES across the files of a solution, but
        NOT their contents: the UI file typically carries a coarse grant
        (Records value="CreateEditDelete") while the data file carries the real
        model (value="Custom" with per-table grants, field restrictions and
        row-level security calculations).

        Deduping by name and keeping the first occurrence therefore discards the
        authorization model outright -- the files sort UI-first. Dedup on
        identity, but keep every file's access block under `access_by_file`.
        """
        all_accounts = []
        for ddr in self.files:
            all_accounts.extend(ddr.accounts)

        priv_by_name = {}
        for ddr in self.files:
            for p in ddr.privileges:
                name = p["name"]
                access = {k: p[k] for k in self._ACCESS_KEYS if k in p}

                if name not in priv_by_name:
                    entry = {k: v for k, v in p.items() if k not in self._ACCESS_KEYS}
                    entry["source_files"] = [ddr.source_file]
                    entry.pop("source_file", None)
                    entry["access_by_file"] = {}
                    priv_by_name[name] = entry
                else:
                    entry = priv_by_name[name]
                    if ddr.source_file not in entry["source_files"]:
                        entry["source_files"].append(ddr.source_file)

                if access:
                    priv_by_name[name]["access_by_file"][ddr.source_file] = access

        # Surface the richest definition at the top level for convenience: the
        # one that actually enumerates tables. Consumers wanting per-file detail
        # read access_by_file.
        for entry in priv_by_name.values():
            best = None
            for source_file, access in entry["access_by_file"].items():
                tables = (access.get("records") or {}).get("tables")
                if tables and (best is None or len(tables) > best[1]):
                    best = (source_file, len(tables))
            chosen = best[0] if best else next(iter(entry["access_by_file"]), None)
            if chosen:
                entry.update(entry["access_by_file"][chosen])
                entry["access_source_file"] = chosen

        return all_accounts, list(priv_by_name.values())

    def merge_custom_functions(self):
        merged = []
        for ddr in self.files:
            merged.extend(ddr.custom_functions)
        return merged

    def merge_conditional_formatting(self):
        merged = []
        for ddr in self.files:
            merged.extend(ddr.conditional_formatting)
        return merged

    def merge_hide_conditions(self):
        merged = []
        for ddr in self.files:
            merged.extend(ddr.hide_conditions)
        return merged

    def merge_all(self, output_dir):
        """Run all merges and write all spec files."""
        os.makedirs(output_dir, exist_ok=True)

        print("\nMerging and writing specs...")

        topology = self.merge_topology()
        write_json(output_dir, "00_topology", topology)

        tables = self.merge_tables()
        write_json(output_dir, "01_tables", tables)

        occurrences = self.merge_table_occurrences()
        write_json(output_dir, "02_table_occurrences", occurrences)

        relationships = self.merge_relationships()
        write_json(output_dir, "03_relationships", relationships)

        layouts = self.merge_layouts()
        write_json(output_dir, "04_layouts", layouts)

        scripts = self.merge_scripts()
        write_json(output_dir, "05_scripts", scripts)

        vlists = self.merge_value_lists()
        write_json(output_dir, "06_value_lists", vlists)

        accounts, privileges = self.merge_security()
        write_json(output_dir, "07_security", {"accounts": accounts, "privileges": privileges})

        functions = self.merge_custom_functions()
        write_json(output_dir, "08_custom_functions", functions)

        cond_fmt = self.merge_conditional_formatting()
        write_json(output_dir, "09_conditional_formatting", cond_fmt)

        hide_conds = self.merge_hide_conditions()
        write_json(output_dir, "10_hide_object_when", hide_conds)

        return {
            "topology": topology,
            "tables": tables,
            "occurrences": occurrences,
            "relationships": relationships,
            "layouts": layouts,
            "scripts": scripts,
            "value_lists": vlists,
            "accounts": accounts,
            "privileges": privileges,
            "custom_functions": functions,
            "conditional_formatting": cond_fmt,
            "hide_conditions": hide_conds,
        }


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    report_paths = find_ddr_reports(input_path)

    # Determine output directory
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    elif os.path.isdir(input_path):
        output_dir = os.path.join(input_path, "specs")
    else:
        output_dir = os.path.join(os.path.dirname(input_path) or ".", "specs")

    multi_file = len(report_paths) > 1
    print(f"Found {len(report_paths)} DDR Report file(s):")
    for rp in report_paths:
        print(f"  - {rp}")
    print(f"Output: {output_dir}\n")

    # Parse each file
    ddr_files = []
    for rp in report_paths:
        ddr = DDRFile(rp)
        ddr.parse_all()
        ddr_files.append(ddr)

    # Merge and write
    merger = DDRMerger(ddr_files)
    results = merger.merge_all(output_dir)

    # Summary
    print(f"\nDone. All specs written to {output_dir}/")

    # NOTE: do NOT `import parse_ddr` here to read the counter. Run as a script
    # this module is __main__, so that import loads a SECOND copy whose counter is
    # always 0 -- the summary silently never printed. _redaction_count is already
    # this module's global; read it directly.
    if _redaction_count:
        print(f"\n  Redacted {_redaction_count} hardcoded credential literal(s) "
              f"from script steps.")
        print(f"  Structure is preserved; values are replaced with "
              f"{REDACTION_PLACEHOLDER}.")
        print(f"  The real values remain in the raw DDR XML, which should stay "
              f"gitignored.")

    if multi_file:
        print(f"\n  Multi-file solution ({len(ddr_files)} files):")
        for ddr in ddr_files:
            print(f"\n  {ddr.source_file}:")
            print(f"    Tables: {len(ddr.tables)}")
            print(f"    Table occurrences: {len(ddr.table_occurrences)}")
            print(f"    Relationships: {len(ddr.relationships)}")
            print(f"    Layouts: {len(ddr.layouts)}")
            print(f"    Scripts: {len(ddr.scripts)}")
            print(f"    Value lists: {len(ddr.value_lists)}")
            print(f"    Custom functions: {len(ddr.custom_functions)}")
            print(f"    External data sources: {len(ddr.external_data_sources)}")
            print(f"    Conditional formatting rules: {len(ddr.conditional_formatting)}")
            print(f"    Hide-object-when rules: {len(ddr.hide_conditions)}")

        unresolved = results["topology"]["unresolved_references"]
        if unresolved:
            print(f"\n  Unresolved cross-file references: {len(unresolved)}")
        print()

    print(f"  Totals:")
    print(f"    Tables: {len(results['tables'])}")
    print(f"    Table occurrences: {len(results['occurrences'])}")
    print(f"    Relationships: {len(results['relationships'])}")
    print(f"    Layouts: {len(results['layouts'])}")
    print(f"    Scripts: {len(results['scripts'])}")
    print(f"    Value lists: {len(results['value_lists'])}")
    print(f"    Accounts: {len(results['accounts'])}")
    print(f"    Privilege sets: {len(results['privileges'])}")
    print(f"    Custom functions: {len(results['custom_functions'])}")
    print(f"    Conditional formatting rules: {len(results['conditional_formatting'])}")
    print(f"    Hide-object-when rules: {len(results['hide_conditions'])}")
