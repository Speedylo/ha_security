# Regression for F10, F13 and F14 (2026-10-06)

`verify/regress_minor.sh` on a fresh clone of `verify-2026-10-minor`: suites 26/26 twice; `nordpool`
end to end twice, 16/16 each. The pinning check (`pinned.log`) at first crashed. It expected a run
record from the unconfined arm, which has no mediator. The check was fixed (the confined arms only)
and run again on the same, unchanged data (`pinned_check.py`). Every criterion held: two installs
resolve identical versions (114), each records `resolved_before` 2026-10-06T00:00:00Z, and both
results carry a `.run.json` with their command line. Against the unpinned run of
`verify-2026-10-f08` the 114 versions are the same.
