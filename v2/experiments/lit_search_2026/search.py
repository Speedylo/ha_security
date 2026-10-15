"""Documented literature search, 2024-12-01 to today (protocol: notes/lit_search_2025_2026_protocol.md).

Runs S1-S4 against OpenAlex, Semantic Scholar and arXiv, and the forward citations of the four seeds
in OpenAlex. Every response is saved under raw/, with the exact query sent, before anything is parsed.
`python3 search.py` fetches; `python3 search.py --merge` builds screening.csv from raw/ without the network.
"""
import csv
import datetime
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SINCE = "2024-12-01"
CAP = 2000  # records kept per query per source; a capped query is marked in its raw file
UA = "capstone-lit-search/1.0"

# The four strings of protocol §4, written once per API's syntax.
QUERIES = {
    "S1": {
        "openalex": '"Home Assistant" AND (integration OR plugin OR extension OR "custom component") AND '
                    '(sandbox OR isolation OR confinement OR permission OR "least privilege" OR "access control")',
        "s2": '"Home Assistant" + (integration | plugin | extension | "custom component") + '
              '(sandbox | isolation | confinement | permission | "least privilege" | "access control")',
        "arxiv": 'all:"Home Assistant" AND (all:integration OR all:plugin OR all:extension OR all:"custom component") AND '
                 '(all:sandbox OR all:isolation OR all:confinement OR all:permission OR all:"least privilege" OR all:"access control")',
    },
    "S2": {
        "openalex": '("smart home" OR "home automation") AND (hub OR gateway OR platform) AND '
                    '(plugin OR extension OR "third-party" OR app) AND '
                    '(sandbox OR isolation OR confinement OR "least privilege" OR permission)',
        "s2": '("smart home" | "home automation") + (hub | gateway | platform) + '
              '(plugin | extension | "third-party" | app) + '
              '(sandbox | isolation | confinement | "least privilege" | permission)',
        "arxiv": '(all:"smart home" OR all:"home automation") AND (all:hub OR all:gateway OR all:platform) AND '
                 '(all:plugin OR all:extension OR all:"third-party" OR all:app) AND '
                 '(all:sandbox OR all:isolation OR all:confinement OR all:"least privilege" OR all:permission)',
    },
    "S3": {
        "openalex": '(openHAB OR "Node-RED" OR Homey OR Hubitat OR Domoticz OR ioBroker) AND '
                    '(sandbox OR isolation OR permission OR "least privilege")',
        "s2": '(openHAB | "Node-RED" | Homey | Hubitat | Domoticz | ioBroker) + '
              '(sandbox | isolation | permission | "least privilege")',
        "arxiv": '(all:openHAB OR all:"Node-RED" OR all:Homey OR all:Hubitat OR all:Domoticz OR all:ioBroker) AND '
                 '(all:sandbox OR all:isolation OR all:permission OR all:"least privilege")',
    },
    "S4": {
        "openalex": '("smart home" OR "Home Assistant" OR "IoT platform") AND (plugin OR integration OR extension) AND '
                    '("API usage" OR overprivilege OR compatibility)',
        "s2": '("smart home" | "Home Assistant" | "IoT platform") + (plugin | integration | extension) + '
              '("API usage" | overprivilege | compatibility)',
        "arxiv": '(all:"smart home" OR all:"Home Assistant" OR all:"IoT platform") AND '
                 '(all:plugin OR all:integration OR all:extension) AND '
                 '(all:"API usage" OR all:overprivilege OR all:compatibility)',
    },
}

# Forward-citation seeds (protocol §3, amendment §9): reference number -> OpenAlex id.
SEEDS = {
    "ref5_corno2022": "W4292348480",
    "ref15_corno2023": "W4385451740",
    "ref33_mannella2024": "W7216995109",
    "ref25_thingnes2025": "W4410819421",
}
SEED_DOIS = {"10.3390/fi17060238"}  # [25] is in the window but is a seed, not a result


def get(url, tries=6):
    """GET with a polite User-Agent; on a rate limit (OpenAlex answers 401 or 429 to heavy boolean
    queries sent faster than one a second), a server error or a dropped connection, wait and retry."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code not in (401, 429, 500, 502, 503) or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == tries - 1:
                raise
        time.sleep(10 * (attempt + 1))


def save(name, query_sent, records, capped, extra=None):
    RAW.mkdir(exist_ok=True)
    out = {"query_sent": query_sent, "retrieved": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "since": SINCE, "count": len(records), "capped_at": CAP if capped else None, "records": records}
    out.update(extra or {})
    with gzip.open(RAW / f"{name}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{name}: {len(records)}{' (capped)' if capped else ''}", flush=True)


def openalex(name, params):
    """Page through an OpenAlex /works query (page numbers: cursor paging now needs a key), keeping the
    raw work objects. Heavy boolean queries are limited to one request a second without a key."""
    records, page_no, total = [], 1, None
    while len(records) < CAP:
        p = dict(params, **{"per-page": "200", "page": str(page_no)})
        page = json.loads(get("https://api.openalex.org/works?" + urllib.parse.urlencode(p)))
        total = page["meta"]["count"]
        records += page["results"]
        time.sleep(1.5)
        if not page["results"] or len(records) >= total:
            break
        page_no += 1
    save(name, "https://api.openalex.org/works?" + urllib.parse.urlencode(params), records[:CAP],
         total > CAP, {"reported_total": total})


def semantic_scholar(name, q):
    """The bulk search endpoint takes the boolean syntax; one request every few seconds without a key."""
    fields = "title,year,publicationDate,venue,externalIds,abstract,url,publicationTypes"
    params = {"query": q, "fields": fields, "publicationDateOrYear": f"{SINCE}:"}
    records, token, total = [], None, None
    while len(records) < CAP:
        p = dict(params, **({"token": token} if token else {}))
        page = json.loads(get("https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + urllib.parse.urlencode(p)))
        total = page.get("total", 0)
        records += page.get("data") or []
        token = page.get("token")
        time.sleep(4)
        if not token:
            break
    save(name, "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + urllib.parse.urlencode(params),
         records[:CAP], total > CAP, {"reported_total": total})


def arxiv(name, q):
    """arXiv's Atom API; the date window goes into the query itself."""
    today = datetime.date.today().strftime("%Y%m%d")
    full = f"({q}) AND submittedDate:[{SINCE.replace('-', '')}0000 TO {today}2359]"
    ns = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/",
          "x": "http://arxiv.org/schemas/atom"}
    records, start, total = [], 0, None
    while start < CAP:
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"search_query": full, "start": start, "max_results": 200})
        root = ET.fromstring(get(url))
        total = int(root.find("o:totalResults", ns).text)
        entries = root.findall("a:entry", ns)
        for e in entries:
            doi = e.find("x:doi", ns)
            records.append({"id": e.find("a:id", ns).text, "title": " ".join(e.find("a:title", ns).text.split()),
                            "published": e.find("a:published", ns).text,
                            "abstract": " ".join(e.find("a:summary", ns).text.split()),
                            "doi": doi.text if doi is not None else None})
        start += 200
        time.sleep(3)
        if not entries or start >= total:
            break
    save(name, "https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(full), records[:CAP],
         total > CAP, {"reported_total": total})


def fetch():
    for sid, q in QUERIES.items():
        # title_and_abstract: the field Semantic Scholar and arXiv search, so the three sources compare
        openalex(f"openalex_{sid}", {"filter": f"from_publication_date:{SINCE},title_and_abstract.search:{q['openalex']}"})
        semantic_scholar(f"s2_{sid}", q["s2"])
        arxiv(f"arxiv_{sid}", q["arxiv"])
    # S1 again over OpenAlex's full text (protocol amendment §10): where a paper closing the gap would be
    openalex("openalex_S1_fulltext", {"filter": f"from_publication_date:{SINCE}", "search": QUERIES["S1"]["openalex"]})
    for ref, wid in SEEDS.items():
        openalex(f"openalex_cites_{ref}", {"filter": f"cites:{wid},from_publication_date:{SINCE}"})


# ---- merge: one row per distinct record, de-duplicated by DOI, then by normalised title ----

def norm_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def norm_doi(d):
    return (d or "").lower().removeprefix("https://doi.org/") or None


def abstract_from_index(inv):
    if not inv:
        return ""
    words = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in words)


def rows_from(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    src = path.name.removesuffix(".json.gz")
    for r in data["records"]:
        if src.startswith("openalex"):
            venue = ((r.get("primary_location") or {}).get("source") or {}).get("display_name")
            yield {"source": src, "title": r.get("title"), "date": r.get("publication_date"), "venue": venue,
                   "doi": norm_doi(r.get("doi")), "url": r.get("id"),
                   "abstract": abstract_from_index(r.get("abstract_inverted_index"))}
        elif src.startswith("s2"):
            ext = r.get("externalIds") or {}
            yield {"source": src, "title": r.get("title"), "date": r.get("publicationDate") or str(r.get("year")),
                   "venue": r.get("venue"), "doi": norm_doi(ext.get("DOI") or (ext.get("ArXiv") and f"10.48550/arxiv.{ext['ArXiv']}")),
                   "url": r.get("url"), "abstract": r.get("abstract") or ""}
        else:
            yield {"source": src, "title": r["title"], "date": r["published"][:10], "venue": "arXiv",
                   "doi": norm_doi(r.get("doi")) or "10.48550/arxiv." + r["id"].rsplit("/abs/", 1)[1].split("v")[0],
                   "url": r["id"], "abstract": r["abstract"]}


def merge():
    by_key, order, found = {}, [], 0
    for path in sorted(RAW.glob("*.json.gz")):
        for row in rows_from(path):
            found += 1
            if row["doi"] in SEED_DOIS:
                continue
            keys = [k for k in (row["doi"] and "doi:" + row["doi"], "t:" + norm_title(row["title"])) if k]
            hit = next((by_key[k] for k in keys if k in by_key), None)
            if hit:
                hit["sources"].add(row["source"])
                hit["abstract"] = hit["abstract"] or row["abstract"]
                hit["doi"] = hit["doi"] or row["doi"]
            else:
                hit = dict(row, sources={row["source"]})
                order.append(hit)
            for k in keys:
                by_key[k] = hit
    cols = ["id", "sources", "title", "date", "venue", "doi", "url", "stage", "decision", "reason", "abstract"]
    with open(HERE / "screening.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(order, 1):
            w.writerow(dict({k: r.get(k) for k in cols}, id=f"R{i:04d}", sources=";".join(sorted(r["sources"])),
                            stage="", decision="", reason=""))
    print(f"records found {found}; after de-duplication {len(order)}")


if __name__ == "__main__":
    merge() if "--merge" in sys.argv else fetch()
