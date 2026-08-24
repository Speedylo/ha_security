# Chapter 5 — Architecture and design rationale

## 5.1 What this chapter must settle

Chapters 3 and 4 constrain this design tightly enough that most of it is determined. Chapter
3 fixed nineteen requirements and four constraints; Chapter 4 enumerated eighteen threats
against a system that has none of them, found four Critical risks, and observed that those
four share a single cause. This chapter converts that into an architecture, and it is
answerable for five things:

1. **The two questions Chapter 3 deliberately left open** (§3.9): how an unmodified
   integration can execute outside the process it was written to run inside, and who authors
   the manifest given that C3 forbids assuming the author is honest.
2. **The four decisions this rebuild re-opened.** The first pass settled a platform, a
   compatibility strategy, an isolation primitive and an implemented scope. None is assumed
   here. Each must be reached by argument from evidence gathered in this pass, and where the
   argument arrives somewhere different, the divergence is followed and reported rather than
   suppressed.
3. **The manifest**, promoted from the strawman of §1.10 to a specified schema with a stated
   granularity, since S5 constrains granularity without fixing it.
4. **Two arguments promised earlier and not yet discharged**: the defence-in-depth framing of
   §1.6, and §1.9's claim that relocation without scoping does not constrain authority. §1.9
   has now been made twice; this chapter must *discharge* it, not repeat it.
5. **Traceability in the other direction.** Chapter 4 mapped each threat to a control and a
   requirement. This chapter must show where each of those controls actually lives, and
   §5.14 is where that is checked rather than asserted.

**The standard being applied.** A design chapter can be written two ways: as a description of
what was built, or as a record of what was chosen and why. The second is what is graded, and
it is also the only one that survives a viva, because a viva probes the alternatives. Options
that were considered and rejected are therefore recorded in `notes/`, and the ones that were
close are recorded in this chapter.

## 5.2 The design problem, restated precisely

Chapter 1 established that an integration can reach the assets of Table 1.2. Chapter 4
established that the four Critical risks share one cause. Neither states the mechanism at the
level of precision a design needs, so this section does.

**Home Assistant loads an integration with Python's ordinary import machinery.** The whole of
the coupling is one line of `homeassistant/loader.py`:

```python
cache[domain] = cast(ComponentProtocol, importlib.import_module(self.pkg_path))
```

The platform's own comment above it describes the function as "mostly a thin wrapper around
importlib.import_module with a dict cache". Because importing a Python module *executes* it,
the integration's code runs inside the platform's process, in the same interpreter and the
same address space, from the moment it is loaded. Two call sites then hand that code the root
object of the running system: `setup.py` passes `hass` to `async_setup`, and
`config_entries.py` passes both `hass` and the configuration entry — the object holding that
integration's stored credentials — to `async_setup_entry`.

From `hass`, the following are reachable by ordinary attribute access: the shared data
dictionary holding every integration's runtime state, the event bus, the service registry,
the state machine, the configuration directory path, the authentication manager, the HTTP
server, every integration's stored configuration, and the event loop itself. A weather
integration needs approximately one of these. It is handed all nine.

**The decisive property is that none of this is conferred by a grant that could be withheld.**
Two facts establish it. First, the root object is ambient rather than disclosed: Home
Assistant stores it in module-level state and publishes `async_get_hass()`, whose documented
purpose is to supply it to code that was not passed it. Withholding the argument would
withhold nothing. Second, and more fundamentally, code sharing an interpreter can enumerate
the objects that interpreter holds — which is the technique Corno and Mannella demonstrate to
reach another integration's live object and read and modify its private state (§2.4.1).

An integration's authority is therefore **positional**: it is a consequence of where the code
runs, not of anything handed to it. This is the single most important sentence in the
chapter, and three consequences follow immediately.

**First, no in-process control can be sound.** A permission layer living in the same
interpreter as the code it constrains is an object in that interpreter's heap, reachable by
the same technique. This is S1, and it is why S1 was called the highest-leverage requirement
in §3.8.

**Second, relocation alone changes nothing — the §1.9 discharge.** §1.9 examined the *Remote
Integration Execution* proposal, which would allow integrations to run on separate machines,
and observed that its motivation is principally reliability. The precise reason relocation is
insufficient can now be stated. Moving the code changes its position, and position is exactly
what conferred its authority — so unless the *new* position confers less, nothing has been
gained. An integration relocated to another machine must still read and write platform state
to be useful, which means it must hold a credential that Home Assistant honours. If that
credential is unscoped, the relocated integration has the same authority it had before,
exercised over a socket rather than a pointer. Relocation without scoping relocates authority
rather than reducing it. This is why S2 requires that the confined code hold no such
credential, and it is why this project is complementary to that proposal rather than
competing with it: the proposal supplies a mechanism for moving code, and what is missing
from it is the scoping.

**Third, the design target is now expressible in one sentence.** The confined integration must
be somewhere that confers no authority, while still being able to obtain — by request, subject
to a decision — exactly the authority its manifest declares. Everything remaining in this
chapter is a consequence of trying to build that while satisfying C1 and C2.

> **On the evidence for this section.** The coupling above was re-derived for this pass by
> reading Home Assistant 2026.8.3 (commit `759e465`) directly, and the method, the full
> attribute table and the line references are in `notes/ch5_evidence_ha_coupling.md`. The
> first pass had reached the same conclusion; under the evidence rule (`00_METHOD.md` §2)
> that was private knowledge and not usable here until re-derived.

## 5.3 Where enforcement can live

Given a design target, the first question is architectural rather than technical: at what
point in the system does a decision get made? Four locations are available, and three are
eliminated by requirements already fixed.

| Location | What it would mean | Verdict |
|---|---|---|
| **L1 — Inside the integration** | A wrapper, decorator or import hook in the integration's own process rejecting disallowed calls | **Eliminated by S1.** In the integration's own address space, therefore reachable by the demonstrated technique. Also fails C3: an author who does not call the wrapper is not constrained by it |
| **L2 — Inside Home Assistant core** | The platform checks a manifest before honouring a call | **Eliminated by C2.** Requires modifying core. Would be the *right* answer for the platform project to adopt, and §5.15 returns to this — but it is a proposal, not a deployable control |
| **L3 — In a separate process on the same host** | The integration runs confined; a mediator in another process holds the credential and decides | **Available** |
| **L4 — In a separate host** | As L3, across a network | **Available, and strictly weaker on C4** — it requires a second machine, which §1.1's deployment does not have |

**L1 deserves more than a table row**, because it is the design most people propose first and
because a variant of it is genuinely useful later. Python offers real interception machinery:
import hooks, audit hooks, module-level shadowing. All of it executes in the interpreter it
is trying to police. Against a buggy integration it works; against a hostile one it is an
object in a heap the adversary can enumerate. This distinction — effective against accident,
void against intent — is precisely the likelihood/impact split of §1.6, and it is why L1
reappears in §5.12 as a defence-in-depth layer and never as the boundary.

**L3 is therefore the architecture**, and the choice is forced rather than preferred: S1
requires enforcement outside the integration's execution context, C2 forbids putting it in
core, and C4 makes a second machine unavailable in the general case. The remaining design
space is *how* to build L3, not whether.

This yields the shape the rest of the chapter fills in:

- a **confined execution context** the integration runs in, conferring no ambient authority;
- a **mediator** in a separate process, holding the platform credential (S2), deciding each
  request against the manifest (F3, S6), and recording the decision (S7);
- a **channel** between them carrying per-integration identity (T02);
- a **manifest** the decisions are made against (F3, S5).

Each is settled below, in the order in which the evidence forces them.

## 5.4 Decision 1 — the platform

The first of the four re-opened decisions is which platform this work targets. It is recorded
here for completeness and because Gate G2 requires all four to be revisited, but it is settled
with less argument than the others, for a reason worth stating plainly: **this decision was
made by Chapters 1 and 2, on evidence, and re-litigating it here would be theatre.**

The evidence that made it is: an ecosystem of 4,220 community integrations installed on 56.6%
of reporting installations (§1.3); a documented incident class in this specific ecosystem, the
2021 disclosures affecting eight integrations (§1.5); a platform whose own security
documentation places third-party integration behaviour outside its security programme (§1.8);
a published threat model of this exact platform to evaluate against (§2.4.1); and a systematic
review naming a Home Assistant proof-of-concept as future work (§2.4.3). No comparable
combination of scale, documented harm, platform-acknowledged gap and published evaluation
baseline was found for any other platform during the Chapter 2 search.

**Divergence from the first pass: none.** The first pass chose Home Assistant, and this pass
re-derives it. Per `01_PLAN.md` §6, re-reaching a decision through an independent chain is
reported as confirmation rather than passed over in silence — but it is also weak
confirmation here, since Chapters 1 and 2 were written about this platform and a chain that
begins with a platform will tend to end with it. The honest statement is that the platform
choice is **not contested by this work and not independently re-tested by it**.

## 5.5 The relocation problem

This is the hardest engineering question in the project, deferred from §3.9 on purpose so
that Chapter 4 could constrain the answer before it was attempted.

**The problem.** C1 requires that integrations run unmodified — no change to their source,
counted mechanically. §5.2 established that an integration's code says `hass.states.async_set(...)`,
`hass.data[DOMAIN]`, `hass.bus.async_listen(...)`, `hass.config.path(...)`, and expects real
answers. §5.3 established that the code must run somewhere that confers no authority.

These two are in direct tension, and the tension is the whole difficulty: **the integration
must find, at the end of every one of those attribute paths, something that behaves as the
real object did — while the real object is in another process and must stay there.**

**The criteria any candidate must meet**, drawn from requirements already fixed:

| # | Criterion | Source |
|---|---|---|
| K1 | Integration source is unchanged | C1 |
| K2 | Home Assistant core is unchanged | C2 |
| K3 | The confined side holds no credential Home Assistant honours | S2 |
| K4 | Every mediated request carries the integration's identity | T02, S7 |
| K5 | Reads and subscriptions are mediated, not only writes | S3 |
| K6 | Runs within the resources of a single-board computer | C4, N1 |
| K7 | Undeclared operations fail closed | S6, N3 |

**The candidates.** Four are viable enough to be worth comparing, and a fifth is recorded
because it will be asked about.

| ID | Approach | Sketch |
|---|---|---|
| **R1** | **Proxy object** | The confined process runs the integration against a stand-in that presents the same attribute surface and forwards each access to the mediator over IPC |
| **R2** | **Minimal platform in the sandbox** | A cut-down real Home Assistant runs inside the confined process, so the integration talks to a genuine local object; only outward effects — state writes, service calls, egress — are mediated |
| **R3** | **Loader interposition** | A custom component installs an import hook so the integration is loaded with a substituted `hass`, staying inside the platform process |
| **R4** | **Wait for the RFC** | Build the scoping layer on *Remote Integration Execution*, and let the platform solve relocation |
| **R5** | **Ask authors to port** | Define an out-of-process integration API and have authors adopt it |

**R5 is eliminated by C1**, and the elimination is the finding of §2.2: Chrome could require
migration because it was a new platform with no installed base; a mechanism for 4,220 existing
volunteer-written integrations cannot. It is recorded because "why not just define a better
API?" is the most common first question, and the answer is that the entire problem is the
existing corpus.

**R3 is eliminated by S1.** Substituting `hass` inside the platform's own process leaves the
integration in the interpreter that holds everything, where the substitution is an object it
can route around — including by calling `async_get_hass()`, which returns the real one. R3 is
a *compatibility* technique that answers nothing about *authority*, and mistaking one for the
other is precisely the error §1.9 warns about.

**R4 is eliminated as a dependency, and retained as a relationship.** The proposal was
examined for this pass against Home Assistant 2026.8.3: it is not implemented — no remote
execution machinery exists in the release, and the RFC remains an open community discussion.
A capstone cannot depend on an unshipped proposal. The relationship §1.9 identified stands
unchanged: if it ships, it supplies relocation and this work supplies the scoping that §5.2
showed relocation does not provide by itself.

**That leaves R1 and R2, and they are genuinely different designs** rather than variants. The
comparison is the substance of the decision, and it is taken up in §5.6.

---

*Chapter in progress. §5.6 (the R1/R2 decision) onward is next; the section plan is in
`notes/ch5_working_notes.md`.*
