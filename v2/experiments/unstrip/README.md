# Experiment — un-stripping toward `http`, and what it costs

**Run:** 2026-08-25 · **Target:** Raspberry Pi 5, 4 GB, aarch64 (the C4 hardware), Python
3.14.7, Home Assistant 2026.8.3 · **Feeds:** §6.12 · **Answers:** §6.11.5's first G3 option

§6.11.3 measured that 16 of 37 community integrations fail against the minimal instance for want
of a component they declare, and that **`http` alone accounts for ten of them**. §6.11.5 offered
three ways forward and called the first the smallest step with the largest expected return:
un-strip toward `http` and pay the footprint. This measures the payment.

## Result

| | Minimal | Un-stripped | Change |
|---|---|---|---|
| **Import-level compatibility** (37 integrations) | 17/37 — **46%** | 26/37 — **70%** | **+24 points** |
| ...with each integration's own declared components too | 21/37 — 57% | 28/37 — **76%** | +19 points |
| Integrations failing for want of a component | 16 | 8 | −8 |
| **PSS per sandbox**, same harness | **54.5 MB** | **130.4 MB** | **+75.9 MB** |
| Sandboxes in 60% of 4 GB, same harness | 44 | **18** | −59% |

**Two changes made it work, and one of them is free.**

## 1. `http` needs an authentication manager, which costs nothing and is the whole blocker

`async_setup_component(hass, "http", {})` returned `False` on a minimal instance with no
exception and no explanation. The reason, once Home Assistant's own log was captured:

```
AttributeError: 'HomeAssistant' object has no attribute 'auth'
  homeassistant/components/http/auth.py:113  hass.auth.async_create_system_user(...)
```

§5.6.3 built the minimal instance with "no HTTP server, no recorder, no frontend and **no
authentication**". `http` will not set up without the third.

One line — `hass.auth = await auth.auth_manager_from_config(hass, [], [])` — takes the cascade
from **0/11 components to 10/11**, and costs **0.1 MB** (73.4 → 73.5 MB). Everything else that
failed was failing *because* `http` had, and said so: "Unable to set up dependencies of
'websocket_api'. Setup failed for dependencies: ['http']".

**This collides with §5.10.3, which is why it is worth arguing rather than assuming.** That
section says `hass.auth` "has no clause and cannot be declared. Users and tokens are the
platform's authentication state; a design whose whole purpose is to keep credentials away from
third-party code should not offer a permission that hands them over."

The manager here is constructed **with no providers**, so its store contains no users, no
credentials and no tokens belonging to anyone. The system user `http` creates belongs to the
sandbox's own store and authenticates against the sandbox's own server, which is bound to the
sandbox's own loopback inside its own network namespace and reaches nothing. It is the same
pattern as the empty state machine and the empty service registry: **a real object whose contents
are nothing.** §5.10.3's refusal stands — what is denied is any route to the *installation's*
auth manager, and this is not one.

## 2. A new network namespace's loopback is down

With auth wired, `http` set up on the host and still failed inside a sandbox. The only clue:

```
homeassistant.components.network: Because the system does not have any enabled IPv4 addresses,
source address detection may be inaccurate
```

**A freshly created network namespace contains a loopback interface, and it is `DOWN`.** Anything
that binds a socket fails until it is raised. §5.7.3 describes the namespace as giving "no route
to anywhere", which is accurate and incomplete — it also gives no *working* loopback, and that is
a different thing that has to be granted deliberately.

One `SIOCSIFFLAGS` ioctl in the supervisor fixes it, and the grant is narrow by construction: the
interface exists only inside that namespace, so the sandbox gains the ability to talk to itself
and nothing else. Nothing routes out; that remains the mediator's job.

## What each component costs

Measured in-process on the host, cumulative, in the order Home Assistant resolves them:

| Component | Cost | Running total | Integrations it unblocks |
|---|---|---|---|
| minimal instance | — | 73.5 MB | — |
| auth manager (no providers) | **0.1 MB** | 73.5 MB | none directly; all of the below |
| **`http`** | **37.8 MB** | 111.3 MB | **10** |
| `websocket_api` | 0.0 MB | 111.3 MB | 3 |
| `frontend` | 26.1 MB | 137.4 MB | 3 |
| `lovelace`, `panel_custom`, `repairs`, `media_source`, `notify` | 0.6 MB total | 138.2 MB | 4, 2, 1, 1, 1 |
| `mqtt` | 12.2 MB | 150.4 MB | 6 |
| `stream` | 28.3 MB | 178.8 MB | 2 |

`python_script` is the one that does not set up, and only because the configuration directory has
no `python_scripts` folder — not structural.

The packages these components require are **449 MB on disk**, dominated by `av` (PyAV) and
`home-assistant-frontend`. They are the platform's own packages, so they are bound read-only and
shared between sandboxes exactly as the `homeassistant` library already is; an integration's own
dependencies stay in a directory of its own.

## The cost at scale, which is the number Gate G3 needs

Peak resident memory is not the budget. §6.3.2's figure is proportional set size across six live
sandboxes, so the successor is measured the same way — `scale.py`, six sandboxes, same probe in
both arms:

| | PSS per sandbox | Sandboxes in 60% of 4 GB |
|---|---|---|
| Minimal | 54.5 MB | 44 |
| Un-stripped | **130.4 MB** | **18** |

**+75.9 MB per sandbox, and the budget more than halves.** That is a far harsher figure than the
per-sandbox *peak* suggested (a median of 100 → 133 MB), and the difference is why PSS is the
figure that decides anything.

> **Translating to §6.3.2's number.** This harness uses a trivial probe; §6.3.2's used one with a
> sensor platform and a coordinator, and measured 90.0 MB. The same +75.9 MB delta puts a
> realistic integration in an un-stripped sandbox at roughly **166 MB PSS, about 14 sandboxes**.
> That is an estimate from a measured delta, not a measurement, and Chapter 7 should take it
> directly.

Against §5.8.1's figure of **4.02** community integrations per HACS-using installation, 14 is
still three and a half times what a typical installation needs.

## What this suggests, and it is not the profile that was measured

The blanket profile pays for `stream` (28 MB, 2 integrations) and `frontend` (26 MB, 3) in every
sandbox including those that need neither. The auth manager — which is what actually unblocks the
cascade — costs 0.1 MB.

**So the indicated design is to wire auth always and set up components per integration, on
demand from its own manifest.** That was not measured here: the per-integration arm ran without
auth wired, which is why it reached only 57%. Re-running it with auth is the obvious next
measurement and is expected to approach 70–76% at well under 130 MB for integrations that
declare little.

## Limits

- **Import-level only.** Everything here inherits `experiments/compat/`'s limits: imports-clean
  is an upper bound, there is no baseline arm against a full Home Assistant, and the corpus is
  head-weighted.
- **The scale figure uses a trivial probe.** Comparable between the two arms and not comparable
  to §6.3.2's without the translation above.
- **`http` binds a real socket in each sandbox.** Ports do not collide because each namespace has
  its own, but nothing here tests what happens when an integration uses that server.

## Reproducing

```bash
uv pip install --python <interp> --target ./platform-deps \
    PyTurboJPEG==1.8.3 RestrictedPython==8.1 av==17.0.1 \
    home-assistant-frontend==20260729.7 numpy==2.3.2 paho-mqtt==2.1.0

PYTHONPATH=./platform-deps <interp> unstrip.py --auth      # per-component cost, on the host
systemd-run --user --scope -q python3 scale.py --count 6 \
    --python <interp> --profile unstripped --platform-deps ./platform-deps
```

`unstrip.py --requirements` prints the package list. Omitting `--auth` reproduces the 0/11
failure that started this.

## Re-run 2026-10-03 — §7.31.12, `results/rerun_20261003/`

`scale.py` on the instance §7.31 corrected: **56.5 MB and 135.7 MB PSS per sandbox, capacity 42 and
17, premium +79.2 MB** (was 54.5 / 130.4 / 44 / 18 / +75.9), within §7.20.3's run-to-run variance.
`unstrip.py` keeps its own frozen `build_hass` and was not re-run.

**The `unstripped` arms need this README's own dependency list**, not `~/r2exp/platform-deps`, which
was rebuilt on 2026-09-02 from the core requirements and no longer holds `paho-mqtt`. Run against it,
compatibility kept 26/37 with eight members swapped (`*_currentdeps.*`, kept as a record of the
mistake); against this list (`*_augdeps.*`) it is identical to August's member for member.
