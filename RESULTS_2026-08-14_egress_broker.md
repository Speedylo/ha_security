# Lateral movement closed — the supervisor brokers egress

**Date:** 2026-08-14
**Problem:** the manifest's `network:` allowlist was *advisory*. A raw socket bypassed it, so a
sandboxed integration could reach any LAN device or internet host, unlogged. Probe checks 7 and 8
measured this and both were ALLOWED even with namespaces and seccomp.
**Result: 8 of 8 probe checks now blocked**, all three integrations unaffected, and the redirect
gap closed as a side effect.

**Framing this was built to:** the goal is not a foolproof system — that is not available — but
one where attacking it is expensive, complex, and conspicuous enough not to be worth it. Every
claim below is stated as cost imposed, not risk eliminated.

---

## Why the old check could not work

`aiohttp_client.py` asked the supervisor for permission and then let the sandbox open the socket:

```python
def get(self, url, **kwargs):
    return self._session.get(self._authorise(url), **kwargs)   # ask, then connect ourselves
```

The check bound only an integration that *chose* to use HA's HTTP helper. `import socket` walked
past it. No amount of tightening that check would have helped, because **the sandbox was the party
making the decision.** That is the actual defect — not a missing rule.

## The fix: move the decision to the side that cannot be skipped

Two changes that only work together:

1. **Seccomp denies `socket(AF_INET)` and `socket(AF_INET6)`** in the sandbox, by default under
   `--isolate`. The sandbox has no IP networking at all — no TCP, no UDP, no DNS.
2. **The supervisor performs the request.** `MediatedClientSession` serialises method, URL,
   headers and body over the existing Unix socket; `egress.py` checks the manifest and makes the
   connection; the response comes back the same way.

`AF_UNIX` remains permitted, so the bridge still works. **The bridge is now the only way out.**

The allowlist is enforcing rather than advisory — and the difference is not a stronger promise
about how the integration behaves. It is that the integration is no longer the one choosing.

---

## Result 1 — 8 of 8

| # | Check | Baseline | Isolated + brokered |
|---|---|---|---|
| 1–4 | entity read, enumeration, `lock.unlock`, mediated exfiltration | BLOCKED | BLOCKED |
| 5 | read host filesystem | ALLOWED | BLOCKED |
| 6 | read supervisor's `/proc` | ALLOWED | BLOCKED |
| 7 | **raw socket → undeclared LAN device** | **ALLOWED** | **BLOCKED** ✅ |
| 8 | **raw socket → undeclared internet host** | **ALLOWED** | **BLOCKED** ✅ |
| | | **4 of 8** | **8 of 8** |

```
[BLOCKED] raw socket → undeclared LAN device    socket refused by syscall filter (EAFNOSUPPORT)
[BLOCKED] raw socket → undeclared internet host socket refused by syscall filter (EAFNOSUPPORT)
```

**A measurement correction was needed to get this right.** Checks 7 and 8 first used *hostnames*,
and `socket.create_connection()` resolves before it opens a socket — so they failed with
`gaierror` and never reached the layer under test. Worse, `gaierror` looks identical whether the
name does not exist or the sandbox has no network. Both checks now use RFC 5737 documentation
**addresses**, so what is measured is the socket call, which is where the control sits. The probe
also now distinguishes a *refused syscall* (`EPERM`/`EACCES`/`EAFNOSUPPORT`) from a request that
merely failed in transit — a connection dying on DNS or a timeout is not a control.

## Result 2 — the integrations still do not notice

| Integration | Baseline ops | Isolated + brokered | Audit chain |
|---|---|---|---|
| `andrews_arnold_quota` | 7 | **7** | intact |
| `matomo` | 44 | **44** | intact |
| `icqa` | 18 | **18** | intact |

Unchanged, and none of the three was modified. Between them they cover the three call shapes real
integrations use — `await session.get(...)`, `await session.request(method=, url=, data=)`, and
`async with session.post(...) as resp:` — plus `.status`, `.json()`, `.text()` and
`raise_for_status()`. The shim response object implements exactly that surface and nothing else,
so an unsupported use fails loudly rather than silently returning something plausible.

## Result 3 — the audit log improved

The old record was a permission question. The new one is what actually happened:

```
http_request -> allow | fetched chaos2.aa.net.uk [200]
```

Host, outcome and status, for every request, including each redirect hop. Previously the log
recorded that permission was granted and had no idea whether a request followed, or where it
ended up.

## Result 4 — the redirect gap closed for free

`aiohttp_client`'s own docstring recorded this: only the initial URL was checked, so a declared
host answering `302 Location: https://evil.example` moved the request off the allowlist unnoticed.
Because the supervisor now handles hops itself, **each one is re-authorised**. Verified:

```
DENIED   declared host redirecting off-allowlist   evil.example.net not in manifest network allowlist
```

---

## The part that matters most: this created new attack surface

**Every security control adds threats.** This one is a confused deputy by construction — the
supervisor now parses attacker-controlled URLs, headers and bodies, and issues requests on the
sandbox's behalf. Pretending otherwise would be worse than not building it.

Each limit in `egress.py` exists because of a specific thing the sandbox could otherwise make the
*trusted* process do. All verified:

| Limit | Attack it bounds | Verified |
|---|---|---|
| Scheme allowlist (`http`, `https`) | `file:///etc/passwd` — using the supervisor as a file reader | `DENIED scheme 'file' not permitted` |
| Per-hop re-authorisation, max 5 | Redirect off the allowlist | `DENIED evil.example.net not in manifest` |
| `MAX_RESPONSE_BYTES` = 8 MiB | Memory exhaustion of the supervisor via a huge response | `DENIED response exceeds 8388608 bytes` |
| `MAX_TIMEOUT_SECONDS` = 30 | Holding supervisor threads open indefinitely | capped on entry |
| Header count and length caps | Resource exhaustion via header spam | capped on entry |
| CRLF rejection in header values | Request splitting / header injection | `DENIED header 'X-Evil' contains a line break` |
| Home Assistant's own host blocked unconditionally | An integration declaring HA in its manifest to reach the thing being protected | `DENIED homeassistant.local is reserved to the supervisor` |
| `ProxyHandler({})` | Redirecting egress via ambient `http_proxy` env | no environment proxies honoured |

The last one is worth noting for the report: **the sandbox cannot reach HA even if its manifest
declares it.** It holds no token so it could not authenticate anyway, but an allowlist that can
name the thing the framework protects is a weaker allowlist than one that cannot.

**Residual, and honestly stated:** `egress.py` is ~170 lines of the trusted computing base that
did not exist this morning. It is small and reviewable, which is the mitigation, but it is real.
A bug there is a bug in the trusted half.

---

## What this costs an attacker now

The useful question is not "is it secure" but "what does an attacker have to do".

**Before:** add one line — `socket.create_connection(("192.168.1.50", 80))` — reach any device on
the user's LAN, leave no record.

**After**, an attacker wanting to reach an undeclared device must do one of:

1. **Declare the host in the manifest.** Then it is *visible* — in a public repository, in a
   reviewable file, with a weather integration inexplicably declaring the lock's address. This is
   the intended outcome: the control converts an invisible capability into a declared one. It does
   not prevent the attack; it makes it conspicuous.
2. **Find a bug in `egress.py`** — a scheme parser confusion, a redirect edge case. ~170 lines,
   which is why keeping it small is itself the control.
3. **Break out of the seccomp filter or the namespaces.** A kernel exploit. Much higher cost than
   one line of Python, and the seccomp denylist deliberately removes the syscalls most often used
   in those chains (`bpf`, `perf_event_open`, `userfaultfd`, `io_uring_setup`).
4. **Abuse a host it legitimately declared** — see below. Still open, and structurally so.

That is the argument. Not "impossible", but *one line of Python* → *a visible manifest entry, a
bug hunt in trusted code, or a kernel exploit*.

**The open-source angle strengthens option 1 specifically.** HACS integrations are public
repositories. A raw `socket.create_connection` in one is reviewable — but nobody reviews for it,
because there is nothing to compare it against. A manifest gives reviewers a **declared baseline**,
and makes the interesting question mechanical: *does this integration's declared reach match what
it plausibly needs?* A weather widget declaring `192.168.1.50` answers itself. The control's value
is as much in what it makes checkable as in what it blocks.

---

## What is still open

- **Exfiltration through a declared host.** If the manifest allows `api.vendor.com` because the
  integration genuinely needs it, stolen data can be encoded into requests to that host. An
  allowlist governs *destination*, not *content*. **Structural — no allowlist fixes this**, and it
  belongs in the threat model as accepted.
- **Declared-capability abuse** — the 3am unlock (§10.1). Unchanged.
- **Resource exhaustion.** No cgroups. A fork bomb still takes down the Pi.
- **WebSockets are not brokered.** `ws_connect` raises `NotImplementedError` rather than falling
  through to a real socket — failing loudly is the point, since silently falling through is
  precisely the advisory-check mistake this replaced. An integration needing WebSockets does not
  run under the framework today.
- **aarch64 / the Pi remains unverified.** Unchanged and still the cheapest outstanding check.

---

## Files

| File | Lines | Job |
|---|---|---|
| `spike/egress.py` | ~170 | **New.** Supervisor-side HTTP with the policy above |
| `spike/shim/.../aiohttp_client.py` | rewritten | Session with no network; serialises over the bridge |
| `spike/supervisor.py` | +30 | `http_request` op; rewrites moved here from the sandbox |
| `spike/isolate.py` | +5 | `AF_INET` denied by default; `HACS_ALLOW_INET=1` restores the old behaviour |
| `spike/probe.py` | ~+20 | IP literals instead of hostnames; errno-based blocked detection |

`net_request` is retained but unused by the shim, so the old advisory behaviour stays reproducible
for the evaluation chapter's before/after.
