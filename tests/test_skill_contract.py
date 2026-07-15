import argparse
import csv
import importlib.util
import json
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
    def snapshot(self, root, scripts):
        spec = root / "05_scripts.json"
        output = root / "source_catalog.json"
        spec.write_text(json.dumps(scripts), encoding="utf-8")
        catalog_contract.snapshot(
            argparse.Namespace(kind="scripts", spec=spec, output=output, force=False)
        )
        return output

    def write_csvs(self, root, catalog):
        csv_root = root / "catalogs"
        csv_root.mkdir()
        grouped = {}
        for entry in catalog["entries"]:
            grouped.setdefault(entry["output_file"], []).append(entry)
        for name, entries in grouped.items():
            with (csv_root / name).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["source_id", "source_hash", "index"])
                writer.writeheader()
                writer.writerows(
                    {key: entry[key] for key in writer.fieldnames} for entry in entries
                )
        return csv_root

    def test_root_scripts_use_visible_root_file_and_exact_coverage_passes(self):
        scripts = [
            {"source_file": "A.fmp12", "id": "1", "group": "", "name": "Open", "steps": []},
            {"source_file": "A.fmp12", "id": "2", "group": "Ops", "name": "Close", "steps": []},
            {"source_file": "A.fmp12", "id": "3", "group": "Ops", "name": "Route", "steps": []},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self.snapshot(root, scripts)
            catalog = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(catalog["entries"][0]["output_file"], "_root.csv")
            self.assertEqual(
                catalog["entries"][1]["output_file"], catalog["entries"][2]["output_file"]
            )
            csv_root = self.write_csvs(root, catalog)
            self.assertEqual(
                catalog_contract.verify(argparse.Namespace(catalog=output, csv_root=csv_root)), 0
            )

    def test_coverage_rejects_duplicate_missing_and_changed_rows(self):
        scripts = [
            {"source_file": "A.fmp12", "id": "1", "group": "", "name": "One", "steps": []},
            {"source_file": "A.fmp12", "id": "2", "group": "", "name": "Two", "steps": []},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self.snapshot(root, scripts)
            catalog = json.loads(output.read_text(encoding="utf-8"))
            csv_root = root / "catalogs"
            csv_root.mkdir()
            first = catalog["entries"][0]
            with (csv_root / "_root.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["source_id", "source_hash", "index"])
                writer.writeheader()
                row = {key: first[key] for key in writer.fieldnames}
                writer.writerow(row)
                writer.writerow(row)
            with self.assertRaisesRegex(ValueError, "coverage failed"):
                catalog_contract.verify(argparse.Namespace(catalog=output, csv_root=csv_root))

    def test_snapshot_refuses_changed_spec_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self.snapshot(
                root,
                [{"source_file": "A", "id": "1", "group": "", "name": "One", "steps": []}],
            )
            spec = root / "05_scripts.json"
            spec.write_text(
                json.dumps(
                    [{"source_file": "A", "id": "1", "group": "", "name": "Changed", "steps": []}]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source changed"):
                catalog_contract.snapshot(
                    argparse.Namespace(kind="scripts", spec=spec, output=output, force=False)
                )


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

    def test_repaired_high_risk_contracts_are_required(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        business = (ROOT / "templates" / "07_business_logic.md").read_text(encoding="utf-8")
        auth = (ROOT / "templates" / "08_auth_roles.md").read_text(encoding="utf-8")
        ui = (ROOT / "templates" / "06_ui_spec.md").read_text(encoding="utf-8")
        for phrase in ["provenance.py", "catalog_contract.py", "07_security.json", "step_text"]:
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
            "SKILL.md": [
                "_provenance.json",
                "stable source identities",
                "07_security.json",
                "extended-privilege definitions",
                "current year",
                "source timezone/DST policy",
            ],
            "workflows/fm-script-explorer.md": [
                "_root.csv",
                "structured `params` and `step_text`",
                "populated comments",
                "effect_owner",
            ],
            "workflows/fm-schema-builder.md": [
                'data_type == "Binary"',
                'data_type == "TimeStamp"',
                "02_table_occurrences.json",
                "compound relationship",
                "surrogate target key only when explicitly chosen",
            ],
            "workflows/fm-cf-explorer.md": [
                "format_css",
                "Never deduplicate on formula alone",
                "every presentation payload",
            ],
            "workflows/fm-hide-explorer.md": [
                "unattributed",
                "07_security.json",
                'Do not call this a "complete access-control model."',
            ],
            "workflows/fm-ui-spec.md": [
                "inventory-only",
                "raw DDR layout XML",
                "Never join hide/CF rules to an object by array position",
            ],
            "reference/business-logic-detection.md": [
                "ExecuteSQL (`",
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
                "Every source identity must map",
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
