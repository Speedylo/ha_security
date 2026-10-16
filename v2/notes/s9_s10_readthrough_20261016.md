# §9 and §10 week-6 read-through — 2026-10-16

Nothing in the submission changes until Younes chooses.

## §10: no changes needed

Six live services: nordpool, smhi_brandrisk, regensburg_transport and dwd_weather without credentials;
pirateweather and trakt_tv through accounts. Two local integrations against simulated devices: midea_ac_lan
and localtuya. The memory budget of 17 to 43 uses the development figures, as §12.3 does, and gives "at least
four times". The cut-off date, the rerun and F18 all match.

## §9: the numbers hold; one cross-reference is wrong, one figure is unsourced

Checked: 56–136 MB (development figures; §12.3 gives the re-measured ones); about 11 µs per push (10.9
development, 11.6 at the rerun); one integration in eight (12.5%); Appendix G exists. Table 9.2's
dictionary row still holds: `_plain` in `framework/confine/sandbox_runtime.py` passes scalars and lists of
scalars only. F54 fixed the list, so a nested dictionary is still dropped.

**C6. §9 twice sends the reader to §8 for the comparison of design candidates, and §8 doesn't contain one.**
- §9 opening: "The reasoning behind each decision belongs to the method and is given in Section 8; this
  section describes the result."
- §9.1: "The full comparison of candidates belongs to the method and is given in Section 8; the paragraphs
  below state each decision, what it rejected, and the evidence that settled it."

§8 has the threat model and the verification method. The alternatives (restricted Python, WebAssembly,
gVisor, microVMs, containers) appear only in §9.1 itself and in one sentence of §4. The comparison
probably lived in the §5.5/§5.6 that were cut. Proposed:
- Opening → "Section 8 gives the threat model these decisions answer; this section describes the result."
- §9.1 → "The paragraphs below state each decision, what it rejected, and the evidence that settled it."

**Q1. "none of the 38 manifests in the project's corpus contains one" (§9.3).** No source found. The number
is not in the working report, a notes file or a results file, and it matches neither corpus (37 + 40
measured, 75 distinct). It was added with §9.3's approval-gate text (`7c26011`). The corpora are on the Pi,
which is off, so this cannot be checked from the laptop. Options:
- (a) Verify on the Pi next time it is on: count `"permissions"` in every corpus `manifest.json`, then state
  the true number (likely "none of the 75 integrations in the two corpora").
- (b) Drop the number now: "and no integration in either of the project's corpora declares one". That still
  needs (a) before typesetting.

## Trim candidates (deferred)

- The `chroot` against `pivot_root` paragraph (§9.2, ~300 words) is the longest single explanation in the
  report. It is good defence material, but could be halved.
- §9.7's paragraph on stored data (~330 words).

## Applied 2026-10-16 (Younes: C6 both pointers fixed; Q1 verify on the Pi, text unchanged for now)

## Q1 resolved 2026-10-16 (Pi on)

On the Pi, `~/r2exp/corpus` (37 integrations, 38 `manifest.json` files: one integration has a second) and `~/r2exp/corpus_uniform` (40, 40): `grep -l "\"permissions\""` matches 0 files in either. "38 manifests" was the head corpus's file count. §9.3 now says "none of the 75 integrations in the project's two corpora declares one" (75 distinct; two are shared).
