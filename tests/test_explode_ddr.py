import contextlib
import glob
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import explode_ddr  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "mini_ddr.xml")
TWO_FILE = os.path.join(HERE, "fixtures", "two_file")

# Synthetic DDR, one element per class of gap the exploder once had. No client data.
GAPS = """<?xml version="1.0" encoding="UTF-16"?>
<FMPReport type="Report" version="22.0.6">
<File name="Gaps.fmp12" path="host">
  <BaseTableCatalog>
    <BaseTable id="1" name="Shadow" records="42" shadow="True" comment="ESS copy">
      <DataSourceRef name="SQL" catalogName="db" schemaName="dbo" tableName="T"/>
      <FieldCatalog>
        <Field id="1" dataType="Text" fieldType="Normal" name="code">
          <AutoEnter allowEditing="True" calculation="False" constant="False" lookup="False">
            <ConstantData/>
            <Calculation table="Shadow">"old rule"</Calculation>
          </AutoEnter>
        </Field>
      </FieldCatalog>
    </BaseTable>
  </BaseTableCatalog>
  <RelationshipGraph>
    <TableList><Table id="100" baseTableId="1" baseTable="Shadow" name="Shadow"/></TableList>
    <RelationshipList/>
  </RelationshipGraph>
  <LayoutCatalog>
    <Layout id="5" name="Form">
      <Table id="100" name="Shadow"/>
      <Object type="Field" key="1" flags="0">
        <FieldObj numOfReps="1" displayType="3" flags="0">
          <Name>Shadow::code</Name>
          <ValueList>Codes</ValueList>
          <ExtendedAttributes fontHeight="10" graphicFormat="5">
            <NumFormat flags="2574" charStyle="0" currencySymbol="€" decimalDigits="2" trueString="Yes" falseString="No"/>
          </ExtendedAttributes>
          <DDRInfo>
            <Field name="code" id="1" repetition="2" maxRepetition="3" table="Shadow"/>
            <ValueList name="Codes" id="7"/>
          </DDRInfo>
        </FieldObj>
      </Object>
      <Object type="Text" key="2" flags="0">
        <TextObj flags="2"><CharacterStyleVector><Style><Data>line one\rline two</Data></Style></CharacterStyleVector></TextObj>
      </Object>
      <Object type="Button" key="3" flags="0">
        <ButtonObj buttonFlags="0">
          <Step enable="True" id="1" name="Perform Script"><StepText>Perform Script [ "Gone" ]</StepText><Script id="77" name="Gone"/></Step>
        </ButtonObj>
      </Object>
    </Layout>
  </LayoutCatalog>
  <ScriptCatalog>
    <Script id="9" name="Mail" runFullAccess="True" includeInMenu="False">
      <StepList>
        <Step enable="True" id="87" name="Show Custom Dialog">
          <StepText>Show Custom Dialog [ "Pick" ]</StepText>
          <Buttons>
            <Button CommitState="True"><Calculation>"Save"</Calculation></Button>
            <Button CommitState="False"><Calculation>"Discard"</Calculation></Button>
          </Buttons>
        </Step>
        <Step enable="True" id="74" name="Go to Related Record">
          <StepText>Go to Related Record [ From table: "Shadow"; New window ]</StepText>
          <Name><Calculation>"Detail window"</Calculation></Name>
        </Step>
        <Step enable="True" id="63" name="Send Mail">
          <StepText>Send Mail [ Send via SMTP Server; User Name: "mailer"; Password: "s3cretPa55" ]</StepText>
          <SMTPUserName><Calculation>"mailer"</Calculation></SMTPUserName>
          <SMTPPassword><Calculation>"s3cretPa55"</Calculation></SMTPPassword>
        </Step>
        <Step enable="True" id="141" name="Set Variable">
          <StepText>Set Variable [ $sig; Value: MBS ( "Hash.HMAC" ; "SHA256" ; "wJalrXUtnFEMI7K7MDENG9bPxRfiCYEXAMPLEKEY" ; $d ) ]</StepText>
          <Value><Calculation>MBS ( "Hash.HMAC" ; "SHA256" ; "wJalrXUtnFEMI7K7MDENG9bPxRfiCYEXAMPLEKEY" ; $d )</Calculation>
            <DisplayCalculation><Chunk type="FunctionRef">// sign it, then send //</Chunk><Chunk type="FunctionRef">MBS</Chunk></DisplayCalculation></Value>
          <Name>$sig</Name>
        </Step>
        <Step enable="True" id="141" name="Set Variable">
          <StepText>Set Variable [ $id; Value: JSONGetElement ( $r ; "access_token" ) ]</StepText>
          <Value><Calculation>JSONGetElement ( $r ; "access_token" )</Calculation></Value>
          <Name>$id</Name>
        </Step>
      </StepList>
    </Script>
  </ScriptCatalog>
  <AuthFileCatalog requireAuthorization="True"/>
  <ExternalDataSourcesCatalog>
    <OdbcDataSource id="2" name="SQL" DSN="SQL">
      <Username><Calculation>"dbuser"</Calculation></Username>
      <Password><Calculation>"Odbc-pw-123"</Calculation></Password>
    </OdbcDataSource>
  </ExternalDataSourcesCatalog>
</File>
</FMPReport>
"""


# A date format whose separator code is a lone UTF-16 surrogate (0xDB50), as FileMaker
# writes in the wild. Once crashed the strict UTF-8 write of the layout file (issue #12).
SURROGATE = """<?xml version="1.0" encoding="UTF-16"?>
<FMPReport type="Report" version="22.0.6">
<File name="Repro.fmp12" path="host">
  <BaseTableCatalog>
    <BaseTable id="1" name="T"><FieldCatalog>
      <Field id="1" dataType="Date" fieldType="Normal" name="d"/>
    </FieldCatalog></BaseTable>
  </BaseTableCatalog>
  <RelationshipGraph>
    <TableList><Table id="100" baseTableId="1" baseTable="T" name="T"/></TableList>
    <RelationshipList/>
  </RelationshipGraph>
  <LayoutCatalog>
    <Layout id="5" name="Form">
      <Table id="100" name="T"/>
      <Object type="Field" key="1" flags="0">
        <FieldObj numOfReps="1" displayType="0" flags="0">
          <Name>T::d</Name>
          <ExtendedAttributes fontHeight="10" graphicFormat="0">
            <DateFormat format="168" charStyle="0" monthStyle="231" dayStyle="11" separator="56144">
              <DateElement>0</DateElement>
              <DateElementSep index="0"></DateElementSep>
            </DateFormat>
          </ExtendedAttributes>
          <DDRInfo><Field name="d" id="1" repetition="1" maxRepetition="1" table="T"/></DDRInfo>
        </FieldObj>
      </Object>
    </Layout>
  </LayoutCatalog>
</File>
</FMPReport>
"""


# Items has an inactive lookup that names Orders field 6, and no field 6 of its own.
NESTED_FIELD = """<?xml version="1.0" encoding="UTF-16"?>
<FMPReport type="Report" version="22.0.6">
<File name="Nested.fmp12" path="host">
  <BaseTableCatalog>
    <BaseTable id="1" name="Orders"><FieldCatalog>
      <Field id="1" dataType="Text" fieldType="Normal" name="code"/>
      <Field id="6" dataType="Text" fieldType="Normal" name="note"/>
    </FieldCatalog></BaseTable>
    <BaseTable id="2" name="Items"><FieldCatalog>
      <Field id="1" dataType="Text" fieldType="Normal" name="sku">
        <AutoEnter allowEditing="True" lookup="False">
          <Lookup><Field table="Orders" id="6" name="note"/></Lookup>
        </AutoEnter>
      </Field>
    </FieldCatalog></BaseTable>
    <BaseTable id="3" name="OldForm">
      <Field id="4" dataType="Text" fieldType="Normal" name="kept"/>
    </BaseTable>
  </BaseTableCatalog>
  <RelationshipGraph>
    <TableList>
      <Table id="100" baseTableId="1" baseTable="Orders" name="Orders"/>
      <Table id="101" baseTableId="2" baseTable="Items" name="Items"/>
      <Table id="102" baseTableId="3" baseTable="OldForm" name="OldForm"/>
    </TableList>
    <RelationshipList/>
  </RelationshipGraph>
  <ScriptCatalog>
    <Script id="9" name="Check">
      <StepList>
        <Step enable="True" id="76" name="Set Field">
          <StepText>Set Field [ Items::&lt;Field Missing&gt; ]</StepText>
          <Field table="Items" id="6" name=""/>
        </Step>
        <Step enable="True" id="76" name="Set Field">
          <StepText>Set Field [ Items::sku ]</StepText>
          <Field table="Items" id="1" name="sku"/>
        </Step>
        <Step enable="True" id="76" name="Set Field">
          <StepText>Set Field [ OldForm::kept ]</StepText>
          <Field table="OldForm" id="4" name="kept"/>
        </Step>
      </StepList>
    </Script>
  </ScriptCatalog>
</File>
</FMPReport>
"""


# FileMaker's own markers for a deleted target, in each place they can sit. No client data.
MARKERS = """<?xml version="1.0" encoding="UTF-16"?>
<FMPReport type="Report" version="22.0.6">
<File name="Marks.fmp12" path="host">
  <BaseTableCatalog>
    <BaseTable id="1" name="Orders"><FieldCatalog>
      <Field id="1" dataType="Text" fieldType="Normal" name="code"/>
    </FieldCatalog></BaseTable>
  </BaseTableCatalog>
  <RelationshipGraph>
    <TableList><Table id="100" baseTableId="1" baseTable="Orders" name="Orders"/></TableList>
    <RelationshipList/>
  </RelationshipGraph>
  <LayoutCatalog>
    <Layout id="1" name="Live">
      <Object type="Field" key="1" flags="0">
        <ConditionalFormatting><Item><Condition>
          <Calculation>Check ( Orders::&lt;Field Missing&gt; )</Calculation>
          <DisplayCalculation><Chunk type="NoRef">Check ( Orders::&lt;Field Missing&gt; )</Chunk></DisplayCalculation>
        </Condition></Item></ConditionalFormatting>
      </Object>
    </Layout>
    <Layout id="2" name="Commented">
      <Object type="Field" key="1" flags="0">
        <ConditionalFormatting><Item><Condition>
          <Calculation>/*Check ( Orders::&lt;Field Missing&gt; )*/ 1 // &lt;Table Missing&gt;</Calculation>
        </Condition></Item></ConditionalFormatting>
      </Object>
    </Layout>
    <Layout id="3" name="Literal">
      <Object type="Field" key="1" flags="0">
        <ConditionalFormatting><Item><Condition>
          <Calculation>"say \\" &lt;unknown&gt; \\" // &lt;Field Missing&gt;" = "&lt;Field Missing&gt;"</Calculation>
        </Condition></Item></ConditionalFormatting>
      </Object>
    </Layout>
    <Layout id="5" name="Button">
      <Object type="Button" key="1" flags="0">
        <ButtonObj buttonFlags="0">
          <Step enable="True" id="6" name="Go to Layout"><StepText>Go to Layout [ &lt;unknown&gt; ]</StepText><Layout id="0" name=""/></Step>
          <Step enable="True" id="99" name="Some Step"><StepText>Some Step [ &lt;File Missing&gt; ]</StepText></Step>
        </ButtonObj>
      </Object>
    </Layout>
    <Layout id="4" name="Merge">
      <Object type="Text" key="1" flags="0">
        <TextObj flags="0">
          <ParagraphStyleVector><Style><Data>&lt;&lt;Orders::&lt;Field Missing&gt;&gt;&gt;</Data></Style></ParagraphStyleVector>
          <CharacterStyleVector><Style><Data>&lt;&lt;Orders::&lt;Field Missing&gt;&gt;&gt;</Data></Style></CharacterStyleVector>
        </TextObj>
      </Object>
    </Layout>
  </LayoutCatalog>
  <ScriptCatalog>
    <Script id="1" name="ById"><StepList>
      <Step enable="True" id="76" name="Set Field">
        <StepText>Set Field [ Orders::&lt;Field Missing&gt; ]</StepText>
        <Field table="Orders" id="6" name=""/>
      </Step>
      <Step enable="False" id="6" name="Go to Layout">
        <StepText>// Go to Layout [ &lt;unknown&gt; ]</StepText>
        <Layout id="0" name=""/>
      </Step>
    </StepList></Script>
    <Script id="2" name="InCalc"><StepList>
      <Step enable="True" id="141" name="Set Variable">
        <StepText>Set Variable [ $x; Value: &lt;Function Missing&gt; ( 1 ) ]</StepText>
        <Value><Calculation>&lt;Function Missing&gt; ( 1 )</Calculation></Value>
        <Name>$x</Name>
      </Step>
    </StepList></Script>
    <Script id="3" name="TextOnly"><StepList>
      <Step enable="True" id="99" name="Some Step">
        <StepText>Some Step [ &lt;File Missing&gt; ]</StepText>
      </Step>
    </StepList></Script>
    <Script id="6" name="EmptySlot"><StepList>
      <Step enable="True" id="76" name="Set Field">
        <StepText>Set Field [ &lt;Table Missing&gt;; "" ]</StepText>
        <Field table="" id="0" name=""/>
      </Step>
    </StepList></Script>
    <Script id="8" name="OtherKind"><StepList>
      <Step enable="True" id="99" name="Some Step">
        <StepText>Some Step [ Orders::&lt;Field Missing&gt; ]</StepText>
        <Layout id="55" name=""/>
      </Step>
    </StepList></Script>
    <Script id="10" name="ZeroLayout"><StepList>
      <Step enable="True" id="6" name="Go to Layout">
        <StepText>Go to Layout [ &lt;unknown&gt; ]</StepText>
        <Layout id="0" name=""/>
      </Step>
    </StepList></Script>
    <Script id="11" name="Mixed"><StepList>
      <Step enable="True" id="99" name="Some Step">
        <StepText>Some Step [ &lt;unknown&gt;; Orders::&lt;Field Missing&gt;; &lt;File Missing&gt; ]</StepText>
        <Field table="Orders" id="6" name=""/>
      </Step>
    </StepList></Script>
    <Script id="12" name="GoneOccurrence"><StepList>
      <Step enable="True" id="76" name="Set Field">
        <StepText>Set Field [ &lt;Table Missing&gt;; "" ]</StepText>
        <Field table="GoneTO" id="3" name=""/>
      </Step>
    </StepList></Script>
    <Script id="13" name="CalcAndId"><StepList>
      <Step enable="True" id="76" name="Set Field">
        <StepText>Set Field [ Orders::&lt;Field Missing&gt;; &lt;Field Missing&gt; + &lt;Table Missing&gt; ]</StepText>
        <Field table="Orders" id="6" name=""/>
        <Calculation>&lt;Field Missing&gt; + &lt;Table Missing&gt;</Calculation>
      </Step>
    </StepList></Script>
    <Script id="4" name="NotReferences"><StepList>
      <Step enable="True" id="89" name="# (comment)">
        <StepText># the &lt;Field Missing&gt; text</StepText>
        <Text># the &lt;Field Missing&gt; text</Text>
      </Step>
      <Step enable="True" id="61" name="Insert Text">
        <StepText>Insert Text [ "payload" ]</StepText>
        <Text>&lt;Field Missing&gt; as plain data</Text>
      </Step>
    </StepList></Script>
    <Script id="5" name="ByName"><StepList>
      <Step enable="True" id="99" name="Some Step">
        <StepText>Some Step</StepText>
        <FieldReference><TableOccurrenceReference id="-1" name="&lt;Table Missing&gt;"/></FieldReference>
      </Step>
    </StepList></Script>
  </ScriptCatalog>
  <CustomFunctionCatalog>
    <CustomFunction id="7" name="Fn"><Calculation>&lt;Table Missing&gt;::x</Calculation></CustomFunction>
  </CustomFunctionCatalog>
</File>
</FMPReport>
"""


def explode(paths, out):
    ex = explode_ddr.Exploder(out)
    with contextlib.redirect_stdout(io.StringIO()):
        results = list(ex.explode(paths))
        ex.write_index()
    return ex, results


def read_all(out):
    texts = {}
    for path in glob.glob(os.path.join(out, "**", "*.txt"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            texts[os.path.relpath(path, out)] = fh.read()
    return texts


class FixtureTest(unittest.TestCase):
    """The shipped fixtures pass every coverage gate, and the index lists every file."""

    def test_fixture_passes_every_gate(self):
        with tempfile.TemporaryDirectory() as out:
            ex, results = explode([FIXTURE], out)
            for _src, raw, shown, uncovered in results:
                self.assertEqual(raw, shown)
                self.assertEqual(uncovered, [])
            self.assertEqual(ex.bad_lines, [])
            with open(os.path.join(out, "index.tsv"), encoding="utf-8") as fh:
                rows = fh.read().splitlines()[1:]
            self.assertEqual(len(rows), len(ex.rows))
            for row in rows:
                self.assertTrue(os.path.isfile(os.path.join(out, row.split("\t")[5])))
            kinds = {row.split("\t")[1] for row in rows}
            self.assertTrue({"tables", "scripts", "layouts", "custom-functions"} <= kinds)
            self.assertTrue(os.path.isfile(os.path.join(out, "LEGEND.md")))

    def test_cross_file_reference_names_the_target_file(self):
        with tempfile.TemporaryDirectory() as out:
            explode(sorted(glob.glob(os.path.join(TWO_FILE, "*.xml"))), out)
            layout = read_all(out)[os.path.join("UI.fmp12", "layouts", "5-Home.txt")]
            self.assertIn("Script id=22 name=Save in=Backend.fmp12", layout)
            self.assertIn("Script id=9 name=Save ref=external", layout)


class GapTest(unittest.TestCase):
    """Each class of gap the real-DDR hunt found, on a synthetic DDR."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        raw = os.path.join(cls.tmp.name, "Gaps.xml")
        with open(raw, "w", encoding="utf-16") as fh:
            fh.write(GAPS)
        cls.out = os.path.join(cls.tmp.name, "out")
        cls.ex, cls.results = explode([raw], cls.out)
        cls.files = read_all(cls.out)
        cls.all = "\n".join(cls.files.values())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def file(self, kind, prefix):
        return next(t for p, t in self.files.items() if f"{os.sep}{kind}{os.sep}{prefix}" in p)

    def test_gates_pass(self):
        for _src, raw, shown, uncovered in self.results:
            self.assertEqual(raw, shown)
            self.assertEqual(uncovered, [])
        self.assertEqual(self.ex.bad_lines, [])

    def test_layout_field_has_id_repetition_and_value_list_id(self):
        layout = self.file("layouts", "5-")
        self.assertIn("Field: Shadow::code#1 rep=2/3", layout)
        self.assertIn("ValueList: Codes#7", layout)

    def test_display_format_and_decoded_code(self):
        layout = self.file("layouts", "5-")
        self.assertIn("displayType=3(checkbox-set)", layout)
        self.assertIn("Display: number flags=2574", layout)
        self.assertIn("currencySymbol=€", layout)
        with open(os.path.join(self.out, "LEGEND.md"), encoding="utf-8") as fh:
            legend = fh.read()
        self.assertIn("### FieldObj@displayType", legend)
        self.assertIn("- `2574`: unknown (1)", legend)

    def test_carriage_return_becomes_a_line(self):
        self.assertNotIn("\r", self.all)
        layout = self.file("layouts", "5-")
        self.assertIn("  | line one\n", layout)

    def test_dangling_reference_is_marked_and_listed(self):
        self.assertIn("Script id=77 name=Gone ref=missing", self.file("layouts", "5-"))
        with open(os.path.join(self.out, "unresolved.tsv"), encoding="utf-8") as fh:
            self.assertIn("Script\t77\tGone\tmissing", fh.read())

    def test_script_options_dialog_buttons_and_omitted_calculations(self):
        script = self.file("scripts", "9-")
        self.assertIn("# options: runFullAccess=True includeInMenu=False", script)
        self.assertIn('Button 1 CommitState=True: "Save"', script)
        self.assertIn('Button 2 CommitState=False: "Discard"', script)
        self.assertIn('| "Detail window"', script)  # GTRR window name, not in StepText

    def test_comment_chunk_is_not_a_function_ref(self):
        script = self.file("scripts", "9-")
        self.assertNotIn("fn://", script)

    def test_base_table_attributes(self):
        table = self.file("tables", "1-")
        self.assertIn("# records: 42", table)
        self.assertIn("# comment: ESS copy", table)
        self.assertIn("# shadow: True", table)
        self.assertIn("table db.dbo.T", table)

    def test_inactive_auto_enter_is_marked(self):
        table = self.file("tables", "1-")
        self.assertIn("calculation=False", table)
        self.assertIn("(inactive):", table)
        self.assertNotIn("constant=False", table)  # its ConstantData is empty: nothing inactive

    def test_values_are_written_as_the_ddr_has_them(self):
        script = self.file("scripts", "9-")
        self.assertIn('Password: "s3cretPa55"', script)
        self.assertIn('"wJalrXUtnFEMI7K7MDENG9bPxRfiCYEXAMPLEKEY"', script)
        self.assertIn('"mailer"', script)
        self.assertIn('"access_token"', script)
        source = self.file("data-sources", "2-")
        self.assertIn('"Odbc-pw-123"', source)
        self.assertIn('"dbuser"', source)

    def test_catalog_attributes_have_a_file(self):
        self.assertIn("requireAuthorization=True", self.file("auth-files", "catalog-"))

    def test_census_reports_an_unread_class(self):
        raw = os.path.join(self.tmp.name, "extra", "Gaps.xml")
        os.makedirs(os.path.dirname(raw))
        with open(raw, "w", encoding="utf-16") as fh:
            fh.write(GAPS.replace('<ValueList name="Codes" id="7"/>',
                                  '<ValueList name="Codes" id="7"/><Mystery code="1"/>'))
        _ex, results = explode([raw], os.path.join(self.tmp.name, "extra", "out"))
        self.assertIn("DDRInfo/Mystery", results[0][3])


class CliTest(unittest.TestCase):
    """The command line run exits 0 and writes every value as the DDR has it."""

    def test_run_exits_zero_with_values_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "raw")
            os.makedirs(raw)
            with open(os.path.join(raw, "Gaps.xml"), "w", encoding="utf-16") as fh:
                fh.write(GAPS)
            out = os.path.join(tmp, "out")
            run = subprocess.run([sys.executable, os.path.join(HERE, "..", "scripts", "explode_ddr.py"), raw, out],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertNotIn("ERROR", run.stderr)
            self.assertEqual(sorted(f for f in os.listdir(out) if not os.path.isdir(os.path.join(out, f))),
                             ["LEGEND.md", "index.tsv", "unresolved.tsv"])
            self.assertIn("s3cretPa55", "\n".join(read_all(out).values()))
            self.assertIn("markers in commented-out code, skipped: 0", run.stdout)

    def test_run_prints_how_many_commented_markers_it_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "raw")
            os.makedirs(raw)
            with open(os.path.join(raw, "Marks.xml"), "w", encoding="utf-16") as fh:
                fh.write(MARKERS)
            run = subprocess.run([sys.executable, os.path.join(HERE, "..", "scripts", "explode_ddr.py"),
                                  raw, os.path.join(tmp, "out")], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("markers in commented-out code, skipped: 2", run.stdout)


class SeparatorCodeTest(unittest.TestCase):
    """A separator code that is no character shows as U+XXXX instead of crashing the write."""

    def test_char_decodes_real_codes_and_marks_the_rest(self):
        self.assertEqual(explode_ddr._char("44"), ",")
        self.assertEqual(explode_ddr._char("0"), "")
        self.assertEqual(explode_ddr._char(None), "")
        self.assertEqual(explode_ddr._char("56144"), "U+DB50")
        self.assertEqual(explode_ddr._char("57343"), "U+DFFF")
        self.assertEqual(explode_ddr._char("1114112"), "U+110000")

    def test_surrogate_date_separator_explodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "Repro.xml")
            with open(raw, "w", encoding="utf-16") as fh:
                fh.write(SURROGATE)
            out = os.path.join(tmp, "out")
            ex, results = explode([raw], out)
            for _src, raw_calcs, shown, uncovered in results:
                self.assertEqual(raw_calcs, shown)
                self.assertEqual(uncovered, [])
            self.assertEqual(ex.bad_lines, [])
            layout = read_all(out)[os.path.join("Repro.fmp12", "layouts", "5-Form.txt")]
            self.assertIn("separator=U+DB50", layout)


class NestedDefinitionTest(unittest.TestCase):
    """Only a real definition counts: a reference nested in a definition proves nothing."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        raw = os.path.join(cls.tmp.name, "Nested.xml")
        with open(raw, "w", encoding="utf-16") as fh:
            fh.write(NESTED_FIELD)
        cls.out = os.path.join(cls.tmp.name, "out")
        cls.ex, cls.results = explode([raw], cls.out)
        cls.script = read_all(cls.out)[os.path.join("Nested.fmp12", "scripts", "9-Check.txt")]
        with open(os.path.join(cls.out, "unresolved.tsv"), encoding="utf-8") as fh:
            cls.rows = fh.read().splitlines()[1:]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_field_named_only_by_a_lookup_is_not_a_field_of_that_table(self):
        self.assertIn("Field table=Items id=6 ", self.script)
        self.assertIn('id=6 name="" ref=missing', self.script)
        self.assertIn(os.path.join("Nested.fmp12", "scripts", "9-Check.txt") + "\tField\t6\t\tmissing", self.rows)

    def test_real_fields_still_resolve_in_both_forms(self):
        self.assertNotIn("id=1 name=sku ref=", self.script)
        self.assertNotIn("id=4 name=kept ref=", self.script)  # a table with no FieldCatalog wrapper
        self.assertEqual(len(self.rows), 1)

    def test_lookup_reference_to_a_real_field_still_resolves(self):
        self.assertFalse(any(r.startswith(os.path.join("Nested.fmp12", "tables")) for r in self.rows))

    def test_base_table_named_inside_a_definition_gets_no_file(self):
        doc = NESTED_FIELD.replace('<Lookup><Field', '<BaseTable id="88" name="Ghost"/><Lookup><Field')
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "Nested.xml")
            with open(raw, "w", encoding="utf-16") as fh:
                fh.write(doc)
            ex, _ = explode([raw], os.path.join(tmp, "out"))
            self.assertEqual(sorted(r[2] for r in ex.rows if r[1] == "tables"), ["1", "2", "3"])


class TextMarkerTest(unittest.TestCase):
    """A marker no id accounts for gets a row, once, and text that only looks like one gets none."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        raw = os.path.join(cls.tmp.name, "Marks.xml")
        with open(raw, "w", encoding="utf-16") as fh:
            fh.write(MARKERS)
        cls.out = os.path.join(cls.tmp.name, "out")
        cls.ex, cls.results = explode([raw], cls.out)
        with open(os.path.join(cls.out, "unresolved.tsv"), encoding="utf-8") as fh:
            cls.rows = [line.split("\t") for line in fh.read().splitlines()[1:]]
        with open(os.path.join(cls.out, "LEGEND.md"), encoding="utf-8") as fh:
            cls.legend = fh.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rows_of(self, kind, prefix):
        where = os.path.join("Marks.fmp12", kind, prefix)
        return [r[1:] for r in self.rows if r[0].startswith(where)]

    def test_gates_pass(self):
        for _src, raw, shown, uncovered in self.results:
            self.assertEqual(raw, shown)
            self.assertEqual(uncovered, [])

    def test_live_calculation_marker_has_a_row_with_no_id(self):
        self.assertEqual(self.rows_of("layouts", "1-"),
                         [["Calculation", "", "Orders::<Field Missing>", "marker"]])

    def test_commented_out_marker_has_no_row_and_is_counted(self):
        self.assertEqual(self.rows_of("layouts", "2-"), [])
        self.assertEqual(self.ex.r.comment_markers, 2)

    def test_commented_out_marker_stays_in_the_object_file(self):
        layout = read_all(self.out)[os.path.join("Marks.fmp12", "layouts", "2-Commented.txt")]
        self.assertIn("/*Check ( Orders::<Field Missing> )*/ 1 // <Table Missing>", layout)

    def test_string_literal_is_not_a_marker(self):
        self.assertEqual(self.rows_of("layouts", "3-"), [])

    def test_merge_field_in_layout_text_has_one_row(self):
        self.assertEqual(self.rows_of("layouts", "4-"),
                         [["Text", "", "Orders::<Field Missing>", "marker"]])

    def test_button_step_on_a_layout_follows_the_same_rule(self):
        self.assertEqual(self.rows_of("layouts", "5-"),
                         [["Layout", "0", "", "none"], ["StepText", "", "<unknown>", "marker"],
                          ["StepText", "", "<File Missing>", "marker"]])

    def test_step_text_marker_of_an_id_reference_adds_no_row(self):
        self.assertEqual(self.rows_of("scripts", "1-"),
                         [["Field", "6", "", "missing"], ["Layout", "0", "", "none"],
                          ["StepText", "", "<unknown>", "marker"]])

    def test_none_row_does_not_absorb_a_marker(self):
        self.assertEqual(self.rows_of("scripts", "6-"),
                         [["Field", "0", "", "none"], ["StepText", "", "<Table Missing>", "marker"]])
        self.assertEqual(self.rows_of("scripts", "10-"),
                         [["Layout", "0", "", "none"], ["StepText", "", "<unknown>", "marker"]])

    def test_row_of_another_kind_does_not_absorb_a_marker(self):
        self.assertEqual(self.rows_of("scripts", "8-"),
                         [["Layout", "55", "", "missing"], ["StepText", "", "Orders::<Field Missing>", "marker"]])

    def test_mixed_step_names_the_marker_left_over(self):
        self.assertEqual(self.rows_of("scripts", "11-"),
                         [["Field", "6", "", "missing"],
                          ["StepText", "", "<unknown>", "marker"],
                          ["StepText", "", "<File Missing>", "marker"]])

    def test_field_on_a_deleted_occurrence_absorbs_a_table_marker(self):
        self.assertEqual(self.rows_of("scripts", "12-"), [["Field", "3", "", "missing"]])

    def test_calculation_and_id_rows_each_absorb_their_own_marker(self):
        self.assertEqual(self.rows_of("scripts", "13-"),
                         [["Field", "6", "", "missing"],
                          ["Calculation", "", "<Field Missing>", "marker"],
                          ["Calculation", "", "<Table Missing>", "marker"]])

    def test_step_text_copy_of_a_calculation_marker_adds_no_row(self):
        self.assertEqual(self.rows_of("scripts", "2-"),
                         [["Calculation", "", "<Function Missing>", "marker"]])

    def test_step_text_marker_alone_has_a_row(self):
        self.assertEqual(self.rows_of("scripts", "3-"), [["StepText", "", "<File Missing>", "marker"]])

    def test_comment_step_and_text_payload_are_not_markers(self):
        self.assertEqual(self.rows_of("scripts", "4-"), [])

    def test_marker_as_a_reference_name_is_missing(self):
        self.assertEqual(self.rows_of("scripts", "5-"),
                         [["TableOccurrenceReference", "-1", "<Table Missing>", "missing"]])
        self.assertIn("ref=missing", read_all(self.out)[os.path.join("Marks.fmp12", "scripts", "5-ByName.txt")])

    def test_custom_function_marker_has_a_row(self):
        self.assertEqual(self.rows_of("custom-functions", "7-"),
                         [["Calculation", "", "<Table Missing>", "marker"]])

    def test_legend_explains_the_statuses_and_the_limit(self):
        self.assertIn("`marker`:", self.legend)
        self.assertNotIn("marker-comment", self.legend)
        self.assertIn("Commented-out markers skipped in this run: 2", self.legend)
        self.assertIn("`<File Missing>`", self.legend)
        self.assertIn("marker 15", self.legend)
        self.assertIn("English", self.legend)


class JapaneseNameTest(unittest.TestCase):
    """Japanese names keep their letters in paths, and two file names never share a folder."""

    def test_japanese_names_keep_their_name_and_do_not_collide(self):
        doc = ('<?xml version="1.0" encoding="UTF-16"?><FMPReport type="Report" version="22.0.6">'
               '<File name="{}" path="host"><BaseTableCatalog>'
               '<BaseTable id="12" name="請求書"><FieldCatalog/></BaseTable>'
               '</BaseTableCatalog></File></FMPReport>')
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i, name in enumerate(["請求書?.fmp12", "請求書*.fmp12"]):
                paths.append(os.path.join(tmp, f"{i}.xml"))
                with open(paths[-1], "w", encoding="utf-16") as fh:
                    fh.write(doc.format(name))
            ex, _ = explode(paths, os.path.join(tmp, "out"))
            rels = sorted(row[5] for row in ex.rows)
            self.assertEqual(len(set(os.path.dirname(os.path.dirname(r)) for r in rels)), 2)
            for rel in rels:
                self.assertTrue(rel.startswith("請求書_.fmp12--"))
                self.assertTrue(rel.endswith(os.path.join("tables", "12-請求書.txt")))
        self.assertEqual(explode_ddr.slug("a/b:c*?.txt."), "a_b_c_.txt")
        self.assertEqual(len(explode_ddr.slug("請" * 100, 80)), 66)  # byte cap, whole characters


if __name__ == "__main__":
    unittest.main()
