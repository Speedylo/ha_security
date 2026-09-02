# Experiment — N2's second number: real integrations, own config flows, confined

**Run:** 2026-09-02 · **Target:** Pi 5, aarch64, HA 2026.8.3, Python 3.14.7 · **Feeds:** §7.17 ·
**Discharges:** N2's second half (partially), F1

§3.6's N2 requires "executed end-to-end" be reported **separately** from "imports-clean" and
never conflated. §7.12 gave the first number over 37 integrations. This gives the second.

## Why the set is five, and why that ceiling is a result

A config entry needs data only each integration's own flow can produce. Surveying all 37 by what
`config_flow.py` asks for:

| | |
|---|---|
| ask for an API key, token, password, username, host or email | **26 of 37** |
| ask for none of those — configured from entities, or from nothing | **11 of 37** |

**So the ceiling on any end-to-end measurement of this corpus is 11, not 37** — and it is a
property of the ecosystem, not of this framework. An unconfined baseline meets the same wall.
Reporting a rate over 37 would conflate N2's two numbers *and* imply a denominator no
measurement of any confinement scheme could reach.

From the 11, five were chosen to exercise different things, and `battery_notes` was excluded
because §7.12 established it fails at import on this release in **both** arms.

## Result

| Integration | Outcome | Own entities | Published via mediator |
|---|---|---|---|
| `thermal_comfort` | ✅ **LOADED** | 15 | **15** |
| `watchman` | ✅ LOADED | 10 | 13 |
| `adaptive_lighting` | ✅ LOADED | 4 | 7 |
| `scheduler` | ❌ SETUP_ERROR | 0 | 0 |
| `powercalc` | ❌ NOT_LOADED | 0 | 0 |

**3 of 5 set up and published. Reported as a named set, never as a rate.**

## The round trip, in one integration

`thermal_comfort` is the case worth reading. It is configured from two entities it does not own,
reads them **through the mediator**, and publishes derived sensors back out:

```
mirrored in   sensor.living_room_temperature  (21.4 °C)
              sensor.living_room_humidity     (48 %)
                        ↓  computed inside the sandbox
published out sensor.living_room_dew_point            9.96
              sensor.living_room_absolute_humidity    9.00
              sensor.living_room_frost_point          7.06
              sensor.living_room_heat_index          20.85
              … 15 in total, every one accepted, `refused: []`
```

The two mirrored entities are exactly what its authority manifest declared. The published
entities are accepted as **ambient** (`(ambient: §5.10.2)`) because an integration publishing its
*own* entities is what being an integration is. A dew point of 9.96 °C from 21.4 °C at 48 % RH is
physically correct, so the integration is not merely loading — it is working.

Unmodified source, its own config flow, its own maths, its own entities, across the boundary.

## The two failures, and neither is the harness

Diagnosed rather than counted, per §6.3.3:

**`scheduler` — the genuine cost of network isolation.**
```
zeroconf/_utils/net.py: add_multicast_member
  listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, _value)
```
The sandbox's network namespace has loopback only, so joining a multicast group fails. It
declares `http` and `websocket_api`; zeroconf arrives through that chain. **This is confinement
costing compatibility**, and it is the first such case found end-to-end. It bears directly on the
egress decision: network isolation costs more than "cannot reach the internet".

**`powercalc` — an undeclared component.** Its flow completed all four steps and created the
entry; setup then failed with `KeyError: 'network'` from
`homeassistant.components.network.async_get_loaded_network`. `powercalc` declares `light`,
`group`, `template`, `select`, `utility_meter` and `integration` — **not `network`**, and does not
import it directly either, so it arrives transitively. This is §6.13.2's undeclared-package
finding in its component form: the declaration exists and is incomplete.

## Harness faults found and fixed on the way

Recorded because §6.3.3 requires a failure be checked against the harness before it is charged to
the design, and three of these would have been:

1. **Hard-coded flow input.** The first version posted values guessed in advance; three
   integrations failed schema validation. The driver now **reads the schema the integration
   returned and satisfies it**, as the frontend does.
2. **Menus unhandled.** `powercalc` opens with `async_show_menu`, not a form.
3. **First menu option taken blindly.** That is `global_configuration` for `powercalc`, not the
   branch that creates a sensor. The branch is now named by the caller, as a user names it.
4. **Log capture installed after the flow ran.** `async_configure` sets the entry up as it
   creates it, so `scheduler`'s SETUP_ERROR arrived with no reason at all. Tracebacks are now
   captured from `exc_info` — without which the two real findings above were invisible.

## Limits

- **Five is a named set, not a sample.** No rate is computed and none should be.
- **No unconfined baseline for this arm.** §7.12 established import-level parity; whether these
  five load unconfined on 2026.8.3 is not measured here, so `scheduler` and `powercalc` are
  attributed by their tracebacks rather than by comparison.
- **The mediator acts on §6.10.2's stand-in.** What crossed the boundary is real; what a live
  Home Assistant would do with it is not tested.

## Reproducing

```bash
systemd-run --user --scope -q python3 -m confine.endtoend \
    --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python --json results/pi5_e2e.json
```
