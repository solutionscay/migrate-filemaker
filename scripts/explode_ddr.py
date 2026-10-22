#!/usr/bin/env python3
"""Explode a FileMaker DDR into one plain-text file per object.

    python3 explode_ddr.py RAW_DIR OUT_DIR

Every catalog item under each <File> becomes a text file an agent can read line
by line: scripts as numbered steps, tables with every field, layouts as their
object tree, table occurrences with their relationships, and every other catalog
(value lists, custom functions, menus, security, data sources, file options ...)
rendered generically, so a catalog this script has never heard of still lands on
disk instead of vanishing.

Presentation-only elements (CSS, number/date formats, character styles) are left
out. Logic is never left out: every <Calculation> in the raw XML must show up in
some object file, and the run fails loudly when the counts disagree.

Output:
    OUT_DIR/<file-slug>/<kind>/<id>-<name>.txt
    OUT_DIR/index.tsv     one row per object: file, kind, id, name, folder, path, sha256, lines
"""

import hashlib
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ddr import (  # noqa: E402
    find_ddr_reports, looks_like_secret_target, parse_xml, redact_all_literals, redact_secrets,
)

# Subtrees that carry only presentation. Never put a logic element here.
SKIP = {
    "Styles", "LocalCSS", "FullCSS", "ExtendedAttributes", "NumFormat", "DateFormat", "TimeFormat",
    "CharacterStyleVector", "ParagraphStyleVector", "CharacterStyle", "ParagraphStyle",
    "DDRInfo", "Theme", "LocalTheme", "CustomStyles", "RenderFormat", "ThemeCatalog",
    "DisplayCalculation",  # structured copy of <Calculation>; rendered as a refs line instead
}
# Field options whose "False" is the default; a False value says nothing.
FIELD_OPTION_TAGS = {"AutoEnter", "Validation", "Storage", "NotEmpty", "Unique", "Existing",
                     "StrictValidation", "MaxDataLength"}
KEEP_FALSE = {"storeCalculationResults", "allowEditing", "enable"}


def css_props(el):
    """Property lines of every LocalCSS under el, as one compact string."""
    props = []
    for css in el.iter("LocalCSS"):
        for ln in (css.text or "").splitlines():
            ln = ln.strip()
            if ln.endswith(";"):
                props.append(ln)
    return " ".join(props)

CATALOG_KIND = {
    "BaseTableCatalog": "tables",
    "RelationshipGraph": "table-occurrences",
    "LayoutCatalog": "layouts",
    "ScriptCatalog": "scripts",
    "ValueListCatalog": "value-lists",
    "AccountCatalog": "accounts",
    "PrivilegesCatalog": "privilege-sets",
    "ExtendedPrivilegeCatalog": "extended-privileges",
    "AuthFileCatalog": "auth-files",
    "CustomFunctionCatalog": "custom-functions",
    "ExternalDataSourcesCatalog": "data-sources",
    "CustomMenuSetCatalog": "custom-menu-sets",
    "CustomMenuCatalog": "custom-menus",
    "BaseDirectoryCatalog": "base-directories",
}


def slug(value, limit=60):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("._")
    return cleaned[:limit] or "unnamed"


class Renderer:
    """Turn an element subtree into indented lines; count every calculation emitted."""

    def __init__(self):
        self.seen = set()  # ids of rendered <Calculation> elements; copies count once

    @property
    def calcs(self):
        return len(self.seen)

    def refs(self, display):
        """One compact line from a <DisplayCalculation>: fields, functions, custom functions."""
        out = []
        for chunk in display.iter("Chunk"):
            kind = chunk.get("type")
            if kind == "FieldRef":
                f = chunk.find("Field")
                if f is not None:
                    tbl = f.get("table") or ""
                    out.append(f"{tbl}::{f.get('name')}#{f.get('id')}" if tbl else f"{f.get('name')}#{f.get('id')}")
            elif kind == "CustomFunctionRef":
                out.append(f"cf:{(chunk.text or '').strip()}")
            elif kind == "FunctionRef":
                out.append(f"fn:{(chunk.text or '').strip()}")
            elif kind in ("VariableReference", "TableOccurrenceRef") or kind not in ("NoRef", None):
                out.append(f"{kind}:{(chunk.text or '').strip()}")
        seen, uniq = set(), []
        for r in out:
            if r not in seen:
                seen.add(r)
                uniq.append(r)
        return uniq

    def calc(self, el, parent, depth, secret, show_text=True):
        self.seen.add(id(el))
        pad = "  " * depth
        display = parent.find("DisplayCalculation") if parent is not None else None
        refs = self.refs(display) if display is not None else []
        if not show_text:
            # The step line already shows this calculation; keep only what it cannot show:
            # which field (by id), custom function or table occurrence it touches.
            refs = [r for r in refs if not r.startswith("fn:")]
            return [f"{pad}refs: {', '.join(refs)}"] if refs else []
        attrs = " ".join(f"{k}={v}" for k, v in el.attrib.items())
        lines = [f"{pad}Calculation{(' ' + attrs) if attrs else ''}:"]
        text = (el.text or "").rstrip()
        text = redact_all_literals(text) if secret else redact_secrets(text)
        for ln in text.splitlines() or [""]:
            lines.append(f"{pad}  | {ln}")
        if refs:
            lines.append(f"{pad}  refs: {', '.join(refs)}")
        return lines

    def element(self, el, depth=0, secret=False, calc_text=True, parent=None):
        tag = el.tag
        if tag in SKIP:
            return []
        if tag == "Calculation":
            return self.calc(el, parent, depth, secret, show_text=calc_text)
        pad = "  " * depth
        if tag == "TextObj":
            # Label text lives inside the character-style runs, which are otherwise skipped.
            runs = el.find("CharacterStyleVector")
            label = "".join(d.text or "" for d in (runs if runs is not None else el).iter("Data")).strip()
            sub = [ln for c in el if c.tag not in SKIP
                   for ln in self.element(c, depth + 1, secret, calc_text, parent=el)]
            head = [f"{pad}Text: {_q(redact_secrets(label))}"] if label else []
            return head + sub
        if tag == "Format":
            # A conditional format's effect is its CSS; 500pt text is how FileMaker hides things.
            props = css_props(el)
            return [f"{pad}Format: {props}"] if props else []
        attrs = {k: v for k, v in el.attrib.items()
                 if not (k in ("rotation", "flags") and v == "0")}
        if tag in FIELD_OPTION_TAGS:
            attrs = {k: v for k, v in attrs.items() if v != "False" or k in KEEP_FALSE}
        bounds = el.find("Bounds")
        if bounds is not None:
            attrs["bounds"] = ",".join(
                str(round(float(bounds.get(s, 0)))) for s in ("top", "left", "bottom", "right"))
        children = [c for c in el if c.tag not in SKIP and c.tag != "Bounds"]
        text = (el.text or "").strip()
        if not attrs and not text and not children:
            return []
        if tag == "Field" and not children and attrs.get("id") == "0" and not attrs.get("name"):
            return []
        sub = []
        for c in children:
            sub += self.element(c, depth + 1, secret, calc_text, parent=el)
        if not attrs and not text and not sub:
            return []  # a wrapper whose content was all presentation or already shown
        head = pad + tag + "".join(f" {k}={_q(v)}" for k, v in attrs.items())
        lines = []
        if text and "\n" not in text and len(text) < 160:
            lines.append(f"{head}: {redact_secrets(text)}")
        else:
            lines.append(head)
            for ln in text.splitlines():
                lines.append(f"{pad}  | {redact_secrets(ln)}")
        return lines + sub


def _q(v):
    return f'"{v}"' if (v == "" or " " in v) else v


class Exploder:
    def __init__(self, out_dir):
        self.out = out_dir
        self.r = Renderer()
        self.rows = []
        self.counts = Counter()

    def write(self, src, kind, oid, name, folder, xpath, header_extra, body):
        rel = os.path.join(slug(src, 80), kind, f"{oid}-{slug(name)}.txt")
        path = os.path.join(self.out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        head = [f"# {kind[:-1] if kind.endswith('s') else kind} {oid}: {name}",
                f"# file: {src}"]
        if folder:
            head.append(f"# folder: {folder}")
        head.append(f"# source: {xpath}")
        head += [f"# {h}" for h in header_extra]
        text = "\n".join(head + [""] + body) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.rows.append((src, kind, oid, name, folder, rel,
                          hashlib.sha256(text.encode()).hexdigest(), str(text.count("\n"))))
        self.counts[kind] += 1

    # ── per-catalog renderers ────────────────────────────────────────────────

    def tables(self, src, cat):
        for t in cat.iter("BaseTable"):
            fields = t.findall("FieldCatalog/Field") or t.findall("Field")
            body = []
            for f in fields:
                secret = looks_like_secret_target(f.get("name"))
                body += self.r.element(f, 0, secret)
                body.append("")
            self.write(src, "tables", t.get("id"), t.get("name"), "",
                       f"BaseTableCatalog/BaseTable[@id={t.get('id')}]",
                       [f"fields: {len(fields)}"], body)

    def occurrences(self, src, graph):
        rels = graph.findall("RelationshipList/Relationship")
        by_to = {}
        for rel in rels:
            for side in ("LeftTable", "RightTable"):
                s = rel.find(side)
                if s is not None:
                    by_to.setdefault(s.get("name"), []).append(rel)
        for to in graph.findall("TableList/Table"):
            body = self.r.element(to)
            mine = by_to.get(to.get("name"), [])
            body += ["", f"relationships: {len(mine)}"]
            for rel in mine:
                body += [""] + self.r.element(rel)
            self.write(src, "table-occurrences", to.get("id"), to.get("name"), "",
                       f"RelationshipGraph/TableList/Table[@id={to.get('id')}]", [], body)
        # Relationships are also written once each, so a relationship is never only a copy.
        for rel in rels:
            l, r = rel.find("LeftTable"), rel.find("RightTable")
            name = f"{l.get('name') if l is not None else '?'} = {r.get('name') if r is not None else '?'}"
            self.write(src, "relationships", rel.get("id"), name, "",
                       f"RelationshipGraph/RelationshipList/Relationship[@id={rel.get('id')}]", [],
                       self.r.element(rel))

    def scripts(self, src, cat):
        def walk(el, path):
            for c in el:
                if c.tag == "Group":
                    walk(c, f"{path} / {c.get('name')}" if path else c.get("name"))
                elif c.tag == "Script":
                    self.script(src, c, path)
        walk(cat, "")

    def script(self, src, sc, folder):
        steps = sc.findall("StepList/Step")
        if sc.get("name") == "-" and not steps:
            self.counts["separators-skipped"] += 1
            return
        body, disabled = [], 0
        for n, st in enumerate(steps, 1):
            on = st.get("enable", "True") == "True"
            disabled += not on
            text = (st.findtext("StepText") or st.get("name") or "").strip()
            # The target is a variable (<Name>$pw</Name>) or a field (<Field name=...>).
            secret = looks_like_secret_target(st.findtext("Name"),
                                              *[f.get("name") for f in st.findall("Field")])
            text = redact_all_literals(text) if secret else redact_secrets(text)
            first, *rest = text.splitlines() or [""]
            body.append(f"{n:>4} {'   ' if on else '// '}{first}")
            body += [f"{'':>4}    {ln}" for ln in rest]
            # Options StepText does not show (restored find requests, sort keys, import maps,
            # file references, script/layout ids) and the refs of every calculation in the step.
            for c in st:
                if c.tag == "StepText" or (st.get("id") == "89" and c.tag == "Text"):
                    continue
                body += [f"{'':>8}{ln}" for ln in self.r.element(c, 0, secret, calc_text=False, parent=st)]
        self.write(src, "scripts", sc.get("id"), sc.get("name"), folder,
                   f"ScriptCatalog/Script[@id={sc.get('id')}]",
                   [f"steps: {len(steps)} ({disabled} disabled)"], body)

    def layouts(self, src, cat):
        def walk(el, path):
            for c in el:
                if c.tag == "Group":
                    walk(c, f"{path} / {c.get('name')}" if path else c.get("name"))
                elif c.tag == "Layout":
                    if c.get("name") == "-" and c.find(".//Object") is None:
                        self.counts["separators-skipped"] += 1
                        continue
                    objs = len(c.findall(".//Object"))
                    self.write(src, "layouts", c.get("id"), c.get("name"), path,
                               f"LayoutCatalog/Layout[@id={c.get('id')}]",
                               [f"objects: {objs}"], self.r.element(c))
        walk(cat, "")

    def generic(self, src, cat, kind):
        """Every child item of a catalog becomes one file. Folders (<Group>) are walked."""
        def walk(el, path):
            for c in el:
                if c.tag == "Group" and c.get("name") is not None and kind != "privilege-sets":
                    walk(c, f"{path} / {c.get('name')}" if path else c.get("name"))
                    continue
                oid = c.get("id") or str(sum(1 for _ in el.iter()))
                name = c.get("name") or c.findtext("Name") or c.tag
                secret = kind == "custom-functions" and _secret_function(c)
                self.write(src, kind, oid, name, path, f"{cat.tag}/{c.tag}[@id={c.get('id')}]", [],
                           self.r.element(c, 0, secret))
        walk(cat, "")

    def explode_file(self, path):
        root = parse_xml(path).getroot()
        for file_el in root.iter("File"):
            src = file_el.get("name")
            raw_calcs = sum(1 for _ in file_el.iter("Calculation"))
            skipped = sum(1 for s in SKIP - {"DisplayCalculation"}
                          for el in file_el.iter(s) for _ in el.iter("Calculation"))
            self.r.seen = set()  # element ids are reused once a file's tree is freed
            for cat in file_el:
                tag = cat.tag
                kind = CATALOG_KIND.get(tag, slug(tag).lower())
                if tag == "BaseTableCatalog":
                    self.tables(src, cat)
                elif tag == "RelationshipGraph":
                    self.occurrences(src, cat)
                elif tag == "ScriptCatalog":
                    self.scripts(src, cat)
                elif tag == "LayoutCatalog":
                    self.layouts(src, cat)
                elif tag == "Options":
                    self.write(src, "file", "0", "options", "", "Options", [], self.r.element(cat))
                elif tag == "ThemeCatalog":
                    continue
                else:
                    self.generic(src, cat, kind)
            emitted = self.r.calcs
            yield src, raw_calcs - skipped, emitted

    def write_index(self):
        with open(os.path.join(self.out, "index.tsv"), "w", encoding="utf-8") as fh:
            fh.write("file\tkind\tid\tname\tfolder\tpath\tsha256\tlines\n")
            for row in sorted(self.rows, key=lambda r: (r[0], r[1], _num(r[2]))):
                fh.write("\t".join(str(v).replace("\t", " ") for v in row) + "\n")


def _num(v):
    return int(v) if str(v).isdigit() else 0


def _secret_function(cf):
    # A zero-arity function whose name reads like a credential returns the secret itself.
    return looks_like_secret_target(cf.get("name"))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    raw, out = sys.argv[1], sys.argv[2]
    if os.path.exists(out) and os.listdir(out):
        sys.exit(f"Error: {out} is not empty. Explode into a new folder.")
    files = find_ddr_reports(raw)
    if not files:
        sys.exit(f"Error: no DDR report XML in {raw}")
    ex = Exploder(out)
    failed = False
    for f in files:
        print(f"Exploding {os.path.basename(f)} ...")
        for src, raw_calcs, emitted in ex.explode_file(f):
            print(f"  {src}: {raw_calcs} calculations in raw XML, {emitted} rendered")
            if emitted < raw_calcs:
                print(f"  ERROR: {raw_calcs - emitted} calculation(s) were not rendered", file=sys.stderr)
                failed = True
    ex.write_index()
    for kind, n in sorted(ex.counts.items()):
        print(f"  {kind}: {n}")
    print(f"Wrote {len(ex.rows)} object files and index.tsv to {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
