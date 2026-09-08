# 12. Simulations, Results and Interpretation

The claim under test was stated before any measurement existed:

> **Unmodified, pre-existing integrations can be confined at a cost worth paying.**

It was separated into three assertions — confinement is **effective**, **compatible** and
**affordable** — and a falsifier was written for each, in advance. This chapter answers them
against those falsifiers rather than against a restatement of them.

## 12.1 Assertion A — confinement is effective

**Falsifier:** *the garbage-collector technique reaches a platform object, or a platform credential
is recoverable from the sandbox, or the 2021 pattern succeeds under the framework. Any one is fatal
to the architecture, not merely to the implementation.*

None of the three occurred, and — the part that matters — **each was measured against an unconfined
arm on the same host and release**, so each block is a difference rather than an assertion.

**Table 12.1 — The paired security result**

| | Unconfined | Confined |
|---|---|---|
| The published `gc` technique reaching a live credential | **reached it 7 ways** | 8,942 objects, **all its own** — while the same token is confirmed live in the mediator's process, 7 references deep |
| The 2021 file-theft canaries | **2 of 2 recovered**; five traversals worked | **0 of 2**; `open("../../secrets.yaml")` raises `FileNotFoundError` |
| Another process's environment | `LEAKED` | `EMPTY` |
| Undeclared entity states | **36 of 36**, and **20 of 20** disclosing occupancy or presence | **1 of 36**, **0 of 20** |

### 12.1.1 The garbage-collector result is the one that matters

The published attack [9] is what eliminated every in-process design. Run against this framework:

**it works.** It is not blocked, not filtered, not detected. It enumerates the heap without error,
exactly as published, **and finds nothing** — because every object in that heap belongs to the
integration running it. The other integrations are in other processes.

That is the difference between a design that *answers* this attack and one that *survives* it. An
in-process defence would have to catch the sweep, which means being an object in the heap the
sweep enumerates. **Here there is nothing to catch, and the attack's own success is the evidence.**

The same shape appears twice more. `/proc` lists one process, so reading another process's
environment returns an empty list rather than a refusal — the threat rated as requiring *no
attacker skill* has nothing left to read. And `setuid(0)` **succeeds**, which is worth stating
rather than omitting: the sandbox is already uid 0 inside its own user namespace, and that uid maps
to an unprivileged user outside. The call does exactly what it says and means nothing.

### 12.1.2 Why the unconfined arm is what turns an absence into a result

An absence produced by a defect is indistinguishable from an absence produced by the framework
working. The confined-only version of the credential test was very nearly a tautology.

The third column of Table 12.1's first row is the fix: **the credential exists, it is exactly as
reachable as the published attack requires, and the sandbox boundary is what the adversary cannot
cross.** Seven reference paths to a live token, in the mediator's own process, in the same session.

### 12.1.3 What the pairing cost the framework, and why that matters

The unconfined arm did not only confirm the design. **It cut against it three times**, and each
correction removed a control the framework does not provide:

- Three attacks fail in **both** arms — `/etc/shadow` is root-only, nothing was listening on the
  platform's port, and a test hostname does not resolve. Reported alone, the confined run would
  have credited this framework with three controls it does not have.
- One compatibility finding was **withdrawn** when the baseline showed the integration broken
  either way, on this release, confined or not.
- One opaque import failure that looked exactly like a confinement failure turned out to be the
  integration's own defect.

**Every one of those would have charged the design *less* than it deserved in the direction an
author's own attributions tend to err.**

### 12.1.4 What A does not extend to

**Thirteen of eighteen threats are demonstrated, five of them paired; two are partial; two are
retained by decisions taken in advance; and one — a malicious update through the authorised path —
has no evidence at all.** Against the closest published register, eight of eleven threats are
mapped and five scored cleanly.

**No aggregate is reported.** A single "threats controlled" figure is the security equivalent of an
unlabelled compatibility percentage, and it would erase the distinction between an attempt that was
*refused* and one that *succeeded and found nothing* — where the second is the stronger outcome.

## 12.2 Assertion B — confinement is compatible

**Falsifier:** *the baseline arm shows that most of the confined shortfall is the design's — i.e.
the baseline passes substantially all 37 while the confined arms pass 31.*

**The opposite happened, twice, on two corpora sharing 5% of their members.**

**Table 12.2 — The headline result**

| Question the corpus answers | Corpus | Confined | Unconfined baseline | **Design's cost** |
|---|---|---|---|---|
| What do most *installations* run? | Head-weighted, 37 | 84% | **84%** | **0** |
| What do most *integrations* do? | Uniform draw, 40 | 92% | **92%** | **0** |

**Identical failure sets, identical error strings** — in four of six cases byte for byte, including
the truncated exception text. **The import-level compatibility cost of confinement, across 77
integrations on this release, is zero.** No integration passes unconfined and fails confined, and
the set difference is empty in both directions.

> **Stating this correctly is most of its value, and it is the one number most likely to be
> misread.** 84% was never a statement about confinement. It is the fraction of the most-installed
> community integrations that import cleanly on Home Assistant 2026.8.3 **at all** — a joint
> property of the corpus and the release — and confinement moves it by nothing. **The result is the
> difference, and the difference is zero.**

### 12.2.1 Which six fail, and whose fault each is

Of the six head-corpus failures, **only three belong to the design.** Three integrations import
`aiofiles`, a package neither the platform nor its `default_config` closure supplies; one fails on
a constant removed from the platform *in this very release*; and two are corpus artifacts rather
than integrations. **31 of 34 — 91% — of what the corpus delivered in a loadable state.**

**One detail on `aiofiles` is worth more than the rate.** Home Assistant's own
`package_constraints.txt` pins it with the comment *"aiofiles keeps getting downgraded by custom
components"*. **That is the platform's own maintainers documenting this exact problem in their own
ecosystem** — independent corroboration of the undeclared-dependency bound rather than this
project's inference about it.

### 12.2.2 The profile decision, and a prediction that did not survive

Compatibility depends on how much of the platform the sandbox supplies. Four profiles were
measured:

| Profile | Clean | Median peak | Premium per sandbox |
|---|---|---|---|
| `minimal` | 17/37 — 46% | 100.6 MB | — |
| `declared` (per-integration) | 21/37 — 57% | 109.6 MB | +9.0 MB |
| `unstripped` blanket ten | 26/37 — 70% | 132.8 MB | +32.2 MB |
| **`declared` + core package set** | **31/37 — 84%** | **119.7 MB** | **+19.1 MB** |

**The last row strictly dominates the blanket profile** — every integration the blanket profile
passes, plus five more, for 13.1 MB *less* per sandbox. There is no trade to weigh.

**"What a stock installation has" is computed, not asserted:** the core set is the `default_config`
dependency closure — 57 components — and the union of their declared requirements — 39 packages —
taken from the platform's own source.

**A registered prediction failed here and the failure is the better result.** The `declared`
profile was predicted to reach 70–76%. It reaches **57%**, over *exactly the same twenty-one
integrations* as an earlier arm that ran without the auth manager wired. **Wiring auth changed
eleven failure reasons and moved the corpus figure by zero.**

### 12.2.3 The honest reading of B

Both figures are **import-level**, and one requirement exists precisely to stop that being read as
compatibility. The executed end-to-end population is **five — a named set, not a rate.** The
ceiling on any such measurement is a property of the ecosystem rather than of this design: **26 of
37 integrations require a credential before their own configuration flow can complete**, and an
unconfined baseline meets the identical wall.

Of the five, three loaded and published confined and four unconfined, so **confinement's cost at
the level that matters more is exactly one integration** — with the reason known (an undeclared
component) and a named fix. One round trip is complete: two declared entities mirrored in, **15
derived sensors published out**, dew point physically correct.

**So the precise claim is: zero import-level cost across 77 integrations, and one integration in
five costed at the level that matters more.** That is smaller than "confinement is free" and it is
what the measurements support.

### 12.2.4 What building the egress proxy actually bought

**30 of 37 integrations — 81% — declare that they reach something.** But that need splits almost
exactly in half, and **the two halves are not the same capability.** Fifteen (41%) are cloud-facing
and reach the internet; the other fifteen (41%) are local-facing and reach devices on the home LAN,
which the design provides for only behind a **separate explicit flag** — because reaching the LAN
is reaching the router's admin page and every other device in the house.

**So building the proxy did not make 81% of the corpus workable. It made 41% workable and put the
other 41% behind a declaration the user is meant to read differently.** That is the sharpest single
statement of what this design's network position costs, and it is a property of the design rather
than a limitation of the artifact.

## 12.3 Assertion C — confinement is affordable

**Falsifier:** *per-sandbox cost puts the budget below the measured mean of 4.02 integrations per
installation, or mediation latency at realistic sandbox counts changes what the platform can do.*

| | Measured | Against |
|---|---|---|
| Per-sandbox memory budget on the target device | **26 sandboxes** | a measured mean of **4.02** integrations per HACS-running installation |
| Mediator capacity, audit write included | **272 decisions/s** | realistic demand of **4.33 req/s** at the full budget — **63× headroom** |
| Latency at 0.009% utilisation | **31.5 µs** | — |
| Durability | `fsync` per decision costs **3.67 ms**, 59× the non-durable write | affordable; the ordering guarantee is kept |

**Assertion C holds, and the arithmetic behind it was corrected once inside the evaluation.** The
first report of headroom was **11,000×**, computed by excluding the audit write. That write was
then measured at a hundred times the mediated request itself, and **the honest figure is 63×.** The
conclusion survives and the number does not, so the corrected one is the one quoted: the mediator is
*comfortably but finitely* clear of demand, not four orders of magnitude clear.

**Two limits are carried with C rather than discovered after it.** The mean is the wrong statistic —
telemetry gives per-integration install counts but not the spread across installations, so a budget
above the mean may still fail the tail. And **the hot path is unmeasured**: at 272 decisions/s a
subscription delivering every state change in a busy home is not obviously affordable, and the push
loop does not exist to measure. **C is established for the request/response shape, and for no
other.**

> **Figure 12.1 — [TO DRAW]** Latency against sandbox count, with the durable-write correction
> marked; and the memory budget curve against the 4.02 mean.

## 12.4 C1 — *unmodified*, counted rather than argued

The word the project's title rests on was, for two months, **argued rather than counted.** The
report claimed a mechanical zero-line diff verified that no integration source was modified. **That
diff did not exist.** What existed was a read-only bind mount making modification impossible in the
confined arm — and nothing at all in the baseline arm, which runs the fetched tree directly.

It was then built and run: **75 tree comparisons across both arms, zero source changes, zero diff
lines.** The instrument is wired into the compatibility harness itself rather than kept as a
separate script, so **every future compatibility run counts C1 by running at all.**

Two departures from the plan are recorded rather than absorbed. Hashing *at fetch* proved
impossible, because the corpus manifest pins `HEAD` and stores no content hash — so the count
covers a run and not the project's history. And **the instrument's first version returned a
reassuring zero because it compared the baseline tree against itself**; it was caught by a
self-test written for exactly that failure mode.

## 12.5 The security result against both registers

| Register | Mapped | Outcome |
|---|---|---|
| This project's own, 18 threats | 18 | **13 demonstrated** (5 paired), 2 partial, 2 retained by prior decision, **1 never evaluated** |
| Corno and Mannella's, 11 threats [9] | 8 of 11 | **5 clean** |

Scoring against the external register is what the independent systematic review [21] proposed, and
doing it produced two findings that would otherwise have gone unsaid. **Three threats had
demonstrated controls sitting in a test suite that no results section reported** — including a real
DNS-rebinding demonstration in which the manifest permits the *name* and the broker refuses the
*resolved address*. And **one threat is the only one in either register that is neither
demonstrated nor declared unevaluable**, which the report states rather than leaves to be found.

## 12.6 The result that arrived last, and mattered most

**Running one real community integration confined against its own real API found a defect that
nothing else in this project could have found.**

`nordpool` is the corpus's only member that both needs a network and configures without a
credential. It was run in three arms — unconfined, confined with its API host declared, and
confined with the clause removed, the third being what makes the second evidence.

**The first run failed, and that is the result.** `nordpool` calls `async_get_clientsession(hass)`
— *what the platform's own documentation tells an author to call*. On 2026.8.3 that builds its DNS
resolver by instantiating Zeroconf, which joins the mDNS multicast group, and a fresh network
namespace's loopback carries no multicast flag. The join fails with `ENODEV`.

**A real integration could not construct an HTTP client inside the sandbox at all**, before any
name was resolved or any connection attempted. **The egress design had been unusable for the 41% of
the corpus it exists to serve, for as long as it had existed, behind eighteen self-test suites that
all passed** — because every earlier test subject had been written by the author of the sandbox and
used a bare client session, skipping the very helper that breaks it.

It was fixed in two measured steps, and the grant is **vacuous by construction**: the multicast
route's device is loopback, so every datagram the sandbox sends is delivered to the sandbox, and no
second interface can be added without a privilege the sandbox does not have.

**The result, after the fix:** `nordpool` published **0.026 — the same electricity price confined as
unconfined, in the same minute** — with three grants logged as
`dataportal-api.nordpoolgroup.com:443` and both audit chains verifying. **With the clause removed:
three denials and a sensor reading `unavailable`.**

That third arm is what makes the second evidence rather than a demonstration.

## 12.7 What the evaluation reports as not done

The fourth falsifier was written about the **evaluation** rather than the artifact:

> *If the evaluation cannot demonstrate a requirement and reports it as passed anyway, or reports an
> aggregate that conceals a decomposition it possesses, the evaluation has failed on its own terms.*

**It fired.** C1 was reported as verified mechanically when it was not (§12.4), and a chapter
committed to scoring the security axis twice had performed neither scoring (§12.5). Both are
repaired above, **and neither repair unfires the falsifier**: the answer is correct now because the
report was read end to end, not because the evaluation caught itself.

Stated plainly, the gaps that remain:

- **The push loop does not exist**, so S3's subscription half is a refusal without a delivered
  stream, and the only latency path that could consume the 63× margin is unmeasurable.
- **The mediator acts on a stand-in**, so what a live platform does with a mediated write is
  untested. What that costs is **entity identity**, not realism.
- **The end-to-end population is five.**
- **The durable audit log was engaged in one experimental run of about eight.** The mechanism is
  built and its properties are demonstrated — tamper, delete and reorder all detected — but it was
  not running underneath most of the evaluation.
- **One threat was never evaluated and was never declared unevaluable.**
- **A transcription error common to a results file and the report would survive both
  read-throughs**, because neither re-ran anything.

## 12.8 One measurement that did not resolve

Memory against declaration depth was attempted and **did not produce a curve**: three points, three
sandboxes each, and the series is non-monotonic — 136.3, 95.7, 115.8 MB — which is proportional set
size's sensitivity to what happens to be shared at that moment rather than a trend. **No curve is
drawn and no trend is claimed.** It is reported because an unresolved measurement that is omitted
becomes an unasked question.

## 12.9 The predictions, scored

**Six of eight registered predictions were wrong, and none was revised.**

**The distinction worth reporting is not the count but which two held.** The two correct predictions
were the two *about the design* — that confinement's compatibility cost would be at or near zero,
and that a zero measured once would hold on a near-independent sample. **Every wrong one was a
prediction about what the ecosystem or the kernel would do**: that a package the platform pins
defensively must therefore be installed; that the mediator would degrade in the tail before the
median; that page-cache charging would kill a legitimate large-file reader; that wiring the auth
manager would raise the compatibility figure; and — wrong *in sign* — that the ecosystem's long
tail would import worse than its head. **It imports eight points better.**

**So: the design behaved as designed; the world did not behave as assumed.** That is a more
defensible claim than a bare six-of-eight, and it is only available because the predictions were on
the record before the numbers.

## 12.10 A finding nobody was looking for

The two compatibility arms produced a number neither was designed to produce:

```
head-weighted corpus    baseline loads a median of 52 components    sandbox sets up  2
uniform corpus          baseline has  53 available                  sandbox sets up  0  (max 7)
                        ── identical import-level compatibility in both ──
```

**Whatever the other fifty components are for, importing a community integration and bringing up
its entity platforms is not it.** The gap *widens* as the integrations get simpler, and the
compatibility outcome does not move.

This bears on three things it was not measured for. It is direct evidence that stripping the
platform to what an integration declares costs no compatibility. It sharpens the honesty cost of
the core package set, because the sandbox carries 641 MB of packages no integration declared while
carrying fifty fewer *components* — **and components are where capability lives.** And it is the
strongest available argument that **a capability check inside the platform's own loader would have
to cover a far smaller surface than the platform's size suggests.**

**What it does not say:** it is an import-and-platform-setup measurement. An integration that
*runs* may need components it does not need to *load*.
