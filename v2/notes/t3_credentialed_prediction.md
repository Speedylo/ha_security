# T3 — one integration with a valid credential, end to end: prediction

**Written 2026-10-03, before the account exists and before any run.** Never revised after.

26 of 37 head-corpus integrations need a credential before their own flow completes, and none has
ever completed setup with a valid one in either arm. §7.24 reached `pirateweather`'s host with a
deliberately invalid key, which answered *what shape* egress takes and not whether an
**authenticated** round trip works from inside a sandbox. `pirateweather` is chosen because it is in
the head corpus, `cloud_polling`, needs nothing but an API key from a free tier, validates the key in
its own flow (a 403 is "Invalid API Key"), and polls through the platform's client session — §7.27's
path, now with an authenticated request. Flow input: both platforms, and the temperature sensor, so
there is a number to compare.

The key lives in `~/.config/capstone/pirateweather.key` on the Pi, mode 600, outside the repository.
The harness scrubs its value from every report before anything is printed or written.

| | Prediction | Confidence |
|---|---|---|
| **P1** | Arm A completes the flow with the valid key and publishes a numeric temperature | high, given the key is valid |
| **P2** | Arm B reaches LOADED and its temperature **equals** A's — fetched minutes apart from a forecast that updates hourly | medium-high |
| **P3** | B's mediator grants `api.pirateweather.net:443` and nothing else, and the durable record reconciles | high |
| **P4** | Arm C **fails its config flow**: the validation call is refused, `ClientError` is caught, and the flow returns an error instead of an entry | medium — the error branch builds a tuple, not a string, which may itself misbehave |
| **P5** | **The key never reaches the mediator.** TLS runs inside the sandbox over a handed-over socket, so the key in the request path is encrypted before it leaves; the mediator's in-memory and durable records hold a host and a port. Measured, not assumed | high |
| **P6** | The key appears nowhere in the result JSON or the console output | high — checked by grep after the run |

**Not tested, and stated now so it is not read as tested later:** re-authentication and token
refresh. Pirate Weather's key is static, so the phase §8.6 says no one has looked at — egress demand
appearing at refresh rather than at setup — is still unexamined. A config entry persisting the secret
inside the stripped instance is exercised, since the sandbox's own `.storage` holds it during the run.
