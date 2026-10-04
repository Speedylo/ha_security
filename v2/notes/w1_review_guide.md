# Reviewing W1 — a guide for owning what was built on 2026-10-04

**Written 2026-10-04, after W1 closed and before W2 starts.** W1 added about 2,900 lines across
24 files in one day, almost all of them written with an assistant. You asked to review it before
anything more is added. This guide is meant to make that review an act of ownership rather than a
read-through. It uses the curriculum's four levels (`learning_curriculum.md`, Part 2). The aim for
the viva is **level 2** — you can explain, without the file open, what each piece does and why it
is in that order — on everything below, and **level 3**, rebuilding from a blank editor, on the
two pieces most likely to be examined: the outbox and the WebSocket framing.

The order is bottom-up: each part depends only on the parts before it. Each part names the
concept, the primary source, the code to read, the questions to answer aloud, and one exercise.

---

## Part 0 — What preparing this guide found

I re-read all of W1 before writing this, so that you would not spend your review on defects I
could have caught. It found three, and all are fixed and re-tested against a fresh (A):

1. **One confined integration could stop the mediator for everyone.** The bridge refuses
   domains it cannot stand in for (a `light`, say). That refusal reached the mediator as an
   exception nothing caught, so a sandbox publishing a light crashed the mediator, and its owner
   record had already been written. Reproduced first, then fixed: a platform's *refusal*
   (`PlatformRefused`) is now a recorded refusal answered to the sandbox, a real crash still
   propagates (§7.36.1's ordering test depends on that), and ownership is recorded only after
   the publish succeeds. `selftest_real_platform` has a regression case (37/37).
2. **A timeout race inside the framework.** The mediator's socket to (A) timed out at 10 s, the
   same as the bridge's own waits. This is the race I fixed in the test's simulated user, but I
   had missed it in the framework. It is now 30 s.
3. **(A) stopped itself five minutes after every fresh start.** Since 2026.8, Home Assistant
   treats an `http:` YAML section as a *pending trial* configuration. Unless an administrator
   confirms it within five minutes, it reverts and restarts, and a restart means exiting for a
   supervisor that does not exist here. `house_a.py` now confirms it
   (`http/config/promote`). Every evidence run so far finished inside that window, which is why
   no result is affected, and why nothing noticed until (A) was found down after a suite run.

None of the three changes a measured figure in §7.36–§7.38, but the first is a real
availability defect, and the report needs a pointer for it (done with this guide's commit).

---

## Part 1 — The wire: frames, and one socket shared by threads

**Concept.** A stream socket carries bytes, not messages, so a protocol must frame them; here, a
4-byte big-endian length, then JSON. One socket shared by several threads must have exactly one
writer and one reader per exchange, or frames interleave.

**Source.** `man 7 unix`; Python's `socket` docs on `sendall`, `recv`, `recvmsg`.

**Read.** `channel.py` — `frame()` and `send()` (W1 split them, so the mediator can queue bytes
without blocking). Then `sandbox_runtime.py` — `Channel.exchange`, `Channel.poll` and
`_read_frame`: the sandbox's half.

**Answer aloud.**
- Why can a push arrive *between* the sandbox sending a request and receiving its reply, and
  what does `exchange` do with it?
- Why does `poll` re-check readiness with `select(..., 0)` when the event loop already said the
  socket was readable? (Hint: another callback in the same loop iteration.)
- What did the missing lock allow before W1, and which code calls `request` from a thread that
  is not the event loop's?

**Exercise.** From a blank file: two processes over a `socketpair`. One sends ten framed JSON
messages in a burst; the other reads them with `recv(7)` calls only, and must reassemble all
ten exactly. Then make the sender send a second message type unprompted, and make the reader
tell the two kinds apart.

---

## Part 2 — WebSocket, from the RFC

**Concept.** WebSocket is an HTTP/1.1 request that *upgrades* the connection, then a framing of
its own: FIN, opcode, MASK, and a length that is 7, 16 or 64 bits. Clients must mask what they
send; servers must not. Ping is answered with pong.

**Source.** RFC 6455 §1.3 (the GUID), §4.1–4.2 (handshake), §5.2 (frame layout), §5.3 (masking),
§5.4 (fragmentation), §5.5 (control frames), §5.7 (the worked examples). It is short; read
those sections whole.

**Read.** `ws.py`, then `selftest_ws.py`. Every check in the test uses a value printed in the
RFC, which is why the test cannot share a misunderstanding with the code.

**Answer aloud.**
- What does `Sec-WebSocket-Accept` prove, and what would go wrong without checking it?
- Why must a client mask? (RFC 6455 §10.3: it is about proxies, not secrecy.)
- Why is the socket left *blocking* with a timeout, when the mediator otherwise refuses to block?
  Who is on the other end, and why does that change the answer?
- Why must the timeout be longer than 10 s? (Part 0, item 2.)

**Exercise (level 3, the viva piece).** From a blank editor, write `encode_frame` and a frame
parser, and make them reproduce §5.7's five examples byte for byte. Then diff against `ws.py`.

---

## Part 3 — The mediator's loop, and never blocking on a sandbox

**Concept.** A single-threaded server multiplexes descriptors with `select`/`epoll`. Writes to a
peer that is not reading block once the kernel's socket buffer is full. A server that must never
block writes with `MSG_DONTWAIT`, keeps what did not fit, and asks the selector for writability.

**Source.** `man 7 socket` (`SO_SNDBUF`), `man 2 send` (`EAGAIN`, `MSG_DONTWAIT`), `man 7 epoll`;
Python's `selectors` docs.

**Read.** `mediator.py`: `_Outbox` (its docstring states the three bounds), `drain`, `_flush`,
`serve`. Then `selftest_push.py`, case P7.

**Answer aloud.**
- Name the three places the mediator holds data for one sandbox, and the bound on each.
- Why does the mediator stop *reading* a sandbox's requests while it owes that sandbox a reply,
  and why does that bound the replies at one?
- P7 found 278 frames, not one. Where were they, and why can coalescing not reach them?
- A file descriptor rides with an egress reply. When exactly is the mediator's copy closed, and
  why then?

**Exercise (level 3, the viva piece).** From a blank editor: a selector loop serving two
socketpairs, where one peer never reads. Push 10,000 messages to both. Show that the reading peer
receives the last one, that the loop never blocks, and that memory for the stalled peer stays
bounded. Then remove `MSG_DONTWAIT` and watch it hang.

---

## Part 4 — Record, then act

**Concept.** An audit record is only worth having if it is durable before the action it records;
otherwise a crash between the two leaves an action no record attributes.

**Source.** §5.11.3 and §6.8.3 in the report; then §7.36.1, which shows the order was false for
every acting operation from 2026-08-25 to 2026-10-04.

**Read.** `Decision.act` in `mediator.py`; `_handle_ready` (the record, then the act, then a
second record if acting turned up a refusal); `ActingPolicy` and `_refusable` in `platform.py`.

**Answer aloud.**
- Why did `selftest_audit`'s original ordering test pass while the real path was wrong?
- What is the difference between a refusal while acting and a crash while acting, and why must
  only the first be caught? (Part 0, item 1.)
- Why is ownership now recorded *after* the publish, and what went wrong when it came first?

**Exercise.** Write the smallest program that records-then-acts and crashes between the two, and
show the record survives; then swap the order and show it does not.

---

## Part 5 — The push loop, and the re-check

**Concept.** A subscription is a decision, made and recorded once; deliveries follow from it and
are counted, not recorded (decision A). A state is a value, so an unsent one can be replaced
(decision B). The manifest is re-read at every spawn, explicitly, because a long-lived mediator
no longer does it by accident.

**Source.** `notes/w1_push_loop_prediction.md`; §7.36; §7.30 for why T12's re-check had been an
accident.

**Read.** `Mediator.push`, `_subscriptions`, `register` (the `bind` call); `ActingPolicy.bind`;
in `sandbox_runtime.py`, `subscribe_declared_entities`, `receive_pushes`, `_apply_pushes`;
`selftest_t12.long_lived_mediator`.

**Answer aloud.**
- Why are subscriptions keyed by channel and not by integration?
- What is the mutation in `selftest_push` P5, and why does the zero mean nothing without it?
- Why must the push handler be installed *before* the subscriptions are sent? (§7.37.2.)
- Why does a file edit not re-bind a running sandbox, and why is that correct, not a weakness?

**Exercise.** Remove the `bind` call from `register` and run `selftest_t12`. Predict, before
running, which two checks fail.

---

## Part 6 — The real platform: one connection, three kinds of message

**Concept.** One WebSocket connection to (A) carries answers to the mediator's calls, state
changes, and users' commands, interleaved. A synchronous `call` must sort what arrives and apply
events only when no call is in progress, or a listener that itself calls (A) would read someone
else's answer.

**Source.** Home Assistant's WebSocket API documentation (`auth`, `call_service`,
`subscribe_entities`). In the pinned source, `handle_subscribe_entities` in
`homeassistant/components/websocket_api/commands.py`, and the compressed `a`/`c`/`r` format itself in
`messages.py` (`ENTITY_EVENT_CHANGE`, `STATE_DIFF_ADDITIONS`).

**Read.** `real_platform.py`: `call`, `pump`, `_sort`, `_apply_events`, `watch`, `_Owners`.

**Answer aloud.**
- What is `_depth` for? Construct the failure it prevents.
- Why is the subscription id recorded *before* `subscribe_entities` is sent?
- Re-subscribing to widen the set leaves a moment with no subscription. Why is no state change
  lost? (What does a new subscription send first?)
- A user adds a new device to the house after the mediator connected. Can a sandbox impersonate
  it? Walk the publish path and say where it stops.
- What happens to the mediator when the connection to (A) drops, and is that acceptable?

**Exercise.** With (A) up, write ten lines that subscribe to two entities with `ws.py`, change one
with `input_number.set_value`, and print the raw `c` event. Then apply it to a dict by hand.

---

## Part 7 — The bridge: identity in Home Assistant

**Concept.** In Home Assistant an entity's identity is its registry row, keyed by `unique_id`,
attached to a config entry and usually a device. A bare state has none of it, which is why
publishing through `/api/states` is not enough. Since 2026.8 the friendly name is built from the
registry as device name plus entity name.

**Source.** Developer docs: entity registry, device registry, `RestoreEntity`, entity naming.
`homeassistant/helpers/entity_registry.py` (`_async_get_full_entity_name`) in the pinned source.

**Read.** `ha_bridge/confine_bridge/`: `__init__.py` (the commands, the roster), `entity.py`,
`sensor.py`, `switch.py`.

**Answer aloud.**
- Why is publishing an admin-only WebSocket command rather than a service, as in the spike?
- What makes 15 of 15 states identical after a restart, with no sandbox running?
- Why did every bridged entity get renamed, and what does the sandbox now send to prevent it?
- The bridge assumes one serial client. What would go wrong with two concurrent publishes of a
  new entity, and why can it not happen with this mediator?

**Exercise.** Install the bridge into (A), publish one sensor by hand with `ws.py`, restart (A),
and find its row in `.storage/core.entity_registry`.

---

## Part 8 — Commands into a sandbox

**Concept.** The third inbound direction: a user's call in (A) waits on a future in the bridge
while the command travels to the sandbox and the answer comes back.

**Source.** `notes/w1_step2b_commands_prediction.md`; §7.38.

**Read.** `BridgeData.command` and `ws_commands`/`ws_command_result` in the bridge;
`Mediator.command` and `_answer_command`; `Bridge._run_command` in `sandbox_runtime.py`.

**Answer aloud.**
- Why is a command recorded, and why does it need no manifest clause?
- Why are commands never coalesced when states are?
- How does the mediator stop a sandbox from answering a command it was never sent?
- Trace a command for a sandbox that has just exited. Where is the user told, and how fast?

---

## Part 9 — (A) itself

**Read.** `house_a.py`: onboarding over REST, the long-lived token minted over WebSocket, the
frontend that recovery mode requires, and the HTTP confirmation from Part 0.

**Answer aloud.** Why is the frontend installed beside `ha314` and not into it? Where is the token,
who can read it, and what is R3 here?

---

## Part 10 — What to be ready to defend

- **Two copies of Home Assistant per confined integration**, and why (B) exists at all (§5.6).
- **The unscoped token.** The mediator holds an owner token for (A), so a compromised mediator is
  a compromised house (R3, §5.15.3). The simulated user in §7.38 holds the same token, so the log
  cannot yet tell a user's command from the mediator's own identity.
- **Losing (A) stops the mediator.** No reconnection.
- **Domains.** The bridge stands in for sensors, binary sensors and switches only.
- **Rates.** Every rate measured in W1 was synthetic; a busy home's real rate of change is not
  measured.
- **The head-of-line cost.** One call to (A) blocks the mediator for its round trip, as an egress
  `connect` already does.

---

## A schedule that fits the slack

W1 finished on its first planned day, so about two weeks of its window remain.

| Days | Parts | Gate |
|---|---|---|
| 1–2 | 1, 2 | Exercise 2 done from a blank editor; diffed against `ws.py` |
| 3–4 | 3, 4 | Exercise 3 done from a blank editor |
| 5 | 5, 6 | Questions answered aloud without the files open |
| 6 | 7, 8, 9 | Exercise 7 done against (A) |
| 7 | 10 | Each limit stated in two sentences, as for the viva |

Questions you cannot answer are the review's real output. Write them down; they are either a
gap to study or a defect in the code, and §7.36–§7.38 show that both happen.
