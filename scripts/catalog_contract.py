#!/usr/bin/env python3
"""Snapshot object files from objects/index.tsv and prove that classified CSVs cover them exactly once.

    catalog_contract.py snapshot --objects OBJECTS_DIR --kind scripts [--kind ...] --output CATALOG
    catalog_contract.py verify --catalog CATALOG --csv-root CSV_ROOT

One identity per index row of the chosen kinds. source_id is the row's path (it holds the
file, kind and id, and stays unique where the DDR gives an item no id); source_hash is the
row's sha256. Each entry names the CSV it must be written to (output_file), one CSV per
batch of objects in the same file, kind and folder.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


FORMAT_VERSION = 2
BATCH_SIZE = 50
INDEX_COLUMNS = ("file", "kind", "id", "name", "folder", "path", "sha256", "lines")


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return cleaned[:60] or "unnamed"


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def read_index(objects: Path) -> list[dict[str, str]]:
    path = objects / "index.tsv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)
        missing = set(INDEX_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} lacks columns: {', '.join(sorted(missing))}")
        return list(reader)


def build_entries(objects: Path, kinds: list[str], batch_size: int) -> list[dict[str, Any]]:
    rows = read_index(objects)
    present = {row["kind"] for row in rows}
    unknown = [kind for kind in kinds if kind not in present]
    if unknown:
        raise ValueError(
            f"kind not in index: {', '.join(unknown)}; index has {', '.join(sorted(present))}"
        )
    entries: list[dict[str, Any]] = []
    batches: Counter[str] = Counter()
    for row in rows:
        if row["kind"] not in kinds:
            continue
        # One folder per source file; same-named folders in two files stay apart.
        group = f"{slug(row['folder'])}--{short_hash(row['folder'])}" if row["folder"] else "_root"
        base = f"{row['kind']}/{slug(row['file'])}--{short_hash(row['file'])}/{group}"
        number = batches[base] // batch_size + 1
        batches[base] += 1
        entries.append({
            "source_id": row["path"],
            "source_hash": row["sha256"],
            "file": row["file"],
            "kind": row["kind"],
            "id": row["id"],
            "name": row["name"],
            "lines": int(row["lines"] or 0),
            "output_file": f"{base}-{number:03d}.csv",
        })
    duplicates = [sid for sid, count in Counter(e["source_id"] for e in entries).items() if count != 1]
    if duplicates:
        raise ValueError(f"index lists {len(duplicates)} path(s) more than once, e.g. {duplicates[0]}")
    return entries


def snapshot(args: argparse.Namespace) -> int:
    objects = args.objects.resolve()
    kinds = sorted(set(args.kind))
    entries = build_entries(objects, kinds, args.batch_size)
    payload = {
        "format_version": FORMAT_VERSION,
        "objects": str(objects),
        "kinds": kinds,
        "batch_size": args.batch_size,
        "count": len(entries),
        "entries": entries,
    }
    if args.output.exists() and not args.force:
        old = json.loads(args.output.read_text(encoding="utf-8"))
        if old != payload:
            raise ValueError(
                "objects changed since this catalog was made; move the old CSVs away, "
                "run snapshot with --force, and classify again"
            )
        print("catalog unchanged")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    batches = len({entry["output_file"] for entry in entries})
    print(f"wrote {args.output} ({len(entries)} objects in {batches} batches)")
    return 0


def csv_paths(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*.csv") if path.is_file())


def verify(args: argparse.Namespace) -> int:
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if catalog.get("format_version") != FORMAT_VERSION:
        raise ValueError("unsupported catalog format; run snapshot again")
    entries = catalog.get("entries", [])
    current = build_entries(Path(catalog["objects"]), catalog["kinds"], catalog["batch_size"])
    if current != entries:
        raise ValueError(
            f"stale catalog: {catalog['objects']}/index.tsv no longer matches it; "
            "run snapshot with --force and classify the changed objects again"
        )
    expected = {entry["source_id"]: entry for entry in entries}
    observed: list[str] = []
    wrong_hash, wrong_file = [], []
    files = list(csv_paths(args.csv_root))
    if expected and not files:
        raise ValueError(f"no classification CSVs found under {args.csv_root}")
    for path in files:
        relative = path.relative_to(args.csv_root).as_posix()
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"source_id", "source_hash"} <= set(reader.fieldnames):
                raise ValueError(f"{path} lacks required columns: source_id, source_hash")
            for row in reader:
                identity = row["source_id"]
                observed.append(identity)
                entry = expected.get(identity)
                if entry is None:
                    continue
                if row["source_hash"] != entry["source_hash"]:
                    wrong_hash.append(identity)
                if relative != entry["output_file"]:
                    wrong_file.append(identity)
    counts = Counter(observed)
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    duplicates = sorted(identity for identity, count in counts.items() if count != 1)
    if missing or extra or duplicates or wrong_hash or wrong_file:
        sample = (missing or extra or duplicates or wrong_hash or wrong_file)[0]
        raise ValueError(
            "classification coverage failed: "
            f"missing={len(missing)}, extra={len(extra)}, duplicates={len(duplicates)}, "
            f"wrong_hash={len(wrong_hash)}, wrong_file={len(wrong_file)} (first: {sample})"
        )
    print(f"catalog coverage verified: {len(expected)} objects exactly once")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest="command", required=True)
    create = subs.add_parser("snapshot")
    create.add_argument("--objects", required=True, type=Path, help="the explode_ddr.py output folder")
    create.add_argument("--kind", required=True, action="append", help="an index kind; repeat for more")
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    create.add_argument("--force", action="store_true")
    check = subs.add_parser("verify")
    check.add_argument("--catalog", required=True, type=Path)
    check.add_argument("--csv-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return snapshot(args) if args.command == "snapshot" else verify(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
