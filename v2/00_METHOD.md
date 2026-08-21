# Method and ground rules for the rebuild

**Started:** 2026-08-21 · **Author:** Younes · **Status:** working note, not a report chapter

This directory rebuilds the capstone from first principles. The work in `~/capstone/`
outside `v2/` is untouched and remains what it actually was: a **two-week feasibility
spike** that established the project is buildable. It is prior work to be cited, not a
draft to be tidied.

---

## 1. Why rebuild at all

The first pass grew outward from an implementation. Decisions were made when they were
forced, evidence was gathered when something needed settling, and the threat model was
written after the code it describes. Everything in it is *true*; the order in which it
became true is not an order that can be defended in a report or a viva.

A capstone is graded on the chain, not the endpoint. This pass builds the chain in the
order it has to hold: **problem → literature and gap → requirements → threat model →
architecture → implementation → evaluation**, where each step is earned by the one before
it.

## 2. The evidence rule

This is the discipline that makes the rebuild worth doing rather than a retelling.

Everything learned in the first pass is **private knowledge**: it tells me where the traps
are, so I do not spend three weeks rediscovering them. It is **not citable evidence** in
this pass until it has been re-derived here, properly, with a stated method.

Concretely — I already know all of the following, and none of it may appear in a report
chapter as established until re-earned:

| Known privately | What re-deriving it requires |
|---|---|
| Integrations cannot run outside HA's process | Read HA's bootstrap; show the coupling |
| eBPF cannot observe a gVisor-sandboxed process | Cite gVisor architecture + Falco's documented workaround |
| The API token is a confused-deputy hole no sandbox sees | Threat model, derived from the trust boundary |
| `/api/states` and `subscribe_events` are a firehose | Read the API surface; demonstrate the leak |
| Egress is required, not deniable | Empirical: what fraction of integrations call out |
| Import success is an upper bound on compatibility | Stated as a measurement limitation, with both numbers |
| The shim is ergonomics, not a security boundary | Falls out of the trust boundary, if drawn correctly |
| Manifests do not stop a determined author | Residual risk, with the browser-extension precedent |
| A local audit log is not authoritative against its writer | Residual risk, stated as an upstream limit |
| Isolation code couples to interpreter layout | Portability finding from running on a second machine |

**Test of good faith:** if a chapter's argument only works because I already knew the
answer, the chapter is wrong and must be rewritten to earn it or to drop the claim.

## 3. Decisions are re-openable

The first pass settled four things: Home Assistant as the platform, a compatibility shim
so unmodified integrations run, namespaces + seccomp as the isolation primitive, and
polling sensors as the implemented scope.

None of these is assumed here. Each must be reached by argument from evidence gathered in
this pass. If the evidence points elsewhere, I follow it and say so explicitly, with the
divergence flagged rather than buried — including the possibility that the first pass was
right for the wrong reason, which is its own finding.

A rebuild that re-derives all four identically is a *result*: independent confirmation.
A rebuild that could never have reached any other conclusion is theatre.

## 4. Layout

```
v2/report/    numbered chapters, academic register, real citations
v2/notes/     working notes: dead ends, rejected alternatives, decisions and their dates
v2/figures/   figures and the scripts that generate them
```

Rejected alternatives go in `notes/`, not the bin. They are what a viva probes, and
"we considered X and rejected it because Y" is the difference between a defensible scope
and an apparently arbitrary one.

## 5. What does *not* get rebuilt yet

The ~7,600 lines of working, tested code in `~/capstone/spike/`. It is cited as a
feasibility result — including its measured limits — and rebuilt deliberately once the new
design says what it should have been. Retyping code that already passes a 10/10
adversarial probe on two architectures would cost weeks and prove nothing.
