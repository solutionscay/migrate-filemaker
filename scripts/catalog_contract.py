#!/usr/bin/env python3
"""Snapshot object files from objects/index.tsv and prove that classified CSVs cover them exactly once.

    catalog_contract.py snapshot --objects OBJECTS_DIR --kind scripts [--kind ...] --output CATALOG
    catalog_contract.py verify --catalog CATALOG --csv-root CSV_ROOT [--assignment AGENT_TSV]
    catalog_contract.py assign --catalog CATALOG [--catalog ...] --agents N --output DIR

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
BATCH_LINES = 6000
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


def absent_kinds(objects: Path, kinds: list[str]) -> list[str]:
    present = {row["kind"] for row in read_index(objects)}
    if not present & set(kinds):
        raise ValueError(
            f"no kind in index: {', '.join(kinds)}; index has {', '.join(sorted(present))}"
        )
    return [kind for kind in kinds if kind not in present]


def build_entries(
    objects: Path, kinds: list[str], batch_size: int, batch_lines: int = BATCH_LINES
) -> list[dict[str, Any]]:
    rows = read_index(objects)
    entries: list[dict[str, Any]] = []
    # Per group: [batch number, objects in it, lines in it]. A batch closes at
    # batch_size objects or batch_lines lines, so one agent can read it whole.
    batches: dict[str, list[int]] = {}
    for row in rows:
        if row["kind"] not in kinds:
            continue
        # One folder per source file; same-named folders in two files stay apart.
        group = f"{slug(row['folder'])}--{short_hash(row['folder'])}" if row["folder"] else "_root"
        base = f"{row['kind']}/{slug(row['file'])}--{short_hash(row['file'])}/{group}"
        lines = int(row["lines"] or 0)
        state = batches.setdefault(base, [1, 0, 0])
        if state[1] and (state[1] >= batch_size or state[2] + lines > batch_lines):
            state[:] = [state[0] + 1, 0, 0]
        state[1] += 1
        state[2] += lines
        number = state[0]
        entries.append({
            "source_id": row["path"],
            "source_hash": row["sha256"],
            "file": row["file"],
            "kind": row["kind"],
            "id": row["id"],
            "name": row["name"],
            "lines": lines,
            "output_file": f"{base}-{number:03d}.csv",
        })
    duplicates = [sid for sid, count in Counter(e["source_id"] for e in entries).items() if count != 1]
    if duplicates:
        raise ValueError(f"index lists {len(duplicates)} path(s) more than once, e.g. {duplicates[0]}")
    return entries


def snapshot(args: argparse.Namespace) -> int:
    objects = args.objects.resolve()
    kinds = sorted(set(args.kind))
    for kind in absent_kinds(objects, kinds):
        print(f"note: no {kind} objects in this solution")
    batch_lines = getattr(args, "batch_lines", BATCH_LINES)
    entries = build_entries(objects, kinds, args.batch_size, batch_lines)
    payload = {
        "format_version": FORMAT_VERSION,
        "objects": str(objects),
        "kinds": kinds,
        "batch_size": args.batch_size,
        "batch_lines": batch_lines,
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
    current = build_entries(Path(catalog["objects"]), catalog["kinds"], catalog["batch_size"],
                            catalog.get("batch_lines", BATCH_LINES))
    if current != entries:
        raise ValueError(
            f"stale catalog: {catalog['objects']}/index.tsv no longer matches it; "
            "run snapshot with --force and classify the changed objects again"
        )
    expected = {entry["source_id"]: entry for entry in entries}
    files = list(csv_paths(args.csv_root))
    if getattr(args, "assignment", None):
        # One agent's share: only its batches must be complete; other CSVs are not read.
        mine = assigned_batches(args.assignment, catalog["kinds"])
        expected = {k: e for k, e in expected.items() if e["output_file"] in mine}
        files = [f for f in files if f.relative_to(args.csv_root).as_posix() in mine]
    observed: list[str] = []
    wrong_hash, wrong_file = [], []
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


def assigned_batches(path: Path, kinds: list[str]) -> set[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {row["output_file"] for row in rows if row["output_file"].split("/", 1)[0] in kinds}


def assign(args: argparse.Namespace) -> int:
    """Pack whole batches into N agents of near-equal object lines, one TSV per agent."""
    batches: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for path in args.catalog:
        catalog = json.loads(path.read_text(encoding="utf-8"))
        for entry in catalog["entries"]:
            batches.setdefault((str(path), entry["output_file"]), []).append(entry)
    loads = [0] * args.agents
    shares: list[list[tuple[str, str]]] = [[] for _ in range(args.agents)]
    for key in sorted(batches, key=lambda k: -sum(e["lines"] for e in batches[k])):
        i = loads.index(min(loads))
        shares[i].append(key)
        loads[i] += sum(e["lines"] for e in batches[key])
    args.output.mkdir(parents=True, exist_ok=True)
    for n, share in enumerate(shares, 1):
        out = args.output / f"agent-{n:02d}.tsv"
        with out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["catalog", "output_file", "source_id", "lines"])
            for catalog, output_file in share:
                for entry in batches[(catalog, output_file)]:
                    writer.writerow([catalog, output_file, entry["source_id"], entry["lines"]])
        print(f"{out}: {len(share)} batches, {loads[n - 1]} lines")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest="command", required=True)
    create = subs.add_parser("snapshot")
    create.add_argument("--objects", required=True, type=Path, help="the explode_ddr.py output folder")
    create.add_argument("--kind", required=True, action="append", help="an index kind; repeat for more")
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    create.add_argument("--batch-lines", type=int, default=BATCH_LINES,
                        help="close a batch before it passes this many object lines")
    create.add_argument("--force", action="store_true")
    check = subs.add_parser("verify")
    check.add_argument("--catalog", required=True, type=Path)
    check.add_argument("--csv-root", required=True, type=Path)
    check.add_argument("--assignment", type=Path, help="an agent TSV from assign: check only its batches")
    share = subs.add_parser("assign")
    share.add_argument("--catalog", required=True, type=Path, action="append")
    share.add_argument("--agents", required=True, type=int)
    share.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return {"snapshot": snapshot, "verify": verify, "assign": assign}[args.command](args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
