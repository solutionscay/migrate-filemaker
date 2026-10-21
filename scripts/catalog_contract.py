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
    source_file: str, group: str, identity: str, root_name: str | None = None
) -> str:
    # One folder per source file: same-named groups in two files stay apart.
    folder = f"{slug(source_file)}--{digest_text(source_file)[:8]}"
    if not group and root_name:
        return f"{folder}/{root_name}"
    return f"{folder}/{slug(group)}--{digest_text(identity)[:8]}.csv"


def flatten(kind: str, value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if kind == "scripts":
        for index, item in enumerate(value):
            identity = token("script", item.get("source_file"), item.get("id"))
            rows.append(
                make_entry(
                    index, identity, item.get("name"), item.get("group", ""), item,
                    item.get("source_file"), root_name="_root.csv",
                )
            )
    elif kind == "calculations":
        index = 0
        for table in value:
            for item in table.get("calculated", []):
                identity = token(
                    "calculation", table.get("source_file"), table.get("id"), item.get("id")
                )
                rows.append(
                    make_entry(
                        index, identity, item.get("name"), table.get("name", ""), item,
                        table.get("source_file"),
                    )
                )
                index += 1
    elif kind == "functions":
        for index, item in enumerate(value):
            identity = token("function", item.get("source_file"), item.get("id"))
            rows.append(
                make_entry(
                    index, identity, item.get("name"), "custom-functions", item, item.get("source_file")
                )
            )
    elif kind in ("conditional-formatting", "hide-rules"):
        occurrences: defaultdict[str, int] = defaultdict(int)
        prefix = "cf" if kind == "conditional-formatting" else "hide"
        for index, item in enumerate(value):
            content_hash = digest_text(canonical(item))
            base = token(prefix, item.get("source_file"), item.get("layout"), content_hash)
            occurrence = occurrences[base]
            occurrences[base] += 1
            identity = token(base, occurrence)
            # Layout names can repeat within a file; the layout id keeps their files apart.
            rows.append(
                make_entry(
                    index, identity, item.get("object_name") or "(unnamed)", item.get("layout", ""),
                    item, item.get("source_file"),
                    group_key=token(item.get("layout_id"), item.get("layout")),
                )
            )
    else:
        raise ValueError(f"unsupported kind: {kind}")
    return rows


def make_entry(
    index: int,
    identity: str,
    label: Any,
    group: str,
    item: dict[str, Any],
    source_file: str | None,
    root_name: str | None = None,
    group_key: str | None = None,
) -> dict[str, Any]:
    source_hash = digest_text(canonical(item))
    return {
        "index": index,
        "source_id": identity,
        "source_hash": source_hash,
        "label": label or "",
        "output_file": grouped_filename(
            source_file or "", group, group if group_key is None else group_key, root_name
        ),
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
    migrate_root = getattr(args, "migrate_csv_root", None)
    if migrate_root is not None:
        old = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else {}
        if not is_flat_layout(old):
            raise ValueError(f"{args.output} is not a catalog from before the per-file folders; nothing to migrate")
        migrate_flat_csvs(migrate_root, entries)
    elif args.output.exists() and not args.force:
        with args.output.open(encoding="utf-8") as handle:
            old = json.load(handle)
        if old != payload:
            if is_flat_layout(old):
                raise ValueError(flat_layout_message(args))
            raise ValueError("explorer source changed; archive/rebuild classifications, then use --force")
        print("catalog unchanged")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(entries)} identities)")
    return 0


def is_flat_layout(catalog: dict[str, Any]) -> bool:
    """True for a catalog built before output_file gained the <file-slug>--<hash8>/ folder."""
    return any("/" not in entry.get("output_file", "/") for entry in catalog.get("entries", []))


def flat_layout_message(args: argparse.Namespace) -> str:
    command = (
        f"python3 {Path(__file__).resolve()} snapshot --kind {args.kind} --spec {args.spec} "
        f"--output {args.output}"
    )
    return (
        f"{args.output} was built before output_file gained the per-source-file folder "
        "(<file-slug>--<hash8>/). Its CSVs sit flat under the CSV root and no longer match.\n"
        f"Move rows whose source_hash still matches into the new folders:\n  {command} "
        "--migrate-csv-root <CSV_ROOT>\n"
        f"Or archive the CSV root outside it, rebuild, and reclassify:\n  {command} --force"
    )


def migrate_flat_csvs(csv_root: Path, entries: list[dict[str, Any]]) -> None:
    """Move rows from flat CSVs into each entry's new output_file.

    All or nothing: every row must match a new entry by source_id and
    source_hash. The old CSVs move to <csv_root>.pre-folder-layout/, outside
    the CSV root, so verify does not count them twice.
    """
    archive = csv_root.parent / f"{csv_root.name}.pre-folder-layout"
    if archive.exists():
        raise ValueError(f"{archive} already exists; remove it or move it away first")
    if any(path.parent != csv_root for path in csv_paths(csv_root)):
        raise ValueError(f"{csv_root} already has CSVs in subfolders; migrate by hand")
    by_id = {entry["source_id"]: entry for entry in entries}
    targets: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
    unmatched = 0
    old_files = list(csv_paths(csv_root))
    for path in old_files:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            if not {"source_id", "source_hash"}.issubset(fieldnames):
                raise ValueError(f"{path} lacks required columns: source_id, source_hash")
            for row in reader:
                entry = by_id.get(row["source_id"])
                if not entry or entry["source_hash"] != row["source_hash"]:
                    unmatched += 1
                    continue
                header, rows = targets.setdefault(entry["output_file"], (fieldnames, []))
                if header != fieldnames:
                    raise ValueError(f"{entry['output_file']} would mix CSVs with different columns")
                rows.append(row)
    if unmatched:
        raise ValueError(
            f"cannot migrate: {unmatched} row(s) have no new entry with the same source_id and "
            "source_hash. Nothing was moved. Archive the CSV root, rebuild with --force, and reclassify."
        )
    for name, (fieldnames, rows) in targets.items():
        target = csv_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    archive.mkdir()
    for path in old_files:
        path.rename(archive / path.name)
    print(f"migrated {sum(len(rows) for _, rows in targets.values())} rows into {len(targets)} CSVs; "
          f"old CSVs archived in {archive}")


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
    create.add_argument(
        "--migrate-csv-root", type=Path,
        help="move flat CSVs from a pre-folder catalog into the new output_file paths",
    )
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
