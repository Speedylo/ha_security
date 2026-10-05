# Phase 3a — the exact measurements, re-run on the frozen tree

Run 2026-10-05 on `verify-2026-10`, temporary files in `/tmp` as in the golden runs, LAN a /16.
Pi time 18 minutes. Checked by `verify/check_3a.py` (control: 55/55 equal on the golden files
themselves) and `verify/compare.py`, against the pairing committed before the run
(`verify/golden_3a.json`).

## Result: 53 of 55 headlines equal; the two that differ are explained

| Measurement (Tier B) | Golden | New | Verdict |
|---|---|---|---|
| Head corpus, baseline (7.12) | 31/37, 6 failing | 31/37, same 6 | **equal** |
| Head corpus, confined, declared + core (7.12) | 31/37, 6 failing | 31/37, same 6 | **equal** → import-level cost 0 reproduces |
| Uniform corpus, baseline and confined (7.23) | 37/40 each, same 3 | 37/40 each, same 3 | **equal** → cost 0 reproduces |
| Minimal and un-stripped profiles (7.31.12) | 17/37 and 26/37 | 17/37 and 26/37, same members | **equal** |
| C1 integrity, every arm (7.29) | 0 changed, 0 lines | 0 changed, 0 lines (37, 38, 40, 40, 53, 46 trees) | **equal** |
| Entity visibility (7.14) | 36 → 1 | 36 → 1, same entity, 7 reads refused | **equal** |
| GC attack (7.15) | 7 → 0; mediator holds the token, 7 references | same; heap 8,942 both | **equal** |
| API surface, uniform corpus (7.33) | — | 0 differences | **equal** |
| Adversary, confined (7.13, 7.22.1) | 38 attacks: BLOCKED 21, DENY 6, EMPTY 10, PERMIT 1 | 40 attacks: DENY 8 | **explained**: the two attacks added after the 09-02 golden (misdirect the audit log; a malformed frame), both refused, as in today's suite log |
| Adversary, unconfined (7.13) | "connect to a TCP service on the host": BLOCKED | LEAKED | **explained**: the attack targets 127.0.0.1:8123, where (A) now runs and nothing ran on 09-02; confined it is still refused, so the pair now shows T10 against a live target |
| Egress shape on a /16 (7.24, 7.31.11) | `aiodns` 25 of 146, **17%** | 14 of 132, **11%** | **outside the criterion (17 ± 5)** by one point: F15 |
| API surface, head sample (contribution 1) | the 144-integration `hacs-top150` sample | not re-run: that corpus is not on disk | F16 |

## Errors of mine, corrected during the sitting

The first run of the two baseline arms omitted `--platform-deps`, which the golden runs used
(`notes/ch7_31_compat_rerun_prediction.md`). The baseline then failed 10 and 4 more integrations
on modules that live in `platform-deps` (`async_timeout`, `numpy`, `turbojpeg`), which looked like a
broken baseline. Re-run with the flag, both reproduce exactly. The first run is kept in
`first_run_without_platform_deps/`. And the API-surface pairing compared the 37-integration head
corpus with the 144-integration sample, which are different populations.

## Findings raised

- **F14 (Minor, traceability).** Result files do not record the command, profile or flags that
  produced them; the campaign had to reconstruct the invocation, and reconstructed it wrongly once.
- **F15 (Minor).** The `aiodns` share is not a stable figure: 17% on 2026-10-03, 11% today, with
  `frigate` alone moving from 11 to 1. The design conclusion (both seams are used, so the shim
  interposes at both) holds; the report should give the range, not one value.
- **F16 (Minor, reproducibility).** The 144-integration `hacs-top150` sample behind contribution 1's
  head figures (fetched 2026-08-24) is not kept on disk; only its result JSON is. It cannot be re-run
  as it was, and a re-fetch would get newer code.
