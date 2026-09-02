# Experiment — what an integration can see of the home, with and without the framework

**Run:** 2026-09-02 · **Target:** Raspberry Pi 5, aarch64, HA 2026.8.3, Python 3.14.7 ·
**Feeds:** §7.14 · **Discharges:** §7.5's S3 criterion

§3.5 fixed S3's verification before any implementation existed, and the paired clause is the
reason this experiment exists:

> "a confined integration attempting to read and to subscribe to undeclared entities is denied,
> **with a paired baseline measuring what is readable without the framework**."

Showing a sandbox refuses a read says nothing about what the refusal is worth. The number that
matters is what the same integration would otherwise have held.

## The home

`confine/home.py` — 36 entities, furnished identically into both arms so the comparison is about
the framework rather than about two differently-populated instances. **20 of the 36 are marked as
disclosing occupancy, presence or routine**: device trackers, `person` entities, motion and
occupancy sensors, door and lock states, the alarm panel, bed presence, TV state, the family
calendar. That marking is a judgement and it is recorded in the source rather than applied
silently in a results table.

§3.5 derives S3 from §1.7's Table 1.2 row 1 precisely because *"a design mediating only state
changes would leave surveillance untouched, which is the majority of the privacy harm."* So the
sensitive subset is counted separately: *"37 of 41 entities readable"* and *"every presence
sensor in the house readable"* are the same number carrying very different weight.

The integration under test declares exactly one entity: `sensor.outdoor_temperature`.

## Result

```
                                        unconfined    confined
  entities present to it                    36/36        1/36
  of those, occupancy or presence           20/20        0/20
  changes by others delivered to it           4/4    none, see below
```

| Probe | Unconfined | Confined |
|---|---|---|
| `sensor.outdoor_temperature` (declared) | read | present; read + subscribe permitted |
| `device_tracker.younes_phone` * | read | **absent**; denied `/permissions/entities/read` |
| `binary_sensor.bedroom_occupancy` * | read | **absent**; denied `/permissions/entities/read` |
| `lock.front_door` * | read | **absent**; denied `/permissions/entities/read` |
| `alarm_control_panel.home_alarm` * | read | **absent**; denied `/permissions/entities/read` |
| `calendar.family` * | read | **absent**; denied `/permissions/entities/read` |
| `sensor.electricity_price` | read | **absent**; denied `/permissions/entities/read` |

`*` discloses occupancy, presence or routine. Raw output: `results/pi5_s3.json`.

## The two mechanisms, kept apart

The report distinguishes them because they are different claims:

- **`present_locally`** — is the entity in the integration's own state machine at all? Confined,
  an undeclared entity is **absent**, not refused. There is nothing to appeal against, and
  nothing had to decide. §5.6.2 on the read path.
- **`mediator_ok`** — will the mediator read or subscribe on its behalf? Confined this is a
  decision carrying a clause pointer. Unconfined the column is filled in as "yes" because
  **nothing was asked**: `hass.states.async_all()` needs no permission and there is no mediator
  to consult.

The unconfined baseline is one line of code, and that is the finding rather than a shortcut:

```python
hass.states.async_all()      # every state in the house, unasked, by any integration
```

## The limit, stated because the number would otherwise overstate it

**The subscription half is verified at the decision layer only.** Unconfined, all four changes to
entities the integration does not own arrive through `EVENT_STATE_CHANGED`, unfiltered. Confined,
none arrive — but that is an **absent feature, not a demonstrated filter**. §6.11.2 records that
no push loop exists: declared entities are mirrored once at construction, so there is no path by
which any state change could arrive, filtered or otherwise.

What *is* demonstrated is that `entity.subscribe` on an undeclared entity is refused with a
clause. What is not demonstrated is a working subscription that delivers declared changes and
withholds the rest. The push loop is on §6.11.2's list of what is still missing.

## Reproducing

```bash
systemd-run --user --scope -q python3 -m confine.selftest_reads \
    --python ~/r2exp/ha314/bin/python --json results/pi5_s3.json
```
