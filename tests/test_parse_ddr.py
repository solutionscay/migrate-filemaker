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
             "script": "Send Officer Dispositions",
             "description": "Perform Script [ “Send Officer Dispositions” ]"},
            # A GroupButtonObj container whose Step is one level deeper.
            {"action": "Perform Script", "button_type": "GroupButtonObj",
             "script": "Set is_Closed from GJ Status",
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
             "params": {"script": "Set User Information at Login"}},
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

EXPECTED_PRIVILEGES = [
    dict(
        {
            "id": "1",
            "name": "[Full Access]",
            "menu": "All",
            "printing": "True",
            "exporting": "True",
            "idleDisconnect": "False",
            "manageAccounts": "True",
            "managedExtended": "True",
            "allowModifyPassword": "True",
            "overrideValidationWarning": "True",
            "comment": "access to everything",
            "source_files": [SRC],
            "access_by_file": {SRC: _FULL_ACCESS_ACCESS},
            "access_source_file": SRC,
        },
        **_FULL_ACCESS_ACCESS,
    ),
    dict(
        {
            "id": "2",
            "name": "Manager",
            "menu": "All",
            "printing": "True",
            "exporting": "True",
            "idleDisconnect": "True",
            "manageAccounts": "False",
            "managedExtended": "False",
            "allowModifyPassword": "True",
            "overrideValidationWarning": "False",
            "comment": "",
            "source_files": [SRC],
            "access_by_file": {SRC: _MANAGER_ACCESS},
            "access_source_file": SRC,
        },
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
        "source_file": SRC,
    },
    {
        "object_name": "stale_banner",
        "object_type": "Text",
        # Produced by the chunk-walker fallback, not by <Calculation> text.
        "formula": "IsEmpty ( LINE_ITEMS_Restitution::Balance_Due )",
        "layout": "Restitution Report",
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
            set(manager) - {"source_files", "access_by_file", "access_source_file"},
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
