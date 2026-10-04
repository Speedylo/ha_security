# W1 step 1 — the push loop and the per-spawn re-check, against the stand-in: design and prediction

**Written 2026-10-04, before any code was changed or run.** The predictions in §4 are never revised
after; corrections go below them as dated pointers.

W1 is two steps (`remaining_work_20261003.md` §2, agreed 2026-10-04). This note covers **step 1**:
build the push loop and §8.7 #14's explicit manifest reload against the existing stand-in
`Platform`, and change `selftest_t12` so that it tests the reload rather than the accident. Step 2
connects the same mechanism to the house's real Home Assistant (the bridge integration and
`RealPlatform`). The point of the order is that step 1 stands on its own: if step 2 runs out of
time, step 1 has still turned S3's subscription half from "nothing is delivered" into a filter that
can be tested, and has removed the accidental re-check.

## 1. Found by reading, before any change

**(1) The record is not written before the action, although §6.8.3 says it is.** §5.11.3 puts step
4 (record) before step 5 (act), "so an action that succeeds and then crashes the mediator is still
attributable", and §6.8.3 states that "the record is written and `fsync`ed before the action is
attempted". In the code, step 5 happens *inside* `acting_policy`'s `policy()`: an `entity.publish`
writes `platform.states`, a `service.call` appends to `platform.calls`, and a `network.egress` has
the broker resolve and **connect to the internet**. `Mediator._handle_ready` only writes the record
after `policy()` returns. So for every acting operation the order is decide, act, record. The
self-test §6.8.3 cites crashes after the record in a harness where the action comes later, which is
why it never saw this. A mediator that dies between the `connect` and the `fsync` has made an
outbound connection that no record attributes, which is exactly the case the ordering exists for.

This matters to the push loop directly: delivering a state change *is* an action, and it must
follow its record. So step 1 splits the policy into a decision and a separate action that the
mediator runs only after the record is durable, and adds a self-test case that crashes between the
two.

**(2) The re-check is still accidental, and nothing would notice it going.** As `selftest_t12`'s
docstring says, a manifest is re-read only because every harness builds a fresh `Mediator` and a
fresh policy per run. A push loop needs a mediator that stays alive across sandbox respawns, so it
can keep watching the platform for them. Once that happens the re-read stops, and `selftest_t12`
keeps passing, because it builds its own fresh policies by hand (§7.30.2, §7.30.4).

**(3) The sandbox's half of the channel cannot receive anything it did not ask for.** In
`sandbox_runtime.Channel.request`, the sandbox sends, then blocks until one frame comes back and
treats that frame as the answer. A frame the mediator sent first would be taken as the reply to
whatever was asked next. The sandbox also sends no request `id` (the mediator echoes `None`), so
nothing on the wire tells a reply apart from anything else today.

**(4) A sandbox that stops reading could stop the mediator.** `Channel.send` uses `sendall` on a
blocking socket. Today that is safe, because the mediator only ever replies to a sandbox that has
just asked and is waiting for the reply. Once the mediator speaks first, a sandbox that never
reads fills its socket buffer, and the next push blocks the mediator's only thread, which stops
every other sandbox too. That would be a denial of service across sandboxes, created by the push
loop itself.

## 2. Design

**The event source.** `Platform` gains `set_state(entity_id, state, attributes)` and a listener
list. Every write to the stand-in's state goes through it, including `seed` and the publish path,
so a change made by one sandbox reaches the others' subscriptions the same way a change in the
house would. In step 2, `RealPlatform` calls the same listeners from (A)'s event bus.

**Subscriptions are decisions; deliveries follow from them.** At start, after mirroring, the bridge
sends one `entity.subscribe` request per declared entity. That request goes through the full five
steps: it is decided against the manifest, recorded, and only if allowed is the entity added to
that sandbox's subscription table. A state change is pushed to a sandbox only if the table holds
that entity. So the filter in S3 is the table, and every entry in the table traces back to a
recorded, allowed decision. A change that is never delivered needs no record, because the sandbox
asked for nothing. (Whether each *delivery* is also recorded is decision A in §3.)

**The wire.** Replies keep their current shape. A push is a frame with `"push": "entity.state"`
and no `id`, carrying `entity`, `state` and `attributes`. The sandbox's `request()` reads frames
until it gets one that is not a push, and queues the pushes it reads on the way. When the sandbox
is idle, the socket is registered with the event loop (`loop.add_reader`), and that reader checks
readiness again before reading, because a `request()` earlier in the same loop iteration may
already have drained the socket. Queued pushes are applied on the next loop iteration with
`hass.states.async_set`, and never from inside `request()`, which is itself called from inside
state-change callbacks. Pushed entities are in `mirrored`, so `watch_local_state` does not echo
them back as publishes.

**A slow sandbox.** The mediator never blocks on a push. Each channel gets a pending map
(`entity → latest state`). A push replaces the entry instead of queueing behind it, and the map is
flushed when the socket is writable. This works because a state is a value rather than an event:
only the latest one matters. So a sandbox that stops reading costs the mediator one entry per
subscribed entity, never a blocked thread. (Decision B in §3.)

**The re-check (§8.7 #14).** The policy becomes an object that holds `manifests` and the
subscription table. Its `bind(identity, component)` loads the manifest from disk and replaces that
identity's entry, and `Mediator.register` calls it every time. So every spawn re-reads the
declaration by construction, not because a harness happened to start a fresh mediator.
`unregister` drops the identity's subscriptions. A running sandbox is still never re-bound by a
file edit, because only `register` calls `bind`, as T12's control requires.

**What `selftest_t12` gains.** One long-lived `Mediator`, two registrations of the same domain with
the manifest edited in between, and an assertion that the second registration decides by v2. The
case is run once against the *current* code first, where it must fail (P1): if it passes there, it
is not testing the trigger.

**What is not in step 1:** (A) itself, the registry and identity question, real service execution,
and restart survival. Those are step 2.

## 3. Decisions for Younes before code

**Decided 2026-10-04 by Younes: A — the subscription only; B — keep the latest state per entity.**

**A. Is each delivery recorded, or only the subscription?**
- *Recommended: only the subscription.* Each `entity.subscribe` is a full decision with an fsynced
  record. Deliveries are counted in memory. The argument is the same as for egress: the connect
  is recorded and the bytes that later flow through it are not. The cost is that the log shows
  *what it was allowed to see*, not *each value it saw*.
- *Alternative: every delivery is an fsynced record.* That gives a complete record of what crossed
  the boundary, at 3.67 ms each. With 272 records a second shared across every sandbox, it is the
  one choice that could actually use up §7.20.1's headroom.

**B. When a sandbox stops reading:** keep only the latest state per entity (recommended, as above),
or disconnect the sandbox once a threshold is crossed.

## 4. Predictions

| | Prediction | Confidence |
|---|---|---|
| **P1** | The new `selftest_t12` case (one long-lived mediator, manifest edited between two registrations) **fails against today's code**: the second registration still decides v1's way. It passes after `bind` | high |
| **P2** | After the change, a file edit still does not re-bind a channel that is already registered (T12's control holds with a long-lived mediator) | high |
| **P3** | Found-by-reading (1) is real: a new case that makes the action raise after the decision shows **no record on disk** for an allowed `entity.publish` with today's code, and a record there after the split | high |
| **P4** | Against the stand-in in a real spawned sandbox, a change to a declared and subscribed entity reaches (B)'s state machine and fires the integration's own listener. For `thermal_comfort`, the dew point it publishes changes after a pushed temperature change, with no change to the integration | medium — the sandbox's dual-mode reading is new, and it has to work inside Home Assistant's event loop |
| **P5** | Changes to undeclared entities: **0 delivered** of all made. With the subscription table bypassed (a mutation), the same run delivers them, so the zero comes from the filter and not from the absence that §7.14.4 describes | high |
| **P6** | No echo: a pushed state never comes back as an `entity.publish` | medium |
| **P7** | A sandbox that never reads does not delay pushes to a second sandbox measurably, and the mediator's memory for it is bounded by its subscription count | medium |
| **P8** | Under decision A as recommended, push delivery costs tens of microseconds per sandbox, well under 1 ms, with no fsync on the path, so pushes do not compete with decisions for §7.20.1's 272 per second | medium — measured on the Pi, not assumed |
| **P9** | Something not listed here is found | high — the four items in §1 were found by reading alone |

---

## 5. Outcomes, 2026-10-04 (appended; §4 is unchanged)

Evidence: `experiments/push_loop/results/prefix_20261004/` (the two new cases run against the
unchanged code) and `experiments/push_loop/results/w1_step1_20261004/` (after the change, on the
Pi: Python 3.13.5 for the decision layer, `~/r2exp/ha314` for the spawned run).

| | Outcome |
|---|---|
| **P1** | **Held.** Against the unchanged code, the long-lived mediator bound the respawn to v1, and both new checks failed (31/33). With `bind` at registration: 33/33 |
| **P2** | **Held.** A manifest edit leaves the running channel deciding v1's way; only the respawn moves |
| **P3** | **Held, and it was a real defect.** Through `Mediator` and `acting_policy`, an allowed `entity.publish` whose action dies left **0 decision records on disk**. After the decide/act split, the record is there. §6.8.3's sentence was true of the hand-staged self-test and false of the path every harness used |
| **P4** | **Held, in a real sandbox.** `thermal_comfort`, unmodified, recomputed from a pushed 30.0 °C: dew point 9.96 → 17.81 °C, heat index 20.85 → 30.74, perception "dry" → "ok_but_humid". 34 decisions, chain verifies, reconciles with memory |
| **P5** | **Held.** 0 of 3 undeclared changes delivered, nothing to the integration with no grant, and the mutation that bypasses the table delivers 3 of 3 to the same observer |
| **P6** | **Held.** None of the 30 publishes is one of the two pushed entities |
| **P7** | **Partly, and the bound was wrong.** The mediator never blocked (20,000 changes, 0.43 s on the Pi, one sandbox never reading), and the reading sandbox got the latest value. But the stalled sandbox's backlog was **278 frames**, not one: coalescing starts only when `send` returns `EAGAIN`, so the kernel's socket buffer fills first. The bound is the socket buffer plus one state per entity. The cross-sandbox *delay* was not measured in the first run, only that it completed. *Measured the same day, after this note's first commit:* the reading sandbox's median delivery was 20.9 µs alone and 24.9 µs beside a stalled neighbour on the Pi (`selftest_push_p7_delay.log`) |
| **P8** | **Held, after the first measurement was thrown out.** The first version let a reader thread race the loop, so 98% of pushes were coalesced and the 5.0 µs was the cost of replacing a dict entry. Re-measured with every push written: **10.9 µs per delivered push on the Pi** (6.1 µs on the x86 laptop), against 3.67 ms per recorded decision. That is the mediator's side only; the sandbox's apply cost is not in it |
| **P9** | **Held.** The sandbox's `channel.request` had no lock and is called from executor threads, and `last_fd` was shared between threads. Fixed with a per-exchange lock and `exchange()` returning the descriptor with its own reply |

**Regression:** all 22 suites (the 21 from 2026-10-03 plus `selftest_push`) pass on the Pi against
the changed code, logs in `experiments/push_loop/results/w1_step1_20261004/suites/`.

**Paid 2026-10-04, before step 2** (§7.36 written, and dated pointers at every place the report
stated what this changed: §5.11.3; §6.8.3, §6.10.5, §6.11.2; §7.5's S3 row, §7.14.4, §7.16.3,
§7.20.1, the threat tables' T06, T1 and T18 rows, §7.26.5, §7.30, §7.32; the abstract and the
front matter's counts; §8.2.3 (table and limits), §8.2.4, §8.3's suite count, §8.6.3 #1, and
§8.7's introduction, #1 and #14). **What the report owed from this:** §6.8.3's "written and fsynced before the action" needs a dated
correction (true from 2026-10-04, false before for every acting operation); §7.14.4's "absent
feature" becomes a measured filter; §8.7 item 1 and #14 move to done-at-the-stand-in; §7.20.1 gains
the push cost; and the P7 bound (socket buffer plus one per entity) is stated as found.
