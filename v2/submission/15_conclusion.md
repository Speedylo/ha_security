# 15. Conclusion

## 15.1 What was claimed, and what holds

Home Assistant loads community-written integrations into its own process with its own authority,
and every control the ecosystem has acts on the *likelihood* that hostile code arrives rather than
on the *impact* once it is running. This project built the missing control — a way for an
integration's required authority to be **declared, enforced and audited** — under three constraints
that eliminate every mechanism prior work used: the integration cannot be modified, the platform
cannot be modified, and the author's cooperation cannot be assumed.

**The claim held.**

Unmodified, pre-existing integrations were confined, and the source trees are hashed before and
after every run to say so: **75 comparisons, zero changes, zero diff lines.** The published attack
that forced the architecture — walking the Python garbage collector to another integration's live
secret — was reproduced against a live credential and **defeated**: it runs perfectly and finds
nothing, while the same token is confirmed reachable seven ways in the mediator's own process. The
2021 file-theft pattern that this ecosystem actually suffered recovers **2 of 2** canary secrets
unconfined and **0 of 2** confined. Undeclared entity visibility falls from **36 of 36 to 1 of 36**,
and from 20 of 20 occupancy-disclosing entities to none.

**And the import-level compatibility cost across 77 real community integrations, on two corpora
sharing 5% of their members, measured against an unconfined baseline both times, is zero.** That
is the contribution nobody else has data for: the closest published evaluation covers three
integrations, two of them purpose-built for the experiment.

On the hardware the requirements name — an unprivileged Raspberry Pi 5 with 4 GB — mediation costs
**31.5 µs**, the audit record is made durable *before* the action it records at **3.67 ms**, the
mediator is **63× clear** of realistic demand, and **26 sandboxes** fit against a measured mean of
4.02 community integrations per installation.

## 15.2 The single ask of the platform

Of the four residual High risks, one is not a property of confinement at all.

**Home Assistant issues no scoped credential.** There is no read-only variant and no per-domain
variant of a long-lived access token, so the mediator must hold *full* authority in order to
mediate at all, and compromise of the mediator is total compromise. This project can move that
credential out of reach of every confined integration; it cannot make the credential smaller.

**One upstream change, to one artifact, would bound what a compromised mediator can do.** It is
worth stating as an ask rather than as a limitation because it has an owner, a specific form, and a
measurement behind it.

## 15.3 The claim is also smaller than it sounds

The report states this in the same voice it states the rest.

Compatibility is measured **at import** for 77 integrations and **end to end for five**, because 26
of 37 need a credential no measurement of any confinement scheme can produce. **Two of eighteen
threats are partial, two are retained by decisions taken before the artifact existed, and one was
never evaluated at all.** Three of the closest published model's eleven threats have no counterpart
in this register. The push loop does not exist, so the subscription half of one requirement is a
refusal without a delivered stream. The mediator's far side is a stand-in. The durable audit log
ran underneath one experiment of about eight.

**What the design converts is invisible authority into declared, bounded and audited authority.**
That is a smaller claim than "confinement makes integrations safe", and it is the claim the
evaluation is scoped to.

## 15.4 The last measurement was the one that mattered most, and it failed first

Running a single real community integration confined against its own real API found that **the
platform's own HTTP helper could not be constructed inside the sandbox at all** — so the egress
design had been unusable for the 41% of the corpus it was built to serve, for as long as it had
existed, **behind nineteen self-test suites that all passed**, because every earlier test subject
had been written by the author of the sandbox.

Two measured steps fixed it, and the integration then published the same electricity price confined
as unconfined, in the same minute, through a mediated connection logged to a named host and port —
and refused, with the sensor unavailable, when the clause was removed.

**The fix is worth a paragraph. The fact that nothing else in this project could have found it is
worth the chapter.** A self-test cannot find it, because a self-test is written by the same person
out of the same assumptions. A paired baseline cannot, because both arms would have to reach the
code that fails. **Only the real integration finds it** — which is why the next stage of work is to
run the whole system for real rather than to write more tests.

## 15.5 What a reader should take from this

**The mechanism is buildable.** Least-privilege confinement can be retrofitted onto an ecosystem of
thousands of pre-existing, unmodifiable extensions, using kernel primitives on commodity hardware,
without the platform's cooperation and without the authors'.

**The cost is measurable, and it is not where anyone would guess.** It is not compatibility — that
is zero at import, twice. It is a **stand-in on the far side of the mediator**, a **push loop not
yet built**, and a **network position that serves half the corpus's need directly and puts the
other half behind a flag the user has to read differently.**

**And the thing that made the project defensible is not in the artifact.** Six of eight
pre-registered predictions were wrong, every one caught by a measurement and none revised
afterwards. A paired baseline stopped three misattributions that a traceback alone would have got
wrong, and **every one of them would have charged the design more than it deserved**. Superseded
sections kept their text and gained a dated pointer, so what was believed *before* each number
arrived is still recoverable.

Across the whole project, **every correction has been to a sentence standing next to a measurement,
and none to a measurement.** That asymmetry is the most transferable result here — and it is an
argument for reading the work again rather than a claim that it is now clean.
