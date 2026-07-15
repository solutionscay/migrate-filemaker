#!/usr/bin/env python3
"""Create or verify a fail-closed provenance manifest for parsed DDR specs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


EXPECTED_SPECS = [
    "00_topology.json",
    "01_tables.json",
    "02_table_occurrences.json",
    "03_relationships.json",
    "04_layouts.json",
    "05_scripts.json",
    "06_value_lists.json",
    "07_security.json",
    "08_custom_functions.json",
    "09_conditional_formatting.json",
    "10_hide_object_when.json",
]
MANIFEST_NAME = "_provenance.json"
FORMAT_VERSION = 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_count(value: Any) -> Any:
    """Return structural cardinalities without copying string values into the manifest."""
    if isinstance(value, list):
        return {"items": len(value)}
    if isinstance(value, dict):
        counts: dict[str, int] = {}
        for key, child in sorted(value.items()):
            if isinstance(child, (list, dict)):
                counts[key] = len(child)
        return counts
    return {"items": 1}


def raw_inventory(raw_dir: Path) -> list[dict[str, Any]]:
    files = sorted(
        path for path in raw_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".xml"
    )
    if not files:
        raise ValueError(f"no XML files found under {raw_dir}")
    return [
        {
            "path": path.relative_to(raw_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files
    ]


def spec_inventory(specs_dir: Path) -> list[dict[str, Any]]:
    missing = [name for name in EXPECTED_SPECS if not (specs_dir / name).is_file()]
    if missing:
        raise ValueError("missing required specs: " + ", ".join(missing))

    inventory = []
    for name in EXPECTED_SPECS:
        path = specs_dir / name
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        inventory.append(
            {
                "path": name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "counts": json_count(value),
            }
        )
    return inventory


def topology_declarations(specs_dir: Path) -> dict[str, Any]:
    with (specs_dir / "00_topology.json").open(encoding="utf-8") as handle:
        topology = json.load(handle)
    files = []
    for item in topology.get("files", []):
        files.append({"name": item.get("name"), "counts": item.get("counts", {})})
    return {
        "file_count": topology.get("file_count"),
        "files": files,
        "unresolved_reference_count": len(topology.get("unresolved_references", [])),
    }


def summary_declarations(raw_dir: Path) -> list[dict[str, Any]]:
    """Capture non-secret FileMaker Summary.xml source/count declarations."""
    summaries = []
    for path in sorted(raw_dir.rglob("*.xml")):
        first = next(
            ET.iterparse(
                path,
                events=("start",),
                parser=ET.XMLParser(encoding="utf-16"),
            )
        )[1]
        if first.tag != "FMPReport" or first.get("type") != "Summary":
            continue
        root = ET.parse(path, parser=ET.XMLParser(encoding="utf-16")).getroot()
        files = []
        for file_element in root.findall("File"):
            counts = {}
            for child in file_element:
                if "count" in child.attrib:
                    counts[child.tag] = child.get("count")
            files.append(
                {
                    "name": file_element.get("name"),
                    "link": file_element.get("link"),
                    "counts": counts,
                }
            )
        summaries.append(
            {
                "path": path.relative_to(raw_dir).as_posix(),
                "filemaker_version": root.get("version"),
                "files": files,
            }
        )
    return summaries


def validate_source_declarations(
    raw_dir: Path,
    summaries: list[dict[str, Any]],
    topology: dict[str, Any],
) -> None:
    raw_names = {path.name.casefold() for path in raw_dir.rglob("*.xml") if path.is_file()}
    summary_names = []
    for summary in summaries:
        for item in summary["files"]:
            summary_names.append(item.get("name"))
            link = item.get("link")
            if link and Path(link.replace("\\", "/")).name.casefold() not in raw_names:
                raise ValueError(f"Summary.xml declares missing report file: {link}")
    topology_names = [item.get("name") for item in topology.get("files", [])]
    if summary_names and sorted(summary_names) != sorted(topology_names):
        raise ValueError("Summary.xml source names do not match parsed topology source names")


def run_tests(skill_dir: Path) -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    result = subprocess.run(
        command,
        cwd=skill_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    match = re.search(r"Ran (\d+) tests?", output)
    if result.returncode or not match or int(match.group(1)) == 0:
        raise RuntimeError(f"parser regression suite failed:\n{output}")
    return {
        "command": "python -m unittest discover -s tests",
        "passed": True,
        "count": int(match.group(1)),
    }


def test_suite_inventory(skill_dir: Path) -> list[dict[str, Any]]:
    tests_dir = skill_dir / "tests"
    files = sorted(
        path
        for path in tests_dir.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    return [
        {
            "path": path.relative_to(skill_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files
    ]


def prove_parser_output(raw_dir: Path, specs_dir: Path, parser: Path) -> dict[str, Any]:
    """Re-run the parser and require the supplied specs to be its exact output."""
    with tempfile.TemporaryDirectory(prefix="migrate-filemaker-provenance-") as directory:
        reproduced = Path(directory) / "specs"
        command = [sys.executable, str(parser.resolve()), str(raw_dir.resolve()), str(reproduced)]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode:
            output = (result.stdout + "\n" + result.stderr).strip()
            raise RuntimeError(f"parser reproduction failed:\n{output}")
        expected = {item["path"]: item["sha256"] for item in spec_inventory(specs_dir)}
        actual = {item["path"]: item["sha256"] for item in spec_inventory(reproduced)}
        if expected != actual:
            changed = sorted(name for name in expected if expected.get(name) != actual.get(name))
            raise ValueError(
                "supplied specs are not the exact output of this parser/raw set: "
                + ", ".join(changed)
            )
    return {"command": "parse_ddr.py RAW TEMP_SPECS", "matched": True}


def build_manifest(raw_dir: Path, specs_dir: Path, parser: Path, run_suite: bool) -> dict[str, Any]:
    if not parser.is_file():
        raise ValueError(f"parser not found: {parser}")
    skill_dir = parser.resolve().parent.parent
    tests = run_tests(skill_dir) if run_suite else {"command": None, "passed": False}
    summaries = summary_declarations(raw_dir)
    topology = topology_declarations(specs_dir)
    validate_source_declarations(raw_dir, summaries, topology)
    return {
        "format_version": FORMAT_VERSION,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "parser": {"path": parser.name, "sha256": sha256(parser)},
        "tests": tests,
        "test_suite_files": test_suite_inventory(skill_dir),
        "raw_files": raw_inventory(raw_dir),
        "summary_declarations": summaries,
        "spec_files": spec_inventory(specs_dir),
        "topology": topology,
    }


def comparable(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "created_utc"}


def create(args: argparse.Namespace) -> int:
    manifest = build_manifest(args.raw_dir, args.specs_dir, args.parser, True)
    if not manifest["tests"]["passed"]:
        raise ValueError("refusing to create trusted provenance without a passing test suite")
    manifest["parser_reproduction"] = prove_parser_output(
        args.raw_dir, args.specs_dir, args.parser
    )
    destination = args.specs_dir / MANIFEST_NAME
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination}")
    return 0


def verify(args: argparse.Namespace) -> int:
    path = args.specs_dir / MANIFEST_NAME
    if not path.is_file():
        raise ValueError(f"missing provenance manifest: {path}")
    with path.open(encoding="utf-8") as handle:
        recorded = json.load(handle)
    if recorded.get("format_version") != FORMAT_VERSION:
        raise ValueError("unsupported provenance format; regenerate specs and manifest")
    if not recorded.get("tests", {}).get("passed"):
        raise ValueError("manifest does not record a passing parser regression suite")
    if not recorded.get("parser_reproduction", {}).get("matched"):
        raise ValueError("manifest does not prove that the parser reproduced these specs")

    current = build_manifest(args.raw_dir, args.specs_dir, args.parser, False)
    current["tests"] = recorded["tests"]
    current["parser_reproduction"] = recorded["parser_reproduction"]
    if comparable(recorded) != comparable(current):
        raise ValueError("raw XML, parser, topology, or spec files changed; regenerate before analysis")
    print("provenance verified")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("raw_dir", type=Path)
        sub.add_argument("specs_dir", type=Path)
        sub.add_argument(
            "--parser",
            type=Path,
            default=Path(__file__).resolve().with_name("parse_ddr.py"),
        )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return create(args) if args.command == "create" else verify(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
