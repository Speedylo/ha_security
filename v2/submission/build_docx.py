#!/usr/bin/env python3
"""Combine the submission sections into one .docx.

Generated, not hand-maintained, for the same reason the figures and the contents
page are: a document assembled by hand drifts from the sources it was assembled
from, and nothing says so. Re-run after editing any section.

    python3 build_docx.py [-o OUT.docx]
"""

from __future__ import annotations

import argparse
import pathlib
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml.ns import nsmap, qn
from docx.shared import Cm, Pt, RGBColor

HERE = pathlib.Path(__file__).parent

# Word 2016's namespace for SVG pictures, unknown to python-docx (see add_figure).
nsmap["asvg"] = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"

# Order is the report's order. The front matter is handled specially.
FILES = [
    "00_front_matter.md",
    "01_introduction.md",
    "02_problem_statement.md",
    "03_project_specification.md",
    "04_steeple.md",
    "05_engineering_standards.md",
    "06_logic_model.md",
    "07_literature_review.md",
    "08_methodology_and_design.md",
    "09_system_architecture.md",
    "10_feasibility.md",
    "11_data_presentation.md",
    "12_results.md",
    "13_ai_use_and_evaluation.md",
    "14_learning_strategies.md",
    "15_future_work.md",
    "16_conclusion.md",
    "17_references.md",
    "18_appendices.md",
]

# Typography. Set in one place because every size below is stated relative to
# the 12 pt body: tables and quotes step down from it, headings step up.
BODY = "Times New Roman"
MONO = "Courier New"
PT_BODY = 12
PT_HEADING = 14
PT_TITLE = 18
PT_TABLE = 10
PT_QUOTE = 11
PT_CODE_INLINE = 11
PT_CODE_BLOCK = 10

# **bold** | *italic* | `code` — non-greedy, and bold is tried before italic.
INLINE = re.compile(r"(\*\*.+?\*\*|(?<!\*)\*[^*\n]+?\*(?!\*)|`[^`\n]+?`)")


def set_font(font, name: str) -> None:
    """Set a font by name on every script slot.

    `font.name` alone writes only the ascii and hAnsi slots, so Word falls back
    to the theme font for anything it classifies otherwise — which is why a
    document that looks correct in one viewer can render half in another face.
    """
    font.name = name
    rpr = font.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for slot in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(slot), name)
    # A theme slot (Word's built-in headings carry `asciiTheme="majorHAnsi"`) outranks the
    # explicit name, which is how the headings came out in Calibri Light.
    for slot in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if rfonts.get(qn(slot)) is not None:
            del rfonts.attrib[qn(slot)]


def shade(element, fill: str) -> None:
    """Apply a solid background fill to a paragraph or table cell."""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    element.append(shd)


def add_runs(paragraph, text: str, *, bold: bool = False,
             italic: bool = False) -> None:
    """Write `text` into `paragraph`, honouring inline markdown.

    Recursive, because the markers nest: a bold span routinely contains an
    inline code span, and handling the outer marker alone emits the inner
    marker's backticks as literal characters.
    """
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            add_runs(paragraph, piece[2:-2], bold=True, italic=italic)
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            run = paragraph.add_run(piece[1:-1])
            set_font(run.font, MONO)
            run.font.size = Pt(PT_CODE_INLINE)
            run.bold, run.italic = bold or None, italic or None
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            add_runs(paragraph, piece[1:-1], bold=bold, italic=True)
        else:
            run = paragraph.add_run(piece)
            # None, not False: a run that says "not bold" overrides its paragraph's style,
            # which left every caption in regular weight.
            run.bold, run.italic = bold or None, italic or None


def _is_continuation(line: str) -> bool:
    """True when `line` continues the list item above it rather than starting
    a new block."""
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^\s*([-*]\s+|\d+[.)]\s+)", line):
        return False
    return not stripped.startswith(("#", "|", ">", "```", "---", "***"))


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    return bool(re.match(r"^\|[\s:\-|]+\|?$", line.strip())) and "-" in line


def add_table(doc, rows: list[list[str]]) -> None:
    # Several tables in the sources are borderless key/value lists written with
    # an empty header row. Rendered as a header they become a shaded blank
    # band, so the row is dropped rather than styled.
    has_header = any(cell.strip() for cell in rows[0])
    if not has_header and len(rows) > 1:
        rows = rows[1:]
    width = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=width)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = column_widths(rows, width)
    grid = table._tbl.tblGrid
    for c, col in enumerate(grid.findall(qn("w:gridCol"))):
        col.set(qn("w:w"), str(int(widths[c] * 567)))
    for r, row in enumerate(rows):
        tr_pr = table.rows[r]._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        if r == 0 and has_header:
            tr_pr.append(OxmlElement("w:tblHeader"))
        for c in range(width):
            cell = table.cell(r, c)
            cell.width = Cm(widths[c])
            cell.text = ""
            para = cell.paragraphs[0]
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            text = row[c] if c < len(row) else ""
            add_runs(para, text)
            # A header keeps with the first row below it, so a table never starts with
            # its header alone at the foot of a page.
            if r == 0 and has_header:
                para.paragraph_format.keep_with_next = True
            for run in para.runs:
                run.font.size = Pt(PT_TABLE)
                if r == 0 and has_header:
                    run.bold = True
            if r == 0 and has_header:
                shade(cell._tc.get_or_add_tcPr(), "E8ECF2")
    doc.add_paragraph()


TEXT_WIDTH_CM = 16.0


def column_widths(rows: list[list[str]], width: int) -> list[float]:
    """Share the text width by how much each column holds, so that an ID or a number
    does not take as much room as a sentence. Long text is damped (square root), and
    no column falls below 1.6 cm."""
    def plain(text: str) -> str:
        return re.sub(r"[*`]", "", text)
    weight = []
    for c in range(width):
        cells = [plain(row[c]) if c < len(row) else "" for row in rows]
        longest_word = max((len(w) for t in cells for w in t.split()), default=1)
        mean = sum(len(t) for t in cells) / max(len(cells), 1)
        weight.append(max(mean ** 0.5, longest_word ** 0.5 * 1.2, 1.0))
    # A column is never narrower than its longest word, so that a name such as
    # `adaptive_lighting` is not broken in two (about 0.215 cm a monospace character at table size, plus cell padding;
    # capped so that one long path cannot take the table), nor narrower than 1.6 cm.
    floors = []
    for c in range(width):
        words = [w for row in rows if c < len(row) for w in plain(row[c]).split()]
        longest = max((len(w) for w in words), default=1)
        floors.append(min(max(1.6, longest * 0.215 + 0.45), 5.5))
    total = sum(weight)
    raw = [TEXT_WIDTH_CM * w / total for w in weight]
    fixed: set[int] = set()        # a column held at its floor stays there
    for _ in range(width):
        below = {i for i in range(width) if raw[i] < floors[i] - 1e-9}
        if not below:
            break
        fixed |= below
        spare = TEXT_WIDTH_CM - sum(floors[i] for i in fixed)
        rest = sum(weight[i] for i in range(width) if i not in fixed)
        if spare <= 0 or rest <= 0:
            break
        raw = [floors[i] if i in fixed else spare * weight[i] / rest for i in range(width)]
    return raw


def add_figure(doc, svg: pathlib.Path) -> None:
    """Embed a figure as SVG, the figure of record, with its PNG as Word's fallback.

    Word stores an SVG picture as an ordinary PNG picture whose blip carries an
    extension pointing at the SVG part; Word 2016 and later, and its PDF export,
    draw the SVG, and older readers draw the PNG. python-docx writes only the
    PNG half, so the SVG part and the extension are added here. The PNG is the
    one each figure script writes beside its SVG.
    """
    png = svg.with_suffix(".png")
    if not png.exists():
        raise SystemExit(f"{png.name} missing: run the figure's script with cairosvg installed")
    doc.add_picture(str(png), width=Cm(16))
    para = doc.paragraphs[-1]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # A figure's caption stands below it, so the figure keeps with the caption.
    para.paragraph_format.keep_with_next = True
    package = doc.part.package
    svg_part = Part(package.next_partname("/word/media/image%d.svg"), "image/svg+xml",
                    svg.read_bytes(), package)
    rid = doc.part.relate_to(svg_part, RT.IMAGE)
    blip = para._p.xpath(".//a:blip")[0]
    ext_lst = OxmlElement("a:extLst")
    ext = OxmlElement("a:ext")
    ext.set("uri", "{96DAC541-7B7A-43D3-8B79-37D633B846F1}")
    svg_blip = OxmlElement("asvg:svgBlip")
    svg_blip.set(qn("r:embed"), rid)
    ext.append(svg_blip)
    ext_lst.append(ext)
    blip.append(ext_lst)


def add_code(doc, lines: list[str]) -> None:
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(0.6)
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(6)
    shade(para._p.get_or_add_pPr(), "F4F5F7")
    run = para.add_run("\n".join(lines))
    set_font(run.font, MONO)
    run.font.size = Pt(PT_CODE_BLOCK)


def add_quote(doc, lines: list[str]) -> None:
    """A blockquote: indented, left-ruled, and it may contain its own table."""
    block, table_rows = [], []

    def flush_text():
        if not block:
            return
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Cm(0.8)
        para.paragraph_format.space_before = Pt(4)
        para.paragraph_format.space_after = Pt(4)
        shade(para._p.get_or_add_pPr(), "F7F7F4")
        add_runs(para, " ".join(block))
        for run in para.runs:
            if run.font.name != MONO:
                run.font.size = Pt(PT_QUOTE)
        block.clear()

    for line in lines:
        if line.startswith("|") and not is_separator(line):
            flush_text()
            table_rows.append(split_row(line))
        elif is_separator(line):
            continue
        elif not line.strip():
            flush_text()
        else:
            if table_rows:
                add_table(doc, table_rows)
                table_rows = []
            block.append(line.strip())
    flush_text()
    if table_rows:
        add_table(doc, table_rows)


# A caption opens its paragraph in bold: "**Table 12.3 — Title**" or "**Figure 9.1 — Title.** Text".
# The bold part becomes a caption paragraph in its own style, so that the lists of tables and
# figures can be generated from those styles; any text after it follows as an ordinary paragraph.
CAPTION = re.compile(r"^\*\*((Table|Figure) [A-Z0-9][^*]*?)\*\*\s*(.*)$")
CAPTION_STYLE = {"Table": "Table Caption", "Figure": "Figure Caption"}

# The front matter's three generated lists, each the field that builds it.
GENERATED = {
    "Contents": (r'TOC \o "1-3" \h \z \u', "contents page"),
    # Built from a TC field inside each caption (see add_caption): a TOC field over a custom
    # paragraph style found no entries when Word updated it.
    "List of Figures": (r'TOC \h \z \f f', "list of figures"),
    "List of Tables": (r'TOC \h \z \f t', "list of tables"),
}


def add_toc_field(doc, instruction: str = GENERATED["Contents"][0],
                  what: str = "contents page") -> None:
    """A TOC field Word populates on open (References > Update Table)."""
    para = doc.add_paragraph()
    run = para.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = f"Right-click and choose Update Field to build the {what}."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, sep, placeholder, end):
        run._r.append(node)


# Front-matter headings that open a new page. The rest of the front matter (Acknowledgements
# after the abstract's page, List of Tables after the List of Figures) follows on.
FRONT_PAGE_BREAK = {"Abstract", "Acknowledgements", "Contents", "List of Figures",
                    "Abbreviations and identifiers"}


def add_field_run(paragraph, instruction: str) -> None:
    """A field with no result text, such as a TC entry, which prints nothing."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, end):
        run._r.append(node)


def add_caption(doc, title: str, kind: str) -> None:
    para = doc.add_paragraph(style=CAPTION_STYLE[kind])
    add_runs(para, title)
    entry = re.sub(r"[*`]", "", title).replace('"', "'").rstrip(".")
    add_field_run(para, f' TC "{entry}" \\f {kind[0].lower()} \\l 1 ')


def body_started(doc) -> bool:
    return len(doc.sections) > 1


def number_pages(section, fmt: str, start: int | None = None) -> None:
    sect_pr = section._sectPr
    for old in sect_pr.findall(qn("w:pgNumType")):
        sect_pr.remove(old)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    sect_pr.append(pg)


def render(doc, lines: list[str], *, first_file: bool, name: str = "") -> None:
    i, n = 0, len(lines)
    para_buf: list[str] = []

    def flush_para():
        if not para_buf:
            return
        text = " ".join(para_buf)
        para_buf.clear()
        caption = CAPTION.match(text)
        if caption:
            title, kind, rest = caption.groups()
            add_caption(doc, title, kind)
            if not rest:
                return
            text = rest
        para = doc.add_paragraph()
        if name == "17_references.md":
            # An APA reference list hangs each entry from its first line, and long URLs are
            # not stretched across the line by justification.
            para.paragraph_format.left_indent = Cm(1.0)
            para.paragraph_format.first_line_indent = Cm(-1.0)
            para.paragraph_format.space_after = Pt(5)
        else:
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if text.endswith(":"):
            # A sentence that introduces what follows stays on its page.
            para.paragraph_format.keep_with_next = True
        add_runs(para, text)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Figure: ![label](path/to/figure.svg)
        figure = re.match(r"^!\[[^\]]*\]\(([^)]+\.svg)\)$", stripped)
        if figure:
            flush_para()
            add_figure(doc, (HERE / figure.group(1)).resolve())
            i += 1
            continue

        # Fenced code
        if stripped.startswith("```"):
            flush_para()
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            add_code(doc, block)
            continue

        # Table
        if stripped.startswith("|") and i + 1 < n and is_separator(lines[i + 1]):
            flush_para()
            rows = [split_row(lines[i])]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            add_table(doc, rows)
            continue

        # Blockquote
        if stripped.startswith(">"):
            flush_para()
            block = []
            while i < n and lines[i].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            add_quote(doc, block)
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            level, text = len(m.group(1)), m.group(2)
            if first_file and level == 1:
                para = doc.add_paragraph(style="Title")
                add_runs(para, text)
            elif first_file and level == 3:
                add_runs(doc.add_paragraph(style="Subtitle"), text)
            elif first_file:
                # Front matter: headed like a section, but outside the outline, so the
                # contents page begins at the Introduction.
                head = doc.add_paragraph(style="Front Heading")
                # "Page break before" on the heading, not a break paragraph: a break
                # paragraph that falls at the top of a page breaks again and leaves it blank.
                head.paragraph_format.page_break_before = text.strip() in FRONT_PAGE_BREAK
                add_runs(head, text)
                if text.strip() in GENERATED:
                    add_toc_field(doc, *GENERATED[text.strip()])
                    # The source's "*[Generated at typeset time.]*" stands where the field now is.
                    j = i + 1
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and lines[j].strip() == "*[Generated at typeset time.]*":
                        i = j
            else:
                new_page = level == 2 and bool(re.match(r"Appendix [B-Z] ", text))
                if level == 1 and not body_started(doc):
                    # The body starts a section of its own: page 1 at the Introduction,
                    # with the front matter numbered in lower-case roman numerals.
                    number_pages(doc.sections[0], "lowerRoman")
                    number_pages(doc.add_section(WD_SECTION.NEW_PAGE), "decimal", start=1)
                elif level == 1:
                    new_page = True
                head = doc.add_heading(level=min(level, 4))
                head.paragraph_format.page_break_before = new_page
                add_runs(head, text)
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(---+|\*\*\*+)$", stripped):
            flush_para()
            i += 1
            continue

        # Bullets and numbered items. A list item wraps across source lines, so
        # its continuation lines are consumed here — otherwise inline markup
        # opened on one line and closed on the next is split across two
        # paragraphs and survives into the document as literal asterisks.
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        style = "List Bullet"
        if not m:
            m = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
            style = "List Number"
        if m:
            flush_para()
            item = [m.group(1)]
            i += 1
            while i < n and _is_continuation(lines[i]):
                item.append(lines[i].strip())
                i += 1
            para = doc.add_paragraph(style=style)
            add_runs(para, " ".join(item))
            continue

        if not stripped:
            flush_para()
        else:
            para_buf.append(stripped)
        i += 1

    flush_para()


def build(out: pathlib.Path) -> tuple[int, int]:
    doc = Document()

    normal = doc.styles["Normal"]
    set_font(normal.font, BODY)
    normal.font.size = Pt(PT_BODY)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.15

    # Word's built-in heading styles are Calibri Light in an accent colour and
    # inherit nothing useful here, so each is restated: one face, one size,
    # bold, black.
    for level in range(1, 5):
        style = doc.styles[f"Heading {level}"]
        set_font(style.font, BODY)
        style.font.size = Pt(PT_HEADING)
        style.font.bold = True
        style.font.italic = False
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(14 if level <= 2 else 10)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True

    for name in CAPTION_STYLE.values():
        style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = normal
        style.font.bold = True
        style.paragraph_format.space_before = Pt(6)
    # A table's caption stands above it, a figure's below.
    doc.styles["Table Caption"].paragraph_format.keep_with_next = True

    front = doc.styles.add_style("Front Heading", WD_STYLE_TYPE.PARAGRAPH)
    front.base_style = normal
    front.font.size = Pt(PT_HEADING)
    front.font.bold = True
    front.paragraph_format.space_before = Pt(14)
    front.paragraph_format.space_after = Pt(6)
    front.paragraph_format.keep_with_next = True

    subtitle = doc.styles["Subtitle"]
    set_font(subtitle.font, BODY)
    subtitle.font.size = Pt(PT_HEADING)
    subtitle.font.italic = False
    subtitle.font.color.rgb = RGBColor(0, 0, 0)

    title = doc.styles["Title"]
    set_font(title.font, BODY)
    title.font.size = Pt(PT_TITLE)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    # The default template rules a line under the title; a title page does not need one.
    for border in title.element.xpath("./w:pPr/w:pBdr"):
        border.getparent().remove(border)

    for name in ("List Bullet", "List Number", "Quote"):
        if name in [s.name for s in doc.styles]:
            style = doc.styles[name]
            set_font(style.font, BODY)
            style.font.size = Pt(PT_BODY)

    for section in doc.sections:
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.5)
        section.top_margin = section.bottom_margin = Cm(2.5)

    words = 0
    for index, name in enumerate(FILES):
        path = HERE / name
        text = path.read_text()
        words += len(text.split())
        render(doc, text.split("\n"), first_file=(index == 0), name=name)

    _add_page_numbers(doc)
    doc.save(out)
    return len(FILES), words


def _add_page_numbers(doc) -> None:
    for section in doc.sections[:1]:   # later sections link to this footer
        para = section.footer.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        for node in (begin, instr, end):
            run._r.append(node)
        set_font(run.font, BODY)
        run.font.size = Pt(10)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="capstone_report_draft.docx")
    args = ap.parse_args()
    target = HERE / args.out
    count, words = build(target)
    print(f"{count} sections, {words:,} words -> {target}")
