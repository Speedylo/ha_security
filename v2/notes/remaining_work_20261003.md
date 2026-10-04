# What is left, and in what order — 2026-10-03

**This is the live plan.** `STATE.md`'s top section points here. Written after T1–T6 and §7.35 closed,
when Younes said there are **at least 1.5–2 months before the final report is due**. That changed the
earlier advice ("go straight to the report"), because there is now room for the two engineering items
that most improve credibility before writing starts. The order below was proposed by me and Younes
asked for it to be recorded as the plan.

## 1. Where things stand

- **All engineering in the T-table (T1–T6) is done**, and so are the two small debts in §7.35 (the
  audit log's directory fsync and §8.7 item 12). Every framework experiment has been re-measured on the
  corrected instance. All 20 `selftest_*` suites plus the base `selftest` pass on the Pi (re-run against current code, logs in `experiments/selftests/results/final_20261003/`).
- **The report (`report/`) is current** up to §7.35, and `report/toc.py --check` passes.
- **The submission draft (`submission/`) is stale.** It still has the old figures: nineteen suites,
  one-in-five end-to-end cost, and §12.8's "unresolved" depth series. Checklist item 5's sweep found 11
  stale statements of absence in it.
- **Diary 1** (`Diary1.docx`, period Sep 23–Oct 9) is filled in, apart from the supervisor's name and
  the meeting summary, which only Younes knows. Its action plan (Oct 9–20) matches W1 below. It reports the real work of the period, which is
  **inconsistent with the proposal's prospective timeline** (that timeline puts implementation from
  12 Oct). Raise this with the supervisor; every later diary will meet the same mismatch.

## 2. The plan

| Weeks (from 5 Oct) | Work | Notes |
|---|---|---|
| **1–2** | **W1: the real Home Assistant component, plus the push loop, plus §8.7 #14's re-check trigger** | One job: the three are coupled (see §3 and §4 below). *2026-10-04: split into two steps; **step 1 done** — the push loop and the re-check against the stand-in, plus the record-before-act defect it found (§7.36, `notes/w1_push_loop_prediction.md`). Step 2, the real component, is next* |
| **3** | **W2: the small items.** (a) one plain-`socket` integration confined; (b) UDP in a real sandbox, plus asyncio datagram endpoints; (c) whether a confined sandbox reads the bytecode cache; (d) token refresh, if a free OAuth integration can be found | (c) is minutes; do it first |
| — | **Hard cut-off after week 3: no new engineering.** Every new piece adds sections and corrections the rewrite must absorb | |
| **4–6** | **R: the report.** Submission rewrite against current figures (checklist item 5); ~8 figures, each generated from source with an assertion it still matches the prose; appendices B–F (Appendix D is what lets an examiner check the zero-compatibility-cost claim); the first full read-through; three `[To verify]` citations; four handbook-blocked title-page fields | |
| **7** | **D: the defence.** Presentation, and a live or recorded demo (deliverable D5 in the proposal). After W1, the demo can show a confined integration's entity in the real Home Assistant UI and a click reaching it | |
| **Throughout** | `notes/learning_curriculum.md`, a little each week. The viva will ask about namespaces, seccomp, `SCM_RIGHTS` and the audit chain | Younes's standing wish to own the substrate |

Everything not in this table is future work and is already written up as such in §8.7 (§5 below).

## 3. The real Home Assistant component — what it is, and why it is not "already there"

There are **two Home Assistants** in the design, and only one runs in the experiments.

```
 (A) the house's real Home Assistant — dashboard, devices, automations, UI
        ▲  step 5: the mediator acts here
   mediator — decides against the manifest, writes the audit record
        ▲  Unix socket
 sandbox: (B) a stripped, private Home Assistant (one per sandbox, empty registries)
             └─ the unmodified integration
```

- **(B) is real and runs in every experiment.** It exists for API compatibility: the integration gets
  the genuine `hass`, `async_add_entities`, `DataUpdateCoordinator` and so on. It is private to one
  sandbox and nobody looks at it.
- **(A) has never run in the confined arm.** The mediator's step 5 acts on `framework/confine/platform.py`'s
  `Platform`: two dicts and a list (`states`, `owners`, `calls`). A published sensor lands in a dict; a
  permitted `lock.unlock` is appended to a list and never executed. The unconfined baseline arm runs a
  full Home Assistant, but nothing in the confined arm is connected to it.
- **So:** everything up to and including the mediator's decision is proven. The last hop, what a
  live (A) does with a mediated result, is not. §8.6.3 limitation 2; §8.7 item 2.

**What the real component changes:**

1. **Entities get a real identity, not just a state.** Publishing over (A)'s states API with a token
   gives a bare state: no entity-registry row, no `unique_id`, no device, no config entry, nothing that
   survives a restart. 83% of integrations publish through `async_add_entities` precisely to get those
   (§5.6.1). So the component is a small custom integration inside (A), a **bridge**, which owns a
   config entry and creates registry-backed entities on each sandbox's behalf. The spike's
   `sandbox_bridge` found this gap. Under `00_METHOD.md` §2 that finding is private knowledge and must be
   re-measured here, not cited.
2. **Service calls really execute**, using a real (A) credential held only by the mediator.
3. **Traffic must flow inward**, which does not exist today. That inward direction is the push loop (§4).

**Shape of the work.** A bridge custom integration in (A). A `RealPlatform` with the same interface as
`Platform`, which slots in cleanly because `acting_policy` already takes the platform as a parameter.
New inbound message types on the channel, which are manifest-checked and audited, since an undeclared
inbound state would be a read leak.

**Measurements to make.** Confined entities appear in (A)'s registry and survive a restart; a command
reaches the confined integration; push latency against the fsync headroom; the security suites re-run
against the real platform. Predictions are registered first, as always.

## 4. The push loop — and why it drags §8.7 #14 in with it

**Today** every message goes sandbox → mediator → answer. Declared entities are copied into (B) **once**
when the sandbox starts (`mirror_declared_entities`), and never again (§6.10.5). The manifest has an
`entities.subscribe` permission and the mediator decides it (§7.14 tested refusal), but a granted
subscription delivers nothing.

**Worked example:** `thermal_comfort` computes dew point from the living-room temperature and humidity.
Confined, it computes once from the start-up values and is then frozen, because no update ever arrives.

**The push loop:** the mediator watches (A) for changes to each sandbox's declared entities and pushes
each change down that sandbox's socket. The sandbox bridge writes it into (B) with
`hass.states.async_set`, which fires the integration's own listener. No change to the integration.

**Why it is the largest missing piece:**

- **It reverses the channel's direction.** The mediator now speaks first, so the sandbox must listen for
  unrequested messages while also sending its own requests over the same socket. That is a protocol
  change.
- **It is half of S3.** "Sees only what it declared" holds for subscriptions today only because nothing
  is delivered. With a push loop, the mediator's filter is doing real work and can be tested.
- **It is the one load that could exhaust the performance budget.** One audited decision costs about
  3.7 ms of fsync, so the mediator can handle about 272 per second. Today's demand is about 4 per
  second (63× headroom, §7.20.1), but a busy home emits many state changes per second, fanned out to
  several sandboxes. Unmeasured.

**The coupling to §8.7 #14 is easy to miss and must not be.** T12's "declaration re-checked per version"
holds today **by accident**: every spawn builds a fresh mediator policy, so the manifest is re-read. A
push loop needs a mediator that **outlives** sandbox respawns. At that point the accidental re-read
disappears, while `selftest_t12` **keeps passing** (§7.30.2, §7.30.4). So building the push loop makes an
explicit manifest reload at each spawn mandatory, together with a `selftest_t12` change that tests it.

The push loop can be built against the stand-in `Platform` first, by changing a dict value and pushing
it, but its natural event source is (A)'s event bus. Hence W1 is a single job.

## 5. The small items (W2), in plain terms

- **(a) Plain `socket` integration, confined.** Integrations use three network stacks: `aiohttp`,
  `requests`/`urllib3`, and plain `socket`. The first two have run end to end in a sandbox (§7.31). The
  third is intercepted by the egress shim and passes its self-test, but no real integration has
  exercised it in a sandbox. "The others are presumably fine" was wrong once already (§7.27). The corpus
  members (`localtuya`, `midea_ac_lan`) need a device or an account, so this probably needs a small
  integration of our own, or recorded fixtures.
- **(b) UDP in a real sandbox.** TCP is pinned by handing over a connected socket. UDP cannot be, so every
  datagram is copied through the mediator and checked in software. `udp_relay` has been tested only
  against the decision path (`selftest_udp`), never across real namespaces. And only the synchronous
  shape is served: integrations on `asyncio.DatagramProtocol` (`govee`, `localtuya`, `tapo_control`,
  `xiaomi_miot`, 4 of the 15 UDP users) wait on a socket that does not exist and **fail closed**
  (`selftest_udp` case 7).
- **(c) Bytecode cache in the sandbox.** §7.35.4 found that §5.6.3's 176 MB was a cold start. The
  sandbox binds the interpreter read-only, so if bytecode is not precompiled at install, every start
  could be cold: about +16 MB and 4–5 s. One `scale.py` run with an empty cache prefix inside the
  sandbox settles it.
- **(d) Token refresh.** Pirate Weather's key is static (§7.34.4). OAuth integrations swap an expiring
  token later, at a phase nobody has observed. This needs a free OAuth integration, and finding one is
  the hard part.

## 6. Future work, and staying that way (§8.7)

Static analysis to derive manifests (#3; the only remaining measured compatibility cost, `dwd_weather`'s
missed host); a filesystem quota (#9; needs a privilege decision against the unprivileged design rule);
end-to-end at scale (#10; blocked on credentials for 26 of 37 — a different project); off-box audit
anchoring (#11; the log already emits what it would consume); enforcement in Home Assistant's own loader
(#13; needs the maintainers, and our measurements are the evidence it would need). **#14 moves into W1**
if the push loop is built.

## 7. Rules that still apply

Predictions are committed before each run and never revised. Corrections are dated pointers, not
deletions. Sync both `framework/` and `experiments/` to the Pi. Use `~/r2exp/t2/platform-deps-aug`
for August-era comparisons. Record the configuration actually measured in the output itself (§7.35.3's
lesson). Never use a variable-expanded `rm`. The Pirate Weather key stays at
`~/.config/capstone/pirateweather.key` on the Pi and is never printed or committed.
