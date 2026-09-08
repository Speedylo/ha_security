# The submission rewrite — outline mapping

**Written 2026-09-08**, against the two capstone outlines in `.claude/Outlines.txt` (Blokbustr, 49
body pages; LucidLink, 61). **Both follow one template**, so that template is the programme's
structure even though the handbook has not arrived. Younes's guidance: no hard page requirement,
30–95 observed, **~60 typical**.

This is the plan for the work `rewrite_consolidation_backlog.md` describes. It is a mapping, not
prose: approve or change the shape here, where it is cheap.

---

## 1. The arithmetic, stated first

| | |
|---|---|
| Chapters 1–8 today | **103,910 words**, 155 tables, **2 figures** |
| Target, ~60 pages | front matter ~8 pp · body ~40 pp · references ~3 pp · appendices ~10 pp |
| Body at ~400 words/page with figures and tables interspersed | **~16,000 words** |
| Required reduction of running prose | **~85%** |

**Two things make that less alarming than it reads.**

1. **Most of the cut is relocation, not deletion.** The 18-threat register, the 20-requirement
   verdict table, the 77-integration results, the syscall list, the corpus manifests — these are
   *tables*. In an appendix they cost almost no words and preserve every piece of evidence a
   reader might want to check. That is where the bulk goes.
2. **Pages are reached with figures, not words.** LucidLink spends 32 of its 61 body pages on
   methodology and architecture, and they are figure-dominated. **This project has two figures.**
   See §4 below — this is the largest piece of genuinely new work and it is additive, not a cut.

---

## 2. The template, and where each section comes from

Merging the two outlines: Blokbustr's separate *System Architecture* chapter is kept (this project
has an architecture worth its own chapter) and LucidLink's *Feasibility Study* is kept (three
experiments already answer it). Legend: **↺** compress from existing · **✎** new writing, sourced
from existing material · **✚** genuinely new.

| § | Section | pp | Source | |
|---|---|---|---|---|
| — | Front matter, abstract, ToC, figures, tables | 8 | `00_front_matter.md` — largely ready | ↺ |
| 1 | Introduction | 2 | Ch 1 §1.1–1.3 (ecosystem scale, Table 1.1) | ↺ |
| 2 | Problem Statement | 2 | Ch 1 §1.4–1.7 + **Table 1.2**, the report's exhibit | ↺ |
| 3 | Project Specification | 3 | Ch 3's 20 requirements → one table; §1.6 scope; §8.7 deliverables | ↺ |
| 3.1–3.6 | Objective · Scope · Key features · Deliverables · Constraints · Expected outcome | | The six sub-heads both examples use | |
| 4 | **STEEPLE Analysis** | 2 | **Nothing exists.** Sourced but unwritten — see §3 below | ✎ |
| 5 | **Engineering Standards** | 3 | ISO 31000 (Ch 4 follows it clause by clause), STRIDE, OWASP Threat Dragon, RFC 1918 — all cited already. Needs 2–3 more named and justified | ✎ |
| 6 | **Logic Model Framework** | 3 | Target population = §1.3's 669,743 / 56.6% HACS; **assumptions = the eight pre-registered predictions**; activities = `01_PLAN.md`'s five stages; outputs = framework + 19 suites + 2 corpora; outcomes = §8.2 | ✎ |
| 7 | Literature Review | 4 | Ch 2 entire, 4,238 → ~1,600 words | ↺ |
| 8 | Methodology and Capstone Design | 8 | Ch 4 threat model (5,554 → ~1,500, register to appendix) + Ch 5 §5.1–5.5 design rationale | ↺ |
| 9 | System Architecture and Technology Integration | 8 | Ch 5 + Ch 6, **39,000 → ~3,200**. The deepest cut in the report | ↺ |
| 10 | Feasibility Study | 2 | `r2_footprint` (technical), `mediation_latency`, the C4 device constraint; economic/legal/ethical/operational are short | ✎ |
| 11 | Data Presentation | 4 | Ch 7's corpora, instruments and measurement setup — what was measured and how, before what it showed | ↺ |
| 12 | Simulations, Results and Interpretation | 10 | **Ch 7, 34,139 → ~4,000.** The chapter that carries the claim. Organise by axis — compatibility / security / performance — not by date measured | ↺ |
| 13 | **Learning Strategies** | 2 | **Nothing in the report; everything in `STATE.md` and `00_METHOD.md`.** The richest section available — see §3 | ✎ |
| 14 | Future Work | 2 | Ch 8 §8.7's twelve items, priced and ordered — ready as written | ↺ |
| 15 | Conclusion | 2 | Ch 8 §8.2 against the falsifiers, §8.9 | ↺ |
| — | References | 3 | `09_references.md`, 28 sources, 28/28 resolving. **Ready** | — |
| A | Open-source repository and artifact index | 1 | Front matter's *The artifact* table | — |
| B | Full requirements register and §7.5 verdict table | 2 | Lift verbatim | — |
| C | Threat register — 18 threats, 7 residual risks, ratings | 3 | Lift verbatim | — |
| D | Full compatibility results, both corpora, both arms | 3 | Lift verbatim | — |
| E | Self-test suites and what each asserts | 1 | 19 suites | — |

**~64 pages.** Sections 4, 5, 6, 10 and 13 are the ones that do not exist today; they total **12
pages** and none of them requires a new measurement.

---

## 3. The four sections that need writing, and what each has to draw on

**§4 STEEPLE.** Both examples keep this to one page of seven short subsections. Material exists
but has never been framed this way: *Social* — 669,743 homes, presence and occupancy data, the
lock; *Technological* — no permission model in the dominant platform, 4,220 authors; *Economic* —
the median integration has 20 installs, hobbyist authors, no vendor to bear a rewrite cost;
*Environmental* — the whole system runs in 60% of a 4 GB Pi, 26 sandboxes; *Political* — smart-home
regulation and the EU Cyber Resilience Act's expectations of connected products; *Legal* — personal
data under GDPR reachable by any integration today; *Ethical* — the 2021 disclosures, and the
project's own choice to build a purpose-built adversary rather than weaponise the disclosed
versions (§7.13.6 already states this).

**§5 Engineering Standards.** Four are already load-bearing and cited: **ISO 31000** (Chapter 4
follows its clause structure section by section — a strong claim most capstones cannot make),
**STRIDE**, **OWASP Threat Dragon**, **RFC 1918**. Worth adding and justifying rather than
name-dropping: **ISO/IEC 27001** Annex A access control, **ISO/IEC 27400** (IoT security and
privacy guidelines), **OWASP Secure Coding Practices**. The Linux interfaces (seccomp BPF, cgroup
v2, namespaces) are kernel ABIs rather than standards and should be presented as such.

**§6 Logic Model Framework.** Maps unusually well. *Underlying assumptions* is the standout: this
project **registered eight predictions before measuring and six were wrong**, which is exactly what
that subsection asks for and almost nobody can answer honestly.

**§13 Learning Strategies.** The single best section available and it is entirely unwritten. Four
sub-heads, each with a real instance: targeted research (re-deriving the HA coupling from source);
practical experimentation (the paired baseline correcting three misattributions); independent
troubleshooting (**the mDNS finding** — a real integration could not construct an HTTP client
inside the sandbox at all, hidden behind eighteen passing suites); and managing breadth (the
consolidation this rewrite is). §8.4.2's four-mechanisms argument belongs here in plain language.

---

## 4. Figures — the real gap

**Two figures exist.** A 60-page report in this template carries 20–40. Missing, all drawable from
material already held:

- the sandbox's structure — namespaces, seccomp, cgroup, in one diagram
- the mediated request path, step by step, with the credential never crossing
- the egress broker's resolve-then-pin structure, and the DNS-rebinding refusal
- compatibility by profile — the 46 / 57 / 70 / 84% bars, both arms overlaid
- latency against sandbox count, with the durable-write correction marked
- PSS per sandbox and the 26-sandbox budget
- the audit chain — hash chain and MAC, and what each detects
- corpus composition — install-count head against the uniform draw

`figures/` already generates two figures from source so they cannot drift; the same discipline
should hold for the new ones. **This is the largest single block of new work in the rewrite and it
adds pages rather than cutting them.**

---

## 5. What must survive the compression

From `rewrite_consolidation_backlog.md`, and it is not negotiable: **the dated corrections and the
pre-registration are load-bearing.** §8.4.2's methodological result — six of eight predictions
wrong, none revised, every correction to a sentence and none to a measurement — is an argument
built entirely on that record. A clean rewrite that silently states current truth destroys the
report's most distinctive claim.

**The convention changes shape rather than disappearing:** each section states its current claim
first, and the history moves to a marked provenance note or to a single appendix. The dates and the
supersession must stay recoverable.

Second thing to preserve: **~51 pointers to unsubmitted files** (`01_PLAN.md`, `notes/*`,
`00_METHOD.md`). Each one is a dead end for an examiner. Either the file ships as an appendix or
the pointer is replaced by the content it points at.

---

## 6. Order of work

1. **§13 Learning Strategies and §6 Logic Model first.** They are new writing, they are short, and
   nothing else depends on them — so they can be finished while the compression order is still
   being argued about.
2. **§12 Results next**, because it carries the claim and its shape decides what §11 must set up.
3. **§9 Architecture last of the big three** — it is the deepest cut and the most reference-heavy.
4. **Figures throughout**, generated from source.
5. **§4 STEEPLE, §5 Standards, §10 Feasibility** are an afternoon each once the rest is settled.

**Younes reviews each section against its source before the next one starts.** This has to be
defensible aloud in a viva, and a condensed version he has not checked line by line is a different
object from the one he watched every number arrive in.
