# Approval of an author-declared manifest in the Repairs panel (2026-11-26)

Why: the 8 Nov screenshots of the approval dialog (Younes's Screenshots folder, 2032*.png) show a
manifest supplied beside the integration ("These permissions were worked out for you, not declared
by the author"), while §9.3 presents an author-declared `permissions` block. Retaken for Figure 9.3.

Pi 5, Home Assistant 2026.8.3, framework from the clone of a55734f (`~/r2exp/banner-20261124/clone`;
framework identical to dfe3ec3). `component/demo_flood/manifest.json` = the repository's
`experiments/flood/demo_flood` with §9.3's example grant added as its `permissions` block.

- 09:33:30 supervisor: not started, no approval on record; the issue appeared in Repairs.
- Younes, in a browser over an ssh tunnel: opened the issue, took the two screenshots
  (laptop clock 08:36, one hour behind the Pi), pressed *Allow and start*.
- 09:37:04 "demo_flood allowed by an administrator, from the Repairs panel"; run 1 started.
  `approvals.jsonl`: provenance `author-declared`, by "an administrator, from the Repairs panel".
- 09:38:34 stopped (Claude, SIGINT), then (A) stopped.

Figure 9.3 = `Screenshot 2026-11-26 083601.png` (copied as `figures/shot_9_3_approval.png`, cropped 12/11/14/12 px left/top/right/bottom to remove the grey backdrop at the rounded corners and the 2-px strip on the right; nothing of the dialog removed; then a 2-px grey (150,150,150) frame added).
