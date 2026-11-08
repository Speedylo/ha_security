## Appendix [R] — Detailed Results

This appendix holds the detail behind Section 12: the full end-to-end table, the complete costs, the bridge's limits, what integrations ask of the platform and of the network, the threat-model accounting, and how the evaluation was checked. All figures come from the final rerun of 1 November 2026 unless stated otherwise.

### [R].1 The attacks

**Table [R].1**
*The four attacks in detail, unconfined and confined*

| Attack | Unconfined | Confined |
|---|---|---|
| The garbage-collector technique, aimed at another integration's live credential (Corno & Mannella, 2022) | Credential reached through 7 live objects | 8,942 objects examined, all the attacker's own; the credential alive in the mediator's process |
| The 2021 path-traversal pattern, aimed at two planted secrets (Home Assistant, 2021) | 2 of 2 secrets recovered | 0 of 2: the file does not exist inside the sandbox |
| Reading another process's environment variables | Contents read | Nothing to read |
| Reading the states of devices the integration was not granted | 36 of 36, including all 20 that reveal whether someone is at home | Only the 1 device that was declared; 0 of the 20 |

An absence carries no information on its own, because a broken test also returns nothing. In each row, the unconfined arm therefore shows the attack working on this device and release, which turns the confined result into a measured difference. The pairing also cut against the framework: three further attacks failed in both arms for reasons unrelated to confinement, such as a file readable only by the system administrator, and they are excluded from its results.

The wider threat model gives the same picture with stated exceptions. Sixteen of its nineteen threats are shown to be controlled. One is partial: the resource limits bound memory, processor time and disk space, but not disk bandwidth or the size of an integration's own data directory. Two are retained by decisions made before the evaluation, namely that the framework controls where an integration connects but not what it sends, and that it honours an over-broad permission the user has approved. Eight of the eleven threats in Corno and Mannella's (2022) model map onto the framework's controls, five of them without qualification, while the three availability threats have none. No single figure of threats controlled is reported, because such a figure would merge refused attempts, impossible ones and retained risks. The same care applies to commands: the mediator stops a command from being redirected, widened or given extra parameters, but it does not check the content of a permitted text value, so misuse of such a value is contained by confinement rather than prevented.

The security result is bounded by who carried out the attacks. All of them were written within the project, including the 39 attempts of the adversary suite and 4,864 malformed requests sent to the mediator, and none produced an escape. No independent tester has attacked the framework. A line-by-line reading of the code found a route out of the sandbox through a shared terminal that no automated test had detected, which suggests that attacks the builders did not anticipate may remain. Within that bound, the evidence supports Assertion A: the published techniques succeed without the framework and find nothing with it. The project's contribution here is a measured replacement of total, invisible authority with authority that is declared and confined. Whether that protection stops integrations from working is the question of Assertion B.

### [R].2 The fifteen integrations

**Table [R].2**
*The fifteen integrations run end to end*

| Integration | What it does | Confined result |
|---|---|---|
| `thermal_comfort` | Calculates comfort measures from temperature and humidity | Dew point 9.96 °C, as unconfined; all 15 devices published |
| `watchman` | Reports configuration that refers to missing devices | Two missing devices against one unconfined, because a device it was not granted does not exist in the sandbox; one once that device is declared |
| `adaptive_lighting` | Adjusts lights to the time of day | Commands brightness 89, as unconfined; with the service permission removed, no command reaches the platform |
| `powercalc` | Estimates the power use of unmetered devices | 8.06, 3.00 and 0.00 W, identical to unconfined |
| `scheduler` | Runs actions at set times | Light switched on at the scheduled second with brightness 200, as unconfined |
| `nordpool` | Electricity prices from an online service | Same price as unconfined (0.036) |
| `smhi_brandrisk` | Fire-risk forecasts from a weather institute | Same values as unconfined |
| `regensburg_transport` | Public-transport departures | Live departure one minute from the unconfined reading (21:02 against 21:03) |
| `dwd_weather` | Forecasts from a national weather service | Same forecast as unconfined; one undeclared host, `www.dwd.de`, refused |
| `pirateweather` | Weather from a service that requires an account key | Same reading (8.53 °C); the key never reached the mediator |
| `midea_ac_lan` | Controls air conditioners on the home network | Same result as unconfined, against a simulated device |
| `localtuya` | Controls smart plugs and similar devices locally | Finds the simulated device, as unconfined |
| `trakt_tv` | A television calendar from an online account | Renews its expired login token inside the sandbox and works |
| `alarmo` | A home alarm managed inside Home Assistant | Armed after its exit delay and disarmed, as unconfined |
| `waste_collection_schedule` | Rubbish-collection dates from a city's online service | Same collection date as unconfined |

All fifteen worked confined. The five that need no outside service were held to 45 predictions, of which 43 held; the two misses were one wrong prediction, made for both arms, that `scheduler`'s switch would end a run as `off` when it ends as `triggered`. The comparison of live values has a limit of its own. It asks that a value read confined equal one read unconfined from the same service minutes earlier, so it cannot tell a wrong value from a service that has moved. `regensburg_transport` missed it by one minute of a real-time departure, as `pirateweather` did by 0.02 °C on the first rerun, and in both cases the integration's value did cross the boundary through the mediator. Each integration that uses the network was also run with its network permission removed, and its requests were then refused and recorded. This third arm shows that the working runs reached their services through the declared permission and not around it.

### [R].3 The bridge

The runs above delivered devices to a simplified stand-in that accepts every kind of device, so they do not show what a household sees. The fifteen were therefore run once more against a real Home Assistant installation. All 65 devices they published appeared there, each as a device of its own kind and in the state the integration had published, and all 36 checks passed. That result depends on the bridge, the component that represents a confined integration's devices in the household's installation. After the interim report, the bridge was extended from 11 kinds of device to 29, and it now covers 36 of the 37 head-weighted integrations by kind, or 247 of the 248 device kinds they provide between them. The one left is the older notification interface of `alexa_media`. The commands, questions and answers of the 29 kinds passed all their checks, 268 offline, 49 for questions and 194 against the real installation.

Coverage by kind is not the same as full function, and the limits are stated rather than absorbed into the count. Cameras are confined to still pictures of up to 512 KiB, so `frigate`, `eufy_security` and `tapo_control` lose live video, which is their main use, and `bambu_lab`'s pictures were not checked. A lock's code format is supplied by the integration and is applied without confinement in the household's installation, a vacuum's room cleaning is refused, and media that an integration fetches for itself does not pass through the bridge. A display check was run in a real browser, in which a confined integration published hostile markup in a state, an attribute and a name. The markup appeared as plain text, nothing ran, and the browser requested no picture from a server the integration had chosen. This check covers the device pages it opened; links were not clicked, and history pages were not part of the test installation.

### [R].4 What integrations ask of the network and the platform

Network use divides the head-weighted sample in a way that follows from the design. Of the 37, 30 (81%) reach something outside the sandbox. Fifteen reach cloud services, which the egress proxy serves directly, and fifteen reach devices on the home network, which require a separate and explicit permission, because reaching the home network also means reaching the router and every other device in the house. A household is therefore asked to read the second kind of permission with more care.

Working integrations also show what a permission system has to cover. Following the method of Li et al. (2025), the source code of the 144 most-installed community integrations, and of the 40 in the uniform sample, was read automatically for each part of the platform it uses (Table [R].3). At 40 integrations, one integration is 2.5 points, so only differences of about ten points or more are read as findings.

**Table [R].3**
*Parts of the platform used by community integrations*

| Part of the platform | 144 most-installed | 40 drawn at random |
|---|---|---|
| Its own configuration entry | 94% | 93% |
| The platform's shared data store | 86% | 80% |
| The event bus, on which every change in the house is announced | 49% | 18% |
| Calls to services, the actions that operate devices | 65% | 38% |
| Calls to another integration's services | 22% | 13% |

The parts an integration needs merely to exist are used about equally in both samples. The parts that widen its reach are not: use of the event bus falls by 31 points in the random sample, and use of services by 27. A study of popular integrations alone would therefore overstate how much of the platform a typical integration touches. The measurement also decides how finely permissions are granted. Almost every integration manages its own configuration entry, but few act on other integrations, so permission is granted per action, and calls to another integration's services are refused unless declared, which affects about one integration in eight in the random sample.

### [R].5 The full costs

**Table [R].4**
*The cost of confinement on the reference device, all figures*

| Quantity | Reported figure | Second final rerun |
|---|---|---|
| Memory per sandbox, no platform components | 56.5 MB | 59.1 MB |
| Memory per sandbox, two components | 92.3 MB | 95.2 MB |
| Memory per sandbox, all ten components measured | 135.6 MB | 141.2 MB |
| Delay added by the mediator to one request | 43 µs | 42.1 µs |
| The same, 26 sandboxes saturating the mediator | 800 µs | 802 µs |
| Writing the decision record to disk, before the action | 3.67 ms | 3.69 ms |
| Mediator cost of one change delivered to a sandbox | 10.9 µs | 11.4 µs |
| A change in the house reaching a confined integration | 0.5–0.9 ms | 0.49 ms |
| A household command reaching the integration | 11–16 ms | 12.5 ms |
| A flooding sandbox, from first request to cut-off | 0.81 s | 0.82 s |
| Start-up to first report, `powercalc`, compiled at installation | 1.87 s | 1.89 s |

Memory decides how many integrations can be confined. Memory is counted as proportional set size, which divides each shared page among the processes that use it, because most of a sandbox consists of pages the kernel shares between sandboxes. If 60% of the device's memory is set aside for sandboxes, it holds between 17 sandboxes, when each integration uses all ten platform components, and 43, when it uses none, or 41 on the rerun's figure. Even the heaviest case is four times the average installation's need. The margin has two limits: the platform publishes only the average number of integrations per installation, so the share of installations that exceed the budget is unknown, and memory was measured with the integrations at rest.

Delay is not a constraint either. Writing each decision to disk before acting is the slowest step, roughly 85 times the cost of the mediation itself, and it limits the mediator to about 269 decisions per second. A generous estimate of real demand, 26 sandboxes each making five requests every thirty seconds, is about four requests per second, so the mediator runs about sixty times clear of it. Under saturation the delay rises to about 800 µs, because the mediator serves sandboxes in turn, but real integrations poll rather than send back to back.

The delays a household would notice are small. A change reaches a confined integration in well under a millisecond and writes nothing to disk once the subscription has been recorded. That median moves between runs without an established cause (findings F46 and F62), so it is best read as a range. A command reaches the integration in between one and two hundredths of a second. A sandbox that floods the mediator is cut off within a second while its neighbours continue to be served. The rate of change in a busy home and a sandbox's own cost of applying each change remain unmeasured.

### [R].6 How the evaluation was checked

The evaluation fails on its own terms if it reports a requirement as passed without demonstrating it, or reports an aggregate that conceals a breakdown it possesses. This falsifier fired twice during development, and both times the fault was found by reading the report as a whole rather than by any test. A requirement was reported as verified two months before the comparison that supports it existed, and a promised scoring of the security results was missing until a read-through supplied it. These two failures motivated a verification campaign designed to detect a third by method rather than by chance.

Before the engineering cut-off, every claim in the report was registered with its evidence and a pass criterion fixed in advance. Of the 153 claims registered, 119 were verified as stated, 27 hold only in a narrower form, 5 rest on argument rather than measurement, and 2 were withdrawn. This section states each claim in the form the register supports. The register only checks claims against evidence, however, so other methods looked for faults the evidence itself might hide (Table [R].5).

**Table [R].5**
*What each verification method found*

| Method | Principal findings | Result at the second final rerun |
|---|---|---|
| Re-measurement on fixed code | The mediation delay was 43 µs, not the 31.5 µs first stated (F17) | Every figure inside its criterion (Table [R].4) |
| Re-derivation of headline figures from raw records | A stated worst-case delay had no record behind it (F23) | 39 of 40 equal; the other was the abstract's outdated suite count |
| Fault injection | A full disk left the audit record unverifiable (F28); losing the platform left no recovery (F29) | 11 of 11 on both hosts |
| Security review and fuzzing | A sandbox could inherit the supervisor's terminal (F34, Critical); malformed requests could stop the mediator (F33) | 4,864 requests, no escape |
| Deliberate defects (mutation testing) | Three defects survived every suite at first; the supervisor ran in no suite (F48) | 90 of 92 caught; the other two change no behaviour, so no test could detect them. All 35 suites pass, twice |
| Reproduction from a fresh copy | No reproduction guide existed (F18) | Guide written and followed from a fresh copy; not yet on a freshly installed device |
| Running real integrations against a real installation | The stand-in hid how few kinds the bridge covered (F64); a picture link could pass the egress allowlist through the household's browser (F71) | 36 of 36 |

The project recorded 71 findings, and Appendix F lists them all. The verification campaign found 53, one of them critical. Ten followed the cut-off, among them a sandbox that could start without the user's approval (F57) and a confined command that lost its target (F54). Eight more came from extending the end-to-end runs and the bridge. None changed the verdict on Assertions A, B or C. One finding remains open (F18), one is retained as a residual risk (F11) and two are stated as limitations (F53, F63). Most of the campaign's major findings concerned statements in the report that were wrong or unsupported, or the framework's behaviour when something around it fails, which no earlier test had exercised.

The deliberate defects carry the most general lesson, because a test suite that cannot fail provides no evidence. The program that exercised the supervisor reported success whatever happened, so every regression run had recorded a pass that could not have been a failure. Real integrations taught the same lesson about test subjects. The first real cloud integration could not construct a web client inside the sandbox, although every suite passed, because the purpose-built subjects never reached that code. A paired comparison has a similar blind spot: two integrations were first misreported, in opposite directions, because both arms ran on a test installation that loaded a platform component only as a side effect. A pairing controls for what the arms do not share, and it cannot control for what they share.

The evaluation was finally repeated in full, twice. Both final reruns were carried out from a fresh clone of a tagged version under predictions committed beforehand, the second at the frozen code of 1 November 2026. Every step of the second met its criterion. It had one deviation, when the device's disk filled during the deliberate-defect run and the affected defects were run again.

The results of the evaluation bound what it shows. The deliberate defects were chosen by hand, so they show that each tested point is guarded, not that every point is. The reproduction guide has not yet been followed on a freshly installed device. Within those bounds, the project's contribution is an evaluation whose own errors were looked for by method and reported.
