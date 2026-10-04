# W1 step 2 — the real Home Assistant behind the mediator: design and prediction

**Written 2026-10-04, before any code.** §4's predictions are never revised; outcomes are appended
below them, dated.

Step 1 (§7.36) built the push loop and the per-spawn re-check against `platform.py`'s stand-in: two
dicts and a list. Step 2 replaces that stand-in with the house's real Home Assistant, which this note
calls **(A)** as `remaining_work_20261003.md` §3 does. (B) is the private instance inside each
sandbox, which already runs in every experiment. Until now (A) has never run in the confined arm.

## 1. What Chapter 5 already fixes, so it is not re-decided here

- **The mediator holds (A)'s credential and uses it only at step 5** (§5.11.3, §5.15.3). That
  credential is a long-lived access token, and residual risk R3 is that it is unscoped. §8.8's
  single ask of the platform is a scoped token, which only makes sense if the mediator reaches (A)
  through (A)'s own API with a token. So the mediator is a *client* of (A), as in the spike's
  `ha_backend.py`.
- **A bridge component inside (A) gives sandboxed entities their identity** (§5.6, §6.10.2). It is
  trusted framework code: it owns a config entry, creates registry-backed entities on a sandbox's
  behalf, and loads nothing from any integration. The spike's `sandbox_bridge` (~250 lines) may be
  reused (`00_METHOD.md` §5), but its *finding* has to be re-measured (§2 of that file).

## 2. Design

**The connection: (A)'s WebSocket API.** REST, which the spike used, cannot push, and the push loop
is the reason for this work. One WebSocket connection carries everything the mediator needs from
(A): `auth` with the token; `subscribe_entities` for the push source, restricted to the entities
some sandbox has subscribed to; `call_service` for permitted service calls; `get_states` for
reads; and a command the bridge registers for publishing. The Pi's system Python has no WebSocket
library (checked 2026-10-04: neither `aiohttp` nor `websockets`), and the mediator is a
single-threaded `selectors` loop. So the client is written here against RFC 6455, with the standard
library only: an HTTP/1.1 upgrade handshake, then masked text frames out and unmasked frames in.
The client is one more file descriptor on the mediator's selector, which is why an asynchronous
library would not fit anyway. It is about 150 lines, and it is the one piece of step 2 that is new
in kind.

**`RealPlatform`** has the interface `ActingPolicy` already uses: `states`, `owners`, `set_state`,
`calls` and `listeners`. Its methods translate to WebSocket messages, and (A)'s `state_changed`
events call the same listeners, so the mediator's push path from step 1 is unchanged. Ownership
(the first-publisher rule of §6.10.3) stays in the mediator, because it is policy and not platform.

**The bridge integration in (A), `confine_bridge`.** It owns one config entry. It registers an
admin-only WebSocket command, `confine_bridge/publish`, which creates or updates a
registry-backed entity with `unique_id = "<integration>:<entity_id>"` and restores its roster on
restart. It is a WebSocket command rather than a service as in the spike, so that it does not appear
in (A)'s service list for automations or scripts to call.

**(A)'s world.** Real entities that change through real services, not bare states posted over
REST. `input_number.living_room_temperature` and `input_number.living_room_humidity` are helpers,
with template sensors `sensor.living_room_temperature` and `sensor.living_room_humidity` that
carry the device classes `thermal_comfort` needs. A push is then caused by `input_number.set_value`,
which is a real service call into (A), and not by the harness editing a dict.

**Running (A).** `hass -c <config>` from the pinned 2026.8.3 build (`~/r2exp/ha314`) on the Pi, as
its own process, onboarded headlessly to mint the token. The spike's `ha_onboard.py` drives the
onboarding API and can be reused. The token is written to a file only the harness reads, and
never into a log.

## 3. Decisions for Younes before code

**Decided 2026-10-04 by Younes: A — WebSocket with a token; B — commands in step 2b, after.**

**A. How the mediator reaches (A).**
- *Recommended: (A)'s WebSocket API with a long-lived token*, through a standard-library RFC 6455
  client. This keeps Chapter 5's credential story, R3 and §8.8's ask exactly as written. The cost is
  about 150 lines that you would need to be able to defend in the viva. RFC 6455 is short and
  belongs in the curriculum anyway.
- *Alternative: a private Unix socket from the mediator to the bridge*, speaking the channel's own
  framing. Less new code, but the bridge would act with (A)'s internal authority rather than through
  a token. That changes R3's framing and §8.8's argument, so Chapter 5 would need a correction.

**B. Commands into a confined integration.** The plan lists "a command reaches the confined
integration": a user in (A) turns on a switch that a sandbox owns, and the call must travel
(A) → mediator → sandbox. That is a third inbound message type, and it needs a switch-shaped test
integration, because `thermal_comfort` only publishes sensors.
- *Recommended: step 2b, after the registry and push are proven on (A)*. If week 2 runs out, it
  becomes a stated limitation, and the registry and push results still stand.
- *Alternative: build it in step 2 from the start.*

## 4. Predictions

| | Prediction | Confidence |
|---|---|---|
| **R1** | `thermal_comfort` confined against (A) publishes its sensors into (A) **with entity-registry rows**: `unique_id`, `platform: confine_bridge`, a config entry. Published over plain `/api/states`, the same states have **no** registry row. This is the re-measurement of the spike's registry finding | high |
| **R2** | After (A) restarts, the confined integration's entities are still in the registry, and restored with their last state before the sandbox republishes | medium — restoring the state needs `RestoreEntity`, and the roster's ordering against platform setup is the risk |
| **R3** | A real `input_number.set_value` in (A) reaches the sandbox and `thermal_comfort` republishes into (A): dew point moves as it did on the stand-in (9.96 → 17.81 °C for 21.4 → 30.0 °C at 48 %) | medium — template sensors round values, so the exact figure may differ slightly |
| **R4** | (A)'s `state_changed` for an undeclared entity never reaches the sandbox, and `subscribe_entities` is asked only for entities in some sandbox's subscription table | high |
| **R5** | Change-to-push latency through (A), from `set_value` to the frame leaving the mediator, is milliseconds (event bus plus WebSocket), not microseconds, and still far below 3.67 ms × anything per change, because no decision is recorded per push | medium |
| **R6** | A permitted `service.call` executes in (A) (visible as a state change there), and a denied one never reaches (A)'s event bus | high |
| **R7** | `selftest_adversary` and the step-1 suites still pass with the stand-in, since `Platform` stays the default. Re-running the security suites against (A) finds nothing new at the decision layer, because the decisions are made before any platform is reached | medium |
| **R8** | Something not listed is found. At least one of: an (A) behaviour the stand-in hid (ownership of a `unique_id` already registered by another platform; `subscribe_entities`' compressed format; restoration ordering), or a defect in the WebSocket client under real traffic | high |

---

## 5. Outcomes, 2026-10-04 (appended; §4 is unchanged)

Evidence: `experiments/real_platform/results/w1_step2_20261004/`. (A) is the pinned 2026.8.3 on the
Pi, rebuilt from nothing (`house_a up --fresh`) before each evidence run.

| | Outcome |
|---|---|
| **R1** | **Held.** All 15 of `thermal_comfort`'s entities have registry rows in (A), each with `platform: confine_bridge`, a `unique_id` naming the integration, a config entry and a device. The same state posted to `/api/states` exists in (A) with **no** registry row. The spike's finding is now re-measured here, and it holds |
| **R2** | **Held, better than predicted.** After restarting (A) with no sandbox running, 15 of 15 rows remain, and 15 of 15 states are identical to before. The bare state is gone |
| **R3** | **Held, exactly.** A real `input_number.set_value` to 30.0 moved the dew point 9.96 → 17.81 °C and the heat index 20.85 → 30.74, the same figures as on the stand-in. The template sensors' `48.0` against the stand-in's `48` changed nothing |
| **R4** | **Held.** (A) is asked for exactly the subscribed entities (`watched`), and a real change to an unsubscribed one is not delivered |
| **R5** | **Held, and much faster than predicted.** Median 0.71 ms, worst 1.57 ms over 30 changes, from the service call leaving the mediator to the change reaching its push. The first measurement (50.7 ms) was the test's own `serve(timeout=0.05)` polling interval and was thrown out |
| **R6** | **Held.** A permitted `input_number.set_value` executed in (A); a refused `input_number.increment` never arrived, and (A) executed exactly one call on the mediator's behalf |
| **R7** | **Held as far as it went.** All 24 suites pass on the Pi (the earlier 22, plus `selftest_ws` and `selftest_real_platform`). The security properties that involve the platform are tested against (A) in `selftest_real_platform`: ownership against (A)'s real entities, refusals never reaching (A), and the filter. **The older security suites still run against the stand-in and were not re-pointed at (A)**: their decisions are made before any platform is reached, but that is an argument, not a measurement |
| **R8** | **Held, five times.** (1) (A) cannot run without the frontend: Home Assistant always sets up `frontend`, treats it as critical, and enters recovery mode if it fails to load, and recovery mode disables every custom integration, the bridge included. (2) The sandbox subscribed before installing its push handler, so a push arriving during a subscribe request was dropped: 4 frames sent, 3 received. (3) Since 2026.8, Home Assistant builds friendly names from the registry as "<device> <entity>", so the bridge renamed every entity ("thermal_comfort living room Dew point"); fixed by carrying the device's and entity's names from (B), and now 15 of 15 match. (4) The sandbox dropped every list-valued attribute, including enum sensors' `options`; now 7 of 7 arrive. (5) A test artefact, R5's 50.7 ms |

**Not done in step 2, by decision (B, 2026-10-04):** commands from (A) into a confined integration.
That is step 2b.
