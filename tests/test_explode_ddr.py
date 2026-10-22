import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import explode_ddr  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "mini_ddr.xml")


class ExplodeTest(unittest.TestCase):
    """Every calculation in the raw XML lands in an object file, and the index lists every file."""

    def test_fixture_explodes_with_full_calculation_coverage(self):
        with tempfile.TemporaryDirectory() as out:
            ex = explode_ddr.Exploder(out)
            with contextlib.redirect_stdout(io.StringIO()):
                results = list(ex.explode_file(FIXTURE))
            ex.write_index()
            for _src, raw, emitted in results:
                self.assertEqual(raw, emitted)
            with open(os.path.join(out, "index.tsv"), encoding="utf-8") as fh:
                rows = fh.read().splitlines()[1:]
            self.assertEqual(len(rows), len(ex.rows))
            for row in rows:
                self.assertTrue(os.path.isfile(os.path.join(out, row.split("\t")[5])))
            kinds = {row.split("\t")[1] for row in rows}
            self.assertTrue({"tables", "scripts", "layouts", "custom-functions"} <= kinds)

    def test_password_variable_is_redacted(self):
        r = explode_ddr.Renderer()
        self.assertTrue(explode_ddr.looks_like_secret_target("$pw"))
        self.assertFalse(explode_ddr.looks_like_secret_target("$sort"))
        self.assertNotIn("hunter2", "\n".join(
            r.calc(explode_ddr.ET.fromstring('<Calculation>"hunter2"</Calculation>'),
                   None, 0, secret=True)))


if __name__ == "__main__":
    unittest.main()
