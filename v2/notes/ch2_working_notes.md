# Chapter 2 — working notes

**Written:** 2026-08-21. Not part of the report.

## Gate G1 result: the gap survives, but narrower than the first pass assumed

`01_PLAN.md` G1 asked whether the literature contains something close. **It does.**
Corno & Mannella [6] threat-model extensible smart-home gateways and validate the model
with a **Home Assistant use case**. That is the same problem on the same platform,
published in 2022, and it must be cited prominently rather than discovered by an examiner.

The gap survives because their contribution is a *model plus developer guidance*, and their
follow-on direction is MUD [8], which is network-layer. Neither builds or evaluates
enforcement of platform-API authority. But the honest framing changed as a result:

- ❌ **Not claimable:** "nobody has identified this problem" — false, [6] and [7] did.
- ❌ **Not claimable:** "manifest permissions for extensions are novel" — false since [1],
  2010, and the report now says so outright in §2.2.
- ✅ **Claimable:** nobody has *built and evaluated* runtime confinement for HA
  integrations, and nobody has measured what confining pre-existing, unmodifiable
  extensions costs in compatibility.

This is a **weaker-sounding but far more defensible** claim than the first pass's implicit
"novel architecture", and it matches the reframing G1 predicted. Say it before an examiner
says it.

## The strongest single argument in the chapter

Table 2.1. Prior smart-home mechanisms ([3], [4], [5]) all assume: a vendor operator, an
existing permission model, a sandbox the operator built, and apps that can be required to
migrate. Home Assistant has none of the four. That table converts "prior work doesn't
apply" from an assertion into something checkable row by row, and it is the thing to point
at if challenged with "isn't this just FlowFence for Home Assistant?".

## Confirmed 2026-08-21 via Mannella's PhD-day poster [15]

Retrieved from `phd-dauin.polito.it` (the publisher PDFs are all Cloudflare-blocked). It
confirms three things I had inferred, now from the author's own words:

1. The threat model was "to help developers during the creation (or the evaluation) of
   plug-ins" — developer-facing guidance, as characterised.
2. The Home Assistant work is "a set of proofs of concept" **demonstrating the threats** —
   i.e. attack PoCs, not a defensive prototype. Stronger than I first wrote.
3. The programme's goal is "to simplify the development of secure and reliable IoT
   solutions", focused on "developers with limited experience in IoT and/or security
   fields" — explicitly aimed at the honest-but-inexperienced author.

Point 3 is the important one. It means the likelihood-vs-impact distinction is not me
reading their work uncharitably; it is *their stated agenda*, and a legitimate one. Frame it
that way in the viva — "their goal and mine are different halves of the same problem" — not
as a deficiency in their work.

## The MUD argument — ✅ resolved 2026-08-21

§2.4 argues MUD cannot reach platform-API authority because reading entities and calling
`lock.unlock` are exercises of HA's own API over a connection any network policy must
permit. The risk flagged here was that [8] might enforce at the *gateway application* layer
rather than the network layer, which would have reduced the argument from one of category
to one of granularity and required §2.4 to be rewritten.

**It did not materialise.** [8] was obtained and read in full: enforcement is by `osMUD` on
an OpenWrt router via `iptables`, so the layer distinction holds exactly as argued. [6],
[7] and the doctoral thesis [17] were also read in full — all four PDFs are in `refs/` —
and §2.9 records the resolution in the report itself.

## Deliberate omissions

- ~~**Tyche: Risk-Based Permissions for Smart Home Platforms**~~ — **✅ no longer omitted.**
  Authorship verified (Rahmati, Fernandes, Eykholt, Prakash) and the paper obtained; cited
  as [16], discussed in §2.3 and §2.4, and it is what S5 rests on. Added in `e51eefd`.
- ~~**Mannella's PhD thesis**~~ (*Securing IoT Gateways in Smart Home Environments*, PoliTo,
  2024) — **✅ no longer omitted.** Obtained and read in full; it is [17] in `refs/`, and
  §2.4.3 is written from it. It did prove to be the fullest statement of [6] and [8], as
  guessed. Added in `dc4ff70`.
- **WebAssembly-based plugin isolation** (e.g. RLBox) — omitted as out of scope: it
  requires recompiling the extension, which the retrofit constraint forbids. Worth one
  sentence in Ch. 5's rejected-alternatives section rather than in the review.
- **Python-specific sandboxing** — deliberately not treated as literature. It is a design
  question for Ch. 5, not a research gap.

## Positioning notes for later chapters

- §2.8 splits the contribution into engineering (item 2) and research (items 1 and 3). This
  should drive page budget: the measurement and the trade-off are what an examiner can
  grade as *research*, and the first pass under-weighted both.
- §2.9's fallback — if the gap closes, items 1 and 3 survive — is deliberate insurance and
  should be repeated in the conclusion. A project that degrades gracefully under bad news
  is a stronger project.
- The complementarity with the RFC [13] is now stated in both Ch. 1 and Ch. 2. Ch. 5 must
  discharge it concretely rather than repeat it a third time.
