"""Fill the EGR 4402 proposal template with the content of proposal.md.

    python3 proposal/build_proposal.py

Reads  ../CSC_Capstone_Project_Proposal_Template-1.docx  (left untouched)
Writes capstone_proposal.docx next to this script.

The template's guidance text and underscore lines are removed from every section that is
filled; the cover block, the lifecycle table and the readiness checklist are kept.
"""

import copy
import re
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.table import Table
from docx.text.paragraph import Paragraph

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "CSC_Capstone_Project_Proposal_Template-1.docx"
SOURCE = HERE / "proposal.md"
OUTPUT = HERE / "capstone_proposal.docx"

CELL_PT = 8.5
BODY_PT = 10

# Sections whose content is a table already in the template.
TABLE_SECTIONS = {"4.3", "5.3", "8", "9", "10.1", "10.2", "11", "12"}


# ---------------------------------------------------------------- parse proposal.md

def parse(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    sections, key = {}, None
    for line in text.splitlines():
        m = re.match(r"^# (\S+)\s*$", line)
        if m:
            key = m.group(1)
            sections[key] = []
        elif key:
            sections[key].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def paragraphs(body):
    """Blank-line-separated blocks; each `- ` line is its own bullet block."""
    out, buf = [], []
    for line in body.splitlines() + [""]:
        if line.startswith("- "):
            if buf:
                out.append(("p", " ".join(buf)))
                buf = []
            out.append(("bullet", line[2:].strip()))
        elif not line.strip():
            if buf:
                out.append(("p", " ".join(buf)))
                buf = []
        else:
            buf.append(line.strip())
    return out


def table_rows(body):
    rows = [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in body.splitlines()
        if line.strip().startswith("|")
    ]
    return [r for r in rows[1:] if not all(re.fullmatch(r"-+", c) for c in r)]


# ---------------------------------------------------------------- citations

class Citations:
    def __init__(self, refs_body):
        self.entries = {}
        for line in refs_body.splitlines():
            m = re.match(r"^\[@([\w-]+)\]:\s*(.+)$", line.strip())
            if m:
                self.entries[m.group(1)] = m.group(2)
        self.order = []

    def resolve(self, text):
        def num(m):
            key = m.group(1)
            if key not in self.entries:
                sys.exit(f"unknown citation key: {key}")
            if key not in self.order:
                self.order.append(key)
            return f"[{self.order.index(key) + 1}]"

        return re.sub(r"\[@([\w-]+)\]", num, text)


# ---------------------------------------------------------------- docx helpers

def add_runs(paragraph, text, size):
    """Write text with **bold**, *italic* and `code` spans."""
    for part in re.split(r"(\*\*.+?\*\*|`[^`]+`|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
        elif part.startswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(part)
        run.font.size = Pt(size)


def new_paragraph_after(anchor_el, parent, style):
    el = docx.oxml.OxmlElement("w:p")
    anchor_el.addnext(el)
    para = Paragraph(el, parent)
    para.style = style
    return para


def remove(el):
    el.getparent().remove(el)


def set_cell(cell, text, size=CELL_PT):
    first = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:
        remove(extra._p)
    was_bold = any(r.bold for r in first.runs)
    for r in list(first.runs):
        remove(r._r)
    for i, chunk in enumerate(text.split("<br>")):
        para = first if i == 0 else cell.add_paragraph()
        add_runs(para, chunk.strip(), size)
        if was_bold:
            for r in para.runs:
                r.bold = True


def fill_table(table, rows):
    body_rows = table.rows[1:]
    while len(body_rows) < len(rows):
        table._tbl.append(copy.deepcopy(body_rows[-1]._tr))
        body_rows = table.rows[1:]
    for extra in body_rows[len(rows):]:
        remove(extra._tr)
    for row, values in zip(table.rows[1:], rows):
        if len(values) != len(row.cells):
            sys.exit(f"row has {len(values)} cells, table has {len(row.cells)}: {values[0]}")
        for cell, value in zip(row.cells, values):
            if value != "=":
                set_cell(cell, value)


# ---------------------------------------------------------------- build

def section_key(paragraph):
    if paragraph.style.name not in ("Heading 1", "Heading 2"):
        return None
    m = re.match(r"^(\d+(?:\.\d+)?)\.\s", paragraph.text)
    if m:
        return m.group(1)
    return paragraph.text.strip()


def main():
    content = parse(SOURCE.read_text(encoding="utf-8"))
    cites = Citations(content.pop("refs"))
    doc = docx.Document(TEMPLATE)
    body = doc.element.body

    # Cover block and project type.
    cover = {r[0]: r[1] for r in table_rows(content.pop("cover"))}
    for row in doc.tables[1].rows:
        label = row.cells[0].text.strip()
        if label in cover:
            set_cell(row.cells[1], cover[label], size=9)
    chosen = content.pop("type").strip()
    for cell in doc.tables[2].rows[0].cells:
        if chosen in cell.text:
            set_cell(cell, cell.text.replace("[ ]", "[X]"), size=9)

    # Walk the body in order, grouping elements under the heading that owns them.
    groups, current = [], None
    for el in list(body.iterchildren()):
        if el.tag == qn("w:p"):
            para = Paragraph(el, doc)
            key = section_key(para)
            if key is not None:
                current = {"key": key, "heading": el, "items": []}
                groups.append(current)
                continue
        if current is not None and el.tag in (qn("w:p"), qn("w:tbl")):
            current["items"].append(el)

    for group in groups:
        key = group["key"]
        if key not in content and key not in ("13. References", "13", "Submission Readiness Check"):
            continue
        text = content.get(key, "")

        if key in TABLE_SECTIONS:
            tables = [e for e in group["items"] if e.tag == qn("w:tbl")]
            for el in group["items"]:
                if el.tag == qn("w:p") and Paragraph(el, doc).text.strip():
                    remove(el)
            fill_table(Table(tables[0], doc), [[cites.resolve(c) for c in r] for r in table_rows(text)])

        elif key == "5.2":
            objectives = [b for _, b in paragraphs(text)]
            lines = [e for e in group["items"] if Paragraph(e, doc).text.startswith("Objective")]
            for el in group["items"]:
                if el not in lines:
                    remove(el)
            for el, obj in zip(lines, objectives):
                para = Paragraph(el, doc)
                label, rest = obj.split(":", 1)
                for r in list(para.runs):
                    remove(r._r)
                add_runs(para, f"**{label}:** {cites.resolve(rest.strip())}", BODY_PT)

        elif key == "9.1":
            milestones = table_rows(text)
            lines = [e for e in group["items"] if Paragraph(e, doc).text.startswith("Milestone")]
            for el, (i, (what, when)) in zip(lines, enumerate(milestones, 1)):
                para = Paragraph(el, doc)
                for r in list(para.runs):
                    remove(r._r)
                add_runs(para, f"**Milestone {i}:** {what} — **Target date:** {when}", BODY_PT)

        elif key == "13":
            for el in group["items"]:
                remove(el)
            anchor = group["heading"]
            for i, ref in enumerate(cites.order, 1):
                para = new_paragraph_after(anchor, doc, "Normal")
                add_runs(para, f"[{i}] {cites.entries[ref]}", 9)
                anchor = para._p

        elif key == "Submission Readiness Check":
            for el in group["items"]:
                if Paragraph(el, doc).text.strip() == "END OF TEMPLATE":
                    remove(el)

        else:  # prose section
            for el in group["items"]:
                if el.tag == qn("w:tbl") or Paragraph(el, doc).text.strip():
                    remove(el)
            anchor = group["heading"]
            for kind, block in paragraphs(text):
                para = new_paragraph_after(anchor, doc, "List Bullet" if kind == "bullet" else "Normal")
                add_runs(para, cites.resolve(block), BODY_PT)
                anchor = para._p

    unused = set(cites.entries) - set(cites.order)
    if unused:
        sys.exit(f"references never cited: {sorted(unused)}")
    missing = set(content) - {g["key"] for g in groups}
    if missing:
        sys.exit(f"sections in proposal.md with no heading in the template: {sorted(missing)}")

    doc.save(OUTPUT)
    print(f"wrote {OUTPUT.relative_to(HERE.parent)} — {len(cites.order)} references")


if __name__ == "__main__":
    main()
