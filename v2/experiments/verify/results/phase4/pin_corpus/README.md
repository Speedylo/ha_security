# F21 — the two corpora, pinned and rebuilt (2026-10-06)

`figures/fetch_hacs_corpus.py` recorded `"ref": "HEAD"` for every repository, so neither corpus
Chapter 7 measured could be redrawn: the copies on the Pi were the only record.

**Pinning.** `verify/pin_corpus.py` (committed before it ran) takes each integration directory on the
Pi, computes the git blob hash of every regular file (`__pycache__` excluded: 158 such directories
were left there by earlier runs, and no repository ships one), and walks each repository's history in
a blobless clone, comparing the set of (path, blob hash) pairs at every commit that changed the
directory. A match is equality, so a near miss counts as a miss.

| Corpus | On disk | Pinned | Not matched | Newest matched commit before the fetch |
|---|---|---|---|---|
| head (`pinned_head.json`) | 37 | **37** | 2: `LaggAt/hacs-govee` and `davidrapan/ha-solarman`, the losing repositories of two domain collisions, whose copies were overwritten by `lasswellt/govee-homeassistant` and `StephanJoubert/home_assistant_solarman` | 14 h 20 min |
| uniform (`pinned_uniform.json`) | 40 | **40** | — | 5 h 12 min |

Every match predates its corpus's fetch (the directories' modification times: 2026-08-25 17:04 and
2026-09-02 22:01, +01:00). One integration matched two commits with identical contents
(`network_scanner`, a directory that returned to an earlier state); the later one is recorded.

**Rebuilding.** The commits were written into both manifests in `experiments/compat/results/`, the
fetcher was changed to resolve the commit before downloading it and to rebuild a manifest at its
commits (`--rebuild`), and both corpora were rebuilt from GitHub into fresh directories on the Pi.
`diff -r -x __pycache__` against the measured copies: **no difference, for either corpus.**

**Not recovered.** The 150-repository sample behind `figures/hacs_corpus_manifest.json` (contribution 1's
API surface) is not on disk anywhere, so there is nothing to match it against (F16).
