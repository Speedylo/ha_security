# Chapter 5 — working notes

**Started:** 2026-08-24 · Not part of the report. Reasoning, rejected alternatives, and the
questions a viva will probe.

---

## Section plan

| § | Content | State |
|---|---|---|
| 5.1 | What the chapter must settle; the standard applied | ✅ drafted |
| 5.2 | The design problem restated — authority is positional; **§1.9 discharged here** | ✅ drafted |
| 5.3 | Where enforcement can live — L1–L4, three eliminated | ✅ drafted |
| 5.4 | Decision 1 — the platform (G2 #1) | ✅ drafted |
| 5.5 | The relocation problem — criteria K1–K7, candidates R1–R5, three eliminated | ✅ drafted |
| 5.6 | **Decision 2 — R1 vs R2** (G2 #2, §3.9 open question 2) | ✅ drafted — **R2 chosen; G2 divergence reported** |
| 5.7 | Decision 3 — the isolation primitive (G2 #3) | ✅ drafted — namespaces + seccomp + cgroup v2; **G2 confirmation**, primitives probed on the Pi |
| 5.8 | Decision 4 — implemented scope (G2 #4) | ✅ drafted — **DIVERGED**: sensors + egress×2 + one lock path |
| 5.9 | Who authors the manifest (§3.9 open question 1) | ✅ drafted — plural provenance, precedence, default-deny; **§3.9's open question 1 closed** |
| 5.10 | The manifest — schema and granularity (S5) | ✅ drafted — 8 declarable clauses, 4 ambient, no wildcards in `services.call` |
| 5.11 | The mediator interface and the channel (T02, K4) | ✅ drafted — identity is the socket; 30 µs measured on the Pi |
| 5.12 | Identity and the audit record (S7) | ✅ drafted — identity is a 3-part tuple; **all three open questions in `decision_audit_identity_and_trust_layer.md` answered** |
| 5.13 | Defence in depth — **§1.6 discharged here** (L1 returns as a layer, never as the boundary) | ✅ drafted — six layers named, **honestly counted as three**; §1.6 discharged in §5.13.6 |
| 5.14 | Figure 5.1, paired with Figure 4.1; threat-to-control traceability | ✅ drafted — figure drawn on Figure 4.1's canvas; the check found **four** rows where the design differs from what §4.10 assumed |
| 5.15 | What the design does not do; L2 as the platform's own better answer | ✅ drafted — limits sorted **by who could fix them**; L2 conceded as the better design; the supervisor named as the component nothing checks |

**Chapter 5 is drafted end to end. It has not yet been READ end to end** — fifteen sections written across two days, and the repetition/drift pass is owed.

## Measurement: what integrations actually talk to

Taken 2026-08-24 against Home Assistant 2026.8.3 (`759e465`), over all 1,482 integrations
shipped in `homeassistant/components/`. This was run to settle R1 vs R2 on evidence rather
than on intuition about what integrations "probably" use.

```bash
cd homeassistant/components
tot=$(ls -d */ | wc -l)
for pat in "homeassistant.helpers" "DataUpdateCoordinator" "async_add_entities" \
           "hass.data" "hass.states.async_set"; do
  n=$(grep -rlF "$pat" --include='*.py' . | sed 's|^\./||' | cut -d/ -f1 | sort -u | wc -l)
  echo "$pat -> $n / $tot"
done
```

| What the integration touches | Integrations | Share |
|---|---|---|
| `homeassistant.helpers` — the helper layer | 1,356 | **91%** |
| `async_add_entities` — helper-layer entity registration | 941 | 63% |
| `DataUpdateCoordinator` — helper-layer polling | 572 | 38% |
| `hass.data` — the raw shared dict | 279 | 18% |
| `hass.states.async_set` — writing state directly on `hass` | **2** | **0.1%** |

**This is the finding that decides §5.6.** Integrations do not, in the main, program against
the `hass` object at all. They program against Home Assistant's *helper layer* — its entity
base classes, its polling coordinator, its platform registration — and that layer is Home
Assistant's own code, which in any confined design is running inside the sandbox and expects
real platform internals beneath it. Two integrations in 1,482 set state directly on `hass`.

The consequence for R1 is direct: substituting the `hass` object substitutes the thing almost
nothing uses directly, and leaves the 91% case resting on how faithfully the helper layer's
expectations are emulated.

**~~Stated limit~~ — discharged 2026-08-24.** These were the *core* integrations. The same
measurement over the 144 most-installed community ones is **stronger**: 100% import the
helper layer, 83% use `async_add_entities`, 58% use `DataUpdateCoordinator`, and 6.9% set
state directly. The dependency R1 would have to emulate is universal in the target
population, not merely common in the one the argument was first made from. Now in §5.6.1 of
the report; full write-up in `ch5_evidence_api_surface.md`.

## The decision that blocks §5.6

§5.5 eliminated R3 (loader interposition — fails S1), R4 (the RFC — verified unshipped in
2026.8.3) and R5 (ask authors to port — fails C1). R1 and R2 remain, and they are different
designs rather than variants of one.

### R1 — Proxy object

The confined process runs the integration against a stand-in `hass` that presents the same
attribute surface and forwards each access to the mediator.

**For.** Conceptually clean: mediation is total by construction, because every attribute
access is already a message. Nothing of the platform is in the sandbox, so the per-sandbox
footprint is small (K6). The credential stays with the mediator without further argument (K3).

**Against, and this is the serious part.** `hass` is not the compatibility surface — it is
the *entry* to it. Real integrations are written against Home Assistant's helper layer:
`DataUpdateCoordinator`, `EntityComponent`, `entity_platform`, `config_entries`, the entity
base classes. That code is Home Assistant's own, it runs in the sandbox, and it expects a
real `hass` with real internals. Proxying the root object means emulating everything the
helper layer touches — which is a large and undocumented surface that moves every release.

Two further costs. Every attribute access becoming an IPC round trip is a latency problem
against N1, and generic attribute proxying with correct sync/async behaviour is genuinely
advanced Python — the kind that is hard to own and hard to defend line by line.

### R2 — A real, minimal Home Assistant inside the sandbox

The confined process runs a stripped Home Assistant. The integration imports the *real*
helper layer and receives a *real* `hass` object — but a local one, whose state machine, bus
and service registry are private to the sandbox and start empty. A single bridge component,
also inside the sandbox, forwards permitted effects to the mediator, which holds the
credential and applies them to the real platform.

**For.**

- **Compatibility stops being emulation.** The helper layer is the genuine article, so the
  large majority of what an integration touches is correct by construction rather than by
  reimplementation. This is the criterion (C1/N2) the whole contribution is measured on.
- **Default-deny becomes structural, not procedural.** The sandbox's state machine starts
  empty. An integration reading an undeclared entity does not get refused by a check — there
  is simply nothing there. Only what the manifest declares is mirrored in. S6 and S3 are
  satisfied by the shape of the design rather than by remembering to check.
- **The bespoke code shrinks and changes character.** What must be written is a bridge with a
  small explicit protocol, not a general-purpose emulation of a framework. That is ordinary
  code, readable and defensible.
- **C2 is untouched.** C2 forbids *modifying* core. Running an unmodified copy is not a
  modification.

**Against.**

- **Footprint.** A Home Assistant core per sandbox on a Pi-class device is the obvious risk to
  C4 and N1, and it is the question this design must answer with measurements rather than
  argument. How much can be stripped — no HTTP, no recorder, no frontend, no auth — is an
  empirical question, and it is the first thing Chapter 6 must establish.
- **Version coupling.** The sandbox's platform version should match the host's, adding an
  operational constraint the proxy design does not have.
- **A larger attack surface inside the sandbox** — but this is far weaker than it sounds. The
  integration is confined by an OS boundary; whatever it reaches inside its own sandbox is its
  own sandbox. The boundary is not made of the platform code sitting next to it.

### Recommendation: R2

Three reasons, in order of weight.

1. **It attacks the criterion the contribution is measured on.** §2.8's third contribution and
   N2 are about what fraction of *real, unmodified* integrations still work. R1 makes that
   number a function of how much of the helper layer was successfully emulated. R2 makes it a
   function of what the manifest denies — which is the thing actually being studied.
2. **Default-deny is structural under R2** and procedural under R1. Designs where the safe
   behaviour is the shape of the system beat designs where it is a check that must not be
   forgotten.
3. **The code is ownable.** A bridge with an explicit protocol can be explained under
   questioning; a generic attribute proxy with sync/async duality is exactly the code that is
   correct, clever, and indefensible in a viva.

**The honest risk:** R2's footprint may not fit C4, and if it does not, the fallback is R1
with a much smaller scope. That fallback should be identified now rather than discovered in
October — see the re-decision point below.

### Divergence from the first pass

The first pass built R1 — a compatibility shim of roughly 3,600 lines. If R2 is chosen, this
is a **G2 divergence and must be reported prominently as one**, per `01_PLAN.md` §6. It is
also the most interesting thing that could come out of the rebuild: an independent chain
reaching a different design, with a stated reason, is a stronger result than four
confirmations.

Note the evidence-rule position carefully. That the shim was hard and large is *private
knowledge* and cannot be an argument in the chapter. The chapter's argument against R1 must
stand on what §5.2 established about the helper layer — which it does, independently.

### Re-decision point — resolved on 2026-08-24, before the decision was taken

This was going to be deferred to Chapter 6. It was instead run first, on the actual Pi 5,
because a design chapter that picks R2 and *then* discovers it does not fit is the expensive
order. Full write-up and raw results in `experiments/r2_footprint/`.

| Question | Result |
|---|---|
| Minimal Home Assistant without `bootstrap`? | **Yes** |
| Ordinary helper-layer integration runs against it? | **Yes** — entry `LOADED`, `sensor.ticks` published |
| One sandbox on the Pi 5 | **176 MB**, ready in 6.1 s |
| Each additional sandbox | **136 MB** — about **17** in 60% of 4 GB |

**R2's premise holds and its footprint fits.** The threshold set in advance was "more than
roughly a fifth of the Pi's memory kills it"; a fifth is 809 MB and the answer is 136 MB.
The test was specified before it was run, and it passed on its own terms.

Three things the experiment produced that the argument did not have before:

1. **`bootstrap` cannot be used in the sandbox** — it imports `.components` at module level,
   frontend included. A minimal instance is built by constructing `HomeAssistant` directly.
   This is a §5.6 design detail, not an implementation one.
2. **The base `homeassistant` component costs 60 MB of the 176 MB.** Whether the sandbox
   needs it is the first thing Chapter 6 should test; dropping it roughly doubles capacity.
3. **17 sandboxes is enough but not generous.** A user with more integrations than that
   cannot have one sandbox each, which makes the *scope* decision (§5.8) load-bearing rather
   than cosmetic — and gives it a number to be decided against.

**What this does not settle.** One synthetic integration, measured idle, with no mediator
attached. It establishes the shape works and the cost is affordable; it is not the
compatibility evaluation and must not be reported as one.

## The pattern that keeps recurring, and is now worth naming in the report

Three independent observations, one shape. In each, the information needed for a security
decision **already exists** and is spent on something that is not one:

| Where | Information that exists | What it is actually used for |
|---|---|---|
| §2.4.1 Corno & Mannella | a plug-in's "scope" | prose in the documentation |
| `ch5_evidence_ha_coupling.md` §5 | `is_built_in` — which code is third-party | the wording of a log line |
| §5.9.1 | `iot_class` — whether it reaches the cloud (83% declare it) | a HomeKit discovery heuristic |

**The contribution is not inventing the declaration; it is making one load-bearing.** That
sentence now rests on three findings rather than on the single Corno & Mannella line
`STATE.md` has been carrying. Worth reusing in §5.1's framing, in Chapter 8, and in the
proposal — it is the most compact honest statement of the gap available.

Second-order point worth keeping: the 83% figure kills the feasibility objection to author
declaration before it is raised. Authors are not being asked for a new behaviour, they are
being asked for a slightly more precise version of one 83% of them already perform unprompted.

## Open conflict for Younes to settle at G3 — the cut order

`01_PLAN.md` §6 says that if G3 fires at the end of October, **the actuator PoC is cut
first**, then coverage-widening. §5.8.2 makes that ordering look wrong.

The cut list was written in August, before the scope was derived from Chapter 3's
verification column. Reading that column back gives:

- **S5's stated verification names a lock operation and its risk-asymmetric counterpart.**
  Cut the actuator and S5 cannot be verified at all — not verified weakly, not verified.
- **T05 is the register's joint-highest risk** (25, Critical, likelihood 5) and §4.10 treats
  it with F3/S5/S6. Cut the actuator and the highest-rated threat has no demonstrated control.
- Cutting **coverage-widening** instead costs a weaker N2 number — real, but N2 is a
  *reporting* requirement and a smaller sample still satisfies it honestly.

**Recommendation: swap the order — cut coverage-widening first, keep the actuator.** Not
applied to `01_PLAN.md`, because the plan is Younes's document and G3 is the decision point.
Flagged in §5.8.5 of the report as a known conflict rather than silently resolved.

The counter-argument worth having ready: the actuator is genuinely more work than widening
the integration set, so if the schedule pressure at G3 is severe, the honest move may be to
cut it *and state in Chapter 7 that S5 is unverified*, rather than to claim it. An unverified
requirement that says so is defensible; a verification criterion quietly rewritten to match
what was built is not.

## §5.13 — why it is a counting discipline and not a list of controls

Written 2026-08-25. The temptation in this section is to enumerate every control the chapter
has produced and let the length of the list carry the argument. That is the standard failure
of defence-in-depth writing, and this advisor audits for exactly it.

So the section leads with a **three-part test** for what counts as a layer — stated failure
mode, something behind it, independent failure cause — and then applies it to its own list
in §5.13.4, where **D2 (structural absence) and D4 (the kernel boundary) collapse into one**.
Both are produced by the supervisor constructing the sandbox and both are lost to the same
failures. Six named layers, three independent ones. Reporting the smaller number is the point
of the section, not a concession made inside it.

**The move that makes §5.13.5 necessary.** R1, R2, R3 and R5 pass through every layer
untouched, because each is *enforcement working as specified on a specification that was too
generous*. A section claiming depth without saying this would be claiming coverage. The
sentence to keep is that more layers of the same kind cannot help, since each would reach the
same verdict.

**D1 makes D0 cheaper** — a reviewer with a declaration has a specification to diff the code
against. This is the strongest form of §1.6's complementarity available and it was not in the
first pass's material at all. It runs from the impact side to the likelihood side, which is
the direction nobody expects.

**The deletion test for L1.** §5.13.3 lets in-process checking back as a diagnostic aid and
then fixes it in place: it appears in no threat treatment, no requirement depends on it, and
deleting it changes no security claim. That test is stated in the report on purpose, so
Chapter 6 cannot promote a convenience into a control by implementing it well.

**Rejected framing:** the "onion" / concentric-rings diagram. It implies every layer wraps
every asset, which is false here — D3 covers only what is routed through the mediator, and D0
covers only what someone read. Figure 5.1 in §5.14 shows where controls sit on the boundaries
instead, which is the honest picture and is already the chapter's figure.

**Fixed while writing this:** §5.3 said L1 "reappears in §5.12", written before the section
numbers settled. §5.12 became identity and the audit record. Corrected to §5.13.

## §5.14 — the traceability check earned its keep

Written 2026-08-25. The temptation was to write §5.14 as a coverage table where all eighteen
rows read "yes". Running it honestly turned up **four rows where the design is not what §4.10
assumed**, and three of the four generate work for later chapters. That is the argument for
doing this as a check rather than a summary.

| Row | What it is | Who owes what |
|---|---|---|
| **T02** | Met by a mechanism §4.10's own wording rules out — identity is the socket, so there is no per-request identity field | Nobody. Stated so a viva does not find it first |
| **T13** | **Half of it is placed nowhere in Ch. 5.** "Enforcement bounded to the declaration" is thorough; "declaration made visible" is not | **Chapter 6 owes a surface.** Bounded by §3.7, which excludes user comprehension — a surface, not evidence anyone reads it |
| **T14** | The design *overshot*: §4.10 says "filesystem isolation to declared resources", but §5.10.2 removed the filesystem clause entirely | **Chapter 7 must not repeat "to declared resources"** — it would misdescribe the artifact |
| **T16** | The control has an operational precondition Ch. 4 could not know: the Pi's `memory` cgroup controller is disabled at boot (§5.7.4) | **Chapter 7 must state it** rather than testing on a machine where it was quietly fixed |

**The reverse check is the part most traceability sections skip.** Running control-to-threat
instead of threat-to-control found three chapter elements answering no threat: manifest
provenance (answers §3.9 Q1 — legitimate), the identity tuple (defines a term S7 left
undefined — legitimate), and in-process checking from §5.13.3 (**answers nothing**). The third
is listed in §5.14.5 on purpose: it was declared as answering nothing where it was introduced,
and a traceability table that silently omitted it would be the place that concession quietly
disappeared.

**What the figure produced that the prose had not.** TB5 and TB6 are crossed by no flow at
all — nobody noticed until it was drawn — and in Figure 4.1 those same two locations carried
five flows. It is now §5.14.2 and it is the best illustration available of §5.13.4. Also
worth keeping: Figure 4.1's caption said the gap between TB1 and TB2 "is where a mediating
component would stand, and today nothing does". Figure 5.1 puts the mediator at exactly those
coordinates. Chapter 4 set the shot up a day before there was anything to put in it.

**Held to honestly:** TB2 is drawn UNCHANGED, not EXISTS, so the figure itself carries R3.
Labelling all six EXISTS was the easy edit and the dishonest one.

## §5.15 — the trap was repetition, and the way out was a different axis

Written 2026-08-25. Six places in the report already state a limit: §3.7, §4.11, §5.6.5,
§5.7.5, §5.10.9, §5.12.6. A closing "limitations" section that walked through them again would
be padding, and worse, it would present every limit in the same voice — which invites the
reading that the design has an unbounded number of holes.

**The way out was to sort them by a question none of the six answers: who could fix this?**
That gives three kinds — structural to confinement (nobody, within this approach), chosen
(this project, at a stated price), inherited (someone else, with a nameable fix). The
taxonomy does real work: it separates what Younes must defend from what he must merely report,
and it converts §4.11's R3 from a weakness into a specific upstream ask.

**Two things in §5.15 are new rather than re-sorted.**

1. **§5.15.4 — the supervisor is trusted absolutely and verified by nothing.** This falls out
   of §5.13.4 (D2 and D4 are one layer because both come from the supervisor) and it is not in
   any of the six places. The three bounds are honest ones: it is off the request path, it is
   unprivileged (§5.7.4 established that), and what a constructed sandbox can reach is testable
   at a moment in a way a running policy is not. The framing that makes it defensible rather
   than damaging: **every confinement design has a component that builds the boundary and is
   not inside one** — the VMM, the container runtime. Naming it first is the whole move.
2. **§5.15.5 — what would refute the design.** Five observations, each answerable by Ch. 6 or
   Ch. 7 rather than by argument. Two would be fatal (integrations largely fail; confinement
   requires modifying them). A design chapter that cannot say what would refute it has not
   made a claim, and this advisor audits methodology.

**§5.15.2 concedes that L2 is the better design, on every axis but one.** This was deliberate
and it is the opposite of the instinct to defend the chosen architecture. The concession is
safe because the one axis L3 wins — deployability — is the only one the population in §1.3
experiences, and because C2 makes it the axis this project is answerable for. The line worth
keeping: *the distinction is between a better design and an available one.*

The second-order point is the more valuable one and was not in the plan for this section:
**this project's most durable contribution to L2 may be the evidence L2 would need** — a
measured compatibility cost, a schema, and a threat model against a published baseline. Those
transfer to L2 unchanged. That is a much better Chapter 8 future-work paragraph than
"the platform should adopt this".

## Questions a viva will probe here

- *Why not just fix Home Assistant?* — L2 is the better answer for the platform project and
  §5.15 says so. C2 is the reason it is not this project's answer, and C2 is not an evasion:
  a control that requires the maintainers to adopt it is a proposal, not a deployable control.
- *Isn't running Home Assistant inside the sandbox circular?* — No. The sandbox's platform has
  no credential, no network, no real devices and an empty state machine. It is a compatibility
  surface, not a second hub.
- *What stops the integration talking to the mediator directly and lying about its identity?*
  — §5.11. Identity is a property of the channel, not a field in the message.
- *Isn't "defence in depth" just a longer list of the same control?* — §5.13.1's third test,
  and §5.13.4 answers it against this design's own list: two of the six collapse. The count
  reported is three independent layers plus a detective record.
- *Which layer stops R2 — the lock unlocked at 03:00?* — **None, and that is stated in
  §5.13.5.** Every layer works correctly and the door opens. Answering it needs contextual
  integrity (§2.3), which is a different mechanism, not another layer of this one.
- *Your threat model says "identity on every request" and your design has no such field —
  which is right?* — §5.14.4. The design is stronger than the control's wording; the wording
  anticipated the weaker construction. Do not defend this by rereading §4.10 charitably.
- *Show me a Chapter 4 control you failed to place.* — T13's visible half, and §5.14.4 says so
  before being asked. It is owed by Chapter 6 and bounded by §3.7.
- *Who verifies your supervisor?* — **Nothing does, and §5.15.4 says so before being asked.**
  Answer with the three bounds and the framing: every confinement design has a component that
  builds the boundary and is not inside one. Do not reach for the audit log — R4 already
  concedes it is not authoritative against whoever controls the machine.
- *Wouldn't it be better to just fix Home Assistant?* — **Yes, and §5.15.2 concedes it on every
  axis but deployability.** Do not defend L3 as superior; defend it as available.
- *What if the integration fetches code at runtime?* — Conceded in
  `decision_audit_identity_and_trust_layer.md`: the hash records what was loaded, not what
  executed. It belongs in the limitations section, stated rather than discovered.
