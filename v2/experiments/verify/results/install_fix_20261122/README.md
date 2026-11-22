# Dependency builds in a sandbox, Pi 5 (aarch64), 2026-11-22

- `selftest_install.log`: a source-only probe package whose build writes outside, reads a planted
  secret, connects to a host listener and looks at a host folder. Built on the host (the installer as
  it was): all four happen. Through `compat.install_requirements` (wheels only on the host, builds in
  a no-network sandbox): none happen, and the package installs. Against the old installer the
  confined arm failed with all four leaks (fails first); PASS after the fix.
- `compare_resolved_77.jsonl` (`compare_resolved.py`): every integration of both evaluated samples
  (37 + 40) installed with the new installer and compared with the resolved versions recorded at the
  second final rerun (`final2_20261101/chunkE_step05_compat/`): 77 of 77 identical; 13 packages built
  in the sandbox.
- `suites_summary.txt`: all 36 suites (the 35 + `selftest_install`) pass on a copy of the working tree.
