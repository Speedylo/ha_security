# Isolation spike — namespaces + seccomp work end to end

**Date:** 2026-08-14
**Question:** *Can this project actually be completed end to end?* Specifically: is workstream 4
(isolation) buildable, or is it a hole the plan cannot close?
**Answer: yes, and it is smaller than expected.** A working implementation is ~260 lines across
two new files, needs no root, and is transparent to the integrations.

> ⏭️ **Snapshot — superseded the same day for rows 7 and 8.** This document records the isolation
> spike as it stood, ending at **6 of 8** with network egress honestly open. Those two rows were
> closed hours later by supervisor-brokered egress — see
> **`RESULTS_2026-08-14_egress_broker.md`**, which takes the probe to **8 of 8**. The body below
> is left as written, because the gap it reports is what motivated the next piece of work.

---

## What was built

| File | Lines | Job |
|---|---|---|
| `spike/isolate.py` | ~230 | Builds an allowlisted root filesystem, pivots into it, mounts a private `/proc`, then execs the runner |
| `spike/syscall_filter.py` | ~110 | Seccomp policy — denies 25 syscalls a polling integration provably never needs |
| `spike/supervisor.py` | +20 | New `--isolate` flag; also strips `HA_TOKEN` from the child's environment |
| `spike/probe.py` | +50 | Three new adversarial checks (#6 `/proc` credential theft, #7 lateral movement, #8 exfiltration) |
| `spike/run_targets.sh` | +5 | `ISOLATE=1` to run every target isolated |

Run it:

```bash
./run_spike.sh --probe --isolate      # one integration, eight adversarial checks
ISOLATE=1 ./run_targets.sh            # all three integrations, isolated
```

---

## Result 1 — the probe goes from 4/8 to 6/8 blocked

Same integration, same manifest, same supervisor. Only `--isolate` differs.

| # | Adversarial check | Baseline | Isolated |
|---|---|---|---|
| 1 | read undeclared entity | BLOCKED | BLOCKED |
| 2 | enumerate whole house | BLOCKED | BLOCKED |
| 3 | call `lock.unlock` | BLOCKED | BLOCKED |
| 4 | exfiltrate to undeclared host (mediated) | BLOCKED | BLOCKED |
| 5 | **read host filesystem** (`/etc/passwd`) | **ALLOWED** | **BLOCKED** ✅ |
| 6 | **read supervisor's `/proc`** (credential theft) | **ALLOWED** | **BLOCKED** ✅ |
| 7 | **raw socket → undeclared LAN device** (lateral movement) | **ALLOWED** | **ALLOWED** ⚠️ |
| 8 | **raw socket → undeclared internet host** (exfiltration) | **ALLOWED** | **ALLOWED** ⚠️ |
| | | **4 of 8** | **6 of 8** |

**Row 5 is the one that matters most.** It is the 2021 HACS file-theft pattern, named in
`PROJECT_STATUS.md` §8 as *"the single strongest result available"*. It is now blocked, so that
result is reachable rather than aspirational.

**Row 6 closes the finding from this morning.** `FINDINGS_2026-08-14_token_leak.md` documented
routes by which the sandbox reaches the HA token. Routes 2 and 3 read `/proc/<supervisor>/environ`
and `/cmdline`; inside a PID namespace the supervisor has no `/proc` entry at all, so both vanish.
Route 1 (the copied environment) is *not* closed by isolation and was fixed separately in
`supervisor.py` — worth keeping distinct, because it shows isolation is necessary but not
sufficient. Verified with a real token present: baseline reports `readable — CONTAINS HA_TOKEN`,
isolated reports `BLOCKED`.

> **A fourth route was found afterwards**, while checking that the first three were really shut:
> `spike/.ha_token`, an ordinary file the sandbox could `open()`. Mode `0600` restricts other
> *users*, and the sandbox ran as the same user. It was already covered — the mount namespace does
> not put it on the allowlist — but the first pass missed the simplest route while finding the
> clever ones. Recorded in the findings doc as an argument for enumerating **where a secret
> physically lives** rather than reasoning attack-by-attack.

**Rows 7 and 8 are the honest remaining gap, and they are exactly the one predicted.**
`ANALYSIS_2026-08-14_isolation_coverage.md` put this in Category B — *looks like isolation solves
it, actually needs new architecture*. Confirmed: a raw socket bypasses the manifest allowlist
entirely, because the check in `aiohttp_client` is advisory and the connection originates inside
the sandbox.

**Row 7 is the one to lead with, and it is worse than "exfiltration".** Row 8 is data leaving.
Row 7 is the sandbox reaching a device on the user's LAN that the manifest never declared — a
lock's local HTTP API, a camera, the router. **None of those need Home Assistant's credential**,
so closing every token route did nothing about them. Demonstrated directly: under full isolation,
namespaces *and* seccomp, a raw socket reached a live local service and got a response.

That matters because **confining lateral movement is the manifest's central promise.** §10.1
already concedes the manifest cannot stop an integration abusing a device it legitimately declared
(the 3am unlock). This is a step earlier: it cannot yet stop an integration reaching devices it
*never* declared. That is a bigger hole — and unlike the declared-capability limit, it is fixable.

---

## Result 2 — the integrations do not notice

All three unmodified HACS integrations, isolated, compared against their baseline runs:

| Integration | Baseline ops | Isolated ops | Audit chain |
|---|---|---|---|
| `andrews_arnold_quota` | 7 allowed, 0 denied | **7 allowed, 0 denied** | intact |
| `matomo` | 44 allowed, 0 denied | **44 allowed, 0 denied** | intact |
| `icqa` | 18 allowed, 0 denied | **18 allowed, 0 denied** | intact |

Identical. The integrations still poll their vendor APIs, still publish their sensors, still run
unmodified. **Isolation is transparent to the compatibility story**, which is the result that
makes it safe to adopt — it does not trade away the thing the project already proved.

---

## Result 3 — seccomp argument filtering forces the proxy architecture

The default filter is a denylist of 25 syscalls (`ptrace`, `bpf`, `perf_event_open`,
`init_module`, `setns`, `mount`, `userfaultfd`, `io_uring_setup`…) chosen so every entry is
something no integration has a legitimate reason to call. Verified enforcing:

```
$ python3 syscall_filter.py
  sandbox: seccomp filter loaded — 25 rules
ptrace returned -1, errno=1 (EPERM)
PASS
```

Separately, `HACS_DENY_INET=1` adds an **argument-level** rule: allow `socket(AF_UNIX)` — the
bridge — and deny `socket(AF_INET)` / `AF_INET6`. *(That flag was opt-in while denial was
experimental. It is now the default, and the flag inverted to `HACS_ALLOW_INET=1` for restoring
the old behaviour — `HACS_DENY_INET` no longer exists.)*

```
  sandbox: seccomp filter loaded — 27 rules, AF_INET denied
  ERROR root: sandbox: integration failed: Unable to login, please re-login.
```

The integration breaks, **and that is the point.** It proves two things at once: seccomp can
filter on syscall arguments and not just names, and denying IP is what would make the manifest's
`network:` allowlist *enforcing* rather than advisory. The integration's traffic would then have
to leave through the supervisor — i.e. rows 7 and 8 are closable, and this is the mechanism that closes
it. Building the proxy on the other side of that socket remains the Category B work.

---

## What this cost, and what went wrong

Useful for estimating the rest, and every one of these was a *practical* obstacle rather than a
conceptual one — which is the main reason to believe the remaining work is tractable.

1. **Mount ordering.** The scratch `tmpfs` on `/tmp` was mounted *after* binding the bridge socket
   directory, which lives under `/tmp`, so it shadowed the bind and the sandbox lost its only
   route to the supervisor. Fix: mount scratch filesystems first, then apply the allowlist.
2. **Virtualenv paths.** `sys.executable` is `.venv/bin/python`, which is not under `/usr` and so
   was not in the allowlist — `exec` failed with `ENOENT`. Fix: add `sys.prefix` when it lives
   outside `/usr`.
3. **`/etc/ld.so.cache`.** `ctypes.util.find_library("seccomp")` resolves a soname by shelling out
   to `ldconfig -p`, which reads this cache. The library itself was present under `/usr`, but
   without the cache it could not be found. This is precisely the *"a mount namespace needs a
   working minimal filesystem"* risk from Category D, and it is the kind of failure that is
   baffling until you know the mechanism.

None required rethinking the design. All three are the predicted class of problem.

---

## Honest limits of this spike

State these rather than let them be found:

- **Architecture and kernel.** Tested on x86_64 under a WSL2 kernel (6.18). **The Pi 5 target is
  aarch64 and has not been tested.** `isolate.py` carries a per-architecture `pivot_root` syscall
  number for exactly this reason, but arm64 is unverified. Some distributions also restrict
  unprivileged user namespaces. **This is the next thing to check, and it is cheap.**
- **Seccomp is a denylist, not an allowlist.** A default-deny allowlist is stronger. It was not
  attempted because CPython, `aiohttp` and OpenSSL issue a wide, version-dependent syscall set,
  and a wrong allowlist fails by crashing the integration in ways that look like bugs. Tightening
  this should be driven by tracing, not guesswork. The denylist is defensible on its own terms —
  every entry is unnecessary for any integration — but it should not be oversold.
- **No network namespace.** Rows 7 and 8 stay open. Adding `--net` would cut the legitimate vendor poll
  too, so it waits for the supervisor-side proxy.
- **No cgroups.** Resource exhaustion is untouched: a malicious integration can still fork-bomb or
  exhaust RAM. Namespaces isolate visibility, not consumption. Availability is a security
  property and this gap belongs in the threat model.
- **The user namespace is itself attack surface.** Unprivileged user namespaces have a real
  local-privilege-escalation history. The seccomp denylist is partly a response to this (it
  removes `bpf`, `perf_event_open`, `setns`, `unshare`, module loading), but the honest position
  is that this is a syscall boundary, not a machine boundary — the trade-off already accepted in
  Decision 2.
- **New dependency.** `pyseccomp` (and `libseccomp` on the host). Chosen over hand-written BPF
  because the resulting policy is readable — `add_rule(ERRNO(EPERM), "ptrace")` — which matters
  for a codebase that has to be defended line by line.

---

## What this means for the plan

**Workstream 4 moves from "not started at all" to "core built, two gaps identified".** It was the
largest unstarted piece and the one that made the plan look risky. It is now the smallest of the
remaining engineering pieces.

Against `PROJECT_STATUS.md` §10.2's five workstreams:

| # | Workstream | Before today | After |
|---|---|---|---|
| 1 | Evidence / measurement | ✅ done | ✅ done |
| 2 | Compatibility (shim) | ✅ done, frozen | ✅ unchanged — isolation did not disturb it |
| 3 | Mediation / policy | ✅ core done | ✅ core done; now *unavoidable* for filesystem and process, still evadable for network |
| 4 | **Isolation** | ❌ **not started** | ✅ **working spike; network + cgroups outstanding** |
| 5 | Evaluation + write-up | ⚠️ 2 of 4 axes | ⚠️ unchanged, but the security axis now has a real before/after table |

**The end-to-end question is answered.** Every workstream now has either a result or a
demonstrated mechanism. Nothing in the plan is now blocked on something unproven.

Remaining work in value order: verify on aarch64; write the threat model; build the egress proxy
(Category B); add cgroups; HMAC the audit chain.
