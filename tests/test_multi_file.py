"""Multi-file regression tests for scripts/parse_ddr.py and catalog_contract.py.

Run:  python3 -m unittest discover -s tests -v

The golden fixture is one file, so it cannot show cross-file defects. These
tests write a small synthetic solution of three files (UI, Data, Archive) and
run the real parser over it. Every name here is invented.

Each test names the issue it guards (#2 ... #10 in the repo's tracker). The
shapes follow real FileMaker 22 DDRs: data sources keep their path in a
`pathList` ATTRIBUTE, and a value list from another file keeps it in a
<UniversalPathList> child.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, os.pardir, "scripts")
sys.path.insert(0, SCRIPTS)

import catalog_contract  # noqa: E402
import parse_ddr  # noqa: E402

HEAD = '<?xml version="1.0"?>\n<FMPReport type="Report" version="22.0.7">\n<File name="{name}" path="example.test">\n'
TAIL = "</File>\n</FMPReport>\n"

UI = """
<BaseTableCatalog>
  <BaseTable id="1" records="0" comment="" name="Prefs"><FieldCatalog /></BaseTable>
</BaseTableCatalog>
<RelationshipGraph>
  <TableList>
    <Table id="1001" baseTableId="1" baseTable="Prefs" name="Prefs" />
    <Table id="1002" baseTableId="1" baseTable="Parcels" name="Parcels"><FileReference id="1" name="Backend" /></Table>
    <Table id="1003" baseTableId="1" baseTable="Parcels" name="Parcels_Old"><FileReference id="2" name="Data" /></Table>
    <Table id="1004" baseTableId="1" baseTable="Remote" name="Remote"><FileReference id="3" name="Elsewhere" /></Table>
  </TableList>
</RelationshipGraph>
<LayoutCatalog>
  <Layout width="600" includeInMenu="True" id="20" name="Home">
    <Table name="Prefs" />
    <Object type="Button" key="1" flags="0">
      <ButtonObj buttonFlags="0">
        <Step enable="True" id="1" name="Perform Script"><StepText>Perform Script [ "Save" from file: "Backend" ]</StepText><Script id="7" name="Save" /><FileReference id="1" name="Backend" /></Step>
      </ButtonObj>
    </Object>
  </Layout>
  <Layout width="600" includeInMenu="True" id="21" name="List">
    <Table name="Prefs" />
    <Object type="Text" key="1" flags="0" name="ribbon">
      <HideCondition findMode="False"><Calculation>1</Calculation></HideCondition>
    </Object>
  </Layout>
  <Layout width="600" includeInMenu="True" id="22" name="List">
    <Table name="Prefs" />
    <Object type="Text" key="1" flags="0" name="ribbon">
      <HideCondition findMode="False"><Calculation>1</Calculation></HideCondition>
    </Object>
  </Layout>
</LayoutCatalog>
<ValueListCatalog>
  <ValueList id="1" name="Stages">
    <Source value="External" />
    <External>
      <FileReference id="1" name="Backend"><UniversalPathList>file:Data</UniversalPathList></FileReference>
      <ValueList id="3" name="Stage Values" />
    </External>
  </ValueList>
  <ValueList id="2" name="Parcel Labels">
    <Source value="Field" />
    <PrimaryField show="True"><Field table="Parcels" name="label_text" /></PrimaryField>
  </ValueList>
</ValueListCatalog>
<ScriptCatalog>
  <Group id="100" name="Utilities">
    <Script includeInMenu="False" id="5" name="Go">
      <StepList>
        <Step enable="True" id="89" name="# (comment)"><StepText># call the backend</StepText></Step>
        <Step enable="True" id="1" name="Perform Script"><StepText>Perform Script [ "Save" from file: "Backend" ]</StepText><Script id="7" name="Save" /><FileReference id="1" name="Backend" /></Step>
        <Step enable="True" id="1" name="Perform Script"><StepText>Perform Script [ &lt;unknown&gt; ]</StepText><Script id="9" /></Step>
      </StepList>
    </Script>
  </Group>
</ScriptCatalog>
<ExternalDataSourcesCatalog>
  <FileReference id="1" pathList="file:Data" name="Backend" />
  <FileReference id="2" link="1" pathList="file:Archive" name="Data" />
  <FileReference id="3" pathList="fmnet:/host.example/Remote.fmp12" name="Elsewhere" />
</ExternalDataSourcesCatalog>
"""

DATA = """
<BaseTableCatalog>
  <BaseTable id="1" records="0" comment="" name="Parcels"><FieldCatalog /></BaseTable>
</BaseTableCatalog>
<RelationshipGraph><TableList><Table id="1001" baseTableId="1" baseTable="Parcels" name="Parcels" /></TableList></RelationshipGraph>
<ValueListCatalog>
  <ValueList id="3" name="Stage Values"><Source value="Custom" /><CustomValues><Text>Draft
Shipped</Text></CustomValues></ValueList>
</ValueListCatalog>
<ScriptCatalog>
  <Group id="100" name="Utilities">
    <Script includeInMenu="False" id="7" name="Save"><StepList /></Script>
  </Group>
  <Group id="101" name="Old">
    <Script includeInMenu="False" id="8" name="Save"><StepList /></Script>
  </Group>
</ScriptCatalog>
"""

ARCHIVE = """
<BaseTableCatalog>
  <BaseTable id="1" records="0" comment="" name="Parcels"><FieldCatalog /></BaseTable>
</BaseTableCatalog>
"""


def write_ddr(folder, filename, file_name, body):
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-16") as fh:
        fh.write(HEAD.format(name=file_name) + body + TAIL)
    return path


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
        result = fn(*args)
    return result, err.getvalue()


def parse(folder, files):
    """files: [(filename, File name, body)] -> (results, stderr)"""
    def run():
        ddrs = []
        for filename, name, body in files:
            d = parse_ddr.DDRFile(write_ddr(folder, filename, name, body))
            d.parse_all()
            ddrs.append(d)
        with tempfile.TemporaryDirectory() as out:
            return parse_ddr.DDRMerger(ddrs).merge_all(out)
    return quiet(run)


SOLUTION = [("UI_fmp12.xml", "UI.fmp12", UI), ("Data_fmp12.xml", "Data.fmp12", DATA),
            ("Archive_fmp12.xml", "Archive.fmp12", ARCHIVE)]


class MultiFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.results, cls.stderr = parse(cls.tmp.name, SOLUTION)
        cls.topo = cls.results["topology"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def to(self, name):
        return next(t for t in self.results["occurrences"] if t["name"] == name and t["source_file"] == "UI.fmp12")

    def eds(self, name):
        ui = next(f for f in self.topo["files"] if f["name"] == "UI.fmp12")
        return next(e for e in ui["external_data_sources"] if e["name"] == name)

    # ── #2: resolve through pathList, not through the data-source name ──────

    def test_2_pathList_attribute_is_read(self):
        self.assertEqual(self.eds("Backend")["paths"], ["file:Data"])
        self.assertEqual(self.eds("Elsewhere")["paths"], ["fmnet:/host.example/Remote.fmp12"])

    def test_2_alias_resolves_through_its_path(self):
        """A data source named "Backend" that points at file:Data."""
        self.assertEqual(self.eds("Backend")["resolved_source_file"], "Data.fmp12")
        self.assertEqual(self.eds("Backend")["resolved_by"], "path")
        self.assertEqual(self.to("Parcels")["resolved_source_file"], "Data.fmp12")

    def test_2_name_of_another_file_does_not_win_over_the_path(self):
        """A data source named "Data" that points at file:Archive."""
        self.assertEqual(self.eds("Data")["resolved_source_file"], "Archive.fmp12")
        self.assertEqual(self.to("Parcels_Old")["resolved_source_file"], "Archive.fmp12")

    def test_2_value_list_path_shape_is_read(self):
        vl = next(v for v in self.results["value_lists"] if v["name"] == "Stages")
        self.assertEqual(vl["external_paths"], ["file:Data"])

    def test_2_paths_with_spaces_and_several_entries(self):
        self.assertEqual(parse_ddr.path_target("file:Ledger Data"), "Ledger Data")
        self.assertEqual(parse_ddr.path_target("fmnet:/host.example/Ledger Data.fmp12"), "Ledger Data")
        self.assertEqual(parse_ddr.path_target("filewin:/C:/Shared/My.Jotter.fmp12"), "My.Jotter")
        el = parse_ddr.ET.fromstring('<FileReference pathList="file:Ledger Data fmnet:/h/Ledger Data" />')
        self.assertEqual(parse_ddr.reference_paths(el), ["file:Ledger Data", "fmnet:/h/Ledger Data"])

    # ── #3: unresolved external occurrences are marked ───────────────────────

    def test_3_external_occurrences_are_marked(self):
        for name in ("Parcels", "Parcels_Old", "Remote"):
            self.assertTrue(self.to(name)["external"], name)
        self.assertNotIn("external", self.to("Prefs"))

    def test_3_unresolved_external_occurrence_is_explicit(self):
        """Remote has base_table_id 1, the same id as the local table Prefs."""
        remote = self.to("Remote")
        self.assertIsNone(remote["resolved_source_file"])
        self.assertTrue(remote["unresolved"])
        self.assertIn("resolved_source_file", remote)  # null, not missing

    # ── #4: cross-file button calls are kept ─────────────────────────────────

    def test_4_button_keeps_the_file_reference(self):
        home = next(l for l in self.results["layouts"] if l["name"] == "Home")
        self.assertEqual(home["buttons"][0]["external_file"], "Backend")

    def test_4_button_call_is_in_cross_file_references(self):
        calls = [c for c in self.topo["cross_file_references"]["script_calls"] if c["via"] == "button"]
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]["layout"], calls[0]["layout_id"], calls[0]["calls_script"],
                          calls[0]["calls_script_id"], calls[0]["resolved_to"]),
                         ("Home", "20", "Save", "7", "Data.fmp12"))

    # ── #5: resolution does not depend on set order ──────────────────────────

    def test_5_ambiguous_match_is_reported_not_picked(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = ('<ExternalDataSourcesCatalog><FileReference id="1" name="DATA" /></ExternalDataSourcesCatalog>'
                    '<RelationshipGraph><TableList><Table id="1" baseTableId="1" baseTable="T" name="T">'
                    '<FileReference id="1" name="DATA" /></Table></TableList></RelationshipGraph>')
            results, err = parse(tmp, [("A_fmp12.xml", "Main.fmp12", body),
                                       ("B_fmp12.xml", "Data.fmp12", ""),
                                       ("C_fmp12.xml", "data.fp7", "")])
        amb = results["topology"]["ambiguous_references"]
        self.assertEqual(amb, [{"from_file": "Main.fmp12", "reference": "DATA",
                                "candidates": ["Data.fmp12", "data.fp7"]}])
        self.assertIsNone(results["occurrences"][0]["resolved_source_file"])
        self.assertIn("matches more than one parsed file", err)

    def test_5_output_is_the_same_under_any_hash_seed(self):
        """Run without -I/-E: they make Python ignore PYTHONHASHSEED, and the
        test would then pass with the bug still there."""
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "in")
            os.mkdir(src)
            # The occurrence makes the chosen file visible in the output.
            body = ('<ExternalDataSourcesCatalog><FileReference id="1" name="DATA" /></ExternalDataSourcesCatalog>'
                    '<RelationshipGraph><TableList><Table id="1" baseTableId="1" baseTable="T" name="T">'
                    '<FileReference id="1" name="DATA" /></Table></TableList></RelationshipGraph>')
            write_ddr(src, "A_fmp12.xml", "Main.fmp12", body)
            write_ddr(src, "B_fmp12.xml", "Data.fmp12", "")
            write_ddr(src, "C_fmp12.xml", "data.fp7", "")
            outputs, hashes = [], set()
            for seed in ("1", "2", "3", "4", "5", "6"):
                env = dict(os.environ, PYTHONHASHSEED=seed)
                out = os.path.join(tmp, "out" + seed)
                subprocess.run([sys.executable, os.path.join(SCRIPTS, "parse_ddr.py"), src, out],
                               env=env, capture_output=True, check=True)
                outputs.append(Path(out, "00_topology.json").read_text().replace(out, "OUT"))
                hashes.add(subprocess.run([sys.executable, "-c", "print(hash('x'))"], env=env,
                                          capture_output=True, text=True).stdout)
        self.assertGreater(len(hashes), 1, "PYTHONHASHSEED had no effect; the test proves nothing")
        self.assertEqual(len(set(outputs)), 1)

    # ── #6: two inputs with the same File name ───────────────────────────────

    def test_6_duplicate_file_name_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = parse_ddr.DDRFile(write_ddr(tmp, "UI_fmp12.xml", "UI.fmp12", ""))
            b = parse_ddr.DDRFile(write_ddr(tmp, "UI_old_fmp12.xml", "UI.fmp12", ""))
            with self.assertRaises(ValueError) as ctx:
                parse_ddr.DDRMerger([a, b])
        self.assertIn("UI_old_fmp12.xml", str(ctx.exception))

    def test_6_cli_exits_non_zero_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_ddr(tmp, "UI_fmp12.xml", "UI.fmp12", "")
            write_ddr(tmp, "UI_old_fmp12.xml", "UI.fmp12", "")
            run = subprocess.run([sys.executable, os.path.join(SCRIPTS, "parse_ddr.py"), tmp,
                                  os.path.join(tmp, "out")], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("same File name", run.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "out")))

    # ── #7: value lists from another file ────────────────────────────────────

    def test_7_external_value_list_is_not_bare(self):
        vl = next(v for v in self.results["value_lists"] if v["name"] == "Stages")
        self.assertEqual(vl["type"], "external")
        self.assertEqual(vl["external_file_reference"], {"name": "Backend", "id": "1"})
        self.assertEqual(vl["external_value_list"], {"id": "3", "name": "Stage Values"})
        self.assertEqual(vl["resolved_source_file"], "Data.fmp12")

    def test_7_field_list_on_an_external_occurrence_names_its_file(self):
        vl = next(v for v in self.results["value_lists"] if v["name"] == "Parcel Labels")
        self.assertEqual(vl["primary_table_source_file"], "Data.fmp12")

    def test_7_unknown_source_is_typed_and_warned(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = '<ValueListCatalog><ValueList id="1" name="X"><Source value="Future" /></ValueList></ValueListCatalog>'
            results, err = parse(tmp, [("A_fmp12.xml", "A.fmp12", body)])
        self.assertEqual(results["value_lists"][0]["type"], "future")
        self.assertIn("unsupported source", err)

    # ── #8: script references keep the script id ─────────────────────────────

    def test_8_step_reference_keeps_the_id(self):
        go = next(s for s in self.results["scripts"] if s["name"] == "Go")
        self.assertEqual(go["steps"][1]["params"]["script_id"], "7")

    def test_8_reference_with_an_id_and_no_name_is_not_lost(self):
        go = next(s for s in self.results["scripts"] if s["name"] == "Go")
        self.assertEqual(go["steps"][2]["params"], {"script": "", "script_id": "9"})

    def test_8_script_call_names_caller_line_and_target_id(self):
        call = next(c for c in self.topo["cross_file_references"]["script_calls"] if c["via"] == "script_step")
        self.assertEqual((call["script_id"], call["step_line"], call["calls_script_id"]), ("5", 2, "7"))

    # ── #9: rules carry the layout id ────────────────────────────────────────

    def test_9_rules_of_same_named_layouts_differ_by_layout_id(self):
        ids = sorted(r["layout_id"] for r in self.results["hide_conditions"] if r["layout"] == "List")
        self.assertEqual(ids, ["21", "22"])

    # ── #10: same-named groups in different files get different CSVs ─────────

    def test_10_same_folder_in_two_files_gets_two_output_files(self):
        rows = catalog_contract.flatten("scripts", self.results["scripts"])
        by_file = {}
        for script, row in zip(self.results["scripts"], rows):
            if script["group"] == "Utilities":
                by_file[script["source_file"]] = row["output_file"]
        self.assertEqual(set(by_file), {"UI.fmp12", "Data.fmp12"})
        self.assertNotEqual(by_file["UI.fmp12"], by_file["Data.fmp12"])

    def test_10_one_file_spec_keeps_its_names(self):
        one = [{"source_file": "A.fmp12", "id": "1", "name": "s", "group": ""},
               {"source_file": "A.fmp12", "id": "2", "name": "t", "group": "Utilities"}]
        rows = catalog_contract.flatten("scripts", one)
        self.assertEqual(rows[0]["output_file"], "_root.csv")
        self.assertEqual(rows[1]["output_file"],
                         catalog_contract.grouped_filename("Utilities", "Utilities"))

    def test_10_root_group_is_per_file_in_a_multi_file_spec(self):
        two = [{"source_file": "A.fmp12", "id": "1", "name": "s", "group": ""},
               {"source_file": "B.fmp12", "id": "1", "name": "s", "group": ""}]
        rows = catalog_contract.flatten("scripts", two)
        self.assertNotEqual(rows[0]["output_file"], rows[1]["output_file"])
        for r in rows:
            self.assertRegex(r["output_file"], r"^_root--[0-9a-f]{8}\.csv$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
