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
| 5.13 | Defence in depth — **§1.6 discharged here** (L1 returns as a layer, never as the boundary) | ⬅ **next** |
| 5.14 | Figure 5.1, paired with Figure 4.1; threat-to-control traceability | not started |
| 5.15 | What the design does not do; L2 as the platform's own better answer | not started |

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

## Questions a viva will probe here

- *Why not just fix Home Assistant?* — L2 is the better answer for the platform project and
  §5.15 says so. C2 is the reason it is not this project's answer, and C2 is not an evasion:
  a control that requires the maintainers to adopt it is a proposal, not a deployable control.
- *Isn't running Home Assistant inside the sandbox circular?* — No. The sandbox's platform has
  no credential, no network, no real devices and an empty state machine. It is a compatibility
  surface, not a second hub.
- *What stops the integration talking to the mediator directly and lying about its identity?*
  — §5.11. Identity is a property of the channel, not a field in the message.
- *What if the integration fetches code at runtime?* — Conceded in
  `decision_audit_identity_and_trust_layer.md`: the hash records what was loaded, not what
  executed. It belongs in the limitations section, stated rather than discovered.
