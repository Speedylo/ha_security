#!/usr/bin/env python3
"""Fill the programme's report template with the final report's sections.

The final report takes the interim report's format (plan, 2026-11-04): the template's front matter
(conduct page, student statement, supervisor approval, acknowledgements, contents, lists of figures
and tables, abstract and French résumé), Times New Roman, APA captions, tables and figures numbered
in one sequence through the body. The template handling is the interim build's
(`interim/build_interim.py`), reused here; this file adds what the final report has and the interim
did not: code blocks, block quotes, the abbreviations list, lettered appendix captions, the
reference list as Section 17, and Appendix H on landscape pages.

    python3 submission/build_final.py [-o OUT.docx]

Then render through Word (`interim/render_word.ps1`) to fill the contents and the lists.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import pathlib
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("build_interim", ROOT / "interim/build_interim.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

SECTIONS = ["01_introduction.md", "02_problem_statement.md", "03_project_specification.md",
            "04_steeple.md", "05_engineering_standards.md", "06_logic_model.md",
            "07_literature_review.md", "08_methodology_and_design.md", "09_system_architecture.md",
            "10_feasibility.md", "11_data_presentation.md", "12_results.md",
            "13_ai_use_and_evaluation.md", "14_learning_strategies.md", "15_future_work.md",
            "16_conclusion.md"]
REFERENCES = "17_references.md"
APPENDICES = ["18_appendices.md", "19_appendix_e_architecture_detail.md",
              "20_appendix_f_results_detail.md", "21_appendix_g_ai_use_disclosure.md"]
LOG = "22_appendix_h_ai_use_log.md"  # on landscape pages, as in the interim


def front(name: str) -> str:
    """One `## ` part of 00_front_matter.md, without its heading."""
    t = (HERE / "00_front_matter.md").read_text()
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", t, re.S | re.M)
    return m.group(1).replace("\n---\n", "\n").strip()


def rows_of(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            rows.append(cells)
    return rows


def table(doc, anchor, rows: list[list[str]], **kw) -> None:
    """The interim build's table, kept on one page when it is short (a table of up to 15 rows that
    starts near the foot of a page otherwise leaves its header behind)."""
    B.table(doc, anchor, rows, **kw)
    if len(rows) <= 15:
        tbl = anchor.getprevious().getprevious()
        trs = tbl.findall(qn("w:tr"))
        for tr in trs[:-1]:
            for p in tr.iter(qn("w:p")):
                ppr = p.find(qn("w:pPr"))
                if ppr is None:
                    ppr = OxmlElement("w:pPr"); p.insert(0, ppr)
                if ppr.find(qn("w:keepNext")) is None:
                    ppr.insert(0, OxmlElement("w:keepNext"))


def renumber(text: str, mapping: dict[str, str]) -> str:
    """The interim build's renumbering, extended to a plural list: in "Tables 12.2 and 12.3" the
    second number has no word of its own before it, so the interim's pattern left it unchanged."""
    def plural(m):
        kind = m.group(1)
        nums = re.sub(r"\d+\.\d+", lambda n: mapping.get(f"{kind} {n.group(0)}", f"{kind} {n.group(0)}").split()[1],
                      m.group(2))
        return f"{kind}s {nums}"
    text = re.sub(r"\b(Table|Figure)s ((?:\d+\.\d+)(?:(?:,| and| or| to) \d+\.\d+)+)", plural, text)
    return B.renumber(text, mapping)


def letter_caption(anchor, kind: str, label: str, title: str) -> None:
    """An appendix caption ("Table C.1"): APA's form, without the SEQ field that would put it in
    the body's lists and numbering."""
    par = B.body_par(anchor, align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6, line=1.0,
                     keep_next=True)
    run = par.add_run(f"{kind} {label}"); B.font(run); run.bold = True
    if title:
        br = par.add_run(); br.add_break(); B.font(br)
        B.add_runs(par, title, italic=True)


def code(anchor, lines: list[str]) -> None:
    for k, line in enumerate(lines):
        par = B.body_par(anchor, align=WD_ALIGN_PARAGRAPH.LEFT, left=0.6,
                         before=6 if k == 0 else 0, after=6 if k == len(lines) - 1 else 0,
                         line=1.0, keep_next=k < len(lines) - 1)
        run = par.add_run(line or " ")
        B.font(run, B.MONO, 9)


def render(doc, anchor, text: str, *, appendix: bool = False) -> None:
    lines = text.split("\n")
    i, first, pending_figure, after_heading = 0, True, None, False
    size = 9 if appendix else 10
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip() == "---":  # a horizontal rule: the headings divide
            i += 1; continue
        if line.startswith("```"):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            code(anchor, lines[i + 1:j])
            i = j + 1; continue
        m = re.match(r"^(#{1,3}) (.*)$", line)
        if not m:
            after_heading = False
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            title = re.sub(r"^(\d+)\.\s+", r"\1 ", title)  # "12. Results" → "12 Results"
            # A lettered appendix starts a page, unless it follows straight on from the heading
            # above it ("Appendices", then "Appendix A"), which has just started one.
            new_page = first or (title.startswith("Appendix ") and not after_heading)
            B.heading(anchor, level, title, new_page=new_page)
            first, after_heading = False, True
            i += 1; continue
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", line)
        if m:
            pending_figure = (HERE / m.group(1)).resolve()
            i += 1; continue
        m = re.match(r"^\*\*(Table|Figure) (\d+)\*\*\s*$", line)
        if m:  # a body caption, already renumbered
            B.caption(anchor, m.group(1), m.group(2), lines[i + 1].strip().strip("*"))
            if m.group(1) == "Figure" and pending_figure:
                B.figure(doc, anchor, pending_figure); pending_figure = None
            i += 2; continue
        m = re.match(r"^\*\*(Table|Figure) ([A-K]\.\d+)\*\*\s*$", line)
        if m:  # an appendix caption with its title on the next line
            letter_caption(anchor, m.group(1), m.group(2), lines[i + 1].strip().strip("*"))
            if m.group(1) == "Figure" and pending_figure:
                B.figure(doc, anchor, pending_figure); pending_figure = None
            i += 2; continue
        m = re.match(r"^\*\*(Table|Figure) ([A-K]\.\d+) — (.+?)\*\*\s*(.*)$", line)
        if m:  # an appendix caption in one line, sometimes followed by a note
            letter_caption(anchor, m.group(1), m.group(2), m.group(3).rstrip("."))
            if m.group(4):
                par = B.body_par(anchor); B.add_runs(par, m.group(4))
            i += 1; continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i]); i += 1
            rows = rows_of(block)
            if rows and not any(rows[0]):  # a headless two-column list (the abbreviations)
                rows = rows[1:]
            table(doc, anchor, rows, size=size)
            continue
        if line.startswith("> "):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").strip()); i += 1
            for q in " ".join(quote).split("  "):
                par = B.body_par(anchor, left=1.27); B.add_runs(par, q.strip())
            continue
        m = re.match(r"^(\d+)\. (.*)$", line)
        b = re.match(r"^- (.*)$", line)
        if m or b:
            par = B.body_par(anchor, left=1.0, hanging=0.6, after=3)
            run = par.add_run(f"{m.group(1)}.\t" if m else "•\t"); B.font(run)
            B.add_runs(par, m.group(2) if m else b.group(1))
            i += 1; continue
        par = B.body_par(anchor)
        B.add_runs(par, line.strip())
        i += 1


def references(anchor, text: str) -> None:
    title = re.search(r"^# (.*)$", text, re.M).group(1)
    B.heading(anchor, 1, re.sub(r"^(\d+)\.\s+", r"\1 ", title), new_page=True)
    for line in text.split("\n"):
        if not re.match(r"^[A-Za-z][^#]*\((\d{4}|n\.d\.)", line):
            continue
        par = B.body_par(anchor, align=WD_ALIGN_PARAGRAPH.LEFT, left=1.27, hanging=1.27,
                         after=6, line=1.5)
        B.add_runs(par, line.strip())


def landscape_log(doc, anchor, text: str) -> None:
    """Appendix H's eight columns on landscape pages: the portrait section ends here."""
    brk = B.body_par(anchor, after=0, line=1.0)
    portrait = copy.deepcopy(anchor)
    brk._p.get_or_add_pPr().append(portrait)
    old = anchor.find(qn("w:pgNumType"))
    if old is not None:
        anchor.remove(old)
    size = anchor.find(qn("w:pgSz"))
    w, h = size.get(qn("w:w")), size.get(qn("w:h"))
    size.set(qn("w:w"), h); size.set(qn("w:h"), w); size.set(qn("w:orient"), "landscape")
    title, rest = text.split("\n", 1)
    B.heading(anchor, 2, title.lstrip("# ").strip(), new_page=False)
    par = B.body_par(anchor)
    B.add_runs(par, rest.strip().split("\n\n")[0])
    rows = rows_of([l for l in text.split("\n") if l.startswith("|")])
    B.table(doc, anchor, rows, widths=[0.7, 1.6, 2.8, 4.2, 5.2, 4.2, 3.6, 2.2], size=8)


def build(out: pathlib.Path) -> None:
    names = SECTIONS + APPENDICES + [LOG]
    texts = {n: (HERE / n).read_text() for n in names}
    mapping = B.numbering([texts[n] for n in SECTIONS])
    texts = {n: renumber(t, mapping) for n, t in texts.items()}

    doc = Document(str(B.TEMPLATE))
    B.PARENT = doc._body
    pars = doc.paragraphs
    by_text = lambda s: [p for p in pars if p.text.strip() == s]

    # The interim build's front matter, as it stands, with the final report's texts. It reads
    # its abstract and résumé from interim/; they are replaced below.
    for p in by_text("Title"):
        B.set_text(p, B.TITLE)
    B.set_text(by_text("Capstone Design Interim Report")[0], "Capstone Design Final Report")
    B.set_text(by_text("Student Name")[0], B.STUDENT)
    for p in by_text("Dr. xxxx"):
        B.set_text(p, B.SUPERVISOR)
    xs = [p for p in pars if re.fullmatch(r"x{20,}\.?", p.text.strip())]
    for label, name in (("Student’s name:", B.STUDENT), ("Supervisor’s name:", B.SUPERVISOR)):
        par = [p for p in pars if p.text.strip() == label][0]
        for run in par.runs[1:]:
            if not run.text.strip():
                run._r.getparent().remove(run._r)
        par.runs[-1].text = par.runs[-1].text.rstrip() + " "
        run = par.add_run(name)
        if par.runs[0]._r.rPr is not None:
            run._r.insert(0, copy.deepcopy(par.runs[0]._r.rPr))
    caption_par = [p for p in pars if p.text.strip() == "Student’s name"][0]
    k = next(i for i, p in enumerate(pars) if p._p is caption_par._p)
    line_par, above = pars[k - 1], pars[k - 2]
    assert line_par._p.xpath(".//w:drawing") and not above.text.strip()
    above.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    above.paragraph_format.left_indent = caption_par.paragraph_format.left_indent
    above.paragraph_format.right_indent = caption_par.paragraph_format.right_indent
    run = above.add_run(B.STUDENT)
    if caption_par.runs[0]._r.rPr is not None:
        run._r.insert(0, copy.deepcopy(caption_par.runs[0]._r.rPr))
    else:
        B.font(run)
    B.set_text(xs[0], B.STATEMENT)
    B.set_text(xs[1], front("Acknowledgements"))

    ack = by_text("ACKNOWLEDGEMENTS")[0]
    for p in pars:
        if p is ack:
            break
        ppr = p._p.pPr
        if ppr is not None:
            for lvl in ppr.findall(qn("w:outlineLvl")):
                ppr.remove(lvl)
    ts = list(doc.element.body.iter(qn("w:t")))
    for a, b, c in zip(ts, ts[1:], ts[2:]):
        if (a.text, b.text, c.text) == ("s", "C", "ONTENT"):
            a.text, c.text = "", "ONTENTS"
            break
    else:
        raise SystemExit("the template's contents heading was not found")
    body_list = list(doc.element.body)
    for el, nxt in zip(body_list, body_list[1:]):
        if nxt.find(".//" + qn("w:sectPr")) is not None and not "".join(nxt.itertext()).strip() \
                and not "".join(el.itertext()).strip():
            for br in el.iter(qn("w:br")):
                if br.get(qn("w:type")) == "page":
                    br.getparent().remove(br)
    sects = [s for s in doc.element.body.iter(qn("w:sectPr"))][:-1]
    for k, sp in enumerate(sects[1:]):
        pg = sp.find(qn("w:pgNumType"))
        if pg is None:
            pg = OxmlElement("w:pgNumType"); sp.find(qn("w:cols")).addprevious(pg)
        pg.set(qn("w:fmt"), "lowerRoman")
        if k > 0 and pg.get(qn("w:start")) is not None:
            del pg.attrib[qn("w:start")]
    tof = next(s for s in doc.styles if s.style_id == "TableofFigures").element.get_or_add_rPr()
    fonts = tof.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts"); tof.insert(0, fonts)
    for slot in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(slot), B.BODY)
    for section in doc.sections:
        section.bottom_margin = Pt(82)
    for section in doc.sections:
        ftr = section.footer._element
        for ext in ftr.iter(qn("wp:extent")):
            if ext.get("cx") == "173355":
                anchor_el = ext.getparent()
                pos = anchor_el.find(qn("wp:positionH")).find(qn("wp:posOffset"))
                grow = 457200 - 173355
                pos.text = str(int(pos.text) - grow // 2)
                ext.set("cx", "457200")
                for xfrm_ext in anchor_el.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}ext"):
                    if xfrm_ext.get("cx") == "173355":
                        xfrm_ext.set("cx", "457200")
                for par in anchor_el.iter(qn("w:p")):
                    B.centre(par)
        for shape in ftr.iter("{urn:schemas-microsoft-com:vml}shape"):
            style = shape.get("style", "")
            if "width:13.65pt" in style:
                style = style.replace("width:13.65pt", "width:36pt")
                style = re.sub(r"margin-left:([\d.]+)pt",
                               lambda m: f"margin-left:{float(m.group(1)) - 11.175:.2f}pt", style)
                shape.set("style", style)
                for par in shape.iter(qn("w:p")):
                    B.centre(par)

    abstract, keywords = front("Abstract").split("**Keywords:**")
    B.set_text(xs[2], abstract.strip())
    kw = [p for p in pars if p.text.strip().startswith("Keywords:")][0]
    B.set_text(kw, "")
    r = kw.add_run("Keywords: "); B.font(r); r.bold = True
    r = kw.add_run(keywords.strip()); B.font(r)
    B.page_break_before([p for p in pars if p.text.strip().startswith("RESUME")][0])
    B.page_break_before(by_text("LIST OF FIGURES")[0])
    resume, mots = re.split(r"\*\*Mots-clés\s?:\*\*", B.french(front("Résumé")))
    B.set_text(xs[3], resume.strip())
    mc = [p for p in pars if p.text.strip().startswith("Mots cl")][0]
    for run in list(mc.runs):
        run._r.getparent().remove(run._r)
    r = mc.add_run("Mots-clés : "); B.font(r); r.bold = True
    r = mc.add_run(mots.strip()); B.font(r)

    # The abbreviations and identifiers, on their own page after the list of tables (before the
    # template's page and section breaks that end that page), under a heading formatted as the
    # template's list headings are.
    from docx.text.paragraph import Paragraph
    tables_head = by_text("LIST OF TABLES")[0]
    # The list is a field whose result runs over several paragraphs, and Word rewrites it when it
    # updates the list; insert before the section break that ends the page instead.
    after_list = tables_head._p.getnext()
    while after_list.find(".//" + qn("w:sectPr")) is None:
        after_list = after_list.getnext()
    head = copy.deepcopy(tables_head._p)
    after_list.addprevious(head)
    head_par = Paragraph(head, B.PARENT)
    B.set_text(head_par, "ABBREVIATIONS AND IDENTIFIERS")
    B.page_break_before(head_par)
    abbrev = [l for l in front("Abbreviations and identifiers").split("\n") if l.startswith("|")]
    rows = [["Term", "Meaning"]] + [r for r in rows_of(abbrev) if any(r)]
    B.table(doc, after_list, rows, widths=[4.5, 12.0], size=10)
    # The empty paragraphs the template leaves after the contents spill onto a page of their own
    # once the contents run to several pages; the list of figures starts its own page anyway.
    figs_head = by_text("LIST OF FIGURES")[0]._p
    prev = figs_head.getprevious()
    while prev is not None and prev.tag == qn("w:p") and not "".join(prev.itertext()).strip() \
            and prev.find(".//" + qn("w:sectPr")) is None:
        gone, prev = prev, prev.getprevious()
        gone.getparent().remove(gone)

    # Replace the template's sample sections, as the interim build does.
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
    pg = sect.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sect.find(qn("w:cols")).addprevious(pg)
    pg.set(qn("w:start"), "1"); pg.set(qn("w:fmt"), "decimal")

    # (After the template's sample pages are removed, which would otherwise remove the box too.)
    # The AI Evidence Box the syllabus requires of every deliverable, on its own page after the
    # résumé and inside the front matter's section, so it keeps a roman page number: the box is
    # inserted after the "Mots clés" paragraph, which carries the section break, and the break moves
    # to a paragraph after the box. Set at 12 pt with 1.15 spacing, which fits one page.
    from docx.text.paragraph import Paragraph
    resume_head = [p for p in pars if p.text.strip().startswith("RESUME")][0]
    sect_pr = mc._p.pPr.find(qn("w:sectPr"))
    holder = OxmlElement("w:p")
    mc._p.addnext(holder)
    head = copy.deepcopy(resume_head._p)
    holder.addprevious(head)
    head_par = Paragraph(head, B.PARENT)
    B.set_text(head_par, "AI EVIDENCE BOX")
    B.page_break_before(head_par)
    for para in front("AI Evidence Box").split("\n\n"):
        par = B.body_par(holder, after=6, line=1.15)
        B.add_runs(par, para.strip(), size=12)
    mc._p.pPr.remove(sect_pr)
    holder_ppr = OxmlElement("w:pPr"); holder.append(holder_ppr)
    holder_ppr.append(sect_pr)


    for name in SECTIONS:
        render(doc, sect, texts[name])
    references(sect, (HERE / REFERENCES).read_text())
    for name in APPENDICES:
        render(doc, sect, texts[name], appendix=True)
    landscape_log(doc, sect, texts[LOG])

    doc.save(str(out))
    print(f"wrote {out}; renumbered {len(mapping)} captions")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", type=pathlib.Path, default=HERE / "final_report.docx")
    build(ap.parse_args().out)
