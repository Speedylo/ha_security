# §4 STEEPLE — plan and decisions (2026-10-15)

Budget 700 words, 2 pp; drafted at 859 prose words (trim at week 6 or on review). Skill loaded before
drafting. Rebuilt from the approved sections and the working report, with the 2026-09-08 draft
(1,346 words) as a skeleton only.

**Stale points fixed against the old draft:**
- 31.5 µs → 43 µs; ~120 MB and "26 sandboxes, ~6× margin" → 17 to 43 sandboxes vs 4.02 (Table 12.4, §10).
- "§12.6" and "§15.2" pointers removed; the coupling now names the HTTP client helper [32] and the release.
- Cyber Resilience Act placeholder → cited [53]: recital 18, Art. 24, Art. 64(10). Checked on a
  reproduction of the OJ text; EUR-Lex itself would not render to the fetcher.
- nordpool as the only live service → six live services (nordpool, smhi_brandrisk,
  regensburg_transport, dwd_weather public; pirateweather key, trakt_tv account), devices simulated
  (midea_ac_lan, localtuya), per Table 12.3.
- "no permission model" / "no record" → after F45, the user permissions exist but do not apply to an
  integration's calls [52], as §2.3.
- Household exemption now cited to the GDPR [54], with recital 18's "provide the means" clause stated
  as an open question rather than the old draft's assertion that the author "is not" exempt.

**Dropped:** the "median of 52 components vs 2" paragraph (a §7.12 result from before the
2026-10-03 rerun corrected the platform instance; it belongs in §12 if anywhere, and is not
re-checked); "single-digit watts" (unsourced); "the largest open-source smart-home platform"
(unsourced); "more than fifteen years ago" (replaced by "while their extension platforms were still new").

**For Younes:**
1. §4.7 says two live services were reached "with the author's own account" (pirateweather's key,
   trakt_tv's account). Confirm both accounts are yours.
2. §4.5 reads the CRA as leaving most community integrations without obligations ("appear to"). That
   is an interpretation of recital 18, hedged; keep, or cut to the bare citation?
3. §4.4's vendor-cloud point is presented as argument without a source. Keep as argument, or cut it?
