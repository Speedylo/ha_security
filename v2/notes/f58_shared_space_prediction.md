# F58, internet egress accepts 100.64.0.0/10: predictions for the fix

**Written 2026-10-10, before the test is changed and before any run.** F58
(`notes/verification_plan_20261005.md`): `egress.is_public` refuses every address Python's
`ipaddress` calls private, loopback, link-local, multicast, reserved or unspecified, and accepts the
rest. RFC 6598's shared address space, 100.64.0.0/10, is none of those, so it passes as public.
Carrier-grade NAT uses that range between a household and its provider, and Tailscale numbers its
devices from it; `is_public("100.86.243.57")`, the Pi's own Tailscale address, is `True`. A granted
name that resolves into the range is therefore connected to. Younes decided on 2026-10-10 that the
fix waits until his review of §9 was complete; it was, the same day. Commit this note before the test
runs; do not edit it after a run (`verify/prereg.py`). Results go to `experiments/verify/results/f58/`.

## 1. Why this range, and only this range

For IPv4, Python defines `is_global` as "not private and not in 100.64.0.0/10". Every other range
`is_global` excludes is already excluded by `is_private`, which is the first term of `is_public`'s
test. So 100.64.0.0/10 is the whole IPv4 gap. For IPv6, `is_global` is essentially `not is_private`,
which `is_public` already applies. IPv4-mapped IPv6 is unwrapped before the test, so
`::ffff:100.64.0.1` falls into the same gap and is closed by the same change.

## 2. The fix

One term is added to the predicate, after the unwrap and inside the same expression, with the range
named as a constant: `SHARED_ADDRESS_SPACE = ipaddress.ip_network("100.64.0.0/10")` and
`or parsed in SHARED_ADDRESS_SPACE`. `is_global` was considered and not used: it would close the
same gap, but it overlaps `is_private` entirely, so the existing mutant M04 (dropping `is_private`)
would stop being killable, and the predicate would no longer say which range it adds. `is_lan` is
not changed: 100.64.0.0/10 is not private, so a local clause never reached it either.

## 3. The test, written first

`selftest_egress` case 4b lists addresses that must not count as public. It gains `100.64.0.1`,
`100.127.255.254` and `::ffff:100.64.0.1`, placed first so that the loop, which stops at the first
public address, names `100.64.0.1`. Its label gains "shared address space". Nothing else in the
suite changes.

**M04's snippet follows the code.** Its mutation is unchanged (drop `is_private`), but its exact
text now spans three lines. **A new mutant, M38**, drops the shared-space term. Both are regenerated
by `verify/mutants/mutants.py`.

## 4. Predictions

**R1, the test before the fix** (the test commit, on the laptop's Python 3.12 and on the Pi's 3.14):
`selftest_egress` fails exactly one check, 4b, naming `100.64.0.1`, and exits non-zero. The other 22
checks pass.

**R2, after the fix**, on both: 23/23, exit 0.

**R3, the predicate directly** on the Pi's Python 3.14: `True` for `93.184.216.34`, `1.1.1.1` and
`2606:4700:4700::1111`; `False` for `100.64.0.1`, `100.86.243.57`, `100.127.255.254`,
`::ffff:100.64.0.1`, `192.168.1.50`, `224.0.0.251`, `ff02::fb` and `240.0.0.5`. `100.63.255.255`
and `100.128.0.0`, just outside the range, stay `True`.

**R4, mutants** at the fix's tag on the Pi: M04 still applies and is killed by `selftest_egress`
(4b, a 192.168 or 10/8 address). M38 is killed by `selftest_egress` (4b, `100.64.0.1`). M05, M06
and M25 apply unchanged, with M06 killed and M25 equivalent, as on 2026-10-06.

**R5, `nordpool` end to end** at the tag: 16/16 as before, because its API resolves to public
addresses and the change only refuses addresses in 100.64.0.0/10.

**R6, the 27 suites** are not run for this tag alone. F57's fix follows directly and changes more
code; its regression runs every suite twice at a tag that contains this fix, and that run covers
both. If F57's fix were abandoned, the suites would be run at this tag instead.

## 5. Ledger

One line in `notes/rewrite_plan_outline_mapping.md`: `fix-2026-10-f58`, `egress.py`,
`selftest_egress.py`, `verify/mutants/mutants.py` (M04's text, M38 new), framework fix (F58), with
what was run. Appendix F gains F58's row.
