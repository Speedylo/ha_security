# Chapter 8 — Conclusions, Limitations and Future Work

## 8.1 What this chapter is for, and what it will not repeat

Seven places in this report already state a limit. §3.7 excludes non-goals; §4.11 states six
residual risks with a rating each; §5.15 sorts the design's limits by who could fix them; §7.9
lists threats to the validity of the evaluation; §7.11 names four things the evaluation cannot do;
§7.26.5 adds a fifth it missed; and every results section in Chapter 7 closes with a *what this
does not establish* block of its own.

A closing chapter that collected them would be padding, and §5.15 already refused to write that
chapter one level down. This one answers three questions no earlier chapter is positioned to
answer:

1. **Did the central claim hold**, judged against the falsifiers §7.7 fixed before any measurement
   ran — including the falsifier that applies to the evaluation rather than to the artifact.
2. **What did this project get wrong**, and what does the pattern of its errors say about the
   method that caught them.
3. **What should the next person do**, priced, and separated from what only somebody else can do.

Limitations appear in §8.6, and only those that no earlier section states — the ones Chapters 6
and 7 discovered, which §5.15 could not have known about because they had not happened yet.

## 8.2 The central claim, answered against the falsifiers fixed in advance

§5.15.6 stated the claim and conceded it was empirical:

> Unmodified, pre-existing integrations can be confined at a cost worth paying.

§7.2 separated it into three assertions and §7.7 wrote a falsifier for each, before any
measurement existed. The claim is answered here against those falsifiers and not against a
restatement of them.

### 8.2.1 A — confinement is effective

**Falsifier (§7.7):** *the garbage-collector technique reaches a platform object, or a platform
credential is recoverable from the sandbox, or the 2021 pattern succeeds under the framework. Any
one is fatal to S1/S2/S8 and to the architecture, not merely to the implementation.*

None of the three occurred, and — the part that matters — each was measured against an unconfined
arm on the same host and release, so each block is a difference rather than an assertion:

| | Unconfined | Confined |
|---|---|---|
| The published `gc` technique reaching a live credential (§7.15.3) | **reached it 7 ways**, off a `CloudClient` attribute and through `hass.data` | 8,942 objects, all its own — **while the same token is confirmed live in the mediator's process, 7 references deep** |
| The 2021 file-theft canaries (§7.13.2) | **2 of 2 recovered**; five traversals worked | **0 of 2**; `open("../../secrets.yaml")` raises `FileNotFoundError`, not `PermissionError` |
| Another process's environment (§7.13) | `LEAKED` | `EMPTY` |
| Undeclared entity states (§7.14.2) | **36 of 36**, and **20 of 20** that disclose occupancy or presence | **1 of 36**, **0 of 20** |

The third row of the first line is what turns an absence into a result. §6.4.5 warned that any
defect producing an absence is indistinguishable from the framework working, and §7.15.1 records
that §6.9's confined-only version of this test was nearly a tautology. The credential exists, it is
exactly as reachable as the published attack requires, and the sandbox boundary is what the
adversary cannot cross.

**Assertion A holds, and it holds against the one published result that forced the architecture.**
§2.4.1 is the load-bearing citation of this project: Corno and Mannella walk `gc.get_objects()` to
another integration's live secret, and that single result eliminates every in-process design.
§7.15 reproduces it and then defeats it.

**What A does not extend to.** Thirteen of Chapter 4's eighteen threats are demonstrated, five of
them paired; two are partial; two are retained by a decision §4.11 recorded in advance; and one —
T12, a malicious update through the authorised path — has no evidence at all (§7.26.5). Against the
external register, eight of Corno and Mannella's eleven are mapped and scored, five cleanly
(§7.26.4). **No aggregate is reported**, on §7.4.2's rule that a single "threats controlled" figure
is the security equivalent of an unlabelled compatibility percentage.

### 8.2.2 B — confinement is compatible

**Falsifier (§7.7):** *the baseline arm shows that most of the confined shortfall is the design's —
i.e. the baseline passes substantially all 37 while the confined arms pass 31. That would make
confinement, not the corpus, the cause, and would reopen G3.*

The opposite happened, twice, on two corpora sharing 5% of their members:

| Question | Corpus | Confined | Unconfined baseline | Design's cost |
|---|---|---|---|---|
| What do most *installations* run? | Head-weighted, 37 | 84% | **84%** | **0** |
| What do most *integrations* do? | Uniform draw, 40 | 92% | **92%** | **0** |

Identical failure sets, identical error strings, in four of six cases byte for byte including the
truncated exception text. **The import-level compatibility cost of confinement, across 77
integrations on this release, is zero.** No integration passes unconfined and fails confined, and
the set difference is empty in both directions.

**This is the contribution nobody else has data for (§2.8, contribution 3), and stating it
correctly is most of its value.** 84% was never a statement about confinement — it is the fraction
of the most-installed community integrations that import cleanly on Home Assistant 2026.8.3 *at
all*, a joint property of the corpus and the release, and confinement moves it by nothing. The
result is the difference, and the difference is zero.

**What B does not extend to, and this is where the honest reading lives.** Both figures are
import-level, and N2 exists precisely to stop that being read as compatibility. The executed
end-to-end population is **five, a named set and not a rate** (§7.17), and the ceiling on any such
measurement is a property of the ecosystem rather than of this design: **26 of 37 integrations
require a credential before their own config flow can complete** (§7.17.1), and an unconfined
baseline meets the identical wall. Of the five, one — `powercalc` — is confirmed as confinement's
cost by comparison rather than by traceback, on an undeclared *component*; and one candidate
finding was withdrawn when the baseline showed it broken either way (§7.17.5).

So the precise claim is: **zero import-level cost across 77 integrations, and one integration in
five costed at the level that matters more, with the reason known and a named fix.** That is
smaller than "confinement is free" and it is what the measurements support.

**A sixth integration was added after those five, and it is the one that carries F2.** §7.27 ran
`nordpool` — unmodified community source, `cloud_polling`, the only member of the corpus that both
needs a network and can be configured without a credential — in three arms: unconfined, confined
with its API host declared, and confined with the clause removed. Confined and declared, it
published **the same electricity price as the unconfined arm produced in the same minute**, with
the mediator's durable record naming `dataportal-api.nordpoolgroup.com:443` three times. With the
clause removed, the same three requests were refused and the sensor read `unavailable`. F2's
criterion is therefore met by a real integration polling its own real API and not only by a
coordinator written for the test.

**And it found a compatibility cost that no other measurement in this report could have found.**
The first run failed: `nordpool` calls `async_get_clientsession(hass)`, which is what the platform
tells an author to call, and in 2026.8.3 that builds a resolver by instantiating Zeroconf, which
joins the mDNS multicast group — an operation a fresh network namespace refuses with `ENODEV`.
**A real integration could not construct an HTTP client inside the sandbox at all**, before any
name was resolved or any connection attempted. §7.25's subject had used a bare
`aiohttp.ClientSession()` and skipped the very helper that broke the design, so every earlier
egress result was measured around the defect rather than through it. Two lines in the namespace
setup fixed it, and §7.27.3 argues that the grant is vacuous — the route's device is `lo`, so a
joined group carries only what the sandbox sends to itself. The finding, not the fix, is the
result: **until 2026-09-03 the egress design did not work for the 41% of the corpus it was built
to serve, and only running a real integration revealed it.**

**One thing B does not say at all, and §7.18.1 said Chapter 8 owed it.** The corpus's need for
a network is the majority position — **30 of 37, 81%, declare that they reach something** — but it
splits almost exactly in half, and the two halves are not the same capability. Fifteen (**41%**) are
`cloud_polling` or `cloud_push` and reach the internet: those are what §5.8.2's scope item 2 serves
directly, and what §7.25 and §7.27 evaluated. The other fifteen (**41%**) are `local_push` or
`local_polling` and reach devices on the home LAN — which §5.10.3 provides for only behind a
**separate explicit flag**, because reaching the LAN is reaching the router's admin page and every
other device in the house (T10), and because §7.26.2 found that flag being read from the sandbox's
own request. **So building the proxy did not make 81% of the corpus workable. It made 41% workable
and put the other 41% behind a declaration the user is meant to read differently.** That is the
sharpest single statement of what this design's network position costs, it is not a limitation of
the artifact but a property of the design, and no chapter before this one states it.

### 8.2.3 C — confinement is affordable

**Falsifier (§7.7):** *per-sandbox cost puts the budget below §5.8.1's measured mean of 4.02
integrations per installation, or mediation latency at realistic sandbox counts changes what the
platform can do.*

| | Measured | Against |
|---|---|---|
| Per-sandbox memory budget on the C4 device | **26 sandboxes** (§6.3.2) | a measured mean of **4.02** integrations per HACS-running installation |
| Mediator capacity, audit write included | **272 decisions/s** (§7.20.1) | realistic demand of **4.33 req/s** at the full budget — **63× headroom** |
| Latency at 0.009% utilisation | **31.5 µs** | — |
| Durability | `fsync` per decision costs **3.67 ms**, 59× the non-durable write | affordable; §5.11.3's ordering guarantee is kept |

**Assertion C holds, and the arithmetic behind it was corrected once inside the chapter.** §7.19.3
first reported 11,000× headroom by excluding the audit write; §7.20.1 measured that write at a
hundred times the mediated request itself and the honest figure is 63×. The conclusion survives and
the number does not, so the corrected one is the one quoted — the mediator is *comfortably but
finitely* clear of demand, not four orders of magnitude clear.

**Two limits carried with C rather than discovered after it.** §7.7 itself recorded that **the mean
is the wrong statistic** — the telemetry gives per-integration install counts but not the spread
across installations, so a budget above the mean may still fail the tail, and the falsifier is
stated against the mean because that is the only figure the data supports. And **the hot path is
unmeasured**: at 272 decisions/s a subscription delivering every state change in a busy home is not
obviously affordable, and §7.14.4 records that the push loop does not exist to measure. C is
established for the request/response shape §5.11.1 calls mediated, and for no other.

### 8.2.4 The fourth falsifier was about the evaluation, and it fired

§7.7 added a falsifier that does not concern the artifact:

> If the evaluation cannot demonstrate a requirement and reports it as passed anyway, or reports an
> aggregate that conceals a decomposition it possesses, the evaluation has failed on its own terms.

Nothing was reported as passed that was not demonstrated: all twenty of §7.5's requirements carry a
verdict, S9's is explicitly against narrowed wording (§7.22.2), S3's and N2's are explicitly
partial, and the two rows that were blocked were named in the criteria table on the day the
criteria were frozen rather than conceded in a limitations section later.

> **That sentence was wrong about one requirement, and Stage 5 found it on 2026-09-04 (§7.28).**
> **C1 was reported as verified mechanically and is not.** The zero-line diff §7.4.1 describes does
> not exist anywhere in the artifact; what exists is a read-only bind mount that makes the confined
> arm structurally incapable of modifying its source, and **nothing at all in the baseline arm**,
> which runs the fetched tree directly. C1's verdict is downgraded from *counted* to *argued*
> rather than withdrawn — no modification has ever been observed and none is expected — but this
> is precisely the falsifier above firing a second time, on the requirement underwriting the word
> *unmodified*. **It is left here as a correction rather than absorbed**, because a section
> answering "did the evaluation report anything as passed that it had not demonstrated" is the
> worst possible place to quietly fix the answer.
>
> **Counted 2026-09-06 (§7.29), and the correction stays.** 75 tree comparisons across both arms,
> zero source changes, zero diff lines; C1's row is ✅ and the diff now exists. What does not change
> is the finding above: for two months this section answered a falsifier about the evaluation's
> honesty with a sentence that was false, and the answer is only correct now because Stage 5 read
> the chapter rather than because the evaluation caught itself. **The falsifier fired; running the
> check afterwards does not unfire it.**

**But the chapter did fail a commitment of its own, and a reader is owed the finding rather than
the reassurance.** §7.2 committed the security axis to being scored twice — against Chapter 4's
eighteen threats and against the eleven of the closest published model — *"so that the result is
comparable against an existing published model rather than against criteria invented here"*, which
is also the framing §2.8 adopts from an independent systematic review. **Neither scoring existed in
§7.12–§7.25.** The results half is organised by requirement, so closing out the measurement
schedule gave no signal that a *reporting* obligation was outstanding, and a T-number appeared
sixteen times in seventeen hundred lines of results, every one of them in passing.

Nothing had to be re-run to fix it: §7.26 performs both scorings from evidence the chapter already
held. Two things came out of doing so that would otherwise have gone unsaid — **T08, T10 and T11
had demonstrated controls sitting in `selftest_egress` that no section reported**, including a real
DNS-rebinding demonstration in which the manifest permits the name and the broker refuses the
resolved address; and **T12 is the only threat in either register that is neither demonstrated nor
declared unevaluable.**

The general lesson is worth more than the repair. **A chapter organised by one table is answerable
to every table it referenced**, and the only instrument that finds the difference is reading it as
one document. That took two passes (§7.21, §7.26) and both found something.

## 8.3 The three contributions, closed against §2.8

§2.8 stated three contributions *"so that each can be checked"*. Checking them is this section.

**Contribution 1 — an empirical account of the API surface community integrations depend on.**
Delivered (`notes/ch5_evidence_api_surface.md`): 1,458 core integrations and 144 community ones
parsed with `ast` rather than grepped, zero parse failures, every figure a stated lower bound. *(1,458 and not §5.6.1's 1,482 because the parser skips the 24 shipped integrations holding no `.py` file; §5.6.1 states the reconciliation.)* It
did the work §2.8 claimed for it — it made the retrofit problem quantitative, and §5.10's schema
takes six specific decisions from it, including that blanket state denial is not available at 41%
and that filesystem permission must be path-scoped because absolute denial breaks 33.3%. It also
caught its own error: a `grep` cross-check disagreed with the parser, and the corrected figures are
up to 1.9× higher than the first run reported.

*The gap.* The community half is head-weighted, and its own §6 said a uniform sample was *"worth
running before Chapter 7 reports coverage"*. §7.23 ran a uniform corpus for **compatibility** and
never re-ran the API-surface parser over it, so §7.8's obligation row was half discharged. This is
the cheapest outstanding item in the whole report — one existing script over an already-fetched
corpus — and §8.7 prices it as such.

**Contribution 2 — a confinement architecture for an extension model that cannot be changed.**
Delivered and evaluated. Eighteen self-test suites pass on the target hardware; C2 holds because
every arm runs against an unmodified official release. **C1 — the word the report's title rests
on — is the one place this chapter has to correct itself**: §8.3 said until 2026-09-04 that
*unmodified* was "counted rather than asserted" by a mechanical diff. **That diff does not exist**
(§7.28). What does is a read-only bind mount that makes modification impossible in the confined arm
and absent in the baseline arm, so C1 was **argued from the harness rather than counted**, and the
check was priced in §8.7. **It was then run (2026-09-06, §7.29): 75 tree comparisons, zero source
changes, zero diff lines, and C1 is counted** — bounded, per §7.29.2, to the run rather than the
project's history, because the corpus manifest pins `HEAD` and stored no content hash to compare
against. §2.8 was careful that the novelty is *"not the manifest, which is established
practice, but the retrofit"*, and the retrofit is what the zero of §8.2.2 measures.

**Contribution 3 — a quantified security/compatibility trade-off.** This is the one §2.8 called
*"most likely to survive scrutiny, because it is the one nobody else has data for"*, and it is
delivered on both halves — but the two halves are not equally strong and the chapter should not
present them as though they were.

| | What exists | Compared against |
|---|---|---|
| Compatibility half | 77 integrations, two corpora, both arms, cost **0** | the closest evaluation covers **three** integrations, two of them purpose-built |
| Security half | per-threat over two registers, five threats paired against an unconfined arm | prior work asserts confinement is desirable, or that overprivilege is prevalent, without reporting either quantity |

**The security half is a decomposition and not a rate, deliberately** (§7.4.2), so it does not
reduce to a number the way the compatibility half does. An attempt that *"succeeded and found
nothing"* is a stronger outcome than one that was denied — it means the capability was structurally
absent rather than merely refused — and any aggregate would erase that distinction. Readers wanting
one number will not find it, and §7.13.3 is the argument for why: reported alone, the confined
adversary run would have credited this framework with three controls it does not provide, because
`/etc/shadow` is root-only, nothing was listening on 8123, and `example.invalid` does not resolve.

## 8.4 What this project got wrong, and why the record of it is a result

### 8.4.1 Six of eight registered predictions were wrong, and none was revised

Predictions were registered before each measurement — §7.6 for five of them, and
`notes/ch7_uniform_prediction.md`, committed before the corpus was drawn, for three more. §7.23.7
carries the scorecard and §7.26.6 corrected its wording back to the register's own.

**The distinction worth reporting is not the count but which two held.** The two correct predictions
were the two *about the design*: that confinement's compatibility cost would be at or near zero,
and that a zero measured once would hold on a near-independent sample. Every wrong one was a
prediction about what the ecosystem or the kernel would do — that a package upstream bothers to
constrain must be installed (it is not), that the mediator would degrade in the tail before the
median (it saturates and degrades in both), that cgroup v2's page-cache charging would kill a
legitimate large-file reader (page cache is reclaimable and it never does), that the ecosystem's
tail would import worse than its head (it imports **eight points better**, and the prediction was
wrong in sign).

**So: the design behaved as designed; the world did not behave as assumed.** That is a more
defensible claim than a bare six-of-eight, and it is only available because the predictions were on
the record before the numbers. §7.1 argued that a pre-registered prediction is worth having
precisely because it can be wrong. Four of those five wrong predictions changed a conclusion in
this report, and the fifth (P6) changed what the coverage claim can say.

### 8.4.2 Every correction has been to a sentence, never to a measurement

Chapter 6 corrected Chapter 5; Chapter 7 corrected Chapter 6 five times and itself twice, across
two read-throughs. **Not one of those corrections has been to a measured figure.** 46/57/70/84%,
the 9.0/32.2/19.1 MB premiums, 31 of 37, the 0.7 MB noise floor, §6.3.2's 136.6-against-136.5 MB
replication, 96% of resolutions via `aiodns`, 2-of-2 canaries, 36-to-1 entities — all hold as first
printed. What was corrected was, every time, a *sentence standing next to* a measurement: a count
recited wrongly, an inference presented as an observation, a prediction paraphrased, a column that
could not be added up, a claim about a string the code had never produced.

This is now consistent across four chapters and it has a plain explanation, which is the reason it
belongs here rather than in a footnote:

> **A number in this project is produced by a harness that is itself tested. A sentence about a
> number is produced by an author writing at the end of a long day.** The measurements have a
> mechanism that catches their errors — a paired baseline, a second instrument, a self-test that
> fails when the finding it encodes stops being true. The prose has only a read-through.

Four specific mechanisms did the catching, a fifth is named below, and each is transferable to any
project of this shape.
**A paired baseline stopped three misattributions** — three attacks blocked in both arms and
therefore not this framework's doing; a multicast finding withdrawn when the integration turned out
broken either way; an opaque `ImportError` that looked exactly like a confinement failure and was
the integration's own defect. **Two instruments bounded one another**: an in-process recorder paired
with `strace` caught the same class of counting error twice — once an observed-egress figure
inflated twenty-threefold by attributing the platform's own connections to integrations, and once a
coverage figure understated by an order of magnitude by counting `AF_NETLINK` and `AF_UNIX`
operations as egress — and the second time the error was in the *cross-check* rather than in the
instrument it was checking. **A self-test that passes when the surprising thing is true**: `case_udp_is_not_pinned`
exists because connected UDP sockets were assumed peer-pinned and are not, and it passes when a
datagram is redirectable — so if a future kernel changes that, the suite fails and the design's
foundation is re-examined rather than quietly invalidated. And **recomputing a figure from the
recorded results rather than re-reading the sentence that quotes it**: two sections reported twelve
of 37 integrations declaring no components where a third reported eighteen, which reads as the
first disagreement between measurements in this report. Recomputed, both are right and count
different fields — declared components against declared-plus-transitive-closure — and only
returning to the results file could establish that (§7.26.6, finding 5).

**Two corrections went the other way, and they are what keep this section honest.** Building the
egress broker's adversary case found that `EgressBroker.open` read `allow_private` from the
sandbox's own request — a field the confined process composes. A hostile integration could have
granted itself the whole of T10's reach by writing one key into a message it already controlled,
while its manifest declared nothing but a public hostname. That was a defect in the artifact, not a
sentence about one; it was found by writing the attack rather than by reading the code, and it is
now regression-tested under exactly that attempt (§7.26.2).

The second is larger and it is the strongest single argument in this report for a fifth mechanism:
**run the real thing, not a faithful model of it.** Every egress result before §7.27 was produced
against integrations written by the author of the sandbox, and they all worked. The first real
community integration run confined against a real API failed immediately, on a platform helper the
synthetic subjects had no reason to call — and the design had been unusable for its target
population for as long as it had existed. A self-test cannot find this, because a self-test is
written by the same person and out of the same assumptions; a paired baseline cannot find it,
because both arms would have to reach the code that fails. Only the real integration finds it.

That is the honest ranking of the five mechanisms: a paired baseline stops misattribution, two
instruments bound each other, a self-test freezes a surprising fact, recomputation checks a
sentence against its source — **and running unmodified real code finds the things none of the four
were looking for.** It is also the most expensive, which is why it happened last and why §8.7's
future work is ordered the way it is.

## 8.5 The finding nobody was looking for

Two arms of the compatibility measurement produced a number neither was designed to produce.

```
    head-weighted corpus     baseline loads a median of 52 components   sandbox sets up  2
    uniform corpus           baseline has  53 available                 sandbox sets up  0   (max 7)
                             ── identical import-level compatibility in both ──
```

**Whatever the other fifty components are for, importing a community integration and bringing up
its entity platforms is not it.** **18 of the 37** head integrations declare no components at all,
and **26 of the 40** uniform ones — a median of one against a median of zero (§7.26.6, finding 5).
The gap *widens* from 52-against-2 to 53-against-0 as the integrations get simpler, and the
compatibility outcome does not move.

This bears on three things it was not measured for. It is direct evidence for §5.6's R2 decision —
stripping the platform to what an integration declares is not a compromise that costs
compatibility, and on this evidence it costs none. It sharpens §6.14.5's honesty cost, because the
sandbox carries 641 MB of packages no integration declared while carrying fifty fewer *components*,
and components are where capability lives. And it is the strongest available argument for §5.15.2's
L2 — a capability check inside the platform's own loader — because it says the surface such a check
would have to cover is far smaller than the platform's size suggests.

**What it does not say.** It is an import-and-platform-setup measurement. An integration that
*runs* may need components it does not need to load, and §7.17's five are the only integrations in
this report driven past setup. The finding is a bound on what loading requires, not on what
operating requires.

## 8.6 Limitations

### 8.6.1 The taxonomy, and why the sorting is the substance

§5.15.1 sorted the design's limits into **structural**, **chosen** and **inherited**, on the
grounds that a limitations section presenting all of them in one voice invites the reading that the
design has an unbounded number of holes. That sorting is kept and extended by one category the
evaluation generated: **limits of the measurement**, which are neither the design's nor anyone
else's to fix, but the next measurement's.

Only limits that no earlier section states appear below. §4.11's residual risks — six as drafted, **seven since R7** — §3.7's
non-goals, §5.15's three inherited limits and §7.9's validity threats stand as written.

### 8.6.2 Structural — and the correct response is to state them, not to add mechanism

R1 (over-declaration), R2 (abuse of declared authority) and R5 (exfiltration through a declared
host) are structural to confinement of this kind, rated High and retained in §4.11. Chapter 7 adds
measurement to two of them and neither measurement changes the rating.

**R5 is now measured rather than asserted, and the measurement makes the retention sharper.** Every
TLS wrap observed in §7.24's twelve integrations had `check_hostname` set. The mediator supplies a
descriptor and the handshake completes end to end between the integration and the remote host, so
**the mediator sees destination and never content, by construction rather than by policy.** T09's
Retained-structural rating in §4.10 is therefore not a concession made for want of effort; it is
what the mechanism is, and no amount of engineering *of this kind* changes it. Content control
would require payload inspection, which is a privacy problem in itself and defeated by the TLS the
measurement confirms is universal.

**R1's ceiling is measured, which narrows the honest statement of it.** §7.16.1 confirms that an
over-broad grant **is honoured** — an integration declaring `binary_sensor.*` reads bedroom
occupancy, and the clause pointer says so. What the test establishes is the shape of the ceiling
over-declaration cannot raise: `lock.*`, `*.temperature`, a bare `*`, a path grant enclosing the
configuration root, a path grant reaching `secrets.yaml` or `.storage/`, and an invented capability
are each **rejected at parse**, each naming the rule that rejected it. So R1 reads more precisely
as: *an author may declare more than they need within a fixed ceiling, and the ceiling contains
exactly the authority Chapter 4 rated Critical* — `lock.unlock`, `secrets.yaml`, and cross-domain
reach. That is smaller than "over-declaration is a residual risk" and it is more defensible.

### 8.6.3 The artifact's own limits — every one of these is fixable, and each has a price

| # | Limitation | Where measured | Why it is not fixed here |
|---|---|---|---|
| 1 | **The push loop does not exist.** Declared entities are mirrored once at sandbox construction, so an integration sees the value that existed when it was built | §6.11.2, §7.14.4 | It is the largest missing piece and it blocks two things: S3's subscription half is a refusal without a delivered stream, and the only latency path that could consume §7.20.1's 63× margin is unmeasurable without it |
| 2 | **The mediator acts on a stand-in, not a live Home Assistant** | §6.10.2, §6.11.2 | What crossed the boundary in §7.17 is real and carries its clause; what a live instance would do with those fifteen entities is untested. **What it costs is entity *identity*, not realism** — §6.10.2's prior-work finding is that the states API publishes without a registry row, and §5.6.1 measured 83% of the corpus publishing by the path that creates one. Priced in §8.7 #2 |
| 3 | **Dependency installation is unresolved**, so the third component of the three-part identity stays vestigial | §6.8.1, §6.11.2 | The identity is well-formed and attributed without it; resolved versions are what it is waiting on |
| 4 | **Disk means space, not I/O bandwidth.** A sandbox cannot exhaust space outside its scratch but it can saturate the device | §7.22.2 | The `io` controller is **present on the host and not delegated to a user manager** — `+io` to the delegated subtree fails with `ENOENT` — so an unprivileged supervisor cannot implement it at any effort. §5.7.4 chose unprivileged. **This is a live T16 vector, and §4.11 now carries it as R7** (entered 2026-09-04; §7.22.2 is where it was found) |
| 5 | **`/sandbox/data` is unbounded.** An integration can fill the user's disk through its own writable directory | §7.22.2 | The cap applies to the private `/tmp`'s tmpfs; bounding a bind-mounted host directory needs filesystem quotas, a privileged operation |
| 6 | **The cgroup kill destroys its own evidence.** The adversary dies before reporting what it attempted | §6.9.4, §7.11 | §6.4.6 chose `EPERM` over `KILL_PROCESS` for seccomp precisely so a refusal stays legible; the cgroup has no `EPERM` to offer. **The audit trail is weakest exactly where the control is strongest**, which is the sharpest form of R4 in this report |
| 7 | **The MAC key does not outlive the mediator.** Records from an earlier run stay hash-verifiable and are no longer MAC-verifiable by anyone | §6.8.4 | Persisting the key hands it to exactly the adversary it exists to stop — anyone who can write the log can read the key beside it. A position on a trade-off, not a defect |
| 8 | **The identity hash records what was *loaded*, not what *executed*.** An integration that fetches or generates code at runtime defeats it | §5.9.6, §5.12.1 | Inherited from the approach; it bounds T12's treatment, and T12 is also the one threat with no evidence (§7.26.5) |
| 9 | **A quarter of datagram integrations are unserved.** The UDP relay serves synchronous senders; asyncio `DatagramProtocol` transports — 4 of 15 measured — are not | §7.25.5 | Named at build time rather than found later. The relay's own reach is measured, not assumed |
| 10 | **The confined UDP round trip was never spawned**, and only one of §7.24.5's three network stacks has run confined. `udp_relay.py` is evaluated against the mediator's decision path, not from inside real namespaces; §7.27 spawned `aiohttp` + `async_get_clientsession`, which is the platform's own, and neither `urllib3`/`requests` nor a raw socket | §7.25.5, §7.27.7 | **Relayed UDP is procedural where handed-over TCP is structural**, and that asymmetry is not measured. §7.27 is the reason to rank this higher than it was ranked: the one stack that was actually spawned turned out to break, and the other two have had no such test |
| 11 | **The egress path is coupled to `aiodns`, and now to the shape of one platform helper.** 96% of resolutions bypass `getaddrinfo`, so the shim patches the platform's resolver stack by name — and §7.27.2 found a second dependency on the same line: `async_get_clientsession(hass)` instantiates Zeroconf to build that resolver, so the sandbox must offer a multicast join or no integration can construct an HTTP client | §7.24.2, §7.24.6, §7.27.2 | A working run today says nothing about a release that replaces `aiodns` or rearranges `aiohttp_client`. §4.12's review triggers already record that the platform moves underneath this model — **and §7.27 is the first measured instance of that risk being real rather than anticipated** |
| 12 | **mDNS discovery does not work in the sandbox, and now fails silently rather than loudly.** The multicast route added in §7.27.3 points at `lo`, so a join succeeds and discovers nothing | §7.27.3, §7.27.7 | The alternative was `ENODEV` at client-session construction, which broke every cloud-facing integration. Silence is the better failure and it is still a failure. §7.24.4's finding that no integration in that sample established a listener does **not** bound this, because that sample was recorded unconfined, where discovery worked |
| 13 | **The declaration is incomplete for packages *and* components.** 16% of the head corpus imports a package it never declared; **8% still does with the core set supplied**; `powercalc` needs a component (`network`) it does not declare | §6.13.3, §6.14.4, §7.17.4, §7.23.5 | The answer is §5.9.3's static analysis marked *derived*, not asking the author — priced in §8.7 |

**On item 13, one detail is worth more than the rate.** `aiofiles` has now blocked integrations in
the compatibility run, the end-to-end run and the egress-shape run — three independent occasions —
and `homeassistant/package_constraints.txt` pins it with the comment *"aiofiles keeps getting
downgraded by custom components"* and an issue reference. **That is the platform's own maintainers
documenting this exact problem in their own ecosystem**, which is independent corroboration of
§6.13.3's bound rather than this project's inference about it. And the three integrations affected
are not reachable by supplying more of what the platform has, because what they want is a package
the platform does not have either — a stock `pip install homeassistant` on 2026.8.3 does not
provide `aiofiles`, and neither does the `default_config` closure.

**One asymmetry to state plainly, because a reader who has absorbed §6.9.1 will otherwise read it
as a hole.** Every capability in this design denies by absence — that is S6 and the whole of
§5.6.2's structural denial. **`resources` cannot.** If an absent `resources` clause meant "no
limit", the integration that declares nothing would run unbounded, inverting default-deny for the
single requirement whose threat is an integration consuming everything. Absence therefore means
*the framework's* bound rather than *the integration's*, and a declaration can only be read as a
request to be bound **more** tightly than the default, never less. `resources` sits in a permissions
manifest despite granting nothing because **it is the one capability whose declaration is a
constraint on its declarer** (§7.22.3).

### 8.6.4 The evaluation's own limits

These belong to the next measurement rather than to the artifact.

- **The executed-end-to-end population is five**, a named set with its selection stated and no rate
  computed. The ceiling is 11 of 37, because 26 require a credential (§7.17.1), and it binds any
  confinement scheme equally — but it means the level that matters most has n=5.
- **PSS against declaration depth did not resolve.** Three points, three sandboxes each, and the
  series is non-monotonic — 136.3, 95.7, 115.8 MB — which is PSS's sensitivity to what happens to
  be shared at that moment rather than a curve. §6.3.2's budget of 26 stands as measured there; no
  trend is claimed (§7.20.3).
- **One figure in Chapter 5 was produced by a known-defective builder.**
  `experiments/r2_footprint/measure.py` still carries the pre-§6.3.3 recipe, which never fires
  `EVENT_HOMEASSISTANT_START`, and §5.6.3's 176/136 MB figures came from it. It is preserved so
  those published figures stay reproducible; the defect affects deferred callbacks rather than
  process size, so the figures are unlikely to move — **and unlikely is not measured** (§7.20.4).
- **The API-surface measurement was never re-run on a uniform corpus** (§8.3).
- **T12 was never evaluated and was never declared unevaluable** (§7.26.5). §7.11 should have
  carried it in advance if it was not going to be run.
- **One release, one host, one architecture, HACS only.** 2026.8.3, Python 3.14.7, aarch64,
  Raspberry Pi 5, 4 GB. `eufy_security` failing on a constant removed *in this very release*, and
  `lightwave2` failing on another in the uniform corpus, are live demonstrations that a
  compatibility figure has a shelf life.
- **A transcription error common to a results file and the report would survive both
  read-throughs**, because neither re-ran anything. §7.24.6's argument applies to the prose: two
  instruments catch what one misses, and for the prose there is currently one.

### 8.6.5 Inherited — the limits with an owner elsewhere

§5.15.3 named three and each stands: R3's unscoped credential, §5.7.5's kernel assumption, and
§5.7.4's absent memory controller. The evaluation adds a fourth of the same kind — **the `io`
controller's non-delegation** (item 4 above), which is §6.4.1's *present-but-not-permitted*
distinction found a second time, one layer deeper, inside a supervisor that is correctly placed.
No position on the host changes it; only privilege or a systemd unit override on the user manager
would, and §5.7.4 chose otherwise.

## 8.7 Future work, priced and ordered

Ordered by what each would settle rather than by effort, with the effort stated so the ordering can
be argued with. Every item is one change to one artifact; none is a wish. **§7.27 reordered this
list after it was first written** — running one real integration promoted the stack-coverage item
from nowhere to seventh, which is the ordering evidence is supposed to do to a plan.

| # | Work | What it settles | Cost |
|---|---|---|---|
| **1** | **The push loop** (§6.11.2) | S3's subscription half moves from a refusal to a demonstrated filter, and the one latency path that could consume §7.20.1's 63× margin becomes measurable. Both are currently stated gaps in the artifact rather than in the measurement | Days. It is the largest missing piece and the highest-value one |
| **2** | **The real Home Assistant component** (§6.10.2, §6.11.2) | **Limitation 2 of §8.6.3, and the largest of them that this list did not price until now.** Step 5 of the mediated call acts on an in-memory stand-in, so what a *live* instance does with a mediated write is untested — §7.14.4 and §7.17.6 each state this beside their own figure. What it would settle is **identity, not realism**: the spike's `registry_gap` finding — cited as prior work in §6.10.2 and deliberately not relied on — is that publishing over the states API produces states with no entity-registry row, no `unique_id`, no config entry and nothing surviving a restart, and §5.6.1 measured that **83% of community integrations publish through `async_add_entities`**, which is the path that produces the registry row and the state machine does not. Until it exists, the end-to-end arm speaks for the mediator's decision and not for what the platform then does with it | Days. The spike's `sandbox_bridge` is ~250 lines that load and execute nothing from any integration, and `00_METHOD.md` §5 permits reusing that code — but its *finding* is private knowledge under §2, so the registry claim has to be re-measured here rather than cited |
| **3** | **Static analysis for the derived manifest**, extended one level up (§6.14.4, §7.17.4) | The undeclared-package *and* undeclared-component bound — item 13 above, and the only measured compatibility cost in the whole report. `import aiofiles` is a top-level import and trivially detectable; **a component dependency is a name in the platform's own source, so the transitive closure is computable exactly rather than approximated**, which `core_requirements()` already does for `default_config`. A strictly larger analysis and a strictly easier one | Days. `--derived` alongside the author's manifest, with every added clause marked as derived per §5.9.3 |
| ~~**4**~~ | ~~**Count C1 instead of arguing it**~~ (§7.28) | ✅ **Done 2026-09-06 — §7.29.** `confine/integrity.py`, wired into both arms of `compat.py` rather than kept as a separate script, so every future compatibility run counts C1 by running at all. **37 trees baseline, 38 confined, zero source changes, zero diff lines.** Two departures from this row as priced: hashing *at fetch* proved impossible — the corpus manifest pins `HEAD` and stores no content hash, so the count covers a run and not the project's history (§7.29.2) — and the instrument reports an uncountable line delta as *unknown* rather than zero, after the first version returned a reassuring 0 by comparing the baseline tree against itself (§7.29.3, §6.4.5's failure mode for the fourth time) | **It was an hour**, and the hour was right |
| **5** | **T12's measurement** (§7.26.5) | The only threat in either register with no evidence. Set an integration up, change its manifest, spawn it again, show the second run is bounded by the second declaration and that the change is visible through `describe.py` before it takes effect | Hours. It was never scheduled, which is why the schedule's close-out did not catch it |
| **6** | **Re-run the API-surface parser on the uniform corpus** (§8.3) | Contribution 1's other half — what most *integrations* ask for, against what most *installations* run. §7.23 answered that question for compatibility and not for the API surface | **One run.** The script exists and the corpus is already fetched: the cheapest outstanding item in the report |
| **7** | **The other two network stacks, confined** (§7.24.5, §7.27.7) | `urllib3`/`requests` synchronously and a raw socket, each spawned in real namespaces against a real destination. **Promoted above the datagram work by §7.27's result**: the one stack that was actually spawned failed on a platform helper nobody had exercised, and the argument that the other two are fine is now exactly the argument that was wrong once | Days. `localtuya` and `midea_ac_lan` are the corpus's members, and both need a device or a credential — so this may need recorded fixtures |
| **8** | **asyncio datagram transports, and a confined UDP round trip** (§7.25.5) | The unserved quarter, and whether relayed UDP behaves in real namespaces as it does against the decision path. It would also let the procedural/structural asymmetry between UDP and TCP be measured rather than conceded | Days |
| **9** | **Filesystem quota for `/sandbox/data`** (§7.22.2) | Item 5 above. Needs privilege, so it also needs a decision about whether the unprivileged position of §5.7.4 admits a privileged installer step. `io.max` is *not* in this row — non-delegation is not a matter of effort | Small, plus a design decision that is not small |
| **10** | **The end-to-end arm at scale** | N2's second number as something other than a named set of five. Blocked on credentials for 26 of 37, so it needs either a cooperating vendor set or recorded request fixtures — the second is the tractable route and would change the measurement's character, which should be stated if it is taken | Weeks, and the honest framing is that this is a different project's measurement |
| **11** | **Off-box audit anchoring** (R4, §5.12.6) | The audit log's authority against whoever controls the machine, and item 7's key-lifetime trade-off. §5.12.6 declined to define a format because *"the moment this chapter specified a format for another machine to consume, the scope would have moved"* — **but the artifact already emits the record such a layer would consume**, which is a more useful piece of future work than an unevidenced suggestion | A different project. The contribution here is that its input already exists |
| **12** | **Re-run `r2_footprint` on the corrected builder; PSS with more sandboxes per point** (§7.20.3, §7.20.4) | Two measurement debts, neither load-bearing on any claim | Small |
| **13** | **L2 — enforcement inside the platform's own loader** (§5.15.2) | §5.15.2 states plainly that L2 is the better design on every axis but deployability, and that this project's most durable contribution to it may be the evidence it would need. A platform proposal must answer what confinement costs in compatibility, what the declaration should express, and what threats it closes. **Those answers do not depend on the L3 architecture that produced them, and §8.5's finding says the surface such a check must cover is far smaller than the platform's size suggests** | Not this project's to do, and the reason it is last rather than absent |

## 8.8 The single ask of the platform

Of the four residual High risks, one is not a property of confinement at all.

**R3 — Home Assistant issues no scoped credential.** There is no read-only variant and no
per-domain variant of a long-lived access token, so the mediator must hold full authority in order
to mediate at all, and compromise of the mediator is total compromise. §5.15.3 named this as the
single change that would most improve any confinement scheme for this platform, and §7.11 records
that this evaluation cannot assess it because it is upstream.

**What Chapter 7 adds is that the consequence is now measured rather than reasoned about.** §7.15.3
confirms the platform credential live in the mediator's process, reachable seven ways by the same
supported API — `gc.get_objects()` — that §2.4.1 used against an integration. The design moves that
credential out of reach of every confined integration and it cannot make the credential smaller.
One upstream change, to one artifact, would bound what a compromised mediator can do; and §4.12
already names scoped tokens as the review trigger that would change this model.

This is worth stating as an ask rather than as a limitation because it has an owner, a specific
form, and a measurement behind it.

## 8.9 What a reader should take from this

**The claim held.** Unmodified, pre-existing integrations were confined; the published attack that
forced the architecture was reproduced and defeated against a live credential; the 2021 file-theft
pattern that this ecosystem actually suffered succeeds unconfined and recovers nothing confined;
and the import-level compatibility cost across 77 integrations on two corpora, measured against an
unconfined baseline both times, is zero. On the hardware the requirements name, the mediator is 63×
clear of realistic demand with durability paid for on every decision.

**The last measurement taken was the one that mattered most, and it failed first.** Running a
single real community integration confined against its own real API found that the platform's own
HTTP helper could not be constructed inside the sandbox at all — so the egress design had been
unusable for the population it was built to serve, for as long as it had existed, behind a suite
of tests that all passed. Two lines fixed it, and `nordpool` then published the same electricity
price confined as unconfined. The fix is worth a paragraph; **the fact that nothing else in the
project could have found it is worth the chapter.**

**The claim is also smaller than it sounds, and the report says so in the same voice it says the
rest.** Compatibility is measured at import for 77 integrations and end-to-end for five, because 26
of 37 need a credential no measurement of any confinement scheme can produce. Two of eighteen
threats are partial, two are retained by decisions taken before the artifact existed, and one was
never evaluated. Three of the closest published model's eleven threats have no counterpart in this
register at all, where §4.14 accounted for one. What the design converts is invisible authority into declared, bounded and audited authority —
which is a smaller claim than "confinement makes integrations safe", and it is the claim the
evaluation is scoped to.

**And the thing that made the project defensible is not in the artifact.** Six of eight
pre-registered predictions were wrong, every one caught by a measurement and none revised
afterwards. A paired baseline stopped three misattributions that a traceback would have got wrong,
and every one of them would have charged the design *more* than it deserved — which is the
direction an author's own attributions tend to err in the opposite way. Two instruments caught the
same over-count twice. Superseded sections kept their text and gained a forward pointer, so a
reader can check what was believed before the number arrived rather than only what is believed now.

Across four chapters and two full read-throughs, **every correction has been to a sentence next to
a measurement, and none to a measurement.** That asymmetry is the most transferable result here.
The measurements had mechanisms that caught their errors. The prose had a read-through, twice, and
both times it found something — which is the argument for doing it a third time on the whole
report rather than an argument that it is now clean.
