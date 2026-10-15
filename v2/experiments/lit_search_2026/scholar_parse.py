"""Parse Google Scholar result pages saved by hand (protocol §9.1) into raw/scholar_S1.json.gz.

Scholar marks each result with div.gs_ri: the title in h3.gs_rt (a link when Scholar has one), the
authors, venue and year in div.gs_a, and a snippet in div.gs_rs. The pages are untrusted input; they
are only read as text.
"""
import datetime
import gzip
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ScholarPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results, self.cur, self.field, self.depth = [], None, None, 0
        self.text = []  # all visible text, for the result count and the "omitted" notice

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "div" and "gs_ri" in cls.split():
            self.cur = {"title": "", "byline": "", "snippet": "", "url": None}
            self.results.append(self.cur)
        if self.cur is None:
            return
        if tag == "h3" and "gs_rt" in cls:
            self.field, self.depth = "title", 0
        elif tag == "div" and "gs_a" in cls.split():
            self.field, self.depth = "byline", 0
        elif tag == "div" and "gs_rs" in cls.split():
            self.field, self.depth = "snippet", 0
        elif tag == "a" and self.field == "title" and not self.cur["url"]:
            self.cur["url"] = a.get("href")
        if self.field and tag in ("h3", "div"):
            self.depth += 1

    def handle_endtag(self, tag):
        if self.field and tag in ("h3", "div"):
            self.depth -= 1
            if self.depth == 0:
                self.field = None

    def handle_data(self, data):
        self.text.append(data)
        if self.cur is not None and self.field:
            self.cur[self.field] += data


def parse(path):
    p = ScholarPage()
    p.feed(path.read_text(encoding="utf-8", errors="replace"))
    for r in p.results:
        for k in ("title", "byline", "snippet"):
            r[k] = " ".join(r[k].split())
        r["title"] = re.sub(r"^(\W*\[(PDF|HTML|BOOK|B|CITATION|C)\]\s*)+", "", r["title"])
        year = re.findall(r"\b(20\d\d|19\d\d)\b", r["byline"])
        r["year"] = int(year[-1]) if year else None
    text = " ".join(" ".join(p.text).split())
    return p.results, text


def main(notes):
    pages = sorted((HERE / "scholar").glob("*.htm"), key=lambda f: (len(f.name), f.name))
    records, info = [], []
    for page_no, f in enumerate(pages, 1):
        results, text = parse(f)
        count = re.search(r"About ([\d,]+) results|([\d,]+) results?", text)
        omitted = "omitted some entries very similar" in text
        info.append({"file": f.name, "results": len(results), "count_text": count.group(0) if count else None,
                     "omitted_notice": omitted})
        for r in results:
            records.append(dict(r, page=page_no))
    out = {"query_sent": notes["query"], "run_by": "Younes, by hand", "retrieved": notes["when"],
           "range": notes["range"], "reported_total": notes["estimate"], "pages": info,
           "count": len(records), "capped_at": None, "records": records,
           "parsed": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with gzip.open(HERE / "raw" / "scholar_S1.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    for i in info:
        print(i)
    print("records", len(records))


if __name__ == "__main__":
    main({"query": '"Home Assistant" (integration OR plugin OR extension OR "custom component") '
                   '(sandbox OR isolation OR confinement OR permission OR "least privilege" OR "access control")',
          "when": "2026-10-15T19:19 local", "range": "2024-2026 (Scholar custom range)", "estimate": 116})
