# W1 step 2b — commands from the house into a sandbox: design and prediction

**Written 2026-10-04, before any code.** §4 is never revised; outcomes are appended below it.

Step 2 (§7.37) made a confined integration's entities first-class in the house's Home Assistant,
(A), and left one direction missing: a user in (A) operating an entity a sandbox owns. Until this
exists, a confined switch, light or lock is display-only in the house. This is the third inbound
message type, after replies and state pushes.

## 1. The test integration

`adaptive_lighting`, unmodified, already an end-to-end subject. Confined it publishes four switches
(2026-10-03 re-run): the instance's main switch and its sleep-mode, adapt-colour and
adapt-brightness switches. Turning the sleep-mode switch on from (A) is an ordinary thing for a
user to do, and in (B) it runs the integration's own `SwitchEntity.async_turn_on`. So no
purpose-built integration is needed, and the integration under test was not written by me.

## 2. Design

**The path.** A user's `switch.turn_on` in (A) reaches the bridge's switch entity. The bridge sends
a command event on a stream the mediator subscribed to (`confine_bridge/commands`, admin-only), and
waits for an answer. The mediator identifies the integration from the entity's `unique_id`, records
the command, and pushes it down that integration's channel. The sandbox calls the same service on
the same entity in (B) with `blocking=True`, so the integration's own handler runs, and answers with
the result. The mediator passes the result back (`confine_bridge/command_result`), and the bridge
either returns, or raises a `HomeAssistantError` the user sees. The integration's new state comes
back the ordinary way, as a publish.

**It is recorded, and it is ambient.** A command tells an integration to act; for a lock
integration, it is "unlock". So it is a durable decision, with op `entity.command`, the integration,
the entity and the service, written before the command is pushed (§7.36.1's order). It needs no
clause: operating an integration's own entity through its own platform is what having the entity
means, as publishing it is (§5.10.2). The mediator still refuses a command for an integration that
has no channel, or for an entity that integration does not own.

**It is never coalesced.** States are coalesced because only the latest value matters (§7.36.2). A
command is an instruction, so commands get their own first-in-first-out queue in each channel's
outbox, bounded at 32. Past that, a command is refused to the user rather than queued without limit.

**Answers are checked.** A sandbox can answer only a command the mediator actually sent to that
channel and has not yet seen answered. Any other answer is ignored and recorded as a protocol
error, so a sandbox cannot use the answer path to make (A) do anything.

**(A) gets a light**, a template light over an `input_boolean`, because `adaptive_lighting` declares
a read of `light.living_room`. Until now that light existed only on the stand-in.

**Scope.** Switches only, through `turn_on` and `turn_off` (Home Assistant's `toggle` arrives as
one of them). Lights, covers and locks need the same path with more service shapes. That is future
work, and the bridge refuses those domains rather than approximating them.

## 3. Defaults taken, not asked

The design was decided in step 2's question B ("2b, after"). Two details have conventional answers,
so I took them rather than asking: the bridge waits for the result (as a native service call does),
with a 10 s timeout; and the command is recorded durably.

## 4. Predictions

| | Prediction | Confidence |
|---|---|---|
| **C1** | A user's `switch.turn_on` on the confined sleep-mode switch in (A) returns success, `adaptive_lighting`'s own handler runs in (B), and the switch reads `on` in (A) afterwards, published back the ordinary way | medium — `adaptive_lighting`'s switch may do more on turn-on than set a state |
| **C2** | With two sandboxes connected, a command reaches only the owning integration's | high |
| **C3** | Each command is a durable `entity.command` record, written before the push leaves | high |
| **C4** | A command for an integration with no running sandbox fails to the user at once (well under 1 s), not at the 10 s timeout | high |
| **C5** | A sandbox that never answers makes the user's call fail at 10 s, and the mediator keeps serving others meanwhile | medium |
| **C6** | A command's round trip, from the user's call to its return, is tens of milliseconds, dominated by (B)'s service handling | medium |
| **C7** | A sandbox answering a command it was never sent is ignored and recorded as a protocol error, and nothing happens in (A) | high |
| **C8** | Something not listed is found | high |

---

## 5. Outcomes, 2026-10-04 (appended; §4 is unchanged)

Evidence: `experiments/real_platform/results/w1_step2b_20261004/`, against a fresh (A) on the Pi.

| | Outcome |
|---|---|
| **C1** | **Held, with the real integration.** A user in (A) turned on `adaptive_lighting`'s sleep-mode switch. Its own handler ran in (B), the call returned success, and the switch reads `on` in (A), published back the ordinary way |
| **C2** | **Held.** With two sandboxes connected, the command reached only the owner's |
| **C3** | **Held.** One durable `entity.command` decision per command, with `requested.service = switch.turn_on`, written before the push |
| **C4** | **Held.** With the owner's sandbox gone, the user's call failed in 2 ms ("selftest has no running sandbox"), and the refusal is recorded |
| **C5** | **Held.** A sandbox that never answers failed the user's call at 10.0 s, and another sandbox was answered in 1.0 ms meanwhile |
| **C6** | **Held, at the low end.** 16 ms from the user's call to its return, through the real `adaptive_lighting` |
| **C7** | **Held.** An answer to a command never sent was refused and recorded as a protocol error, and the channel survived |
| **C8** | **Held only on the test's side. No framework defect was found.** Two defects in my own test: C5's "meanwhile" was first reported as 301 ms, which was the test helper's `serve(timeout=0.3)` (the same mistake as step 2's R5); and the simulated user's socket timeout equalled the bridge's 10 s, so the two raced, and one run lost the outcome |

**Limits.** Switches only (`turn_on`, `turn_off`). If two sandboxes claim the same integration, a
command goes to the first one registered. The simulated user in (A) uses the mediator's own owner
token, so the command's context names the same user as the mediator.
