# Experiment — Corno & Mannella's garbage-collector attack, with the credential real

**Run:** 2026-09-02 · **Target:** Raspberry Pi 5, aarch64, HA 2026.8.3, Python 3.14.7 ·
**Feeds:** §7.15 · **Discharges:** §7.5's S1, the baseline half

§2.4.1 is the single published result that eliminates every in-process design: an integration
walks `gc.get_objects()` to reach *another* integration's live object and read its private
state. It is the reason S1 (enforcement outside the integration's process) and S2 (the
credential held away from it) exist.

§6.9's adversary suite already runs the sweep confined and finds nothing — but with only its own
integration in the process, "found nothing" is close to a tautology, and that arm has no victim
whose secret it *could* have found. This experiment supplies the missing half.

## The pairing

| | Where the credential lives | Where the adversary runs |
|---|---|---|
| **Unconfined** | a victim integration's live client object, same process | co-resident integration, same process |
| **Confined** | the **mediator's** process (S2) | a **sandbox** (S1), a different process |

The same sweep (`gc_probe.GC_SWEEP`) runs in both arms. The victim is a real custom integration
(`victim_cloud`) set up through the platform's own config-entry path, so its token enters the
heap through its actual `async_setup_entry` — not placed there by the test.

## Result

```
UNCONFINED — victim integration and adversary in one process
  victim's token reached by the heap walk : YES — 7 live objects held it
  reached as                              : CloudClient.attr, dict-value, module.attr

CONFINED — credential in the mediator (S2), adversary in a sandbox (S1)
  adversary's heap                        : 8942 objects, all its own
  token reached by the heap walk          : no
  same token live in the mediator process : yes (7 refs)
```

Raw output: `results/pi5_s1.json`.

**Unconfined, the attack succeeds** — the token is reached seven ways, including directly off the
victim's `CloudClient` instance attribute and through `hass.data`'s nested dict. No traversal, no
exploit: `gc.get_objects()` is a supported API returning live objects.

**Confined, it finds nothing** — and the same token is confirmed live in the mediator's process
(7 references) at the same time, so "nothing" means *unreachable across the process boundary*,
not *absent*. That confirmation is the point of the third line: without it, the adversary finding
nothing would be uninformative.

## Why this is the faithful reproduction, and §6.9 was not

§6.9's confined sweep reported `EMPTY — 11,488 objects, all its own`. True, but a process holding
one integration holds one integration's objects; the result is near-tautological because there
was no other secret in the process to find. Here the secret **exists**, is **live**, and is
**gc-reachable** — demonstrated in the unconfined arm and re-confirmed in the mediator — and the
sandbox boundary is what stops the adversary reaching it. That is S1 and S2 doing the work
§2.4.1 says they must, measured rather than only cited.

## Limits

- **The confined credential is the mediator's, not a second integration's.** That is the
  design's own claim (S2 puts the platform credential in the mediator), and it is the right
  thing to protect. It is *not* a reproduction of two confined integrations failing to reach
  each other; each is in its own sandbox by construction, and two-sandbox mutual isolation is a
  separate demonstration (`selftest_channel`).
- **The adversary here runs only the sweep**, not a full integration. §7.13's adversary is the
  full hostile integration; this experiment is narrowed to S1's published attack so the victim
  and the credential can be made real.

## Reproducing

```bash
systemd-run --user --scope -q python3 -m confine.selftest_gc \
    --python ~/r2exp/ha314/bin/python --json results/pi5_s1.json
```
