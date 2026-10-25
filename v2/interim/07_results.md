# 7 Results and Findings

The results are reported against the three assertions of Table 5.1 in turn: that confinement is effective, compatible and affordable. Every security and compatibility result compares a confined arm with an unconfined arm, run on the same device and the same platform release, so each difference can be attributed to the framework.

## 7.1 Confinement is effective

The first assertion would fail if either published attack technique succeeded under confinement, or if a platform credential could be recovered from inside a sandbox. Neither happened. Table 7.1 sets out the four attacks that test these conditions, each run in both arms.

**Table 7.1**
*Four attacks, unconfined and confined*

| Attack | Unconfined | Confined |
|---|---|---|
| The garbage-collector technique, aimed at another integration's live credential (Corno & Mannella, 2022) | Credential reached | Nothing found: every object visible belonged to the attacker |
| The 2021 path-traversal pattern, aimed at two planted secrets (Home Assistant, 2021) | 2 of 2 secrets recovered | 0 of 2: the file does not exist inside the sandbox |
| Reading another process's environment variables | Contents read | Nothing to read |
| Reading the states of devices the integration was not granted | 36 of 36, including all 20 that reveal whether someone is at home | Only the 1 device that was declared |

The garbage-collector result carries the most weight, because it is the attack the design was built to defeat. Python offers every program a list of all the objects alive in its process, and when all integrations share one process, that list includes the other integrations' credentials. Unconfined, the attack found a victim integration's cloud credential. Confined, the same code ran without error and examined 8,942 objects, all of them its own, while the credential was confirmed to be alive in the mediator's separate process. The attack therefore did not fail at a check that an attacker might find a way around; it succeeded and found nothing, because the credential was not there. The path-traversal result has the same form: the planted secrets were reported as missing rather than forbidden, because the file is absent from the sandbox's view of the system. For a household, the last row matters most. Unconfined, one request returned every device state in the test home, including every sensor that reveals whether someone is in; confined, the integration saw only the device its permissions named.

Beyond these four attacks, the project's own 39 attacks, derived from its threat model, recovered neither planted secret, and sixteen of the model's nineteen threats are shown to be controlled. This result is bounded by who carried out the attacks: all of them were written within the project, and no independent tester has attacked the framework. A line-by-line reading of the code found a route out of the sandbox through a shared terminal that no automated test had detected; it was fixed and is now tested from inside the sandbox, but its discovery suggests that attacks the builders did not anticipate may remain. Within that bound, the evidence supports the first assertion: the two published attack techniques succeed without the framework and find nothing with it. In practical terms, a confined integration installed to show electricity prices can no longer read the household's stored passwords, and it can learn when the house is empty only if it has been granted the sensors that show it.

## 7.2 Confinement is compatible

The second assertion would fail if the unconfined arm showed that most failures under confinement were caused by the design rather than by the integrations or the platform. The opposite was found. Table 7.2 gives the share of integrations that import and set up cleanly in each arm.

**Table 7.2**
*Integrations that load cleanly, unconfined and confined*

| Sample | Integrations | Unconfined | Confined | Failures caused by confinement |
|---|---|---|---|---|
| Head-weighted | 37 | 31 (84%) | 31 (84%) | 0 |
| Uniform | 40 | 37 (92%) | 37 (92%) | 0 |

The two arms failed on exactly the same integrations, and a repeat run on a corrected test setup gave identical error messages in both arms. No integration loaded unconfined and failed confined. The 84% figure is therefore not a statement about confinement. It is the share of the most-installed community integrations that load cleanly on this platform release at all, whether or not they are confined. The uniform sample was predicted to do 10 to 30 points worse, on the reasoning that less popular integrations are less well maintained, and it did 8 points better. A typical integration in that sample depends on fewer parts of the platform and on fewer outside packages, so it has less that can go missing. Compatibility therefore follows how much of the platform an integration needs, not whether it is confined.

Loading is not the same as working, so thirteen integrations were also run end to end, each set up through its own unmodified configuration steps and then given a task whose correct outcome was predicted before the run (Table 7.3). They are reported by name rather than as a rate, because most integrations cannot complete their setup without an account or a physical device, a limit that applies to the unconfined arm as much as to the confined one.

**Table 7.3**
*The thirteen integrations run end to end*

| Integration | What it does | Confined result |
|---|---|---|
| `thermal_comfort` | Calculates comfort measures from temperature and humidity | Correct dew point (9.96 °C from 21.4 °C at 48% humidity), as unconfined |
| `watchman` | Reports configuration that refers to missing devices | Correct; a device it was not granted is reported missing, because it does not exist in the sandbox |
| `adaptive_lighting` | Adjusts lights to the time of day | Brightness 38 against 39 unconfined, half a minute apart |
| `powercalc` | Estimates the power use of unmetered devices | 8.06, 3.00 and 0.00 W, identical to unconfined |
| `scheduler` | Runs actions at set times | Light switched on at the scheduled second, as unconfined |
| `nordpool` | Electricity prices from an online service | Same price as unconfined |
| `smhi_brandrisk` | Fire-risk forecasts from a weather institute | Same three values as unconfined |
| `regensburg_transport` | Public-transport departures | Same departure in both arms |
| `dwd_weather` | Forecasts from a national weather service | Same forecast as unconfined |
| `pirateweather` | Weather from a service that requires an account key | Same reading within 0.02 °C; the key never reached the mediator |
| `midea_ac_lan` | Controls air conditioners on the home network | Same result as unconfined, against a simulated device |
| `localtuya` | Controls smart plugs and similar devices locally | Finds the simulated device, as unconfined |
| `trakt_tv` | A television calendar from an online account | Renews its expired login token inside the sandbox and works |

All thirteen worked confined. Each integration that uses the network was also run with its network permission removed, and every one of its requests was then refused and recorded, which shows that the working runs reached their services through the declared permission and not around it.

Working integrations also show what a permission system has to cover. Following the method of Li et al. (2025), the source code of the 144 most-installed community integrations, and of the 40 in the uniform sample, was read automatically for each part of the platform it uses. Because this reads the code rather than running it, it covers integrations that could not be set up. Table 7.4 gives the main results.

**Table 7.4**
*Parts of the platform used by community integrations*

| Part of the platform | 144 most-installed | 40 drawn at random |
|---|---|---|
| Its own configuration entry | 94% | 93% |
| The platform's shared data store | 86% | 80% |
| The event bus, on which every change in the house is announced | 49% | 18% |
| Calls to services, the actions that operate devices | 65% | 38% |
| Calls to another integration's services | 22% | 13% |

The parts an integration needs merely to exist, such as its own configuration entry, are used almost equally in both samples. The parts that widen its reach are used far less in the random sample: the event bus by 31 points less, and services by 27 points less. A study of popular integrations alone would therefore overstate how much of the platform a typical integration touches. The measurement also decides how finely permissions are granted. Almost every integration manages its own configuration entry, but few need to act on other integrations, so permission is granted per action rather than for a whole part of the platform, and calls to another integration's services are refused unless declared, which affects about one integration in eight in the random sample.

The compatibility result therefore holds in a precise form: confinement caused no loading failure across 75 integrations and no failure among the thirteen run end to end. In practical terms, an integration that works in a household's installation today was not found to stop working when confined, within the two samples, the named set and the single platform release.

## 7.3 Confinement is affordable

The third assertion would fail if the device could not hold as many sandboxes as the average installation has community integrations, 4.02 (Home Assistant, n.d.-b), or if mediation changed what the platform can do. Neither condition was met. Table 7.5 gives the main costs, each measured in ten passes on fixed code.

**Table 7.5**
*The cost of confinement on a Raspberry Pi 5 with 4 GB of memory*

| Quantity | Median |
|---|---|
| Memory per sandbox, integration using no other platform parts | 56.5 MB |
| Memory per sandbox, integration using all ten platform parts measured | 135.6 MB |
| Delay added by the mediator to one request | 43 µs |
| Writing the decision record to disk, before the action | 3.67 ms |
| A change in the house reaching a confined integration | 0.5–0.9 ms |
| A household command reaching the integration | 11–16 ms |

Memory decides how many integrations can be confined. If 60% of the device's memory is set aside for sandboxes, it holds between 17 sandboxes, when each integration uses every platform part measured, and 43, when it uses none. Even the heaviest case is four times the average installation's need. The margin has two limits: the platform publishes only the average number of integrations per installation, not how they are spread, so the share of installations that exceed the budget is unknown; and memory was measured with the integrations at rest.

Delay is not a constraint either. Writing each decision to disk before acting is the slowest step, and it limits the mediator to about 269 decisions per second. A generous estimate of real demand, 26 sandboxes each making five requests every thirty seconds, is about four requests per second, so the mediator runs about sixty times clear of it. The delays a household would notice, a change reaching an integration or a command reaching the device, take about a millisecond and between one and two hundredths of a second respectively. The device can therefore afford confinement with a wide margin, within the limits of an average and of measurements at rest. In practical terms, a household running the typical four community integrations on a Raspberry Pi could confine all of them and would not notice the delay.
