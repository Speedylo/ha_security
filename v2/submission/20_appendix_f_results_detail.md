## Appendix F — Detailed results

This appendix holds the detail behind Section 12: two facts about the attacks, the full end-to-end table, the bridge's limits, what integrations ask of the platform and of the network, the complete costs, and what each method of checking the evaluation found. All figures come from the final rerun of 1 November 2026 unless stated otherwise.

### F.1 The attacks

Section 12.1 gives the four attacks, and Appendix C gives the verdict on every threat. Two facts complete them. Beyond the 39 attempts of the adversary suite, 4,864 malformed requests were sent to the mediator, and none produced an escape. Six further attempts, such as reading a file only the system administrator can read or resolving a name that does not exist, failed in both arms for reasons unrelated to confinement, so the framework is not credited with stopping them. The mediator also stops a command from being redirected, widened or given extra parameters, but it does not check the content of a permitted text value, so misuse of such a value is contained by confinement rather than prevented.

### F.2 The fifteen integrations

**Table F.1**
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

### F.3 The bridge

Coverage by kind is not the same as full function, and the limits are stated rather than absorbed into the count. Cameras are confined to still pictures of up to 512 KiB, so `frigate`, `eufy_security` and `tapo_control` lose live video, which is their main use, and `bambu_lab`'s pictures were not checked. A lock's code format is supplied by the integration and is applied without confinement in the household's installation, a vacuum's room cleaning is refused, and media that an integration fetches for itself does not pass through the bridge. A display check was run in a real browser, in which a confined integration published hostile markup in a state, an attribute and a name. The markup appeared as plain text, nothing ran, and the browser requested no picture from a server the integration had chosen. This check covers the device pages it opened; links were not clicked, and history pages were not part of the test installation.

### F.4 What integrations ask of the network and the platform

Network use divides the head-weighted sample in a way that follows from the design. Of the 37, 30 (81%) reach something outside the sandbox. Fifteen reach cloud services, which the egress proxy serves directly, and fifteen reach devices on the home network, which require a separate and explicit permission, because reaching the home network also means reaching the router and every other device in the house. A household is therefore asked to read the second kind of permission with more care.

Working integrations also show what a permission system has to cover. Following the method of Li et al. (2025), the source code of the 144 most-installed community integrations, and of the 40 in the uniform sample, was read automatically for each part of the platform it uses (Table F.2). At 40 integrations, one integration is 2.5 points, so only differences of about ten points or more are read as findings.

**Table F.2**
*Parts of the platform used by community integrations*

| Part of the platform | 144 most-installed | 40 drawn at random |
|---|---|---|
| Its own configuration entry | 94% | 93% |
| The platform's shared data store | 86% | 80% |
| The event bus, on which every change in the house is announced | 49% | 18% |
| The service registry, to offer actions or call them | 65% | 38% |
| Calls to another integration's services | 22% | 13% |

The parts an integration needs merely to exist are used about equally in both samples. The parts that widen its reach are not: use of the event bus falls by 31 points in the random sample, and use of the service registry by 27. A study of popular integrations alone would therefore overstate how much of the platform a typical integration touches. The measurement also decides how finely permissions are granted. Almost every integration manages its own configuration entry, but few act on other integrations, so permission is granted per action, and calls to another integration's services are refused unless declared, which affects about one integration in eight in the random sample.

### F.5 The full costs

**Table F.3**
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

Section 12.3 discusses these figures. The rows it does not give are the memory with two components, the delay with 26 sandboxes saturating the mediator, the cost of one delivered change, the cut-off of a flooding sandbox and `powercalc`'s start-up.

### F.6 How the evaluation was checked

The evaluation fails on its own terms if it reports a requirement as passed without demonstrating it, or reports an aggregate that conceals a breakdown it possesses. This happened twice during development, and both times the fault was found by reading the report as a whole rather than by any test: a requirement was reported as verified two months before the comparison that supports it existed, and a promised scoring of the security results was missing. These two failures led to the checking methods in Table F.4, and the claim register in Appendix D.

**Table F.4**
*What each verification method found*

| Method | Principal findings | Result at the second final rerun |
|---|---|---|
| Re-measurement on fixed code | The mediation delay was 43 µs, not the 31.5 µs first stated (F17) | Every figure inside its criterion (Table F.3) |
| Re-derivation of headline figures from raw records | A stated worst-case delay had no record behind it (F23) | 39 of 40 equal; the other was the abstract's outdated suite count |
| Fault injection | A full disk left the audit record unverifiable (F28); losing the platform left no recovery (F29) | 11 of 11 on both hosts |
| Security review and fuzzing | A sandbox could inherit the supervisor's terminal (F34, Critical); malformed requests could stop the mediator (F33) | 4,864 requests, no escape |
| Deliberate defects (mutation testing) | Three defects survived every suite at first; the supervisor ran in no suite (F48) | 90 of 92 caught; the other two change no behaviour, so no test could detect them. All 35 suites pass, twice |
| Reproduction from a fresh copy | No reproduction guide existed (F18) | Guide written and followed from a fresh copy; not yet on a freshly installed device |
| Running real integrations against a real installation | The stand-in hid how few kinds the bridge covered (F64); a picture link could pass the egress allowlist through the household's browser (F71) | 36 of 36 |

The evaluation was repeated in full twice, each time from a fresh copy of a tagged version under predictions committed beforehand, the second at the frozen code of 1 November 2026, and every step of the second met its criterion. Its bounds are stated in Section 12.5: the deliberate defects were chosen by hand, so they show that each tested point is guarded, not that every point is, and the reproduction guide has not yet been followed on a freshly installed device.
