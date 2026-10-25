#!/usr/bin/env python3
"""Fill the interim-report template with the approved interim sections.

Generated, not hand-maintained, like the final report's build: the template's front matter is
kept and its placeholders filled; its sample sections are replaced by the interim's own, in the
template's typography (Times New Roman; sections 14 pt, subsections 13 then 12 pt; body 12 pt).
Tables and figures are numbered in one sequence through the report, and every in-text
reference is renumbered to match.

    python3 interim/build_interim.py [-o OUT.docx]

Then render through Word (`submission/render_word.ps1`) to fill the contents and the lists.
"""

from __future__ import annotations

import argparse
import copy
import pathlib
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
TEMPLATE = ROOT / "Capstone_Interimreport_RESEARCH-1.docx"

TITLE = "Confining Unmodified Community Integrations in Home Assistant"
STUDENT = "Younes Rahati"
SUPERVISOR = "Dr. Fiaz Ahmad"
# Owed by the author; marked so that none can be missed (highlighted in the document).
TODO_STATEMENT = "[Student statement: wording to be provided]"
TODO_ACK = "[Acknowledgements: to be written by the author]"
TODO_REPO = "[Repository URL: to be provided]"

SECTIONS = ["01_introduction.md", "02_problem_statement.md", "03_objectives.md",
            "04_literature_review.md", "05_methodology.md", "06_ai_use.md", "07_results.md",
            "08_discussion.md", "09_conclusion.md", "10_future_work.md"]

BODY = "Times New Roman"
MONO = "Courier New"
SIZES = {1: 14, 2: 13, 3: 12}

#: The document body, the parent every inserted paragraph needs (pictures reach the package
#: through it). Set by build().
PARENT = None

INLINE = re.compile(r"(\*\*.+?\*\*|(?<!\*)\*[^*\n]+?\*(?!\*)|`[^`\n]+?`)")


# ---------------------------------------------------------------- numbering of tables and figures

def numbering(texts: list[str]) -> dict[str, str]:
    """Old label ("Table 5.1") → new label ("Table 1"), in order of the captions."""
    out: dict[str, str] = {}
    count = {"Table": 0, "Figure": 0}
    for text in texts:
        for kind, num in re.findall(r"^\*\*(Table|Figure) (\d+\.\d+)\*\*\s*$", text, re.M):
            count[kind] += 1
            out[f"{kind} {num}"] = f"{kind} {count[kind]}"
    return out


def renumber(text: str, mapping: dict[str, str]) -> str:
    # Longest labels first is unnecessary (X.Y never prefixes X.YZ here, but guard anyway).
    def new(m):
        label = mapping.get(f"{m.group(1)} {m.group(3)}")
        return f"{m.group(1)}{m.group(2)} {label.split()[1]}" if label else m.group(0)
    return re.sub(r"\b(Table|Figure)(s?) (\d+\.\d+)\b(?!\.\d)", new, text)


# ---------------------------------------------------------------- low-level helpers

def font(run, name: str = BODY, size: float | None = 12) -> None:
    run.font.name = name
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for slot in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(slot), name)
    if size:
        run.font.size = Pt(size)


def add_runs(par, text: str, size: float = 12, bold: bool = False, italic: bool = False) -> None:
    text = text.replace("n.d.-", "n.d.\u2011")  # a non-breaking hyphen keeps n.d.-c whole
    for piece in INLINE.split(text):
        if not piece:
            continue
        b, i, mono = bold, italic, False
        if piece.startswith("**") and piece.endswith("**"):
            piece, b = piece[2:-2], True
        elif piece.startswith("`") and piece.endswith("`"):
            piece, mono = piece[1:-1], True
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 1:
            piece, i = piece[1:-1], True
        run = par.add_run(piece)
        run.bold, run.italic = b or None, i or None
        font(run, MONO if mono else BODY, size - 1 if mono else size)


def body_par(anchor, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=6, line=1.5,
             left=None, hanging=None, keep_next=False):
    """A new paragraph inserted before `anchor` (the final sectPr), formatted directly."""
    p = OxmlElement("w:p")
    anchor.addprevious(p)
    par = Paragraph(p, PARENT)
    pf = par.paragraph_format
    pf.alignment = align
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = line
    pf.keep_with_next = keep_next or None
    if left is not None:
        pf.left_indent = Cm(left)
    if hanging is not None:
        pf.first_line_indent = Cm(-hanging)
    return par


def outline(par, level: int) -> None:
    ppr = par._p.get_or_add_pPr()
    lvl = OxmlElement("w:outlineLvl")
    lvl.set(qn("w:val"), str(level))
    ppr.append(lvl)


def page_break_before(par) -> None:
    par.paragraph_format.page_break_before = True


def field(par, instruction: str, placeholder: str, size: float = 12, bold=False, italic=False):
    def r(kind=None, text=None, instr=None):
        run = par.add_run()
        font(run, BODY, size)
        run.bold, run.italic = bold or None, italic or None
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            run._r.append(fc)
        if instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = instr
            run._r.append(it)
        if text is not None:
            run.text = text
    r("begin"); r(instr=f" {instruction} "); r("separate"); r(text=placeholder); r("end")


def set_text(par, text: str, *, highlight: bool = False) -> None:
    """Replace a template paragraph's text, keeping its first run's formatting."""
    runs = par.runs
    if not runs:
        run = par.add_run(text)
        font(run)
    else:
        runs[0].text = text
        for extra in runs[1:]:
            extra._r.getparent().remove(extra._r)
        run = runs[0]
    if highlight:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def centre(p_el) -> None:
    """Centre a raw w:p, keeping pPr's schema order (jc before rPr)."""
    ppr = p_el.get_or_add_pPr()
    jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center")
    rpr = ppr.find(qn("w:rPr"))
    if rpr is not None:
        rpr.addprevious(jc)
    else:
        ppr.append(jc)


def borders(table, edges: dict[str, int]) -> None:
    tbl_pr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        size = edges.get(edge, 0)
        e.set(qn("w:val"), "single" if size else "nil")
        if size:
            e.set(qn("w:sz"), str(size))
            e.set(qn("w:color"), "000000")
        b.append(e)
    tbl_pr.append(b)


# ---------------------------------------------------------------- blocks

def caption(anchor, kind: str, number: str, title: str, *, keep_next=True) -> None:
    """APA: the label in bold and the title in italics, above the table or figure.

    The label carries a SEQ field, so the template's lists of tables and figures (TOC \\c) find
    it; the title follows on a new line in the same paragraph, so the list shows both.
    """
    par = body_par(anchor, align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6, line=1.0,
                   keep_next=keep_next)
    run = par.add_run(f"{kind} ")
    font(run); run.bold = True
    field(par, f"SEQ {kind} \\* ARABIC", number.split()[-1], bold=True)
    br = par.add_run(); br.add_break(WD_BREAK.LINE); font(br)
    add_runs(par, title, italic=True)


def table(doc, anchor, rows: list[list[str]], widths: list[float] | None = None,
          size: float = 10) -> None:
    ncols = len(rows[0])
    t = doc.add_table(rows=len(rows), cols=ncols)
    anchor.addprevious(t._tbl)
    borders(t, {"top": 8, "bottom": 8, "insideH": 2})
    if widths is None:
        # Width in proportion to each column's longest cell, with a floor.
        longest = [max(len(r[c]) for r in rows) for c in range(ncols)]
        weights = [max(8, min(l, 90)) for l in longest]
        widths = [16.5 * w / sum(weights) for w in weights]
    for c, w in enumerate(widths):
        for cell in t.columns[c].cells:
            cell.width = Cm(w)
    for ri, row in enumerate(rows):
        for ci, text in enumerate(row):
            cell = t.cell(ri, ci)
            par = cell.paragraphs[0]
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.line_spacing = 1.0
            add_runs(par, text, size=size, bold=ri == 0)
            if ri == 0:
                tr_pr = t.rows[0]._tr.get_or_add_trPr()
                h = OxmlElement("w:tblHeader"); tr_pr.append(h)
    # The header row ruled off from the body, as APA tables are.
    for cell in t.rows[0].cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        b = OxmlElement("w:tcBorders")
        e = OxmlElement("w:bottom")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "6"); e.set(qn("w:color"), "000000")
        b.append(e); tc_pr.append(b)
    after = body_par(anchor, after=6, line=1.0)
    after.paragraph_format.space_after = Pt(6)


def figure(anchor, path: pathlib.Path) -> None:
    par = body_par(anchor, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12, line=1.0)
    par.add_run().add_picture(str(path), width=Cm(15.5))


def heading(anchor, level: int, text: str, *, new_page: bool) -> None:
    if level == 1:
        text = re.sub(r"^(\d+)\s+", r"\1  ", text).upper()
    par = body_par(anchor, align=WD_ALIGN_PARAGRAPH.LEFT, before=18 if level == 1 else 12,
                   after=6, line=1.0, keep_next=True)
    run = par.add_run(text)
    font(run, BODY, SIZES[level]); run.bold = True
    outline(par, level - 1)
    if new_page:
        page_break_before(par)


def render(doc, anchor, text: str, base: pathlib.Path) -> None:
    lines = text.split("\n")
    i = 0
    pending_caption: tuple[str, str] | None = None
    pending_figure: pathlib.Path | None = None
    first = True
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1; continue
        m = re.match(r"^(#{1,3}) (.*)$", line)
        if m:
            heading(anchor, len(m.group(1)), m.group(2).strip(), new_page=first)
            first = False
            i += 1; continue
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", line)
        if m:  # Markdown puts the image first; APA puts the caption first, so hold it.
            pending_figure = (base / m.group(1)).resolve()
            i += 1; continue
        m = re.match(r"^\*\*(Table|Figure) (\d+)\*\*\s*$", line)
        if m:
            title = lines[i + 1].strip().strip("*")
            caption(anchor, m.group(1), m.group(2), title)
            if m.group(1) == "Figure" and pending_figure:
                figure(anchor, pending_figure)
                pending_figure = None
            i += 2; continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            table(doc, anchor, rows)
            continue
        m = re.match(r"^(\d+)\. (.*)$", line)
        b = re.match(r"^- (.*)$", line)
        if m or b:
            par = body_par(anchor, left=1.0, hanging=0.6, after=3)
            run = par.add_run(f"{m.group(1)}.\t" if m else "•\t"); font(run)
            add_runs(par, (m or b).group(2) if m else b.group(1))
            i += 1; continue
        par = body_par(anchor)
        add_runs(par, line.strip())
        i += 1


def references(anchor, text: str) -> None:
    heading(anchor, 1, "References", new_page=True)
    for line in text.split("\n"):
        if not re.match(r"^[A-Za-z][^#]*\((\d{4}|n\.d\.)", line):
            continue  # the file's working header
        entry = re.sub(r"\s+—\s+(\[\d+\]|new).*$", "", line.strip())
        par = body_par(anchor, align=WD_ALIGN_PARAGRAPH.LEFT, left=1.27, hanging=1.27,
                       after=6, line=1.5)
        add_runs(par, entry)


def appendices(doc, anchor, log_text: str) -> None:
    heading(anchor, 1, "Appendix A: Code", new_page=True)
    par = body_par(anchor)
    add_runs(par, "The framework, the experiments, their predictions and results, and the AI-use "
                  "log are kept in the project's repository: ")
    run = par.add_run(TODO_REPO); font(run); run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    # Appendix C's eight columns need a landscape page: the body's section ends here, and the
    # document's last section (the anchor) is turned on its side.
    brk = body_par(anchor, after=0, line=1.0)
    portrait = copy.deepcopy(anchor)
    brk._p.get_or_add_pPr().append(portrait)
    for tag in ("w:pgNumType",):
        old = anchor.find(qn(tag))
        if old is not None:
            anchor.remove(old)
    size = anchor.find(qn("w:pgSz"))
    w, h = size.get(qn("w:w")), size.get(qn("w:h"))
    size.set(qn("w:w"), h); size.set(qn("w:h"), w); size.set(qn("w:orient"), "landscape")
    heading(anchor, 1, "Appendix C: AI-Use Log", new_page=False)
    par = body_par(anchor)
    add_runs(par, "Each row records a correction to AI output: what the AI produced, what was "
                  "wrong, how it was caught and the correction made. Entries marked *rebuilt* "
                  "were reconstructed from the project's records rather than logged at the time.")
    rows = []
    for line in log_text.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                rows.append(cells)
    table(doc, anchor, rows, widths=[0.8, 2.0, 2.6, 4.4, 4.8, 3.9, 4.4, 1.3], size=8)


# ---------------------------------------------------------------- the build

def french(text: str) -> str:
    """French typography: a non-breaking space before ; : and inside numbers."""
    text = re.sub(r" ([;:!?])", "\u00a0\\1", text)
    return re.sub(r"(\d) (\d{3})", "\\1\u00a0\\2", text)


def section_body(path: pathlib.Path) -> str:
    return path.read_text().split("\n", 1)[1].strip()


def build(out: pathlib.Path) -> None:
    texts = {name: (HERE / name).read_text() for name in SECTIONS}
    mapping = numbering([texts[n] for n in SECTIONS])
    texts = {n: renumber(t, mapping) for n, t in texts.items()}

    global PARENT
    doc = Document(str(TEMPLATE))
    PARENT = doc._body
    pars = doc.paragraphs
    by_text = lambda s: [p for p in pars if p.text.strip() == s]

    # Front matter.
    for p in by_text("Title"):
        set_text(p, TITLE)
    set_text(by_text("Student Name")[0], STUDENT)
    for p in by_text("Dr. xxxx"):
        set_text(p, SUPERVISOR)
    xs = [p for p in pars if re.fullmatch(r"x{20,}\.?", p.text.strip())]
    # In order: student statement, acknowledgements, abstract, résumé.
    set_text(xs[0], TODO_STATEMENT, highlight=True)
    set_text(xs[1], TODO_ACK, highlight=True)

    # The template gives its title-page and statement lines outline levels, so a contents page
    # lists them as headings; only the front-matter headings from the acknowledgements on keep one.
    ack = by_text("ACKNOWLEDGEMENTS")[0]
    for p in pars:
        if p is ack:
            break
        ppr = p._p.pPr
        if ppr is not None:
            for lvl in ppr.findall(qn("w:outlineLvl")):
                ppr.remove(lvl)
    # The template's contents heading carries a stray "s", in runs "s" | "C" | "ONTENT".
    ts = list(doc.element.body.iter(qn("w:t")))
    for a, b, c in zip(ts, ts[1:], ts[2:]):
        if (a.text, b.text, c.text) == ("s", "C", "ONTENT"):
            a.text, c.text = "", "ONTENTS"
            break
    else:
        raise SystemExit("the template's contents heading was not found")
    # A manual page break directly before a section break (which itself starts a new page)
    # makes Word number two pages alike; the section break alone does the job.
    body_list = list(doc.element.body)
    for el, nxt in zip(body_list, body_list[1:]):
        if nxt.find(".//" + qn("w:sectPr")) is not None and not "".join(nxt.itertext()).strip() \
                and not "".join(el.itertext()).strip():
            for br in el.iter(qn("w:br")):
                if br.get(qn("w:type")) == "page":
                    br.getparent().remove(br)
    # Front matter in roman numerals, numbered on from the conduct page (the template restarts
    # at the acknowledgements, which numbers two pages ii, and leaves later sections arabic).
    sects = [s for s in doc.element.body.iter(qn("w:sectPr"))][:-1]
    for k, sp in enumerate(sects[1:]):
        pg = sp.find(qn("w:pgNumType"))
        if pg is None:  # schema order: pgNumType comes before cols
            pg = OxmlElement("w:pgNumType"); sp.find(qn("w:cols")).addprevious(pg)
        pg.set(qn("w:fmt"), "lowerRoman")
        if k > 0 and pg.get(qn("w:start")) is not None:
            del pg.attrib[qn("w:start")]

    # The roman page number sits in a text box 13.65 pt wide, which clips "viii" to "vii".
    # Widen it about its centre, in both the drawing and its legacy fallback, and centre the
    # number inside it.
    for section in doc.sections:
        ftr = section.footer._element
        for ext in ftr.iter(qn("wp:extent")):
            if ext.get("cx") == "173355":
                anchor_el = ext.getparent()
                pos = anchor_el.find(qn("wp:positionH")).find(qn("wp:posOffset"))
                grow = 457200 - 173355  # to 36 pt
                pos.text = str(int(pos.text) - grow // 2)
                ext.set("cx", "457200")
                for xfrm_ext in anchor_el.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}ext"):
                    if xfrm_ext.get("cx") == "173355":
                        xfrm_ext.set("cx", "457200")
                for par in anchor_el.iter(qn("w:p")):
                    centre(par)
        for shape in ftr.iter("{urn:schemas-microsoft-com:vml}shape"):
            style = shape.get("style", "")
            if "width:13.65pt" in style:
                style = style.replace("width:13.65pt", "width:36pt")
                style = re.sub(r"margin-left:([\d.]+)pt",
                               lambda m: f"margin-left:{float(m.group(1)) - 11.175:.2f}pt", style)
                shape.set("style", style)
                for par in shape.iter(qn("w:p")):
                    centre(par)

    abstract = section_body(HERE / "00_abstract.md")
    body, keywords = abstract.split("**Keywords:**")
    set_text(xs[2], body.strip())
    kw = [p for p in pars if p.text.strip().startswith("Keywords:")][0]
    set_text(kw, "")
    r = kw.add_run("Keywords: "); font(r); r.bold = True
    r = kw.add_run(keywords.strip()); font(r)

    page_break_before([p for p in pars if p.text.strip().startswith("RESUME")][0])
    resume = french(section_body(HERE / "00_resume.md"))
    body, mots = re.split(r"\*\*Mots-clés\u00a0?:\*\*", resume)
    set_text(xs[3], body.strip())
    mc = [p for p in pars if p.text.strip().startswith("Mots cl")][0]
    for run in list(mc.runs):
        run._r.getparent().remove(run._r)
    r = mc.add_run("Mots-clés\u00a0: "); font(r); r.bold = True
    r = mc.add_run(mots.strip()); font(r)

    # Replace the template's sample sections: everything after the résumé's section break.
    body_el = doc.element.body
    sect = body_el[-1]
    assert sect.tag == qn("w:sectPr")
    started = False
    for el in list(body_el):
        if el is mc._p:
            started = True
            continue
        if started and el is not sect:
            body_el.remove(el)
    # The body is numbered from 1 in arabic numerals.
    pg = sect.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sect.find(qn("w:cols")).addprevious(pg)
    pg.set(qn("w:start"), "1"); pg.set(qn("w:fmt"), "decimal")

    for name in SECTIONS:
        render(doc, sect, texts[name], HERE)
    references(sect, (HERE / "references_apa.md").read_text())
    appendices(doc, sect, (ROOT / "notes" / "ai_use_log.md").read_text())

    doc.save(str(out))
    print(f"wrote {out}; renumbered {len(mapping)} captions: "
          + ", ".join(f"{k}→{v}" for k, v in mapping.items()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", type=pathlib.Path, default=HERE / "interim_report.docx")
    build(ap.parse_args().out)
