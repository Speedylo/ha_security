# §7 after the documented literature search — draft for Younes's approval

**Written 2026-10-15.** §7 was approved on 2026-10-14, before the search ran. The search
(`experiments/lit_search_2026/summary.md`) found nothing that closes the gap, but it found
SandTrap (2021), which §7 did not cite and which bears on two of its sentences, and two works inside
the window worth citing. Nothing below is in `submission/07_literature_review.md` yet. Placeholders
[S], [T] and [K] stand for the new references; their numbers are assigned after approval, because
numbering by first appearance shifts every later reference (see "Renumbering" at the end).

Five changes. Each shows the text as approved, then the proposed text.

---

## 1. §7.1 — the method paragraph states the search

**As approved (from "The review is narrative…" to the end of the paragraph):**

> The review is narrative rather than systematic: the search was not registered in advance, inclusion
> was by judgement, and no second reviewer screened the results. Relevant work may therefore have been
> missed, and Section 7.6 states what would follow if it had. The four sources closest to this project
> [5], [15], [33], [25] were read in full.

**Proposed:**

> For work published before December 2024 the review is narrative, and it relies on Thingnes and
> Meland's systematic review [25] for that period. Work published from December 2024 to October 2026
> was covered by a documented search whose protocol was registered before it ran. Four search strings
> were sent to OpenAlex, Semantic Scholar and arXiv, the works citing the four sources closest to this
> project were collected, and Google Scholar was searched once by hand. Of 642 distinct records, 52 were
> screened on their abstracts; none builds or evaluates confinement of Home Assistant's integrations,
> and five are adjacent, of which the two that bear on the argument are discussed below. Following the
> references of one of them led to an earlier work, SandTrap [S], that the narrative review had missed.
> One reviewer screened every record, and a second checked every adjacent record and a random sample of
> twenty exclusions. The search is documented rather than systematic, since it applies a single
> protocol without appraising the quality of what it includes, so relevant work may still have been
> missed, and Section 7.6 states what would follow if it had. The four sources closest to this project
> [5], [15], [33], [25] were read in full.

*Two conditions:* the sentence on the second reviewer holds only once your review of the B rows and
`review_sample.csv` is done. **And who the "one reviewer" was is your decision:** I screened the
records. If the submission discloses AI assistance elsewhere, this sentence should match it.

## 2. §7.3 — a new closing paragraph after "None transfers to modules…"

**Proposed (new paragraph):**

> One line of work does confine unmodified extensions inside a running platform, on trigger-action
> platforms rather than smart-home hubs. Ahmadpanah et al. [S] found that the nodes extending Node-RED,
> a self-hosted automation platform, are published to an open catalogue and run with the full authority
> of the platform's Node.js process. Their system, SandTrap, wraps each node in a monitor that enforces
> a policy over the modules, interfaces, values and shared state the node may use, without modifying it,
> and the added time stayed below 100 ms per node. The evaluation examined selected benign and malicious
> cases rather than a catalogue, and each policy was written for its case, averaging 2,650 lines for
> Node-RED. TAPShield [T] combines such sandboxes with trusted execution against a compromised cloud and
> reports security, performance and compatibility trade-offs for Node-RED and IFTTT applications. Both
> enforce inside the JavaScript runtime that the extension shares with the platform. Home Assistant's
> integrations are Python modules sharing the platform's interpreter, where Corno and Mannella showed
> one module reaching another's live objects through the garbage collector [5], and Section 9 explains
> why this project separates integrations into processes rather than restricting them within one.

## 3. §7.4 — one sentence in "Independent reviews reach the same position"

**Proposed (inserted after the GitHub Security Lab sentence, before "This project adopts…"):**

> A threat-modelling methodology for smart homes published in 2026 [K] reaches the same point from the
> owner's side: it lists integrations among a home's entry points, cites vulnerabilities disclosed in
> Home Assistant itself, and leaves the mitigation for integration code obtained from GitHub to the
> owner reviewing it.

## 4. §7.6 — the strands paragraph and the gap sentence

**Strands paragraph, proposed addition** (after "…applications that can be changed."):

> Unmodified extensions have been confined on JavaScript trigger-action platforms [S], [T], but by a
> monitor inside the runtime they share with the platform, a boundary that Home Assistant's single
> Python process does not provide [5].

**Gap sentence, as approved:**

> No published work builds or evaluates runtime confinement of Home Assistant's community
> integrations, and none measures the compatibility cost of confining extensions that already exist
> and cannot be rewritten, which determines whether any such scheme can be deployed.

**Proposed:**

> No published work builds or evaluates runtime confinement of Home Assistant's community
> integrations, or measures what fraction of those integrations still work once confined, which
> determines whether any such scheme can be deployed on the platform.

*Why:* the approved second half is about extensions in general. TAPShield reports compatibility
trade-offs on real-world apps, and its full text could not be read, so the general claim cannot be
defended. Narrowed to Home Assistant, it holds whatever TAPShield measured (your decision, 2026-10-15).

## 5. §7.6 — contributions two and three

**Contribution 2, as approved:**

> The second is a confinement architecture for an extension model that cannot be changed, whose novelty
> lies in the retrofit, enforcing declared authority on code written to assume it has none, without the
> cooperation of the platform's maintainers or the integration's author, and not in the manifest.

**Proposed:**

> The second is a confinement architecture for an extension model that cannot be changed. Its novelty
> lies neither in the manifest nor in confining unmodified extensions as such, which SandTrap achieved
> for JavaScript [S], but in doing so for Python integrations that share the platform's process:
> enforcing declared authority on code written to assume it has none, without the cooperation of the
> platform's maintainers or the integration's author.

**Contribution 3, as approved (its last clause):**

> … but none reports what fraction of real, unmodified extensions still work once confined.

**Proposed:**

> … but none reports what fraction of Home Assistant's real, unmodified integrations still work once
> confined, and the closest confinement work on another platform was evaluated on selected cases rather
> than a catalogue [S].

---

## Beyond §7

- **Appendix B, Table B.1, N2** gives as its source "No prior work reports what fraction of real,
  unmodified extensions still work under confinement". If that column is quoted as frozen on
  2026-09-02, it stays as it is, with a dated note; if not, it narrows to "… unmodified Home Assistant
  integrations …". Your call.
- No other section restates the gap: the abstract, §1, §3, §14 and §15 were checked.

## The three references (IEEE)

- [S] M. M. Ahmadpanah, D. Hedin, M. Balliu, L. E. Olsson and A. Sabelfeld, "SandTrap: Securing
  JavaScript-driven trigger-action platforms," in *Proc. 30th USENIX Security Symp.*, 2021,
  pp. 2899–2916. Read in full (author copy, Chalmers).
- [T] M. Moazen, N. Paladi, A. J. Ahsan and M. Balliu, "TAPShield: Securing trigger-action platforms
  against strong attackers," in *Proc. IEEE 10th European Symp. Security and Privacy (EuroS&P)*,
  Venice, Italy, 2025, pp. 60–77, doi: 10.1109/EuroSP63326.2025.00013. Abstract only; full text not
  obtained.
- [K] S. Kulkarni, A. Mylonas and S. Vidalis, "P3CRID: A threat model methodology for smart homes,"
  *Algorithms*, vol. 19, no. 5, Art. no. 347, May 2026, doi: 10.3390/a19050347. Read in full
  (repository copy, University of Hertfordshire).

## Renumbering

[S] and [T] first appear in §7.3 after [38]; [K] in §7.4 after the GitHub Security Lab audit, now [40].
Numbering by first appearance therefore gives [S] = 39 and [T] = 40; the current [39] and [40] become 41
and 42; [K] = 43; and every reference from the current [41] onwards moves up by three, across the whole
submission. That is mechanical, done after approval, in a single
commit with its own map, as on 2026-10-15 (`notes/references_renumbering_20261015.md`).
