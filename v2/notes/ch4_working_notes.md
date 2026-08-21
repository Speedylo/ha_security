# Chapter 4 — working notes

**Written:** 2026-08-21. Not part of the report.

## The best find in the chapter

Corno & Mannella define a plug-in's **scope** as "the set of variables, files, or resources
that the plug-in can legitimately access", where legitimacy is established because "the
plug-in documentation has to include its possible use". Every one of their eleven threats is
defined as acting *outside its scope*.

So the only published threat model for this problem **presupposes a notion of scope that has
no machine-readable form and no enforcement**. It lives in prose. This project's manifest is
precisely that notion made explicit and enforced.

This is the single most useful sentence available for the viva and for the proposal. It
converts "my work is adjacent to theirs" into "their model requires the thing my work
builds". Do not bury it — §4.14 states it, and Chapter 5's opening should reuse it.

## The ordering discipline paid off visibly

Chapter 3 had no resource-exhaustion requirement, because nothing in Chapters 1–2 justified
one and the traceability rule forbade inventing it. I flagged in `ch3_working_notes.md` that
if the threat model raised availability, a requirement should appear *there*.

It did (T16), and **S9 is now derived in §4.10.1** — with the derivation stated in the
report. That is a demonstration that the method is real rather than decorative, and it is
worth pointing at if anyone asks whether the ISO 31000 framing is doing work or is window
dressing.

Corno & Mannella's T7 explicitly names "gateway's resource saturation up to a frozen state",
so the requirement rests on published grounds, not on my instinct that cgroups are needed.

## Ratings — the honest position

The four Critical inherent risks (T01, T03, T04, T05) all have likelihood 5, "occurs by
default in normal operation". Expect to be challenged on rating ordinary behaviour as
Critical risk. The answer is that this is the correct output of the method: an integration
calling `lock.unlock` is not exploiting anything, and a risk assessment that recorded it as
Low because it is *normal* would be describing the platform's intent rather than the owner's
exposure.

Weaknesses I would concede immediately if pressed:

- **AC1 (malicious author) likelihood 2** is the softest number in the chapter. There is no
  documented Home Assistant case. Everything about AC1 rests on capability plus analogy to
  other ecosystems. I have deliberately *not* inflated it, and §4.5 says so. If challenged
  that the whole project rests on an unevidenced actor: the reply is that AC3 (documented,
  2021) and AC4 (demonstrated) carry the argument on their own, and the controls are the
  same regardless of which actor is assumed.
- **Ordinal scales multiplied** — §4.7 states explicitly that the product is not a quantity.
  Keep that caveat; removing it would be the kind of thing this advisor notices.
- **T09 vs T08** (exfiltration through a declared host vs an undeclared one) — the rating gap
  is a judgement, not a measurement.

## Residual risks: four remain High

R1 (over-declaration), R2 (declared-capability abuse), R3 (unscoped credential), R5
(exfiltration through a declared host). Each structural.

§4.11's summary deliberately says this satisfies the risk appetite "only under its second
clause, and that should be said plainly rather than presented as a clean result". Resist any
temptation to tidy this. A threat model that concludes all risks are comfortably treated is
the least believable possible outcome, and this advisor audits for a living.

**R3 is the one to raise with the platform.** Home Assistant has no scoped tokens, so the
mediator must hold full authority. That is genuinely an upstream limitation and stating it as
such — rather than as a flaw in this design — is both accurate and generous. It is also a
concrete, creditable recommendation to make in the conclusion.

## Things to watch in Chapter 5

- T12 (malicious update) is treated as adequately handled because confinement applies to
  whatever version runs. **Check this holds** once the design exists — specifically whether
  a new version's *declaration* is re-checked rather than cached from install time.
- T02 (spoofing another integration) needs per-integration identity on every mediated
  request. That is a design requirement disguised as a threat treatment; make sure the
  architecture actually carries identity rather than assuming one connection equals one
  integration.
- T11 (declared name resolving to an internal address at request time) requires
  resolve-then-pin, not name checking. Easy to get wrong.

## Deliberate omission

Their T8 (physical damage — repeated activation until a device burns out) is excluded. It is
reachable by no control available here and would be retained immediately, so including it
would pad the register without changing any treatment. §4.14 says so openly rather than
silently dropping it.
