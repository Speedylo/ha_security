# Verification 4.10 — every reference checked against its source (2026-10-06)

Criteria: `notes/integrity_consistency_prediction.md` §4.10. For each entry: authors, title, venue or
publisher, year, any identifier, and, where a sentence attributes a figure or a quotation to the
source, that sentence. "PDF" means the copy held in `v2/refs/`, read with `pypdf`. "Crossref" and
"handle" mean the DOI's registered record (`api.crossref.org`, `doi.org/api/handles`).

| Ref | Checked against | Result |
|---|---|---|
| [1] | page and JSON resolve (200); the figures re-derive from the committed snapshot (F37) | ok |
| [2], [3], [5], [10] | URLs resolve (200) | ok |
| [4], [6] | the posts: titles and dates (22 and 23 January 2021) | ok |
| [7] | the post: title, CVE-2023-27482 | ok; date added (9 May 2023) |
| [8] | both URLs resolve | ok |
| [9] | PDF metadata; Crossref | ok; DOI added |
| [11] | the topic: title, poster (Thibault Cohen, titilambert), 12 May 2026 | ok |
| [12] | NDSS 2010 record; 25 extensions, 88 %, 76 % as Chapter 2 states | ok |
| [13] | 37th IEEE S&P 2016; 499 SmartApps and 132 device handlers | ok |
| [14] | 25th USENIX Security 2016, six authors | ok |
| [15] | NDSS 2017, seven authors | ok |
| [16] | 26th USENIX Security 2017, seven authors | ok |
| [17] | Crossref | **venue misnamed** ("IEEE Secure Development Conference"; it is the IEEE Cybersecurity Development Conference); the preprint's different title noted (F41) |
| [18] | PDF metadata; Crossref | **venue and DOI were missing**: 8th SpliTech 2023, DOI 10.23919/SpliTech58164.2023.10193747 (F41) |
| [19], [28] | RFC Editor pages resolve; authors and dates as listed | ok |
| [20] | Politecnico di Torino record: title, 2024, defended 24 October 2024 | ok |
| [21] | PDF; Crossref; 713 screened, 16 selected, eight challenges, both challenge names, January 2019 to November 2024, both quotations, word for word | ok |
| [22] | the post: author A. Muñoz, 30 November 2023 | ok; author and date added |
| [23] | 44th IEEE S&P 2023, four authors | ok |
| [24] | arXiv record and full text: 2,562 (the paper says "applications"); the four properties Chapter 2 attributes are each stated | ok |
| [25] | ISO 31000:2018 clause titles 6.3.2, 6.3.3, 6.3.4, 6.4.2 in published tables of contents (ISO's own preview refused the request, 403) | ok, against secondary tables of contents |
| [26] | publisher records: Wiley 2014, ISBN 978-1-118-80999-0; Kohnfelder and Garg, Microsoft *Interface*, 1 April 1999 | ok; ISBN and date added |
| [27] | URL resolves | ok |
| [29] | arXiv record: eight authors in order, USENIX Security '23 | ok |
| §7.44.1's two standards | Common Criteria Part 2 v3.1 R5, read in the primary PDF; NIST SP 800-53 Rev. 5 AU-5, in a transcription, with the DOI checked | **the sentence overstated both** (F40); now cited as [30] and [31] with a dated correction |

Every URL in the bibliography returned 200, except three sites that refuse automated clients
(`doi.org` for MDPI, `iris.polito.it`, `iso.org`). For those, the DOI's registered record or a
second source stood in.
