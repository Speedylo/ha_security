# Figure 4.1 — drawing specification

**Written:** 2026-08-24 · **Working note, not a report chapter.**
**Implements:** `decision_threat_model_diagrams.md` (OWASP Threat Dragon, visualisation
only; Ch. 4 draws **today**, Ch. 5 draws the fix).
**For:** `report/04_threat_model.md` §4.6. · **Status:** **drawn.**

> **Built, 2026-08-24.** `figures/fig_4_1_current_state.py` generates both the Threat Dragon
> model (`.json`) and the rendered figure (`.svg`, plus `.png` when cairosvg is present)
> from one description, so the two cannot drift apart. Open the `.json` in Threat Dragon to
> adjust it by hand; re-run the script to regenerate from source. §8 below records what
> changed between this specification and the figure as built.

Everything below is derived from §4.2 (scope), §4.4 (assets), §4.5 (actors) and §4.6
(boundaries) as they already stand. **No element here is new.** If drawing it makes you
want to add something not in those tables, that is a signal the chapter is incomplete —
fix the chapter first, not the figure.

---

## 1. The one rule this figure exists to respect

**Draw the system as it is today. Do not draw the fix.**

The path of least resistance when drawing a data-flow diagram is to draw the mediating
component, because a DFD wants tidy separated boxes. The moment you draw that box, Chapter
4 contains Chapter 5, and the ordering discipline that is this chapter's central
methodological claim (§4.1 — controls answer threats enumerated independently of them)
quietly collapses.

TB1 is recorded in §4.6 as **Absent**. On this figure it is a boundary that is *labelled
and marked absent*, never a box with something inside it.

**The second trap, specific to this system.** Integrations are drawn as separate shapes
because they are separate *code*. They are not separate *processes* — §1.2 and the source
walk in `ch5_evidence_ha_coupling.md` establish that they share one OS process and one
Python interpreter. A reader who takes the shapes for isolation has read the figure exactly
backwards. Two devices defeat this, and both are required:

1. Every in-process element sits inside one heavy container labelled as a single process.
2. The container's label says so in words, and the caption repeats it.

---

## 2. Elements

### 2.1 External entities (Threat Dragon: *Actor*)

| Label on the figure | Ties to | Note for you while drawing |
|---|---|---|
| **Home occupant / user** | AC5 | The asset owner. Interacts through the web UI |
| **Integration author + HACS channel** | AC1, AC2, §1.4 | Draw as **one** entity. §4.6 pairs them in TB4 because the channel verifies structure, not behaviour — separating them implies a check that does not happen |
| **External network endpoints** | §1.2 Table 1.2, A8 | Vendor clouds and arbitrary hosts. Deliberately vague: today there is no restriction on which, and the vagueness *is* the finding |
| **Home devices and LAN** | A1, A4, A8 | Locks, cameras, the rest of the network |

### 2.2 Processes (Threat Dragon: *Process*)

| Label on the figure | Ties to | Note |
|---|---|---|
| **Home Assistant core** — bus, states, services, config_entries, auth, http | §1.2 | One shape. Resist splitting into subsystems; the subsystem list belongs in the label, not in five boxes |
| **Integration A (third-party)** | AC1–AC4 | |
| **Integration B (third-party)** | AC4 | The second one exists **only** so TB6 has two endpoints. Without it the figure cannot show integration-to-integration reach |

All three sit inside the container in §2.4.

### 2.3 Data stores (Threat Dragon: *Store*)

| Label on the figure | Ties to | Note |
|---|---|---|
| **`secrets.yaml` + config directory** | A3 | On disk. Reachable by any integration via `hass.config.path()` |
| **Config entry store** (`.storage/`) — every integration's saved credentials | A3, A6 | On disk. Reachable via `hass.config_entries` |
| **In-memory shared state** — `hass.data`, state machine | A2, A6 | Label it *in-memory* explicitly, or a reader assumes a database. This is where "every integration's working data in one dict" lives |

**Deliberately not drawn — and why, so the omissions are choices rather than gaps:**

- **The audit record (A7).** It does not exist today. Drawing it would draw the fix.
- **PyPI / runtime `pip` install** (`requirements.py:190`). Real, and relevant to
  supply-chain threats, but §4.6 defines no boundary for it. Adding an element the boundary
  table does not carry would put the figure ahead of the chapter. If you want it in, add
  the boundary to §4.6 first — that is a legitimate change, but it is a *chapter* change.
- **The recorder database.** Holds history, so it touches A2, but nothing in the six
  boundaries turns on it. Omit for legibility.

### 2.4 The container, which is the whole point

One large boundary box enclosing **HA core, Integration A, Integration B, and the in-memory
store**, labelled:

> **Home Assistant — one OS process, one Python interpreter.
> No boundary exists between the elements inside this box.**

This is the most important label on the figure. If a reader remembers one thing, it is this.

---

## 3. Trust boundaries, and how to mark absence

Threat Dragon draws every trust boundary the same way — a dashed curve. So "exists" versus
"absent" **cannot** be carried by the shape, and colour is not reliably portable between
Threat Dragon versions and an exported PNG. Carry it in the **name**, which always exports:

- Existing: `TB2 · EXISTS — unscoped API surface`
- Absent: `TB1 · ABSENT — required by S1`

**Words, not ✓ and ✗.** The specification originally called for the tick and cross. The
first render proved that wrong: both came out as tofu boxes in a font that lacked them, and
a symbol that may not render is worse than no symbol. `EXISTS` and `ABSENT` survive any
font and any greyscale printout. Colour is carried too, but only as reinforcement.

| ID | Where to draw it | Name | Status |
|---|---|---|---|
| TB1 | Between HA core and the integrations, *inside* the container | `TB1 · ABSENT — required by S1` | Absent |
| TB2 | Hugging HA core's API surface, inside the same corridor | `TB2 · EXISTS — unscoped API surface` | Exists |
| TB3 | Between the container and **External network endpoints** | `TB3 · ABSENT — required by F2/S4` | Absent |
| TB4 | Between **Integration author + HACS channel** and the machine | `TB4 · EXISTS — structure, not behaviour` | Exists |
| TB5 | Between the container and the host OS / filesystem stores | `TB5 · ABSENT — required by S8` | Absent |
| TB6 | Between Integration A and Integration B, *inside* the container | `TB6 · ABSENT — demonstrated crossable` | Absent |

**Four absent, two present.** That ratio is the argument the figure exists to make, and it
should be visible from across a room without reading a single flow label. The generator
asserts it before writing, so a later edit cannot silently break it.

**TB1 and TB2 are drawn as two near-parallel curves in one corridor**, with an empty gap
between them. That gap is where a mediating component would stand, and today nothing does —
which is what makes it honest to draw the two boundaries as coinciding at a single
interface. Chapter 5's paired figure fills the gap; that is the delta.

---

## 4. Flows

Direction matters — an arrow claims something. Each row states which boundary it crosses so
you can check, while drawing, that no flow crosses a boundary the chapter does not list.

| # | From → To | Label | Crosses |
|---|---|---|---|
| F1 | Author + HACS → Config directory | installs / updates integration source | TB4 |
| F2 | HA core → Integration A | `import_module`, then `async_setup(hass, …)` — **passes the `hass` reference** | TB1 (absent) |
| F3 | Integration A → HA core | service calls, state writes, event subscription | TB1 (absent), TB2 |
| F4 | Integration A → In-memory shared state | direct read/write of `hass.data`, all domains | TB1 (absent) |
| F4b | Integration B → In-memory shared state | the same shared dict, from another integration | TB1 (absent) |
| F5 | Integration A → Config entry store | reads any integration's stored credentials | TB1 (absent) |
| F6 | Integration A → `secrets.yaml` / config dir | arbitrary file read via `hass.config.path()` | TB5 (absent) |
| F7 | Integration A → External network endpoints | unrestricted outbound | TB3 (absent) |
| F8 | Integration A ↔ Integration B | direct object access (in-process) | TB6 (absent) |
| F9 | Integration A → Home devices and LAN | local network access | TB3, TB5 (both absent) |
| F10 | User ↔ HA core | web UI | none |

**F2 is the flow to make visually prominent** — thicker, or placed centrally. It is the
single line that explains why the other nine are possible, and it is the flow Chapter 5's
paired figure will interrupt.

**Do not draw** a flow from Integration A to the host OS *labelled as an exploit*, or any
flow whose label names a threat. Threats stay in the §4.8 tables (`decision_threat_model_
diagrams.md`: no threats on the diagram). F6 and F9 already carry the reach; naming what an
attacker does with it is the tables' job.

---

## 5. Rough layout

Not prescriptive — Threat Dragon's canvas will push things around. It fixes the two
relationships that matter: everything in-process inside one box, and the four absent
boundaries on the box's edges and interior.

```
   ┌──────────────────────┐                      ┌───────────────────────┐
   │ Integration author   │                      │ External network      │
   │ + HACS channel       │                      │ endpoints             │
   └──────────┬───────────┘                      └───────────▲───────────┘
              │ F1                                           │ F7
       TB4 ✓ ─┼─ verifies structure, not behaviour     TB3 ✗ ─┼─ ABSENT
              │                                               │
  ╔═══════════▼═══════════════════════════════════════════════╪═══════════╗
  ║  HOME ASSISTANT — ONE OS PROCESS, ONE PYTHON INTERPRETER   │           ║
  ║  No boundary exists between the elements inside this box   │           ║
  ║                                                            │           ║
  ║   ┌───────────────┐   TB1 ✗ ABSENT   ┌──────────────────┐  │           ║
  ║   │ HA core       │◄───────F2/F3────►│ Integration A    │──┘           ║
  ║   │ bus, states,  │                  │ (third-party)    │              ║
  ║   │ services,     │                  └────┬──────┬──────┘              ║
  ║   │ config_entries│                       │ F8   │ F4                  ║
  ║   │ auth, http    │                  TB6 ✗│ABSENT│                     ║
  ║   └───┬───────────┘                  ┌────▼─────┐│   ┌───────────────┐ ║
  ║       │ TB2 ✓ exists — unscoped      │Integr. B ││   │ In-memory     │ ║
  ║       │                              └──────────┘└──►│ shared state  │ ║
  ╚═══════╪═══════════════════════════════╪══════════════│ hass.data (A2,│ ║
          │ F10                           │ F5, F6, F9   │ A6)           │ ║
          ▼                        TB5 ✗ ─┼─ ABSENT      └───────────────┘ ║
   ┌──────────────┐                       │              ╚════════════════╝
   │ Home occupant│      ┌────────────────▼──────┐  ┌──────────────────┐
   │ / user       │      │ secrets.yaml + config │  │ Config entry     │
   └──────────────┘      │ directory (A3)        │  │ store (A3, A6)   │
                         └───────────────────────┘  └──────────────────┘
                                    ┌───────────────────┐
                                    │ Home devices, LAN │
                                    │ (A1, A4, A8)      │
                                    └───────────────────┘
```

---

## 6. Caption

To sit under the figure. Names the tool at the weight `decision_threat_model_diagrams.md`
settled on — a caption, not a methodology claim, and §4.1 stays untouched.

> **Figure 4.1 — Home Assistant as it stands today, with the six trust boundaries of
> §4.6 overlaid.** Integrations are drawn as distinct elements because they are distinct
> code; they are not distinct processes. Everything within the heavy border shares one
> operating-system process and one Python interpreter, so the boundaries marked ✗ have no
> enforcement point anywhere in the running system. Four of six do not exist. Assets carry
> the identifiers of §4.4; threats are not shown and remain in the tables of §4.8. Drawn
> with OWASP Threat Dragon.

---

## 7. The §4.6 paragraph

Insert **after** the boundary table and **before** the existing closing sentence "Four of
six boundaries do not currently exist…" — which then reads as the figure's conclusion
rather than as a claim the reader must take on trust.

> These six boundaries are overlaid on the system as it exists today in Figure 4.1. The
> figure asserts nothing that the table above does not already state; its purpose is that
> the *distribution* of the absences is spatial, and a table flattens it. Three of the four
> missing boundaries — TB1, TB5 and TB6 — are missing for one reason, visible in the figure
> as a single enclosure: the integration and the platform occupy the same process, so there
> is no location at which any of the three could be enforced. This is why §4.9 finds four
> Critical risks sharing a single cause, and why no combination of controls placed *inside*
> that enclosure can address them.

**Why it is worded that way.** It claims only what the table already carries (so the figure
cannot be accused of smuggling in an argument), states the one thing a picture genuinely
adds over a table, and lands on the §4.9 finding the chapter has to reach anyway. It does
**not** hint at the remedy — "no control inside the enclosure helps" is a statement about
today, not a proposal, and Chapter 5 remains free to be surprising.

---

## 8. As built, and how to change it

**Regenerate:** `python3 figures/fig_4_1_current_state.py`. It writes the Threat Dragon
model, the SVG, and — only if `cairosvg` happens to be installed — a PNG. The SVG is the
figure of record; the PNG is a convenience for pasting into a word processor.

**Edit by hand instead:** open `fig_4_1_current_state.json` in Threat Dragon (the web
version at `owasp-threat-dragon.github.io` or the desktop app; no account needed for a
local model). Anything moved there is lost on the next run of the script, so if a change is
worth keeping, put it in the script.

**Three departures from this specification, made while building and worth recording:**

1. **Symbols became words** (§3). The ✓/✗ convention failed its first render.
2. **F4 gained a twin, F4b.** The specification had F4 crossing TB6, which cannot be drawn
   honestly: the shared store sits on Integration A's side of any line between A and B.
   Drawing *both* integrations connected to the same store says "shared" better than a
   boundary crossing would, and it is also ordinary DFD practice.
3. **F10 crosses nothing.** The specification had it crossing TB2. It does not: none of
   §4.6's six boundaries is "user ↔ platform". The user is AC5 — a source of risk through
   action, not an external attacker — and inventing a boundary for that flow would have put
   the figure ahead of the chapter.
4. **The Integration A ↔ B band was rebuilt** after review, 2026-08-24. Four flows left
   Integration A by the same bottom port and fanned out through a 73-pixel gap that also
   carried TB6 and two labels. The band is now 113 pixels; F3 returns to the platform by
   the left port as a bowed second leg of the F2/F3 pair; F5 and F6 diverge early, right
   and left; and **F8 is the only flow that crosses TB6**, which is correct — it is the
   only integration-to-integration flow. TB6's label sits at the line's right end so it
   never hides F8's arrow. Nothing about the figure's content changed, only its legibility.

**Checks before committing a change** — each catches a specific way this figure could
mislead:

- Four ABSENT, two EXISTS. The script asserts this; do not remove the assertion.
- No element on the canvas that §4.4/§4.5/§4.6 does not name.
- No box representing a mediator, broker, sandbox or proxy anywhere.
- No flow label naming a threat or an attack.
- The container's label says *one process, one interpreter* in words.
- A stranger shown only the figure can say which four boundaries are missing.

---

## 9. Afterwards

Chapter 5 draws the **same diagram** with TB1, TB3, TB5 and TB6 instantiated, and the delta
between the two is the argument (`decision_threat_model_diagrams.md`). Two consequences for
how you draw this one:

- Keep the element positions. If Figure 5.x can be recognised as Figure 4.1 with boundaries
  added, the comparison does the work by itself. Redrawn from scratch, it does not.
- Work from a **copy** of the JSON when the time comes, so Figure 4.1 stays exactly as it
  was.

One option stays open at zero cost, recorded in `decision_threat_model_diagrams.md` and not
taken now: running Threat Dragon's per-element threat generator *after* the hand-derived
enumeration, and reporting what it surfaced — including nothing — as a partial answer to
§4.13's concession that a threat model enumerates only what its author thought of. That
changes the chapter from visualisation to method and would need §4.1 rewritten, so it is a
deliberate later decision, not a thing to do while the model happens to be open.
