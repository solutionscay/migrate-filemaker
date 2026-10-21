#!/usr/bin/env python3
"""Snapshot explorer inputs and prove that classified CSVs cover them exactly once."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


FORMAT_VERSION = 1
KINDS = ("scripts", "calculations", "functions", "conditional-formatting", "hide-rules")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def token(*parts: Any) -> str:
    return "|".join(str(part or "") for part in parts)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return cleaned[:80] or "unnamed"


def grouped_filename(
    group: str, identity: str, root_name: str | None = None, source_file: str | None = None
) -> str:
    """The CSV of a group. In a multi-file spec, pass `source_file`: groups with
    the same name in different files then get different CSVs, the root group
    included (`_root--<hash>.csv`). A one-file spec keeps `_root.csv`."""
    if source_file is not None:
        identity = token(source_file, identity)
    if not group and root_name:
        if source_file is None:
            return root_name
        stem, dot, ext = root_name.rpartition(".")
        return f"{stem}--{digest_text(identity)[:8]}.{ext}" if dot else f"{root_name}--{digest_text(identity)[:8]}"
    return f"{slug(group)}--{digest_text(identity)[:8]}.csv"


def flatten(kind: str, value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Group names repeat across files (two files with a folder "Utilities").
    # In a multi-file spec the file is part of every group's output file.
    if kind == "calculations":
        files = {table.get("source_file") for table in value}
    else:
        files = {item.get("source_file") for item in value}
    multi = len(files) > 1
    src = (lambda item: item.get("source_file")) if multi else (lambda item: None)
    if kind == "scripts":
        for index, item in enumerate(value):
            identity = token("script", item.get("source_file"), item.get("id"))
            rows.append(make_entry(index, identity, item.get("name"), item.get("group", ""), item, "_root.csv", src(item)))
    elif kind == "calculations":
        index = 0
        for table in value:
            for item in table.get("calculated", []):
                identity = token(
                    "calculation", table.get("source_file"), table.get("id"), item.get("id")
                )
                rows.append(make_entry(index, identity, item.get("name"), table.get("name", ""), item, source_file=src(table)))
                index += 1
    elif kind == "functions":
        for index, item in enumerate(value):
            identity = token("function", item.get("source_file"), item.get("id"))
            rows.append(make_entry(index, identity, item.get("name"), "custom-functions", item, source_file=src(item)))
    elif kind in ("conditional-formatting", "hide-rules"):
        occurrences: defaultdict[str, int] = defaultdict(int)
        prefix = "cf" if kind == "conditional-formatting" else "hide"
        for index, item in enumerate(value):
            content_hash = digest_text(canonical(item))
            base = token(prefix, item.get("source_file"), item.get("layout"), content_hash)
            occurrence = occurrences[base]
            occurrences[base] += 1
            identity = token(base, occurrence)
            rows.append(make_entry(index, identity, item.get("object_name") or "(unnamed)", item.get("layout", ""), item,
                                  source_file=src(item)))
    else:
        raise ValueError(f"unsupported kind: {kind}")
    return rows


def make_entry(
    index: int,
    identity: str,
    label: Any,
    group: str,
    item: dict[str, Any],
    root_name: str | None = None,
    source_file: str | None = None,
) -> dict[str, Any]:
    source_hash = digest_text(canonical(item))
    return {
        "index": index,
        "source_id": identity,
        "source_hash": source_hash,
        "label": label or "",
        "output_file": grouped_filename(group, group, root_name, source_file),
    }


def load_spec(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def snapshot(args: argparse.Namespace) -> int:
    entries = flatten(args.kind, load_spec(args.spec))
    ids = [entry["source_id"] for entry in entries]
    duplicates = [identity for identity, count in Counter(ids).items() if count != 1]
    if duplicates:
        raise ValueError(f"source identity collision ({len(duplicates)} identities)")
    payload = {
        "format_version": FORMAT_VERSION,
        "kind": args.kind,
        "spec_path": args.spec.name,
        "spec_sha256": sha256(args.spec),
        "count": len(entries),
        "entries": entries,
    }
    if args.output.exists() and not args.force:
        with args.output.open(encoding="utf-8") as handle:
            old = json.load(handle)
        if old != payload:
            raise ValueError("explorer source changed; archive/rebuild classifications, then use --force")
        print("catalog unchanged")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(entries)} identities)")
    return 0


def csv_paths(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*.csv") if path.is_file())


def verify(args: argparse.Namespace) -> int:
    with args.catalog.open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    if catalog.get("format_version") != FORMAT_VERSION:
        raise ValueError("unsupported catalog format; rebuild explorer state")
    expected = {entry["source_id"]: entry for entry in catalog.get("entries", [])}
    observed: list[str] = []
    wrong_hash = []
    files = list(csv_paths(args.csv_root))
    if expected and not files:
        raise ValueError(f"no classification CSVs found under {args.csv_root}")
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"source_id", "source_hash"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError(f"{path} lacks required columns: source_id, source_hash")
            for row in reader:
                identity = row["source_id"]
                observed.append(identity)
                entry = expected.get(identity)
                if entry and row["source_hash"] != entry["source_hash"]:
                    wrong_hash.append(identity)
    counts = Counter(observed)
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    duplicates = sorted(identity for identity, count in counts.items() if count != 1)
    if missing or extra or duplicates or wrong_hash:
        raise ValueError(
            "classification coverage failed: "
            f"missing={len(missing)}, extra={len(extra)}, duplicates={len(duplicates)}, "
            f"wrong_hash={len(wrong_hash)}"
        )
    print(f"catalog coverage verified: {len(expected)} identities exactly once")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    create = subs.add_parser("snapshot")
    create.add_argument("--kind", required=True, choices=KINDS)
    create.add_argument("--spec", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--force", action="store_true")
    check = subs.add_parser("verify")
    check.add_argument("--catalog", required=True, type=Path)
    check.add_argument("--csv-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return snapshot(args) if args.command == "snapshot" else verify(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
