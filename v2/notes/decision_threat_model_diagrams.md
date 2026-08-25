# Decision — diagramming the threat model, and the ordering it has to respect

**Decided:** 2026-08-22 · Not part of the report. · **Affects:** Ch. 4 §4.6 (figure),
Ch. 5 (paired figure), `figures/`. · **Status:** decided; Figure 4.1 drawn 2026-08-24, Figure 5.1 drawn 2026-08-25.

## The decision

**OWASP Threat Dragon, for visualisation only.** It is a drawing tool in this project, not
a method. ISO 31000 supplies the process and STRIDE supplies the identification technique
(§4.1); nothing about that changes, and §4.1 is not amended.

**Two diagrams, not one:**

| Figure | Chapter | Shows |
|---|---|---|
| 4.1 | Ch. 4 §4.6 | Home Assistant **as it stands today** — one process holding the platform and every integration, with the six boundaries overlaid and four of them drawn as absent |
| 5.1 | Ch. 5 §5.14.1 | The same data-flow diagram with TB1, TB3, TB5 and TB6 instantiated |

**The delta between the two is the argument.** §4.9 already makes it in prose — four
Critical risks sharing one cause, integration and platform in one process with no boundary
between them — and that claim is inherently spatial. §4.6's "four of six boundaries do not
currently exist" is a sentence carrying weight a picture carries better.

## The trap this avoids

A DFD wants processes, stores and flows — that is, a design. The path of least resistance
when drawing one is to draw the mediating component, the sandbox, the broker. **At that
moment Chapter 4 contains Chapter 5**, and the ordering discipline that is Ch. 4's central
methodological claim (§4.1: controls answer threats enumerated independently of them)
quietly collapses. TB1 is recorded as *Absent*; a figure that draws it as a box has already
answered Ch. 5's question.

The rule is therefore about **what is drawn**, not about what the report claims the tool
did: Ch. 4 draws today, Ch. 5 draws the fix. Splitting it this way costs nothing and
reinforces the chapter order rather than eroding it.

## Why this tool

Standard DFD notation — process, data store, external entity, trust boundary — that an
auditor reads without a legend. That is the whole of the benefit for a visualisation-only
use, and it is a better reason than any of the tool's threat-generation features.

## Bounds on the figures

- **No threats on the diagram.** Boundaries, assets and flows only. The T-numbers stay in
  the §4.8 tables; a DFD carrying eighteen annotations is a diagram nobody reads.
- **No mention in §4.1.** A caption — "Figure 4.1 — drawn with OWASP Threat Dragon" — is
  the correct weight. Naming a drawing tool in the methodology section would claim more
  than is being done, and this advisor knows what Threat Dragon is.
- **Commit the model, export the image.** The `.json` model file is the source, matching
  the norm set by `figures/ecosystem_scale.py`, where every number in Ch. 1 is regenerable.

## Considered and not taken

**Model-as-code (`pytm`, `threagile`).** Purer fit with the reproducibility norm — the
diagram generates from a text file that diffs cleanly. More setup, and for two or three
diagrams it does not pay for itself. Revisit only if the figure count grows.

**The per-element threat generator, as a completeness cross-check.** §4.13 concedes that
"a threat model enumerates what its author thought of". Running Threat Dragon's generator
*after* the hand-derived enumeration and reporting what it surfaced — including nothing —
would partially answer that concession and would be a gradeable methodological result.
Deliberately **not** taken now, because it changes the chapter from visualisation to method
and would need §4.1 rewritten. It stays available at no cost: the model will be loaded in
the tool anyway.

## The broader gap this exposes

`figures/` currently holds one data script and **no diagrams**, across four chapters
covering a loading architecture, an authority table and six trust boundaries. For a
capstone graded partly on Clarity, that is a real weakness independent of which tool is
chosen. Ch. 1 §1.2 (how an integration is loaded) is the other obvious candidate — and it
carries the same discipline: draw what exists, not the fix.
