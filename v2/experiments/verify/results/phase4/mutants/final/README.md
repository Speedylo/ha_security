# Mutants on `verify-2026-10-final` (2026-10-06) — exit criterion 5

All 18 mutants (M01–M17, M08 split), applied to the final tag's framework and run against every
suite (`verify/mutants/run_mutants.sh`, `run.txt`, one directory per mutant). M02, M07 and M16 were
re-anchored where F33 reworked the code, with the same mutations, and committed before the run
(`771a70a`).

**18 of 18 killed**, each on its claim's own check: M01 in 10 suites, including F39's new T07 write
case; M02 `selftest_channel` "expected deny"; M03 the egress port; M04 and M05 the address checks;
M06 T11's resolved address; M07 "an action that dies leaves its record on disk: 0"; M08a and M08b
the two chains; M09 in 5 suites; M10 the subscription filter; M11 the cut-off (the flood suite runs to
its limit, and the real-platform suite shows no cut-off and no Repairs issue); M12 re-registration;
M13 the preflight refuses to confine (`unshare`, `ptrace`, `keyctl` allowed); M14 the own directory
writable; M15 the PID namespace; M16 the forged command answer (F22's case); M17 `lock.*` accepted.
Mutants ran with their own `TMPDIR` on disk, the lesson of the first run's 1.2 GB leftover.
