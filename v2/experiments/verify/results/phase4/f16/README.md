# F16 — the 144-integration sample, rebuilt and pinned (2026-10-06)

Contribution 1's community figures (`figures/api_surface_hacs.json`, 144 integrations, 4,628
files) were parsed on 2026-08-24 from a sample whose manifest was overwritten the next day, when
the 40-integration head corpus was fetched to the same default path. This rebuilds the sample and
checks the rebuild against the committed result. Criteria: `notes/minor_findings_prediction.md`.

**Steps** (all on the Pi; each script committed before it ran):

1. `verify/rebuild_top150.py` draws the selection with the fetcher's own `candidates(150)`. It
   ranks the committed analytics snapshot of 2026-08-21 (F37), which the fetcher read, against
   today's HACS index, and takes each repository's default branch at its last commit before
   2026-08-24 20:53:36 +01:00, when the result was committed. **The same 144 domains came back.**
   Parsed with `api_surface.py` as of `671795d` under Python 3.13, 41 files failed to parse and 12
   integrations differed.
2. Under **Python 3.14**, Home Assistant 2026.8's own interpreter, the 41 parse failures vanish.
   So the original parse ran on 3.14, and "zero parse failures" holds only there. Five integrations
   still differed.
3. `verify/rebuild_top150_match.py` searched each of the five repositories' commits for the one
   whose parse equals the committed entry exactly, and found all five. `govee` is a domain
   collision: two repositories declare it, and the measured one is `lasswellt/govee-homeassistant`
   at the very commit step 1 chose, while the other overwrote it in the rebuild's directory.
   `chime_tts`, `dwains_dashboard`, `f1_sensor` and `solaredge_modbus_multi` match at commits
   older than their branch's last commit before the fetch. Neither the first-parent line nor any
   other branch explains why the original fetch got those trees. That is **not established**, and
   these four are pinned by parse equality, not by byte equality.
4. `verify/rebuild_top150_finish.py` fetched all 144 at their final commits and parsed them
   (`rebuilt_final.json`): **identical to the committed `api_surface_hacs.json`, field for field.**

**The manifest** is `figures/hacs_top150_manifest.json`. Each of the 150 candidates says how its
commit was decided: 139 by date, 5 by parse equality, and 6 not in the sample (3 replaced by a later
repository declaring the same domain, 1 collision where the other repository was measured, 2 whose
integration directory was not found). The 3 replaced, as one directory holds one domain, are
confirmed only by the result's equality.

**What this does and does not establish.** The committed figures re-derive exactly from a pinned,
refetchable sample, which is what F16 asked. For 139 repositories the sample is the one the
fetcher would have taken on that date. For the four matched by parse, it is a tree that produces
identical figures, possibly but not certainly the bytes that were parsed in August.
