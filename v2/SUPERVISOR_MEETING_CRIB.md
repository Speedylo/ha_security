# Supervisor meeting — crib sheet

**He knows nothing: not the topic, not that you've started.** The first 90 seconds do most of the
work. Say the problem before the project. Disclose the summer work early and flatly. Leave with the
handbook.

---

## 1 · Open with the problem (~40 s)

> "Home Assistant is the biggest open-source smart-home platform — about **670,000 homes**. It's
> useful because anyone can write a plug-in for it, and about **4,200 people have**. The problem is
> that every one of those plug-ins runs *inside* Home Assistant with Home Assistant's full
> authority. So a plug-in you installed to show your electricity prices can read every password in
> the house, unlock your front door, and see whether you're home. It's not a bug — there's **no
> permission model at all**."

## 2 · Then the difficulty — this is what makes it a project (~20 s)

> "The obvious fix is to sandbox them. Nobody does, because you'd need 4,200 hobbyist authors to
> rewrite their code. So my project builds confinement that needs **no change to the plug-in and no
> change to Home Assistant** — and measures what it costs."

## 3 · Disclose the summer work, then ask the question (~30 s)

> "Over the summer I built a prototype to check the idea was feasible before committing a semester
> to it. It works, which is why I can be concrete about what's left."
>
> **"Is there anything in the regulations about work done before the semester starts that I should
> know about?"**

**Ask it in the same breath.** Asking is what protects you. Ten seconds of his time settles a
worry you can't settle yourself.

## 4 · One result, then stop

> "I ran **77 real community integrations** both with and without the sandbox. They fail on exactly
> the same ones, for exactly the same reasons — so the **compatibility cost of confining them is
> zero**. Measured twice, on two samples that overlap by only 5%."

## 5 · Hand him the gap — this is what stops "you're done, do something else"

> "What it doesn't do yet is run against a *real* Home Assistant. The part that would actually turn
> on your light is a stand-in I wrote for testing. The audit log has only run in one experiment out
> of eight. Five integrations have actually executed end to end — one against a real API. **That's
> what I think the semester should be.**"

Then the sentence that makes him stop worrying about you:

> "Two of my components passed every test I wrote for them and then broke the first time real code
> went through them. Two instances is a pattern. It says the next work is running the whole thing
> for real, not writing more tests out of the same assumptions I already made."

## 6 · Give him a real decision

> "I can see three candidates for the semester's core — the live component, running many
> integrations for real, or the live-streaming path that's the one requirement I can't fully close.
> I lean toward the first two. Which fits the programme's expectations better?"

## 7 · Don't leave without

1. **The handbook and the deadlines** — "I need them to plan." *(Blocking 4 title-page fields since 21 Aug.)*
2. **The pre-semester question** (§3 above).
3. **What the AI-use declaration has to cover** — it now covers the summer work too.

---

## Numbers, if he asks

| | |
|---|---|
| Ecosystem | 669,743 installs · 4,220 community integrations · 56.6% run HACS · median integration has 20 installs |
| Hardware | Raspberry Pi 5, 4 GB · Home Assistant 2026.8.3 · Python 3.14 · unprivileged, no root |
| Compatibility | **84%** head corpus (37) · **92%** uniform corpus (40) · **identical in both arms** · design's cost **0**, twice |
| Requirements | 20 total — **19 met, 1 partial** (entity subscriptions, needs the push loop) |
| Threat model | 18 threats · 7 residual risks · STRIDE + ISO 31000 + OWASP Threat Dragon |
| Tests | **19 self-test suites** pass on the Pi |
| Attacks | Unconfined: **2/2** canary secrets stolen, 11 attacks returned data. Confined: **0/2** |
| The gc attack | Unconfined reaches a live token **7 ways**; confined finds nothing — token confirmed still live in the mediator |
| Entity visibility | Unconfined **36/36** + all presence; confined **1/36** |
| Speed | **31.5 µs** per mediated request · 3.67 ms with durable audit write · **63×** headroom over realistic load |
| Footprint | ~120 MB per sandbox · **26 sandboxes** fit in 60% of a 4 GB Pi |
| Rigour | **6 of 8** predictions registered in advance were wrong; **none revised** |
| Unmodified | 75 integration trees hashed before/after — **0 changed, 0 diff lines** |

## If he says… say…

| He says | You say |
|---|---|
| "Have you considered *X*?" | "That's on my list — I've scoped it, roughly *N* days. Should it come before the live component?" **Turn a suggestion into a scheduling question.** |
| "Is this actually novel?" | "The problem was identified in 2022 and manifest permissions go back to 2010 — I don't claim either. What nobody has done is **build and evaluate** it, and measure the compatibility cost. A published systematic review asks for exactly this: a proof-of-concept for Home Assistant evaluated against that 2022 threat model." |
| "This sounds ambitious." | "It's built and running on a Pi. That was the risk, and it's settled." |
| "Sounds like you've finished." | Go to §5. The mediator's far side is a stand-in; the audit log ran once in eight; five integrations executed. |
| "What's been hardest?" | The mDNS finding: a real integration couldn't create an HTTP client inside the sandbox **at all** — hidden behind eighteen passing tests, because every earlier test subject was written by me. *Best answer you have. Let him ask for it.* |

## Traps — don't

- **Don't lead with 84%.** He'll hear "16% broken by your sandbox." It's the fraction that loads on
  that Home Assistant version at all; both arms return it. **Your number is the zero.**
- **Don't demo the Pi live.** A network hiccup costs you the credibility the result just bought.
  Laptop, two things pre-opened: the compatibility table and the passing test suite.
- **Don't say "finished" or "done."** It isn't — and §5 is the true and better answer.
- **Don't oversell novelty.** Conceding the two prior-art points *first* is what makes the real
  claim credible.

## Bring

Laptop with the compatibility table + test suite already on screen · `PROJECT_OVERVIEW.md` open
behind them for detail · something to write the deadlines on.
