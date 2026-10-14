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

The security result is bounded by who attacked the framework. Every attack was written within the project: the adversary suite's 39 attempts, the unconfined arms, deliberate defects introduced to test the test suites, a fuzzer run against the mediator, and a line-by-line review of the enforcement code. An independent adversary was planned and then dropped, because the framework was built with AI assistance and neither the author nor the assistant would have been independent of its design. The limitation is real. The code review found that a sandbox could inherit the supervisor's terminal as its controlling terminal, a route across every isolation layer at once that no test suite had detected. It was removed and is now tested from inside the sandbox. Assertion A is therefore demonstrated against the published techniques that motivated the design, and none of its falsifier's three conditions was met. The review's finding nevertheless suggests that attacks the builders did not anticipate may remain. Whether this protection costs integrations their ability to run is the question of Assertion B.

## 12.2 Assertion B: confinement is compatible

The falsifier for this assertion concerns where incompatibility comes from. Assertion B fails if the unconfined arm shows that most of the confined shortfall is caused by the design, that is, if the unconfined arm passes substantially all of the head-weighted corpus while the confined arm does not. The opposite occurred, on two corpora that share only two of their members, as Table 12.2 shows.

**Table 12.2 — Import-level compatibility, confined and unconfined, on Home Assistant 2026.8.3**

| Corpus | Integrations | Unconfined | Confined | Failures caused by confinement |
|---|---|---|---|---|
| Head-weighted, by install count | 37 | 31 (84%) | 31 (84%) | 0 |
| Uniform draw from the community catalogue | 40 | 37 (92%) | 37 (92%) | 0 |

Confinement costs nothing in import-level compatibility on either corpus. Across 77 measurements of 75 integrations, the two arms failed on the same integrations, and in the re-run on the corrected platform instance every failing integration gave the same error message in both arms, byte for byte (Appendix D). No integration passed unconfined and failed confined. The 84% figure is therefore not a statement about confinement: it is the fraction of the most-installed community integrations that import cleanly on this platform release at all, a joint property of the corpus and the release that confinement does not change. The uniform corpus sharpens this reading. It was predicted to perform 10 to 30 points worse than the head-weighted corpus, on the reasoning that less popular integrations are less maintained, and it performed 8 points better. A typical integration in the uniform corpus declares no platform components and no packages, whereas the head-weighted failures were mostly missing packages and components, so an integration that asks for less has less to fail on. Compatibility therefore tracks how much of the platform an integration reaches for, rather than whether it is confined. Importing, however, is not the same as working.

Thirteen integrations were therefore executed end to end, each through its own unmodified setup flow, and all thirteen load confined. Table 12.3 gives, for each one, what it does, what its run exercised, and what the confined arm produced. They form a named set rather than a sample, because the ceiling on such measurements lies in the ecosystem: 26 of the 37 head-weighted integrations require an account credential or a device address before their own setup can complete, and the unconfined arm meets the same limit.

**Table 12.3 — The thirteen integrations executed end to end**

| Integration | What it does | What the run exercised | Result, confined |
|---|---|---|---|
| `thermal_comfort` | Derives comfort measures from temperature and humidity sensors | Reads two declared sensors through the mediator, computes, publishes its own entities | Dew point 9.96 °C from 21.4 °C at 48% relative humidity, which is physically correct; all 15 entities published |
| `watchman` | Reports entities and actions that the configuration references but that do not exist | Scans a planted configuration naming a granted entity, an existing entity it was not granted, a non-existent entity and a non-existent action | Two missing entities and one missing action, against one and one unconfined: the entity it was not granted does not exist inside the sandbox. With both entities declared, one and one, as unconfined |
| `adaptive_lighting` | Adjusts the brightness and colour of lights through the day | A light assigned through its options flow, then its own adaptation to the sun's position | Commands brightness 38 from its computed 15.05%, against 39 from 15.16% unconfined half a minute apart; with the service clause withheld, no command reaches the platform |
| `powercalc` | Estimates the power consumption of devices that have no meter | Four-step setup flow in linear mode, then the lamp dimmed and switched off | 8.06, 3.00 and 0.00 W, as its own formula gives and identical to unconfined; without the subscription clause the estimate stays at 8.06 W |
| `scheduler` | Runs actions at scheduled times | A schedule added through its own service, to turn on a light at the next minute with a given brightness | Turns the light on at the scheduled second with brightness 200, as unconfined. The first run lost the command's target, a framework defect since fixed (F54) |
| `nordpool` | Electricity spot prices from the Nord Pool API | Polls the API over `aiohttp` through the mediator | Same price as unconfined (0.033) |
| `smhi_brandrisk` | Fire-risk forecasts from the Swedish meteorological institute | Polls two hosts over `aiohttp`; a further arm withholds one host | Same three values as unconfined |
| `regensburg_transport` | Public-transport departures for a chosen stop | Searches for the stop with `requests` during setup, then polls with `aiohttp` | 16:05 against 16:04 unconfined, a live value read a minute apart |
| `dwd_weather` | Forecasts and measurements from the German weather service | Polls over `httpx` | Same forecast issue time and measurement time as unconfined |
| `pirateweather` | Weather forecasts from a keyed commercial API | Validates a real account key in its own setup, then polls with it | 17.6 °C against 17.62 °C unconfined; the key never reaches the mediator |
| `midea_ac_lan` | Controls air conditioners on the home network | Discovers the device over UDP, then connects over TCP, against a simulated air conditioner that logged every packet | Same climate entity as unconfined; the device saw traffic only from the mediator's host |
| `localtuya` | Local control of Tuya devices | Discovers devices through asyncio datagram endpoints, against a simulated device broadcasting once a second | Discovers the device as it does unconfined |
| `trakt_tv` | A television calendar from a Trakt account | Refreshes an expired OAuth token inside the sandbox, then polls | Refreshes, loads and publishes; the new token exists only in the sandbox |

Every row of Table 12.3 now reports a value that was predicted before its run and checked against the integration's own behaviour. The first runs of `watchman`, `adaptive_lighting`, `powercalc` and `scheduler` showed only that setup completed and that entities crossed the boundary, so a later retest gave each a stimulus and the value its own code implies, in both arms, and 42 of its 45 predictions held. Two of the three that failed concerned `scheduler`'s switch, which ends a single run as `triggered` rather than `off` in both arms, so the prediction misread the integration rather than the boundary. The third was a defect in the framework. Confined, `scheduler`'s command reached the platform without its target, because the bridge dropped a target given as a list, and the decision record named no device for any service call, whatever its form. Both were fixed after the cut-off, with a test that failed before the fix, and the table reports the corrected result. `watchman` shows a difference between the arms that is correct rather than a fault: confined, it reports an entity it was not granted as missing, because inside the sandbox that entity does not exist, and it agrees with the unconfined arm once the entity is declared. The thirteen are therefore evidence of working confined integrations in every case, within the stimuli each run applied.

Each network-facing integration in Table 12.3 was also run with its network clause removed, and in every case the requests were refused, each refusal recorded with the clause that would have permitted it. That third arm is what makes the second evidence of mediation: it shows that the confined integration reached its service through the declaration, not around it. The table nevertheless understates what these runs contributed, because their most important results were the defects they exposed.

Running real integrations exposed defects that the purpose-built test subjects had concealed. The platform's integration quality rules recommend that an integration obtain its HTTP client through the shared helper `async_get_clientsession` [32]. In the platform release under test, that helper constructs its DNS resolver through Zeroconf, which joins a multicast group on start-up. A freshly created network namespace provides a loopback interface without multicast enabled, so the join failed and `nordpool`, the first real integration run against a real API, could not construct an HTTP client at all. The earlier test subjects had opened a bare client session and so bypassed the code path that ordinary integrations use. Until this was found, the egress design did not work for the 41% of the corpus it was built to serve, while every test suite passed. Enabling multicast on the sandbox's loopback interface, with a multicast route to that interface alone, corrected the fault without granting any route out of the sandbox. A test subject is evidence only for the code paths it exercises, and the same lesson applies to the evaluation's own instruments.

A paired comparison controls for everything the two arms do not share, and it cannot control for what they share. Two of the five platform-only integrations were first reported wrongly, in opposite directions, because both arms ran on a test instance that loaded a platform component only as a side effect. `powercalc` was charged to confinement because only the confined arm lacked that component, and `scheduler` was charged to the platform because both arms failed in the same way. On a corrected instance, both load in both arms, and the measured cost of confinement across the five fell from one integration to none. The correction changed a conclusion in each direction, which suggests that further defects of this kind may remain in any instrument shared by both arms. The final result concerns the network itself.

The corpus's need for the network divides into two halves that require different capabilities. Of the 37 head-weighted integrations, 30 (81%) declare that they reach something outside the sandbox. Fifteen (41%) reach cloud services on the internet, which the egress proxy serves directly. The other fifteen (41%) reach devices on the home network, which the design serves only behind a separate, explicit permission, because reaching the home network also means reaching the router's administration page and every other device in the house. For TCP, that permission was at first specified but not implemented, so these integrations failed closed whatever they declared; it was built later in the project, and `midea_ac_lan` in Table 12.3 measures the implemented path. Building the egress proxy therefore made 41% of the corpus workable directly, not 81%, and placed the other 41% behind a declaration that a user is meant to read with more care. This division is a property of the design and not a defect of the implementation.

Assertion B holds in a precise form. Confinement caused no import-level failure across 75 integrations on two corpora and no failure among the thirteen executed end to end, nine of which produced checkable values, and the falsifier did not fire. This is a narrower statement than "confinement is free": it rests on two corpora and a named set, and on one platform release, and the defects found along the way show that such measurements keep finding faults that passing suites conceal. Whether the protection of Section 12.1 and the compatibility shown here can be afforded on the reference device is the question of Assertion C.

## 12.3 Assertion C: confinement is affordable

The falsifier for this assertion concerns the reference device, a Raspberry Pi 5 with 4 GB of memory. Assertion C fails if the cost of each sandbox reduces the number the device can hold below the mean number of community integrations an installation runs, 4.02 according to the platform's public telemetry, or if mediation at realistic numbers of sandboxes changes what the platform can do. Table 12.4 gives the costs that decide both conditions. Each figure was measured during development and then re-measured in five passes during the verification campaign, on frozen code.

**Table 12.4 — The cost of confinement on the reference device**

| Quantity | Figure | Range across five verification passes |
|---|---|---|
| Memory per sandbox (proportional set size), no platform components | 56.5 MB | 58.6–58.8 MB |
| Memory per sandbox, two components (`http`, `websocket_api`) | 92.3 MB | not re-measured |
| Memory per sandbox, all ten components | 135.6 MB | 141 MB in every pass |
| Mediation latency, one sandbox (median) | 43 µs | 41.2–43.4 µs |
| Mediation latency, 26 sandboxes saturating the mediator (median) | 800 µs | 794–814 µs |
| Durable audit record, written to disk before the action | 3.67 ms | 3.62–3.69 ms |
| Mediator cost of one state change pushed to a sandbox | 10.9 µs | 11.3–11.5 µs |
| A change in Home Assistant reaching the sandbox (median) | 0.71 ms | 0.71–0.93 ms |
| A user's command reaching the integration's code | 11–16 ms | 11.1–15.7 ms |
| A flooding sandbox, from first request to cut-off | 0.81 s | 0.807–0.818 s |
| Start-up to first report, `powercalc`, with bytecode compiled at installation | 1.87 s | 1.87–1.94 s |

Memory is the cost that decides how many integrations can be confined, and the device holds several times the number a typical installation needs. Memory is measured as proportional set size, which divides each shared page among the processes that map it, because most of a sandbox consists of interpreter and library pages that the kernel shares between sandboxes; resident size counts those pages once per process, and in the first measurement it overstated the cost of six sandboxes by 126 MB. Taking 60% of the device's 4 GB as the share available to sandboxes, the budget ranges from 43 sandboxes when a sandbox sets up no platform components (41 on the verification passes' figure) to 17 when it sets up all ten, with 26 for a sandbox that sets up the two web components `http` and `websocket_api`. Even the heaviest profile holds four times the mean of 4.02. This margin is comfortable but bounded in two ways: the telemetry publishes a mean, not the spread across installations, so some installations certainly run more than four integrations and the data cannot say how many exceed the budget; and the sandboxes were measured at rest. The mediator is the second resource every sandbox shares.

The mediator handles about sixty times the realistic demand, and the durable audit record, not the mediation itself, sets that limit. Writing a record to disk before each action takes 3.67 ms, roughly 85 times the 43 µs the mediated request costs, so the mediator can decide about 269 requests per second. A generous estimate of realistic demand, 26 sandboxes each making five mediated requests per thirty-second polling interval, is 4.33 requests per second, which leaves a headroom of 62 times. An earlier estimate that left out the audit write put the headroom at about 11,000 times; the figure quoted here includes it. The mediator is therefore comfortably, not unboundedly, clear of demand. Its latency under load shows why the remaining margin is enough.

Mediation latency grows with the number of sandboxes because the mediator serves them in turn, and it stays below a millisecond at the full budget. With 26 sandboxes sending requests back to back, the median rises to about 800 µs while aggregate throughput stays near 30,000 requests per second from 2 sandboxes to 26, the signature of a saturated serial server rather than of a design that degrades with scale. Real integrations poll instead of sending back to back, so at realistic load the queue is empty and each request costs the one-sandbox figure. That figure was first published as 31.5 µs. Re-measured during verification it was 43 µs, and measuring every intermediate version of the code traced the increase to two features the design depends on: passing connected sockets to sandboxes for egress, and the push loop that delivers state changes. The figure was corrected rather than the features removed. The remaining rows of Table 12.4 concern the paths a household experiences directly.

The paths a household experiences are measured in milliseconds, and the push path draws almost nothing from the mediator's capacity. A subscription to state changes is decided and recorded once, after which each delivered change costs the mediator 10.9 µs and writes nothing to disk. A change in Home Assistant reaches a confined integration in 0.71 ms at the median, and a user's command reaches the integration's code in 11 to 16 ms. A sandbox that floods the mediator with refused requests is cut off within a second, while its neighbours continue to be served, and a confined `powercalc` starts and reports in 1.9 s when its bytecode is compiled at installation. These results extend Assertion C from polling to push delivery, although the rate of change in a busy home, and a sandbox's own cost of applying each change, remain unmeasured.

Assertion C holds, and neither condition of its falsifier was met: the device holds at least 17 sandboxes against a mean need of about four, and mediation at realistic load costs tens of microseconds per request. The assertion is bounded by the statistic available, a mean rather than a distribution, and by measurement at rest. The three assertions about the framework have now been answered; the fourth falsifier asks whether the evaluation that answered them can be trusted.

## 12.4 The evaluation tested against itself

The fourth falsifier concerns the evaluation rather than the framework. It holds that the evaluation fails on its own terms if it reports a requirement as passed without demonstrating it, or reports an aggregate that conceals a breakdown it possesses. This falsifier fired twice during development, and both times the fault was found by reading the report as a whole rather than by any test. The requirement that integrations run unmodified was reported as verified mechanically before any comparison of source trees existed; when the comparison was run, 75 tree comparisons found no change, but the report had been wrong for two months. And the scoring of the security results against both threat registers, promised in the evaluation's design, was missing until a read-through supplied it. These two failures motivated a verification campaign before the engineering cut-off, designed so that a third would be detected by the method rather than by chance.

Before the cut-off, every claim in the report was registered with its evidence, the version of the code it was measured on, and a pass criterion fixed before it was re-run. All measurements were then repeated on one frozen version of the code. Of the 153 claims registered, 119 were verified as stated, 27 hold only in a narrower form, 5 rest on argument rather than measurement, and 2 were withdrawn. This report states each claim in the form the register supports, which is why some results in this section are worded as suggestions rather than demonstrations. The register, however, only checks claims against evidence; Table 12.5 summarises the methods that looked for faults the evidence itself might hide.

**Table 12.5 — What each verification method found**

| Method | Principal findings | Outcome |
|---|---|---|
| Re-measurement on frozen code | 12 of 13 timing and memory figures within criterion; mediation latency 43 µs, not the 31.5 µs published (F17) | Figure corrected; increase traced to two features |
| Re-derivation of 39 headline figures from raw records | A stated worst-case push latency had no record behind it (F23) | Corrected to the recorded range |
| Fault injection | A full disk left the audit log permanently unverifiable (F28); a killed supervisor left an orphaned sandbox (F30); a restarted mediator broke the log's hash chain (F31); losing Home Assistant left no recovery (F29) | All four fixed and retested |
| Security review: line-by-line reading and fuzzing with 4,864 malformed requests | A sandbox could inherit the supervisor's terminal (F34, Critical); 26 malformed requests could stop the mediator for every sandbox (F33); a manifest could loosen its own resource bound (F32) | Each fixed with a test that failed before the fix |
| Mutation testing and branch coverage | Three deliberate defects survived every suite at first (M16, M18c, M31); the supervisor ran in no suite (F48); nine security branches had no test (F49) | Tests added; 39 of 40 defects caught, 1 equivalent |
| Reproduction from a fresh copy, and acceptance by hand | No reproduction guide (F18); the corpora could not be rebuilt (F21); restarting Home Assistant from its interface stopped it permanently (F42) | Guide written, corpora pinned, F42 fixed; F18 open until the guide is followed on a freshly installed device |

The campaign recorded 53 findings, one of them critical, and none changed the verdict on Assertions A, B or C. Twelve were rated Major, four between Minor and Major, 32 Minor, and four were notes or requests to re-measure. One remains open (F18), one is retained as a residual risk (F11) and one is stated as a limitation (F53); the rest are resolved. A functional retest after the cut-off added three more, all resolved: the framework defect in Section 12.2 that left a confined command without its target (F54, Major), and two faults in the evaluation's own unconfined arm (F55, F56, Minor). The critical finding was an isolation defect, fixed in code and now tested from inside the sandbox. The major findings fall into three groups: six were statements in the report that were wrong or unsupported, four concerned the framework's behaviour when something around it fails, which no earlier test had exercised, and two concerned whether an examiner could reproduce the work. The findings also qualify an earlier record of this project, which held that every correction had been to a sentence and never to a measured figure. Two findings concerned figures: one had become stale because the code changed after it was measured, and one had no record behind it. Both are corrected, and the earlier record is restated accordingly. The mutation results carry the most general lesson.

A test suite that cannot fail provides no evidence, and deliberate defects showed where the suites could not fail. The program that exercised the supervisor reported success whatever happened, so every regression run since the refusal-flood work had recorded a pass that could not have been a failure. One defect, which removed the supervisor's ability to stop a flooding sandbox, survived because the test integration stopped by itself once its channel closed; the supervisor's own action was tested only where another mechanism had already done its job. A second test integration that does not stop now exercises it. Each of the 40 deliberate defects is now caught by the check written for it, except one that is equivalent to the original code on the interpreter in use. Section 13 returns to this as a lesson about method.

The fourth falsifier fired twice before the campaign, and the campaign is the evidence that the evaluation can now detect such failures by method. Its results bound what it shows. The deliberate defects were chosen by hand, so they show that each tested point is guarded, not that every point is; an automated mutation run that would measure the rest was not performed. No independent adversary attacked the framework, as Section 12.1 records. And the reproduction guide has been followed from a fresh copy of the code but not yet on a freshly installed device.

## 12.5 Interpretation

The central claim holds within stated bounds. Confinement defeats the published attack techniques that motivated the design, causes no import-level failure across 75 integrations on two corpora and no failure among the thirteen executed end to end, and leaves the mediator about sixty times clear of realistic demand on a device with 4 GB of memory. The falsifiers for Assertions A, B and C did not fire. The evaluation's own falsifier fired twice during development, and the verification campaign found six further statements in the report that were wrong or unsupported; all were corrected before the cut-off, and all are reported rather than absorbed. What the framework changes is the nature of an integration's authority: authority that was previously total and invisible becomes declared before installation, bounded while the integration runs, and recorded each time it is exercised.

Each assertion carries a bound that the results do not remove. The security result is demonstrated against published techniques and attacks written within the project, and no independent adversary has tested it. The compatibility result is complete at import level but functionally checked for nine integrations, a named set limited by the credentials that most integrations require. The affordability result rests on a mean number of integrations per installation, because the public telemetry offers no distribution, and on memory measured at rest. All three were measured on a single release of Home Assistant, 2026.8.3, and an integration ecosystem that changes with every release may move any of them.

These bounds mark the edges of what was measured rather than defects in what was found, and each corresponds to work that would extend it. Section 14 sets out that work and its cost, beginning with an independent adversary and a functional retest of the integrations whose runs showed setup only.

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
