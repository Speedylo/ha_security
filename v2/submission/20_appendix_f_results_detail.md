## Appendix F — Detailed results

This appendix holds the detail behind Section 12: two facts about the attacks, the full end-to-end table and the bridge's limits. All figures come from the final rerun of 1 November 2026 unless stated otherwise.

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
