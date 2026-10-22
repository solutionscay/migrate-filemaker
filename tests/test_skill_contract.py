import argparse
import contextlib
import csv
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog_contract = load_script("catalog_contract.py")
provenance = load_script("provenance.py")


class ProvenanceTests(unittest.TestCase):
    def make_fixture(self, root):
        raw = root / "raw"
        specs = root / "specs"
        raw.mkdir(parents=True)
        specs.mkdir()
        (raw / "sample.xml").write_text(
            '<?xml version="1.0" encoding="UTF-16"?><FMPReport type="Report"/>',
            encoding="utf-16",
        )
        (raw / "Summary.xml").write_text(
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<FMPReport type="Summary" version="22.0.6">'
            '<File link=".//sample.xml" name="sample.fmp12">'
            '<Scripts count="1"/></File></FMPReport>',
            encoding="utf-16",
        )
        topology = {
            "file_count": 1,
            "files": [{"name": "sample.fmp12", "counts": {"scripts": 0}}],
            "unresolved_references": [],
        }
        payloads = {name: [] for name in provenance.EXPECTED_SPECS}
        payloads["00_topology.json"] = topology
        payloads["07_security.json"] = {"accounts": [], "privileges": []}
        for name, value in payloads.items():
            (specs / name).write_text(json.dumps(value) + "\n", encoding="utf-8")
        scripts = root / "scripts"
        scripts.mkdir()
        parser = scripts / "parse_ddr.py"
        parser.write_text("# fixture parser\n", encoding="utf-8")
        tests = root / "tests"
        tests.mkdir()
        (tests / "test_guard.py").write_text("# fixture test\n", encoding="utf-8")
        manifest = provenance.build_manifest(raw, specs, parser, False)
        manifest["tests"] = {"command": "fixture", "passed": True}
        manifest["parser_reproduction"] = {"command": "fixture", "matched": True}
        (specs / provenance.MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return raw, specs, parser

    def verify(self, raw, specs, parser):
        return provenance.verify(
            argparse.Namespace(raw_dir=raw, specs_dir=specs, parser=parser)
        )

    def test_manifest_verifies_unchanged_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, specs, parser = self.make_fixture(Path(directory))
            manifest = json.loads(
                (specs / provenance.MANIFEST_NAME).read_text(encoding="utf-8")
            )
            declaration = manifest["summary_declarations"][0]
            self.assertEqual(declaration["files"][0]["name"], "sample.fmp12")
            self.assertEqual(declaration["files"][0]["counts"]["Scripts"], "1")
            self.assertEqual(self.verify(raw, specs, parser), 0)

    def test_manifest_rejects_raw_semantic_change(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, specs, parser = self.make_fixture(Path(directory))
            (raw / "sample.xml").write_text(
                '<?xml version="1.0" encoding="UTF-16"?><FMPReport type="Report"><Changed/></FMPReport>',
                encoding="utf-16",
            )
            with self.assertRaisesRegex(ValueError, "changed"):
                self.verify(raw, specs, parser)

    def test_manifest_rejects_spec_or_parser_change(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, specs, parser = self.make_fixture(Path(directory))
            (specs / "05_scripts.json").write_text('[{"id":"new"}]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                self.verify(raw, specs, parser)

    def test_manifest_rejects_test_suite_change(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, specs, parser = self.make_fixture(Path(directory))
            (Path(directory) / "tests" / "test_guard.py").write_text(
                "# weakened fixture test\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "changed"):
                self.verify(raw, specs, parser)

    def test_manifest_rejects_missing_summary_report(self):
        with tempfile.TemporaryDirectory() as directory:
            raw, specs, parser = self.make_fixture(Path(directory))
            (raw / "Summary.xml").write_text(
                '<?xml version="1.0" encoding="UTF-16"?>'
                '<FMPReport type="Summary" version="22.0.6">'
                '<File link=".//missing.xml" name="sample.fmp12"/>'
                "</FMPReport>",
                encoding="utf-16",
            )
            with self.assertRaisesRegex(ValueError, "missing report file"):
                provenance.build_manifest(raw, specs, parser, False)

    def test_parser_reproduction_requires_exact_spec_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw, specs, parser = self.make_fixture(root)
            parser.write_text(
                "from pathlib import Path\n"
                "import shutil, sys\n"
                "source = Path(__file__).parent.parent / 'specs'\n"
                "target = Path(sys.argv[2])\n"
                "target.mkdir(parents=True)\n"
                "for path in source.glob('*.json'):\n"
                "    if path.name != '_provenance.json':\n"
                "        shutil.copy2(path, target / path.name)\n",
                encoding="utf-8",
            )
            proof = provenance.prove_parser_output(raw, specs, parser)
            self.assertTrue(proof["matched"])
            parser.write_text(
                parser.read_text(encoding="utf-8")
                + "(target / '05_scripts.json').write_text('[]\\n')\n",
                encoding="utf-8",
            )
            (specs / "05_scripts.json").write_text('[{"id": "expected"}]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not the exact output"):
                provenance.prove_parser_output(raw, specs, parser)

    def test_test_gate_rejects_vacuous_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            with self.assertRaisesRegex(RuntimeError, "regression suite failed"):
                provenance.run_tests(root)
            raw, specs, parser = self.make_fixture(Path(directory) / "second")
            parser.write_text("# changed parser\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                self.verify(raw, specs, parser)


class CatalogContractTests(unittest.TestCase):
    ROWS = [
        ("A.fmp12", "scripts", "1", "Open", "", "A.fmp12/scripts/1-Open.txt"),
        ("A.fmp12", "scripts", "2", "Log", "Utilities", "A.fmp12/scripts/2-Log.txt"),
        ("A.fmp12", "scripts", "3", "Route", "Utilities", "A.fmp12/scripts/3-Route.txt"),
        ("B.fmp12", "scripts", "2", "Log", "Utilities", "B.fmp12/scripts/2-Log.txt"),
        ("A.fmp12", "tables", "1", "People", "", "A.fmp12/tables/1-People.txt"),
        # The DDR gives some items no id; explode_ddr.py can then repeat one.
        ("A.fmp12", "base-directories", "5", "Options", "", "A.fmp12/base-directories/5-Options.txt"),
        ("A.fmp12", "base-directories", "5", "List", "", "A.fmp12/base-directories/5-List.txt"),
    ]

    def write_index(self, objects, rows):
        objects.mkdir(exist_ok=True)
        lines = ["file\tkind\tid\tname\tfolder\tpath\tsha256\tlines"]
        lines += ["\t".join(row + (f"hash-{row[5]}", "3")) for row in rows]
        (objects / "index.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def snapshot(self, root, kinds, rows=None, force=False, batch_size=50):
        objects = root / "objects"
        if rows is not None or not (objects / "index.tsv").exists():
            self.write_index(objects, self.ROWS if rows is None else rows)
        output = root / "catalog.json"
        with contextlib.redirect_stdout(io.StringIO()):
            catalog_contract.snapshot(argparse.Namespace(
                objects=objects, kind=kinds, output=output, force=force, batch_size=batch_size,
            ))
        return output, json.loads(output.read_text(encoding="utf-8"))

    def write_csvs(self, root, entries, place=lambda entry: entry["output_file"]):
        csv_root = root / "csv"
        grouped = {}
        for entry in entries:
            grouped.setdefault(place(entry), []).append(entry)
        for name, rows in grouped.items():
            path = csv_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["source_id", "source_hash", "purpose"])
                writer.writeheader()
                writer.writerows(
                    {"source_id": e["source_id"], "source_hash": e["source_hash"], "purpose": "x"}
                    for e in rows
                )
        return csv_root

    def verify(self, catalog, csv_root):
        with contextlib.redirect_stdout(io.StringIO()):
            return catalog_contract.verify(argparse.Namespace(catalog=catalog, csv_root=csv_root))

    def test_one_entry_per_index_row_of_the_kind_and_full_coverage_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, catalog = self.snapshot(root, ["scripts"])
            self.assertEqual([e["source_id"] for e in catalog["entries"]],
                             [row[5] for row in self.ROWS if row[1] == "scripts"])
            self.assertEqual(catalog["entries"][0]["source_hash"], "hash-A.fmp12/scripts/1-Open.txt")
            self.assertEqual(self.verify(output, self.write_csvs(root, catalog["entries"])), 0)

    def test_output_files_split_by_file_folder_and_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            _, catalog = self.snapshot(Path(directory), ["scripts"], batch_size=1)
            files = [e["output_file"] for e in catalog["entries"]]
            self.assertEqual(len(set(files)), 4, files)
            self.assertTrue(files[0].startswith("scripts/A.fmp12--"), files[0])
            self.assertTrue(files[0].endswith("/_root-001.csv"), files[0])
            self.assertTrue(files[2].endswith("-002.csv"), files[2])

    def test_kinds_combine_and_rows_without_ids_stay_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, catalog = self.snapshot(root, ["tables", "base-directories"])
            self.assertEqual(catalog["count"], 3)
            self.assertEqual(self.verify(output, self.write_csvs(root, catalog["entries"])), 0)

    def test_absent_kind_is_noted_and_no_present_kind_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            _, catalog = self.snapshot(Path(directory), ["tables", "auth-files"])
            self.assertEqual(catalog["count"], 1)
            with self.assertRaisesRegex(ValueError, "no kind in index"):
                self.snapshot(Path(directory), ["layouts"])

    def test_coverage_rejects_missing_duplicate_and_changed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, catalog = self.snapshot(root, ["scripts"])
            entries = catalog["entries"]
            for rows in (entries[1:], entries + entries[:1],
                         [dict(entries[0], source_hash="other")] + entries[1:]):
                shutil.rmtree(root / "csv", ignore_errors=True)
                with self.assertRaisesRegex(ValueError, "coverage failed"):
                    self.verify(output, self.write_csvs(root, rows))

    def test_coverage_rejects_a_row_outside_its_output_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, catalog = self.snapshot(root, ["scripts"])
            csv_root = self.write_csvs(root, catalog["entries"], place=lambda e: "all.csv")
            with self.assertRaisesRegex(ValueError, "wrong_file=4"):
                self.verify(output, csv_root)

    def test_verify_fails_when_the_index_changed_after_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, catalog = self.snapshot(root, ["scripts"])
            csv_root = self.write_csvs(root, catalog["entries"])
            rows = [row[:3] + ("Renamed",) + row[4:] if row[2] == "3" else row for row in self.ROWS]
            self.write_index(root / "objects", rows)
            with self.assertRaisesRegex(ValueError, "stale catalog"):
                self.verify(output, csv_root)

    def test_snapshot_refuses_changed_objects_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.snapshot(root, ["scripts"])
            changed = self.ROWS[:1]
            with self.assertRaisesRegex(ValueError, "objects changed"):
                self.snapshot(root, ["scripts"], rows=changed)
            _, catalog = self.snapshot(root, ["scripts"], rows=changed, force=True)
            self.assertEqual(catalog["count"], 1)


class GuidanceRegressionTests(unittest.TestCase):
    def read_scope(self):
        paths = [ROOT / "SKILL.md"]
        paths.extend(sorted((ROOT / "workflows").glob("*.md")))
        paths.extend(
            path
            for path in sorted((ROOT / "reference").glob("*.md"))
            if path.name != "ddr-xml-reference.md"
        )
        paths.extend(sorted((ROOT / "templates").glob("*")))
        return "\n".join(path.read_text(encoding="utf-8") for path in paths)

    def test_frontmatter_contains_only_supported_keys(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])

    def test_positional_resume_and_imagined_tokens_do_not_return(self):
        text = self.read_scope()
        banned = [
            "next_idx = max(done_indices)",
            "field_type') == 'Container'",
            "format_actions,category",
            "create CRUD endpoints for each real table",
            "Spot-check 10 random records",
            "single-value variable shared across sessions",
            "UPDATE table SET field = value` (no WHERE)",
            "Any script attached to a script trigger",
            "custom functions are almost always",
            "framework 2025",
        ]
        for phrase in banned:
            self.assertNotIn(phrase, text)

    def test_guidance_reads_object_files_not_json_specs(self):
        text = self.read_scope()
        self.assertNotRegex(text, r"\b\d\d_[a-z_]+\.json")
        self.assertNotIn("parse_ddr.py", (ROOT / "SKILL.md").read_text(encoding="utf-8"))
        for phrase in ["alarming", "suspicious", "surprising", "spot-check", "spot check"]:
            self.assertNotIn(phrase, text.lower())

    def test_every_exploded_kind_has_an_explorer(self):
        explode = load_script("explode_ddr.py")
        workflows = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "workflows").glob("*.md"))
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for kind in set(explode.CATALOG_KIND.values()) | {"relationships", "file"}:
            self.assertIn(f"--kind {kind}", workflows, kind)
        for path in (ROOT / "workflows").glob("*.md"):
            self.assertIn(f"workflows/{path.name}", skill)

    def test_repaired_high_risk_contracts_are_required(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        business = (ROOT / "templates" / "07_business_logic.md").read_text(encoding="utf-8")
        auth = (ROOT / "templates" / "08_auth_roles.md").read_text(encoding="utf-8")
        ui = (ROOT / "templates" / "06_ui_spec.md").read_text(encoding="utf-8")
        for phrase in ["explode_ddr.py", "catalog_contract.py"]:
            self.assertIn(phrase, skill)
        for phrase in [
            "Calculated fields",
            "Custom functions",
            "Conditional formatting",
            "Hide-object rules",
            "Security predicates",
        ]:
            self.assertIn(phrase, business)
        for phrase in [
            "Entity operation matrix",
            "Record-level policies",
            "Field-level policies",
            "Negative authorization tests",
            "service principals",
        ]:
            self.assertIn(phrase, auth)
        self.assertIn("inventory-only / behavior-ready / implementation-ready", ui)

    def test_all_audit_remediations_remain_explicit(self):
        required = {
            "workflows/fm-script-explorer.md": ["--kind scripts", "Choose by effect, not by name or folder"],
            "workflows/fm-table-explorer.md": ["--kind tables", "logic_count", "Binary"],
            "workflows/fm-layout-explorer.md": [
                "--kind layouts", "HideCondition", "ConditionalFormatting", "ToolTip", "FilterCalc",
                "It does not grant access",
            ],
            "workflows/fm-graph-explorer.md": ["--kind relationships", "fk_candidate"],
            "workflows/fm-security-explorer.md": ["--kind privilege-sets", "--kind extended-privileges"],
            "reference/explorer-contract.md": ["Do not judge whether the client's logic is correct"],
            "reference/business-logic-detection.md": [
                "fn:ExecuteSQL",
                "never exclusion filters",
                "generic utility",
            ],
            "reference/script-translation-patterns.md": [
                "current found set",
                "never emit an unqualified `UPDATE`",
                "Categorize by ownership, not invocation",
                "It is not evidence of an inbound webhook",
            ],
            "reference/filemaker-concepts.md": [
                "independently for each client/session",
                "DDR exposes no password/hash",
                "validation can vary by timing",
            ],
            "reference/tech-stack-decision-matrix.md": [
                "established repository",
                "Authentication is not authorization",
                "current year/date",
            ],
            "templates/03_migration_plan.md": [
                "Per-column null/distinct/min/max/length/domain",
                "Stable-value hashes",
                "Rejected/changed rows",
            ],
            "templates/05_api_design.md": [
                "Do not create CRUD endpoints for every",
                "Default deny",
                "DDR contains no password or password hash",
            ],
            "templates/07_business_logic.md": [
                "Every source identity (an object file",
                "A script-only document is incomplete",
            ],
            "templates/08_auth_roles.md": [
                "Default deny",
                "Field-level policies",
                "service principals",
                "Negative authorization tests",
            ],
        }
        for relative, phrases in required.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase, text, f"missing {phrase!r} from {relative}")

        auth = (ROOT / "templates" / "08_auth_roles.md").read_text(encoding="utf-8")
        self.assertNotIn("record.assigned_to", auth)


if __name__ == "__main__":
    unittest.main()
