"""Golden-fixture regression test for scripts/parse_ddr.py.

Run:  python3 -m unittest discover -s tests -v
      python3 tests/test_parse_ddr.py

Stdlib only, on purpose: parse_ddr.py is stdlib-only and must stay that way.

WHY THIS EXISTS
---------------
parse_ddr.py has a verify() self-check, but it only reconciles COUNTS against
the raw XML. Counts cannot see semantic corruption. The worst defect this parser
ever shipped -- get_calculation deleting every field reference, turning
"Get ( AccountName ) <> Case_Notes::log_created_account" into
"Get ( AccountName ) <>" -- changes no count at all. verify() would have passed
it. It corrupted 9,148 field references across 6,229 calculations in gold, drove
a "drop" recommendation on live restitution accounting, and inverted the
documented meaning of the single largest authorization rule.

So this test asserts VALUES, not counts. Each test names the defect it guards
and fails with the concrete wrong output, not a number that is off by one.

See tests/README.md and docs/013_ddr-extractor-audit.md (in the dacw repo).
"""

import io
import contextlib
import os
import sys
import tempfile
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "scripts"))

import parse_ddr  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "mini_ddr.xml")


def parse_fixture():
    """Run the real parser end-to-end over the fixture, silencing its chatter."""
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        ddr = parse_ddr.DDRFile(FIXTURE)
        ddr.parse_all()
        merger = parse_ddr.DDRMerger([ddr])
        with tempfile.TemporaryDirectory() as tmp:
            results = merger.merge_all(tmp)
    return ddr, results, buf.getvalue(), err.getvalue()


# ─── EXPECTED OUTPUT (golden) ────────────────────────────────────────────────

SRC = "Mini.fmp12"

EXPECTED_TABLES = [
    {
        "id": "1",
        "name": "Intakes",
        "records": 3,
        "fields": [
            {
                "id": "1",
                "name": "ID",
                "data_type": "Text",
                "field_type": "Normal",
                "comment": "Primary key",
                # <Calculation> DIRECT text -- there is no <Text> child to read.
                "auto_enter": {"calculation": "Get ( UUID )"},
                "validation": {"not_empty": True, "unique": True},
                "index": "Minimal",
            }
        ],
        "calculated": [
            {
                "id": "2",
                "name": "Restitution_Owed_Display",
                "data_type": "Number",
                "field_type": "Calculated",
                # A single FieldRef chunk. This key going missing is the exact
                # signature that made 8 live fields look formula-less.
                "calculation": "LINE_ITEMS_Restitution::Balance_Due",
            }
        ],
        "summary": [
            {"id": "5", "name": "sum_amount", "data_type": "Number", "field_type": "Summary"}
        ],
        "globals": [
            {
                "id": "4",
                "name": "g_scratch",
                "data_type": "Text",
                "field_type": "Normal",
                "global": True,
            }
        ],
        "source_file": SRC,
    }
]

EXPECTED_OCCURRENCES = [
    {"id": "1001", "name": "Intakes", "base_table": "Intakes", "base_table_id": "1",
     "source_file": SRC},
    {"id": "1002", "name": "LINE_ITEMS_Restitution", "base_table": "Intakes",
     "base_table_id": "1", "source_file": SRC},
]

EXPECTED_RELATIONSHIPS = [
    {
        "id": "1",
        "left_table": "Intakes",
        "right_table": "LINE_ITEMS_Restitution",
        "predicates": [{"operator": "Equal", "left_field": "ID", "right_field": "Intake_ID"}],
        "source_file": SRC,
    }
]

EXPECTED_LAYOUTS = [
    {
        "id": "11",
        "name": "Intake Detail",
        "width": "690",
        "in_menu": True,
        "table": "Intakes",
        "fields": [
            {"table": "Intakes", "field": "ID"},
            {"table": "LINE_ITEMS_Restitution", "field": "Balance_Due"},
        ],
        "portals": [
            {"table": "LINE_ITEMS_Restitution",
             "fields": [{"table": "LINE_ITEMS_Restitution", "field": "Balance_Due"}]}
        ],
        "buttons": [
            # A plain ButtonObj -- ignored outright by the original parser.
            {"action": "Perform Script", "button_type": "ButtonObj",
             "object_key": "2",
             "script": "Send Officer Dispositions", "script_id": "79",
             "description": "Perform Script [ “Send Officer Dispositions” ]"},
            # A GroupButtonObj container whose Step is one level deeper.
            {"action": "Perform Script", "button_type": "GroupButtonObj",
             "object_key": "3",
             "script": "Set is_Closed from GJ Status", "script_id": "1539",
             "description": "Perform Script [ “Set is_Closed from GJ Status” ]"},
        ],
        "source_file": SRC,
    },
    {
        "id": "12",
        "name": "Restitution Report",
        "width": "690",
        "in_menu": True,
        "group": "Reports",
        "table": "Intakes",
        "fields": [],
        "portals": [],
        "buttons": [],
        "source_file": SRC,
    },
]

EXPECTED_SCRIPTS = [
    {
        # Declared at ScriptCatalog ROOT. group == "".
        "id": "1",
        "name": "Open",
        "group": "",
        "in_menu": False,
        "steps": [
            {"id": "1", "name": "Perform Script", "enable": "True",
             "step_text": "Perform Script [ “Set User Information at Login” ]",
             "params": {"script": "Set User Information at Login", "script_id": "794"}},
            # REDACTION: the keyword sits in the VARIABLE NAME, not in the value.
            # <Value> is bare ("hunter2-should-not-ship"), so keyword-adjacency
            # alone cannot see it -- looks_like_secret_target must catch it via
            # $password. This exact case leaked when the redactor first shipped.
            {"id": "90", "name": "Set Variable", "enable": "True",
             "step_text": 'Set Variable [ $password ; Value: "<REDACTED>" ]',
             "params": {"variable": "$password", "value": '"<REDACTED>"'}},
            # REDACTION: caught two ways over -- keyword adjacency ("api_key" =)
            # inside the calculation, and $apikey as the target.
            {"id": "91", "name": "Set Variable", "enable": "True",
             "step_text": 'Set Variable [ $apikey ; Value: "<REDACTED>" ]',
             "params": {"calculation": 'Let ( $api_key = "<REDACTED>" ; $api_key )',
                        "variable": "$apikey"}},
            # MUST NOT REDACT: "Token" is INSIDE the quotes and the field refs are
            # unquoted. A redactor that fires here is eating business logic.
            {"id": "92", "name": "Set Field", "enable": "True",
             "step_text": 'Set Field [ Intakes::Status; If ( Intakes::Kind = "Token" ; "yes" ; "no" ) ]'},
            {"id": "2", "name": "Set Field", "enable": "True",
             "step_text": "Set Field [ Intakes::is_Closed; 1 ]",
             "params": {"field": "is_Closed", "calculation": "1"}},
        ],
        "source_file": SRC,
    },
    {
        "id": "1539",
        "name": "Set is_Closed from GJ Status",
        "group": "Modules/Grand Jury",
        "in_menu": True,
        "steps": [
            {"id": "1", "name": "If", "enable": "True",
             "step_text": 'If [ Grand_Jury_Docket_Display::GJ_Disposition = "No Billed" ]',
             "params": {
                 "calculation": 'Grand_Jury_Docket_Display::GJ_Disposition = "No Billed"'}},
            # No params: a bare "End If" has no structured children. step_text is
            # the only thing that makes it readable.
            {"id": "2", "name": "End If", "enable": "True", "step_text": "End If"},
        ],
        "source_file": SRC,
    },
]

EXPECTED_VALUE_LISTS = [
    {"id": "1", "name": "Case Status", "type": "custom", "values": ["Open", "Closed"],
     "source_file": SRC}
]

EXPECTED_ACCOUNTS = [
    {"id": "1", "name": "[Guest]", "status": "Inactive",
     "privilege_set": "[Read-Only Access]", "empty_password": "False", "source_file": SRC},
    {"id": "2", "name": "tenloe", "status": "Active",
     "privilege_set": "Manager", "empty_password": "False", "source_file": SRC},
]

_FULL_ACCESS_ACCESS = {
    "records": {"value": "CreateEditDelete"},
    "layouts": {"value": "Modifiable", "allow_creation": "True"},
    "scripts": {"value": "Modifiable", "allow_creation": "True"},
    "value_lists": {"value": "Modifiable", "allow_creation": "True"},
}

_MANAGER_ACCESS = {
    "records": {
        "value": "Custom",
        "tables": [
            {
                "table": "Intakes",
                "create": "True",
                "view": "Limited",
                "edit": "False",
                "delete": "False",
                "field_access": "Limited",
                # THE row-level security predicate. It only survives because
                # get_calculation resolves FieldRef children.
                "view_calculation": "not Investigation_boolean and not isAdmin_Private",
                "fields": [
                    {"field": "ID", "restriction": "ViewOnly"},
                    {"field": "Restitution_Owed_Display", "restriction": "Modifiable"},
                ],
            },
            {
                "table": "[Any New Table]",
                "create": "False",
                "view": "False",
                "edit": "False",
                "delete": "False",
                "field_access": "NoAccess",
            },
        ],
    },
    # FIXED (was pinned here as known-lossy, and this assertion duly failed when
    # the fix landed -- which is the whole point of a golden test).
    # FileMaker emits Layouts/LayoutList/Layout/LayoutAccess: LayoutAccess is a
    # CHILD of Layout carrying value=, not a sibling carrying name=, and
    # DataAccess is LayoutAccess's SIBLING. Reading LayoutList/LayoutAccess
    # directly matched nothing and silently dropped every per-layout grant
    # (236 in gold's RCDA_Schema). Same wrapper trap as ConditionalFormatting's
    # <Item>. This now guards against the regression.
    "layouts": {
        "value": "Custom",
        "allow_creation": "False",
        "items": [
            {
                "layout": "Intake Detail",
                "id": "11",
                "access": "Modifiable",
                "data_access": "Modifiable",
            }
        ],
    },
    # No "items" for these two, and that is CORRECT rather than lossy: measured
    # across all 13 offices, Scripts is only ever ExecutableOnly/Modifiable/
    # NoAccess and ValueLists only ViewOnly/Modifiable/NoAccess. Neither is ever
    # "Custom", so no per-item list exists to parse and its shape has never been
    # observed. The parser deliberately does not guess at one.
    "scripts": {"value": "ExecutableOnly", "allow_creation": "False"},
    "value_lists": {"value": "ViewOnly", "allow_creation": "False"},
}

_FULL_ACCESS_ATTRS = {
    "id": "1",
    "menu": "All",
    "printing": "True",
    "exporting": "True",
    "idleDisconnect": "False",
    "manageAccounts": "True",
    "managedExtended": "True",
    "allowModifyPassword": "True",
    "overrideValidationWarning": "True",
    "comment": "access to everything",
}

_MANAGER_ATTRS = {
    "id": "2",
    "menu": "All",
    "printing": "True",
    "exporting": "True",
    "idleDisconnect": "True",
    "manageAccounts": "False",
    "managedExtended": "False",
    "allowModifyPassword": "True",
    "overrideValidationWarning": "False",
    "comment": "",
}

EXPECTED_PRIVILEGES = [
    dict(
        {
            "name": "[Full Access]",
            "source_files": [SRC],
            "attrs_by_file": {SRC: _FULL_ACCESS_ATTRS},
            "access_by_file": {SRC: _FULL_ACCESS_ACCESS},
            "access_source_file": SRC,
        },
        **_FULL_ACCESS_ATTRS,
        **_FULL_ACCESS_ACCESS,
    ),
    dict(
        {
            "name": "Manager",
            "source_files": [SRC],
            "attrs_by_file": {SRC: _MANAGER_ATTRS},
            "access_by_file": {SRC: _MANAGER_ACCESS},
            "access_source_file": SRC,
        },
        **_MANAGER_ATTRS,
        **_MANAGER_ACCESS,
    ),
]

EXPECTED_CUSTOM_FUNCTIONS = [
    {"id": "1", "name": "TrimAll2", "parameters": "theValue", "visible": "True",
     "calculation": 'Trim ( Substitute ( theValue ; "  " ; " " ) )', "source_file": SRC}
]

EXPECTED_CONDITIONAL_FORMATTING = [
    {
        "object_name": "Juvenile_flag",
        "object_type": "Field",
        "condition_type": "0",
        "flags": "3",
        "formula": "Intakes::Juvenile_boolean",
        "format_css": "self:normal .self { color: rgba(85.098%,4.31373%,0%,1); }",
        "layout": "Intake Detail",
        "layout_id": "11",
        "source_file": SRC,
    }
]

EXPECTED_HIDE_CONDITIONS = [
    {
        # 92.5% of gold objects carry no name attribute. "" is correct here.
        "object_name": "",
        "object_type": "Button",
        # Truncating this to "Get ( AccountName ) ≠" is the defect that got
        # read as "hardcoded account name (stripped by DDR)". It is a row-level
        # author-ownership check.
        "formula": "Get ( AccountName ) ≠ Case_Notes::log_created_account",
        "layout": "Intake Detail",
        "layout_id": "11",
        "source_file": SRC,
    },
    {
        "object_name": "stale_banner",
        "object_type": "Text",
        # Produced by the chunk-walker fallback, not by <Calculation> text.
        "formula": "IsEmpty ( LINE_ITEMS_Restitution::Balance_Due )",
        "layout": "Restitution Report",
        "layout_id": "12",
        "source_file": SRC,
    },
]


class GoldenFixtureTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.ddr, cls.results, cls.stdout, cls.stderr = parse_fixture()

    # ─── whole-output golden comparison ─────────────────────────────────

    def test_golden_output_matches_exactly(self):
        for key, expected in (
            ("tables", EXPECTED_TABLES),
            ("occurrences", EXPECTED_OCCURRENCES),
            ("relationships", EXPECTED_RELATIONSHIPS),
            ("layouts", EXPECTED_LAYOUTS),
            ("scripts", EXPECTED_SCRIPTS),
            ("value_lists", EXPECTED_VALUE_LISTS),
            ("accounts", EXPECTED_ACCOUNTS),
            ("privileges", EXPECTED_PRIVILEGES),
            ("custom_functions", EXPECTED_CUSTOM_FUNCTIONS),
            ("conditional_formatting", EXPECTED_CONDITIONAL_FORMATTING),
            ("hide_conditions", EXPECTED_HIDE_CONDITIONS),
        ):
            with self.subTest(spec=key):
                self.assertEqual(self.results[key], expected)

    # ─── D1: get_calculation ────────────────────────────────────────────

    def test_d1_calculation_reads_direct_text_not_a_Text_child(self):
        """<Calculation> holds the formula as direct text; 0/36,051 gold calcs
        have a <Text> child. Any code reading Calculation/Text is dead."""
        field = self.results["tables"][0]["fields"][0]
        self.assertEqual(field["auto_enter"]["calculation"], "Get ( UUID )")

    def test_d1_fieldref_operands_survive_in_formulas(self):
        """A FieldRef chunk's payload is a nested <Field table= name=/> with
        empty .text. Joining only .text deletes every field operand and leaves a
        syntactically plausible, semantically wrong formula."""
        hide = {h["object_type"]: h["formula"] for h in self.results["hide_conditions"]}

        self.assertEqual(
            hide["Button"], "Get ( AccountName ) ≠ Case_Notes::log_created_account",
            "field operand deleted from a hide formula -- this is D1, the defect "
            "no count check can see",
        )
        # Belt and braces: the truncated form must never be what we emit.
        self.assertNotEqual(hide["Button"], "Get ( AccountName ) ≠")
        self.assertIn("Case_Notes::log_created_account", hide["Button"])

    def test_d1_chunk_walker_fallback_resolves_fields_and_strips_indentation(self):
        """The fallback walker is where the operand deletion lived. It must
        render <Field> as Table::field, and must NOT leak the pretty-print
        indentation that surrounds a FieldRef's nested child."""
        formula = next(h["formula"] for h in self.results["hide_conditions"]
                       if h["object_name"] == "stale_banner")
        self.assertEqual(formula, "IsEmpty ( LINE_ITEMS_Restitution::Balance_Due )")

    def test_d1_single_fieldref_calculation_is_not_formula_less(self):
        """When a calculation is a SINGLE FieldRef chunk the whole formula used
        to render to whitespace, get_calculation returned None, and the field
        surfaced as having no formula. That is what produced the 8 false 'drop'
        recommendations -- including on Line_Items::Allocations, whose real
        formula excludes voided rows."""
        calc_field = self.results["tables"][0]["calculated"][0]
        self.assertIn(
            "calculation", calc_field,
            "a Calculated field emitted with NO calculation key -- downstream "
            "explorers read this as 'formula was removed' and recommend dropping "
            "the field",
        )
        self.assertEqual(calc_field["calculation"], "LINE_ITEMS_Restitution::Balance_Due")

    def test_d1_row_level_security_predicate_survives(self):
        manager = next(p for p in self.results["privileges"] if p["name"] == "Manager")
        intakes = manager["records"]["tables"][0]
        self.assertEqual(intakes["view_calculation"],
                         "not Investigation_boolean and not isAdmin_Private")

    # ─── D2: ungrouped scripts ──────────────────────────────────────────

    def test_d2_root_level_script_is_not_dropped(self):
        """ScriptCatalog holds scripts at its root as well as inside Groups.
        Descending only into Groups dropped 1,860 of 17,870 scripts repo-wide --
        startup, login, routing and case-closure logic, with their bodies."""
        names = [s["name"] for s in self.results["scripts"]]
        self.assertIn("Open", names, "root-level script dropped -- this is D2")
        root = next(s for s in self.results["scripts"] if s["name"] == "Open")
        self.assertEqual(root["group"], "")
        # The point is that the BODY survives, not the exact count -- the golden
        # comparison pins the body. Asserting an exact count here just means this
        # test breaks every time the fixture gains a step, which teaches people to
        # edit the number rather than read the failure.
        self.assertGreaterEqual(len(root["steps"]), 2,
                                "root script recovered but body empty")

    def test_d2_grouped_script_keeps_its_group_path(self):
        grouped = next(s for s in self.results["scripts"]
                       if s["name"] == "Set is_Closed from GJ Status")
        self.assertEqual(grouped["group"], "Modules/Grand Jury")

    # ─── separators ─────────────────────────────────────────────────────

    def test_separator_scripts_are_filtered_at_root_and_in_groups(self):
        """FileMaker '-' pseudo-scripts are menu separators. They were dropped at
        root (with the real scripts) and KEPT in groups -- 91 junk rows in gold's
        shipped list. Both root and grouped separators must go."""
        self.assertEqual([s["name"] for s in self.results["scripts"]],
                         ["Open", "Set is_Closed from GJ Status"])

    def test_separator_layout_is_filtered(self):
        self.assertEqual([l["name"] for l in self.results["layouts"]],
                         ["Intake Detail", "Restitution Report"])

    # ─── D3: conditional formatting ─────────────────────────────────────

    def test_d3_conditional_formatting_is_extracted(self):
        """<Condition> is nested under <Item>; findall is non-recursive, so a
        direct lookup returned [] for 100% of blocks. All 13 offices shipped a
        2-byte 09_conditional_formatting.json."""
        self.assertEqual(len(self.results["conditional_formatting"]), 1,
                         "conditional formatting extracted 0 rules -- this is D3")

    def test_d3_conditional_formatting_reads_op_flags_and_localcss(self):
        """Three more things were wrong at once: the attribute is `op` not
        `type`, <Format> is Condition's SIBLING under <Item>, and the payload is
        Styles/LocalCSS *text* -- reading child tags yielded the constant
        ['Styles']."""
        rule = self.results["conditional_formatting"][0]
        self.assertEqual(rule["condition_type"], "0")
        self.assertEqual(rule["flags"], "3")
        self.assertEqual(rule["formula"], "Intakes::Juvenile_boolean")
        self.assertEqual(rule["format_css"],
                         "self:normal .self { color: rgba(85.098%,4.31373%,0%,1); }")

    # ─── D4: privilege sets ─────────────────────────────────────────────

    def test_d4_privilege_set_contents_are_extracted(self):
        """The parser used to emit every privilege set as bare {id, name}: no
        per-table grants, no field-level restrictions, no row-level predicates.
        The RBAC design was then built from hide formulas instead."""
        manager = next(p for p in self.results["privileges"] if p["name"] == "Manager")
        self.assertNotEqual(
            set(manager) - {"source_files", "attrs_by_file", "access_by_file",
                            "access_source_file"},
            {"id", "name"},
            "privilege set emitted as bare {id, name} -- this is D4",
        )
        self.assertEqual(manager["records"]["value"], "Custom")
        self.assertEqual([t["table"] for t in manager["records"]["tables"]],
                         ["Intakes", "[Any New Table]"])

    def test_d4_field_level_access_restrictions_are_extracted(self):
        manager = next(p for p in self.results["privileges"] if p["name"] == "Manager")
        intakes = manager["records"]["tables"][0]
        self.assertEqual(intakes["field_access"], "Limited")
        self.assertEqual(intakes["fields"],
                         [{"field": "ID", "restriction": "ViewOnly"},
                          {"field": "Restitution_Owed_Display", "restriction": "Modifiable"}])

    def test_d4_privilege_set_attributes_are_captured(self):
        manager = next(p for p in self.results["privileges"] if p["name"] == "Manager")
        for attr in ("menu", "printing", "exporting", "idleDisconnect", "manageAccounts",
                     "managedExtended", "allowModifyPassword", "overrideValidationWarning",
                     "comment"):
            self.assertIn(attr, manager)

    def test_d4_merge_security_keeps_the_access_block(self):
        """merge_security used to dedup privilege sets by name and keep the first
        occurrence -- which discarded the recovered model, because the files sort
        UI-first and the UI file carries only a coarse grant."""
        manager = next(p for p in self.results["privileges"] if p["name"] == "Manager")
        self.assertEqual(manager["access_source_file"], SRC)
        self.assertIn("tables", manager["access_by_file"][SRC]["records"])

    # ─── D6: buttons ────────────────────────────────────────────────────

    def test_d6_plain_buttonobj_is_extracted(self):
        """Only GroupButtonObj was handled. 1,617 Step-bearing ButtonObj were
        ignored in gold alone; 24,018 across the swept offices."""
        layout = self.results["layouts"][0]
        scripts = {b["script"] for b in layout["buttons"]}
        self.assertIn("Send Officer Dispositions", scripts,
                      "plain ButtonObj ignored -- this is D6")

    def test_d6_nested_step_in_groupbuttonobj_is_extracted(self):
        """1,140 of gold's 5,256 GroupButtonObj are containers whose Step sits a
        level deeper than el.find('Step') looks."""
        layout = self.results["layouts"][0]
        nested = [b for b in layout["buttons"] if b["button_type"] == "GroupButtonObj"]
        self.assertEqual(len(nested), 1,
                         "GroupButtonObj container's nested Step missed -- this is D6")
        self.assertEqual(nested[0]["script"], "Set is_Closed from GJ Status")

    def test_d6_buttons_are_deduped_without_collapsing_distinct_actions(self):
        layout = self.results["layouts"][0]
        self.assertEqual(len(layout["buttons"]), 2)

    # ─── D7: StepText ───────────────────────────────────────────────────

    def test_d7_step_text_is_emitted(self):
        """The structured params are an allow-list of ~10 child tags out of ~102
        that occur, so 62% of gold steps emitted no params at all. StepText is
        FileMaker's own faithful rendering and was never read."""
        for script in self.results["scripts"]:
            for step in script["steps"]:
                self.assertIn("step_text", step,
                              f"step {step['name']!r} lost its StepText -- this is D7")

    def test_d7_step_text_is_the_only_payload_of_an_unstructured_step(self):
        end_if = self.results["scripts"][1]["steps"][1]
        self.assertNotIn("params", end_if)
        self.assertEqual(end_if["step_text"], "End If")

    # ─── D5: malformed input ────────────────────────────────────────────

    def test_d5_control_characters_are_stripped_and_warned_about(self):
        """FileMaker emits raw C0 control chars inside <Data> (8 x 0x1E in
        SCDA_Main). expat rejects the file; the old code swallowed the exception
        and dropped 90% of that office's scripts with no warning and exit 0."""
        with open(FIXTURE, encoding="utf-16") as fh:
            src = fh.read()
        injected = src.replace("Primary key", "Primary\x1ekey", 1)
        self.assertIn("\x1e", injected, "fixture changed; injection point is gone")

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "dirty.xml")
            with open(path, "w", encoding="utf-16") as fh:
                fh.write(injected)

            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                tree = parse_ddr.parse_xml(path)

            self.assertEqual(tree.getroot().tag, "FMPReport")
            self.assertIn("stripped 1 invalid control char", err.getvalue(),
                          "control char stripped silently -- a whole-file drop must "
                          "never be exit-0 and unannounced")

    def test_d5_unparseable_file_warns_rather_than_vanishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "broken.xml"), "w", encoding="utf-16") as fh:
                fh.write('<?xml version="1.0"?>\n<FMPReport><File name="x"></FMPReport>')

            err = io.StringIO()
            out = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                try:
                    parse_ddr.find_ddr_reports(tmp)
                except SystemExit:
                    pass
            self.assertIn("could not parse broken.xml", err.getvalue(),
                          "an unparseable DDR file vanished silently -- this is D5")

    # ─── verify() self-check ────────────────────────────────────────────

    def test_verify_self_check_reconciles(self):
        self.assertEqual(self.ddr.verify(), [],
                         "the parser's own count self-check does not reconcile "
                         "against the fixture")

    def test_verify_does_not_inflate_script_count_via_references(self):
        """<Script> also appears inside steps and buttons as a *reference*. The
        fixture contains 3 such references. A verify() that used iter() would
        count them and inflate the total."""
        self.assertEqual(self.ddr._count_catalog("ScriptCatalog", "Script",
                                                 skip_separators=True), 2)

    # ─── REDACTION ──────────────────────────────────────────────────────

    def test_no_secret_literal_reaches_the_parsed_output(self):
        """The parser is the boundary between the gitignored raw DDR and the
        COMMITTED specs. Nothing that looks like a credential value may cross it.

        This is the backstop for the whole redaction feature: it greps the entire
        emitted structure rather than checking a field, so a secret arriving via
        some future param name still trips it."""
        blob = json.dumps(self.results)
        for leaked in ("hunter2-should-not-ship", "AKIAIOSFODNN7EXAMPLE"):
            self.assertNotIn(leaked, blob,
                             f"{leaked!r} reached the parsed specs -- the specs are "
                             f"committed to git, the raw DDR is not")

    def test_redaction_preserves_structure(self):
        """Mask the value, keep the shape. An analyst still has to see THAT a step
        sets an SMTP password, and where, to plan the migration."""
        step = self._step("90")
        self.assertEqual(step["step_text"],
                         'Set Variable [ $password ; Value: "<REDACTED>" ]')
        self.assertEqual(step["params"]["variable"], "$password")

    def test_redaction_catches_secret_named_by_its_target_not_its_value(self):
        """Set Variable [ $password ; Value: "hunter2" ] -- <Value> is bare, so
        keyword-adjacency cannot see it. The variable NAME is the only signal.
        This leaked when the redactor first shipped; the fixture caught it."""
        self.assertEqual(self._step("90")["params"]["value"], '"<REDACTED>"')

    def test_redaction_catches_secret_inside_a_calculation(self):
        self.assertEqual(self._step("91")["params"]["calculation"],
                         'Let ( $api_key = "<REDACTED>" ; $api_key )')

    def test_redaction_does_not_eat_business_logic(self):
        """A quoted string that merely CONTAINS a credential word is not a secret,
        and unquoted field refs never are. Over-redacting silently destroys logic
        -- the same failure mode as the bug this parser was audited for, pointed
        the other way."""
        step = self._step("92")
        self.assertIn('Intakes::Kind = "Token"', step["step_text"])
        self.assertNotIn("REDACTED", step["step_text"])

    def _step(self, step_id):
        for script in self.results["scripts"]:
            for step in script.get("steps", []):
                if step["id"] == step_id:
                    return step
        self.fail(f"step {step_id} missing from fixture output")


class _StubDDR:
    """The slice of DDRFile that merge_security reads. The fixture is one file,
    so it cannot show what happens when two files share a privilege-set name."""

    def __init__(self, source_file, privileges):
        self.source_file = source_file
        self.accounts = []
        self.external_data_sources = []
        self.privileges = [dict(p, source_file=source_file) for p in privileges]


class MultiFileSecurityMergeTest(unittest.TestCase):
    """merge_security used to take a privilege set's id and flags from the first
    file and its access blocks plus access_source_file from the richest one. The
    top-level record then matched no file: in a real six-file DDR a set that is
    id="10" allowModifyPassword="True" in the file named by access_source_file
    came out as id 11, allowModifyPassword False -- the first file's values."""

    UI = "A.fmp12"    # sorts first, coarse grant
    DATA = "B.fmp12"  # the real model

    UI_SET = {"id": "11", "name": "SetX", "allowModifyPassword": "False", "menu": "Minimal",
              "records": {"value": "CreateEditDelete"}}
    DATA_SET = {"id": "10", "name": "SetX", "allowModifyPassword": "True", "menu": "All",
                "records": {"value": "Custom", "tables": [{"name": "T1"}, {"name": "T2"}]}}

    def _merge(self, *files):
        _, privileges = parse_ddr.DDRMerger(list(files)).merge_security()
        self.assertEqual(len(privileges), 1)
        return privileges[0]

    def test_top_level_id_and_flags_come_from_access_source_file(self):
        p = self._merge(_StubDDR(self.UI, [self.UI_SET]), _StubDDR(self.DATA, [self.DATA_SET]))
        self.assertEqual(p["access_source_file"], self.DATA)
        self.assertEqual((p["id"], p["allowModifyPassword"], p["menu"]), ("10", "True", "All"))
        self.assertEqual(p["records"], self.DATA_SET["records"])

    def test_every_files_id_and_flags_are_kept(self):
        p = self._merge(_StubDDR(self.UI, [self.UI_SET]), _StubDDR(self.DATA, [self.DATA_SET]))
        self.assertEqual(p["attrs_by_file"], {
            self.UI: {"id": "11", "allowModifyPassword": "False", "menu": "Minimal"},
            self.DATA: {"id": "10", "allowModifyPassword": "True", "menu": "All"},
        })

    def test_top_level_does_not_depend_on_file_order(self):
        forward = self._merge(_StubDDR(self.UI, [self.UI_SET]), _StubDDR(self.DATA, [self.DATA_SET]))
        reverse = self._merge(_StubDDR(self.DATA, [self.DATA_SET]), _StubDDR(self.UI, [self.UI_SET]))
        for key in ("id", "allowModifyPassword", "menu", "records", "access_source_file"):
            self.assertEqual(forward[key], reverse[key], key)

    def test_same_name_without_access_keeps_both_files_flags(self):
        """Two files with an unrelated [Guest], same id, different flags."""
        a = {"id": "4", "name": "[Guest]", "printing": "False"}
        b = {"id": "4", "name": "[Guest]", "printing": "True"}
        p = self._merge(_StubDDR(self.UI, [a]), _StubDDR(self.DATA, [b]))
        self.assertEqual(p["attrs_by_file"][self.UI]["printing"], "False")
        self.assertEqual(p["attrs_by_file"][self.DATA]["printing"], "True")
        self.assertEqual(p["access_source_file"], self.UI)
        self.assertEqual(p["printing"], "False")


class _StubFile:
    """The slice of DDRFile that external-reference resolution reads."""

    def __init__(self, source_file, sources=(), occurrences=()):
        self.source_file = source_file
        self.external_data_sources = [
            dict(type="filemaker", id=str(i), source_file=source_file, **s)
            for i, s in enumerate(sources, 1)]
        self.table_occurrences = [dict(o, source_file=source_file) for o in occurrences]


def _ext_to(name, ref):
    return {"id": "1", "name": name, "base_table": name, "base_table_id": "1",
            "external_file_reference": {"name": ref, "id": "1"}}


class ExternalReferenceResolutionTest(unittest.TestCase):
    """Issues #2, #5, #3: references resolved by the data-source alias, in set
    order, and an unresolved external TO looked like a local one."""

    def test_fixture_pathList_attribute_is_read(self):
        ddr, _, _, _ = parse_fixture()
        self.assertEqual(ddr.external_data_sources[0]["paths"], ["file:Mini_Schema"])

    def test_pathList_entries_split_without_breaking_spaced_names(self):
        self.assertEqual(
            parse_ddr.split_path_list("file:My Data fmnet:/*/My Data\nfilemac:/HD/x/Data.fmp12"),
            ["file:My Data", "fmnet:/*/My Data", "filemac:/HD/x/Data.fmp12"])
        self.assertEqual(parse_ddr.path_target_name("fmnet:/*/My Data"), "My Data")

    def test_every_real_pathList_shape_splits_to_one_entry_and_the_right_name(self):
        """Shapes seen in real multi-file DDRs, with placeholder names. Each
        real pathList held a single entry."""
        shapes = [
            ("file:Name", "Name"),
            ("file:Name Name", "Name Name"),
            ("file:Name_9.fmp12", "Name_9.fmp12"),
            ("fmnet:/host/Name", "Name"),
            ("fmnet:/host.example.test/Name_Name", "Name_Name"),
            ("fmnet:/1.2.3.4/Name", "Name"),
            ("fmnet:/1.2.3.4/Name Name Name", "Name Name Name"),
            ("filewin:/C:/dir/dir/dir/Name_Name", "Name_Name"),
            ("filemac:/Disk Name/dir/dir/dir/Name", "Name"),
        ]
        for value, target in shapes:
            with self.subTest(value=value):
                self.assertEqual(parse_ddr.split_path_list(value), [value])
                self.assertEqual(parse_ddr.path_target_name(value), target)

    def test_path_without_a_scheme_resolves_by_its_last_segment(self):
        for value in ("Data", "dir/dir/Data.fmp12", "dir\\Data", "fmnet:/host/Data/"):
            with self.subTest(value=value):
                self.assertEqual(parse_ddr.path_target_name(value).split(".")[0], "Data")
        ui = _StubFile("UI.fmp12", [{"name": "Alias", "paths": ["dir/Data"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12")])
        self.assertEqual(m._resolve_external_ref("UI.fmp12", "Alias"), "Data.fmp12")

    def test_reference_paths_reads_all_three_shapes(self):
        import xml.etree.ElementTree as ET
        shapes = {
            '<FileReference id="1" name="A" pathList="file:Data"/>': ["file:Data"],
            '<FileReference id="1" name="A"><PathList><Path>file:Data</Path>'
            '<Path>fmnet:/host/Data</Path></PathList></FileReference>': ["file:Data", "fmnet:/host/Data"],
            '<FileReference id="1" name="A"><UniversalPathList>file:Data</UniversalPathList>'
            '</FileReference>': ["file:Data"],
        }
        for xml, paths in shapes.items():
            with self.subTest(xml=xml):
                self.assertEqual(parse_ddr.reference_paths(ET.fromstring(xml)), paths)

    def test_link_attribute_is_kept_on_the_data_source(self):
        import xml.etree.ElementTree as ET
        ddr = parse_ddr.DDRFile.__new__(parse_ddr.DDRFile)
        ddr.source_file = "UI.fmp12"
        ddr.file_el = ET.fromstring(
            '<File><ExternalDataSourcesCatalog>'
            '<FileReference id="1" link="x" name="A" pathList="file:Data"/>'
            '<FileReference id="2" name="B" pathList="file:Other"/>'
            '</ExternalDataSourcesCatalog></File>')
        with contextlib.redirect_stdout(io.StringIO()):
            a, b = ddr._parse_external_data_sources()
        self.assertEqual((a["link"], a["paths"]), ("x", ["file:Data"]))
        self.assertNotIn("link", b)

    def test_own_paths_win_over_the_data_source_of_that_name(self):
        ui = _StubFile("UI.fmp12", [{"name": "Data", "paths": ["file:Data"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12"), _StubFile("Archive.fmp12")])
        self.assertEqual(m.resolve_external_ref_info("UI.fmp12", "Data", ["file:Archive"])["resolved_to"],
                         "Archive.fmp12")
        self.assertEqual(m.resolve_external_ref_info("UI.fmp12", "Data", ["file:Gone"])["resolved_to"],
                         "Data.fmp12")

    def test_multi_entry_pathList_keeps_spaced_names_and_drive_letters(self):
        value = "file:Name Name\nfmnet:/1.2.3.4/Name Name filewin:/C:/dir name/Name"
        self.assertEqual(parse_ddr.split_path_list(value),
                         ["file:Name Name", "fmnet:/1.2.3.4/Name Name", "filewin:/C:/dir name/Name"])

    def test_alias_resolves_through_its_path(self):
        ui = _StubFile("UI.fmp12", [{"name": "Backend", "paths": ["file:Data"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12")])
        self.assertEqual(m._resolve_external_ref("UI.fmp12", "Backend"), "Data.fmp12")
        self.assertEqual(m.resolve_external_ref_info("UI.fmp12", "Backend")["resolved_via"], "path")

    def test_path_beats_a_file_with_the_alias_name(self):
        ui = _StubFile("UI.fmp12", [{"name": "Data", "paths": ["file:Archive"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12"), _StubFile("Archive.fmp12")])
        self.assertEqual(m._resolve_external_ref("UI.fmp12", "Data"), "Archive.fmp12")

    def test_later_path_entry_is_tried_when_the_first_does_not_match(self):
        ui = _StubFile("UI.fmp12", [{"name": "B", "paths": ["file:Gone", "fmnet:/*/Data"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12")])
        self.assertEqual(m._resolve_external_ref("UI.fmp12", "B"), "Data.fmp12")

    def test_name_fallback_is_marked(self):
        ui = _StubFile("UI.fmp12", [{"name": "Data", "paths": ["file:Gone"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12")])
        self.assertEqual(m.resolve_external_ref_info("UI.fmp12", "Data"),
                         {"resolved_to": "Data.fmp12", "resolved_via": "name_fallback"})

    def test_ambiguous_match_is_reported_not_picked(self):
        ui = _StubFile("UI.fmp12", [{"name": "X", "paths": ["file:DATA"]}])
        m = parse_ddr.DDRMerger([ui, _StubFile("data.fp7"), _StubFile("Data.fmp12")])
        info = m.resolve_external_ref_info("UI.fmp12", "X")
        self.assertIsNone(info["resolved_to"])
        self.assertEqual(info["ambiguous_candidates"], ["Data.fmp12", "data.fp7"])

    def test_resolution_does_not_depend_on_hash_seed(self):
        import subprocess
        code = ("import sys; sys.path.insert(0, %r); sys.path.insert(0, %r); "
                "import parse_ddr, test_parse_ddr as t; "
                "m = parse_ddr.DDRMerger([t._StubFile('UI.fmp12', [{'name': 'DATA'}]), "
                "t._StubFile('Data.fmp12'), t._StubFile('data.fp7')]); "
                "print(m.resolve_external_ref_info('UI.fmp12', 'DATA'))"
                % (os.path.dirname(parse_ddr.__file__), os.path.dirname(os.path.abspath(__file__))))
        outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                               env=dict(os.environ, PYTHONHASHSEED=str(seed))).stdout
                for seed in range(1, 7)}
        self.assertEqual(len(outs), 1, outs)
        self.assertIn("ambiguous_candidates", outs.pop())

    def test_unresolved_external_to_is_marked(self):
        ui = _StubFile("UI.fmp12", [{"name": "Gone", "paths": ["file:Gone"]}],
                       [_ext_to("Contacts", "Gone")])
        to = parse_ddr.DDRMerger([ui]).merge_table_occurrences()[0]
        self.assertEqual((to["external"], to["resolved_source_file"], to["unresolved"]),
                         (True, None, True))

    def test_resolved_external_to_is_marked(self):
        ui = _StubFile("UI.fmp12", [{"name": "Backend", "paths": ["file:Data"]}],
                       [_ext_to("Contacts", "Backend")])
        to = parse_ddr.DDRMerger([ui, _StubFile("Data.fmp12")]).merge_table_occurrences()[0]
        self.assertEqual((to["external"], to["resolved_source_file"], to["resolved_via"]),
                         (True, "Data.fmp12", "path"))
        self.assertNotIn("unresolved", to)


TWO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "two_file")


class CrossFileScriptCallTest(unittest.TestCase):
    """UI.fmp12 calls Save in Backend.fmp12 from a script step and from a
    button. Backend.fmp12 has two scripts named Save (ids 21 and 22). Buttons
    used to drop their FileReference, so the button call resolved against
    UI.fmp12 and never reached cross_file_references (#4). Every script
    reference used to drop the script id, so the two Saves could not be told
    apart (#8). A second button calls a file with no DDR (Gone)."""

    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            cls.files = []
            for name in ("UI.xml", "Backend.xml"):
                ddr = parse_ddr.DDRFile(os.path.join(TWO_FILE, name))
                ddr.parse_all()
                cls.files.append(ddr)
            cls.merger = parse_ddr.DDRMerger(cls.files)
            cls.topology = cls.merger.merge_topology()
        cls.calls = cls.topology["cross_file_references"]["script_calls"]

    def test_step_keeps_the_target_script_id(self):
        params = self.files[0].scripts[0]["steps"][0]["params"]
        self.assertEqual((params["script"], params["script_id"], params["external_file"]),
                         ("Save", "21", "Backend"))

    def test_button_keeps_the_file_reference_and_script_id(self):
        button = self.files[0].layouts[0]["buttons"][0]
        self.assertEqual((button["script"], button["script_id"], button["external_file"]),
                         ("Save", "22", "Backend"))
        self.assertEqual((button["object_key"], button["object_name"]), ("7", "btnSave"))

    def test_step_call_row_carries_step_and_script_ids(self):
        row = next(c for c in self.calls if c["origin"] == "script_step")
        self.assertEqual(row, {
            "origin": "script_step", "from_file": "UI.fmp12",
            "script": "Go", "script_id": "3", "step": "Perform Script", "step_line": 1,
            "calls_script": "Save", "calls_script_id": "21",
            "external_ref": "Backend", "resolved_to": "Backend.fmp12",
            "resolved_via": "path", "matched_path": "file:Backend",
        })

    def test_button_call_row_is_marked_and_resolved_like_a_step(self):
        row = next(c for c in self.calls if c["origin"] == "button" and c["object_key"] == "7")
        self.assertEqual(row, {
            "origin": "button", "from_file": "UI.fmp12",
            "layout": "Home", "layout_id": "5", "button_type": "ButtonObj",
            "object_key": "7", "object_name": "btnSave", "step": "Perform Script",
            "calls_script": "Save", "calls_script_id": "22",
            "external_ref": "Backend",
            "resolved_to": self.merger._resolve_external_ref("UI.fmp12", "Backend"),
            "resolved_via": "path", "matched_path": "file:Backend",
        })
        self.assertEqual(row["resolved_to"], "Backend.fmp12")

    def test_open_file_button_is_not_a_script_call(self):
        """In the real DDRs every button with a FileReference was Open File.
        Those reached script_calls as calls with no script."""
        self.assertEqual(sorted(c["object_key"] for c in self.calls if c["origin"] == "button"),
                         ["7", "8"])

    def test_unresolved_button_call_is_reported(self):
        unresolved = [r for r in self.topology["unresolved_references"]
                      if r["type"] == "script_call"]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual((unresolved[0]["origin"], unresolved[0]["reference"]), ("button", "Gone"))

    def test_ambiguous_script_call_carries_its_candidates(self):
        """A second parsed file with the same name and another FM extension
        (Backend.fp7) makes Backend ambiguous. The step row and the button row
        both name the candidates instead of picking one."""
        twin = _StubFile("Backend.fp7")
        twin.filepath = "Backend.xml"
        twin.tables = twin.relationships = twin.layouts = twin.scripts = []
        twin.value_lists = twin.custom_functions = []
        twin.conditional_formatting = twin.hide_conditions = []
        with contextlib.redirect_stdout(io.StringIO()):
            topology = parse_ddr.DDRMerger(self.files + [twin]).merge_topology()
        rows = [c for c in topology["cross_file_references"]["script_calls"]
                if c["external_ref"] == "Backend"]
        self.assertEqual({c["origin"] for c in rows}, {"script_step", "button"})
        for row in rows:
            self.assertIsNone(row["resolved_to"])
            self.assertEqual(row["ambiguous_candidates"], ["Backend.fmp12", "Backend.fp7"])
        flagged = [r for r in topology["unresolved_references"]
                   if r["type"] == "script_call" and r.get("ambiguous_candidates")]
        self.assertEqual(len(flagged), len(rows))


class ValueListSourceTest(unittest.TestCase):
    """Only Custom and Field sources were parsed; any other source came out as
    a bare {id, name, source_file} (#7). UI.fmp12 has a Field list on an
    external TO and two synthetic External lists, one into a file with no DDR.
    No real DDR with an External source has been seen."""

    @classmethod
    def setUpClass(cls):
        cls.err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(cls.err):
            files = []
            for name in ("UI.xml", "Backend.xml"):
                ddr = parse_ddr.DDRFile(os.path.join(TWO_FILE, name))
                ddr.parse_all()
                files.append(ddr)
            merger = parse_ddr.DDRMerger(files)
            cls.vlists = {v["name"]: v for v in merger.merge_value_lists()}
            cls.topology = merger.merge_topology()

    def test_unknown_source_is_typed_flagged_and_warned(self):
        vl = self.vlists["Statuses"]
        self.assertEqual((vl["type"], vl["unparsed"]), ("external", True))
        self.assertEqual(vl["source"], {"attributes": {"value": "External"},
                                        "children": ["FileReference"]})
        self.assertIn("value list 'Statuses' has unsupported source 'External'",
                      self.err.getvalue())

    def test_external_file_is_kept_and_resolved(self):
        vl = self.vlists["Statuses"]
        self.assertEqual((vl["external_file"], vl["resolved_source_file"]),
                         ("Backend", "Backend.fmp12"))
        self.assertNotIn("unresolved", vl)

    def test_unresolved_external_file_is_reported(self):
        vl = self.vlists["Lost"]
        self.assertEqual((vl["resolved_source_file"], vl["unresolved"]), (None, True))
        refs = [r for r in self.topology["unresolved_references"] if r["type"] == "value_list"]
        self.assertEqual([r["reference"] for r in refs], ["Gone"])

    def test_field_list_resolves_base_tables_through_the_to_map(self):
        vl = self.vlists["Items"]
        self.assertEqual((vl["primary_table"], vl["primary_base_table"],
                          vl["primary_base_table_file"]),
                         ("Items_ext", "Items", "Backend.fmp12"))
        self.assertEqual((vl["secondary_base_table"], vl["secondary_base_table_file"]),
                         ("Prefs", "UI.fmp12"))



class DuplicateSourceFileTests(unittest.TestCase):
    """Two inputs with one DDR `File name` would mix their ids. Stop instead."""

    def test_same_file_name_in_two_inputs_stops_and_names_both(self):
        a = parse_ddr.DDRFile(FIXTURE)
        b = parse_ddr.DDRFile(FIXTURE)
        b.filepath = "/elsewhere/old_export.xml"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
            parse_ddr.check_unique_source_files([a, b])
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("Mini.fmp12", err.getvalue())
        self.assertIn(FIXTURE, err.getvalue())
        self.assertIn("/elsewhere/old_export.xml", err.getvalue())

    def test_distinct_file_names_pass(self):
        a = parse_ddr.DDRFile(FIXTURE)
        b = parse_ddr.DDRFile(FIXTURE)
        b.source_file = "Other.fmp12"
        parse_ddr.check_unique_source_files([a, b])


if __name__ == "__main__":
    unittest.main(verbosity=2)
