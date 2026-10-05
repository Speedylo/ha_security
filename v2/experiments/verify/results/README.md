# Verification campaign — results

The campaign of `notes/verification_plan_20261005.md`, run on the tag `verify-2026-10` (commit
`6aa2eb6`), copied to `~/r2exp/verify/v2` on the Pi and checked file by file (704 files identical).
The claim register it tests is `verify/claims_register.md`.

| File | Phase | What |
|---|---|---|
| `environment_pre_reboot.json` | 1 | kernel, OS, Python, package-environment hashes, filesystem types (`/tmp` is tmpfs; `~/r2exp/disktmp` is ext4), corpora, credential modes |
| `phase1_after_reboot.json` | 1 | state after the reboot: nothing left running, no leftover cgroups or scratch |
| `phase1_preflight.log` | 1 | the framework's preflight on the frozen tree: 8 of 8 pass |
