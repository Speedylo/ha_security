# §5.12 explained from the ground up — identity and the audit record

**Written:** 2026-08-24 · **Working note, for the author.**
**Companion to:** `report/05_architecture.md` §5.12, which states the same thing formally.

Same format as `ch5_evidence_ha_coupling_explained.md`: build up the ideas, then the section,
then how to say it aloud, then six questions to test yourself against.

---

## Part 0 — The problem §5.12 solves

Suppose something bad happens in your home — a door unlocks at 3am, or a credential turns up
somewhere it shouldn't. **Which integration did it?**

Today the answer is: nobody knows. That's threat T18 in Chapter 4 — an integration acts
without attribution — and asset A7, the audit record, is called a *meta-asset* because its
integrity decides whether any *other* loss can be pinned on anything.

Requirement S7 says: record every enforcement decision, in a tamper-evident log, with **the
integration's identity**. It doesn't say what "identity" means. §5.12 decides.

---

## Part 1 — Three ideas you need

### 1.1 A hash is a fingerprint of data

A **hash function** takes any amount of data and produces a short fixed-length string — say
64 characters. Two properties make it useful:

- **The same input always gives the same output.**
- **Any change to the input — one character — gives a completely different output.**

You cannot go backwards from the fingerprint to the data, and you cannot practically find two
different inputs with the same fingerprint. So a hash is a compact answer to "is this exactly
the thing I saw before?"

> **Analogy:** a wax seal on an envelope. It doesn't tell you what's inside. It tells you
> whether it's the same envelope, unopened.

### 1.2 A name is not an identity

An integration's *name* — `example_weather` — never changes. Version 1.0 and version 2.7 have
the same name, and so does the malicious version 2.8 that arrives through the normal update
channel. That last case is threat T12.

So a log entry saying "example_weather read your locks" is nearly useless after the fact:
**it can't tell you which version did it.** If the author shipped a bad update and then
replaced it, the log names something that no longer exists in the form that misbehaved.

### 1.3 A hash chain makes tampering visible

Write a log where **each entry contains the fingerprint of the entry before it.**

Now delete entry 5. Entry 6 still carries entry 5's fingerprint — but there's no entry 5 to
compare it against. Modify entry 5 instead, and its fingerprint changes, so entry 6's stored
copy no longer matches. Reorder them and the same thing happens.

You can't quietly remove or alter a single record. **You'd have to rewrite the entire log from
that point onward.**

> **Analogy:** a numbered ledger where every page's header repeats the previous page's
> checksum. Tear out one page and the numbers stop lining up from there to the end.

---

## Part 2 — What §5.12 actually decides

### 2.1 Identity = name + a fingerprint of three things

Not just the code. **Three components, each fingerprinted separately, and then all together:**

| Component | Why it's in there |
|---|---|
| **The source code** | The obvious one — what actually ran |
| **The manifest** (including the permissions block) | Because **the manifest *is* the permission grant** |
| **The declared dependencies**, with the versions actually installed | Because that's where supply-chain attacks land |

**The manifest one is the subtle and important one.** The manifest is the document saying what
this integration is allowed to do. If identity covered only the source code, someone could
leave the code alone and quietly *widen the permissions* — and the log would show the same
identity before and after. You'd have recorded an authority change as if nothing happened.
That's the most direct possible attack on the whole design, so the grant has to be part of
what identity means.

### 2.2 Why three fingerprints instead of one

You could hash everything together and get one string. §5.12 keeps three *and* the combined
one, because:

- **One combined fingerprint tells you *something* changed.**
- **Three separate ones tell you *what* changed.**

And those are genuinely different situations. "The author shipped new code" is routine. "The
code is identical but the permissions grew" is alarming. "Code and permissions unchanged, but
a dependency moved to a new version" is the XZ Utils pattern from §1.6. One number can't
distinguish them; three can.

### 2.3 Computed once per run, not per decision

The fingerprint is calculated **when the sandbox is built**, and written into a **run record**.
Every later decision record just says "this was run #47" rather than repeating the whole
fingerprint.

Two benefits. Records stay small — which matters, because §5.11 measured that the system can
handle ~33,000 requests per second and you don't want each one carrying 200 characters of
fingerprint. And re-computing at every start means **a changed integration is a changed
identity before it has run a single line** — so T12's "re-check the declaration on every
version" happens automatically instead of being a rule someone has to remember.

### 2.4 The part I'd want you to lead with

Here's where the section says something stronger than the requirement asked for.

"Tamper-evident" means: *if someone messes with the log, you can tell.* That's what S7 asks
for, and the hash chain provides it.

But ask the sharper question — **tamper-evident against whom?**

**Against a malicious integration, the log isn't tamper-evident. It's **unreachable**.**

Remember what the sandbox is (§5.7): the integration has its own filesystem view containing
only its own directory. The log isn't in it. Its only way to communicate at all is one socket
carrying a fixed list of allowed messages (§5.11), and **none of those messages writes to the
log**. So the integration can't tamper and get caught — it can't tamper at all.

**Against someone who has broken into the host machine and can write files directly**, the
chain is *evidence*, not protection. Someone who can rewrite one record can rewrite all of
them. A keyed fingerprint — where the secret is only in the mediator's memory — makes that
harder, but doesn't survive a full compromise either.

So the honest, defensible sentence is:

> **Authoritative against the confined integration. Evidentiary against everything else.**

That's smaller than "tamper-proof audit log", and it's the claim the architecture can actually
support. Chapter 4 already put host compromise out of scope, so this matches the threat model
rather than quietly exceeding it.

### 2.5 Decisions get logged; their consequences don't

An integration says "let me watch the living-room temperature sensor." That's a **decision** —
the mediator checks the manifest, allows it, logs it once.

Then that sensor updates every 30 seconds, forever. Those updates are **not** decisions —
they're a permission already granted, being used. Logging every one would bury the entries
that matter under millions that don't.

S7 says record every enforcement *decision*, and §5.12 reads that literally rather than
conveniently. The justification: **a log nobody can read has the same value as no log** — and
"the user can't tell what happened" is exactly §1.8's complaint about the current situation.
Producing an unreadable log would be that failure again, wearing a security badge.

### 2.6 What the user sees

Should the fingerprint be shown to the user before they install?

**No — and yes.** The 64-character string itself means nothing to someone who doesn't program,
and §3.7 explicitly refuses to make claims about users understanding security disclosures.
Showing it would be decoration.

But a **change** in it is meaningful and actionable:

> *"This integration's code has changed since you approved its permissions."*

That's a sentence anyone can act on. So: **the fingerprint is for the machine, the change is
for the person.**

---

## Part 3 — Saying it out loud

**Thirty seconds.** *S7 requires decisions to be logged with the integration's identity but
doesn't define identity. We define it as the name plus a fingerprint of three things: the
source, the manifest, and the dependencies. The manifest is in there because the manifest is
the permission grant — otherwise someone could widen their permissions without changing the
identity. Records form a hash chain, so tampering breaks the chain. And against the adversary
we actually model, the log isn't just tamper-evident, it's unreachable: it's outside the
sandbox's filesystem and no message on the channel writes to it.*

**"Isn't a local log worthless against a determined attacker?"** *Against someone with root on
the host, yes — the chain is evidence, not protection, and we say so. But that's not our
adversary. Chapter 4 scopes to threats from an integration, and against an integration the log
is unreachable, not merely protected. Anchoring records externally is real future work and
Chapter 4's residual risk R4 already names it.*

**"Why not log everything?"** *Because a log nobody can read is worth the same as no log. We
log decisions, not the consequences of decisions already made. A subscription is logged once;
the updates it delivers aren't.*

**"Why is the manifest part of the identity?"** *Because the manifest is the grant. If
identity were the code alone, an author could keep the code identical and widen their
permissions, and the log would show no change at the exact moment authority changed.*

---

## Part 4 — Check yourself

Answer in your own words; the bracket says where to re-read.

1. Why isn't the integration's name enough to identify it in a log? [1.2]
2. What would go wrong if identity were a fingerprint of the source code only? [2.1]
3. What does keeping three separate fingerprints buy over one combined one? [2.2]
4. Explain how a hash chain makes a deleted log entry detectable. [1.3]
5. What's the difference between saying the log is *tamper-evident* and saying it's
   *unreachable* — and which applies to which attacker? [2.4]
6. An integration subscribes to a sensor that updates every 30 seconds. What gets logged, and
   why not more? [2.5]

**If you keep one thing:** the log is *authoritative* against the confined integration and
*evidentiary* against everything else — and being able to say which adversary you mean is what
separates a defensible claim from an overclaim.
