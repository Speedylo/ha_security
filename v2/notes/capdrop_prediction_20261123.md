# Prediction: dropping every capability before the integration starts (2026-11-23)

Written before the test or the fix exists (freeze rule: prediction → fails first → fix → rerun).

## The defect (found 2026-11-22, session 8)

`enter.py` builds the sandbox as uid 0 in a new user namespace, then installs seccomp and calls
`execve`. Nothing drops a capability on the way, and uid 0 keeps a full set across `execve`. So the
integration itself holds every capability over its own namespaces: `CAP_NET_ADMIN` (the gate in front
of the netfilter / nf_tables code behind the known user-namespace escalations), `CAP_NET_RAW`,
`CAP_SYS_ADMIN` over its UTS namespace, and the rest. They reach nothing outside the sandbox, but
they put capability-gated kernel code within the integration's reach for no reason: every step that
needs them is finished before `execve`.

## Fix

Just before `execve`, after seccomp: drop every capability from the bounding set
(`PR_CAPBSET_DROP`), clear the ambient set, and clear the inheritable set (`capset`). With the bounding
and inheritable sets empty, `execve` gives uid 0 an empty permitted and effective set.
`no_new_privs` (already set by seccomp) stops file capabilities from adding any back. Seccomp stays
as it is: `unshare(CLONE_NEWUSER)` needs no capability and would hand a full set back, so the
filter's refusal of new namespaces is what makes the drop stick. The two layers are complementary.

## Predictions

P1 (fails first, laptop, current code): four new adversary attempts return LEAKED:
  - capabilities held: CapEff in `/proc/self/status` is non-zero;
  - change a network interface (`SIOCSIFFLAGS` on `lo` with its current flags): `CAP_NET_ADMIN`;
  - open a raw socket: `CAP_NET_RAW`;
  - set the hostname to its current value: `CAP_SYS_ADMIN` over the UTS namespace.
  The suite FAILS with LEAKED 4; the other attempts as before (BLOCKED 26 on the laptop).
P2 (laptop, fixed): the capability read is EMPTY (CapEff, CapPrm, CapBnd, CapAmb all zero) and the
  other three are BLOCKED (EPERM); PASS; LEAKED 0; preflight READY.
P3 (Pi, 27 Nov): preflight READY; 36/36 suites; adversary PASS, LEAKED 0 (BLOCKED 28 + 1 EMPTY);
  the 77 evaluated integrations give the same per-integration outcomes as the final2 rerun
  (1 Nov). Expected because no evaluated integration needs a capability at run time (search of the
  37 corpus integrations on 22 Nov: one hit, `xiaomi_home` SO_BINDTODEVICE, which has no LAN
  interface to bind in a sandbox anyway).

## Falsifiers

- P1 fails (no LEAKED against current code): the defect is not as described; stop and re-check.
- Any suite or any of the 77 integrations changes outcome after the fix: that integration needs a
  capability. Then fall back to option (b): revert the drop, disclose the limit, prepare the answer.
- Home Assistant does not start in a sandbox after the fix.

## Report (if P2 and P3 hold)

F76 (rating for Younes), counts 75 → 76 everywhere the F72–F75 update touched; number check; rebuild
before the signature on 30 Nov.

## Outcome (2026-11-23, results `experiments/verify/results/capdrop_20261123/`)

P1 HELD on both machines (laptop LEAKED 4 / BLOCKED 26; Pi LEAKED 4 / BLOCKED 25). P2 HELD (laptop PASS,
LEAKED 0; preflight READY). P3 HELD: Pi preflight READY; suites 36/36 twice; adversary BLOCKED 28, EMPTY 11,
LEAKED 0; the 77 confined measurements 0 differences from final2; the fifteen against real (A) as on 1 Nov
except the live-value check (nordpool failed once on a price change; rerun 16/16; regensburg passed this
time). No falsifier fired. Timing control: the slower install-bearing steps are not the drop (390 s
without, 400 s with). Next: Younes rates F76; commit the three framework files; report.
