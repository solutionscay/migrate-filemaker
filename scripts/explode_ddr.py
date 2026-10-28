#!/usr/bin/env python3
"""Explode a FileMaker DDR into one plain-text file per object.

    python3 explode_ddr.py RAW_DIR OUT_DIR

Every catalog item under each <File> becomes a text file an agent can read line
by line: scripts as numbered steps, tables with every field, layouts as their
object tree, table occurrences with their relationships, and every other catalog
(value lists, custom functions, menus, security, data sources, file options ...)
rendered generically, so a catalog this script has never heard of still lands on
disk instead of vanishing.

Only presentation is left out (CSS, fonts, character styles, theme definitions).
Every value is written as the DDR has it.
The run checks its own coverage and fails loudly when:
  - a <Calculation> was not shown (its text, or proof that the step text shows it);
  - an element, attribute or text class of the raw XML reached no object file and
    is not on the presentation list below.

Output:
    OUT_DIR/<file-slug>/<kind>/<id>-<name>.txt
    OUT_DIR/index.tsv       one row per object: file, kind, id, name, folder, path, sha256, lines
    OUT_DIR/unresolved.tsv  every reference to an id that is 0, deleted, or outside the DDR set
    OUT_DIR/LEGEND.md       the markers and codes used in the object files
"""

import fnmatch
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ddr import (  # noqa: E402
    _strip_fm_extension, find_ddr_reports, parse_xml, path_target_name, reference_paths,
)

# Subtrees the generic walk does not print. Each is either presentation or read by a
# special case: DDRInfo and ExtendedAttributes by FieldObj/TextObj, Styles for the
# style name, Theme for the layout header, DisplayCalculation for the refs line.
SKIP = {
    "Styles", "LocalCSS", "FullCSS", "ExtendedAttributes", "NumFormat", "DateFormat", "TimeFormat",
    "CharacterStyleVector", "ParagraphStyleVector", "CharacterStyle", "ParagraphStyle",
    "DDRInfo", "Theme", "LocalTheme", "CustomStyles", "RenderFormat", "ThemeCatalog",
    "DisplayCalculation",
}
# Subtrees the coverage census does not walk: theme definitions (CSS only) and the
# chunked copy of each calculation, which the refs line reads.
UNREAD = {"ThemeCatalog", "DisplayCalculation", "CharacterStyle", "ParagraphStyleVector",
          "LocalTheme", "LocalCSS", "FullCSS", "RenderFormat"}
# Raw classes (Parent/Tag, Parent/Tag@attr, Parent/Tag#text) the coverage census does
# not require in the output. Presentation only; never put logic here.
PRESENTATION = [
    "*/CharacterStyleVector@*", "CharacterStyleVector/Style", "CharacterStyleVector/Style@*",
    "Style/Data@*", "Styles/CustomStyles", "*/Styles",
    "Layout/Theme@*", "DefaultTheme/Theme*", "*/ExtendedAttributes@fontHeight", "*/ExtendedAttributes@graphicFormat",
    "*/NumFormat@charStyle", "*/DateFormat@charStyle", "*/TimeFormat@charStyle",
    "FMPReport@*", "/FMPReport",
]
# Field options whose "False" is the default; a False value says nothing.
FIELD_OPTION_TAGS = {"AutoEnter", "Validation", "Storage", "NotEmpty", "Unique", "Existing",
                     "StrictValidation", "MaxDataLength"}
KEEP_FALSE = {"storeCalculationResults", "allowEditing", "enable"}
# An option flag that is False while its child still holds a setting: the child is inactive.
INACTIVE_CHILD = {"calculation": "Calculation", "lookup": "Lookup", "constant": "ConstantData",
                  "valuelist": "ValueList", "maxLength": "MaxDataLength"}

# Codes with a meaning read from the data (see LEGEND.md). Unknown values stay raw.
DECODE = {
    ("FieldObj", "displayType"): {"0": "edit box", "1": "drop-down list", "2": "pop-up menu",
                                  "3": "checkbox set", "4": "radio button set", "6": "drop-down calendar"},
}
BITS = {
    ("Trigger", "triggerFlags"): {1: "browse", 2: "find", 4: "preview"},
}
# Codes printed raw. LEGEND.md lists every value seen, so an agent knows what exists.
CODES = [
    ("Object", "flags"), ("FieldObj", "flags"), ("FieldObj", "inputMode"), ("FieldObj", "keyboardType"),
    ("FieldObj", "pictFormat"), ("FieldObj", "tableViewVisibility"), ("TextObj", "flags"),
    ("ButtonObj", "buttonFlags"), ("ButtonObj", "displayType"), ("PortalObj", "portalFlags"),
    ("TabControlObj", "tabFlagSet"), ("TabControlObj", "tabJustification"),
    ("SlideControlObj", "slideFlagSet"), ("PopoverObj", "position"), ("ExternalObj", "externalFlagSet"),
    ("Condition", "op"), ("Item", "flags"), ("Encryption", "type"), ("Shortcut", "key"),
    ("Shortcut", "modifier"), ("NewWndStyles", "Styles"), ("NumFormat", "flags"),
    ("DateFormat", "format"), ("TimeFormat", "flags"),
] + list(DECODE) + list(BITS)
CODE_SET = set(CODES)
LEGEND_VALUES = 20  # most common values listed per code in LEGEND.md

SINGULAR = {
    "tables": "table", "table-occurrences": "table occurrence", "relationships": "relationship",
    "layouts": "layout", "scripts": "script", "value-lists": "value list", "accounts": "account",
    "privilege-sets": "privilege set", "extended-privileges": "extended privilege",
    "auth-files": "auth file", "custom-functions": "custom function", "data-sources": "data source",
    "custom-menu-sets": "custom menu set", "custom-menus": "custom menu",
    "base-directories": "base directory", "file": "file",
}

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

_LINE_BREAK = re.compile("\r\n?|[\n\x0b\x0c\x1c-\x1e\x85\u2028\u2029]")
_IDENT = re.compile(r"[A-Za-z_][\w.]*")


def slug(value, limit=60):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("._")
    return cleaned[:limit] or "unnamed"


def lines_of(text):
    """Split on every line break a reader may honour (CR, LF, CRLF, VT, FF ...)."""
    return _LINE_BREAK.sub("\n", text or "").split("\n")


def one_line(text):
    """FileMaker's own ¶ for a line break inside a single-line value."""
    return _LINE_BREAK.sub("¶", text or "")


def norm(text):
    """Whitespace- and quote-insensitive form, to test whether StepText shows a calculation."""
    text = (text or "").replace("“", '"').replace("”", '"').replace("…", "")
    return re.sub(r"\s+", "", text)


def _q(v):
    v = one_line(v)
    return f'"{v}"' if (v == "" or " " in v) else v


def css_props(el):
    """Property lines of every LocalCSS under el, as one compact string."""
    props = []
    for css in el.iter("LocalCSS"):
        for ln in lines_of(css.text):
            ln = ln.strip()
            if ln.endswith(";"):
                props.append(ln)
    return " ".join(props)


class Catalog:
    """Ids of one <File>, read before rendering so references can be checked."""

    def __init__(self, file_el):
        self.el = file_el
        self.name = file_el.get("name") or ""
        self.slug = slug(self.name, 80)
        self.stem = _strip_fm_extension(self.name).lower()
        self.tables, self.fields = {}, defaultdict(set)
        for t in file_el.iterfind("BaseTableCatalog/BaseTable"):
            self.tables[t.get("id")] = t.get("name")
            for f in t.iter("Field"):
                self.fields[t.get("id")].add(f.get("id"))
        self.tos = {t.get("name"): t for t in file_el.iterfind("RelationshipGraph/TableList/Table")}
        self.to_ids = {t.get("id") for t in self.tos.values()}
        self.scripts, self.script_seps = self._items("ScriptCatalog", "Script", "StepList/Step")
        self.layouts, self.layout_seps = self._items("LayoutCatalog", "Layout", ".//Object")
        self.data_sources = {}
        for ds in file_el.iterfind("ExternalDataSourcesCatalog/*"):
            self.data_sources[ds.get("id")] = ds
        self.ids = {
            "ValueList": {v.get("id") for v in file_el.iterfind("ValueListCatalog/ValueList")},
            "CustomMenu": {m.get("id") for m in file_el.iterfind("CustomMenuCatalog/CustomMenu")},
            "CustomMenuSet": {m.get("id") for m in file_el.iterfind("CustomMenuSetCatalog/CustomMenuSet")},
            "PrivilegeSet": {p.get("id") for p in file_el.iterfind("PrivilegesCatalog/PrivilegeSet")},
            "BaseTable": set(self.tables),
        }

    def _items(self, cat_tag, item_tag, content):
        ids, seps = set(), set()

        # Walk the catalog and its folders only. A <Script> inside a step is a call to
        # a script, not a script; counting it hid every call to a deleted script.
        def walk(node):
            for it in node:
                if it.tag != item_tag:
                    if it.tag == "Group":
                        ids.add(it.get("id"))  # privilege sets list folders by id too
                    walk(it)
                elif it.get("name") == "-" and it.find(content) is None:
                    seps.add(it.get("id"))
                else:
                    ids.add(it.get("id"))
                    if it.find(content) is None:
                        walk(it)  # a folder (group) item holds more items

        cat = self.el.find(cat_tag)
        if cat is not None:
            walk(cat)
        return ids, seps

    def table_path(self, table_id):
        return f"{self.slug}/tables/{table_id}-{slug(self.tables.get(table_id))}.txt"


class Renderer:
    """Turn an element subtree into indented lines; record what each raw class reached."""

    def __init__(self, ex):
        self.ex = ex
        self.cat = None
        self.parent = {}
        self.seen = set()       # ids of <Calculation> elements whose text is shown
        self.reached = set()    # raw classes that reached output
        self.codes = defaultdict(Counter)
        self.step_text = ""     # normalized StepText of the step being rendered
        self.unresolved = []    # (tag, id, name, status) for the object being rendered

    @property
    def calcs(self):
        return len(self.seen)

    def key(self, el):
        p = self.parent.get(el)
        return f"{p.tag if p is not None else ''}/{el.tag}"

    def mark(self, el, attrs=(), text=False):
        k = self.key(el)
        self.reached.add(k)
        for a in attrs:
            self.reached.add(f"{k}@{a}")
        if text:
            self.reached.add(f"{k}#text")

    def refs(self, display):
        """One compact line from a <DisplayCalculation>: fields, functions, custom functions."""
        out = []
        for chunk in display.iter("Chunk"):
            kind = chunk.get("type")
            text = (chunk.text or "").strip()
            if kind == "FieldRef":
                f = chunk.find("Field")
                if f is not None:
                    tbl = f.get("table") or ""
                    out.append(f"{tbl}::{f.get('name')}#{f.get('id')}" if tbl else f"{f.get('name')}#{f.get('id')}")
            elif kind == "CustomFunctionRef":
                out.append(f"cf:{text}")
            elif kind == "FunctionRef":
                # The DDR types a // comment // as FunctionRef too; the comment is in the text.
                if _IDENT.fullmatch(text):
                    out.append(f"fn:{text}")
            elif kind not in ("NoRef", None):
                out.append(f"{kind}:{one_line(text)}")
        return list(dict.fromkeys(out))

    def calc(self, el, parent, depth, show_text=True, inactive=False):
        self.seen.add(id(el))
        self.mark(el, el.attrib, text=True)
        pad = "  " * depth
        display = parent.find("DisplayCalculation") if parent is not None else None
        refs = self.refs(display) if display is not None else []
        raw = (el.text or "").rstrip()
        if not show_text and norm(raw) in self.step_text:
            # The step line already shows this calculation; keep only its refs: which
            # field (by id), custom function, function or table occurrence it touches.
            return [f"{pad}refs: {', '.join(refs)}"] if refs else []
        attrs = " ".join(f"{k}={_q(v)}" for k, v in el.attrib.items())
        flag = " (inactive)" if inactive else ""
        lines = [f"{pad}Calculation{(' ' + attrs) if attrs else ''}{flag}:"]
        for ln in lines_of(raw) if raw else [""]:
            lines.append(f"{pad}  | {ln}")
        if refs:
            lines.append(f"{pad}  refs: {', '.join(refs)}")
        return lines

    # ── references ───────────────────────────────────────────────────────────

    def ref_status(self, el, parent):
        """None when the reference resolves; else none / missing / separator / external."""
        tag, oid, name = el.tag, el.get("id"), el.get("name")
        cat = self.cat
        if tag in ("Script", "Layout", "ValueList") and parent is not None:
            fr = parent.find("FileReference")
            if fr is not None:
                cat = self.ex.data_source_file(self.cat, fr.get("id"))
                if cat is None:
                    return "external"
        if tag == "Field" and "table" in el.attrib:
            if oid == "0":
                return "none"
            if not el.get("table"):
                return None if name else "missing"
            target = self.ex.base_table(self.cat, el.get("table"))
            if target is None:
                return "missing"
            if target == "external":
                return "external"
            tcat, btid = target
            return None if oid in tcat.fields.get(btid, ()) else "missing"
        if oid is None:
            return None
        if oid == "-1" and name == "<Current Table>":
            return None  # Truncate Table and similar steps on the current table
        if tag == "CustomMenuSet" and oid == "0" and not name:
            return None  # a layout's "[File Default]" menu set, not a broken reference
        if tag == "Script":
            ids, seps = cat.scripts, cat.script_seps
        elif tag == "Layout":
            ids, seps = cat.layouts, cat.layout_seps
        elif tag == "Table" and parent is not None and parent.tag != "TableList":
            ids, seps = cat.to_ids, set()
        elif tag == "FileReference":
            ids, seps = set(cat.data_sources), set()
        elif tag in cat.ids:
            ids, seps = cat.ids[tag], set()
        else:
            return None
        if oid == "0":
            return "none"
        if oid in seps:
            return "separator"
        if tag in ("Script", "Layout") and name == "--" and parent is not None and parent.tag != "Step":
            return None  # a privilege set's end-of-folder marker, not an object
        return None if oid in ids else "missing"

    def side_attrs(self, to_name):
        """to=<id> base=<table file> for one side of a relationship."""
        to = self.cat.tos.get(to_name)
        if to is None:
            return {"ref": "missing"}
        return {"to": to.get("id"), "base": self.ex.base_label(self.cat, to_name)}

    # ── element rendering ────────────────────────────────────────────────────

    def attrs(self, el, parent):
        """The attributes to print, with defaults dropped, codes decoded and line breaks as ¶."""
        tag = el.tag
        self.mark(el, el.attrib)
        attrs = {}
        for k, v in el.attrib.items():
            if k in ("rotation", "flags") and v == "0":
                continue
            if tag in FIELD_OPTION_TAGS and v == "False" and k not in KEEP_FALSE \
                    and INACTIVE_CHILD.get(k) not in self.inactive_children(el):
                continue
            if k == "Parameter" and el.find("Calculation") is not None:
                continue  # the Calculation child shows the same parameter
            if (tag, k) in CODE_SET:
                self.codes[(tag, k)][v] += 1
            if (tag, k) in DECODE and v in DECODE[(tag, k)]:
                v = f"{v}({DECODE[(tag, k)][v].replace(' ', '-')})"
            elif (tag, k) in BITS and v.isdigit():
                names = [n for b, n in BITS[(tag, k)].items() if int(v) & b]
                if int(v) & ~sum(BITS[(tag, k)]):
                    names.append("?")
                v = f"{v}({'+'.join(names)})"
            attrs[k] = v
        if tag == "Validation" and el.get("valuelist") == "True" and el.find("ValueList") is None:
            attrs["valuelist"] = "True(list-not-named-in-DDR)"
        style = el.find("Styles/CustomStyles/Name")
        if style is not None and (style.text or "").strip():
            self.mark(style, text=True)
            attrs["style"] = style.text.strip()
        bounds = el.find("Bounds")
        if bounds is not None:
            self.mark(bounds, bounds.attrib)
            attrs["bounds"] = ",".join(
                str(round(float(bounds.get(s, 0)))) for s in ("top", "left", "bottom", "right"))
        if tag in ("LeftTable", "RightTable") and el.get("name") is not None:
            attrs.update(self.side_attrs(el.get("name")))
        return attrs

    def inactive_children(self, el):
        """Tags of the children of a field option that hold a setting while the option is off."""
        if el.tag not in FIELD_OPTION_TAGS:
            return set()
        off = set()
        for k, v in el.attrib.items():
            child = el.find(INACTIVE_CHILD.get(k, "-"))
            if v == "False" and child is not None and (len(child) or (child.text or "").strip()):
                off.add(child.tag)
        if el.get("constant") == "True":
            off.discard("Calculation")  # the DDR mirrors a constant as a Calculation
        return off

    def display_formats(self, el):
        """One line of the number, date and time formats under el that differ from the default.
        They sit in <ExtendedAttributes> (layout fields, merge text) or directly (chart axes)."""
        ext = el.find("ExtendedAttributes")
        if ext is None:
            ext = el
        else:
            self.mark(ext, ext.attrib)
        if ext.find("NumFormat") is None and ext.find("DateFormat") is None and ext.find("TimeFormat") is None:
            return None
        parts = []
        num = ext.find("NumFormat")
        if num is not None:
            self.mark(num, num.attrib)
            self.codes[("NumFormat", "flags")][num.get("flags")] += 1
            if num.get("flags") not in ("0", "2304"):
                a = dict(num.attrib)
                a.pop("charStyle", None)
                for k in ("thousandsSep", "decimalPoint"):
                    a[k] = _char(a.get(k))
                parts.append("number " + " ".join(f"{k}={_q(v)}" for k, v in a.items()))
        date = ext.find("DateFormat")
        if date is not None:
            self.mark(date, date.attrib)
            self.codes[("DateFormat", "format")][date.get("format")] += 1
            for e in date:
                self.mark(e, e.attrib, text=True)
            if date.get("format") != "0":
                a = {k: v for k, v in date.attrib.items() if k != "charStyle"}
                a["separator"] = _char(a.get("separator"))
                elems = ",".join(e.text or "" for e in date.iter("DateElement"))
                seps = "|".join(e.text or "" for e in date.iter("DateElementSep"))
                parts.append("date " + " ".join(f"{k}={_q(v)}" for k, v in a.items())
                             + f" elements={elems} separators={_q(seps)}")
        time = ext.find("TimeFormat")
        if time is not None:
            self.mark(time, time.attrib)
            self.codes[("TimeFormat", "flags")][time.get("flags")] += 1
            if time.get("flags") not in ("0", "143"):
                a = {k: v for k, v in time.attrib.items() if k != "charStyle"}
                a["separator"] = _char(a.get("separator"))
                parts.append("time " + " ".join(f"{k}={_q(v)}" for k, v in a.items()))
        return "Display: " + "; ".join(parts) if parts else None

    def field_obj_lines(self, el, pad):
        """Field and value list of a layout field, with ids, from DDRInfo."""
        lines = []
        info = el.find("DDRInfo")
        if info is None:
            return lines, set()
        self.mark(info)
        f, vl = info.find("Field"), info.find("ValueList")
        consumed = set()
        if f is not None:
            self.mark(f, f.attrib)
            if el.find("Name") is not None:
                self.mark(el.find("Name"), text=True)  # the same TO::name, without the id
            line = f"{pad}  Field: {f.get('table')}::{f.get('name')}#{f.get('id')}"
            if f.get("maxRepetition", "1") != "1":
                line += f" rep={f.get('repetition')}/{f.get('maxRepetition')}"
            line += self.ref_suffix(f, info)
            lines.append(line)
            consumed.add("Name")
        if vl is not None:
            self.mark(vl, vl.attrib)
            if el.find("ValueList") is not None:
                self.mark(el.find("ValueList"), text=True)
            lines.append(f"{pad}  ValueList: {vl.get('name')}#{vl.get('id')}" + self.ref_suffix(vl, info))
            consumed.add("ValueList")
        return lines, consumed

    def ref_suffix(self, el, parent):
        status = self.ref_status(el, parent)
        if status:
            self.unresolved.append((el.tag, el.get("id"), el.get("name") or "", status))
            return f" ref={status}"
        return ""

    def element(self, el, depth=0, calc_text=True, parent=None, defn=False, inactive=False):
        tag = el.tag
        if tag in SKIP:
            return []
        if tag == "Calculation":
            return self.calc(el, parent, depth, show_text=calc_text, inactive=inactive)
        pad = "  " * depth
        flag = "(inactive) " if inactive else ""
        if tag == "TextObj":
            # Label text lives inside the character-style runs, which are otherwise skipped.
            runs = el.find("CharacterStyleVector")
            if runs is not None:
                self.mark(runs)
            datas = list((runs if runs is not None else el).iter("Data"))
            for d in datas:
                self.mark(d, text=True)
            label = "".join(d.text or "" for d in datas).strip()
            attrs = self.attrs(el, parent)
            head = f"{pad}Text" + "".join(f" {k}={_q(v)}" for k, v in attrs.items())
            label_lines = lines_of(label)
            if not label:
                out = [head] if attrs else []
            elif len(label_lines) == 1:
                out = [f"{head}: {_q(label_lines[0])}"]
            else:
                out = [head] + [f"{pad}  | {ln}" for ln in label_lines]
            fmt = self.display_formats(el)
            if fmt:
                out.append(f"{pad}  {fmt}")
            return out + [ln for c in el if c.tag not in SKIP
                          for ln in self.element(c, depth + 1, calc_text, parent=el)]
        if tag == "Format":
            # A conditional format's effect is its CSS; 500pt text is how FileMaker hides things.
            self.mark(el, el.attrib)
            props = css_props(el)
            fa = "".join(f" {k}={_q(v)}" for k, v in el.attrib.items())
            return [f"{pad}Format{fa}: {props}"] if props or fa else []
        if tag == "Button" and parent is not None and parent.tag == "Buttons":
            # Show Custom Dialog: Get ( LastMessageChoice ) returns this number.
            self.mark(el, el.attrib)
            calc = el.find("Calculation")
            label = ""
            if calc is not None:
                self.seen.add(id(calc))
                self.mark(calc, calc.attrib, text=True)
                label = one_line(calc.text or "")
            n = list(parent).index(el) + 1
            fa = "".join(f" {k}={_q(v)}" for k, v in el.attrib.items())
            return [f"{pad}Button {n}{fa}: {label}" if label else f"{pad}Button {n}{fa}"]
        if tag == "PlatformData":
            self.mark(el, el.attrib, text=True)
            return [f"{pad}PlatformData" + "".join(f" {k}={_q(v)}" for k, v in el.attrib.items())
                    + f": ({len((el.text or '').strip()) // 2} bytes of printer settings, not shown)"]
        attrs = self.attrs(el, parent)
        if not defn:
            status = self.ref_status(el, parent)
            if status:
                attrs["ref"] = status
                self.unresolved.append((tag, el.get("id"), el.get("name") or "", status))
            elif tag in ("Script", "Layout", "ValueList") and parent is not None \
                    and parent.find("FileReference") is not None:
                tcat = self.ex.data_source_file(self.cat, parent.find("FileReference").get("id"))
                if tcat is not None and tcat is not self.cat:
                    attrs["in"] = tcat.slug
        pre, consumed = [], set()
        if tag == "FieldObj":
            pre, consumed = self.field_obj_lines(el, pad)
        fmt = self.display_formats(el)
        if fmt:
            pre.append(f"{pad}  {fmt}")
        children = [c for c in el if c.tag not in SKIP and c.tag != "Bounds" and c.tag not in consumed]
        text = (el.text or "").strip()
        if text:
            self.mark(el, text=True)
        if not attrs and not text and not children and not pre:
            return []
        off = self.inactive_children(el)
        sub = list(pre)
        for c in children:
            sub += self.element(c, depth + 1, calc_text, parent=el, inactive=c.tag in off)
        if not attrs and not text and not sub:
            return []  # a wrapper whose content was all presentation or already shown
        head = pad + flag + tag + "".join(f" {k}={_q(v)}" for k, v in attrs.items())
        lines = []
        tlines = lines_of(text) if text else []
        if len(tlines) == 1 and len(text) < 160:
            lines.append(f"{head}: {text}")
        else:
            lines.append(head)
            for ln in tlines:
                lines.append(f"{pad}  | {ln}")
        return lines + sub


class Exploder:
    def __init__(self, out_dir):
        self.out = out_dir
        self.r = Renderer(self)
        self.rows = []
        self.unresolved = []
        self.counts = Counter()
        self.catalogs = {}       # file stem (lower case) -> Catalog
        self.bad_lines = []      # paths with a line break a reader would split differently

    def write(self, src, kind, oid, name, folder, xpath, header_extra, body):
        rel = os.path.join(slug(src, 80), kind, f"{oid}-{slug(name)}.txt")
        path = os.path.join(self.out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        head = [f"# {SINGULAR.get(kind, kind)} {oid}: {one_line(name)}", f"# file: {src}"]
        if folder:
            head.append(f"# folder: {folder}")
        head.append(f"# source: {xpath}")
        head += [f"# {one_line(h)}" for h in header_extra]
        text = "\n".join(head + [""] + body) + "\n"
        if len(text.splitlines()) != text.count("\n"):
            self.bad_lines.append(rel)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.rows.append((src, kind, oid, name, folder, rel,
                          hashlib.sha256(text.encode()).hexdigest(), str(text.count("\n"))))
        for row in self.r.unresolved:
            self.unresolved.append((rel,) + row)
        self.r.unresolved = []
        self.counts[kind] += 1

    # ── cross-file resolution ────────────────────────────────────────────────

    def data_source_file(self, cat, ds_id):
        """The Catalog a data source points at, or None when it is not in this DDR set."""
        ds = cat.data_sources.get(ds_id)
        if ds is None:
            return None
        for p in reference_paths(ds):
            target = self.catalogs.get(_strip_fm_extension(path_target_name(p)).lower())
            if target is not None:
                return target
        return None

    def base_table(self, cat, to_name):
        """(Catalog, base table id) of a TO; "external" when its file is not in the set."""
        to = cat.tos.get(to_name)
        if to is None:
            return None
        fr = to.find("FileReference")
        tcat = cat if fr is None else self.data_source_file(cat, fr.get("id"))
        if tcat is None:
            return "external"
        return tcat, to.get("baseTableId")

    def base_label(self, cat, to_name):
        target = self.base_table(cat, to_name)
        if target is None:
            return "missing"
        if target == "external":
            return "external"
        tcat, btid = target
        return tcat.table_path(btid) if btid in tcat.tables else "missing"

    # ── per-catalog renderers ────────────────────────────────────────────────

    def tables(self, src, cat):
        self.r.mark(cat)
        for t in cat.iter("BaseTable"):
            self.r.mark(t, t.attrib)
            fc = t.find("FieldCatalog")
            if fc is not None:
                self.r.mark(fc)
            fields = t.findall("FieldCatalog/Field") or t.findall("Field")
            extra = [f"fields: {len(fields)}", f"records: {t.get('records')}"]
            if (t.get("comment") or "").strip():
                extra.append(f"comment: {t.get('comment')}")
            if t.get("shadow") == "True":
                extra.append("shadow: True (external SQL table)")
            ref = t.find("DataSourceRef")
            if ref is not None:
                self.r.mark(ref, ref.attrib)
                ds = next((d for d in self.r.cat.data_sources.values() if d.get("name") == ref.get("name")), None)
                where = f"{self.r.cat.slug}/data-sources/{ds.get('id')}-{slug(ds.get('name'))}.txt" if ds is not None \
                    else "ref=missing"
                extra.append(f"external: data source {ref.get('name')} ({where}) "
                             f"table {ref.get('catalogName')}.{ref.get('schemaName')}.{ref.get('tableName')}")
            body = []
            for f in fields:
                body += self.r.element(f, 0, defn=True)
                ae = f.find("AutoEnter")
                if (f.get("fieldType") == "Calculated" and f.find("Calculation") is None) or \
                        (ae is not None and ae.get("calculation") == "True" and ae.find("Calculation") is None):
                    body.append("  (no formula in DDR)")
                body.append("")
            self.write(src, "tables", t.get("id"), t.get("name"), "",
                       f"BaseTableCatalog/BaseTable[@id={t.get('id')}]", extra, body)

    def occurrences(self, src, graph):
        self.r.mark(graph)
        for wrap in graph:
            self.r.mark(wrap)
        rels = graph.findall("RelationshipList/Relationship")
        by_to = {}
        for rel in rels:
            for side in ("LeftTable", "RightTable"):
                s = rel.find(side)
                if s is not None:
                    by_to.setdefault(s.get("name"), []).append(rel)
        for to in graph.findall("TableList/Table"):
            body = self.r.element(to, defn=True)
            mine = by_to.get(to.get("name"), [])
            body += ["", f"relationships: {len(mine)}"]
            for rel in mine:
                body += [""] + self.r.element(rel, defn=True)
            self.write(src, "table-occurrences", to.get("id"), to.get("name"), "",
                       f"RelationshipGraph/TableList/Table[@id={to.get('id')}]",
                       [f"base table: {self.base_label(self.r.cat, to.get('name'))}"], body)
        # Relationships are also written once each, so a relationship is never only a copy.
        for rel in rels:
            l, r = rel.find("LeftTable"), rel.find("RightTable")
            name = f"{l.get('name') if l is not None else '?'} = {r.get('name') if r is not None else '?'}"
            self.write(src, "relationships", rel.get("id"), name, "",
                       f"RelationshipGraph/RelationshipList/Relationship[@id={rel.get('id')}]", [],
                       self.r.element(rel, defn=True))

    def walk_groups(self, el, path, groups, item_tag, on_item):
        for c in el:
            if c.tag == "Group":
                self.r.mark(c, c.attrib)
                g = f"id={c.get('id')} " + " ".join(f"{k}={v}" for k, v in c.attrib.items()
                                                     if k not in ("id", "name"))
                self.walk_groups(c, f"{path} / {c.get('name')}" if path else c.get("name"),
                                 groups + [g.strip()], item_tag, on_item)
            elif c.tag == item_tag:
                on_item(c, path, groups)

    def scripts(self, src, cat):
        self.r.mark(cat)
        self.walk_groups(cat, "", [], "Script", lambda sc, path, groups: self.script(src, sc, path, groups))

    def script(self, src, sc, folder, groups):
        steps = sc.findall("StepList/Step")
        self.r.mark(sc, sc.attrib)
        if sc.get("name") == "-" and not steps:
            self.counts["separators-skipped"] += 1
            return
        if sc.find("StepList") is not None:
            self.r.mark(sc.find("StepList"))
        body, disabled = [], 0
        for n, st in enumerate(steps, 1):
            self.r.mark(st, st.attrib)
            on = st.get("enable", "True") == "True"
            disabled += not on
            raw = (st.findtext("StepText") or "").strip()
            if st.find("StepText") is not None:
                self.r.mark(st.find("StepText"), text=True)
            if st.get("id") == "89" and st.find("Text") is not None:
                self.r.mark(st.find("Text"), text=True)  # comment text; StepText holds it
            text = raw or ("#" if st.get("id") == "89" else st.get("name") or "")
            if not on and text.startswith("//"):
                text = text[2:].lstrip()
            first, *rest = lines_of(text)
            body.append(f"{n:>4} {'   ' if on else '// '}{first}")
            body += [f"{'':>4}    {ln}" for ln in rest]
            # Options StepText does not show (restored find requests, sort keys, import maps,
            # file references, script/layout ids), each calculation StepText leaves out or
            # truncates, and the refs of every calculation in the step.
            self.r.step_text = norm(raw)
            for c in st:
                if c.tag == "StepText" or (st.get("id") == "89" and c.tag == "Text"):
                    continue
                body += [f"{'':>8}{ln}" for ln in self.r.element(c, 0, calc_text=False, parent=st)]
            self.r.step_text = ""
        options = " ".join(f"{k}={v}" for k, v in sc.attrib.items() if k not in ("id", "name"))
        extra = [f"steps: {len(steps)} ({disabled} disabled)", f"options: {options}"]
        if groups:
            extra.append(f"folder group: {groups[-1]}")
        self.write(src, "scripts", sc.get("id"), sc.get("name"), folder,
                   f"ScriptCatalog/Script[@id={sc.get('id')}]", extra, body)

    def layouts(self, src, cat):
        self.r.mark(cat)

        def one(c, path, groups):
            self.r.mark(c, c.attrib)
            if c.get("name") == "-" and c.find(".//Object") is None:
                self.counts["separators-skipped"] += 1
                return
            extra = [f"objects: {len(c.findall('.//Object'))}"]
            theme = c.find("Theme")
            if theme is not None:
                self.r.mark(theme)
                extra.append(f"theme: {theme.get('name')}")
            if groups:
                extra.append(f"folder group: {groups[-1]}")
            self.write(src, "layouts", c.get("id"), c.get("name"), path,
                       f"LayoutCatalog/Layout[@id={c.get('id')}]", extra, self.r.element(c, defn=True))
        self.walk_groups(cat, "", [], "Layout", one)

    def generic(self, src, cat, kind):
        """Every catalog item with an id becomes one file. Folders (<Group>) and id-less
        wrappers of items (<Inbound>, <BaseDirectoryList>) are walked; the catalog's own
        attributes and id-less settings go to <kind>/catalog-<Tag>.txt."""
        self.r.mark(cat, cat.attrib)
        rest = []

        def walk(el, path):
            for c in el:
                if c.tag == "Group" and c.get("name") is not None and kind != "privilege-sets":
                    self.r.mark(c, c.attrib)
                    walk(c, f"{path} / {c.get('name')}" if path else c.get("name"))
                elif c.get("id") is None and any(g.get("id") is not None for g in c):
                    self.r.mark(c, c.attrib)
                    walk(c, f"{path} / {c.tag}" if path else c.tag)
                elif c.get("id") is None:
                    rest.append(c)
                else:
                    name = c.get("name") or c.findtext("Name") or c.tag
                    self.write(src, kind, c.get("id"), name, path, f"{cat.tag}/{c.tag}[@id={c.get('id')}]",
                               [], self.r.element(c, 0, defn=True))
        walk(cat, "")
        if cat.attrib or rest:
            body = [" ".join(f"{k}={_q(v)}" for k, v in cat.attrib.items())] if cat.attrib else []
            for c in rest:
                body += self.r.element(c, 0, defn=True)
            self.write(src, kind, "catalog", cat.tag, "", cat.tag, [], body)

    # ── driver ───────────────────────────────────────────────────────────────

    def load(self, paths):
        """Parse every DDR of the set, so cross-file references resolve both ways."""
        files = []
        for p in paths:
            root = parse_xml(p).getroot()
            for file_el in root.iter("File"):
                cat = Catalog(file_el)
                self.catalogs[cat.stem] = cat
                files.append((root, cat))
        return files

    def explode(self, paths):
        """Yield (file, raw calculations, shown calculations, uncovered classes) per <File>."""
        for root, cat in self.load(paths):
            file_el, src = cat.el, cat.name
            self.r.cat = cat
            self.r.parent = {c: p for p in root.iter() for c in p}
            self.r.seen, self.r.reached = set(), set()
            self.r.mark(file_el, file_el.attrib)
            raw_calcs = sum(1 for _ in file_el.iter("Calculation"))
            unread = sum(1 for el in file_el.iter("ThemeCatalog") for _ in el.iter("Calculation"))
            for c in file_el:
                tag = c.tag
                kind = CATALOG_KIND.get(tag, slug(tag).lower())
                if tag == "BaseTableCatalog":
                    self.tables(src, c)
                elif tag == "RelationshipGraph":
                    self.occurrences(src, c)
                elif tag == "ScriptCatalog":
                    self.scripts(src, c)
                elif tag == "LayoutCatalog":
                    self.layouts(src, c)
                elif tag == "Options":
                    extra = [f"host: {file_el.get('path')}",
                             f"ddr: FileMaker {root.get('version')} {root.get('creationDate')}"]
                    self.write(src, "file", "0", "options", "", "Options", extra,
                               self.r.element(c, defn=True))
                elif tag == "ThemeCatalog":
                    continue
                else:
                    self.generic(src, c, kind)
            yield src, raw_calcs - unread, self.r.calcs, self.uncovered(file_el)
            self.r.parent = {}

    def uncovered(self, file_el):
        """Raw classes that reached no object file and are not presentation."""
        raw, stack = set(), [file_el]
        while stack:
            el = stack.pop()
            if el.tag in UNREAD:
                continue
            k = self.r.key(el)
            raw.add(k)
            raw.update(f"{k}@{a}" for a in el.attrib)
            if (el.text or "").strip():
                raw.add(f"{k}#text")
            stack.extend(el)
        return sorted(k for k in raw - self.r.reached
                      if not any(fnmatch.fnmatchcase(k, p) for p in PRESENTATION))

    def write_index(self):
        with open(os.path.join(self.out, "index.tsv"), "w", encoding="utf-8") as fh:
            fh.write("file\tkind\tid\tname\tfolder\tpath\tsha256\tlines\n")
            for row in sorted(self.rows, key=lambda r: (r[0], r[1], _num(r[2]))):
                fh.write("\t".join(one_line(str(v)).replace("\t", " ") for v in row) + "\n")
        with open(os.path.join(self.out, "unresolved.tsv"), "w", encoding="utf-8") as fh:
            fh.write("path\ttag\tid\tname\tstatus\n")
            for row in self.unresolved:
                fh.write("\t".join(one_line(str(v)).replace("\t", " ") for v in row) + "\n")
        self.write_legend()

    def write_legend(self):
        statuses = Counter(r[-1] for r in self.unresolved)
        out = [
            "# Legend",
            "",
            "Markers and codes used in these object files. Generated by explode_ddr.py.",
            "",
            "## Conventions",
            "",
            "- An option that is not printed has its default value: False for a field option,",
            "  0 for `flags` and `rotation`.",
            "- `(inactive)` marks a setting the DDR keeps while its option is off, for example an",
            "  auto-enter calculation with `calculation=False`. FileMaker does not run it.",
            "- `refs:` lists the fields (`TO::field#id`), custom functions (`cf:`) and functions",
            "  (`fn:`) a calculation uses.",
            "- In a script, a step option shows only its `refs:` line when the step text already",
            "  shows the calculation; otherwise the full calculation is printed under the option.",
            "- `¶` in a single-line value is a line break in the raw value.",
            "- `<Field Missing>`, `<Table Missing>`, `<Function Missing>`, `<unknown>` are",
            "  FileMaker's own markers in the DDR for a deleted target.",
            "- `Field: TO::name#id rep=r/max` on a layout field gives the field id from DDRInfo.",
            "  `rep` is printed only for a repeating field.",
            "- `Display:` on a layout field or merge text gives a number, date or time format",
            "  that is not the default (number flags 0 or 2304, date format 0, time flags 0 or 143).",
            "- `PlatformData` (print setup) is binary and is not shown.",
            "- AutoEnter `Serial`: the DDR does not say if serial numbering is on.",
            "- The DDR has no layout parts (header, body, footer) and no layout view type.",
            "- `(no formula in DDR)` on a field: the field is calculated, or has an auto-enter",
            "  calculation switched on, but the DDR has no formula text for it.",
            "- `<Function Missing>` in a calculation is also a plugin function (for example",
            "  `MBS`, `FTPeek`) whose plugin was not installed when the DDR was made.",
            "- A `cf:` ref can be a custom-function parameter with the same name as a custom",
            "  function: the DDR types it as a function reference. Check the function's parameters.",
            "- In a script, a step's text can run over several lines; the continuation lines have",
            "  the same indent as the option lines under the step.",
            "- Script step options name fields as `Field table=<TO> id=<n> repetition=<r> name=<f>`.",
            "  `Field table=\"\" id=0 ref=none` is an empty slot (for example an unused dialog input).",
            "- A trigger's or button's parameter sits under its `Script` line.",
            "- A disabled script step prints as `<n> // <step>`; a live step as `<n>    <step>`.",
            "- A find, sort or import step with `Restore state=False` still shows its saved",
            "  request, sort order or map; FileMaker does not use it when the step runs.",
            "- On a layout, a step's text may print as a bare `StepText` line followed by `|` lines.",
            "- `CustomMenuSet id=0 name=\"\"` on a layout is FileMaker's `[File Default]`: the",
            "  layout uses the menu set named in the file options.",
            "- `Import Records` shows its target table occurrence and field map. The DDR often does",
            "  not include the import source file or path.",
            "- A table occurrence whose data source has `ref=missing` shows `base table: external`:",
            "  its file is not in this DDR set and its data source entry is gone.",
            "- A privilege set's `[Any New Layout]`, `[Any New Table]`, `[Any New Field]` entries set",
            "  the access for objects added later. `FieldAccess value=Limited` with no field list",
            "  restricts no field beyond the table rule.",
            "",
            "## References",
            "",
            "A reference to an id that does not resolve has a `ref=` marker, and a row in",
            "`unresolved.tsv`:",
            "",
            "- `ref=none`: the id is 0 (nothing selected, or chosen by calculation at run time).",
            "- `ref=missing`: the id is not in the target catalog (deleted in the source).",
            "- `ref=separator`: the id is a `-` separator, which has no object file.",
            "- `ref=external`: the target file is not in this DDR set.",
            "- `in=<file>`: the target is in another file of the set.",
            "- A table occurrence header and each relationship side give `base=` the path of",
            "  the base table file, in whichever file of the set holds it.",
            "",
            "Counts in this run: " + (", ".join(f"{k} {v}" for k, v in sorted(statuses.items())) or "none"),
            "",
            "## Relationship options",
            "",
            "- `cascadeCreate=True` on a side: records can be created in that side's table",
            "  through this relationship.",
            "- `cascadeDelete=True` on a side: records in that side's table are deleted when",
            "  the related record on the other side is deleted.",
            "",
            "## Codes",
            "",
            "Decoded codes are printed as `value(meaning)`. The meanings come from the values",
            "observed in real DDRs (for example displayType 6 is only on date fields). Values",
            "with no known meaning are printed raw and marked `unknown` below.",
            "",
        ]
        for tag, attr in sorted(CODE_SET):
            seen = self.r.codes.get((tag, attr))
            if not seen:
                continue
            table = DECODE.get((tag, attr))
            bits = BITS.get((tag, attr))
            out.append(f"### {tag}@{attr}")
            out.append("")
            ranked = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0] or ""))
            for v, n in ranked[:LEGEND_VALUES]:
                if table:
                    meaning = table.get(v, "unknown")
                elif bits and (v or "").isdigit():
                    names = [nm for b, nm in bits.items() if int(v) & b]
                    meaning = "+".join(names) or "none"
                    if int(v) & ~sum(bits):
                        meaning += " +unknown bits"
                else:
                    meaning = "unknown"
                out.append(f"- `{v}`: {meaning} ({n})")
            if len(ranked) > LEGEND_VALUES:
                rest = ranked[LEGEND_VALUES:]
                out.append(f"- {len(rest)} more values, {sum(n for _, n in rest)} uses")
            out.append("")
        with open(os.path.join(self.out, "LEGEND.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))


def _char(code):
    """A separator stored as a character code: 44 -> ','; 0 or absent -> ''.

    FileMaker also writes codes that are no character (56144, a lone UTF-16
    surrogate): they show as U+DB50, since a strict UTF-8 write rejects them.
    """
    if not (code and code.isdigit() and code != "0"):
        return ""
    n = int(code)
    return f"U+{n:04X}" if 0xD800 <= n <= 0xDFFF or n > 0x10FFFF else chr(n)


def _num(v):
    return int(v) if str(v).isdigit() else 0


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
    print(f"Exploding {len(files)} DDR file(s) ...")
    for src, raw_calcs, shown, uncovered in ex.explode(files):
        print(f"  {src}: {raw_calcs} calculations in raw XML, {shown} shown")
        if shown < raw_calcs:
            print(f"  ERROR: {raw_calcs - shown} calculation(s) were not shown", file=sys.stderr)
            failed = True
        if uncovered:
            print(f"  ERROR: {len(uncovered)} raw class(es) reached no object file:", file=sys.stderr)
            for k in uncovered:
                print(f"    {k}", file=sys.stderr)
            failed = True
    ex.write_index()
    for rel in ex.bad_lines:
        print(f"  ERROR: a raw line break survived in {rel}", file=sys.stderr)
        failed = True
    for kind, n in sorted(ex.counts.items()):
        print(f"  {kind}: {n}")
    statuses = Counter(r[-1] for r in ex.unresolved)
    print(f"  unresolved references: {len(ex.unresolved)} "
          f"({', '.join(f'{k} {v}' for k, v in sorted(statuses.items())) or 'none'})")
    print(f"Wrote {len(ex.rows)} object files, index.tsv, unresolved.tsv and LEGEND.md to {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
