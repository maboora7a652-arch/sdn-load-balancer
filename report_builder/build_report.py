"""SDN Track 1 final report: publication-grade DOCX and print-PDF generator.

Run with Python 3.14 (python-docx 1.2.0, lxml, Pillow, pypdf):

    py -3.14 report_builder/build_report.py [--out PATH] [--validate]
    py -3.14 report_builder/build_report.py --pdf-only [--pdf PATH]

Inputs (imported from this directory):
    content_part1.py  META, ABSTRACT_PARAGRAPHS, KEYWORDS, CHAPTERS_PART1
    content_part2.py  CHAPTERS_PART2, REFERENCES, APPENDICES

The DOCX carries live Word fields (TOC, PAGE, NUMPAGES) refreshed by Word 16.0
COM in export_pdf.ps1. Because headless Word ExportAsFixedFormat hangs on this
host, export_pdf.ps1 invokes --pdf-only to render the matching print PDF via
Chrome headless with 2-pass exact TOC page-number synchronization and pypdf
heading bookmarks. Fully offline.
"""
from __future__ import annotations

import argparse
import datetime
import html as html_mod
import importlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Twips
from PIL import Image
from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
DEFAULT_OUT = ROOT / "output" / "report" / "sdn-track-1-report.docx"
DEFAULT_PDF = ROOT / "output" / "report" / "sdn-track-1-report.pdf"
VALIDATOR = Path(r"C:\Users\Fouad\.gemini\config\skills\docx\scripts\office\validate.py")
CHROME_CANDIDATES = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / r"Google\Chrome\Application\chrome.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / r"Google\Chrome\Application\chrome.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / r"Microsoft\Edge\Application\msedge.exe",
]

# Palette
NAVY, TEAL, SLATE, INK = "173B61", "0F6E6E", "475569", "1E293B"
RULE, SOFT, CODE_BG, CODE_INK, INLINE_BG = "CBD5E1", "F8FAFC", "F8FAFC", "0F172A", "F1F5F9"
CALLOUT_BG, WHITE = "F4F8F8", "FFFFFF"

# Fonts
BODY_FONT, HEAD_FONT, CODE_FONT, MATH_FONT, AR_FONT = "Times New Roman", "Segoe UI", "Consolas", "Cambria", "Arial"

# A4 geometry in DXA (1 mm = 56.6929 DXA): 17 mm T/B, 18.5 mm L/R -> 173 mm printable width
PAGE_W, PAGE_H = 11906, 16838
MARGIN_TB, MARGIN_LR = 964, 1049
TEXT_W = PAGE_W - 2 * MARGIN_LR  # 9808 DXA (173 mm = 6.81 in)
MAX_FIG_W_IN = 5.75
MAX_FIG_H_DIAGRAM_IN = 2.26
MAX_FIG_H_SHOT_IN = 2.48
MAX_FIG_H_TALL_SHOT_IN = 3.85

HEADER_TEXT = "ECE2606 \u00b7 Computer Networks \u2014 SDN Track 1: Intelligent Load Balancer with Fault Tolerance"
FOOTER_LEFT = "Helwan National University \u00b7 Intelligent Systems Engineering"

TEAM_DEFAULT = [
    ("921230064", "عبدالحميد أحمد"),
    ("921230066", "عبدالرحمن أحمد محمد محمد"),
    ("921230065", "عبدالرحمن أحمد فؤاد"),
    ("921230069", "عبدالرحمن عمرو عبدالحليم"),
    ("921230061", "صهيب وائل محمد"),
    ("921230068", "عبدالرحمن صلاح الدين يحي"),
]

PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
             "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
             "sectPr", "pPrChange"]
RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
             "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
             "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
             "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"]

ARABIC = r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+"
ARABIC_RUN_RE = re.compile(f"({ARABIC}(?:[ \\t]+{ARABIC})*)")
INLINE_RE = re.compile(
    r"\*\*(?=\S)(.+?)(?<=\S)\*\*|`([^`]+)`|(?<![\w/\\])\*(?=[^\s*/\\])([^*/\\]+?)(?<=[^\s*/\\])\*(?![\w*.])"
)
SCRIPT_RE = re.compile(r"([_^])(\{[^}]*\}|[A-Za-z0-9\u03b1-\u03c9\u0391-\u03a9](?![A-Za-z0-9]))")
NUM_RE = re.compile(r"^[\s+\-\u2212~<>\u2264\u2265\u2248]*\d[\d,.\s]*(?:\u00b1\s*[\d,.]+)?\s*"
                    r"(?:%|ms|s|Mbps|Gbps|pp|\u00d7|x|MB|KB)?$")


# --------------------------------------------------------------------------- XML helpers

def localname(e) -> str:
    return e.tag.split("}")[-1]


def el(tag: str, attrs: dict | None = None, children=()):
    e = OxmlElement(tag if ":" in tag else "w:" + tag)
    for k, v in (attrs or {}).items():
        if v is not None:
            e.set(qn(k if ":" in k else "w:" + k), str(v))
    for c in children:
        e.append(c)
    return e


def insert_ordered(parent, child, order):
    name = localname(child)
    for sib in list(parent):
        if localname(sib) == name:
            parent.remove(sib)
    idx = order.index(name)
    for sib in parent:
        n = localname(sib)
        if n in order and order.index(n) > idx:
            sib.addprevious(child)
            return child
    parent.append(child)
    return child


def ppr_of(p):
    return p._p.get_or_add_pPr()


def pbdr(parent_ppr, **sides):
    box = el("pBdr")
    for side in ("top", "left", "bottom", "right"):
        if side in sides:
            sz, color, space = sides[side]
            box.append(el(side, {"val": "single", "sz": sz, "space": space, "color": color}))
    insert_ordered(parent_ppr, box, PPR_ORDER)


def make_rpr(font=None, size=None, bold=None, italic=None, color=None, shade=None, spacing=None,
             vert=None, rtl=False, cs_font=None, underline=None):
    rpr = OxmlElement("w:rPr")

    def add(tag, **attrs):
        insert_ordered(rpr, el(tag, attrs), RPR_ORDER)

    if font or cs_font:
        add("rFonts", ascii=font, hAnsi=font, eastAsia=font, cs=cs_font or font)
    if bold is not None:
        add("b", val=None if bold else "0")
        add("bCs", val=None if bold else "0")
    if italic is not None:
        add("i", val=None if italic else "0")
        add("iCs", val=None if italic else "0")
    if color:
        add("color", val=color)
    if spacing:
        add("spacing", val=spacing)
    if size:
        add("sz", val=int(round(size * 2)))
        add("szCs", val=int(round(size * 2)))
    if underline:
        add("u", val=underline)
    if shade:
        add("shd", val="clear", color="auto", fill=shade)
    if vert:
        add("vertAlign", val=vert)
    if rtl:
        add("rtl")
        add("lang", val="en-US", bidi="ar-EG")
    return rpr if len(rpr) else None


def _run(text=None, **props):
    r = OxmlElement("w:r")
    rpr = make_rpr(**props)
    if rpr is not None:
        r.append(rpr)
    if text is not None:
        parts = re.split(r"(\t)", text)
        for part in parts:
            if part == "\t":
                r.append(el("tab"))
            elif part:
                t = el("t")
                t.text = part
                t.set(qn("xml:space"), "preserve")
                r.append(t)
    return r


def add_run(p, text: str, **props):
    text = (text or "").replace("\r", "").replace("\n", " ")
    if not text:
        return None
    last = None
    for seg in ARABIC_RUN_RE.split(text):
        if not seg:
            continue
        sp = dict(props)
        if ARABIC_RUN_RE.fullmatch(seg):
            sp.update(rtl=True, cs_font=AR_FONT)
        last = _run(seg, **sp)
        p._p.append(last)
    return last


def add_inline(p, text: str, code_size: float = 9.5, parse_math: bool = False, **base):
    text = (text or "").replace("\r", "").replace("\n", " ")
    emit = (lambda s, **kw: add_math(p, s, **kw)) if parse_math else (lambda s, **kw: add_run(p, s, **kw))
    pos = 0
    for m in INLINE_RE.finditer(text):
        emit(text[pos:m.start()], **base)
        if m.group(1) is not None:
            emit(m.group(1), **{**base, "bold": True})
        elif m.group(2) is not None:
            light = base.get("color") == WHITE
            add_run(p, m.group(2).strip(), **{**base, "font": CODE_FONT, "size": code_size, "bold": base.get("bold"),
                                              "color": WHITE if light else CODE_INK, "shade": None if light else INLINE_BG})
        else:
            emit(m.group(3), **{**base, "italic": True})
        pos = m.end()
    emit(text[pos:], **base)


def add_math(p, text: str, **props):
    pos = 0
    for m in SCRIPT_RE.finditer(text):
        add_run(p, text[pos:m.start()], **props)
        body = m.group(2)
        body = body[1:-1] if body.startswith("{") else body
        add_run(p, body, vert="subscript" if m.group(1) == "_" else "superscript", **props)
        pos = m.end()
    add_run(p, text[pos:], **props)


def add_field(p, instr: str, result: str, **props):
    for kind in ("begin", None, "separate", "result", "end"):
        if kind in ("begin", "separate", "end"):
            r = _run(**props)
            r.append(el("fldChar", {"fldCharType": kind}))
        elif kind is None:
            r = _run(**props)
            it = el("instrText")
            it.text = f" {instr} "
            it.set(qn("xml:space"), "preserve")
            r.append(it)
        else:
            r = _run(result, **props)
        p._p.append(r)


def clear_children(e, keep=()):
    for c in list(e):
        if localname(c) not in keep:
            e.remove(c)


# --------------------------------------------------------------------------- styles

def fix_rfonts(style, name):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = insert_ordered(rpr, el("rFonts"), RPR_ORDER)
    for k in list(rf.attrib):
        del rf.attrib[k]
    for a in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn("w:" + a), name)


def mk_style(doc, name, *, base="Normal", font=None, size=None, bold=None, italic=None, color=None,
             align=None, before=None, after=None, line=None, exact=None, keep_next=None, keep_lines=None,
             left=None, hanging=None, page_break=None, widow=None, rule_bottom=None):
    styles = doc.styles
    try:
        st = styles[name]
    except KeyError:
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = styles[base] if base else None
        st.quick_style = True
    f, pf = st.font, st.paragraph_format
    if font:
        f.name = font
        fix_rfonts(st, font)
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color:
        f.color.rgb = RGBColor.from_string(color)
    if align is not None:
        pf.alignment = align
    if before is not None:
        pf.space_before = Pt(before)
    if after is not None:
        pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing = line
    if exact is not None:
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = Pt(exact)
    if keep_next is not None:
        pf.keep_with_next = keep_next
    if keep_lines is not None:
        pf.keep_together = keep_lines
    if left is not None:
        pf.left_indent = Twips(left)
    if hanging is not None:
        pf.first_line_indent = Twips(-hanging)
    if page_break is not None:
        pf.page_break_before = page_break
    if widow is not None:
        pf.widow_control = widow
    if rule_bottom:
        pbdr(st.element.get_or_add_pPr(), bottom=rule_bottom)
    return st


def setup_styles(doc):
    L, C, J = WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY
    dd = doc.styles.element.find(qn("w:docDefaults"))
    if dd is not None:
        for rf in dd.iter(qn("w:rFonts")):
            for k in list(rf.attrib):
                del rf.attrib[k]
            for a in ("ascii", "hAnsi", "eastAsia", "cs"):
                rf.set(qn("w:" + a), BODY_FONT)
    # Strictly 12 pt Times New Roman body per assignment Section 11 rubric
    mk_style(doc, "Normal", base=None, font=BODY_FONT, size=12, color=INK, align=J, before=0, after=3.0,
             line=1.05, widow=True)
    mk_style(doc, "Heading 1", font=HEAD_FONT, size=16.5, bold=True, italic=False, color=NAVY, align=L, before=0,
             after=5.5, line=1.0, keep_next=True, keep_lines=True, page_break=True, rule_bottom=(12, NAVY, 3))
    mk_style(doc, "Heading 2", font=HEAD_FONT, size=12.5, bold=True, italic=False, color=TEAL, align=L, before=7,
             after=2.5, line=1.0, keep_next=True, keep_lines=True, page_break=False)
    mk_style(doc, "Heading 3", font=HEAD_FONT, size=11, bold=True, italic=False, color=NAVY, align=L, before=5,
             after=2, line=1.0, keep_next=True, keep_lines=True, page_break=False)
    mk_style(doc, "Front Heading", font=HEAD_FONT, size=16.5, bold=True, color=NAVY, align=L, before=0, after=7,
             line=1.0, keep_next=True, keep_lines=True, rule_bottom=(12, NAVY, 3))
    mk_style(doc, "Table Caption", font=HEAD_FONT, size=9.5, bold=True, color=NAVY, align=L, before=6, after=2.5,
             line=1.0, keep_next=True, keep_lines=True)
    mk_style(doc, "Figure Image", align=C, before=4, after=2, line=1.0, keep_next=True, keep_lines=True)
    mk_style(doc, "Figure Caption", font=HEAD_FONT, size=9, italic=True, color=SLATE, align=C, before=1,
             after=6, line=1.0, keep_lines=True)
    mk_style(doc, "Table Text", font=HEAD_FONT, size=8.5, color=INK, align=L, before=0, after=0, line=1.04)
    mk_style(doc, "Table Header", font=HEAD_FONT, size=9, bold=True, color=WHITE, align=L, before=0, after=0,
             line=1.04)
    mk_style(doc, "Callout Title", font=HEAD_FONT, size=10, bold=True, color=TEAL, align=L, before=0, after=2,
             line=1.0, keep_next=True)
    mk_style(doc, "Callout Text", size=10.5, align=J, before=0, after=2, line=1.06)
    mk_style(doc, "Code Title", font=HEAD_FONT, size=8.5, bold=True, color=NAVY, align=L, before=0, after=0,
             line=1.0, keep_next=True)
    mk_style(doc, "Code Line", font=CODE_FONT, size=8, color=CODE_INK, align=L, before=0, after=0, line=1.0)
    mk_style(doc, "Equation Formula", font=MATH_FONT, size=11.5, italic=True, color=INK, align=C, before=0,
             after=0, line=1.05)
    mk_style(doc, "Equation Number", font=HEAD_FONT, size=9.5, bold=True, color=NAVY, align=WD_ALIGN_PARAGRAPH.RIGHT,
             before=0, after=0, line=1.0)
    mk_style(doc, "Equation Note", size=9.5, color=SLATE, align=L, before=2, after=4, line=1.05)
    mk_style(doc, "Reference", size=9.5, align=L, before=0, after=2.2, line=1.05, left=460, hanging=460)
    mk_style(doc, "Spacer", size=2, align=L, before=0, after=0, exact=4)
    mk_style(doc, "Cover University", font=HEAD_FONT, size=22, bold=True, color=NAVY, align=C, before=8, after=2,
             line=1.0)
    mk_style(doc, "Cover Line", font=HEAD_FONT, size=12.5, color=INK, align=C, before=0, after=1, line=1.0)
    mk_style(doc, "Cover Title", font=HEAD_FONT, size=23, bold=True, color=NAVY, align=C, before=18, after=6,
             line=1.08)
    mk_style(doc, "Cover Subtitle", font=HEAD_FONT, size=12.5, color=SLATE, align=C, before=0, after=12, line=1.0)
    mk_style(doc, "Cover Label", font=HEAD_FONT, size=10, bold=True, color=TEAL, align=C, before=0, after=5,
             line=1.0)
    mk_style(doc, "Cover Meta", font=HEAD_FONT, size=10.5, color=INK, align=C, before=0, after=2.5, line=1.1)
    mk_style(doc, "Header", font=HEAD_FONT, size=8.5, color=SLATE, align=L, before=0, after=0, line=1.0)
    mk_style(doc, "Footer", font=HEAD_FONT, size=8.5, color=SLATE, align=L, before=0, after=0, line=1.0)
    for name in ("Header", "Footer"):
        ppr = doc.styles[name].element.get_or_add_pPr()
        for t in ppr.findall(qn("w:tabs")):
            ppr.remove(t)
    for name, hang in (("List Bullet", 260), ("List Number", 320)):
        st = mk_style(doc, name, size=12, align=J, before=0, after=1.5, line=1.08, left=520, hanging=hang)
        ppr = st.element.get_or_add_pPr()
        for n in ("numPr", "contextualSpacing"):
            for e in ppr.findall(qn("w:" + n)):
                ppr.remove(e)
    toc1 = mk_style(doc, "toc 1", font=HEAD_FONT, size=8.5, bold=True, color=NAVY, align=L, before=1.0, after=0,
                    line=0.95, left=0)
    toc2 = mk_style(doc, "toc 2", font=HEAD_FONT, size=7.8, color=INK, align=L, before=0, after=0, line=0.94,
                    left=260)
    for st in (toc1, toc2):
        st.paragraph_format.tab_stops.add_tab_stop(Twips(TEXT_W), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    try:
        hl = doc.styles["Hyperlink"]
    except KeyError:
        hl = doc.styles.add_style("Hyperlink", WD_STYLE_TYPE.CHARACTER)
    rpr = hl.element.get_or_add_rPr()
    clear_children(rpr)
    rpr.append(el("noProof"))


def setup_numbering(doc):
    root = doc.part.numbering_part.element
    bullet = parse_xml(
        '<w:abstractNum xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:abstractNumId="90">'
        '<w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="\u2022"/>'
        '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="520" w:hanging="260"/></w:pPr>'
        f'<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:hint="default"/><w:color w:val="{TEAL}"/>'
        '</w:rPr></w:lvl>'
        '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="\u2013"/>'
        '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="920" w:hanging="260"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:hint="default"/></w:rPr></w:lvl>'
        '</w:abstractNum>')
    decimal = parse_xml(
        '<w:abstractNum xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:abstractNumId="91">'
        '<w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/>'
        '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="520" w:hanging="320"/></w:pPr>'
        f'<w:rPr><w:rFonts w:ascii="{HEAD_FONT}" w:hAnsi="{HEAD_FONT}" w:cs="{HEAD_FONT}"/><w:b/>'
        f'<w:color w:val="{NAVY}"/><w:sz w:val="22"/></w:rPr></w:lvl>'
        '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%2)"/>'
        '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="920" w:hanging="320"/></w:pPr>'
        '</w:lvl></w:abstractNum>')
    first_num = root.find(qn("w:num"))
    for a in (bullet, decimal):
        if first_num is not None:
            first_num.addprevious(a)
        else:
            root.append(a)
    root.append(parse_xml('<w:num xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                          'w:numId="900"><w:abstractNumId w:val="90"/></w:num>'))
    return {"next": 901}


def new_number_list(state) -> int:
    nid = state["next"]
    state["next"] += 1
    root_w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    return nid, parse_xml(
        f'<w:num xmlns:w="{root_w}" w:numId="{nid}"><w:abstractNumId w:val="91"/>'
        '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>')


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Twips(PAGE_W), Twips(PAGE_H)
    sec.top_margin = sec.bottom_margin = Twips(MARGIN_TB)
    sec.left_margin = sec.right_margin = Twips(MARGIN_LR)
    sec.header_distance = sec.footer_distance = Twips(510)
    sec.gutter = Twips(0)
    sec.different_first_page_header_footer = True
    sec.first_page_header.is_linked_to_previous = False
    sec.first_page_footer.is_linked_to_previous = False
    hp = sec.header.paragraphs[0]
    hp.style = doc.styles["Header"]
    pbdr(ppr_of(hp), bottom=(4, RULE, 3))
    add_run(hp, HEADER_TEXT)
    fp = sec.footer.paragraphs[0]
    fp.style = doc.styles["Footer"]
    pbdr(ppr_of(fp), top=(4, RULE, 3))
    fp.paragraph_format.tab_stops.add_tab_stop(Twips(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
    add_run(fp, f"{FOOTER_LEFT}\tPage ")
    add_field(fp, "PAGE", "1")
    add_run(fp, " of ")
    add_field(fp, "NUMPAGES", "1")
    settings = doc.settings.element
    zoom = settings.find(qn("w:zoom"))
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    compat = settings.find(qn("w:compat"))
    if compat is None:
        compat = el("compat")
        later = [qn("w:" + n) for n in ("docVars", "rsids", "mathPr", "attachedSchema", "themeFontLang",
                                         "clrSchemeMapping", "doNotIncludeSubdocsInStats", "shapeDefaults",
                                         "decimalSymbol", "listSeparator")]
        anchor = next((c for c in settings if c.tag in later), None)
        if anchor is not None:
            anchor.addprevious(compat)
        else:
            settings.append(compat)
    for s in compat.findall(qn("w:compatSetting")):
        if s.get(qn("w:name")) == "compatibilityMode":
            compat.remove(s)
    compat.append(el("compatSetting", {"name": "compatibilityMode", "uri": "http://schemas.microsoft.com/office/word",
                                       "val": "15"}))


# --------------------------------------------------------------------------- DOCX tables & blocks

def set_table(tbl, widths, *, bidi_visual=False, jc=None, total=None):
    tblpr = tbl._tbl.tblPr
    clear_children(tblpr)
    total = total or sum(widths)
    if bidi_visual:
        tblpr.append(el("bidiVisual"))
    tblpr.append(el("tblW", {"w": total, "type": "dxa"}))
    if jc:
        tblpr.append(el("jc", {"val": jc}))
    tblpr.append(el("tblLayout", {"type": "fixed"}))
    tblpr.append(el("tblCellMar", children=[el(s, {"w": 0, "type": "dxa"}) for s in ("top", "left", "bottom", "right")]))
    grid = tbl._tbl.tblGrid
    for gc in list(grid):
        grid.remove(gc)
    for w in widths:
        grid.append(el("gridCol", {"w": w}))


def style_cell(cell, width, *, fill=None, borders=None, margins=None, valign="top"):
    tcpr = cell._tc.get_or_add_tcPr()
    clear_children(tcpr)
    tcpr.append(el("tcW", {"w": width, "type": "dxa"}))
    if borders:
        tb = el("tcBorders")
        for side in ("top", "left", "bottom", "right"):
            if side in borders:
                val, sz, color = borders[side]
                tb.append(el(side, {"val": val, "sz": sz, "space": 0, "color": color}))
        tcpr.append(tb)
    if fill:
        tcpr.append(el("shd", {"val": "clear", "color": "auto", "fill": fill}))
    if margins:
        tcpr.append(el("tcMar", children=[el(s, {"w": margins.get(s, 0), "type": "dxa"})
                                          for s in ("top", "left", "bottom", "right")]))
    tcpr.append(el("vAlign", {"val": valign}))


def style_row(row, *, cant_split=True, header=False):
    trpr = row._tr.get_or_add_trPr()
    if cant_split:
        trpr.append(el("cantSplit"))
    if header:
        trpr.append(el("tblHeader"))


def cell_paras(cell, texts, style, **base):
    out = []
    for i, text in enumerate(texts):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.style = cell.part.document.styles[style]
        add_inline(p, text, **base)
        out.append(p)
    return out


def spacer(doc):
    doc.add_paragraph(style="Spacer")


def to_dxa(weights_mm, n):
    if not weights_mm or len(weights_mm) != n:
        weights_mm = [1] * n
    s = float(sum(weights_mm))
    cols = [int(round(w / s * TEXT_W)) for w in weights_mm]
    cols[-1] += TEXT_W - sum(cols)
    return cols


def split_caption(caption, ident, kind):
    caption = (caption or "").strip()
    m = re.match(rf"^({kind}\s+[A-Za-z0-9.]+)\s*[:.]?\s*(.*)$", caption, re.S)
    if m:
        return m.group(1), m.group(2)
    if ident:
        return ident, caption
    return "", caption


def render_table(doc, blk, ctx):
    headers = [str(h) for h in blk.get("headers", [])]
    rows = [[str(c) for c in r] for r in blk.get("rows", [])]
    n = len(headers) or (len(rows[0]) if rows else 1)
    rows = [(r + [""] * n)[:n] for r in rows]
    widths = to_dxa(blk.get("col_widths_mm") or blk.get("col_weights"), n)
    prefix, rest = split_caption(blk.get("caption"), blk.get("id") or blk.get("number"), "Table")
    cap = doc.add_paragraph(style="Table Caption")
    add_run(cap, f"{prefix}: " if prefix and rest else prefix)
    add_inline(cap, rest, code_size=8.5)
    ctx["table_ids"].append(prefix)
    numeric = [all(NUM_RE.match(r[j].strip()) and len(r[j].strip()) <= 22 for r in rows if r[j].strip())
               and any(r[j].strip() for r in rows) for j in range(n)]
    arabic_col = [any(bool(re.fullmatch(f"{ARABIC}(?:[ \\t]+{ARABIC})*", r[j].strip() or "x")) for r in rows)
                  for j in range(n)]
    tbl = doc.add_table(rows=1 + len(rows) if headers else len(rows), cols=n)
    set_table(tbl, widths)
    mar = {"top": 36, "bottom": 36, "left": 75, "right": 75}
    base_rule = ("single", 4, RULE)
    for ri, row in enumerate(tbl.rows):
        is_head = bool(headers) and ri == 0
        data = headers if is_head else rows[ri - (1 if headers else 0)]
        style_row(row, header=is_head)
        zebra = (not is_head) and ((ri - (1 if headers else 0)) % 2 == 1)
        for ci, cell in enumerate(row.cells):
            borders = {"bottom": base_rule if not is_head else ("single", 4, NAVY),
                       "top": ("nil", 0, "auto"), "left": ("nil", 0, "auto"), "right": ("nil", 0, "auto")}
            style_cell(cell, widths[ci], fill=NAVY if is_head else (SOFT if zebra else None), borders=borders,
                       margins=mar, valign="center" if is_head or numeric[ci] else "top")
            texts = data[ci].split("\n") if data[ci] else [""]
            paras = cell_paras(cell, texts, "Table Header" if is_head else "Table Text", code_size=8)
            for p in paras:
                if numeric[ci]:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif is_head and arabic_col[ci]:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                if ri <= (1 if headers else 0):
                    p.paragraph_format.keep_with_next = True
                if re.fullmatch(f"{ARABIC}(?:[ \\t]+{ARABIC})*", texts[0].strip() or "x"):
                    insert_ordered(ppr_of(p), el("bidi"), PPR_ORDER)
                    p.alignment = None
            ctx["prose"].extend(t for t in texts if not is_head)
    spacer(doc)


def box_table(doc, *, accent, fill, accent_sz=30, margins=None):
    tbl = doc.add_table(rows=1, cols=1)
    set_table(tbl, [TEXT_W])
    style_row(tbl.rows[0])
    cell = tbl.rows[0].cells[0]
    style_cell(cell, TEXT_W, fill=fill,
               borders={"left": ("single", accent_sz, accent), "top": ("nil", 0, "auto"),
                        "bottom": ("nil", 0, "auto"), "right": ("nil", 0, "auto")},
               margins=margins or {"top": 90, "bottom": 90, "left": 180, "right": 160})
    return tbl, cell


def render_callout(doc, blk, ctx):
    _, cell = box_table(doc, accent=TEAL, fill=CALLOUT_BG)
    first = True
    if blk.get("title"):
        p = cell.paragraphs[0]
        p.style = doc.styles["Callout Title"]
        add_inline(p, blk["title"], code_size=9)
        first = False
    text = blk.get("text", "")
    for t in (text if isinstance(text, list) else str(text).split("\n")):
        if not t.strip():
            continue
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.style = doc.styles["Callout Text"]
        add_inline(p, t, code_size=9)
        ctx["prose"].append(t)
    spacer(doc)


def render_equation(doc, blk, ctx):
    formula, number = blk.get("formula") or blk.get("text", ""), blk.get("number", "")
    widths = [TEXT_W - 1050, 1050]
    tbl = doc.add_table(rows=1, cols=2)
    set_table(tbl, widths)
    style_row(tbl.rows[0])
    none = {s: ("nil", 0, "auto") for s in ("top", "left", "bottom", "right")}
    c0, c1 = tbl.rows[0].cells
    style_cell(c0, widths[0], fill=SOFT, borders=none, margins={"top": 70, "bottom": 70, "left": 120, "right": 120},
               valign="center")
    style_cell(c1, widths[1], borders=none, margins={"top": 70, "bottom": 70, "left": 50, "right": 0},
               valign="center")
    lines = [l for l in str(formula).split("\n") if l.strip()] or [""]
    for i, line in enumerate(lines):
        p = c0.paragraphs[0] if i == 0 else c0.add_paragraph()
        p.style = doc.styles["Equation Formula"]
        add_math(p, line)
    c1.paragraphs[0].style = doc.styles["Equation Number"]
    add_run(c1.paragraphs[0], number)
    if blk.get("note"):
        p = doc.add_paragraph(style="Equation Note")
        add_inline(p, blk["note"], code_size=8.5, parse_math=True)
        ctx["prose"].append(blk["note"])
    else:
        spacer(doc)


def render_code(doc, blk, ctx):
    lines = [str(l).replace("\r", "").replace("\t", "    ") for l in blk.get("lines", [])]
    tbl = doc.add_table(rows=2, cols=1)
    set_table(tbl, [TEXT_W])
    accent = {"left": ("single", 24, NAVY), "top": ("nil", 0, "auto"), "bottom": ("nil", 0, "auto"),
              "right": ("nil", 0, "auto")}
    small = len(lines) <= 34
    for r in tbl.rows:
        style_row(r, cant_split=small)
    head, body = tbl.rows[0].cells[0], tbl.rows[1].cells[0]
    style_cell(head, TEXT_W, fill="E8EEF5", borders=accent, margins={"top": 38, "bottom": 38, "left": 120, "right": 90},
               valign="center")
    style_cell(body, TEXT_W, fill=CODE_BG,
               borders={**accent, "bottom": ("single", 4, RULE)},
               margins={"top": 45, "bottom": 45, "left": 120, "right": 90})
    hp = head.paragraphs[0]
    hp.style = doc.styles["Code Title"]
    hp.paragraph_format.tab_stops.add_tab_stop(Twips(TEXT_W - 260), WD_TAB_ALIGNMENT.RIGHT)
    add_run(hp, blk.get("title", "Listing"))
    lang = blk.get("language")
    if lang:
        add_run(hp, "\t" + str(lang).upper(), bold=False, color=SLATE, size=7.5)
    for i, line in enumerate(lines or [""]):
        p = body.paragraphs[0] if i == 0 else body.add_paragraph()
        p.style = doc.styles["Code Line"]
        add_run(p, line if line else " ")
    spacer(doc)


def resolve_asset(name):
    if not name:
        raise FileNotFoundError("figure without file")
    cand = Path(name)
    for c in (cand, ROOT / cand, ASSETS / cand, ASSETS / cand.name):
        if c.is_file():
            return c
    hits = list(ASSETS.rglob(cand.name)) if ASSETS.exists() else []
    if hits:
        return hits[0]
    raise FileNotFoundError(f"asset not found: {name}")


def figure_dimensions(path: Path, req_w: float, bordered: bool):
    w = min(float(req_w or 5.6), MAX_FIG_W_IN)
    with Image.open(path) as im:
        pw, ph = im.size
    h = w * ph / pw
    if bordered and (pw / ph) < 1.45:
        cap_h = MAX_FIG_H_TALL_SHOT_IN
    else:
        cap_h = MAX_FIG_H_SHOT_IN if bordered else MAX_FIG_H_DIAGRAM_IN
    if h > cap_h:
        w, h = w * cap_h / h, cap_h
    return w, h


def render_figure(doc, blk, ctx):
    path = resolve_asset(blk.get("file") or blk.get("path"))
    bordered = bool(blk.get("border"))
    w, _ = figure_dimensions(path, blk.get("width_in", 5.6), bordered)
    prefix, rest = split_caption(blk.get("caption"), blk.get("id") or blk.get("number"), "Figure")
    p = doc.add_paragraph(style="Figure Image")
    shape = p.add_run().add_picture(str(path), width=Inches(w))
    shape._inline.docPr.set("descr", f"{prefix}: {rest}"[:240])
    shape._inline.docPr.set("name", prefix or path.stem)
    if bordered:
        sppr = shape._inline.graphic.graphicData.pic.spPr
        sppr.append(parse_xml('<a:ln xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" w="9525">'
                              f'<a:solidFill><a:srgbClr val="{RULE}"/></a:solidFill></a:ln>'))
    cap = doc.add_paragraph(style="Figure Caption")
    if prefix:
        add_run(cap, f"{prefix}:" if rest else prefix, bold=True, italic=False)
        add_run(cap, " ")
    add_inline(cap, rest, code_size=8.5)
    ctx["figure_ids"].append(prefix)


def render_list(doc, blk, ctx, numbered):
    items = [i["text"] if isinstance(i, dict) else str(i) for i in blk.get("items", [])]
    if numbered:
        nid, num = new_number_list(ctx["num"])
        doc.part.numbering_part.element.append(num)
        left, hang = 520, 320
    else:
        nid, left, hang = 900, 520, 260
    for i, text in enumerate(items):
        p = doc.add_paragraph(style="List Number" if numbered else "List Bullet")
        insert_ordered(ppr_of(p), el("numPr", children=[el("ilvl", {"val": 0}), el("numId", {"val": nid})]), PPR_ORDER)
        p.paragraph_format.left_indent = Twips(left)
        p.paragraph_format.first_line_indent = Twips(-hang)
        if i == len(items) - 1:
            p.paragraph_format.space_after = Pt(4)
        add_inline(p, text, code_size=9.5)
        ctx["prose"].append(text)


def render_blocks(doc, blocks, ctx):
    for blk in blocks:
        kind = blk.get("type")
        if kind in ("h2", "h3"):
            text = str(blk.get("text", "")).strip()
            num = str(blk.get("number", "") or "")
            if num and not text.startswith(num):
                text = f"{num} {text}"
            h = doc.add_paragraph(style="Heading 2" if kind == "h2" else "Heading 3")
            add_inline(h, text, code_size=10)
        elif kind == "p":
            p = doc.add_paragraph(style="Normal")
            add_inline(p, blk.get("text", ""), code_size=9.5)
            ctx["prose"].append(blk.get("text", ""))
        elif kind == "bullets":
            render_list(doc, blk, ctx, False)
        elif kind == "numbered":
            render_list(doc, blk, ctx, True)
        elif kind == "callout":
            render_callout(doc, blk, ctx)
        elif kind == "equation":
            render_equation(doc, blk, ctx)
        elif kind == "code":
            render_code(doc, blk, ctx)
        elif kind == "figure":
            render_figure(doc, blk, ctx)
        elif kind == "table":
            render_table(doc, blk, ctx)
        else:
            raise ValueError(f"unknown block type: {kind!r}")


# --------------------------------------------------------------------------- DOCX document parts

def chapter_heading(ch):
    number = str(ch.get("number", "")).strip()
    return f"{number}\u2003{ch['title']}" if number else ch["title"]


def appendix_heading(ap):
    return f"Appendix {ap['letter']}\u2003{ap['title']}"


def parse_team(team):
    out = []
    for t in team or TEAM_DEFAULT:
        if isinstance(t, dict):
            sid, name = t.get("id") or t.get("student_id"), t.get("name_ar") or t.get("name")
        else:
            a, b = t[0], t[1]
            sid, name = (a, b) if str(a).strip().isdigit() else (b, a)
        out.append((str(sid).strip(), str(name).strip()))
    return out


def build_cover(doc, meta, team):
    sec_logo = None
    try:
        sec_logo = resolve_asset(meta.get("logo_file") or "hnu_logo.png")
    except FileNotFoundError:
        fallback = ROOT / "media" / "hnu-logo.png"
        sec_logo = fallback if fallback.is_file() else None
    if sec_logo:
        p = doc.add_paragraph(style="Figure Image")
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.keep_with_next = False
        shape = p.add_run().add_picture(str(sec_logo), width=Inches(1.30))
        shape._inline.docPr.set("descr", "Helwan National University seal")
    doc.add_paragraph(meta.get("university", "Helwan National University"), style="Cover University")
    doc.add_paragraph(meta.get("faculty", "Faculty of Engineering"), style="Cover Line")
    p = doc.add_paragraph(meta.get("department", "Intelligent Systems Engineering"), style="Cover Line")
    for r in p.runs:
        r.font.color.rgb = RGBColor.from_string(SLATE)
        r.font.size = Pt(11.5)
    p.paragraph_format.space_after = Pt(10)
    rule = doc.add_paragraph(style="Spacer")
    pbdr(ppr_of(rule), bottom=(12, NAVY, 1))
    doc.add_paragraph(meta.get("title", "Intelligent Load Balancer with Fault Tolerance in Software-Defined Networks"),
                      style="Cover Title")
    doc.add_paragraph(meta.get("subtitle", "ECE2606 \u2014 Computer Networks Course Project (Track 1)"),
                      style="Cover Subtitle")
    rule = doc.add_paragraph(style="Spacer")
    pbdr(ppr_of(rule), bottom=(4, RULE, 1))
    lab = doc.add_paragraph("Submitted by", style="Cover Label")
    lab.paragraph_format.space_before = Pt(10)
    widths = [4800, 2300]
    tbl = doc.add_table(rows=1 + len(team), cols=2)
    set_table(tbl, widths, bidi_visual=True, jc="center")
    mar = {"top": 70, "bottom": 70, "left": 140, "right": 140}
    rule_b = {"bottom": ("single", 4, RULE), "top": ("nil", 0, "auto"), "left": ("nil", 0, "auto"),
              "right": ("nil", 0, "auto")}
    for ri, row in enumerate(tbl.rows):
        style_row(row, header=ri == 0)
        name_cell, id_cell = row.cells
        head = ri == 0
        fill = NAVY if head else (SOFT if ri % 2 == 0 else None)
        style_cell(name_cell, widths[0], fill=fill, borders=rule_b, margins=mar, valign="center")
        style_cell(id_cell, widths[1], fill=fill, borders=rule_b, margins=mar, valign="center")
        name = "\u0627\u0644\u0627\u0633\u0645" if head else team[ri - 1][1]
        sid = "Student ID" if head else team[ri - 1][0]
        np_ = name_cell.paragraphs[0]
        np_.style = doc.styles["Table Text"]
        insert_ordered(ppr_of(np_), el("bidi"), PPR_ORDER)
        ip = id_cell.paragraphs[0]
        ip.style = doc.styles["Table Text"]
        ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
        color = WHITE if head else INK
        add_run(np_, name, font=AR_FONT, size=11.5 if not head else 10.5, bold=True if head else False, color=color,
                rtl=True, cs_font=AR_FONT)
        add_run(ip, sid, font=HEAD_FONT, size=10.5 if not head else 10, bold=True if head else False, color=color)
    first = True
    for label, key, default in (("Course Coordinator", "supervisor", "Prof. Ahmed M. Abdelhaleem"),
                                ("Semester", "semester", "Fall 2026/2027"),
                                ("Date", "date", "November 2026")):
        p = doc.add_paragraph(style="Cover Meta")
        if first:
            p.paragraph_format.space_before = Pt(20)
            first = False
        add_run(p, f"{label}: ", bold=True, color=SLATE)
        add_run(p, str(meta.get(key, default)))


def collect_toc_entries(chapters, appendices):
    entries = []
    idx = 0
    for ch in chapters:
        idx += 1
        entries.append((1, f"sec-{idx}", chapter_heading(ch)))
        for b in ch["blocks"]:
            if b.get("type") == "h2":
                idx += 1
                num = str(b.get("number", "") or "")
                text = str(b.get("text", "")).strip()
                entries.append((2, f"sec-{idx}", f"{num} {text}" if num and not text.startswith(num) else text))
    idx += 1
    entries.append((1, f"sec-{idx}", "References"))
    for ap in appendices:
        idx += 1
        entries.append((1, f"sec-{idx}", appendix_heading(ap)))
    return entries


def build_front_matter(doc, abstract, keywords, toc_entries):
    h = doc.add_paragraph("Abstract", style="Front Heading")
    h.paragraph_format.page_break_before = True
    _, cell = box_table(doc, accent=NAVY, fill=SOFT, accent_sz=24,
                        margins={"top": 130, "bottom": 100, "left": 220, "right": 200})
    paras = abstract if isinstance(abstract, list) else [abstract]
    for i, text in enumerate(paras):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.style = doc.styles["Normal"]
        add_inline(p, text, code_size=9.5)
    kw = keywords if isinstance(keywords, str) else ", ".join(keywords or [])
    kp = doc.add_paragraph(style="Normal")
    kp.paragraph_format.space_before = Pt(8)
    kp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_run(kp, "Keywords: ", bold=True, color=NAVY, font=HEAD_FONT, size=10)
    add_run(kp, kw, italic=True, size=11)

    th = doc.add_paragraph("Table of Contents", style="Front Heading")
    th.paragraph_format.page_break_before = True
    entries = [(lvl, txt) for lvl, _, txt in toc_entries] or [(1, "Update field to populate Table of Contents.")]
    for i, (level, text) in enumerate(entries):
        p = doc.add_paragraph(style="toc 1" if level == 1 else "toc 2")
        if i == 0:
            for kind in ("begin", "instr", "separate"):
                if kind == "instr":
                    r = _run()
                    it = el("instrText")
                    it.text = ' TOC \\o "1-2" \\h \\z \\u '
                    it.set(qn("xml:space"), "preserve")
                    r.append(it)
                else:
                    r = _run()
                    r.append(el("fldChar", {"fldCharType": kind}))
                p._p.append(r)
        add_run(p, text)
        if i == len(entries) - 1:
            r = _run()
            r.append(el("fldChar", {"fldCharType": "end"}))
            p._p.append(r)


def render_references(doc, refs):
    doc.add_paragraph("References", style="Heading 1")
    for i, ref in enumerate(refs, 1):
        text = re.sub(r"^\[\d+\]\s*", "", str(ref).strip())
        p = doc.add_paragraph(style="Reference")
        add_run(p, f"[{i}]\t", font=BODY_FONT)
        add_inline(p, text, code_size=8.5)


# --------------------------------------------------------------------------- Print HTML -> Chrome PDF mirror

def html_inline(text: str, parse_math: bool = False) -> str:
    text = (text or "").replace("\r", "").replace("\n", " ")
    emit = html_math if parse_math else html_mod.escape
    out, pos = [], 0
    for m in INLINE_RE.finditer(text):
        out.append(emit(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(f"<strong>{emit(m.group(1))}</strong>")
        elif m.group(2) is not None:
            out.append(f"<code>{html_mod.escape(m.group(2).strip())}</code>")
        else:
            out.append(f"<em>{emit(m.group(3))}</em>")
        pos = m.end()
    out.append(emit(text[pos:]))
    return "".join(out)


def html_math(text: str) -> str:
    out, pos = [], 0
    for m in SCRIPT_RE.finditer(text):
        out.append(html_mod.escape(text[pos:m.start()]))
        body = m.group(2)
        body = body[1:-1] if body.startswith("{") else body
        tag = "sub" if m.group(1) == "_" else "sup"
        out.append(f"<{tag}>{html_mod.escape(body)}</{tag}>")
        pos = m.end()
    out.append(html_mod.escape(text[pos:]))
    return "".join(out)


def render_html_doc(content: dict, toc_pages: dict[str, int] | None = None) -> tuple[str, list[tuple[int, str, str]]]:
    meta = content["meta"]
    team = parse_team(meta.get("team"))
    chapters, appendices, refs = content["chapters"], content["appendices"], content["references"]
    toc_entries = collect_toc_entries(chapters, appendices)
    toc_pages = toc_pages or {}

    logo_uri = ""
    try:
        logo_uri = resolve_asset(meta.get("logo_file") or "hnu_logo.png").resolve().as_uri()
    except FileNotFoundError:
        fb = ROOT / "media" / "hnu-logo.png"
        if fb.is_file():
            logo_uri = fb.resolve().as_uri()

    parts = [f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html_mod.escape(meta.get("title", "SDN Track 1 Report"))}</title>
<style>
@page {{
  size: A4;
  margin: 17mm 18.5mm 17mm 18.5mm;
  @top-center {{
    content: "{HEADER_TEXT}";
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 8.5pt;
    color: #{SLATE};
    border-bottom: 0.6pt solid #{RULE};
    width: 100%;
    padding-bottom: 2.5pt;
    margin-bottom: 5pt;
    vertical-align: bottom;
  }}
  @bottom-left {{
    content: "{FOOTER_LEFT}";
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 8.5pt;
    color: #{SLATE};
    border-top: 0.6pt solid #{RULE};
    padding-top: 2.5pt;
    margin-top: 4pt;
    vertical-align: top;
  }}
  @bottom-right {{
    content: "Page " counter(page) " of " counter(pages);
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 8.5pt;
    color: #{SLATE};
    border-top: 0.6pt solid #{RULE};
    padding-top: 2.5pt;
    margin-top: 4pt;
    vertical-align: top;
  }}
}}
@page :first {{
  @top-center {{ content: none; border: none; }}
  @bottom-left {{ content: none; border: none; }}
  @bottom-right {{ content: none; border: none; }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Times New Roman", Georgia, serif;
  font-size: 12pt;
  line-height: 1.09;
  color: #{INK};
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}
p {{
  margin: 0 0 3.5pt 0;
  text-align: justify;
  orphans: 2;
  widows: 2;
}}
code {{
  font-family: "Consolas", "Courier New", monospace;
  font-size: 9.5pt;
  color: #{CODE_INK};
  background: #{INLINE_BG};
  padding: 0 1pt;
  border-radius: 1.5pt;
}}
.cover {{
  text-align: center;
  padding-top: 6mm;
}}
.cover-logo {{ width: 1.30in; height: auto; margin-bottom: 5pt; }}
.cover-uni {{ font-family: "Segoe UI", sans-serif; font-size: 21pt; font-weight: 700; color: #{NAVY}; margin: 4pt 0 2pt; text-align: center; }}
.cover-fac {{ font-family: "Segoe UI", sans-serif; font-size: 12.5pt; color: #{INK}; margin: 0 0 1pt; text-align: center; }}
.cover-dep {{ font-family: "Segoe UI", sans-serif; font-size: 11.5pt; color: #{SLATE}; margin: 0 0 10pt; text-align: center; }}
.rule-navy {{ border: 0; border-bottom: 1.5pt solid #{NAVY}; margin: 6pt 0 14pt; }}
.rule-light {{ border: 0; border-bottom: 0.75pt solid #{RULE}; margin: 10pt 0 10pt; }}
.cover-title {{ font-family: "Segoe UI", sans-serif; font-size: 22pt; font-weight: 700; color: #{NAVY}; line-height: 1.12; margin: 10pt 0 6pt; text-align: center; }}
.cover-sub {{ font-family: "Segoe UI", sans-serif; font-size: 12.5pt; color: #{SLATE}; margin: 0 0 10pt; text-align: center; }}
.cover-label {{ font-family: "Segoe UI", sans-serif; font-size: 10pt; font-weight: 700; color: #{TEAL}; margin: 10pt 0 6pt; text-align: center; letter-spacing: 0.4pt; text-transform: uppercase; }}
.roster {{
  width: 126mm;
  margin: 0 auto 16pt auto;
  border-collapse: collapse;
  direction: rtl;
}}
.roster th {{
  background: #{NAVY};
  color: #FFFFFF;
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 10.5pt;
  font-weight: 700;
  padding: 5.5pt 10pt;
  border-bottom: 1pt solid #{NAVY};
}}
.roster td {{
  padding: 5pt 10pt;
  border-bottom: 0.6pt solid #{RULE};
  font-size: 11.5pt;
  vertical-align: middle;
}}
.roster tr:nth-child(even) td {{ background: #{SOFT}; }}
.roster .ar {{ font-family: Arial, Tahoma, sans-serif; text-align: right; direction: rtl; }}
.roster .sid {{ font-family: "Segoe UI", sans-serif; font-size: 10.5pt; text-align: center; direction: ltr; width: 38mm; }}
.cover-meta {{ font-family: "Segoe UI", sans-serif; font-size: 10.5pt; color: #{INK}; margin: 2.5pt 0; text-align: center; }}
.cover-meta strong {{ color: #{SLATE}; }}

h1, .front-h1 {{
  font-family: "Segoe UI", sans-serif;
  font-size: 16.5pt;
  font-weight: 700;
  color: #{NAVY};
  border-bottom: 1.5pt solid #{NAVY};
  padding-bottom: 3pt;
  margin: 0 0 8pt 0;
  break-before: page;
  break-after: avoid;
  page-break-before: always;
  page-break-after: avoid;
}}
h2 {{
  font-family: "Segoe UI", sans-serif;
  font-size: 12.5pt;
  font-weight: 700;
  color: #{TEAL};
  margin: 8pt 0 3pt 0;
  break-after: avoid;
  page-break-after: avoid;
}}
h3 {{
  font-family: "Segoe UI", sans-serif;
  font-size: 11pt;
  font-weight: 700;
  color: #{NAVY};
  margin: 6pt 0 2.5pt 0;
  break-after: avoid;
  page-break-after: avoid;
}}
.abstract-box {{
  background: #{SOFT};
  border-left: 3pt solid #{NAVY};
  padding: 10pt 14pt;
  margin-bottom: 8pt;
}}
.keywords {{
  font-size: 11pt;
  text-align: left;
  margin-top: 6pt;
}}
.keywords strong {{ font-family: "Segoe UI", sans-serif; font-size: 10pt; color: #{NAVY}; }}
.toc-list {{ margin: 4pt 0 0 0; padding: 0; list-style: none; }}
.toc-item {{
  display: flex;
  align-items: baseline;
  font-family: "Segoe UI", sans-serif;
  text-decoration: none;
  color: inherit;
}}
.toc-l1 {{ font-size: 9pt; font-weight: 700; color: #{NAVY}; margin-top: 2pt; }}
.toc-l2 {{ font-size: 8.2pt; font-weight: 400; color: #{INK}; padding-left: 14pt; line-height: 1.2; }}
.toc-dots {{ flex: 1; border-bottom: 0.7pt dotted #94A3B8; margin: 0 5pt; position: relative; top: -2pt; }}
.toc-pg {{ font-variant-numeric: tabular-nums; min-width: 14pt; text-align: right; }}

ul, ol {{ margin: 2pt 0 5pt 0; padding-left: 18pt; }}
li {{ margin: 0 0 2pt 0; text-align: justify; }}
ul li::marker {{ color: #{TEAL}; }}
ol li::marker {{ color: #{NAVY}; font-family: "Segoe UI", sans-serif; font-weight: 700; font-size: 10.5pt; }}

.callout {{
  background: #{CALLOUT_BG};
  border-left: 3.5pt solid #{TEAL};
  padding: 7pt 11pt;
  margin: 5pt 0 6pt 0;
  break-inside: avoid;
}}
.callout-title {{ font-family: "Segoe UI", sans-serif; font-size: 10pt; font-weight: 700; color: #{TEAL}; margin: 0 0 2pt 0; text-align: left; }}
.callout p {{ font-size: 10.5pt; line-height: 1.1; margin: 0 0 2pt 0; }}
.callout p:last-child {{ margin-bottom: 0; }}

.eq-wrap {{ margin: 5pt 0 6pt 0; break-inside: avoid; }}
.eq-row {{ display: flex; align-items: center; }}
.eq-box {{
  flex: 1;
  background: #{SOFT};
  padding: 6pt 10pt;
  text-align: center;
  font-family: "Cambria", "Times New Roman", serif;
  font-size: 11.5pt;
  font-style: italic;
  color: #{INK};
}}
.eq-num {{
  width: 18mm;
  text-align: right;
  font-family: "Segoe UI", sans-serif;
  font-size: 9.5pt;
  font-weight: 700;
  color: #{NAVY};
}}
.eq-note {{ font-size: 9.5pt; color: #{SLATE}; margin: 2.5pt 0 0 0; text-align: left; line-height: 1.08; }}

.code-block {{
  border-left: 3pt solid #{NAVY};
  border-bottom: 0.6pt solid #{RULE};
  margin: 3.5pt 0 4.5pt 0;
  break-inside: avoid;
}}
.code-hdr {{
  background: #E8EEF5;
  padding: 2.5pt 8pt;
  font-family: "Segoe UI", sans-serif;
  font-size: 8.3pt;
  font-weight: 700;
  color: #{NAVY};
  display: flex;
  justify-content: space-between;
}}
.code-lang {{ font-weight: 400; color: #{SLATE}; font-size: 7.3pt; }}
.code-body {{
  background: #{CODE_BG};
  padding: 3.2pt 8pt;
  margin: 0;
  font-family: "Consolas", "Courier New", monospace;
  font-size: 7.4pt;
  line-height: 1.09;
  color: #{CODE_INK};
  white-space: pre-wrap;
  word-break: break-word;
}}

.fig-wrap {{
  margin: 3.5pt 0 5pt 0;
  text-align: center;
  break-inside: avoid;
  page-break-inside: avoid;
}}
.fig-wrap img {{
  display: block;
  margin: 0 auto 3pt auto;
  height: auto;
}}
.fig-wrap img.bordered {{
  border: 0.75pt solid #{RULE};
}}
.fig-cap {{
  font-family: "Segoe UI", sans-serif;
  font-size: 9pt;
  color: #{SLATE};
  text-align: center;
  margin: 0;
  line-height: 1.12;
}}
.fig-cap strong {{ color: #{NAVY}; font-style: normal; }}

.tbl-wrap {{ margin: 5pt 0 6pt 0; }}
.tbl-cap {{
  font-family: "Segoe UI", sans-serif;
  font-size: 9.5pt;
  font-weight: 700;
  color: #{NAVY};
  margin: 0 0 3pt 0;
  text-align: left;
  break-inside: avoid;
  page-break-inside: avoid;
  break-after: avoid;
  page-break-after: avoid;
  orphans: 3;
  widows: 3;
}}
table.data-tbl {{
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 8.3pt;
  line-height: 1.14;
}}
table.data-tbl thead {{ display: table-header-group; }}
table.data-tbl tr {{ break-inside: avoid; page-break-inside: avoid; }}
table.data-tbl th {{
  background: #{NAVY};
  color: #FFFFFF;
  font-size: 8.5pt;
  font-weight: 700;
  padding: 3.5pt 5pt;
  text-align: left;
  border-bottom: 1pt solid #{NAVY};
  vertical-align: middle;
}}
table.data-tbl td {{
  padding: 3pt 5pt;
  border-bottom: 0.5pt solid #{RULE};
  vertical-align: top;
  word-wrap: break-word;
}}
table.data-tbl tbody tr:nth-child(even) td {{ background: #{SOFT}; }}
table.data-tbl th.num, table.data-tbl td.num {{ text-align: center; vertical-align: middle; }}
table.data-tbl th.ar-hdr {{ text-align: right; }}
table.data-tbl td.ar {{ direction: rtl; text-align: right; font-family: Arial, Tahoma, sans-serif; }}
table.data-tbl code {{ font-size: 7.7pt; }}

.ref-item {{
  font-size: 9.5pt;
  line-height: 1.12;
  padding-left: 24pt;
  text-indent: -24pt;
  margin: 0 0 2.5pt 0;
  text-align: left;
}}
</style>
</head>
<body>
"""]

    # Cover
    parts.append('<section class="cover">')
    if logo_uri:
        parts.append(f'<img class="cover-logo" src="{logo_uri}" alt="Helwan National University seal">')
    parts.append(f'<div class="cover-uni">{html_mod.escape(meta.get("university", "Helwan National University"))}</div>')
    parts.append(f'<div class="cover-fac">{html_mod.escape(meta.get("faculty", "Faculty of Engineering"))}</div>')
    parts.append(f'<div class="cover-dep">{html_mod.escape(meta.get("department", "Intelligent Systems Engineering"))}</div>')
    parts.append('<hr class="rule-navy">')
    parts.append(f'<div class="cover-title">{html_mod.escape(meta.get("title", "Intelligent Load Balancer with Fault Tolerance in Software-Defined Networks"))}</div>')
    parts.append(f'<div class="cover-sub">{html_mod.escape(meta.get("subtitle", "ECE2606 \u2014 Computer Networks Course Project (Track 1)"))}</div>')
    parts.append('<hr class="rule-light">')
    parts.append('<div class="cover-label">Submitted by</div>')
    parts.append('<table class="roster"><thead><tr><th class="ar" lang="ar-EG">الاسم</th><th class="sid">Student ID</th></tr></thead><tbody>')
    for sid, name in team:
        parts.append(f'<tr><td class="ar" lang="ar-EG">{html_mod.escape(name)}</td><td class="sid">{html_mod.escape(sid)}</td></tr>')
    parts.append('</tbody></table>')
    for label, key, default in (("Course Coordinator", "supervisor", "Prof. Ahmed M. Abdelhaleem"),
                                ("Semester", "semester", "Fall 2026/2027"),
                                ("Date", "date", "November 2026")):
        parts.append(f'<div class="cover-meta"><strong>{label}:</strong> {html_mod.escape(str(meta.get(key, default)))}</div>')
    parts.append('</section>')

    # Abstract
    parts.append('<div class="front-h1">Abstract</div><div class="abstract-box">')
    for text in (content["abstract"] if isinstance(content["abstract"], list) else [content["abstract"]]):
        parts.append(f"<p>{html_inline(text)}</p>")
    parts.append('</div>')
    kw = content["keywords"] if isinstance(content["keywords"], str) else ", ".join(content["keywords"] or [])
    parts.append(f'<p class="keywords"><strong>Keywords:</strong> <em>{html_mod.escape(kw)}</em></p>')

    # TOC
    parts.append('<div class="front-h1">Table of Contents</div><div class="toc-list">')
    for lvl, sid, title in toc_entries:
        pg = str(toc_pages.get(sid, ""))
        cls = "toc-l1" if lvl == 1 else "toc-l2"
        parts.append(f'<a class="toc-item {cls}" href="#{sid}"><span>{html_mod.escape(title)}</span>'
                     f'<span class="toc-dots"></span><span class="toc-pg">{pg}</span></a>')
    parts.append('</div>')

    # Chapters + References + Appendices
    sec_idx = 0

    def emit_blocks(blocks):
        nonlocal sec_idx
        for blk in blocks:
            kind = blk.get("type")
            if kind == "h2":
                sec_idx += 1
                num = str(blk.get("number", "") or "")
                text = str(blk.get("text", "")).strip()
                full = f"{num} {text}" if num and not text.startswith(num) else text
                parts.append(f'<h2 id="sec-{sec_idx}">{html_inline(full)}</h2>')
            elif kind == "h3":
                num = str(blk.get("number", "") or "")
                text = str(blk.get("text", "")).strip()
                full = f"{num} {text}" if num and not text.startswith(num) else text
                parts.append(f'<h3>{html_inline(full)}</h3>')
            elif kind == "p":
                parts.append(f'<p>{html_inline(blk.get("text", ""))}</p>')
            elif kind in ("bullets", "numbered"):
                tag = "ol" if kind == "numbered" else "ul"
                parts.append(f"<{tag}>")
                for item in blk.get("items", []):
                    t = item["text"] if isinstance(item, dict) else str(item)
                    parts.append(f"<li>{html_inline(t)}</li>")
                parts.append(f"</{tag}>")
            elif kind == "callout":
                parts.append('<div class="callout">')
                if blk.get("title"):
                    parts.append(f'<div class="callout-title">{html_inline(blk["title"])}</div>')
                txt = blk.get("text", "")
                for t in (txt if isinstance(txt, list) else str(txt).split("\n")):
                    if t.strip():
                        parts.append(f"<p>{html_inline(t)}</p>")
                parts.append('</div>')
            elif kind == "equation":
                formula = blk.get("formula") or blk.get("text", "")
                num = blk.get("number", "")
                lines = [l for l in str(formula).split("\n") if l.strip()] or [""]
                body = "<br>".join(html_math(l) for l in lines)
                parts.append(f'<div class="eq-wrap"><div class="eq-row"><div class="eq-box">{body}</div>'
                             f'<div class="eq-num">{html_mod.escape(num)}</div></div>')
                if blk.get("note"):
                    parts.append(f'<div class="eq-note">{html_inline(blk["note"], parse_math=True)}</div>')
                parts.append('</div>')
            elif kind == "code":
                lines = [str(l).replace("\r", "").replace("\t", "    ") for l in blk.get("lines", [])]
                lang = str(blk.get("language") or "").upper()
                parts.append(f'<div class="code-block"><div class="code-hdr"><span>{html_mod.escape(blk.get("title", "Listing"))}</span>'
                             f'<span class="code-lang">{html_mod.escape(lang)}</span></div>'
                             f'<pre class="code-body">{html_mod.escape(chr(10).join(lines))}</pre></div>')
            elif kind == "figure":
                path = resolve_asset(blk.get("file") or blk.get("path"))
                bordered = bool(blk.get("border"))
                w, _ = figure_dimensions(path, blk.get("width_in", 5.6), bordered)
                prefix, rest = split_caption(blk.get("caption"), blk.get("id") or blk.get("number"), "Figure")
                cls = ' class="bordered"' if bordered else ""
                cap_html = (f'<strong>{html_mod.escape(prefix)}:</strong> <em>{html_inline(rest)}</em>'
                            if prefix and rest else f'<strong>{html_mod.escape(prefix)}</strong>')
                parts.append(f'<div class="fig-wrap"><img{cls} src="{path.resolve().as_uri()}" style="width:{w:.2f}in;">'
                             f'<div class="fig-cap">{cap_html}</div></div>')
            elif kind == "table":
                headers = [str(h) for h in blk.get("headers", [])]
                rows = [[str(c) for c in r] for r in blk.get("rows", [])]
                n = len(headers) or (len(rows[0]) if rows else 1)
                rows = [(r + [""] * n)[:n] for r in rows]
                weights = blk.get("col_widths_mm") or blk.get("col_weights") or [1] * n
                tot = float(sum(weights))
                pcts = [100.0 * w / tot for w in weights]
                prefix, rest = split_caption(blk.get("caption"), blk.get("id") or blk.get("number"), "Table")
                numeric = [all(NUM_RE.match(r[j].strip()) and len(r[j].strip()) <= 22 for r in rows if r[j].strip())
                           and any(r[j].strip() for r in rows) for j in range(n)]
                arabic_col = [any(bool(re.fullmatch(f"{ARABIC}(?:[ \\t]+{ARABIC})*", r[j].strip() or "x")) for r in rows)
                              for j in range(n)]
                cap_txt = f"{prefix}: {rest}" if prefix and rest else prefix
                parts.append(f'<div class="tbl-wrap"><div class="tbl-cap">{html_inline(cap_txt)}</div>')
                parts.append('<table class="data-tbl"><colgroup>')
                for pct in pcts:
                    parts.append(f'<col style="width:{pct:.2f}%">')
                parts.append('</colgroup>')
                if headers:
                    parts.append('<thead><tr>')
                    for ci, h in enumerate(headers):
                        cls = ' class="num"' if numeric[ci] else (' class="ar-hdr"' if arabic_col[ci] else "")
                        parts.append(f'<th{cls}>{html_inline(h)}</th>')
                    parts.append('</tr></thead>')
                parts.append('<tbody>')
                for r in rows:
                    parts.append('<tr>')
                    for ci, val in enumerate(r):
                        is_ar = bool(re.fullmatch(f"{ARABIC}(?:[ \\t]+{ARABIC})*", val.strip() or "x"))
                        cls = ' class="ar" lang="ar-EG"' if is_ar else (' class="num"' if numeric[ci] else "")
                        cell_html = "<br>".join(html_inline(ln) for ln in val.split("\n"))
                        parts.append(f'<td{cls}>{cell_html}</td>')
                    parts.append('</tr>')
                parts.append('</tbody></table></div>')

    for ch in chapters:
        sec_idx += 1
        parts.append(f'<h1 id="sec-{sec_idx}">{html_mod.escape(chapter_heading(ch))}</h1>')
        emit_blocks(ch["blocks"])

    sec_idx += 1
    parts.append(f'<h1 id="sec-{sec_idx}">References</h1>')
    for i, ref in enumerate(refs, 1):
        text = re.sub(r"^\[\d+\]\s*", "", str(ref).strip())
        parts.append(f'<div class="ref-item">[{i}] {html_inline(text)}</div>')

    for ap in appendices:
        sec_idx += 1
        parts.append(f'<h1 id="sec-{sec_idx}">{html_mod.escape(appendix_heading(ap))}</h1>')
        emit_blocks(ap["blocks"])

    parts.append("</body></html>")
    return "\n".join(parts), toc_entries


def find_chrome() -> Path:
    for cand in CHROME_CANDIDATES:
        if cand.is_file():
            return cand
    raise FileNotFoundError("Chrome/Edge executable not found for offline PDF rendering.")


def run_chrome_pdf(chrome: Path, html_path: Path, pdf_path: Path, profile_dir: Path):
    args = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-extensions",
        "--disable-sync",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        f"--user-data-dir={profile_dir}",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(f"Chrome PDF export failed (rc={res.returncode}): {res.stderr}")


def locate_heading_pages(pdf_path: Path, toc_entries: list[tuple[int, str, str]]) -> dict[str, int]:
    """Locate the exact 1-based PDF page number of every TOC heading sequentially (skipping TOC page)."""
    reader = PdfReader(str(pdf_path))
    pages_norm = []
    for p in reader.pages:
        t = re.sub(r"\s+", " ", (p.extract_text() or "")).strip().lower()
        pages_norm.append(t)

    found: dict[str, int] = {}
    cur_page = 3  # 0-based index 3 = Page 4 (skip Cover=0, Abstract=1, TOC=2)
    for _, sid, title in toc_entries:
        needle = re.sub(r"\s+", " ", title).strip().lower()
        short = needle[:42]
        hit = None
        for pi in range(cur_page, len(pages_norm)):
            if needle in pages_norm[pi] or short in pages_norm[pi]:
                hit = pi
                break
        if hit is None:
            for pi in range(3, len(pages_norm)):
                if short in pages_norm[pi]:
                    hit = pi
                    break
        if hit is not None:
            found[sid] = hit + 1
            cur_page = hit
        else:
            found[sid] = cur_page + 1
    return found


def attach_pdf_bookmarks(pdf_path: Path, toc_entries: list[tuple[int, str, str]], toc_pages: dict[str, int], meta: dict):
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    writer.add_metadata({
        "/Title": meta.get("title", "Intelligent Load Balancer with Fault Tolerance in Software-Defined Networks"),
        "/Author": "Helwan National University — Intelligent Systems Engineering (Track 1)",
        "/Subject": "ECE2606 Computer Networks Course Project (Track 1)",
    })
    parent_item = None
    for lvl, sid, title in toc_entries:
        pg_idx = max(0, min(toc_pages.get(sid, 1) - 1, len(reader.pages) - 1))
        if lvl == 1:
            parent_item = writer.add_outline_item(title, pg_idx)
        else:
            writer.add_outline_item(title, pg_idx, parent=parent_item)
    tmp = pdf_path.with_suffix(".bm.pdf")
    with open(tmp, "wb") as fh:
        writer.write(fh)
    tmp.replace(pdf_path)
    return len(reader.pages)


def build_pdf(content: dict, pdf_out: Path) -> int:
    chrome = find_chrome()
    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="sdn-pdf-build-"))
    try:
        profile = scratch / "chrome-profile"
        html1 = scratch / "pass1.html"
        pdf1 = scratch / "pass1.pdf"
        html_src, toc_entries = render_html_doc(content, {})
        html1.write_text(html_src, encoding="utf-8")
        run_chrome_pdf(chrome, html1, pdf1, profile)
        toc_pages = locate_heading_pages(pdf1, toc_entries)

        html2 = scratch / "pass2.html"
        html_src2, _ = render_html_doc(content, toc_pages)
        html2.write_text(html_src2, encoding="utf-8")
        run_chrome_pdf(chrome, html2, pdf_out, profile)
        # Re-verify page numbers in case TOC digits shifted anything (rare)
        toc_pages2 = locate_heading_pages(pdf_out, toc_entries)
        if toc_pages2 != toc_pages:
            html_src3, _ = render_html_doc(content, toc_pages2)
            html2.write_text(html_src3, encoding="utf-8")
            run_chrome_pdf(chrome, html2, pdf_out, profile)
            toc_pages = toc_pages2
        n_pages = attach_pdf_bookmarks(pdf_out, toc_entries, toc_pages, content["meta"])
        print(f"Exported PDF: {pdf_out} ({pdf_out.stat().st_size / 1024:.0f} KiB) | Exact PDF Pages: {n_pages} | Bookmarks: {len(toc_entries)}")
        return n_pages
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --------------------------------------------------------------------------- lint + packaging

def lint(ctx, refs):
    notes = []
    prose = "\n".join(ctx["prose"])
    for ids in (ctx["figure_ids"], ctx["table_ids"]):
        for ident in ids:
            if ident and not re.search(re.escape(ident) + r"(?![\d.]*\d)", prose):
                notes.append(f"{ident} is never cited in prose")
    cited = set()
    for m in re.finditer(r"\[(\d+)\]\s*[\u2013\-]\s*\[(\d+)\]", prose):
        cited.update(range(int(m.group(1)), int(m.group(2)) + 1))
    for m in re.finditer(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]", prose):
        cited.update(int(x) for x in re.findall(r"\d+", m.group(1)))
    missing = [i for i in range(1, len(refs) + 1) if i not in cited]
    if missing:
        notes.append("references never cited in prose: " + ", ".join(f"[{i}]" for i in missing))
    bad = sorted(i for i in cited if i > len(refs))
    if bad:
        notes.append("citations beyond the reference list: " + ", ".join(f"[{i}]" for i in bad))
    dashes = prose.count("\u2014") + prose.count("\u2013")
    if dashes:
        notes.append(f"{dashes} em/en-dashes found in prose")
    return notes


def strip_dir_entries(path: Path):
    with zipfile.ZipFile(path) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    if not any(i.filename.endswith("/") for i, _ in items):
        return
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for i, data in items:
            if not i.filename.endswith("/"):
                zout.writestr(i.filename, data)
    tmp.replace(path)


def load_content(content_dir: Path):
    sys.path.insert(0, str(content_dir))
    p1 = importlib.import_module("content_part1")
    p2 = importlib.import_module("content_part2")
    return {
        "meta": getattr(p1, "META", {}),
        "abstract": getattr(p1, "ABSTRACT_PARAGRAPHS", []),
        "keywords": getattr(p1, "KEYWORDS", []),
        "chapters": list(getattr(p1, "CHAPTERS_PART1", [])) + list(getattr(p2, "CHAPTERS_PART2", [])),
        "references": list(getattr(p2, "REFERENCES", [])),
        "appendices": list(getattr(p2, "APPENDICES", [])),
    }


def build(content: dict, out: Path) -> Path:
    meta = content["meta"]
    chapters, appendices = content["chapters"], content["appendices"]
    doc = Document()
    setup_styles(doc)
    num_state = setup_numbering(doc)
    setup_page(doc)
    ctx = {"prose": [], "figure_ids": [], "table_ids": [], "num": num_state}
    build_cover(doc, meta, parse_team(meta.get("team")))
    build_front_matter(doc, content["abstract"], content["keywords"], collect_toc_entries(chapters, appendices))
    ctx["prose"].extend(content["abstract"] if isinstance(content["abstract"], list) else [content["abstract"]])
    for ch in chapters:
        doc.add_paragraph(chapter_heading(ch), style="Heading 1")
        render_blocks(doc, ch["blocks"], ctx)
    render_references(doc, content["references"])
    for ap in appendices:
        doc.add_paragraph(appendix_heading(ap), style="Heading 1")
        render_blocks(doc, ap["blocks"], ctx)
    cp = doc.core_properties
    cp.title = meta.get("title", "Intelligent Load Balancer with Fault Tolerance in Software-Defined Networks")
    cp.subject = "ECE2606 Computer Networks, Course Project, Track 1"
    cp.author = "Helwan National University, Intelligent Systems Engineering, Track 1 team"
    cp.last_modified_by = cp.author
    cp.keywords = ", ".join(content["keywords"]) if isinstance(content["keywords"], list) else str(content["keywords"])
    cp.comments = ""
    cp.language = "en-US"
    cp.created = cp.modified = datetime.datetime.now()
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    strip_dir_entries(out)
    for note in lint(ctx, content["references"]):
        print("LINT:", note)
    print(f"Saved {out} ({out.stat().st_size / 1024:.0f} KiB): {len(doc.paragraphs)} body paragraphs, "
          f"{len(doc.tables)} tables, {len(ctx['figure_ids'])} figures, {len(ctx['table_ids'])} numbered tables")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ap.add_argument("--content-dir", type=Path, default=HERE)
    ap.add_argument("--pdf-only", action="store_true", help="export matching print PDF via headless Chrome")
    ap.add_argument("--validate", action="store_true", help="run the docx skill's XSD validator afterwards")
    args = ap.parse_args()
    content = load_content(args.content_dir)
    if args.pdf_only:
        build_pdf(content, args.pdf)
        return
    out = build(content, args.out)
    if args.validate and VALIDATOR.is_file():
        sys.exit(subprocess.call([sys.executable, str(VALIDATOR), str(out)]))


if __name__ == "__main__":
    main()
