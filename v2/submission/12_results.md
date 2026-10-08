# 12. Simulations, Results and Interpretation

The central claim of this project is that unmodified, pre-existing integrations can be confined at a cost worth paying. Section 11 divided that claim into three assertions that can be tested separately: confinement is effective, it is compatible, and it is affordable. Before any measurement was made, a falsifier was recorded for each assertion, naming the observation that would show it to be false, and a fourth falsifier was recorded for the evaluation itself. This section reports the results against those four falsifiers in turn. Every security and compatibility result is reported as a difference between two arms run on the same host and the same platform release: a confined arm, in which the integration runs inside the framework, and an unconfined arm, in which the same integration runs as Home Assistant runs it today. The first assertion is examined first, because the architecture was designed around it.

## 12.1 Assertion A: confinement is effective

The falsifier for this assertion was fixed in advance. Assertion A fails if the garbage-collector technique reaches a platform object from inside the sandbox, if a platform credential can be recovered from the sandbox, or if the attack pattern disclosed in 2021 [6] succeeds under the framework. Any one of these outcomes would defeat the architecture itself, not merely its implementation. None of the three occurred, and Table 12.1 sets out the four attacks that test them in both arms.

**Table 12.1 — Four attacks, unconfined and confined, on the same host and platform release**

| Attack | Unconfined | Confined |
|---|---|---|
| Heap walk with the garbage collector [9] to another integration's live credential | Credential reached through 7 live objects | 8,942 objects enumerated, all the attacker's own; the same credential live in the mediator, held by 7 references |
| The 2021 path-traversal pattern [6] against two planted canary secrets | 2 of 2 recovered; 5 traversals succeeded | 0 of 2; the path does not exist (`FileNotFoundError`) |
| Reading another process's environment | Contents leaked | Nothing to read |
| Reading undeclared entity states (of which reveal occupancy or presence) | 36 of 36 (20 of 20) | 1 of 36, the one declared (0 of 20) |

Confinement removed every capability these attacks rely on, and each removal is a measured difference rather than an assertion. An absence carries no information on its own, since a broken test also returns nothing; in each row, the unconfined arm shows the attack working on this host and release. The pairing also cut against the framework. Three further attacks failed in both arms for reasons unrelated to confinement, such as `/etc/shadow` being readable only by root, and they are therefore excluded from the framework's results. Of the four rows that remain, the first carries the most weight.

The garbage-collector technique is the result the architecture was designed to defeat. Corno and Mannella [9] showed that an integration can call `gc.get_objects()`, a supported Python interface that returns every live object in the process, to reach another integration's object and read its secret. Because all integrations share one process, no in-process permission layer can prevent this: the layer would itself be an object on the heap the attack enumerates. Unconfined, the technique reached a victim integration's cloud token through seven live objects. Confined, the same code ran without error over 8,942 objects, all its own, while the token was confirmed live in the mediator's process. The attack did not fail; it succeeded and found nothing, because the credential was in another process. This outcome is stronger than a refusal, as there is no check for an attacker to evade, and the measurement in the mediator shows that the secret existed and was as reachable as the attack requires. The remaining rows show the same structure for files, processes and household data.

The 2021 disclosure [6] described integrations that read files outside their own directory by path traversal. Unconfined, five traversals succeeded and both canary secrets were recovered. Confined, the same path raises `FileNotFoundError` rather than `PermissionError`, because the file is absent from the sandbox's view of the file system and no rule had to refuse it. The entity result matters most to a household. Unconfined, a single call returned all 36 entity states on the test instance, including all 20 that reveal occupancy or presence. Confined, the integration saw only the one entity its manifest declared, and each other read was refused with a record naming the clause that refused it. Access to household data thus becomes a declaration that a user can read before installing, rather than a property of the platform. These four attacks are, however, only part of the threat register.

Against the project's threat register, sixteen of nineteen threats are demonstrated, six of them against an unconfined arm. One threat is partial: the resource limits (T16) bound memory, processor time and disk space, but not I/O bandwidth, which the test device's kernel does not delegate to an unprivileged user, nor the size of an integration's persistent data directory. Two threats are retained by decisions made before the evaluation: the framework controls where an integration connects but not what it sends (T09), and it honours an over-broad grant that a user has approved (T13). The register was also scored against the eleven threats of Corno and Mannella's model [9], so that the result can be checked against criteria this project did not write. Eight of the eleven map onto the framework's controls, five without qualification, while the three availability threats of delay, partial loss and physical damage have none. No single figure of threats controlled is reported, as Section 11 sets out, because such a figure would merge refused attempts, impossible ones and retained risks into one number. Appendix C gives the full register.

The security result is bounded by who attacked the framework. Every attack was written within the project: the adversary suite's 38 attempts, the unconfined arms, deliberate defects introduced to test the test suites, a fuzzer run against the mediator, and a line-by-line review of the enforcement code. An independent adversary was planned and then dropped, because the framework was built with AI assistance and neither the author nor the assistant would have been independent of its design. The limitation is real. The code review found that a sandbox could inherit the supervisor's terminal as its controlling terminal, a route across every isolation layer at once that no test suite had detected. It was removed and is now tested from inside the sandbox. Assertion A is therefore demonstrated against the published techniques that motivated the design, and none of its falsifier's three conditions was met. The review's finding nevertheless suggests that attacks the builders did not anticipate may remain. Whether this protection costs integrations their ability to run is the question of Assertion B.

<!-- ================================================================================== -->
<!-- Below this line: the 2026-09-08 draft, not yet rebuilt (notes/s12_results_plan.md). -->
<!-- ================================================================================== -->

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
