# Phase 4.2 — reproduction from a clean checkout (first half, 2026-10-06)

**What was run.** The tag `verify-2026-10` was bundled (`git bundle`) and cloned fresh into
`~/r2exp/clean` on the Pi, a directory nothing else has written to. Every suite was run from that clone
by `verify/phase4_suites_clean.sh`, which is `experiments/selftests/suites_all.sh` at the tag changed in
two places only: where it runs and where it writes. (A) was up from the frozen copy.

**Result: 26 of 26 suites exit 0, and the clone was left clean** (`git status` empty afterwards). Each
log was compared with Phase 2's L1 log (`../../phase2/suites_run1/`) with every number masked. 16 are
identical. The other 10 differ only in the scratch directory's path (`/tmp` here, `~/r2exp/disktmp`
there), random identifiers, column padding, and `selftest`'s home-directory row, which passes here and
failed there for exactly the reason F10 records. **The code at the tag runs from a fresh clone as it does
from the working tree.** The three framework copies on the Pi (`~/r2exp/v2`, `~/r2exp/verify/v2`,
`~/r2exp/clean/v2`) are byte-identical apart from `__pycache__`, so Phase 2's L1 tested the frozen code
whichever copy it ran from.

**What this does not establish: the examiner's path.** It reused this Pi's hand-built environment
(`~/r2exp/ha314`, the corpus, the platform packages, `houseA-deps`, the memory controller already
enabled), and no document in the repository says how to build any of it. That half fails before a
command runs: F18, F19, F20 in the findings log.
